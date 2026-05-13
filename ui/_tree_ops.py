# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import copy

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox

from foam.nodes import FoamNode
from foam.parser import OpenFoamParser, ParseError
from foam.writer import write_node, write_root
from model.tree_model import FoamTreeModel
from ui.layout_constants import (
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

        node = self.current_model.index(index.row(), 0, index.parent()).internalPointer()
        parent_node = node.parent if node.parent is not None else self.current_model.root

        value_index = self.current_model.index(
            index.row(), FoamTreeModel.COL_VALUE, index.parent()
        )
        can_paste = bool(self.current_model.flags(value_index) & Qt.ItemIsEditable)
        can_add_sibling = (
            parent_node is self.current_model.root
            or parent_node.node_type == "dictionary"
        )
        can_add_child = node.node_type == "dictionary"

        menu = QMenu(self)
        copy_action = menu.addAction("Copy Value\tCtrl+C")
        paste_action = menu.addAction("Paste Value\tCtrl+V")
        paste_action.setEnabled(can_paste)

        menu.addSeparator()
        add_after_action = menu.addAction("Add Entry After")
        add_after_action.setEnabled(can_add_sibling)
        add_child_action = menu.addAction("Add Child Entry")
        add_child_action.setEnabled(can_add_child)
        dup_action = menu.addAction("Duplicate")
        dup_action.setEnabled(can_add_sibling)

        is_commented_out = self._is_commented_out_node(node)

        menu.addSeparator()
        comment_action = menu.addAction("Comment Out")
        comment_action.setEnabled(can_add_sibling and not is_commented_out)
        restore_action = menu.addAction("Restore from Comment")
        restore_action.setEnabled(is_commented_out)
        delete_action = menu.addAction("Delete")
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

    def _tree_copy_value(self) -> None:
        index = self._current_primary_index()
        if not index.isValid():
            return
        value_index = self.current_model.index(
            index.row(), FoamTreeModel.COL_VALUE, index.parent()
        )
        text = self.current_model.data(value_index, Qt.DisplayRole) or ""
        if text:
            QApplication.clipboard().setText(text)
            self.statusBar().showMessage(f"Copied: {text}", _STATUS_SHORT)

    def _tree_paste_value(self) -> None:
        index = self._current_primary_index()
        if not index.isValid():
            return
        value_index = self.current_model.index(
            index.row(), FoamTreeModel.COL_VALUE, index.parent()
        )
        if not (self.current_model.flags(value_index) & Qt.ItemIsEditable):
            return
        text = QApplication.clipboard().text().strip()
        if not text:
            return
        ok = self.current_model.setData(value_index, text, Qt.EditRole)
        if ok:
            self._after_model_edit()
        else:
            self.statusBar().showMessage("Paste failed: value format not accepted", _STATUS_WARNING)

    # ── tree mutations ────────────────────────────────────────────────────────

    def _tree_add_entry_after(self, node: FoamNode) -> None:
        parent_node = node.parent if node.parent is not None else self.current_model.root
        position = parent_node.children.index(node) + 1
        new_node = FoamNode(name="newKey", node_type="word", value="newValue", modified=True)
        new_index = self.current_model.insert_node(parent_node, position, new_node)
        self.tree.setCurrentIndex(new_index)
        self.tree.scrollTo(new_index)
        self.tree.edit(new_index)
        self._after_model_edit()

    def _tree_add_child_entry(self, node: FoamNode) -> None:
        position = len(node.children)
        new_node = FoamNode(name="newKey", node_type="word", value="newValue", modified=True)
        parent_idx = self.current_model._index_of_node(node)
        self.tree.expand(parent_idx)
        new_index = self.current_model.insert_node(node, position, new_node)
        self.tree.setCurrentIndex(new_index)
        self.tree.scrollTo(new_index)
        self.tree.edit(new_index)
        self._after_model_edit()

    def _tree_duplicate(self, node: FoamNode) -> None:
        parent_node = node.parent if node.parent is not None else self.current_model.root
        position = parent_node.children.index(node) + 1
        orig_parent = node.parent
        node.parent = None
        new_node = copy.deepcopy(node)
        node.parent = orig_parent
        self.current_model._attach_parents(new_node, None)
        new_node.modified = True
        new_index = self.current_model.insert_node(parent_node, position, new_node)
        self.tree.setCurrentIndex(new_index)
        self.tree.scrollTo(new_index)
        self._after_model_edit()

    def _tree_comment_out(self, node: FoamNode) -> None:
        parent_node = node.parent if node.parent is not None else self.current_model.root
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
        self.current_model.remove_node(node)
        inserted = self.current_model.insert_node(parent_node, position, new_node)
        self.tree.setCurrentIndex(inserted)
        self._after_model_edit()

    def _tree_delete(self, node: FoamNode) -> None:
        reply = QMessageBox.question(
            self, "Delete Entry",
            f"Delete '{node.name}'? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        parent_node = node.parent if node.parent is not None else self.current_model.root
        self._mark_parent_modified(parent_node)
        self.current_model.remove_node(node)
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
            QMessageBox.warning(self, "Restore Failed", f"Could not parse the uncommented text:\n\n{e}")
            return

        if not parsed_root.children:
            QMessageBox.warning(self, "Restore Failed", "No entries found after removing comment markers.")
            return

        parent_node = node.parent if node.parent is not None else self.current_model.root
        position = parent_node.children.index(node)
        self._mark_parent_modified(parent_node)
        self.current_model.remove_node(node)
        last_index = None
        for offset, restored in enumerate(parsed_root.children):
            restored.modified = True
            last_index = self.current_model.insert_node(parent_node, position + offset, restored)
        if last_index is not None:
            self.tree.setCurrentIndex(last_index)
            self.tree.scrollTo(last_index)
        self._after_model_edit()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _node_indent(self, node: FoamNode) -> int:
        indent = 0
        current = node.parent
        while current is not None and current is not self.current_model.root:
            indent += 1
            current = current.parent
        return indent

    def _mark_parent_modified(self, parent_node: FoamNode) -> None:
        if parent_node is not self.current_model.root:
            parent_node.modified = True

    def _is_commented_out_node(self, node: FoamNode) -> bool:
        if node.node_type != "unknown_raw_entry":
            return False
        raw = node.raw_text or str(node.value or "")
        non_blank = [l for l in raw.split("\n") if l.strip()]
        return bool(non_blank) and all(l.lstrip().startswith("//") for l in non_blank)

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
            self.detail_panel.show_field_value_for_node(node, self.current_model)
        else:
            self.detail_panel.show_for_node(node, self.current_model, self.current_file)

    def _on_value_apply(self, new_value: str) -> None:
        index = self._current_primary_index()
        if not index.isValid():
            return

        value_index = self.current_model.index(index.row(), 2, index.parent())
        ok = self.current_model.setData(value_index, new_value, Qt.EditRole)
        if not ok:
            QMessageBox.warning(self, "Edit Error", "Could not apply the value to the selected node.")
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
            QMessageBox.warning(self, "Edit Error", "Field Type must not be empty.")
            return

        node.value["field_type"] = field_type
        node.modified = True

        value_index = self.current_model.index(index.row(), 2, index.parent())
        ok = self.current_model.setData(value_index, raw_value, Qt.EditRole)
        if not ok:
            QMessageBox.warning(self, "Edit Error", "Could not apply the field value.")
            return

        type_index = self.current_model.index(index.row(), 1, index.parent())
        self.current_model.dataChanged.emit(type_index, value_index, [Qt.DisplayRole, Qt.EditRole])
        self._after_model_edit()

    # ── editor ↔ tree sync ────────────────────────────────────────────────────

    def apply_text_to_tree(self) -> None:
        text = self.editor_panel.get_text()
        try:
            root = OpenFoamParser(text).parse()
            if self.current_file:
                self._parsed_roots[self.current_file] = root
                self.boundary_panel.update_field(self.current_file, root)
            self._load_tree(root)
            self._mark_dirty()
            self.statusBar().showMessage("Parsed successfully and tree updated", _STATUS_NORMAL)
        except ParseError as e:
            self.statusBar().showMessage(f"Parse failed: {e}", _STATUS_WARNING)
            QMessageBox.warning(
                self,
                "Parse Error",
                f"Tree update failed.\n\n{e}\n\n"
                "Text editor contents are kept as-is. "
                "You can continue editing and try again.",
            )

    def reload_text_from_tree(self) -> None:
        self.editor_panel.set_text(write_root(self.current_root))
        self._update_window_title()
        self._update_file_label()
        if self.current_file:
            self.file_list_panel.mark_dirty(self.current_file, self.text_dirty)
        self.statusBar().showMessage("Reloaded text from current tree", _STATUS_SHORT)

    def _on_user_text_changed(self) -> None:
        if not self.current_file:
            return
        self._mark_dirty()
