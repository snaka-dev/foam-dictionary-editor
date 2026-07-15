# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""
Regression test for Tools > View Log Summary... (ui/mixins/_tools_ops.py).

QDialog.close() without Qt.WA_DeleteOnClose only hides the widget; it does not
destroy it. _on_view_log_summary_clicked() must account for that when reusing
the cached self._log_summary_dialog instance, or the dialog never reappears
after being closed once.
"""
from __future__ import annotations


def test_view_log_summary_reopens_after_being_closed(main_window, tmp_path):
    win = main_window
    win.state.current_case_dir = str(tmp_path)

    win._on_view_log_summary_clicked()
    dialog = win._log_summary_dialog
    assert dialog is not None
    assert dialog.isVisible() is True

    dialog.close()
    assert dialog.isVisible() is False

    win._on_view_log_summary_clicked()
    assert win._log_summary_dialog is dialog
    assert dialog.isVisible() is True


def test_view_log_summary_no_case_dir_is_a_no_op(main_window):
    win = main_window
    win.state.current_case_dir = None

    win._on_view_log_summary_clicked()
    assert win._log_summary_dialog is None


def test_view_log_summary_follows_case_switch(main_window, tmp_path):
    """An already-open dialog must re-point at a newly opened case immediately,
    not keep showing the case it was first opened for (ui/mixins/_file_ops.py's
    _load_case_dir is the single funnel every case-open path goes through)."""
    win = main_window

    case_a = tmp_path / "case_a"
    case_a.mkdir()
    (case_a / "log.blockMesh").write_text("Exec   : blockMesh\n")

    case_b = tmp_path / "case_b"
    case_b.mkdir()
    (case_b / "log.snappyHexMesh").write_text("Exec   : snappyHexMesh\n")

    win._load_case_dir(str(case_a))
    win._on_view_log_summary_clicked()
    dialog = win._log_summary_dialog
    assert dialog._file_edit.text() == str(case_a / "log.blockMesh")

    win._load_case_dir(str(case_b))
    assert win._log_summary_dialog is dialog
    assert dialog._file_edit.text() == str(case_b / "log.snappyHexMesh")


def test_view_log_summary_action_listed_in_view_and_tools_menus(main_window):
    """The same QAction is offered under both Tools (where it belongs, next to
    the run actions that produce the logs) and View (where users go looking
    for anything that starts with "View")."""
    from PySide6.QtWidgets import QMenu

    win = main_window
    menu_titles = {
        obj.title()
        for obj in win._view_log_summary_action.associatedObjects()
        if isinstance(obj, QMenu)
    }
    assert {"Tools", "View"} <= menu_titles
