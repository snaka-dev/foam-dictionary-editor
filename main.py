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
    DEFAULT_UI_SCALE,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
    MAX_UI_SCALE,
    MIN_UI_SCALE,
)
from i18n import set_language
from ui.main_window import MainWindow
from ui.session_restore import restore_session
from ui.theme import apply_theme

_PRESETS_DIR = Path(__file__).parent / "presets"
_VALID_VARIANTS = ["standard", "no-terminal", "no-terminal-blockmesh"]
_VALID_THEMES = ["system", "light", "dark"]


def _apply_variant(variant: str) -> None:
    preset_path = _PRESETS_DIR / f"{variant}.json"
    if not preset_path.exists():
        print(f"Error: unknown variant '{variant}'. Valid options: {', '.join(_VALID_VARIANTS)}")
        sys.exit(1)
    features = json.loads(preset_path.read_text(encoding="utf-8")).get("features", {})
    get_app_config().set_features(features)


def _apply_ui_scale(percent: int, forced: bool) -> None:
    """Put the interface scale into the environment, before Qt reads it.

    Qt settles its scale factor when the QApplication is constructed and offers
    no way to change it afterwards, so this is an environment variable set from
    inside the process — the same trick QTWEBENGINE_CHROMIUM_FLAGS uses above.

    A scale that came from the config file yields to a QT_SCALE_FACTOR already
    in the environment: a desktop or a wrapper script that sets one knows more
    about the display in front of the user than a setting they last touched on
    another machine. One passed on the command line overrides it instead, since
    overriding is the whole point of passing it.
    """
    if percent == DEFAULT_UI_SCALE:
        return
    value = f"{percent / 100:g}"
    if forced:
        os.environ["QT_SCALE_FACTOR"] = value
    else:
        os.environ.setdefault("QT_SCALE_FACTOR", value)


def main():
    parser = argparse.ArgumentParser(description="foam dictionary editor")
    parser.add_argument(
        "--variant",
        choices=_VALID_VARIANTS,
        metavar="VARIANT",
        help=f"launch in a specific feature variant: {', '.join(_VALID_VARIANTS)}",
    )
    parser.add_argument(
        "--theme",
        choices=_VALID_THEMES,
        metavar="THEME",
        help=f"use this appearance theme for this run only ({', '.join(_VALID_THEMES)}); "
        "overrides the saved setting without changing it",
    )
    parser.add_argument(
        "--ui-scale",
        type=int,
        metavar="PERCENT",
        help=f"scale the whole interface by this percentage ({MIN_UI_SCALE}-{MAX_UI_SCALE}) "
        "for this run only; overrides the saved setting and QT_SCALE_FACTOR "
        "without changing either",
    )
    parser.add_argument(
        "--no-restore",
        action="store_true",
        help="start with a default layout instead of the last session's, for this run only; "
        "the stored session is kept and the next normal launch uses it again",
    )
    args, qt_args = parser.parse_known_args()

    if args.ui_scale is not None and not MIN_UI_SCALE <= args.ui_scale <= MAX_UI_SCALE:
        print(f"Error: --ui-scale must be between {MIN_UI_SCALE} and {MAX_UI_SCALE}")
        sys.exit(1)

    # Before the QApplication, which is the point at which Qt reads it.
    _apply_ui_scale(
        args.ui_scale if args.ui_scale is not None else get_app_config().get_ui_scale(),
        forced=args.ui_scale is not None,
    )

    app = QApplication([sys.argv[0]] + qt_args)

    if args.variant:
        _apply_variant(args.variant)

    # Before MainWindow, so every widget is built against the final palette.
    # --theme overrides the stored value for this process only: nothing writes
    # it back, so launching a second window in the other theme (to compare the
    # two, or to capture a matched screenshot pair) leaves the setting alone.
    apply_theme(app, args.theme or get_app_config().get_theme())

    set_language(get_app_config().get_language())

    width, height = get_app_config().get_window_size_or_default(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)

    window = MainWindow()
    window.resize(width, height)
    window.show()

    # After show(), because restoring geometry and splitter sizes needs a window
    # that has been laid out, and before the VTK block below, whose xterm check
    # must see the terminal mode the restore chose rather than the default.
    if not args.no_restore:
        restore_session(app, window)

    # Eagerly initialise VTK so it claims the OpenGL context before WebEngine's
    # GPU process can grab it.  Skip when xterm is the default (VTK stays idle
    # until the user switches to Simple mode).
    if window.block_mesh_panel is not None:
        no_xterm = window.terminal_panel is None or not window.terminal_panel.use_xterm
        if no_xterm:
            QTimer.singleShot(0, window.block_mesh_panel.init_plotter)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
