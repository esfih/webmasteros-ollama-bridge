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
import re
import sys
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_BIND_HOST = "127.0.0.1"
DEFAULT_BIND_PORT = 19081
DEFAULT_UPSTREAM = "http://127.0.0.1:11434"
APP_VERSION = "0.1.7"

LOGGER = logging.getLogger("webmasteros.ollama_bridge")
THINK_BLOCK_RE = re.compile(r"<think\b[^>]*>.*?</think>", re.IGNORECASE | re.DOTALL)


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
        "proxy_mode": "nothink",
        "inject_system_nothink": True,
        "strip_think_blocks": True,
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
    merged["proxy_mode"] = normalize_proxy_mode(merged.get("proxy_mode", "nothink"))
    merged["inject_system_nothink"] = bool(merged.get("inject_system_nothink", True))
    merged["strip_think_blocks"] = bool(merged.get("strip_think_blocks", True))
    migrate_config_file(path, data, merged)
    return merged


def migrate_config_file(path: Path, raw_data: dict, merged: dict) -> None:
    if not isinstance(raw_data, dict):
        raw_data = {}

    persisted = dict(raw_data)
    changed = False

    for key in ["proxy_mode", "inject_system_nothink", "strip_think_blocks"]:
        if key not in persisted or persisted.get(key) != merged.get(key):
            persisted[key] = merged.get(key)
            changed = True

    if not changed:
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(persisted, indent=2) + "\n", encoding="utf-8")


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
    parser.add_argument(
        "--proxy-mode",
        default=None,
        choices=["nothink", "passthrough"],
        help="Proxy mode for upstream chat requests. 'nothink' injects reasoning-disable directives.",
    )
    return parser.parse_args()


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


def normalize_proxy_mode(value: str | None) -> str:
    return "passthrough" if str(value or "").strip().lower() == "passthrough" else "nothink"


def inject_no_think(payload: dict, inject_system_nothink: bool = True) -> dict:
    if not isinstance(payload, dict):
        return payload

    enriched = json.loads(json.dumps(payload))
    enriched["think"] = False
    enriched["reasoning_effort"] = "none"

    reasoning = enriched.get("reasoning")
    if isinstance(reasoning, dict):
        reasoning = dict(reasoning)
    else:
        reasoning = {}
    reasoning["effort"] = "none"
    enriched["reasoning"] = reasoning

    messages = enriched.get("messages")
    if inject_system_nothink and isinstance(messages, list):
        system_message = next(
            (
                message
                for message in messages
                if isinstance(message, dict) and message.get("role") == "system" and isinstance(message.get("content"), str)
            ),
            None,
        )
        if system_message:
            if "/no_think" not in system_message["content"]:
                system_message["content"] = "/no_think\n" + system_message["content"]
        else:
            messages.insert(0, {"role": "system", "content": "/no_think"})

    return enriched


def strip_think_blocks_from_text(value: str) -> str:
    text = str(value or "")
    text = THINK_BLOCK_RE.sub("", text)
    return text.strip()


def sanitize_chat_response(payload: dict, strip_think_blocks: bool) -> dict:
    if not strip_think_blocks or not isinstance(payload, dict):
        return payload

    cleaned = json.loads(json.dumps(payload))

    if isinstance(cleaned.get("message"), dict) and isinstance(cleaned["message"].get("content"), str):
        cleaned["message"]["content"] = strip_think_blocks_from_text(cleaned["message"]["content"])

    if isinstance(cleaned.get("response"), str):
        cleaned["response"] = strip_think_blocks_from_text(cleaned["response"])

    return cleaned


def record_request(path: str, status: int, elapsed_ms: int, extra: dict | None = None) -> None:
    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "path": path,
        "status": int(status),
        "elapsed_ms": int(elapsed_ms),
    }
    if extra:
        entry["extra"] = extra
    REQUEST_LOG.append(entry)
    if len(REQUEST_LOG) > 200:
        del REQUEST_LOG[: len(REQUEST_LOG) - 200]


