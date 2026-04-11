# Releases

## Release Direction

`WebmasterOS Ollama Bridge` is intended to publish its own releases independently from:

- the WordPress plugin
- the browser extension
- control-panel integrations

## Planned Artifacts

### Windows

- installer source: `install-ollama-bridge.ps1`
- Windows build scaffold: `build-windows-bridge.ps1`
- Inno Setup installer source: `WebmasterOSOllamaBridge.iss`
- first packaged release target: `.exe`
- future packaged release: signed `.exe`

### macOS

- installer source: `install-ollama-bridge.command`
- future packaged release: signed `.pkg` or `.dmg`

### Linux

- installer source: `install-ollama-bridge.sh`
- future packaged release: AppImage, with optional `.deb` and `.rpm`

## Versioning

Current tracked version:

- `0.1.2`

## Monorepo Stage

Until the standalone public repository is created, release scaffolding is generated from this repo through:

```bash
./scripts/build-ollama-bridge.sh
```

The exported standalone repo also includes:

- `.github/workflows/windows-release.yml`
- `packaging/windows/build-windows-bridge.ps1`
- `packaging/windows/WebmasterOSOllamaBridge.iss`
