# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""
Regression tests for dirty-state tracking on tree edits made directly in the
Tree panel (inline cell editing), as opposed to edits applied through the
Detail panel.

Qt's built-in inline cell editor calls FoamTreeModel.setData() directly, not
through the "Apply" handlers in ui/mixins/_tree_sync_ops.py -- those handlers
are the only callers that used to invoke _after_model_edit() (which
regenerates the editor text and marks the file dirty). This left inline tree
edits invisible to dirty tracking: the node value changed, but the editor
text and the file's dirty flag never updated, so even "Reload from Tree"
would not flag the file as unsaved.

The fix connects FoamTreeModel.dataChanged to _after_model_edit() (see
ui/mixins/_model_ops.py::_load_tree), so any successful setData() call --
regardless of caller -- triggers the same follow-up. These tests call
setData() directly on the tree model to simulate the inline-edit path,
bypassing the Detail panel entirely.
"""
from __future__ import annotations

from PySide6.QtCore import Qt

from model.tree_model import FoamTreeModel


def _make_case(tmp_path, control_dict_text):
    (tmp_path / "system").mkdir()
    dict_path = tmp_path / "system" / "controlDict"
    dict_path.write_text(control_dict_text, encoding="utf-8")
    return str(dict_path)


class TestInlineTreeEditMarksDirty:
    def test_inline_value_edit_marks_file_dirty(self, main_window, tmp_path, control_dict_text):
        win = main_window
        dict_path = _make_case(tmp_path, control_dict_text)
        win._load_case_dir(str(tmp_path))
        win.load_selected_file(dict_path)

        assert win.state.text_dirty is False

        root = win.state.current_root
        row = next(i for i, c in enumerate(root.children) if c.name == "application")
        value_index = win.state.current_model.index(row, FoamTreeModel.COL_VALUE)

        ok = win.state.current_model.setData(value_index, "simpleFoam", Qt.EditRole)

        assert ok is True
        assert win.state.text_dirty is True
        assert win.state.file_dirty[dict_path] is True

    def test_inline_value_edit_regenerates_editor_text(self, main_window, tmp_path, control_dict_text):
        win = main_window
        dict_path = _make_case(tmp_path, control_dict_text)
        win._load_case_dir(str(tmp_path))
        win.load_selected_file(dict_path)

        root = win.state.current_root
        row = next(i for i, c in enumerate(root.children) if c.name == "application")
        value_index = win.state.current_model.index(row, FoamTreeModel.COL_VALUE)

        win.state.current_model.setData(value_index, "simpleFoam", Qt.EditRole)

        assert "simpleFoam" in win.editor_panel.get_text()

    def test_rejected_edit_does_not_mark_dirty(self, main_window, tmp_path, control_dict_text):
        """setData() returning False (invalid value) must not trigger dirty tracking."""
        win = main_window
        dict_path = _make_case(tmp_path, control_dict_text)
        win._load_case_dir(str(tmp_path))
        win.load_selected_file(dict_path)

        root = win.state.current_root
        row = next(i for i, c in enumerate(root.children) if c.name == "deltaT")
        value_index = win.state.current_model.index(row, FoamTreeModel.COL_VALUE)

        ok = win.state.current_model.setData(value_index, "notanumber", Qt.EditRole)

        assert ok is False
        assert win.state.text_dirty is False
        assert win.state.file_dirty.get(dict_path, False) is False
