# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import csv
import io
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from foam.nodes import FoamNode
from ui.boundary_edit_dialog import _get_patch_type, _patch_inner_text, _value_complexity

_PATH_ROLE = Qt.UserRole
_PATCH_NAME_ROLE = Qt.UserRole + 1
_PATCH_NODE_ROLE = Qt.UserRole + 2


def _is_in_dir(path: str, case_dir: str, dir_name: str) -> bool:
    try:
        return Path(path).relative_to(case_dir).parts[0] == dir_name
    except (ValueError, IndexError):
        return False


def _extract_boundary(root: FoamNode) -> dict[str, FoamNode]:
    """Return {patch_name: patch_dict_node} from root's boundaryField dict."""
    for node in root.children:
        if node.name == "boundaryField" and node.node_type == "dictionary":
            return {
                child.name: child
                for child in node.children
                if child.node_type == "dictionary"
            }
    return {}


def _is_printable(text: str) -> bool:
    """Return False if text contains non-printable control characters (binary data)."""
    return not any(c < "\x09" for c in text)


def _extra_patch_lines(patch_node: FoamNode, max_lines: int) -> list[str]:
    """Return up to max_lines additional key-value lines from a patch node (type excluded)."""
    lines: list[str] = []
    for child in patch_node.children:
        if child.name == "type":
            continue
        val = child.value
        if isinstance(val, (str, int, float)) and str(val).strip():
            display = str(val).split("\n")[0].strip()
            lines.append(f"{child.name}  {display if _is_printable(display) else '(binary)'}")
        else:
            lines.append(f"{child.name}  ...")
        if len(lines) >= max_lines:
            break
    return lines


def _make_cell_item(
    patch_node: FoamNode | None, path: str, patch_name: str, n_lines: int = 1
) -> QTableWidgetItem:
    if patch_node is None:
        item = QTableWidgetItem("–")
        item.setForeground(QColor("#aaaaaa"))
        item.setBackground(QColor("#f5f5f5"))
    else:
        type_str = _get_patch_type(patch_node)
        complexity = _value_complexity(patch_node)
        if type_str:
            label = f"{type_str} †" if complexity else type_str
            if n_lines > 1:
                extra = _extra_patch_lines(patch_node, n_lines - 1)
                if extra:
                    label = label + "\n" + "\n".join(extra)
        else:
            lines = _extra_patch_lines(patch_node, n_lines)
            if lines:
                if complexity:
                    lines[0] += " †"
                label = "\n".join(lines)
            else:
                label = "– †" if complexity else "–"
        item = QTableWidgetItem(label)
        if not type_str:
            f = QFont()
            f.setItalic(True)
            item.setFont(f)
        if complexity:
            data_desc = "binary data" if complexity == "binary" else "large data"
            item.setToolTip(f"type {type_str};\nvalue: {data_desc} — edit in Text Editor")
        else:
            if patch_node.raw_text and patch_node.raw_text.strip():
                rt = patch_node.raw_text.strip()
            else:
                inner = _patch_inner_text(patch_node)
                indented = "\n".join(f"    {ln}" for ln in inner.splitlines()) if inner else ""
                rt = f"{patch_node.name}\n{{\n{indented}\n}}"
            item.setToolTip(rt)
        item.setData(_PATCH_NODE_ROLE, patch_node)

    # Always store path and patch_name so all cells support context menu and create.
    item.setData(_PATH_ROLE, path)
    item.setData(_PATCH_NAME_ROLE, patch_name)
    return item


