#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Task-based HTTP runner for launching Flower jobs."""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import threading
from dataclasses import dataclass
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("flower-runner-api")

_LOCK = threading.RLock()
_ACTIVE_TASK: "ManagedTask | None" = None


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _resolve_path(base_dir: Path, path_value: str) -> Path:
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate.resolve()
    return (base_dir / candidate).resolve()


def _resolve_api_path(path_value: str) -> Path:
    assert CONFIG is not None

    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate.resolve()

    if candidate.parts and candidate.parts[0] == CONFIG.app_dir.name:
        return (CONFIG.app_dir.parent / candidate).resolve()

    return (CONFIG.app_dir / candidate).resolve()


def _write_json_file(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + ".tmp")
    temp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp_path.replace(path)


def _read_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning("Failed to read JSON file: %s", path)
        return {}


def _touch_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)


def _format_run_config_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def _format_run_config(run_config: dict[str, Any]) -> str:
    parts: list[str] = []
    for key, value in run_config.items():
        if value is None:
            continue
        parts.append(f"{key}={_format_run_config_value(value)}")
    return " ".join(parts)


class ServerConfig:
    def __init__(
        self,
        app_dir: str,
        runs_dir: str | None,
        federation: str | None,
        datasets_root: str | None,
    ) -> None:
        script_dir = Path(__file__).resolve().parent
        self.app_dir = _resolve_path(script_dir, app_dir)
        self.runs_dir = _resolve_path(self.app_dir, runs_dir or "runs")
        self.datasets_root = _resolve_path(self.app_dir, datasets_root or "allDatasets")
        self.default_federation = federation
        self.index_dir = self.runs_dir / ".index"


CONFIG: ServerConfig | None = None


@dataclass
class ManagedTask:
    task_id: str
    work_dir: Path
    process: subprocess.Popen[str]
    request_payload: dict[str, Any]
    status_file: Path
    summary_file: Path
    rounds_file: Path
    log_file: Path
    final_model_path: Path
    num_rounds: int | None
    started_at: str
    stop_requested: bool = False
    finalized: bool = False


