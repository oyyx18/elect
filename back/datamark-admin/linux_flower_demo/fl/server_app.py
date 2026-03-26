"""Flower ServerApp entry point."""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import torch
from flwr.app import ArrayRecord, ConfigRecord, Context, MetricRecord
from flwr.serverapp import Grid, ServerApp
from flwr.serverapp.strategy import FedAvg

from fl.task import get_task

app = ServerApp()
TASK_MODULE = None
LAST_ROUND_METRICS: dict[str, Any] | None = None
RUNTIME: "RuntimeFiles | None" = None


@dataclass
class RuntimeFiles:
    task_id: str | None
    task_dir: Path | None
    status_file: Path | None
    summary_file: Path | None
    rounds_file: Path | None
    final_model_path: Path
    started_at: str
    num_rounds: int | None


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _resolve_env_path(name: str) -> Path | None:
    value = os.getenv(name)
    if not value:
        return None
    return Path(value).expanduser().resolve()


def _write_json_file(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + ".tmp")
    temp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp_path.replace(path)


def _read_json_file(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _merge_json_file(path: Path | None, updates: dict[str, Any]) -> dict[str, Any]:
    if path is None:
        return updates
    payload = _read_json_file(path)
    payload.update(updates)
    _write_json_file(path, payload)
    return payload


def _append_jsonl(path: Path | None, payload: dict[str, Any]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False))
        handle.write("\n")


def _serialize_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    serialized: dict[str, Any] = {}
    for key, value in metrics.items():
        if isinstance(value, bool):
            serialized[str(key)] = value
            continue
        try:
            serialized[str(key)] = float(value)
        except (TypeError, ValueError):
            continue
    return serialized


def _init_runtime(num_rounds: int | None = None) -> RuntimeFiles:
    global RUNTIME

    if RUNTIME is not None:
        if num_rounds is not None:
            RUNTIME.num_rounds = num_rounds
        return RUNTIME

    task_dir = _resolve_env_path("FLOWER_TASK_DIR")
    status_file = _resolve_env_path("FLOWER_STATUS_FILE")
    summary_file = _resolve_env_path("FLOWER_SUMMARY_FILE")
    rounds_file = _resolve_env_path("FLOWER_ROUND_METRICS_FILE")
    final_model_path = _resolve_env_path("FLOWER_FINAL_MODEL_PATH") or Path("final_model.pt").resolve()

    RUNTIME = RuntimeFiles(
        task_id=os.getenv("FLOWER_TASK_ID"),
        task_dir=task_dir,
        status_file=status_file,
        summary_file=summary_file,
        rounds_file=rounds_file,
        final_model_path=final_model_path,
        started_at=_now_iso(),
        num_rounds=num_rounds,
    )
    return RUNTIME


def _update_status(
    status: str,
    *,
    current_round: int | None = None,
    latest_metrics: dict[str, Any] | None = None,
    final_metrics: dict[str, Any] | None = None,
    final_model_path: str | None = None,
    error_message: str | None = None,
    finished_at: str | None = None,
) -> None:
    runtime = _init_runtime()
    updates: dict[str, Any] = {
        "taskId": runtime.task_id,
        "status": status,
        "numRounds": runtime.num_rounds,
        "startedAt": runtime.started_at,
        "updatedAt": _now_iso(),
    }

    if current_round is not None:
        updates["currentRound"] = current_round
    if latest_metrics is not None:
        updates["latestMetrics"] = latest_metrics
    if final_metrics is not None:
        updates["finalMetrics"] = final_metrics
    if final_model_path is not None:
        updates["finalModelPath"] = final_model_path
    if error_message is not None:
        updates["errorMessage"] = error_message
    if finished_at is not None:
        updates["finishedAt"] = finished_at

    _merge_json_file(runtime.status_file, updates)


def _update_summary(
    status: str,
    *,
    final_metrics: dict[str, Any] | None = None,
    final_model_path: str | None = None,
    error_message: str | None = None,
    finished_at: str | None = None,
) -> None:
    runtime = _init_runtime()
    updates: dict[str, Any] = {
        "taskId": runtime.task_id,
        "status": status,
        "startedAt": runtime.started_at,
        "updatedAt": _now_iso(),
    }

    if final_metrics is not None:
        updates["finalMetrics"] = final_metrics
    if final_model_path is not None:
        updates["finalModelPath"] = final_model_path
    if error_message is not None:
        updates["errorMessage"] = error_message
    if finished_at is not None:
        updates["finishedAt"] = finished_at

    _merge_json_file(runtime.summary_file, updates)


