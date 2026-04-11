# Changelog

All notable changes to `WebmasterOS Ollama Bridge` should be documented in this file.

The format is intentionally simple while the project is still in monorepo incubation.

## [0.1.6] - 2026-04-11

### Changed

- Existing bridge config files are now auto-migrated on startup so missing no-think keys are written back to disk
- Upgrade migration preserves existing user values while making runtime no-think defaults explicit in the config file

## [0.1.5] - 2026-04-11

### Fixed

- Windows installer now attempts to stop a running `WebmasterOSOllamaBridge.exe` during upgrade instead of leaving users blocked at the "Closing applications" step
- Windows installer now enables Inno Setup close-app detection for bridge upgrades

## [0.1.4] - 2026-04-11

### Added

- Bridge-level no-think proxy mode with `nothink` and `passthrough` runtime modes
- Injection of `think: false`, `reasoning_effort: "none"`, and `reasoning.effort: "none"` for chat requests in `nothink` mode
- Optional `/no_think` system-message injection at the bridge layer
- Response scrubbing for accidental `<think>...</think>` blocks
- New control endpoints:
  - `GET /proxy/status`
  - `POST /proxy/mode`

### Changed

- `/health` now reports bridge proxy-mode details in addition to upstream Ollama health

## [0.1.3] - 2026-04-11

### Fixed

- Windows startup no longer crashes during config-time upstream auto-detection because `json_request()` is now defined before config loading runs

## [0.1.2] - 2026-04-11

### Changed

- Bridge runtime now writes a persistent local log file by default
- Windows startup failures now stay visible in the console and report the log path instead of disappearing immediately
- Windows packaging now launches through `run-ollama-bridge.cmd`, writes `launcher.log`, and records the bridge exit code for early-startup diagnosis

## [0.1.1] - 2026-04-11

### Changed

- Bridge runtime now writes a persistent local log file by default
- Windows startup failures now stay visible in the console and report the log path instead of disappearing immediately

## [0.1.0] - 2026-04-09

### Added

- Initial localhost helper in `bridge.py`
- `/health`, `/api/tags`, and `/api/chat` bridge endpoints
- Cross-platform first-run config conventions for Windows, macOS, and Linux
- Initial per-OS installer-source scripts
- Browser extension bridge mode support
- Windows-first release scaffolding:
  - PyInstaller build script
  - Inno Setup installer script
  - GitHub Actions Windows release workflow scaffold
