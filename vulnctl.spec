# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the vulnctl standalone binary.
# Entry point: src/cli/user.py (HTTP only — no grpcio/temporalio).

a = Analysis(
    ["src/cli/user.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=[
        "src.adapters.http_cve_store",
        "src.core.use_cases",
        "src.core.ports",
        "httpx",
        "rich",
        "typer",
        "shellingham",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["grpcio", "temporalio", "protobuf", "sqlalchemy", "asyncpg"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="vulnctl",
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
