# Ollama Bridge Installer Plan

## Goal

Ship `WebmasterOS Ollama Bridge` as a one-click companion install for:

- Windows 10/11
- macOS
- Linux desktop

## First Version

The first packaged version uses:

- Python bridge runtime as the reference implementation
- per-OS installer scripts
- staged release bundles created by `scripts/build-ollama-bridge.sh`

## OS Packaging Direction

### Windows

- installer source: `packaging/windows/install-ollama-bridge.ps1`
- frozen build script: `packaging/windows/build-windows-bridge.ps1`
- PyInstaller spec: `packaging/windows/webmasteros-ollama-bridge.spec`
- Inno Setup script: `packaging/windows/WebmasterOSOllamaBridge.iss`
- first-run target: `%LOCALAPPDATA%\\WebmasterOS\\OllamaBridge`
- first packaged release target: `.exe` via Inno Setup
- future packaging: signed `.exe` installer plus optional tray app

### macOS

- installer source: `packaging/macos/install-ollama-bridge.command`
- first-run target: `~/Applications/WebmasterOS/OllamaBridge`
- future packaging: signed `.pkg` or `.dmg`

### Linux

- installer source: `packaging/linux/install-ollama-bridge.sh`
- first-run target: `~/.local/share/webmasteros/ollama-bridge`
- future packaging: AppImage first, then `.deb`/`.rpm`

## First-Run Convention

- install bridge files into a user-local app folder
- write config only if missing
- default bind: `127.0.0.1:19081`
- default upstream: `127.0.0.1:11434`
- auto-detect reachable upstream where possible

## Future Packaging Steps

1. validate the Windows build on a real Windows runner
2. freeze the Python runtime into standalone binaries for macOS and Linux too
3. add tray or menu-bar status UI
4. register auto-start option
5. sign installers and binaries
