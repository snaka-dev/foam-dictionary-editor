# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
import sys

from PySide6.QtWidgets import QApplication

from app_config import get_app_config
from app_config.defaults import (
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
)
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)

    width, height = get_app_config().get_window_size_or_default(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)

    window = MainWindow()
    window.resize(width, height)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
