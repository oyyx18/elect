#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal HTTP control plane for launching a Flower run."""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Optional
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("flower-server-api")

_LOCK = threading.Lock()
_PROCESS: Optional[subprocess.Popen] = None


class ServerConfig:
    def __init__(self, app_dir: str) -> None:
        self.app_dir = os.path.abspath(app_dir)

    @property
    def server_cwd(self) -> str:
        return os.getcwd()


CONFIG: Optional[ServerConfig] = None


def _write_json(handler: BaseHTTPRequestHandler, status: int, payload: Dict[str, Any]) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _build_command() -> list[str]:
    assert CONFIG is not None
    app_dir = CONFIG.app_dir
    if app_dir == ".":
        resolved_app_dir = CONFIG.server_cwd
    elif os.path.isabs(app_dir):
        resolved_app_dir = app_dir
    else:
        resolved_app_dir = os.path.abspath(os.path.join(CONFIG.server_cwd, app_dir))
        if not os.path.isdir(resolved_app_dir) and os.path.basename(CONFIG.server_cwd) == app_dir:
            resolved_app_dir = CONFIG.server_cwd

    return ["flwr", "run"]


def _start_server() -> bool:
    with _LOCK:
        global _PROCESS
        if _PROCESS is not None and _PROCESS.poll() is None:
            logger.info("Flower run already active")
            return True

        cmd = _build_command()
        logger.info("Starting Flower run: %s", " ".join(cmd))
        _PROCESS = subprocess.Popen(
            cmd,
            cwd=CONFIG.server_cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        threading.Thread(target=_stream_logs, args=(_PROCESS,), daemon=True).start()
        return True


def _stream_logs(process: subprocess.Popen) -> None:
    if process.stdout is None:
        return
    for line in process.stdout:
        logger.info("[Flower] %s", line.rstrip())


def _stop_server() -> bool:
    with _LOCK:
        global _PROCESS
        if _PROCESS is None:
            return False
        if _PROCESS.poll() is None:
            _PROCESS.terminate()
            try:
                _PROCESS.wait(timeout=10)
            except subprocess.TimeoutExpired:
                _PROCESS.kill()
        return True


def _is_running() -> bool:
    with _LOCK:
        return _PROCESS is not None and _PROCESS.poll() is None


class ControlHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            _write_json(self, 200, {"ok": True})
            return
        if parsed.path == "/status":
            _write_json(self, 200, {"running": _is_running()})
            return
        _write_json(self, 404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path == "/start":
            ok = _start_server()
            _write_json(self, 200, {"started": ok})
            return
        if self.path == "/stop":
            ok = _stop_server()
            _write_json(self, 200, {"stopped": ok})
            return
        _write_json(self, 404, {"error": "not found"})

    def log_message(self, format: str, *args: Any) -> None:
        logger.info("%s - %s", self.address_string(), format % args)


def main() -> None:
    parser = argparse.ArgumentParser(description="Flower server control API")
    parser.add_argument("--host", default="0.0.0.0", help="HTTP host to bind")
    parser.add_argument("--port", type=int, default=9000, help="HTTP port to bind")
    parser.add_argument("--app-dir", default="flower_app", help="Flower app directory")
    args = parser.parse_args()

    global CONFIG
    CONFIG = ServerConfig(app_dir=args.app_dir)

    httpd = ThreadingHTTPServer((args.host, args.port), ControlHandler)
    logger.info("Flower control API listening on %s:%s", args.host, args.port)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
