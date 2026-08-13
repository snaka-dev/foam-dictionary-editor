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
from i18n import tr
from ui.widgets._checkable_list import checked_items, set_all_check_states

_DIALOG_WIDTH = 580
_DIALOG_HEIGHT = 420


class CaseLibraryDialog(QDialog):
    """Manage user-added Case Library directories.

    $FOAM_TUTORIALS is shown read-only in a separate section;
    it is always available when the environment variable is set.
    """

    def __init__(self, user_dirs: list[str], parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(tr("Manage Case Library"))
        self.resize(_DIALOG_WIDTH, _DIALOG_HEIGHT)

        self._dirs = list(user_dirs)
        foam = AppConfigManager.foam_tutorials_dir()

        layout = QVBoxLayout(self)

        # ── auto-detected section ─────────────────────────────────────────────
        auto_box = QGroupBox(tr("Auto-detected (read-only)"))
        auto_layout = QVBoxLayout(auto_box)
        if foam:
            # "[$FOAM_TUTORIALS]" names the environment variable, not prose.
            auto_label = QLabel(f"{foam}   <i>[$FOAM_TUTORIALS]</i>")  # i18n: skip
            auto_label.setTextFormat(Qt.TextFormat.RichText)
        else:
            auto_label = QLabel(f"<i>{tr('$FOAM_TUTORIALS is not set or does not exist.')}</i>")
            auto_label.setTextFormat(Qt.TextFormat.RichText)
            auto_label.setEnabled(False)
        auto_layout.addWidget(auto_label)
        layout.addWidget(auto_box)

        # ── user-added section ────────────────────────────────────────────────
        user_box = QGroupBox(tr("User-added directories"))
        user_layout = QVBoxLayout(user_box)

        sel_row = QHBoxLayout()
        select_all_btn = QPushButton(tr("Select All"))
        deselect_all_btn = QPushButton(tr("Deselect All"))
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
        add_btn = QPushButton(tr("Add Directory..."))
        bottom.addWidget(add_btn)
        bottom.addStretch()
        self._remove_btn = QPushButton()
        close_btn = QPushButton(tr("Close"))
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
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self._list.addItem(item)
        self._list.blockSignals(False)

    def _update_remove_btn(self) -> None:
        n = len(checked_items(self._list))
        self._remove_btn.setText(tr("Remove Selected ({n})").format(n=n))
        self._remove_btn.setEnabled(n > 0)

    def _select_all(self) -> None:
        set_all_check_states(self._list, Qt.CheckState.Checked)
        self._update_remove_btn()

    def _deselect_all(self) -> None:
        set_all_check_states(self._list, Qt.CheckState.Unchecked)
        self._update_remove_btn()

    def _add_directory(self) -> None:
        start = self._dirs[-1] if self._dirs else ""
        directory = QFileDialog.getExistingDirectory(self, tr("Add Directory to Case Library"), start)
        if not directory or directory in self._dirs:
            return
        self._dirs.append(directory)
        self._rebuild_list()
        self._update_remove_btn()

    def _remove_checked(self) -> None:
        for item in checked_items(self._list):
            self._dirs.remove(item.text())
        self._rebuild_list()
        self._update_remove_btn()
