# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import copy

from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox

from foam.nodes import FoamNode
from foam.parser import OpenFoamParser, ParseError
from foam.writer import write_node, write_root
from model.tree_model import FoamTreeModel
from i18n import tr
from ui.layout_constants import (
    BLOCKMESH_DICT_NAME as _BLOCKMESH_DICT_NAME,
    STATUS_NORMAL as _STATUS_NORMAL,
    STATUS_WARNING as _STATUS_WARNING,
    STATUS_SHORT as _STATUS_SHORT,
)


class _TreeOpsMixin:
    """Tree view and editor↔tree sync operations."""

    # ── copy / paste setup ────────────────────────────────────────────────────

    def _setup_tree_copy_paste(self) -> None:
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_tree_context_menu)

        copy_sc = QShortcut(QKeySequence.Copy, self.tree)
        copy_sc.setContext(Qt.WidgetShortcut)
        copy_sc.activated.connect(self._tree_copy_value)

        paste_sc = QShortcut(QKeySequence.Paste, self.tree)
        paste_sc.setContext(Qt.WidgetShortcut)
        paste_sc.activated.connect(self._tree_paste_value)

    def _on_tree_context_menu(self, pos) -> None:
        index = self.tree.indexAt(pos)
        if not index.isValid():
            return

        src = self._to_source(index)
        node = src.internalPointer()
        parent_node = node.parent if node.parent is not None else self.state.current_model.root

        value_index = self.state.current_model.index(
            src.row(), FoamTreeModel.COL_VALUE, src.parent()
        )
        can_paste = bool(self.state.current_model.flags(value_index) & Qt.ItemIsEditable)
        can_add_sibling = (
            parent_node is self.state.current_model.root
            or parent_node.node_type == "dictionary"
        )
        can_add_child = node.node_type == "dictionary"

        menu = QMenu(self)
        copy_action = menu.addAction(tr("Copy Value\tCtrl+C"))
        paste_action = menu.addAction(tr("Paste Value\tCtrl+V"))
        paste_action.setEnabled(can_paste)

        menu.addSeparator()
        add_after_action = menu.addAction(tr("Add Entry After"))
        add_after_action.setEnabled(can_add_sibling)
        add_child_action = menu.addAction(tr("Add Child Entry"))
        add_child_action.setEnabled(can_add_child)
        dup_action = menu.addAction(tr("Duplicate"))
        dup_action.setEnabled(can_add_sibling)

        is_commented_out = self._is_commented_out_node(node)
        is_boundary_entry = node.node_type == "boundary_entry"
        is_boundary_field_patch = (
            node.node_type == "dictionary"
            and node.parent is not None
            and node.parent.name == "boundaryField"
        )
        is_renameable_boundary = is_boundary_entry or is_boundary_field_patch

        rename_boundary_action = None
        if is_renameable_boundary:
            menu.addSeparator()
            rename_boundary_action = menu.addAction(tr("Rename Boundary..."))

        menu.addSeparator()
        comment_action = menu.addAction(tr("Comment Out"))
        comment_action.setEnabled(can_add_sibling and not is_commented_out)
        restore_action = menu.addAction(tr("Restore from Comment"))
        restore_action.setEnabled(is_commented_out)
        delete_action = menu.addAction(tr("Delete"))
        delete_action.setEnabled(can_add_sibling)

        action = menu.exec(self.tree.viewport().mapToGlobal(pos))
        if action == copy_action:
            self._tree_copy_value()
        elif action == paste_action:
            self._tree_paste_value()
        elif action == add_after_action:
            self._tree_add_entry_after(node)
        elif action == add_child_action:
            self._tree_add_child_entry(node)
        elif action == dup_action:
            self._tree_duplicate(node)
        elif action == comment_action:
            self._tree_comment_out(node)
        elif action == restore_action:
            self._tree_restore_comment(node)
        elif action == delete_action:
            self._tree_delete(node)
        elif action is not None and action == rename_boundary_action:
            self._on_rename_boundary_by_name(node.name)

    def _tree_copy_value(self) -> None:
        index = self._current_primary_index()
        if not index.isValid():
            return
        value_index = self.state.current_model.index(
            index.row(), FoamTreeModel.COL_VALUE, index.parent()
        )
        text = self.state.current_model.data(value_index, Qt.DisplayRole) or ""
        if text:
            QApplication.clipboard().setText(text)
            self.statusBar().showMessage(tr("Copied: {text}").format(text=text), _STATUS_SHORT)

    def _tree_paste_value(self) -> None:
        index = self._current_primary_index()
        if not index.isValid():
            return
        value_index = self.state.current_model.index(
            index.row(), FoamTreeModel.COL_VALUE, index.parent()
        )
        if not (self.state.current_model.flags(value_index) & Qt.ItemIsEditable):
            return
        text = QApplication.clipboard().text().strip()
        if not text:
            return
        ok = self.state.current_model.setData(value_index, text, Qt.EditRole)
        if ok:
            self._after_model_edit()
        else:
            self.statusBar().showMessage(tr("Paste failed: value format not accepted"), _STATUS_WARNING)

    # ── tree mutations ────────────────────────────────────────────────────────

    def _tree_add_entry_after(self, node: FoamNode) -> None:
        parent_node = node.parent if node.parent is not None else self.state.current_model.root
        position = parent_node.children.index(node) + 1
        new_node = FoamNode(name="newKey", node_type="word", value="newValue", modified=True)
        src_index = self.state.current_model.insert_node(parent_node, position, new_node)
        new_index = self._to_proxy(src_index)
        self.tree.setCurrentIndex(new_index)
        self.tree.scrollTo(new_index)
        self.tree.edit(new_index)
        self._after_model_edit()

    def _tree_add_child_entry(self, node: FoamNode) -> None:
        position = len(node.children)
        new_node = FoamNode(name="newKey", node_type="word", value="newValue", modified=True)
        parent_src_idx = self.state.current_model._index_of_node(node)
        self.tree.expand(self._to_proxy(parent_src_idx))
        src_index = self.state.current_model.insert_node(node, position, new_node)
        new_index = self._to_proxy(src_index)
        self.tree.setCurrentIndex(new_index)
        self.tree.scrollTo(new_index)
        self.tree.edit(new_index)
        self._after_model_edit()

    def _tree_duplicate(self, node: FoamNode) -> None:
        parent_node = node.parent if node.parent is not None else self.state.current_model.root
        position = parent_node.children.index(node) + 1
        orig_parent = node.parent
        node.parent = None
        new_node = copy.deepcopy(node)
        node.parent = orig_parent
        self.state.current_model._attach_parents(new_node, None)
        new_node.modified = True
        src_index = self.state.current_model.insert_node(parent_node, position, new_node)
        new_index = self._to_proxy(src_index)
        self.tree.setCurrentIndex(new_index)
        self.tree.scrollTo(new_index)
        self._after_model_edit()

    def _tree_comment_out(self, node: FoamNode) -> None:
        parent_node = node.parent if node.parent is not None else self.state.current_model.root
        position = parent_node.children.index(node)
        indent = self._node_indent(node)
        raw = write_node(node, indent)
        commented = "\n".join(
            ("// " + line) if line.strip() else line
            for line in raw.rstrip("\n").split("\n")
        ) + "\n"
        new_node = FoamNode(
            name="", node_type="unknown_raw_entry",
            value=commented.strip(), modified=False,
        )
        new_node.raw_text = commented
        self._mark_parent_modified(parent_node)
        self.state.current_model.remove_node(node)
        src_index = self.state.current_model.insert_node(parent_node, position, new_node)
        self.tree.setCurrentIndex(self._to_proxy(src_index))
        self._after_model_edit()

    def _tree_delete(self, node: FoamNode) -> None:
        reply = QMessageBox.question(
            self, tr("Delete Entry"),
            tr("Delete '{node_name}'? This cannot be undone.").format(node_name=node.name),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        parent_node = node.parent if node.parent is not None else self.state.current_model.root
        self._mark_parent_modified(parent_node)
        self.state.current_model.remove_node(node)
        self._after_model_edit()

    def _tree_restore_comment(self, node: FoamNode) -> None:
        raw = node.raw_text or str(node.value or "")
        uncommented_lines = []
        for line in raw.split("\n"):
            stripped = line.lstrip()
            indent_chars = len(line) - len(stripped)
            prefix = line[:indent_chars]
            if stripped.startswith("// "):
                uncommented_lines.append(prefix + stripped[3:])
            elif stripped.startswith("//"):
                uncommented_lines.append(prefix + stripped[2:])
            else:
                uncommented_lines.append(line)
        uncommented = "\n".join(uncommented_lines)

        try:
            parsed_root = OpenFoamParser(uncommented).parse()
        except ParseError as e:
            QMessageBox.warning(self, tr("Restore Failed"), tr("Could not parse the uncommented text:\n\n{e}").format(e=e))
            return

        if not parsed_root.children:
            QMessageBox.warning(self, tr("Restore Failed"), tr("No entries found after removing comment markers."))
            return

        parent_node = node.parent if node.parent is not None else self.state.current_model.root
        position = parent_node.children.index(node)
        self._mark_parent_modified(parent_node)
        self.state.current_model.remove_node(node)
        last_index = None
        for offset, restored in enumerate(parsed_root.children):
            restored.modified = True
            last_index = self.state.current_model.insert_node(parent_node, position + offset, restored)
        if last_index is not None:
            proxy_index = self._to_proxy(last_index)
            self.tree.setCurrentIndex(proxy_index)
            self.tree.scrollTo(proxy_index)
        self._after_model_edit()

    # ── comparison panel ─────────────────────────────────────────────────────

    def _apply_comparison_value(self, b_node: FoamNode) -> None:
        """Apply a leaf value from the reference case tree to the current tree."""
        # Build key path: walk b_node up to root (parent is None).
        path: list[str] = []
        current = b_node
        while current is not None and current.parent is not None:
            if current.name:
                path.append(current.name)
            current = current.parent
        path.reverse()

        if not path:
            return

        parent_path, leaf_key = path[:-1], path[-1]

        # Walk to the parent dictionary in the current tree.
        parent_node = self.state.current_root
        for key in parent_path:
            found = next((c for c in parent_node.children if c.name == key), None)
            if found is None:
                self.statusBar().showMessage(
                    tr("Cannot apply: '{path}' not found in current case").format(
                        path='/'.join(parent_path)
                    ),
                    _STATUS_WARNING,
                )
                return
            parent_node = found

        existing = next((c for c in parent_node.children if c.name == leaf_key), None)

        if existing is not None:
            # Overwrite type and value directly to handle cross-type changes.
            existing.node_type = b_node.node_type
            existing.value = (
                copy.deepcopy(b_node.value)
                if isinstance(b_node.value, (list, dict))
                else b_node.value
            )
            existing.modified = True
            src_idx = self.state.current_model._index_of_node(existing)
            row_start = self.state.current_model.index(src_idx.row(), 0, src_idx.parent())
            row_end = self.state.current_model.index(
                src_idx.row(), FoamTreeModel.COL_VALUE, src_idx.parent()
            )
            self.state.current_model.dataChanged.emit(
                row_start, row_end, [Qt.DisplayRole, Qt.EditRole]
            )
            msg = tr("Applied '{key}' from reference case").format(key=leaf_key)
        else:
            new_node = copy.deepcopy(b_node)
            new_node.modified = True
            self._mark_parent_modified(parent_node)
            position = len(parent_node.children)
            src_idx = self.state.current_model.insert_node(parent_node, position, new_node)
            proxy_idx = self._to_proxy(src_idx)
            self.tree.setCurrentIndex(proxy_idx)
            self.tree.scrollTo(proxy_idx)
            msg = tr("Inserted '{key}' from reference case").format(key=leaf_key)

        self._after_model_edit()
        self._recompute_diff()
        self.statusBar().showMessage(msg, _STATUS_SHORT)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _node_indent(self, node: FoamNode) -> int:
        indent = 0
        current = node.parent
        while current is not None and current is not self.state.current_model.root:
            indent += 1
            current = current.parent
        return indent

    def _mark_parent_modified(self, parent_node: FoamNode) -> None:
        if parent_node is not self.state.current_model.root:
            parent_node.modified = True

    def _is_commented_out_node(self, node: FoamNode) -> bool:
        if node.node_type != "unknown_raw_entry":
            return False
        raw = node.raw_text or str(node.value or "")
        non_blank = [l for l in raw.split("\n") if l.strip()]
        return bool(non_blank) and all(l.lstrip().startswith("//") for l in non_blank)

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
        from pathlib import Path

        text = self.editor_panel.get_text()
        try:
            _parser = OpenFoamParser(text)
            root = _parser.parse()
            if self.state.current_file:
                self.state.parsed_roots[self.state.current_file] = root
                self.boundary_panel.update_field(self.state.current_file, root)
                if self.block_mesh_panel is not None and Path(self.state.current_file).name == _BLOCKMESH_DICT_NAME:
                    self.block_mesh_panel.update_block_mesh(self.state.current_file, root)
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
        from foam.block_mesh_extractor import parse_vertices
        from foam.utils import format_scalar
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
