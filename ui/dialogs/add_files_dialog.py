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

from i18n import tr
from services.case_loader import list_directory_files
from ui.panels.file_list_panel import group_display_name
from ui.widgets._checkable_list import checked_items, set_all_check_states

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
        shown = group_display_name(group)
        self.setWindowTitle(tr("Add files from '{group}'").format(group=shown))
        self.resize(_DIALOG_WIDTH, _DIALOG_HEIGHT)

        all_files = list_directory_files(case_dir, group)
        unloaded = [f for f in all_files if f not in loaded_paths]

        layout = QVBoxLayout(self)

        if unloaded:
            layout.addWidget(QLabel(tr("Select files to add from '{group}':").format(group=shown)))

            sel_row = QHBoxLayout()
            select_all_btn = QPushButton(tr("Select All"))
            deselect_all_btn = QPushButton(tr("Deselect All"))
            sel_row.addWidget(select_all_btn)
            sel_row.addWidget(deselect_all_btn)
            sel_row.addStretch()
            layout.addLayout(sel_row)

            self._list = QListWidget()
            for path in unloaded:
                item = QListWidgetItem(Path(path).name)
                item.setData(Qt.ItemDataRole.UserRole, path)
                item.setToolTip(path)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                self._list.addItem(item)
            layout.addWidget(self._list)

            bottom = QHBoxLayout()
            bottom.addStretch()
            self._add_btn = QPushButton()
            cancel_btn = QPushButton(tr("Cancel"))
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
            layout.addWidget(
                QLabel(tr("All files in '{group}' are already in the file list.").format(group=shown))
            )
            bottom = QHBoxLayout()
            bottom.addStretch()
            close_btn = QPushButton(tr("Close"))
            close_btn.clicked.connect(self.reject)
            bottom.addWidget(close_btn)
            layout.addLayout(bottom)

    def _update_add_btn(self) -> None:
        n = len(checked_items(self._list))
        self._add_btn.setText(tr("Add Selected ({n})").format(n=n))
        self._add_btn.setEnabled(n > 0)

    def _select_all(self) -> None:
        set_all_check_states(self._list, Qt.CheckState.Checked)
        self._update_add_btn()

    def _deselect_all(self) -> None:
        set_all_check_states(self._list, Qt.CheckState.Unchecked)
        self._update_add_btn()

    @property
    def selected_paths(self) -> list[str]:
        return [item.data(Qt.ItemDataRole.UserRole) for item in checked_items(self._list)]
