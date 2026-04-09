param(
  [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path,
  [string]$PythonCmd = "python",
  [switch]$InstallBuildDeps,
  [switch]$BuildInstaller
)

$ErrorActionPreference = "Stop"

$DistRoot = Join-Path $ProjectRoot "dist\windows"
$BuildRoot = Join-Path $ProjectRoot "build\windows"
$StageRoot = Join-Path $DistRoot "stage"
$InstallerRoot = Join-Path $DistRoot "installer"
$SpecPath = Join-Path $PSScriptRoot "webmasteros-ollama-bridge.spec"
$ExeName = "WebmasterOSOllamaBridge.exe"
$StageAppRoot = Join-Path $StageRoot "WebmasterOSOllamaBridge"

function Require-Command {
  param([string]$Name)
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Required command not found: $Name"
  }
}

Require-Command $PythonCmd

if ($InstallBuildDeps) {
  & $PythonCmd -m pip install --upgrade pip
  & $PythonCmd -m pip install pyinstaller
}

New-Item -ItemType Directory -Force -Path $DistRoot, $BuildRoot | Out-Null
Remove-Item -Recurse -Force $StageRoot, $InstallerRoot -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $StageAppRoot, $InstallerRoot | Out-Null

Push-Location $ProjectRoot
try {
  & $PythonCmd -m PyInstaller --clean --noconfirm --distpath $DistRoot --workpath $BuildRoot $SpecPath
  if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
  }
} finally {
  Pop-Location
}

$BuiltExe = Join-Path $DistRoot $ExeName
if (-not (Test-Path $BuiltExe)) {
  throw "Expected executable not found at $BuiltExe"
}

Copy-Item $BuiltExe (Join-Path $StageAppRoot $ExeName) -Force
Copy-Item (Join-Path $ProjectRoot "README.md") (Join-Path $StageAppRoot "README.md") -Force
Copy-Item (Join-Path $ProjectRoot "CHANGELOG.md") (Join-Path $StageAppRoot "CHANGELOG.md") -Force
Copy-Item (Join-Path $ProjectRoot "LICENSE-NOTICE.md") (Join-Path $StageAppRoot "LICENSE-NOTICE.md") -Force

New-Item -ItemType Directory -Force -Path (Join-Path $StageAppRoot "config") | Out-Null
Copy-Item (Join-Path $ProjectRoot "config\default-config.json") (Join-Path $StageAppRoot "config\default-config.json") -Force
Copy-Item (Join-Path $PSScriptRoot "install-ollama-bridge.ps1") (Join-Path $StageRoot "install-ollama-bridge.ps1") -Force

$Launcher = @"
@echo off
start "" "%LOCALAPPDATA%\WebmasterOS\OllamaBridge\$ExeName"
"@
Set-Content -Path (Join-Path $StageAppRoot "run-ollama-bridge.cmd") -Value $Launcher -Encoding ASCII

if ($BuildInstaller) {
  $Iscc = Get-Command "iscc" -ErrorAction SilentlyContinue
  if (-not $Iscc) {
    $Iscc = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
  }
  if (-not $Iscc) {
    $FallbackIscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    if (Test-Path $FallbackIscc) {
      $Iscc = @{ Source = $FallbackIscc }
    }
  }
  if (-not $Iscc) {
    throw "Inno Setup compiler 'iscc' was not found. Install Inno Setup or omit -BuildInstaller."
  }
  & $Iscc.Source (Join-Path $PSScriptRoot "WebmasterOSOllamaBridge.iss") "/DProjectRoot=$ProjectRoot" "/DStageRoot=$StageRoot" "/DInstallerRoot=$InstallerRoot"
  if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup build failed."
  }
}

Write-Host "Built Windows bridge executable: $BuiltExe"
Write-Host "Stage directory: $StageRoot"
if ($BuildInstaller) {
  Write-Host "Installer directory: $InstallerRoot"
}
