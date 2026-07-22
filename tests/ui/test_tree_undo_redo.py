# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for snapshot-based tree undo/redo (ui/mixins/_undo_ops.py).

Undo is a single global timeline of serialized-text snapshots taken before each
tree mutation: inline edits stash a snapshot via FoamTreeModel.about_to_change
and commit it only once the edit is confirmed real; direct mutations
(CRUD/boundary ops) checkpoint explicitly. Undo re-parses the snapshot and
reloads the tree through _load_tree.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from model.tree_model import FoamTreeModel


def _make_case(tmp_path, control_dict_text):
    (tmp_path / "system").mkdir()
    dict_path = tmp_path / "system" / "controlDict"
    dict_path.write_text(control_dict_text, encoding="utf-8")
    return str(dict_path)


def _open(win, tmp_path, control_dict_text):
    dict_path = _make_case(tmp_path, control_dict_text)
    win._load_case_dir(str(tmp_path))
    win.load_selected_file(dict_path)
    return dict_path


def _set_value(win, key, value):
    root = win.state.current_root
    row = next(i for i, c in enumerate(root.children) if c.name == key)
    value_index = win.state.current_model.index(row, FoamTreeModel.COL_VALUE)
    ok = win.state.current_model.setData(value_index, value, Qt.EditRole)
    QApplication.processEvents()
    return ok


def _value_of(win, key):
    return next(c for c in win.state.current_root.children if c.name == key).value


class TestInlineEditUndoRedo:
    def test_undo_restores_value_text_and_dirty(self, main_window, tmp_path, control_dict_text):
        win = main_window
        dict_path = _open(win, tmp_path, control_dict_text)
        original = _value_of(win, "application")

        assert _set_value(win, "application", "simpleFoam")
        assert win.state.text_dirty is True

        win._tree_undo()

        assert _value_of(win, "application") == original
        assert "simpleFoam" not in win.editor_panel.get_text()
        # The restored text matches the on-disk file, so the file is clean.
        assert win.state.text_dirty is False
        assert win.state.file_dirty[dict_path] is False

    def test_redo_reapplies_the_edit(self, main_window, tmp_path, control_dict_text):
        win = main_window
        _open(win, tmp_path, control_dict_text)

        _set_value(win, "application", "simpleFoam")
        win._tree_undo()
        win._tree_redo()

        assert _value_of(win, "application") == "simpleFoam"
        assert "simpleFoam" in win.editor_panel.get_text()
        assert win.state.text_dirty is True

    def test_new_edit_clears_redo(self, main_window, tmp_path, control_dict_text):
        win = main_window
        _open(win, tmp_path, control_dict_text)

        _set_value(win, "application", "simpleFoam")
        win._tree_undo()
        _set_value(win, "application", "pisoFoam")

        assert win.state.undo.redo_stack == []
        win._tree_redo()  # nothing to redo; must not change anything
        assert _value_of(win, "application") == "pisoFoam"

    def test_multiple_undo_steps(self, main_window, tmp_path, control_dict_text):
        win = main_window
        _open(win, tmp_path, control_dict_text)
        original = _value_of(win, "application")

        _set_value(win, "application", "simpleFoam")
        _set_value(win, "application", "pisoFoam")

        win._tree_undo()
        assert _value_of(win, "application") == "simpleFoam"
        win._tree_undo()
        assert _value_of(win, "application") == original

    def test_rejected_edit_preserves_undo_and_redo(self, main_window, tmp_path, control_dict_text):
        """A rejected inline edit changes nothing, so it must leave the undo AND
        redo stacks untouched (regression: about_to_change fires before
        validation and used to clear the redo branch)."""
        win = main_window
        _open(win, tmp_path, control_dict_text)
        original = _value_of(win, "application")

        _set_value(win, "application", "simpleFoam")
        win._tree_undo()
        assert len(win.state.undo.redo_stack) == 1

        # Rejected edit: invalid scalar into a numeric cell, setData returns False.
        assert _set_value(win, "deltaT", "notanumber") is False

        # Redo history survived, and redo still works.
        assert len(win.state.undo.redo_stack) == 1
        assert win.state.undo.undo_stack == []
        win._tree_redo()
        assert _value_of(win, "application") == "simpleFoam"
        assert _value_of(win, "application") != original

    def test_value_unchanged_edit_pushes_nothing(self, main_window, tmp_path, control_dict_text):
        """Re-entering the identical value must not add an undo snapshot."""
        win = main_window
        _open(win, tmp_path, control_dict_text)
        _set_value(win, "application", "simpleFoam")
        assert len(win.state.undo.undo_stack) == 1

        _set_value(win, "application", "simpleFoam")  # no-op
        assert len(win.state.undo.undo_stack) == 1

    def test_undo_with_empty_stack_is_a_noop(self, main_window, tmp_path, control_dict_text):
        win = main_window
        _open(win, tmp_path, control_dict_text)
        before = win.editor_panel.get_text()
        win._tree_undo()
        assert win.editor_panel.get_text() == before