def _record_round_metrics(server_round: int, metrics: dict[str, Any]) -> None:
    runtime = _init_runtime()
    payload = {
        "taskId": runtime.task_id,
        "roundNo": server_round,
        "metrics": metrics,
        "timestamp": _now_iso(),
    }
    _append_jsonl(runtime.rounds_file, payload)


def _build_metric_record(test_loss: float, test_metrics: Any) -> dict[str, Any]:
    if isinstance(test_metrics, (dict, MetricRecord)):
        metrics = dict(test_metrics)
    else:
        metric_name = getattr(TASK_MODULE, "METRIC_NAME", "metric")
        metrics = {metric_name: float(test_metrics)}

    serialized = _serialize_metrics(metrics)
    serialized["loss"] = float(test_loss)
    return serialized


@app.main()
def main(grid: Grid, context: Context) -> None:
    """Main entry point for the ServerApp."""

    global LAST_ROUND_METRICS
    global TASK_MODULE

    fraction_evaluate: float = context.run_config["fraction-evaluate"]
    num_rounds: int = context.run_config["num-server-rounds"]
    node_count = max(1, int(context.run_config.get("node-count", 2)))
    lr: float = context.run_config["learning-rate"]
    TASK_MODULE = get_task(context.run_config.get("task-type"))
    LAST_ROUND_METRICS = None
    runtime = _init_runtime(num_rounds)

    global_model = TASK_MODULE.Net()
    arrays = ArrayRecord(global_model.state_dict())
    min_evaluate_nodes = 0 if fraction_evaluate <= 0 else max(1, min(node_count, math.ceil(node_count * fraction_evaluate)))
    strategy = FedAvg(
        fraction_evaluate=fraction_evaluate,
        min_train_nodes=node_count,
        min_evaluate_nodes=min_evaluate_nodes,
        min_available_nodes=node_count,
    )

    _update_status("RUNNING", current_round=0)

    try:
        result = strategy.start(
            grid=grid,
            initial_arrays=arrays,
            train_config=ConfigRecord({"lr": lr}),
            num_rounds=num_rounds,
            evaluate_fn=global_evaluate,
        )

        print("\nSaving final model to disk...")
        state_dict = result.arrays.to_torch_state_dict()
        runtime.final_model_path.parent.mkdir(parents=True, exist_ok=True)
        if hasattr(TASK_MODULE, "save_model"):
            TASK_MODULE.save_model(state_dict, runtime.final_model_path)
        else:
            torch.save(state_dict, runtime.final_model_path)

        finished_at = _now_iso()
        _update_summary(
            "COMPLETED",
            final_metrics=LAST_ROUND_METRICS,
            final_model_path=str(runtime.final_model_path),
            finished_at=finished_at,
        )
        _update_status(
            "COMPLETED",
            current_round=num_rounds,
            latest_metrics=LAST_ROUND_METRICS,
            final_metrics=LAST_ROUND_METRICS,
            final_model_path=str(runtime.final_model_path),
            finished_at=finished_at,
        )
    except Exception as exc:
        finished_at = _now_iso()
        error_message = str(exc)
        _update_summary(
            "FAILED",
            final_metrics=LAST_ROUND_METRICS,
            error_message=error_message,
            finished_at=finished_at,
        )
        _update_status(
            "FAILED",
            latest_metrics=LAST_ROUND_METRICS,
            final_metrics=LAST_ROUND_METRICS,
            error_message=error_message,
            finished_at=finished_at,
        )
        raise


def global_evaluate(server_round: int, arrays: ArrayRecord) -> MetricRecord:
    """Evaluate model on central data."""

    global LAST_ROUND_METRICS
    global TASK_MODULE

    if TASK_MODULE is None:
        TASK_MODULE = get_task()

    model = TASK_MODULE.Net()
    model.load_state_dict(arrays.to_torch_state_dict())
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    model.to(device)

    test_dataloader = TASK_MODULE.load_centralized_dataset()
    test_loss, test_metrics = TASK_MODULE.test(model, test_dataloader, device)
    metrics = _build_metric_record(test_loss, test_metrics)

    LAST_ROUND_METRICS = metrics
    _record_round_metrics(server_round, metrics)
    _update_status("RUNNING", current_round=server_round, latest_metrics=metrics)

    return MetricRecord(metrics)
