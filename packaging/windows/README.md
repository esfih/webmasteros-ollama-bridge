# Windows Packaging

This directory contains the Windows-first packaging scaffold for `WebmasterOS Ollama Bridge`.

## Packaging Model

The first Windows packaging path is:

1. freeze `bridge.py` into a standalone `WebmasterOSOllamaBridge.exe` with PyInstaller
2. stage the default config and runtime launcher files
3. wrap the staged files into a Windows installer with Inno Setup

## Files

- `build-windows-bridge.ps1`
  - builds the standalone executable and prepares an installer stage directory
- `webmasteros-ollama-bridge.spec`
  - PyInstaller build definition
- `WebmasterOSOllamaBridge.iss`
  - Inno Setup installer definition
- `install-ollama-bridge.ps1`
  - direct script-based installer source used before a packaged `.exe` is produced

## Expected Outputs

- `dist/windows/WebmasterOSOllamaBridge.exe`
- `dist/windows/stage/`
- `dist/windows/installer/WebmasterOSOllamaBridge-Setup.exe`

## Runtime Diagnostics

The Windows build is intended to:

- stay open as a console app while the bridge is running
- write runtime logs to the user-local bridge log file
- write a bootstrap `launcher.log` file before the bridge process starts
- keep the console visible on fatal startup failure so first-time users can read the error and log paths

## Local Build Notes

The packaged Windows `.exe` and installer should be built on Windows.

Typical local flow:

```powershell
pwsh -File .\packaging\windows\build-windows-bridge.ps1
```

If Inno Setup is installed, the script can also generate the installer.
