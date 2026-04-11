#!/usr/bin/env python3
"""
WebmasterOS Ollama Bridge

Tiny localhost helper that proxies browser-extension requests to a local Ollama
server from a non-browser process. This avoids browser-origin restrictions while
keeping the extension-side protocol simple.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_BIND_HOST = "127.0.0.1"
DEFAULT_BIND_PORT = 19081
DEFAULT_UPSTREAM = "http://127.0.0.1:11434"
APP_VERSION = "0.1.1"

LOGGER = logging.getLogger("webmasteros.ollama_bridge")


def default_config_path() -> Path:
    system = platform.system().lower()
    home = Path.home()
    if system == "windows":
        appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
        return appdata / "WebmasterOS" / "OllamaBridge" / "config.json"
    if system == "darwin":
        return home / "Library" / "Application Support" / "WebmasterOS" / "OllamaBridge" / "config.json"
    return home / ".config" / "webmasteros" / "ollama-bridge" / "config.json"


def default_config_values() -> dict:
    return {
        "host": DEFAULT_BIND_HOST,
        "port": DEFAULT_BIND_PORT,
        "ollama_url": DEFAULT_UPSTREAM,
        "allow_origins": [],
        "auto_detect_upstream": True,
        "log_file": "",
    }


def default_log_path(config_path: Path) -> Path:
    return config_path.parent / "logs" / "bridge.log"


def detect_upstream(default_value: str) -> str:
    candidates = [
        default_value,
        "http://127.0.0.1:11434",
        "http://host.docker.internal:11434",
        "http://172.17.80.1:11434",
    ]
    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        status, payload, _headers = json_request(f"{candidate.rstrip('/')}/api/tags", method="GET", timeout=2)
        if status == 200 and isinstance(payload, dict):
            return candidate.rstrip("/")
    return default_value.rstrip("/")


def ensure_config_file(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(default_config_values(), indent=2) + "\n", encoding="utf-8")


def load_config(path: Path) -> dict:
    ensure_config_file(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = default_config_values()
    if not isinstance(data, dict):
        data = default_config_values()
    merged = default_config_values()
    merged.update(data)
    if merged.get("auto_detect_upstream", True):
        merged["ollama_url"] = detect_upstream(str(merged.get("ollama_url", DEFAULT_UPSTREAM)))
    else:
        merged["ollama_url"] = str(merged.get("ollama_url", DEFAULT_UPSTREAM)).rstrip("/")
    merged["host"] = str(merged.get("host", DEFAULT_BIND_HOST))
    merged["port"] = int(merged.get("port", DEFAULT_BIND_PORT))
    merged["allow_origins"] = list(merged.get("allow_origins") or [])
    merged["log_file"] = str(Path(merged.get("log_file") or default_log_path(path)).expanduser())
    return merged


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the WebmasterOS Ollama Bridge.")
    parser.add_argument("--config", default=str(default_config_path()), help="Path to the bridge config file.")
    parser.add_argument("--write-default-config", action="store_true", help="Write a default config file and exit.")
    parser.add_argument("--print-config-path", action="store_true", help="Print the resolved config path and exit.")
    parser.add_argument("--host", default=None, help="Override bind host for the bridge.")
    parser.add_argument("--port", type=int, default=None, help="Override bind port for the bridge.")
    parser.add_argument(
        "--ollama-url",
        default=None,
        help="Base URL for the upstream Ollama server, for example http://127.0.0.1:11434 or a Windows host IP from WSL.",
    )
    parser.add_argument(
        "--allow-origin",
        action="append",
        default=None,
        help="Optional allowed Origin header. May be repeated. Overrides config. Default is permissive for local bridge use.",
    )
    return parser.parse_args()


ARGS = parse_args()
CONFIG_PATH = Path(ARGS.config).expanduser()

if ARGS.print_config_path:
    print(CONFIG_PATH)
    raise SystemExit(0)

if ARGS.write_default_config:
    ensure_config_file(CONFIG_PATH)
    print(f"Wrote default config to {CONFIG_PATH}")
    raise SystemExit(0)

CONFIG = load_config(CONFIG_PATH)
BIND_HOST = ARGS.host or CONFIG["host"]
BIND_PORT = ARGS.port if ARGS.port is not None else CONFIG["port"]
UPSTREAM = (ARGS.ollama_url or CONFIG["ollama_url"]).rstrip("/")
ALLOWED_ORIGINS = set(ARGS.allow_origin if ARGS.allow_origin is not None else CONFIG["allow_origins"])
LOG_PATH = Path(CONFIG["log_file"]).expanduser()


def setup_logging(log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    LOGGER.setLevel(logging.INFO)
    LOGGER.handlers.clear()
    LOGGER.propagate = False

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    LOGGER.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    LOGGER.addHandler(stream_handler)


setup_logging(LOG_PATH)


def json_request(url: str, method: str = "GET", payload: dict | None = None, timeout: int = 300) -> tuple[int, dict, dict]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw) if raw else {}
            headers = dict(response.headers.items())
            return response.status, data, headers
    except HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            data = {"error": raw or str(exc)}
        return exc.code, data, dict(exc.headers.items())
    except URLError as exc:
        return 502, {"error": str(exc.reason)}, {}


class OllamaBridgeHandler(BaseHTTPRequestHandler):
    server_version = "WebmasterOSOllamaBridge/0.1"

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._write_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == "/health":
            self._handle_health()
            return
        if self.path == "/api/tags":
            self._proxy_tags()
            return
        self._write_json(404, {"success": False, "error": "not_found"})

    def do_POST(self) -> None:
        if self.path == "/api/chat":
            self._proxy_chat()
            return
        self._write_json(404, {"success": False, "error": "not_found"})

    def _handle_health(self) -> None:
        status, payload, _headers = json_request(f"{UPSTREAM}/api/tags", method="GET")
        models = payload.get("models", []) if isinstance(payload, dict) else []
        model_names = [row.get("name", "") for row in models if isinstance(row, dict) and row.get("name")]
        self._write_json(
            200 if status == 200 else 502,
            {
                "bridge_ok": status == 200,
                "version": APP_VERSION,
                "config_path": str(CONFIG_PATH),
                "log_path": str(LOG_PATH),
                "upstream_url": UPSTREAM,
                "upstream_status": status,
                "upstream_models": model_names,
                "error": None if status == 200 else payload.get("error", "upstream_unavailable"),
            },
        )

    def _proxy_tags(self) -> None:
        status, payload, _headers = json_request(f"{UPSTREAM}/api/tags", method="GET")
        self._write_json(status, payload)

    def _proxy_chat(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            self._write_json(400, {"error": "invalid_json"})
            return
        status, response_payload, _headers = json_request(f"{UPSTREAM}/api/chat", method="POST", payload=payload)
        self._write_json(status, response_payload)

    def _read_json_body(self) -> dict | None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def _write_json(self, status: int, payload: dict) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self._write_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _write_cors_headers(self) -> None:
        origin = self.headers.get("Origin", "")
        if not ALLOWED_ORIGINS:
            allow_origin = origin if origin else "*"
        else:
            allow_origin = origin if origin in ALLOWED_ORIGINS else "null"
        self.send_header("Access-Control-Allow-Origin", allow_origin)
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def log_message(self, fmt: str, *args) -> None:
        LOGGER.info("[Ollama Bridge] %s - %s", self.address_string(), fmt % args)


def wait_on_windows_failure(message: str) -> None:
    if platform.system().lower() != "windows":
        return
    if not sys.stdin or not sys.stdin.isatty():
        return
    try:
        input(f"{message}\nPress Enter to close WebmasterOS Ollama Bridge...")
    except EOFError:
        return


def main() -> int:
    LOGGER.info("Starting WebmasterOS Ollama Bridge v%s", APP_VERSION)
    LOGGER.info("Config path: %s", CONFIG_PATH)
    LOGGER.info("Log path: %s", LOG_PATH)
    LOGGER.info("Requested bind: http://%s:%s", BIND_HOST, BIND_PORT)
    LOGGER.info("Upstream Ollama URL: %s", UPSTREAM)

    try:
        server = ThreadingHTTPServer((BIND_HOST, BIND_PORT), OllamaBridgeHandler)
    except OSError as exc:
        LOGGER.exception("Bridge startup failed while binding to %s:%s", BIND_HOST, BIND_PORT)
        wait_on_windows_failure(
            f"Bridge startup failed: {exc}\nLog file: {LOG_PATH}"
        )
        return 1

    LOGGER.info(
        "WebmasterOS Ollama Bridge listening on http://%s:%s -> upstream %s",
        BIND_HOST,
        BIND_PORT,
        UPSTREAM,
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info("Bridge interrupted by user")
    except Exception:
        LOGGER.exception("Bridge runtime crashed unexpectedly")
        wait_on_windows_failure(
            f"Bridge runtime crashed unexpectedly.\nLog file: {LOG_PATH}"
        )
        return 1
    finally:
        try:
            server.server_close()
        except Exception:
            LOGGER.exception("Bridge shutdown raised an unexpected error")

    LOGGER.info("Bridge stopped cleanly")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        LOGGER.error("Fatal bridge bootstrap error\n%s", traceback.format_exc())
        wait_on_windows_failure(
            f"Fatal bridge bootstrap error.\nLog file: {LOG_PATH}"
        )
        raise
