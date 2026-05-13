# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app_config.app_config_manager import AppConfigManager

_DIALOG_WIDTH = 580
_DIALOG_HEIGHT = 420


class CaseLibraryDialog(QDialog):
    """Manage user-added Case Library directories.

    $FOAM_TUTORIALS is shown read-only in a separate section;
    it is always available when the environment variable is set.
    """

    def __init__(self, user_dirs: list[str], parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Manage Case Library")
        self.resize(_DIALOG_WIDTH, _DIALOG_HEIGHT)

        self._dirs = list(user_dirs)
        foam = AppConfigManager.foam_tutorials_dir()

        layout = QVBoxLayout(self)

        # ── auto-detected section ─────────────────────────────────────────────
        auto_box = QGroupBox("Auto-detected (read-only)")
        auto_layout = QVBoxLayout(auto_box)
        if foam:
            auto_label = QLabel(f"{foam}   <i>[$FOAM_TUTORIALS]</i>")
            auto_label.setTextFormat(Qt.RichText)
        else:
            auto_label = QLabel("<i>$FOAM_TUTORIALS is not set or does not exist.</i>")
            auto_label.setTextFormat(Qt.RichText)
            auto_label.setEnabled(False)
        auto_layout.addWidget(auto_label)
        layout.addWidget(auto_box)

        # ── user-added section ────────────────────────────────────────────────
        user_box = QGroupBox("User-added directories")
        user_layout = QVBoxLayout(user_box)

        sel_row = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        deselect_all_btn = QPushButton("Deselect All")
        sel_row.addWidget(select_all_btn)
        sel_row.addWidget(deselect_all_btn)
        sel_row.addStretch()
        user_layout.addLayout(sel_row)

        self._list = QListWidget()
        self._rebuild_list()
        user_layout.addWidget(self._list)

        layout.addWidget(user_box)

        # ── bottom buttons ────────────────────────────────────────────────────
        bottom = QHBoxLayout()
        add_btn = QPushButton("Add Directory...")
        bottom.addWidget(add_btn)
        bottom.addStretch()
        self._remove_btn = QPushButton()
        close_btn = QPushButton("Close")
        bottom.addWidget(self._remove_btn)
        bottom.addWidget(close_btn)
        layout.addLayout(bottom)

        self._update_remove_btn()

        self._list.itemChanged.connect(self._update_remove_btn)
        select_all_btn.clicked.connect(self._select_all)
        deselect_all_btn.clicked.connect(self._deselect_all)
        add_btn.clicked.connect(self._add_directory)
        self._remove_btn.clicked.connect(self._remove_checked)
        close_btn.clicked.connect(self.accept)

    @property
    def library_dirs(self) -> list[str]:
        """Return the current user-added directories."""
        return list(self._dirs)

    def _rebuild_list(self) -> None:
        self._list.blockSignals(True)
        self._list.clear()
        for path in self._dirs:
            item = QListWidgetItem(path)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self._list.addItem(item)
        self._list.blockSignals(False)

    def _checked_items(self) -> list[QListWidgetItem]:
        return [
            self._list.item(i)
            for i in range(self._list.count())
            if self._list.item(i).checkState() == Qt.Checked
        ]

    def _update_remove_btn(self) -> None:
        n = len(self._checked_items())
        self._remove_btn.setText(f"Remove Selected ({n})")
        self._remove_btn.setEnabled(n > 0)

    def _select_all(self) -> None:
        self._list.blockSignals(True)
        for i in range(self._list.count()):
            self._list.item(i).setCheckState(Qt.Checked)
        self._list.blockSignals(False)
        self._update_remove_btn()

    def _deselect_all(self) -> None:
        self._list.blockSignals(True)
        for i in range(self._list.count()):
            self._list.item(i).setCheckState(Qt.Unchecked)
        self._list.blockSignals(False)
        self._update_remove_btn()

    def _add_directory(self) -> None:
        start = self._dirs[-1] if self._dirs else ""
        directory = QFileDialog.getExistingDirectory(self, "Add Directory to Case Library", start)
        if not directory or directory in self._dirs:
            return
        self._dirs.append(directory)
        self._rebuild_list()
        self._update_remove_btn()

    def _remove_checked(self) -> None:
        for item in self._checked_items():
            self._dirs.remove(item.text())
        self._rebuild_list()
        self._update_remove_btn()