def build_ui_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>WebmasterOS Ollama Bridge</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
      --bg: #0b1220;
      --panel: #121b2f;
      --panel-2: #0f172a;
      --text: #e2e8f0;
      --muted: #94a3b8;
      --accent: #38bdf8;
      --good: #22c55e;
      --warn: #f59e0b;
      --bad: #ef4444;
      --border: rgba(148, 163, 184, 0.18);
    }}
    body {{
      margin: 0;
      background: radial-gradient(circle at top, #16213b 0%, #0b1220 55%, #0a1020 100%);
      color: var(--text);
    }}
    header {{
      padding: 24px 28px 14px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid var(--border);
    }}
    header h1 {{
      margin: 0;
      font-size: 20px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    header .meta {{
      color: var(--muted);
      font-size: 12px;
    }}
    main {{
      padding: 20px 28px 32px;
      display: grid;
      gap: 16px;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 16px;
      box-shadow: 0 18px 30px rgba(0,0,0,0.18);
    }}
    .card h2 {{
      margin: 0 0 12px;
      font-size: 14px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--accent);
    }}
    .stat {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 0;
      border-bottom: 1px solid rgba(148, 163, 184, 0.08);
      font-size: 13px;
    }}
    .stat:last-child {{ border-bottom: none; }}
    .pill {{
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 600;
    }}
    .pill.good {{ background: rgba(34,197,94,0.2); color: var(--good); }}
    .pill.warn {{ background: rgba(245,158,11,0.2); color: var(--warn); }}
    .pill.bad {{ background: rgba(239,68,68,0.2); color: var(--bad); }}
    .list {{
      font-size: 12px;
      color: var(--muted);
      line-height: 1.6;
      max-height: 180px;
      overflow: auto;
      background: var(--panel-2);
      border-radius: 10px;
      padding: 10px;
      border: 1px solid rgba(148, 163, 184, 0.12);
    }}
    .list code {{
      color: var(--text);
    }}
    .button {{
      background: rgba(56,189,248,0.18);
      border: 1px solid rgba(56,189,248,0.4);
      color: #e0f2fe;
      padding: 6px 10px;
      border-radius: 8px;
      font-size: 12px;
      cursor: pointer;
    }}
    .grid-wide {{
      grid-column: 1 / -1;
    }}
    .requests {{
      font-size: 12px;
      color: var(--muted);
      line-height: 1.5;
    }}
    .requests div {{
      display: grid;
      grid-template-columns: 90px 1fr 70px 80px;
      gap: 8px;
      padding: 6px 0;
      border-bottom: 1px solid rgba(148, 163, 184, 0.08);
    }}
    .requests div:last-child {{ border-bottom: none; }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>WebmasterOS Ollama Bridge</h1>
      <div class="meta">Local helper status console</div>
    </div>
    <button class="button" id="refresh">Refresh</button>
  </header>
  <main>
    <section class="card">
      <h2>Bridge Status</h2>
      <div class="stat"><span>Status</span><span class="pill good" id="bridge-status">Running</span></div>
      <div class="stat"><span>Version</span><span id="bridge-version">-</span></div>
      <div class="stat"><span>Uptime</span><span id="bridge-uptime">-</span></div>
      <div class="stat"><span>Requests</span><span id="bridge-requests">-</span></div>
      <div class="stat"><span>Proxy Mode</span><span id="bridge-mode">-</span></div>
    </section>
    <section class="card">
      <h2>Upstream Ollama</h2>
      <div class="stat"><span>URL</span><span id="upstream-url">-</span></div>
      <div class="stat"><span>Models</span><span id="upstream-models">-</span></div>
      <div class="list" id="model-list">Loading models...</div>
    </section>
    <section class="card">
      <h2>Connection</h2>
      <div class="stat"><span>Bind</span><span id="bridge-bind">-</span></div>
      <div class="stat"><span>Config</span><span id="bridge-config">-</span></div>
      <div class="stat"><span>Log</span><span id="bridge-log">-</span></div>
      <div class="stat"><span>Allow Origins</span><span id="bridge-origins">-</span></div>
    </section>
    <section class="card grid-wide">
      <h2>Recent Requests</h2>
      <div class="requests" id="request-log"></div>
    </section>
  </main>
  <script>
    const refreshButton = document.getElementById('refresh');
    const el = (id) => document.getElementById(id);

    function formatDuration(seconds) {{
      if (seconds < 60) return seconds + 's';
      const mins = Math.floor(seconds / 60);
      const rem = seconds % 60;
      return mins + 'm ' + rem + 's';
    }}

    function renderRequests(rows) {{
      const host = el('request-log');
      host.innerHTML = '';
      if (!rows || !rows.length) {{
        host.textContent = 'No recent requests yet.';
        return;
      }}
      rows.slice().reverse().forEach((row) => {{
        const div = document.createElement('div');
        const status = row.status >= 200 && row.status < 300 ? row.status : row.status;
        div.innerHTML = `
          <span>${row.timestamp || '-'}</span>
          <span>${row.path || '-'}</span>
          <span>${status}</span>
          <span>${row.elapsed_ms || 0}ms</span>
        `;
        host.appendChild(div);
      }});
    }}

    async function fetchData() {{
      const response = await fetch('/ui/data');
      const payload = await response.json();
      if (!payload || !payload.success) return;

      el('bridge-version').textContent = payload.version || '-';
      el('bridge-uptime').textContent = formatDuration(payload.uptime_seconds || 0);
      el('bridge-requests').textContent = payload.request_count || 0;
      el('bridge-mode').textContent = payload.proxy_mode || '-';
      el('bridge-bind').textContent = payload.bind ? `${payload.bind.host}:${payload.bind.port}` : '-';
      el('bridge-config').textContent = payload.config_path || '-';
      el('bridge-log').textContent = payload.log_path || '-';
      el('bridge-origins').textContent = payload.allow_origins && payload.allow_origins.length ? payload.allow_origins.join(', ') : 'Any';
      el('upstream-url').textContent = payload.upstream_url || '-';

      const modelList = el('model-list');
      const tagResp = await fetch('/api/tags');
      const tagPayload = await tagResp.json();
      const models = tagPayload && Array.isArray(tagPayload.models) ? tagPayload.models : [];
      el('upstream-models').textContent = models.length;
      modelList.innerHTML = models.length
        ? models.map((m) => `<div><code>${m.name || '-'}</code></div>`).join('')
        : '<span>No models detected.</span>';

      renderRequests(payload.recent_requests || []);
    }}

    refreshButton.addEventListener('click', () => {{
      fetchData().catch(() => {{}});
    }});

    fetchData().catch(() => {{}});
  </script>
</body>
</html>"""

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
PROXY_MODE = normalize_proxy_mode(ARGS.proxy_mode or CONFIG["proxy_mode"])
INJECT_SYSTEM_NOTHINK = bool(CONFIG["inject_system_nothink"])
STRIP_THINK_BLOCKS = bool(CONFIG["strip_think_blocks"])
REQUEST_COUNT = 0
STARTED_AT = time.time()
REQUEST_LOG: list[dict] = []

setup_logging(LOG_PATH)


class OllamaBridgeHandler(BaseHTTPRequestHandler):
    server_version = "WebmasterOSOllamaBridge/0.1"

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._write_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == "/ui":
            self._handle_ui()
            return
        if self.path == "/ui/data":
            self._handle_ui_data()
            return
        if self.path == "/proxy/status":
            self._handle_proxy_status()
            return
        if self.path == "/health":
            self._handle_health()
            return
        if self.path == "/api/tags":
            self._proxy_tags()
            return
        self._write_json(404, {"success": False, "error": "not_found"})

    def do_POST(self) -> None:
        if self.path == "/proxy/mode":
            self._handle_proxy_mode()
            return
        if self.path == "/api/chat":
            self._proxy_chat()
            return
        self._write_json(404, {"success": False, "error": "not_found"})

    def _handle_ui(self) -> None:
        html = build_ui_html()
        encoded = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _handle_ui_data(self) -> None:
        uptime = max(0, int(time.time() - STARTED_AT))
        self._write_json(
            200,
            {
                "success": True,
                "version": APP_VERSION,
                "uptime_seconds": uptime,
                "request_count": REQUEST_COUNT,
                "proxy_mode": PROXY_MODE,
                "inject_system_nothink": INJECT_SYSTEM_NOTHINK,
                "strip_think_blocks": STRIP_THINK_BLOCKS,
                "bind": {
                    "host": BIND_HOST,
                    "port": BIND_PORT,
                },
                "upstream_url": UPSTREAM,
                "allow_origins": sorted(ALLOWED_ORIGINS),
                "config_path": str(CONFIG_PATH),
                "log_path": str(LOG_PATH),
                "recent_requests": REQUEST_LOG[-40:],
            },
        )

    def _handle_proxy_status(self) -> None:
        self._write_json(
            200,
            {
                "success": True,
                "version": APP_VERSION,
                "proxy_mode": PROXY_MODE,
                "inject_system_nothink": INJECT_SYSTEM_NOTHINK,
                "strip_think_blocks": STRIP_THINK_BLOCKS,
                "request_count": REQUEST_COUNT,
                "upstream_url": UPSTREAM,
                "log_path": str(LOG_PATH),
            },
        )

    def _handle_proxy_mode(self) -> None:
        global PROXY_MODE
        payload = self._read_json_body()
        if payload is None:
            self._write_json(400, {"success": False, "error": "invalid_json"})
            return
        next_mode = normalize_proxy_mode(payload.get("mode"))
        PROXY_MODE = next_mode
        LOGGER.info("Proxy mode updated to %s", PROXY_MODE)
        self._write_json(
            200,
            {
                "success": True,
                "proxy_mode": PROXY_MODE,
                "inject_system_nothink": INJECT_SYSTEM_NOTHINK,
                "strip_think_blocks": STRIP_THINK_BLOCKS,
            },
        )

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
                "proxy_mode": PROXY_MODE,
                "inject_system_nothink": INJECT_SYSTEM_NOTHINK,
                "strip_think_blocks": STRIP_THINK_BLOCKS,
                "error": None if status == 200 else payload.get("error", "upstream_unavailable"),
            },
        )

    def _proxy_tags(self) -> None:
        started_at = time.time()
        status, payload, _headers = json_request(f"{UPSTREAM}/api/tags", method="GET")
        elapsed_ms = int((time.time() - started_at) * 1000)
        record_request("GET /api/tags", status, elapsed_ms, {"model_count": len(payload.get("models", [])) if isinstance(payload, dict) else 0})
        self._write_json(status, payload)

    def _proxy_chat(self) -> None:
        global REQUEST_COUNT
        payload = self._read_json_body()
        if payload is None:
            self._write_json(400, {"error": "invalid_json"})
            return
        outgoing_payload = payload
        if PROXY_MODE == "nothink":
            outgoing_payload = inject_no_think(outgoing_payload, INJECT_SYSTEM_NOTHINK)
        started_at = time.time()
        status, response_payload, _headers = json_request(f"{UPSTREAM}/api/chat", method="POST", payload=outgoing_payload)
        elapsed_ms = int((time.time() - started_at) * 1000)
        response_payload = sanitize_chat_response(response_payload, STRIP_THINK_BLOCKS)
        REQUEST_COUNT += 1
        record_request(
            "POST /api/chat",
            status,
            elapsed_ms,
            {
                "model": outgoing_payload.get("model", "") if isinstance(outgoing_payload, dict) else "",
                "mode": PROXY_MODE,
            },
        )
        LOGGER.info(
            "RESP /api/chat %s %sms mode:%s model:%s",
            status,
            elapsed_ms,
            PROXY_MODE,
            outgoing_payload.get("model", "") if isinstance(outgoing_payload, dict) else "",
        )
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
