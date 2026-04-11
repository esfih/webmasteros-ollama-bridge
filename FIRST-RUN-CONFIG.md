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
  "log_file": ""
}
```

## First-Run Rules

- if no config exists, write a default config file
- if `auto_detect_upstream` is enabled, probe likely Ollama addresses and persist the best reachable upstream in memory
- keep the first version local-only and user-scoped
- never bind publicly by default
- if no explicit log path is configured, write logs into a user-local `logs/bridge.log` file beside the config

## WSL Note

When the bridge runs inside WSL but Ollama runs on Windows, the upstream may need to be a Windows host IP such as `172.17.80.1` instead of `127.0.0.1`.
