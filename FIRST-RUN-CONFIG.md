# First-Run Config Conventions

## Config File Paths

### Windows

`%APPDATA%\\WebmasterOS\\OllamaBridge\\config.json`

### macOS

`~/Library/Application Support/WebmasterOS/OllamaBridge/config.json`

### Linux

`~/.config/webmasteros/ollama-bridge/config.json`

## Default Values

```json
{
  "host": "127.0.0.1",
  "port": 19081,
  "ollama_url": "http://127.0.0.1:11434",
  "allow_origins": [],
  "auto_detect_upstream": true,
  "log_file": "",
  "proxy_mode": "nothink",
  "inject_system_nothink": true,
  "strip_think_blocks": true
}
```

## First-Run Rules

- if no config exists, write a default config file
- if an older config exists but is missing newer no-think keys, auto-migrate the file in place and preserve the user's existing values
- if `auto_detect_upstream` is enabled, probe likely Ollama addresses and persist the best reachable upstream in memory
- keep the first version local-only and user-scoped
- never bind publicly by default
- if no explicit log path is configured, write logs into a user-local `logs/bridge.log` file beside the config
- on Windows packaging, also write a bootstrap `logs/launcher.log` file that captures the launcher start and the bridge exit code
- default bridge behavior is `nothink` mode so reasoning-heavy models become faster and less likely to leak `<think>` blocks into app responses
- `inject_system_nothink` keeps `/no_think` in the system message when messages are present
- `strip_think_blocks` removes accidental `<think>...</think>` blocks from Ollama responses before they return to the extension

## WSL Note

When the bridge runs inside WSL but Ollama runs on Windows, the upstream may need to be a Windows host IP such as `172.17.80.1` instead of `127.0.0.1`.