class TestFreeTextInteraction:
    def test_undo_after_unapplied_free_text_preserves_it_for_redo(
        self, main_window, tmp_path, control_dict_text
    ):
        """Typing free text in the editor without Apply, then undoing a prior
        tree edit, must not silently destroy the typed text: it is captured in
        the redo snapshot (regression: the snapshot used write_root(tree))."""
        win = main_window
        _open(win, tmp_path, control_dict_text)
        _set_value(win, "application", "simpleFoam")

        # Simulate unapplied free-text editing in the bottom editor.
        typed = win.editor_panel.get_text() + "\n// hand-typed note\n"
        win.editor_panel.set_text(typed)
        win._on_user_text_changed()
        assert win.state.source_lines_valid is False

        win._tree_undo()  # undoes the application edit
        assert _value_of(win, "application") != "simpleFoam"

        win._tree_redo()  # brings the free-text-bearing state back
        assert "hand-typed note" in win.editor_panel.get_text()


class TestCrudUndo:
    def test_delete_then_undo_restores_node(self, main_window, tmp_path, control_dict_text, monkeypatch):
        win = main_window
        _open(win, tmp_path, control_dict_text)
        root = win.state.current_root
        node = next(c for c in root.children if c.name == "application")

        from PySide6.QtWidgets import QMessageBox
        monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
        win._tree_delete(node)
        QApplication.processEvents()
        assert not any(c.name == "application" for c in win.state.current_root.children)

        win._tree_undo()
        assert any(c.name == "application" for c in win.state.current_root.children)

    def test_add_entry_then_undo_removes_it(self, main_window, tmp_path, control_dict_text):
        win = main_window
        _open(win, tmp_path, control_dict_text)
        node = next(c for c in win.state.current_root.children if c.name == "application")
        n_before = len(win.state.current_root.children)

        win._tree_add_entry_after(node)
        QApplication.processEvents()
        assert len(win.state.current_root.children) == n_before + 1

        win._tree_undo()
        assert len(win.state.current_root.children) == n_before

    def test_explicit_op_does_not_double_checkpoint(self, main_window, tmp_path, control_dict_text):
        """One CRUD op = one snapshot: the setData signal inside the same op
        must not add a second (which would make undo a two-step affair)."""
        win = main_window
        _open(win, tmp_path, control_dict_text)
        node = next(c for c in win.state.current_root.children if c.name == "application")

        win._tree_duplicate(node)
        QApplication.processEvents()
        assert len(win.state.undo.undo_stack) == 1


class TestMultiFileUndo:
    def test_multi_file_snapshot_restores_all_files(self, main_window, tmp_path, control_dict_text):
        win = main_window
        dict_path = _open(win, tmp_path, control_dict_text)
        other = tmp_path / "system" / "fvSchemes"
        other.write_text("ddtSchemes { default Euler; }\n", encoding="utf-8")
        other_path = str(other)
        win._cache_parsed_root(other_path)

        # Mimic a boundary-style multi-file operation: checkpoint both files,
        # then mutate both buffers/roots directly.
        win._checkpoint_for_undo([dict_path, other_path])
        _set_value(win, "application", "simpleFoam")
        win.state.file_buffers[other_path] = "ddtSchemes { default backward; }\n"
        win.state.file_dirty[other_path] = True
        QApplication.processEvents()

        win._tree_undo()

        assert _value_of(win, "application") != "simpleFoam"
        assert "Euler" in win.state.file_buffers[other_path]
        assert win.state.file_dirty[other_path] is False

    def test_undo_of_non_current_file_switches_view(self, main_window, tmp_path, control_dict_text):
        """A checkpoint on a file that is not on screen is still reachable from
        any view, and undo switches to the affected file so the change shows
        (regression: snapshots were keyed by the current file and unreachable)."""
        win = main_window
        dict_path = _open(win, tmp_path, control_dict_text)
        other = tmp_path / "system" / "fvSchemes"
        other.write_text("ddtSchemes { default Euler; }\n", encoding="utf-8")
        other_path = str(other)
        win.state.file_buffers[other_path] = other.read_text()
        win.state.file_dirty[other_path] = False

        # Simulate an op that edits only the non-current file.
        win._checkpoint_for_undo([other_path])
        win.state.file_buffers[other_path] = "ddtSchemes { default backward; }\n"
        win.state.file_dirty[other_path] = True

        assert win.state.current_file == dict_path
        win._tree_undo()

        # Reachable from the controlDict view, restored, and now shown.
        assert "Euler" in win.state.file_buffers[other_path]
        assert win.state.current_file == other_path


class TestStackLifecycle:
    def test_stacks_cleared_on_case_reload(self, main_window, tmp_path, control_dict_text):
        win = main_window
        _open(win, tmp_path, control_dict_text)
        _set_value(win, "application", "simpleFoam")
        assert win.state.undo.undo_stack

        win._load_case_dir(str(tmp_path))
        assert win.state.undo.undo_stack == []
        assert win.state.undo.redo_stack == []

    def test_depth_cap(self, main_window, tmp_path, control_dict_text, monkeypatch):
        import ui.mixins._undo_ops as undo_ops
        monkeypatch.setattr(undo_ops, "_UNDO_DEPTH", 3)
        win = main_window
        _open(win, tmp_path, control_dict_text)

        for i in range(6):
            _set_value(win, "application", f"solver{i}")

        assert len(win.state.undo.undo_stack) == 3
