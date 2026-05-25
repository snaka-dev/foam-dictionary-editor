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

_DIALOG_WIDTH = 520
_DIALOG_HEIGHT = 360


def find_rename_targets(name: str, roots: dict[str, FoamNode]) -> dict[str, list[FoamNode]]:
    """Return {path: [nodes]} for boundary nodes whose name matches across all roots."""
    result: dict[str, list[FoamNode]] = {}
    for path, root in roots.items():
        hits = _collect(root, name)
        if hits:
            result[path] = hits
    return result


def _collect(node: FoamNode, name: str) -> list[FoamNode]:
    hits = []
    if node.name == name and _is_boundary_node(node):
        hits.append(node)
    for child in node.children:
        hits.extend(_collect(child, name))
    return hits


def _is_boundary_node(node: FoamNode) -> bool:
    if node.node_type == "boundary_entry":
        return True
    # Patch key inside a boundaryField dictionary (field files like 0/U)
    if node.node_type == "dictionary" and node.parent is not None:
        return node.parent.name == "boundaryField"
    return False


class RenameBoundaryDialog(QDialog):
    def __init__(
        self,
        old_name: str,
        targets: dict[str, list[FoamNode]],
        case_dir: str,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Rename Boundary")
        self.resize(_DIALOG_WIDTH, _DIALOG_HEIGHT)

        self._old_name = old_name
        self._new_name: str = ""
        self._selected_paths: list[str] = []

        layout = QVBoxLayout(self)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel(f'Rename "{old_name}" to:'))
        self._name_edit = QLineEdit(old_name)
        self._name_edit.selectAll()
        name_row.addWidget(self._name_edit)
        layout.addLayout(name_row)

        if not targets:
            layout.addWidget(QLabel("No matching boundary entries found in loaded files."))
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(self.reject)
            bottom = QHBoxLayout()
            bottom.addStretch()
            bottom.addWidget(close_btn)
            layout.addLayout(bottom)
            return

        hdr = QHBoxLayout()
        hdr.addWidget(QLabel("Apply to:"))
        hdr.addStretch()
        sel_all_btn = QPushButton("Select All")
        desel_all_btn = QPushButton("Deselect All")
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
            item.setData(Qt.UserRole, path)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self._list.addItem(item)
        layout.addWidget(self._list)

        bottom = QHBoxLayout()
        bottom.addStretch()
        self._rename_btn = QPushButton()
        cancel_btn = QPushButton("Cancel")
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

    def _checked_items(self) -> list[QListWidgetItem]:
        return [
            self._list.item(i)
            for i in range(self._list.count())
            if self._list.item(i).checkState() == Qt.Checked
        ]

    def _update_rename_btn(self) -> None:
        new = self._name_edit.text().strip()
        n = len(self._checked_items())
        valid = bool(new) and new != self._old_name and n > 0
        self._rename_btn.setText(f"Rename ({n} file{'s' if n != 1 else ''})")
        self._rename_btn.setEnabled(valid)

    def _select_all(self) -> None:
        self._list.blockSignals(True)
        for i in range(self._list.count()):
            self._list.item(i).setCheckState(Qt.Checked)
        self._list.blockSignals(False)
        self._update_rename_btn()

    def _deselect_all(self) -> None:
        self._list.blockSignals(True)
        for i in range(self._list.count()):
            self._list.item(i).setCheckState(Qt.Unchecked)
        self._list.blockSignals(False)
        self._update_rename_btn()

    def _on_rename(self) -> None:
        self._new_name = self._name_edit.text().strip()
        self._selected_paths = [item.data(Qt.UserRole) for item in self._checked_items()]
        self.accept()
