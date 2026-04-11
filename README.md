# Ollama Bridge

`Ollama Bridge` is a tiny localhost helper for WebmasterOS.

It is now treated as a fourth software surface in the WebmasterOS stack and is intended to move into its own public GitHub repository with its own releases.

It allows the browser extension to talk to local Ollama through a non-browser process, which avoids browser-origin restrictions on direct extension-to-Ollama chat.

It also now includes an optional no-think compatibility layer for reasoning-heavy local models such as Qwen or DeepSeek variants.

## Why It Exists

Direct browser-extension chat to Ollama may be blocked by origin policy even when Ollama works fine from:

- the WordPress plugin server side
- VS Code
- GitHub Copilot-style native clients
- terminal tools

The bridge changes the path to:

`browser extension -> Ollama Bridge -> local Ollama`

## Requirements

- Python 3
- Ollama already installed and running

## Config

The bridge writes a user-local config file on first run.

Default locations:

- Windows: `%APPDATA%\WebmasterOS\OllamaBridge\config.json`
- macOS: `~/Library/Application Support/WebmasterOS/OllamaBridge/config.json`
- Linux: `~/.config/webmasteros/ollama-bridge/config.json`

The bridge also writes a local log file by default:

- Windows: `%APPDATA%\\WebmasterOS\\OllamaBridge\\logs\\bridge.log`
- macOS: `~/Library/Application Support/WebmasterOS/OllamaBridge/logs/bridge.log`
- Linux: `~/.config/webmasteros/ollama-bridge/logs/bridge.log`

Windows packaging also writes a launcher/bootstrap log:

- Windows: `%APPDATA%\\WebmasterOS\\OllamaBridge\\logs\\launcher.log`

Important no-think defaults:

- `proxy_mode`: `nothink`
- `inject_system_nothink`: `true`
- `strip_think_blocks`: `true`

That means the bridge will, by default:

- inject `think: false`
- inject `reasoning_effort: "none"` and `reasoning.effort: "none"`
- prepend `/no_think` to the system message when possible
- strip accidental `<think>...</think>` blocks from returned text

## Run

Typical desktop setup:

```bash
python3 bridge.py --ollama-url http://127.0.0.1:11434
```

Write a default config and exit:

```bash
python3 bridge.py --write-default-config
```

Print the resolved config path:

```bash
python3 bridge.py --print-config-path
```

WSL talking to Windows-side Ollama:

```bash
python3 bridge.py --ollama-url http://172.17.80.1:11434
```

Custom bind port:

```bash
python3 bridge.py --port 19081 --ollama-url http://127.0.0.1:11434
```

## Endpoints

- `GET /health`
- `GET /api/tags`
- `POST /api/chat`
- `GET /proxy/status`
- `POST /proxy/mode`

## Proxy Modes

The bridge now supports two runtime modes:

- `nothink`: default, injects no-think directives for faster and more deterministic responses
- `passthrough`: forwards requests unchanged

Switch mode without restarting:

```bash
curl -X POST http://127.0.0.1:19081/proxy/mode \
  -H "Content-Type: application/json" \
  -d '{"mode":"passthrough"}'

curl -X POST http://127.0.0.1:19081/proxy/mode \
  -H "Content-Type: application/json" \
  -d '{"mode":"nothink"}'
```

Inspect current mode and request counters:

```bash
curl http://127.0.0.1:19081/proxy/status
```

## Browser Extension Settings

Use:

- `Connection mode`: `Ollama Bridge`
- `Bridge URL`: `http://127.0.0.1:19081`
- `Base URL`: keep as the upstream Ollama address for reference and diagnostics

## Cross-Platform Note

This first bridge is intentionally tiny and Python-based so it can work on Windows, macOS, and Linux with minimal code. Packaging it as a native installer or tray app can come later.

## Startup Diagnostics

If the bridge fails during startup:

- it writes the failure details to the local bridge log file
- on Windows, the launcher writes a `launcher.log` file, records the process exit code, and keeps the console open on non-zero exit

## Installer Sources

First-version installer sources live under:

- `packaging/windows/`
- `packaging/macos/`
- `packaging/linux/`

## Windows Packaging

Windows is the first packaging target for turning the bridge into an end-user installable companion app.

The Windows packaging scaffold now includes:

- a PyInstaller build definition
- a PowerShell build script
- an Inno Setup installer definition
- a GitHub Actions workflow for Windows release artifacts

Windows upgrade behavior:

- the installer now attempts to stop `WebmasterOSOllamaBridge.exe` automatically during upgrade before replacing files
