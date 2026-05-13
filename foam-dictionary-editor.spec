# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import PySide6
from PyInstaller.utils.hooks import collect_all

block_cipher = None

app_name = "foam-dictionary-editor"
project_root = Path(".").resolve()

datas, binaries, hiddenimports = collect_all("PySide6", include_py_files=False)

for name in ("README.md", "README_ja.md"):
    p = project_root / name
    if p.exists():
        datas.append((str(p), "."))

pyside_dir = Path(PySide6.__file__).resolve().parent
plugin_dir = pyside_dir / "plugins"
translations_dir = pyside_dir / "translations"

if plugin_dir.exists():
    datas.append((str(plugin_dir), "PySide6/plugins"))

if translations_dir.exists():
    datas.append((str(translations_dir), "PySide6/translations"))

a = Analysis(
    ["main.py"],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + [
        "schemas.control_dict",
        "schemas.fv_schemes",
        "schemas.fv_solution",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PyQt5", "PyQt6", "PySide2"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=app_name,
    contents_directory=".",
)
