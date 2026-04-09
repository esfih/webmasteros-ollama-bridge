# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


ROOT = Path(SPEC).resolve().parent.parent.parent

a = Analysis(
    [str(ROOT / "bridge.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "config" / "default-config.json"), "config"),
        (str(ROOT / "README.md"), "."),
        (str(ROOT / "CHANGELOG.md"), "."),
        (str(ROOT / "LICENSE-NOTICE.md"), "."),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="WebmasterOSOllamaBridge",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