def _write_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_request_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    content_length = int(handler.headers.get("Content-Length", "0"))
    if content_length <= 0:
        return {}

    raw_body = handler.rfile.read(content_length)
    if not raw_body:
        return {}

    payload = json.loads(raw_body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("JSON request body must be an object")
    return payload


def _task_index_file(task_id: str) -> Path:
    assert CONFIG is not None
    return CONFIG.index_dir / f"{task_id}.json"


def _write_task_index(task_id: str, work_dir: Path) -> None:
    _write_json_file(
        _task_index_file(task_id),
        {
            "taskId": task_id,
            "workDir": str(work_dir),
            "updatedAt": _now_iso(),
        },
    )


def _read_task_index(task_id: str) -> Path | None:
    index_payload = _read_json_file(_task_index_file(task_id))
    work_dir = index_payload.get("workDir")
    if not work_dir:
        return None
    return Path(str(work_dir))


def _default_work_dir(task_id: str) -> Path:
    assert CONFIG is not None
    return (CONFIG.runs_dir / task_id).resolve()


def _resolve_task_work_dir(task_id: str) -> Path | None:
    with _LOCK:
        if _ACTIVE_TASK is not None and _ACTIVE_TASK.task_id == task_id:
            return _ACTIVE_TASK.work_dir

    indexed = _read_task_index(task_id)
    if indexed is not None:
        return indexed.resolve()

    default_dir = _default_work_dir(task_id)
    if default_dir.exists():
        return default_dir
    return None


def _task_paths(work_dir: Path) -> dict[str, Path]:
    return {
        "task": work_dir / "task.json",
        "status": work_dir / "status.json",
        "summary": work_dir / "summary.json",
        "rounds": work_dir / "round_metrics.jsonl",
        "log": work_dir / "train.log",
        "final_model": work_dir / "final_model.pt",
    }


def _to_public_api_path(path: Path) -> str:
    assert CONFIG is not None

    resolved = path.resolve()
    try:
        return resolved.relative_to(CONFIG.app_dir.parent).as_posix()
    except ValueError:
        return str(resolved).replace("\\", "/")


def _detect_dataset_format(dataset_path: Path) -> str:
    try:
        for child in dataset_path.rglob("*.xml"):
            if child.is_file():
                return "VOC"
    except OSError:
        logger.warning("Failed to inspect dataset format under %s", dataset_path)

    if (dataset_path / "data.yaml").is_file():
        return "YOLO"
    if (dataset_path / "labels").is_dir():
        return "YOLO"
    if (dataset_path / "train" / "labels").is_dir():
        return "YOLO"
    if (dataset_path / "valid" / "labels").is_dir():
        return "YOLO"
    if (dataset_path / "val" / "labels").is_dir():
        return "YOLO"
    return "UNKNOWN"


def _list_datasets() -> list[dict[str, Any]]:
    assert CONFIG is not None

    root = CONFIG.datasets_root
    if not root.exists() or not root.is_dir():
        return []

    items: list[dict[str, Any]] = []
    try:
        for child in sorted(root.iterdir(), key=lambda path: path.name.lower()):
            if not child.is_dir():
                continue
            items.append(
                {
                    "name": child.name,
                    "path": _to_public_api_path(child),
                    "format": _detect_dataset_format(child),
                }
            )
    except OSError:
        logger.warning("Failed to scan datasets under %s", root)
        return []

    return items


def _read_round_metrics(rounds_file: Path) -> list[dict[str, Any]]:
    if not rounds_file.exists():
        return []

    items: list[dict[str, Any]] = []
    try:
        with rounds_file.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning("Skipping invalid round metrics line in %s", rounds_file)
                    continue
                if isinstance(payload, dict):
                    items.append(payload)
    except OSError:
        logger.warning("Failed to read round metrics file: %s", rounds_file)
    return items


def _build_latest_metrics(rounds_file: Path) -> tuple[int, dict[str, Any] | None]:
    rounds = _read_round_metrics(rounds_file)
    if not rounds:
        return 0, None

    last_item = rounds[-1]
    round_no = int(last_item.get("roundNo") or 0)
    metrics = last_item.get("metrics")
    return round_no, metrics if isinstance(metrics, dict) else None


def _merge_status_file(status_file: Path, updates: dict[str, Any]) -> dict[str, Any]:
    payload = _read_json_file(status_file)
    payload.update(updates)
    _write_json_file(status_file, payload)
    return payload


def _merge_summary_file(summary_file: Path, updates: dict[str, Any]) -> dict[str, Any]:
    payload = _read_json_file(summary_file)
    payload.update(updates)
    _write_json_file(summary_file, payload)
    return payload


def _detect_error_message(exit_code: int, stop_requested: bool) -> str | None:
    if stop_requested:
        return None
    if exit_code == 0:
        return None
    return f"Flower run exited with code {exit_code}"


def _refresh_active_task_locked() -> None:
    global _ACTIVE_TASK
    if _ACTIVE_TASK is None:
        return
    if _ACTIVE_TASK.process.poll() is None:
        return
    _finalize_task_locked(_ACTIVE_TASK, _ACTIVE_TASK.process.poll() or 0)


def _build_command(
    run_config: dict[str, Any],
    federation: str | None,
    federation_config: dict[str, Any] | None,
) -> list[str]:
    command = ["flwr", "run", "."]
    target_federation = federation or (CONFIG.default_federation if CONFIG is not None else None)
    if target_federation:
        command.append(target_federation)

    federation_config_text = _format_run_config(federation_config or {})
    if federation_config_text:
        command.extend(["--federation-config", federation_config_text])

    run_config_text = _format_run_config(run_config)
    if run_config_text:
        command.extend(["--run-config", run_config_text])

    return command


def _task_response(task_id: str, work_dir: Path) -> dict[str, Any]:
    paths = _task_paths(work_dir)
    task_payload = _read_json_file(paths["task"])
    status_payload = _read_json_file(paths["status"])
    summary_payload = _read_json_file(paths["summary"])
    current_round, latest_metrics = _build_latest_metrics(paths["rounds"])

    if not status_payload:
        return {"taskId": task_id, "status": "UNKNOWN"}

    if not status_payload.get("currentRound"):
        status_payload["currentRound"] = current_round

    if not status_payload.get("latestMetrics") and latest_metrics is not None:
        status_payload["latestMetrics"] = latest_metrics

    final_metrics = summary_payload.get("finalMetrics")
    final_model_path = summary_payload.get("finalModelPath")
    if not final_model_path and paths["final_model"].exists():
        final_model_path = str(paths["final_model"])

    return {
        "taskId": task_id,
        "status": status_payload.get("status", "UNKNOWN"),
        "currentRound": status_payload.get("currentRound", 0),
        "numRounds": status_payload.get("numRounds")
        or task_payload.get("runConfig", {}).get("num-server-rounds"),
        "latestMetrics": status_payload.get("latestMetrics"),
        "finalMetrics": final_metrics,
        "finalModelPath": final_model_path,
        "errorMessage": status_payload.get("errorMessage"),
        "startedAt": status_payload.get("startedAt"),
        "finishedAt": status_payload.get("finishedAt"),
        "pid": status_payload.get("pid"),
        "workDir": str(work_dir),
    }


def _stream_process_output(task: ManagedTask) -> None:
    if task.process.stdout is None:
        return

    with task.log_file.open("a", encoding="utf-8") as log_handle:
        for line in task.process.stdout:
            log_handle.write(line)
            log_handle.flush()
            logger.info("[%s] %s", task.task_id, line.rstrip())


def _finalize_task_locked(task: ManagedTask, exit_code: int) -> None:
    global _ACTIVE_TASK

    if task.finalized:
        if _ACTIVE_TASK is not None and _ACTIVE_TASK.task_id == task.task_id and task.process.poll() is not None:
            _ACTIVE_TASK = None
        return

    task.finalized = True

    round_no, latest_metrics = _build_latest_metrics(task.rounds_file)
    summary_payload = _read_json_file(task.summary_file)
    final_metrics = summary_payload.get("finalMetrics")
    final_model_path = summary_payload.get("finalModelPath")
    if not final_model_path and task.final_model_path.exists():
        final_model_path = str(task.final_model_path)

    final_status = str(summary_payload.get("status") or "")
    if task.stop_requested:
        final_status = "STOPPED"
    elif not final_status:
        final_status = "COMPLETED" if exit_code == 0 else "FAILED"

    finished_at = summary_payload.get("finishedAt") or _now_iso()
    error_message = summary_payload.get("errorMessage") or _detect_error_message(exit_code, task.stop_requested)

    _merge_status_file(
        task.status_file,
        {
            "taskId": task.task_id,
            "status": final_status,
            "currentRound": round_no,
            "numRounds": task.num_rounds,
            "latestMetrics": latest_metrics,
            "finalMetrics": final_metrics,
            "finalModelPath": final_model_path,
            "errorMessage": error_message,
            "startedAt": task.started_at,
            "finishedAt": finished_at,
            "pid": None,
            "updatedAt": _now_iso(),
        },
    )

    _merge_summary_file(
        task.summary_file,
        {
            "taskId": task.task_id,
            "status": final_status,
            "finalMetrics": final_metrics,
            "finalModelPath": final_model_path,
            "errorMessage": error_message,
            "startedAt": task.started_at,
            "finishedAt": finished_at,
            "updatedAt": _now_iso(),
        },
    )

    if _ACTIVE_TASK is not None and _ACTIVE_TASK.task_id == task.task_id:
        _ACTIVE_TASK = None


def _watch_process(task: ManagedTask) -> None:
    exit_code = task.process.wait()
    with _LOCK:
        _finalize_task_locked(task, exit_code)


def _stop_process_tree(process: subprocess.Popen[str]) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        process.wait(timeout=10)
        return

    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _create_task(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    global _ACTIVE_TASK
    assert CONFIG is not None

    task_id = str(payload.get("taskId") or "").strip()
    if not task_id:
        return 400, {"error": "taskId is required"}

    run_config = payload.get("runConfig") or {}
    if not isinstance(run_config, dict):
        return 400, {"error": "runConfig must be an object"}

    env_payload = payload.get("env") or {}
    if not isinstance(env_payload, dict):
        return 400, {"error": "env must be an object"}

    federation_config = payload.get("federationConfig") or {}
    if not isinstance(federation_config, dict):
        return 400, {"error": "federationConfig must be an object"}

    body_app_dir = str(payload.get("appDir") or ".")
    body_federation = payload.get("federation")
    work_dir_value = str(payload.get("workDir") or _default_work_dir(task_id))
    app_dir = _resolve_api_path(body_app_dir)
    work_dir = _resolve_api_path(work_dir_value)
    paths = _task_paths(work_dir)

    with _LOCK:
        _refresh_active_task_locked()
        if _ACTIVE_TASK is not None:
            return 409, {
                "error": "Another Flower task is already running",
                "activeTaskId": _ACTIVE_TASK.task_id,
            }

        if paths["task"].exists():
            return 409, {"error": f"Task already exists: {task_id}"}

        work_dir.mkdir(parents=True, exist_ok=True)
        _touch_file(paths["rounds"])
        _touch_file(paths["log"])
        _write_task_index(task_id, work_dir)

        started_at = _now_iso()
        num_rounds = run_config.get("num-server-rounds")
        env = os.environ.copy()
        env.update({str(key): str(value) for key, value in env_payload.items()})
        env.update(
            {
                "PYTHONUNBUFFERED": "1",
                "FLOWER_TASK_ID": task_id,
                "FLOWER_TASK_DIR": str(work_dir),
                "FLOWER_STATUS_FILE": str(paths["status"]),
                "FLOWER_SUMMARY_FILE": str(paths["summary"]),
                "FLOWER_ROUND_METRICS_FILE": str(paths["rounds"]),
                "FLOWER_FINAL_MODEL_PATH": str(paths["final_model"]),
            }
        )

        command = _build_command(
            run_config,
            str(body_federation) if body_federation else None,
            federation_config,
        )
        request_snapshot = {
            "taskId": task_id,
            "appDir": str(app_dir),
            "workDir": str(work_dir),
            "federation": body_federation or CONFIG.default_federation,
            "federationConfig": federation_config,
            "runConfig": run_config,
            "env": env_payload,
            "command": command,
            "createdAt": started_at,
        }

        _write_json_file(paths["task"], request_snapshot)
        _write_json_file(
            paths["status"],
            {
                "taskId": task_id,
                "status": "CREATED",
                "currentRound": 0,
                "numRounds": num_rounds,
                "latestMetrics": None,
                "finalMetrics": None,
                "finalModelPath": None,
                "errorMessage": None,
                "startedAt": None,
                "finishedAt": None,
                "pid": None,
                "updatedAt": started_at,
            },
        )

        try:
            process = subprocess.Popen(
                command,
                cwd=app_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
        except Exception as exc:
            logger.exception("Failed to start Flower task %s", task_id)
            failed_at = _now_iso()
            _merge_status_file(
                paths["status"],
                {
                    "status": "FAILED",
                    "startedAt": started_at,
                    "finishedAt": failed_at,
                    "errorMessage": str(exc),
                    "updatedAt": failed_at,
                },
            )
            _merge_summary_file(
                paths["summary"],
                {
                    "taskId": task_id,
                    "status": "FAILED",
                    "errorMessage": str(exc),
                    "startedAt": started_at,
                    "finishedAt": failed_at,
                    "updatedAt": failed_at,
                },
            )
            return 500, {"error": f"Failed to start task: {exc}"}

        task = ManagedTask(
            task_id=task_id,
            work_dir=work_dir,
            process=process,
            request_payload=request_snapshot,
            status_file=paths["status"],
            summary_file=paths["summary"],
            rounds_file=paths["rounds"],
            log_file=paths["log"],
            final_model_path=paths["final_model"],
            num_rounds=int(num_rounds) if isinstance(num_rounds, (int, float)) else None,
            started_at=started_at,
        )
        _ACTIVE_TASK = task

        _merge_status_file(
            paths["status"],
            {
                "status": "RUNNING",
                "startedAt": started_at,
                "pid": process.pid,
                "updatedAt": _now_iso(),
            },
        )

    threading.Thread(target=_stream_process_output, args=(task,), daemon=True).start()
    threading.Thread(target=_watch_process, args=(task,), daemon=True).start()

    logger.info("Started Flower task %s with pid %s", task_id, process.pid)
    return 200, {
        "taskId": task_id,
        "status": "RUNNING",
        "pid": process.pid,
        "workDir": str(work_dir),
    }


def _stop_task(task_id: str) -> tuple[int, dict[str, Any]]:
    with _LOCK:
        _refresh_active_task_locked()
        if _ACTIVE_TASK is None or _ACTIVE_TASK.task_id != task_id:
            work_dir = _resolve_task_work_dir(task_id)
            if work_dir is None:
                return 404, {"error": f"Task not found: {task_id}"}
            return 409, {"error": f"Task is not running: {task_id}"}

        task = _ACTIVE_TASK
        task.stop_requested = True
        try:
            _stop_process_tree(task.process)
        except Exception as exc:
            logger.exception("Failed to stop Flower task %s", task_id)
            return 500, {"error": f"Failed to stop task: {exc}"}

        _finalize_task_locked(task, task.process.poll() or 0)
        response = _task_response(task_id, task.work_dir)
        logger.info("Stopped Flower task %s", task_id)
        return 200, response


class ControlHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        parts = [part for part in parsed.path.split("/") if part]

        try:
            if parsed.path == "/health":
                with _LOCK:
                    _refresh_active_task_locked()
                    payload = {
                        "ok": True,
                        "running": _ACTIVE_TASK is not None,
                        "activeTaskId": _ACTIVE_TASK.task_id if _ACTIVE_TASK is not None else None,
                        "appDir": str(CONFIG.app_dir) if CONFIG is not None else None,
                        "runsDir": str(CONFIG.runs_dir) if CONFIG is not None else None,
                        "datasetsRoot": str(CONFIG.datasets_root) if CONFIG is not None else None,
                    }
                _write_response(self, 200, payload)
                return

            if parsed.path == "/status":
                with _LOCK:
                    _refresh_active_task_locked()
                    payload = {
                        "running": _ACTIVE_TASK is not None,
                        "taskId": _ACTIVE_TASK.task_id if _ACTIVE_TASK is not None else None,
                    }
                _write_response(self, 200, payload)
                return

            if len(parts) == 3 and parts[0] == "runner" and parts[1] == "tasks":
                task_id = parts[2]
                work_dir = _resolve_task_work_dir(task_id)
                if work_dir is None:
                    _write_response(self, 404, {"error": f"Task not found: {task_id}"})
                    return
                with _LOCK:
                    _refresh_active_task_locked()
                _write_response(self, 200, _task_response(task_id, work_dir))
                return

            if len(parts) == 2 and parts[0] == "runner" and parts[1] == "datasets":
                _write_response(self, 200, {"items": _list_datasets()})
                return

            if len(parts) == 4 and parts[0] == "runner" and parts[1] == "tasks" and parts[3] == "rounds":
                task_id = parts[2]
                work_dir = _resolve_task_work_dir(task_id)
                if work_dir is None:
                    _write_response(self, 404, {"error": f"Task not found: {task_id}"})
                    return

                query_params = parse_qs(parsed.query)
                after_round = int(query_params.get("afterRound", ["0"])[0] or 0)
                rounds = [
                    item
                    for item in _read_round_metrics(_task_paths(work_dir)["rounds"])
                    if int(item.get("roundNo") or 0) > after_round
                ]
                _write_response(self, 200, {"taskId": task_id, "items": rounds})
                return

            _write_response(self, 404, {"error": "not found"})
        except ValueError as exc:
            _write_response(self, 400, {"error": str(exc)})
        except Exception as exc:  # pragma: no cover - defensive HTTP error handling
            logger.exception("Unhandled GET error")
            _write_response(self, 500, {"error": str(exc)})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        parts = [part for part in parsed.path.split("/") if part]

        try:
            if len(parts) == 2 and parts[0] == "runner" and parts[1] == "tasks":
                payload = _read_request_json(self)
                status, response = _create_task(payload)
                _write_response(self, status, response)
                return

            if len(parts) == 4 and parts[0] == "runner" and parts[1] == "tasks" and parts[3] == "stop":
                task_id = parts[2]
                status, response = _stop_task(task_id)
                _write_response(self, status, response)
                return

            if parsed.path == "/stop":
                with _LOCK:
                    _refresh_active_task_locked()
                    active_task_id = _ACTIVE_TASK.task_id if _ACTIVE_TASK is not None else None
                if active_task_id is None:
                    _write_response(self, 200, {"stopped": False})
                    return
                status, response = _stop_task(active_task_id)
                payload = {"stopped": status == 200, "taskId": active_task_id, "details": response}
                _write_response(self, status, payload)
                return

            _write_response(self, 404, {"error": "not found"})
        except ValueError as exc:
            _write_response(self, 400, {"error": str(exc)})
        except Exception as exc:  # pragma: no cover - defensive HTTP error handling
            logger.exception("Unhandled POST error")
            _write_response(self, 500, {"error": str(exc)})

    def log_message(self, fmt: str, *args: Any) -> None:
        logger.info("%s - %s", self.address_string(), fmt % args)


def main() -> None:
    parser = argparse.ArgumentParser(description="Flower task runner API")
    parser.add_argument("--host", default="0.0.0.0", help="HTTP host to bind")
    parser.add_argument("--port", type=int, default=9000, help="HTTP port to bind")
    parser.add_argument(
        "--app-dir",
        default=".",
        help="Flower app directory. Defaults to the directory containing this script.",
    )
    parser.add_argument(
        "--runs-dir",
        default="runs",
        help="Directory used to store task runtime artifacts.",
    )
    parser.add_argument(
        "--federation",
        default=None,
        help="Optional default Flower federation name.",
    )
    parser.add_argument(
        "--datasets-root",
        default="allDatasets",
        help="Directory used to scan datasets for the HTTP API.",
    )
    args = parser.parse_args()

    global CONFIG
    CONFIG = ServerConfig(
        app_dir=args.app_dir,
        runs_dir=args.runs_dir,
        federation=args.federation,
        datasets_root=args.datasets_root,
    )

    httpd = ThreadingHTTPServer((args.host, args.port), ControlHandler)
    logger.info(
        "Flower runner API listening on %s:%s, app_dir=%s, runs_dir=%s, datasets_root=%s",
        args.host,
        args.port,
        CONFIG.app_dir,
        CONFIG.runs_dir,
        CONFIG.datasets_root,
    )
    httpd.serve_forever()


if __name__ == "__main__":
    main()
