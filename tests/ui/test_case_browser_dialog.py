# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for ui/dialogs/case_browser_dialog.py.

Covers the non-modal window setting (a real regression guard -- the dialog
sets it explicitly), the tree/list panes sharing one CaseTreeModel, the
double-click open-vs-descend split in the list pane, action-row enablement by
selection kind, and that the dialog and the compact Cases tab move together
because both are views over the same CaseNavigator.
"""
from __future__ import annotations

import pytest
from PySide6.QtCore import QItemSelectionModel, Qt

from ui.case_navigation import CaseNavigator
from ui.dialogs.case_browser_dialog import CaseBrowserDialog
from ui.panels.case_nav_panel import CaseNavPanel


@pytest.fixture
def navigator(qapp):
    nav = CaseNavigator()
    yield nav
    nav.deleteLater()


@pytest.fixture
def dialog(navigator, qapp):
    d = CaseBrowserDialog(navigator)
    yield d
    d.deleteLater()


@pytest.fixture
def sample_tree(tmp_path):
    (tmp_path / "case1" / "system").mkdir(parents=True)
    (tmp_path / "case1" / "constant").mkdir()
    (tmp_path / "plain").mkdir()
    return tmp_path


def _select_in_list(dialog, index):
    dialog._list.selectionModel().select(
        index,
        QItemSelectionModel.SelectionFlag.ClearAndSelect | QItemSelectionModel.SelectionFlag.Rows,
    )


# ── window modality ──────────────────────────────────────────────────────────

class TestNonModal:
    def test_window_modality_is_non_modal(self, dialog):
        assert dialog.windowModality() == Qt.WindowModality.NonModal


# ── shared model, tree-drives-navigation ─────────────────────────────────────

class TestSharedModel:
    def test_both_panes_share_one_model(self, dialog, navigator):
        assert dialog._tree.model() is navigator.model
        assert dialog._list.model() is navigator.model

    def test_clicking_a_tree_row_navigates(self, dialog, navigator, sample_tree, qapp):
        navigator.go_to(sample_tree)
        qapp.processEvents()
        plain = sample_tree / "plain"
        dialog._on_tree_clicked(navigator.model.index_for_path(plain))
        assert navigator.current_dir == plain

    def test_list_pane_is_rooted_at_the_current_location(self, dialog, navigator, sample_tree, qapp):
        navigator.go_to(sample_tree)
        qapp.processEvents()
        assert dialog._list.rootIndex() == navigator.model.index_for_path(sample_tree)


# ── list pane double click: open vs. descend ─────────────────────────────────

class TestListActivation:
    """_on_list_activated is called directly with the index doubleClicked would
    carry -- a real double-click cannot be delivered to an offscreen widget."""

    def test_double_click_case_emits_open_case_requested(self, dialog, navigator, sample_tree, qapp):
        navigator.go_to(sample_tree)
        qapp.processEvents()
        case1 = sample_tree / "case1"
        received: list[str] = []
        navigator.open_case_requested.connect(received.append)
        dialog._on_list_activated(navigator.model.index_for_path(case1))
        assert received == [str(case1)]

    def test_double_click_plain_folder_navigates(self, dialog, navigator, sample_tree, qapp):
        navigator.go_to(sample_tree)
        qapp.processEvents()
        plain = sample_tree / "plain"
        dialog._on_list_activated(navigator.model.index_for_path(plain))
        assert navigator.current_dir == plain


# ── action-row enablement ─────────────────────────────────────────────────────

class TestActionRowEnablement:
    def test_no_selection_disables_case_only_actions_but_new_folder_stays_enabled(
        self, dialog, navigator, sample_tree, qapp
    ):
        navigator.go_to(sample_tree)
        qapp.processEvents()
        dialog._update_actions()
        assert not dialog._open_btn.isEnabled()
        assert not dialog._compare_btn.isEnabled()
        assert not dialog._duplicate_btn.isEnabled()
        assert not dialog._move_btn.isEnabled()
        assert not dialog._rename_btn.isEnabled()
        assert not dialog._delete_btn.isEnabled()
        assert dialog._new_folder_btn.isEnabled()

    def test_selecting_a_case_enables_every_action(self, dialog, navigator, sample_tree, qapp):
        navigator.go_to(sample_tree)
        qapp.processEvents()
        _select_in_list(dialog, navigator.model.index_for_path(sample_tree / "case1"))
        assert dialog._open_btn.isEnabled()
        assert dialog._compare_btn.isEnabled()
        assert dialog._duplicate_btn.isEnabled()
        assert dialog._move_btn.isEnabled()
        assert dialog._rename_btn.isEnabled()
        assert dialog._delete_btn.isEnabled()

    def test_selecting_a_plain_folder_enables_only_move_rename_delete(
        self, dialog, navigator, sample_tree, qapp
    ):
        navigator.go_to(sample_tree)
        qapp.processEvents()
        _select_in_list(dialog, navigator.model.index_for_path(sample_tree / "plain"))
        assert not dialog._open_btn.isEnabled()
        assert not dialog._compare_btn.isEnabled()
        assert not dialog._duplicate_btn.isEnabled()
        assert dialog._move_btn.isEnabled()
        assert dialog._rename_btn.isEnabled()
        assert dialog._delete_btn.isEnabled()


# ── one navigator, two views ──────────────────────────────────────────────────

class TestSharedNavigatorMovesBothViews:
    def test_navigating_in_the_dialog_moves_the_cases_tab_too(self, navigator, sample_tree, qapp):
        panel = CaseNavPanel(navigator)
        dialog = CaseBrowserDialog(navigator)
        try:
            navigator.go_to(sample_tree)
            qapp.processEvents()
            plain = sample_tree / "plain"
            dialog._on_tree_clicked(navigator.model.index_for_path(plain))
            qapp.processEvents()
            assert dialog._path_label.text() == str(plain)
            assert panel._path_text == str(plain)
            assert panel._tree.rootIndex() == navigator.model.index_for_path(plain)
        finally:
            panel.deleteLater()
            dialog.deleteLater()
