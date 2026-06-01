# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
import argparse
import json
import os
import sys
from pathlib import Path

# On Linux, QtWebEngine's GPU process fails GBM and falls back to Vulkan,
# which corrupts VTK/pyVista's OpenGL context.  Disabling the GPU here
# forces WebEngine to use SwiftShader (CPU software rendering), which is
# sufficient for the text terminal and leaves the GPU free for VTK.
# --log-level=2 suppresses the "GPUInfo not initialized on GpuInfoUpdate"
# warning that Chromium emits as a side-effect of --disable-gpu.
# Must be set before QApplication is created.
os.environ.setdefault(
    "QTWEBENGINE_CHROMIUM_FLAGS",
    "--disable-gpu --disable-vulkan --log-level=2",
)

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app_config import get_app_config
from app_config.defaults import (
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
)
from i18n import set_language
from ui.main_window import MainWindow


_PRESETS_DIR = Path(__file__).parent / "presets"
_VALID_VARIANTS = ["standard", "no-terminal", "no-terminal-blockmesh"]


def _apply_variant(variant: str) -> None:
    preset_path = _PRESETS_DIR / f"{variant}.json"
    if not preset_path.exists():
        print(f"Error: unknown variant '{variant}'. Valid options: {', '.join(_VALID_VARIANTS)}")
        sys.exit(1)
    features = json.loads(preset_path.read_text(encoding="utf-8")).get("features", {})
    cfg = get_app_config()
    cfg._features = features


def main():
    parser = argparse.ArgumentParser(description="foam dictionary editor")
    parser.add_argument(
        "--variant",
        choices=_VALID_VARIANTS,
        metavar="VARIANT",
        help=f"launch in a specific feature variant: {', '.join(_VALID_VARIANTS)}",
    )
    args, qt_args = parser.parse_known_args()

    app = QApplication([sys.argv[0]] + qt_args)

    if args.variant:
        _apply_variant(args.variant)

    set_language(get_app_config().get_language())

    width, height = get_app_config().get_window_size_or_default(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)

    window = MainWindow()
    window.resize(width, height)
    window.show()

    # Eagerly initialise VTK so it claims the OpenGL context before WebEngine's
    # GPU process can grab it.  Skip when xterm is the default (VTK stays idle
    # until the user switches to Simple mode).
    if window.block_mesh_panel is not None:
        no_xterm = window.terminal_panel is None or not window.terminal_panel.use_xterm
        if no_xterm:
            QTimer.singleShot(0, window.block_mesh_panel._init_plotter)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
