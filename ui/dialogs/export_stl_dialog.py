# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Export loaded topoSetDict / snappyHexMeshDict / setFieldsDict shapes as STL files."""
from __future__ import annotations

import dataclasses
import re
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from foam.set_fields_extractor import SetFieldsShape
from foam.snappy_hex_mesh_extractor import SnappyShape
from foam.topo_set_extractor import TopoShape
from i18n import tr
from ui.panels.shape_mesh import make_shape_mesh
from ui.widgets._checkable_list import checked_indices, set_all_check_states

_DIALOG_WIDTH = 520
_DIALOG_HEIGHT = 460
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_-]+")


@dataclasses.dataclass
class _Entry:
    group_label: str  # "topoSet" | "snappyHexMesh" | "setFields"
    name: str         # shape label, may be ""
    kind: str         # the shape classes' shared geometry/source keyword
    geometry: dict
    default_checked: bool


def _safe_filename(name: str) -> str:
    cleaned = _SAFE_NAME_RE.sub("_", name).strip("_")
    return cleaned or "shape"


class ExportStlDialog(QDialog):
    """Pick topoSet/snappyHexMesh/setFields shapes and write each as its own STL file."""

    def __init__(
        self,
        topo_shapes: list[TopoShape],
        topo_visible: set[int],
        snappy_shapes: list[SnappyShape],
        snappy_visible: set[int],
        parent: QWidget | None = None,
        *,
        set_fields_shapes: list[SetFieldsShape] | None = None,
        set_fields_visible: set[int] | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(tr("Export Shapes as STL"))
        self.resize(_DIALOG_WIDTH, _DIALOG_HEIGHT)

        set_fields_visible = set_fields_visible or set()
        groups: list[tuple[str, list, set[int]]] = [
            ("topoSet", list(topo_shapes), topo_visible),
            ("snappyHexMesh", list(snappy_shapes), snappy_visible),
            ("setFields", list(set_fields_shapes or []), set_fields_visible),
        ]
        self._entries: list[_Entry] = [
            _Entry(group, shape.label, shape.kind, shape.geometry, id(shape) in visible)
            for group, shapes, visible in groups
            for shape in shapes
        ]

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr("Choose which shapes to save as STL files:")))

        sel_row = QHBoxLayout()
        select_all_btn = QPushButton(tr("Select All"))
        deselect_all_btn = QPushButton(tr("Deselect All"))
        sel_row.addWidget(select_all_btn)
        sel_row.addWidget(deselect_all_btn)
        sel_row.addStretch()
        layout.addLayout(sel_row)

        self._list = QListWidget()
        for entry in self._entries:
            label = entry.name or tr("(unnamed)")
            item = QListWidgetItem(f"[{entry.group_label}] {label}  ·  {entry.kind}")
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if entry.default_checked else Qt.CheckState.Unchecked)
            self._list.addItem(item)
        layout.addWidget(self._list)

        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel(tr("Output folder:")))
        self._folder_edit = QLineEdit()
        self._folder_edit.setReadOnly(True)
        folder_row.addWidget(self._folder_edit, 1)
        browse_btn = QPushButton(tr("Browse…"))
        folder_row.addWidget(browse_btn)
        layout.addLayout(folder_row)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton(tr("Cancel"))
        self._export_btn = QPushButton(tr("Export"))
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(self._export_btn)
        layout.addLayout(btn_row)

        select_all_btn.clicked.connect(self._select_all)
        deselect_all_btn.clicked.connect(self._deselect_all)
        browse_btn.clicked.connect(self._choose_folder)
        cancel_btn.clicked.connect(self.reject)
        self._export_btn.clicked.connect(self._export)
        self._list.itemChanged.connect(self._update_export_btn)

        self._update_export_btn()

    # ── selection helpers ────────────────────────────────────────────────────

    def _select_all(self) -> None:
        set_all_check_states(self._list, Qt.CheckState.Checked)
        self._update_export_btn()

    def _deselect_all(self) -> None:
        set_all_check_states(self._list, Qt.CheckState.Unchecked)
        self._update_export_btn()

    def _choose_folder(self) -> None:
        chosen = QFileDialog.getExistingDirectory(
            self, tr("Select Output Folder"), self._folder_edit.text()
        )
        if chosen:
            self._folder_edit.setText(chosen)
        self._update_export_btn()

    def _update_export_btn(self) -> None:
        self._export_btn.setEnabled(
            bool(checked_indices(self._list)) and bool(self._folder_edit.text())
        )

    # ── export ───────────────────────────────────────────────────────────────

    def _export(self) -> None:
        out_dir = Path(self._folder_edit.text())
        written: list[str] = []
        skipped: list[str] = []
        failed: list[str] = []
        used_names: set[str] = set()

        for i in checked_indices(self._list):
            entry = self._entries[i]
            label = entry.name or tr("(unnamed)")
            try:
                mesh = make_shape_mesh(entry.kind, entry.geometry)
                if mesh is None:
                    skipped.append(label)
                    continue
                # algorithm=None: pyvista's recommended, auto-selected (and more
                # performant) surface extraction; pins today's future default so
                # behaviour doesn't shift under us and silences the FutureWarning.
                surface = mesh.extract_surface(algorithm=None).triangulate()
                base = _safe_filename(entry.name)
                name = base
                n = 2
                while name in used_names:
                    name = f"{base}_{n}"
                    n += 1
                used_names.add(name)
                surface.save(str(out_dir / f"{name}.stl"))
                written.append(f"{name}.stl")
            except Exception as e:
                failed.append(f"{label}: {e}")

        lines = [tr("{n} file(s) written to {dir}.").format(n=len(written), dir=out_dir)]
        if skipped:
            lines.append(
                tr("Skipped (no drawable geometry): {names}").format(names=", ".join(skipped))
            )
        if failed:
            lines.append(tr("Failed: {names}").format(names=", ".join(failed)))
        QMessageBox.information(self, tr("Export Shapes as STL"), "\n".join(lines))
        self.accept()
