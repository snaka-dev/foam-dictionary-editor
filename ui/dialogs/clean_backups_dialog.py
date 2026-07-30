# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import re
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
    QWidget,
)

from i18n import tr
from ui.widgets._checkable_list import checked_items, set_all_check_states

_BAK_RE = re.compile(r"\.bak_\d{8}_\d{6}$")
_DIALOG_WIDTH = 560
_DIALOG_HEIGHT = 400


def find_backup_files(case_dir: str) -> list[tuple[str, str, int]]:
    """Return [(abs_path, rel_path, size_bytes)] for .bak_YYYYMMDD_HHMMSS files."""
    base = Path(case_dir)
    result = []
    for p in sorted(base.rglob("*"), key=lambda x: str(x.relative_to(base)).lower()):
        if p.is_file() and _BAK_RE.search(p.name):
            try:
                size = p.stat().st_size
            except OSError:
                size = 0
            result.append((str(p), str(p.relative_to(base)), size))
    return result


def _fmt_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


class CleanBackupsDialog(QDialog):
    def __init__(
        self,
        backups: list[tuple[str, str, int]],
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(tr("Clean Backup Files"))
        self.resize(_DIALOG_WIDTH, _DIALOG_HEIGHT)

        self._paths_to_delete: list[str] = []

        layout = QVBoxLayout(self)

        if not backups:
            layout.addWidget(QLabel(tr("No backup files found in this case.")))
            close_btn = QPushButton(tr("Close"))
            close_btn.clicked.connect(self.reject)
            bottom = QHBoxLayout()
            bottom.addStretch()
            bottom.addWidget(close_btn)
            layout.addLayout(bottom)
            return

        layout.addWidget(QLabel(tr("{n} backup file(s) found in this case:").format(n=len(backups))))

        sel_row = QHBoxLayout()
        select_all_btn = QPushButton(tr("Select All"))
        deselect_all_btn = QPushButton(tr("Deselect All"))
        sel_row.addWidget(select_all_btn)
        sel_row.addWidget(deselect_all_btn)
        sel_row.addStretch()
        layout.addLayout(sel_row)

        self._list = QListWidget()
        for abs_path, rel_path, size in backups:
            item = QListWidgetItem(f"{rel_path}    ({_fmt_size(size)})")
            item.setData(Qt.ItemDataRole.UserRole, abs_path)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self._list.addItem(item)
        layout.addWidget(self._list)

        bottom = QHBoxLayout()
        bottom.addStretch()
        self._delete_btn = QPushButton()
        cancel_btn = QPushButton(tr("Cancel"))
        bottom.addWidget(self._delete_btn)
        bottom.addWidget(cancel_btn)
        layout.addLayout(bottom)

        self._update_delete_btn()

        self._list.itemChanged.connect(self._update_delete_btn)
        select_all_btn.clicked.connect(self._select_all)
        deselect_all_btn.clicked.connect(self._deselect_all)
        self._delete_btn.clicked.connect(self._on_delete)
        cancel_btn.clicked.connect(self.reject)

    @property
    def paths_to_delete(self) -> list[str]:
        return list(self._paths_to_delete)

    def _update_delete_btn(self) -> None:
        n = len(checked_items(self._list))
        self._delete_btn.setText(tr("Delete Selected ({n})").format(n=n))
        self._delete_btn.setEnabled(n > 0)

    def _select_all(self) -> None:
        set_all_check_states(self._list, Qt.CheckState.Checked)
        self._update_delete_btn()

    def _deselect_all(self) -> None:
        set_all_check_states(self._list, Qt.CheckState.Unchecked)
        self._update_delete_btn()

    def _on_delete(self) -> None:
        self._paths_to_delete = [
            item.data(Qt.ItemDataRole.UserRole) for item in checked_items(self._list)
        ]
        self.accept()
