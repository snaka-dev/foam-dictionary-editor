# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from services.case_loader import list_directory_files

_DIALOG_WIDTH = 400
_DIALOG_HEIGHT = 300


class AddFilesDialog(QDialog):
    """Shows files in a case subdirectory that are not yet loaded, for the user to select."""

    def __init__(
        self,
        case_dir: str,
        group: str,
        loaded_paths: set[str],
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(f"Add files from '{group}'")
        self.resize(_DIALOG_WIDTH, _DIALOG_HEIGHT)

        all_files = list_directory_files(case_dir, group)
        unloaded = [f for f in all_files if f not in loaded_paths]

        layout = QVBoxLayout(self)

        if unloaded:
            layout.addWidget(QLabel(f"Select files to add from '{group}':"))

            sel_row = QHBoxLayout()
            select_all_btn = QPushButton("Select All")
            deselect_all_btn = QPushButton("Deselect All")
            sel_row.addWidget(select_all_btn)
            sel_row.addWidget(deselect_all_btn)
            sel_row.addStretch()
            layout.addLayout(sel_row)

            self._list = QListWidget()
            for path in unloaded:
                item = QListWidgetItem(Path(path).name)
                item.setData(Qt.UserRole, path)
                item.setToolTip(path)
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
                self._list.addItem(item)
            layout.addWidget(self._list)

            bottom = QHBoxLayout()
            bottom.addStretch()
            self._add_btn = QPushButton()
            cancel_btn = QPushButton("Cancel")
            bottom.addWidget(self._add_btn)
            bottom.addWidget(cancel_btn)
            layout.addLayout(bottom)

            self._update_add_btn()

            self._list.itemChanged.connect(self._update_add_btn)
            select_all_btn.clicked.connect(self._select_all)
            deselect_all_btn.clicked.connect(self._deselect_all)
            self._add_btn.clicked.connect(self.accept)
            cancel_btn.clicked.connect(self.reject)
        else:
            layout.addWidget(QLabel(f"All files in '{group}' are already in the file list."))
            bottom = QHBoxLayout()
            bottom.addStretch()
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(self.reject)
            bottom.addWidget(close_btn)
            layout.addLayout(bottom)

    def _checked_items(self) -> list[QListWidgetItem]:
        return [
            self._list.item(i)
            for i in range(self._list.count())
            if self._list.item(i).checkState() == Qt.Checked
        ]

    def _update_add_btn(self) -> None:
        n = len(self._checked_items())
        self._add_btn.setText(f"Add Selected ({n})")
        self._add_btn.setEnabled(n > 0)

    def _select_all(self) -> None:
        self._list.blockSignals(True)
        for i in range(self._list.count()):
            self._list.item(i).setCheckState(Qt.Checked)
        self._list.blockSignals(False)
        self._update_add_btn()

    def _deselect_all(self) -> None:
        self._list.blockSignals(True)
        for i in range(self._list.count()):
            self._list.item(i).setCheckState(Qt.Unchecked)
        self._list.blockSignals(False)
        self._update_add_btn()

    @property
    def selected_paths(self) -> list[str]:
        return [item.data(Qt.UserRole) for item in self._checked_items()]
