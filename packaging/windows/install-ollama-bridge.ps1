param(
  [string]$InstallRoot = "$env:LOCALAPPDATA\WebmasterOS\OllamaBridge",
  [string]$PythonCmd = "python",
  [string]$OllamaUrl = "http://127.0.0.1:11434"
)

$ErrorActionPreference = "Stop"

$BridgeRoot = Split-Path -Parent $PSScriptRoot
$ConfigRoot = Join-Path $env:APPDATA "WebmasterOS\OllamaBridge"
$ConfigPath = Join-Path $ConfigRoot "config.json"

New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
New-Item -ItemType Directory -Force -Path $ConfigRoot | Out-Null

Copy-Item (Join-Path $BridgeRoot "bridge.py") (Join-Path $InstallRoot "bridge.py") -Force
Copy-Item (Join-Path $BridgeRoot "config\default-config.json") (Join-Path $InstallRoot "default-config.json") -Force

if (-not (Test-Path $ConfigPath)) {
  $config = @{
    host = "127.0.0.1"
    port = 19081
    ollama_url = $OllamaUrl
    allow_origins = @()
    auto_detect_upstream = $true
  } | ConvertTo-Json -Depth 5
  Set-Content -Path $ConfigPath -Value $config -Encoding UTF8
}

$launcher = @"
@echo off
$PythonCmd "$InstallRoot\bridge.py" --config "$ConfigPath"
"@
Set-Content -Path (Join-Path $InstallRoot "run-ollama-bridge.cmd") -Value $launcher -Encoding ASCII

Write-Host "Installed WebmasterOS Ollama Bridge to $InstallRoot"
Write-Host "Config path: $ConfigPath"
Write-Host "Run with: $InstallRoot\run-ollama-bridge.cmd"
