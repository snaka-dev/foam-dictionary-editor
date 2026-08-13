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

ONEFILE = sys.platform == "win32"   # change to False on Linux/macOS

block_cipher = None

# ── Data files ────────────────────────────────────────────────────────────────
datas = [
    # HTML template for the xterm.js terminal
    ("ui/xterm_terminal.html", "ui"),
    # Hand-authored toolbar/menu icon SVGs (ui/icons.py).
    ("ui/assets/icons", "ui/assets/icons"),
]

# xterm.js itself is deliberately never bundled here. It is MIT-licensed and
# fetched at runtime into a gitignored ui/xterm/ cache (see
# ui/widgets/_xterm_widget.py); whether that cache happened to exist on the
# machine doing the build used to decide whether a release redistributed
# xterm.js — and therefore whether the MIT copyright-notice obligation
# attached to it — which made that obligation depend on build-machine state
# rather than on anything in this spec. Never bundling it means the
# obligation never attaches, and keeps the About dialog's "loaded
# automatically on first launch" description true for every build. An
# offline bundle, if one is ever wanted, is a deliberate separate variant
# that must also ship xterm.js's own LICENSE file alongside it.

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
