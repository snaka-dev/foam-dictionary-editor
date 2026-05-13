# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for foam-dictionary-editor.
#
# Build (onefile):
#   pyinstaller foam_dict_editor.spec
#
# NOTE for Linux/macOS: --onefile is unreliable when QWebEngineWidgets is
# present because Qt spawns QtWebEngineProcess as a separate subprocess and
# cannot find it inside the single-file temp directory.
# Use ONEFILE = False (onedir mode) on Linux/macOS if the xterm terminal
# is needed.  On Windows, WebEngine is not imported, so ONEFILE = True works.

import sys
from pathlib import Path

ONEFILE = sys.platform == "win32"   # change to False on Linux/macOS

block_cipher = None

# ── Data files ────────────────────────────────────────────────────────────────
datas = [
    # HTML template for the xterm.js terminal
    ("ui/xterm_terminal.html", "ui"),
]

# Bundle the pre-downloaded xterm.js cache if it exists.
# Run the download script (step 2 in the README) before building.
xterm_dir = Path("ui/xterm")
if xterm_dir.exists():
    datas.append(("ui/xterm", "ui/xterm"))

# ── Hidden imports ────────────────────────────────────────────────────────────
# schemas/registry.py loads these via importlib.import_module() at runtime.
hiddenimports = [
    "schemas.control_dict",
    "schemas.fv_schemes",
    "schemas.fv_solution",
    "schemas.block_mesh_dict",
    "schemas.snappy_hex_mesh_dict",
]

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tests", "pytest", "pytest_qt", "_pytest"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── Executable ────────────────────────────────────────────────────────────────
if ONEFILE:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name="foam-dictionary-editor",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
else:
    # onedir mode — recommended on Linux/macOS with QWebEngineWidgets
    exe = EXE(
        pyz,
        a.scripts,
        [],
        name="foam-dictionary-editor",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="foam-dictionary-editor",
    )