class BoundaryViewPanel(QWidget):
    patch_edit_requested        = Signal(str, str, object)  # (path, patch_name, patch_node)
    patch_create_requested      = Signal(str, str)          # (path, patch_name)
    patch_delete_requested      = Signal(str, str)          # (path, patch_name)
    patch_paste_requested       = Signal(str, str, str)     # (path, patch_name, content)
    patch_delete_all_requested  = Signal(str)               # (patch_name) — all field files
    patch_add_all_requested     = Signal(str)               # (patch_name) — all field files
    patch_rename_requested      = Signal(str)               # (patch_name) — rename across all files
    patch_selected              = Signal(str, str)          # (path, patch_name) — single-click navigation

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._all_field_roots: dict[str, FoamNode] = {}
        self._case_dir: str | None = None
        self._transposed: bool = False
        self._clipboard: str | None = None

        self._dir_combo = QComboBox()
        self._dir_combo.setEnabled(False)
        self._dir_combo.currentIndexChanged.connect(self._refresh_table)

        self._lines_spin = QSpinBox()
        self._lines_spin.setMinimum(1)
        self._lines_spin.setMaximum(10)
        self._lines_spin.setValue(1)
        self._lines_spin.setToolTip("Number of lines to display per cell")
        self._lines_spin.valueChanged.connect(self._refresh_table)

        self._transpose_chk = QCheckBox("Transpose")
        self._transpose_chk.setToolTip("Swap rows (fields) and columns (patches)")
        self._transpose_chk.toggled.connect(self._on_transpose_toggled)

        self._autoscroll_chk = QCheckBox("Auto-scroll editor")
        self._autoscroll_chk.setChecked(True)
        self._autoscroll_chk.setToolTip(
            "When checked, clicking a cell opens its file in the editor\n"
            "and scrolls to the patch entry."
        )

        self._copy_btn = QPushButton("Copy Table")
        copy_menu = QMenu(self)
        copy_menu.addAction("Copy as Markdown", self._copy_as_markdown)
        copy_menu.addAction("Copy as CSV", self._copy_as_csv)
        self._copy_btn.setMenu(copy_menu)

        dir_row = QHBoxLayout()
        dir_row.addWidget(QLabel("Directory:"))
        dir_row.addWidget(self._dir_combo)
        dir_row.addStretch()
        dir_row.addWidget(self._transpose_chk)
        dir_row.addSpacing(12)
        dir_row.addWidget(self._autoscroll_chk)
        dir_row.addSpacing(12)
        dir_row.addWidget(QLabel("Lines per cell:"))
        dir_row.addWidget(self._lines_spin)
        dir_row.addSpacing(12)
        dir_row.addWidget(self._copy_btn)

        self._table = QTableWidget()
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectItems)
        self._table.itemClicked.connect(self._on_cell_clicked)
        self._table.itemDoubleClicked.connect(self._on_cell_double_clicked)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_table_context_menu)

        for hdr in (self._table.horizontalHeader(), self._table.verticalHeader()):
            hdr.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.horizontalHeader().customContextMenuRequested.connect(
            self._on_horizontal_header_context_menu
        )
        self._table.verticalHeader().customContextMenuRequested.connect(
            self._on_vertical_header_context_menu
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addLayout(dir_row)
        layout.addWidget(self._table)

    # ── public API ────────────────────────────────────────────────────────────

    def load_case(
        self,
        field_roots: dict[str, FoamNode],
        case_dir: str,
        available_dirs: list[str],
    ) -> None:
        self._all_field_roots = dict(field_roots)
        self._case_dir = case_dir

        self._dir_combo.blockSignals(True)
        self._dir_combo.clear()
        for d in available_dirs:
            self._dir_combo.addItem(d)
        self._dir_combo.setEnabled(len(available_dirs) > 1)
        self._dir_combo.blockSignals(False)

        self._refresh_table()

    def update_field(self, path: str, root: FoamNode) -> None:
        """Refresh the display for one file after it has been edited."""
        self._all_field_roots[path] = root
        if self._case_dir is None:
            return
        selected = self._dir_combo.currentText()
        if not _is_in_dir(path, self._case_dir, selected):
            return
        basename = Path(path).name
        n_lines = self._lines_spin.value()
        bd = _extract_boundary(root)

        if not self._transposed:
            for row in range(self._table.rowCount()):
                header = self._table.verticalHeaderItem(row)
                if header is not None and header.text() == basename:
                    for col in range(self._table.columnCount()):
                        h = self._table.horizontalHeaderItem(col)
                        if h is None:
                            continue
                        pn = h.text()
                        self._table.setItem(row, col, _make_cell_item(bd.get(pn), path, pn, n_lines))
                    self._table.resizeRowToContents(row)
                    break
        else:
            for col in range(self._table.columnCount()):
                header = self._table.horizontalHeaderItem(col)
                if header is not None and header.text() == basename:
                    for row in range(self._table.rowCount()):
                        h = self._table.verticalHeaderItem(row)
                        if h is None:
                            continue
                        pn = h.text()
                        self._table.setItem(row, col, _make_cell_item(bd.get(pn), path, pn, n_lines))
                    self._table.resizeColumnToContents(col)
                    break

    def refresh(self) -> None:
        """Rebuild the table from the current field roots (use after structural changes)."""
        self._refresh_table()

    def clear(self) -> None:
        self._all_field_roots.clear()
        self._case_dir = None
        self._dir_combo.blockSignals(True)
        self._dir_combo.clear()
        self._dir_combo.blockSignals(False)
        self._dir_combo.setEnabled(False)
        self._table.clear()
        self._table.setRowCount(0)
        self._table.setColumnCount(0)

    # ── internals ─────────────────────────────────────────────────────────────

    def _on_transpose_toggled(self, checked: bool) -> None:
        self._transposed = checked
        self._refresh_table()

    def _current_dir(self) -> str:
        return self._dir_combo.currentText()

    def _refresh_table(self) -> None:
        selected = self._current_dir()
        if not selected or not self._case_dir:
            self._table.clear()
            self._table.setRowCount(0)
            self._table.setColumnCount(0)
            return

        roots = {
            path: root
            for path, root in self._all_field_roots.items()
            if _is_in_dir(path, self._case_dir, selected)
        }
        if not roots:
            self._table.clear()
            self._table.setRowCount(0)
            self._table.setColumnCount(0)
            return

        field_paths = sorted(roots.keys(), key=lambda p: Path(p).name.lower())
        field_names = [Path(p).name for p in field_paths]

        all_boundaries: dict[str, dict[str, FoamNode]] = {}
        seen_patches: set[str] = set()
        for path in field_paths:
            bd = _extract_boundary(roots[path])
            all_boundaries[path] = bd
            seen_patches.update(bd.keys())
        patch_names = sorted(seen_patches)

        n_lines = self._lines_spin.value()
        self._table.blockSignals(True)
        self._table.clear()

        if not self._transposed:
            self._table.setRowCount(len(field_paths))
            self._table.setColumnCount(len(patch_names))
            self._table.setHorizontalHeaderLabels(patch_names)
            self._table.setVerticalHeaderLabels(field_names)
            for row, path in enumerate(field_paths):
                bd = all_boundaries[path]
                for col, patch_name in enumerate(patch_names):
                    self._table.setItem(row, col, _make_cell_item(bd.get(patch_name), path, patch_name, n_lines))
        else:
            self._table.setRowCount(len(patch_names))
            self._table.setColumnCount(len(field_paths))
            self._table.setHorizontalHeaderLabels(field_names)
            self._table.setVerticalHeaderLabels(patch_names)
            for row, patch_name in enumerate(patch_names):
                for col, path in enumerate(field_paths):
                    bd = all_boundaries[path]
                    self._table.setItem(row, col, _make_cell_item(bd.get(patch_name), path, patch_name, n_lines))

        self._table.blockSignals(False)
        self._table.resizeColumnsToContents()
        self._table.resizeRowsToContents()

    def _table_data(self) -> tuple[list[str], list[str], list[list[str]]]:
        """Return (col_headers, row_headers, rows_of_cell_text) from the current table."""
        t = self._table
        col_headers = [
            (t.horizontalHeaderItem(c).text() if t.horizontalHeaderItem(c) else "")
            for c in range(t.columnCount())
        ]
        row_headers = [
            (t.verticalHeaderItem(r).text() if t.verticalHeaderItem(r) else "")
            for r in range(t.rowCount())
        ]
        rows = [
            [
                (t.item(r, c).text() if t.item(r, c) else "–")
                for c in range(t.columnCount())
            ]
            for r in range(t.rowCount())
        ]
        return col_headers, row_headers, rows

    def _copy_as_markdown(self) -> None:
        col_headers, row_headers, rows = self._table_data()
        all_cols = [""] + col_headers
        sep = "|" + "|".join("---" for _ in all_cols) + "|"
        lines = ["| " + " | ".join(all_cols) + " |", sep]
        for rh, cells in zip(row_headers, rows):
            escaped = [c.replace("\n", "<br>") for c in cells]
            lines.append("| " + " | ".join([rh] + escaped) + " |")
        QApplication.clipboard().setText("\n".join(lines))

    def _copy_as_csv(self) -> None:
        col_headers, row_headers, rows = self._table_data()
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([""] + col_headers)
        for rh, cells in zip(row_headers, rows):
            writer.writerow([rh] + cells)
        QApplication.clipboard().setText(buf.getvalue())

    def _on_cell_clicked(self, item: QTableWidgetItem) -> None:
        if not self._autoscroll_chk.isChecked():
            return
        if item is None:
            return
        path = item.data(_PATH_ROLE)
        patch_name = item.data(_PATCH_NAME_ROLE)
        if path is None or patch_name is None:
            return
        self.patch_selected.emit(path, patch_name)

    def _on_cell_double_clicked(self, item: QTableWidgetItem) -> None:
        if item is None:
            return
        path = item.data(_PATH_ROLE)
        patch_name = item.data(_PATCH_NAME_ROLE)
        if path is None or patch_name is None:
            return
        patch_node = item.data(_PATCH_NODE_ROLE)
        if patch_node is None:
            self.patch_create_requested.emit(path, patch_name)
        else:
            self.patch_edit_requested.emit(path, patch_name, patch_node)

    def _on_table_context_menu(self, pos) -> None:
        item = self._table.itemAt(pos)
        if item is None:
            return
        path = item.data(_PATH_ROLE)
        patch_name = item.data(_PATCH_NAME_ROLE)
        if path is None or patch_name is None:
            return

        patch_node = item.data(_PATCH_NODE_ROLE)

        menu = QMenu(self)
        edit_action = menu.addAction("Edit")
        edit_action.setEnabled(patch_node is not None)
        create_action = menu.addAction("Create Entry")
        create_action.setEnabled(patch_node is None)
        delete_action = menu.addAction("Delete Entry")
        delete_action.setEnabled(patch_node is not None)

        menu.addSeparator()
        copy_action = menu.addAction("Copy")
        copy_action.setEnabled(patch_node is not None)
        paste_action = menu.addAction("Paste")
        paste_action.setEnabled(self._clipboard is not None)

        menu.addSeparator()
        rename_action = menu.addAction("Rename Boundary...")

        action = menu.exec(self._table.viewport().mapToGlobal(pos))
        if action == edit_action:
            self.patch_edit_requested.emit(path, patch_name, patch_node)
        elif action == create_action:
            self.patch_create_requested.emit(path, patch_name)
        elif action == delete_action:
            self.patch_delete_requested.emit(path, patch_name)
        elif action == copy_action:
            self._clipboard = _patch_inner_text(patch_node)
        elif action == paste_action and self._clipboard is not None:
            self.patch_paste_requested.emit(path, patch_name, self._clipboard)
        elif action == rename_action:
            self.patch_rename_requested.emit(patch_name)

    def _on_horizontal_header_context_menu(self, pos) -> None:
        # Non-transposed: horizontal header = patch names.
        # Transposed: horizontal header = field names (ignore).
        if self._transposed:
            return
        idx = self._table.horizontalHeader().logicalIndexAt(pos)
        item = self._table.horizontalHeaderItem(idx) if idx >= 0 else None
        patch_name = item.text() if item else None
        self._show_patch_header_menu(
            patch_name, self._table.horizontalHeader().mapToGlobal(pos)
        )

    def _on_vertical_header_context_menu(self, pos) -> None:
        # Non-transposed: vertical header = field names (ignore).
        # Transposed: vertical header = patch names.
        if not self._transposed:
            return
        idx = self._table.verticalHeader().logicalIndexAt(pos)
        item = self._table.verticalHeaderItem(idx) if idx >= 0 else None
        patch_name = item.text() if item else None
        self._show_patch_header_menu(
            patch_name, self._table.verticalHeader().mapToGlobal(pos)
        )

    def _show_patch_header_menu(self, patch_name: str | None, global_pos) -> None:
        menu = QMenu(self)
        delete_action = menu.addAction(
            f"Delete BoundaryField  '{patch_name}'" if patch_name else "Delete BoundaryField"
        )
        delete_action.setEnabled(patch_name is not None)
        rename_action = menu.addAction(
            f"Rename Boundary  '{patch_name}'..." if patch_name else "Rename Boundary..."
        )
        rename_action.setEnabled(patch_name is not None)
        menu.addSeparator()
        add_action = menu.addAction("Add BoundaryField...")

        action = menu.exec(global_pos)
        if action == delete_action and patch_name:
            self.patch_delete_all_requested.emit(patch_name)
        elif action == rename_action and patch_name:
            self.patch_rename_requested.emit(patch_name)
        elif action == add_action:
            self._prompt_add_boundary_field()

    def _prompt_add_boundary_field(self) -> None:
        existing: set[str] = set()
        for root in self._all_field_roots.values():
            existing.update(_extract_boundary(root).keys())

        name, ok = QInputDialog.getText(self, "Add BoundaryField", "New patch name:")
        if not ok:
            return
        name = name.strip()
        if not name:
            return
        if name in existing:
            QMessageBox.warning(
                self, "Add BoundaryField", f"Patch '{name}' already exists in the boundary view."
            )
            return
        self.patch_add_all_requested.emit(name)
