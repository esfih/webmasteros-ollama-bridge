# Changelog

All notable changes to `WebmasterOS Ollama Bridge` should be documented in this file.

The format is intentionally simple while the project is still in monorepo incubation.

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
