# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QVBoxLayout,
)

_SECTIONS: list[tuple[str, list[tuple[str, str]]]] = [
    ("Editor", [
        ("Find",               "Ctrl+F"),
        ("Find Next",          "F3"),
        ("Find Previous",      "Shift+F3"),
        ("Find in Tree",       "Ctrl+Shift+T"),
        ("Undo",               "Ctrl+Z"),
        ("Redo",               "Ctrl+Y"),
        ("Cut",                "Ctrl+X"),
        ("Copy",               "Ctrl+C"),
        ("Paste",              "Ctrl+V"),
        ("Select All",         "Ctrl+A"),
    ]),
    ("Tree", [
        ("Copy Value",         "Ctrl+C"),
        ("Paste Value",        "Ctrl+V"),
    ]),
    ("Application", [
        ("Open Case",          "Ctrl+O"),
        ("Save Case",          "Ctrl+Shift+S"),
        ("Exit",               "Ctrl+Q"),
    ]),
    ("BlockMesh 3-D viewer (mouse)", [
        ("Rotate",             "Left drag"),
        ("Pan",                "Shift + left drag"),
        ("Zoom",               "Scroll wheel  or  right drag"),
        ("Reset camera",       "R"),
        ("Fly to point",       "F"),
    ]),
]


class KeyboardShortcutsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keyboard Shortcuts")
        self.setMinimumWidth(340)

        layout = QVBoxLayout(self)

        for section_name, shortcuts in _SECTIONS:
            group = QGroupBox(section_name)
            grid = QGridLayout(group)
            grid.setColumnStretch(0, 1)
            for row, (action, key) in enumerate(shortcuts):
                action_lbl = QLabel(action)
                key_lbl = QLabel(key)
                key_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                key_lbl.setStyleSheet("font-family: monospace; color: #555;")
                grid.addWidget(action_lbl, row, 0)
                grid.addWidget(key_lbl,    row, 1)
            layout.addWidget(group)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
