# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtWidgets import QMessageBox

from foam.block_mesh_extractor import parse_vertices
from foam.nodes import FoamNode
from foam.parser import OpenFoamParser, ParseError
from foam.utils import format_scalar
from foam.writer import write_root
from model.tree_model import FoamTreeModel
from i18n import tr
from ui.layout_constants import (
    BLOCKMESH_DICT_NAME as _BLOCKMESH_DICT_NAME,
    TOPOSET_DICT_NAME as _TOPOSET_DICT_NAME,
    STATUS_NORMAL as _STATUS_NORMAL,
    STATUS_WARNING as _STATUS_WARNING,
    STATUS_SHORT as _STATUS_SHORT,
)


class _TreeSyncOpsMixin:
    """Tree ↔ editor synchronisation, selection handling, and detail panel updates."""

    # ── editor → tree sync ────────────────────────────────────────────────────

    def _sync_tree_to_editor_line(self) -> None:
        if not self.state.source_lines_valid:
            self.statusBar().showMessage(tr("Apply Text to Tree to enable editor-to-tree sync"), _STATUS_SHORT)
            return

        line = self.editor_panel.current_line_number()
        node = self._find_deepest(self.state.current_root, line)

        if node is None:
            self.statusBar().showMessage(tr("No tree entry found for line {line}").format(line=line), _STATUS_SHORT)
            return

        # Walk up to the nearest ancestor visible in the proxy (not filtered out).
        proxy_index = QModelIndex()
        current = node
        while current is not None and current is not self.state.current_root:
            src_index = self.state.current_model._index_of_node(current)
            proxy_index = self._to_proxy(src_index)
            if proxy_index.isValid():
                break
            current = current.parent

        if not proxy_index.isValid():
            self.statusBar().showMessage(tr("Entry is hidden by the current filter"), _STATUS_SHORT)
            return

        self.state.syncing = True
        self.tree.setCurrentIndex(proxy_index)
        self.tree.scrollTo(proxy_index)
        self.state.syncing = False

    def _find_deepest(self, node: FoamNode, line: int) -> FoamNode | None:
        children = (
            node.value
            if node.node_type == "field_value_block" and isinstance(node.value, list)
            else node.children
        )
        for child in children:
            if child.source_line > 0 and child.source_line <= line <= child.source_end_line:
                deeper = self._find_deepest(child, line)
                return deeper if deeper is not None else child
        return None

    # ── tree selection + detail panel ─────────────────────────────────────────

    def on_tree_selection(self) -> None:
        index = self._current_primary_index()
        if not index.isValid():
            self.detail_panel.show_empty()
            return

        node = index.internalPointer()
        if node is None:
            self.detail_panel.show_empty()
            return

        if node.node_type == "field_value":
            self.detail_panel.show_field_value_for_node(node, self.state.current_model)
        else:
            self.detail_panel.show_for_node(node, self.state.current_model, self.state.current_file)

        if self.state.syncing:
            return

        if node.source_line > 0 and self.state.source_lines_valid:
            self.editor_panel.jump_to_node(
                node.source_line, node.source_end_line,
                scroll=self.editor_autoscroll_checkbox.isChecked(),
            )
        elif not self.state.source_lines_valid:
            self.statusBar().showMessage(tr("Apply Text to Tree to re-enable jump-to-line"), _STATUS_SHORT)
        elif node.source_line == 0:
            self.statusBar().showMessage(tr("No source location — entry was added or modified in the tree"), _STATUS_SHORT)

    def _on_value_apply(self, new_value: str) -> None:
        index = self._current_primary_index()
        if not index.isValid():
            return

        value_index = self.state.current_model.index(index.row(), 2, index.parent())
        ok = self.state.current_model.setData(value_index, new_value, Qt.EditRole)
        if not ok:
            QMessageBox.warning(self, tr("Edit Error"), tr("Could not apply the value to the selected node."))
            return
        self._after_model_edit()

    def _on_field_value_apply(self, field_type: str, raw_value: str) -> None:
        index = self._current_primary_index()
        if not index.isValid():
            return

        node = index.internalPointer()
        if node is None or node.node_type != "field_value":
            return

        if not field_type:
            QMessageBox.warning(self, tr("Edit Error"), tr("Field Type must not be empty."))
            return

        node.value["field_type"] = field_type
        node.modified = True

        value_index = self.state.current_model.index(index.row(), 2, index.parent())
        ok = self.state.current_model.setData(value_index, raw_value, Qt.EditRole)
        if not ok:
            QMessageBox.warning(self, "Edit Error", "Could not apply the field value.")
            return

        type_index = self.state.current_model.index(index.row(), 1, index.parent())
        self.state.current_model.dataChanged.emit(type_index, value_index, [Qt.DisplayRole, Qt.EditRole])
        self._after_model_edit()

    # ── editor ↔ tree sync ────────────────────────────────────────────────────

    def apply_text_to_tree(self) -> None:
        text = self.editor_panel.get_text()
        try:
            _parser = OpenFoamParser(text)
            root = _parser.parse()
            if self.state.current_file:
                self.state.parsed_roots[self.state.current_file] = root
                self.boundary_panel.update_field(self.state.current_file, root)
                if self.block_mesh_panel is not None and Path(self.state.current_file).name == _BLOCKMESH_DICT_NAME:
                    self.block_mesh_panel.update_block_mesh(self.state.current_file, root)
                if self.block_mesh_panel is not None and Path(self.state.current_file).name == _TOPOSET_DICT_NAME:
                    self.block_mesh_panel.update_topo_set(self.state.current_file, root)
            self._load_tree(root)
            self._mark_dirty()
            if _parser.errors:
                n = len(_parser.errors)
                self.statusBar().showMessage(
                    f"Parsed and tree updated — {n} unrecognized entr{'y' if n == 1 else 'ies'}",
                    _STATUS_WARNING,
                )
            else:
                self.statusBar().showMessage(tr("Parsed successfully and tree updated"), _STATUS_NORMAL)
        except ParseError as e:
            self.statusBar().showMessage(tr("Parse failed: {e}").format(e=e), _STATUS_WARNING)
            QMessageBox.warning(
                self,
                "Parse Error",
                f"Tree update failed.\n\n{e}\n\n"
                "Text editor contents are kept as-is. "
                "You can continue editing and try again.",
            )

    def reload_text_from_tree(self) -> None:
        self.editor_panel.set_text(write_root(self.state.current_root))
        self._update_window_title()
        self._update_file_label()
        if self.state.current_file:
            self.file_list_panel.mark_dirty(self.state.current_file, self.state.text_dirty)
        self.statusBar().showMessage(tr("Reloaded text from current tree"), _STATUS_SHORT)

    def _on_blockmesh_vertices_changed(self, idx: int, xyz: list) -> None:
        if self.state.current_root is None:
            return
        vtx_node = next(
            (c for c in self.state.current_root.children
             if c.name == "vertices" and c.node_type == "raw_list"),
            None,
        )
        if vtx_node is None:
            return
        verts = parse_vertices(str(vtx_node.value))
        if idx < 0 or idx >= len(verts):
            return
        verts[idx] = xyz
        vtx_node.value = "\n" + "".join(
            f"    ({format_scalar(v[0])} {format_scalar(v[1])} {format_scalar(v[2])})\n"
            for v in verts
        )
        vtx_node.modified = True
        self.editor_panel.set_text(write_root(self.state.current_root))
        self._mark_dirty()
        self._resize_tree_columns()
        self.on_tree_selection()
        self.statusBar().showMessage(tr("Vertex coordinates updated"), _STATUS_SHORT)

    def _on_user_text_changed(self) -> None:
        if not self.state.current_file:
            return
        self._mark_dirty()
        self.state.source_lines_valid = False
        self._update_sync_checkbox()
        self.editor_panel.clear_node_highlight()
