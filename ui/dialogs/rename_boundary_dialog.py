# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from foam.nodes import FoamNode
from i18n import tr
from ui.widgets._checkable_list import checked_items, set_all_check_states

_DIALOG_WIDTH = 520
_DIALOG_HEIGHT = 360


class RenameBoundaryDialog(QDialog):
    def __init__(
        self,
        old_name: str,
        targets: dict[str, list[FoamNode]],
        case_dir: str,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(tr("Rename Boundary"))
        self.resize(_DIALOG_WIDTH, _DIALOG_HEIGHT)

        self._old_name = old_name
        self._new_name: str = ""
        self._selected_paths: list[str] = []

        layout = QVBoxLayout(self)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel(tr('Rename "{name}" to:').format(name=old_name)))
        self._name_edit = QLineEdit(old_name)
        self._name_edit.selectAll()
        name_row.addWidget(self._name_edit)
        layout.addLayout(name_row)

        if not targets:
            layout.addWidget(QLabel(tr("No matching boundary entries found in loaded files.")))
            close_btn = QPushButton(tr("Close"))
            close_btn.clicked.connect(self.reject)
            bottom = QHBoxLayout()
            bottom.addStretch()
            bottom.addWidget(close_btn)
            layout.addLayout(bottom)
            return

        hdr = QHBoxLayout()
        hdr.addWidget(QLabel(tr("Apply to:")))
        hdr.addStretch()
        sel_all_btn = QPushButton(tr("Select All"))
        desel_all_btn = QPushButton(tr("Deselect All"))
        hdr.addWidget(sel_all_btn)
        hdr.addWidget(desel_all_btn)
        layout.addLayout(hdr)

        base = Path(case_dir)
        self._list = QListWidget()
        for path, nodes in sorted(targets.items(), key=lambda kv: Path(kv[0]).name.lower()):
            try:
                label = str(Path(path).relative_to(base))
            except ValueError:
                label = Path(path).name
            n = len(nodes)
            item = QListWidgetItem(f"{label}    ({n} match{'es' if n != 1 else ''})")
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self._list.addItem(item)
        layout.addWidget(self._list)

        bottom = QHBoxLayout()
        bottom.addStretch()
        self._rename_btn = QPushButton()
        cancel_btn = QPushButton(tr("Cancel"))
        bottom.addWidget(self._rename_btn)
        bottom.addWidget(cancel_btn)
        layout.addLayout(bottom)

        self._update_rename_btn()

        self._name_edit.textChanged.connect(self._update_rename_btn)
        self._list.itemChanged.connect(self._update_rename_btn)
        sel_all_btn.clicked.connect(self._select_all)
        desel_all_btn.clicked.connect(self._deselect_all)
        self._rename_btn.clicked.connect(self._on_rename)
        cancel_btn.clicked.connect(self.reject)

    @property
    def new_name(self) -> str:
        return self._new_name

    @property
    def selected_paths(self) -> list[str]:
        return list(self._selected_paths)

    def _update_rename_btn(self) -> None:
        new = self._name_edit.text().strip()
        n = len(checked_items(self._list))
        valid = bool(new) and new != self._old_name and n > 0
        self._rename_btn.setText(tr("Rename ({n} file{s})").format(n=n, s="s" if n != 1 else ""))
        self._rename_btn.setEnabled(valid)

    def _select_all(self) -> None:
        set_all_check_states(self._list, Qt.CheckState.Checked)
        self._update_rename_btn()

    def _deselect_all(self) -> None:
        set_all_check_states(self._list, Qt.CheckState.Unchecked)
        self._update_rename_btn()

    def _on_rename(self) -> None:
        self._new_name = self._name_edit.text().strip()
        self._selected_paths = [item.data(Qt.ItemDataRole.UserRole) for item in checked_items(self._list)]
        self.accept()
