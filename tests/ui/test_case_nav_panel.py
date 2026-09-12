# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for ui/panels/case_nav_panel.py and its ui/case_navigation.py controller.

Covers the Cases tab in isolation, without a MainWindow: set_location re-rooting
and the Up button's filesystem-root floor, the double-click open-vs-descend
split, every navigator signal the context menu can raise, location persistence
through app_config (CaseNavigator.go_to / initial_location), and long case
names eliding instead of growing a horizontal scrollbar.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QModelIndex

from app_config import get_app_config
from i18n import tr
from ui.case_navigation import CaseNavigator
from ui.panels.case_nav_panel import CaseNavPanel


@pytest.fixture
def navigator(qapp):
    nav = CaseNavigator()
    yield nav
    nav.deleteLater()


@pytest.fixture
def panel(navigator, qapp):
    p = CaseNavPanel(navigator)
    yield p
    p.deleteLater()


@pytest.fixture
def sample_tree(tmp_path):
    """Two cases, a plain folder with a subdirectory, an empty dir, a loose file."""
    (tmp_path / "case1" / "system").mkdir(parents=True)
    (tmp_path / "case1" / "constant").mkdir()
    (tmp_path / "case2" / "constant").mkdir(parents=True)
    (tmp_path / "plain" / "sub").mkdir(parents=True)
    (tmp_path / "empty").mkdir()
    (tmp_path / "loose.txt").write_text("x", encoding="utf-8")
    return tmp_path


def _choose_context_menu_action(panel, index, label):
    """Build the context menu for *index* and run the action labelled *label*.

    Goes through _build_context_menu, which is split out of _on_context_menu
    for exactly this reason: QMenu.exec() blocks waiting for a mouse an
    offscreen test has no way to supply, and neither assigning over the QMenu
    class's exec nor swapping the module's QMenu for a subclass reliably
    intercepts it. The menu here is the real one -- same rows, same order,
    same handlers -- so the wiring between a row and the signal it raises is
    still what is under test; only the blocking half is left out.
    """
    menu, actions = panel._build_context_menu(index)
    action = next((act for act in menu.actions() if act.text() == label), None)
    assert action is not None, (
        f"no {label!r} row in the menu; rows were "
        f"{[a.text() for a in menu.actions() if not a.isSeparator()]}"
    )
    actions[action]()


# ── set_location ─────────────────────────────────────────────────────────────

class TestSetLocation:
    def test_reroots_the_view_and_sets_the_path_label(self, panel, navigator, sample_tree, qapp):
        navigator.go_to(sample_tree)
        qapp.processEvents()
        assert panel._tree.rootIndex() == navigator.model.index_for_path(sample_tree)
        assert panel._path_label.toolTip() == str(sample_tree)

    def test_up_button_disables_at_the_filesystem_root(self, panel, navigator, qapp):
        fs_root = navigator.model.root_path()
        assert fs_root is not None
        navigator.go_to(fs_root)
        qapp.processEvents()
        assert not panel._up_btn.isEnabled()

    def test_up_button_enabled_elsewhere(self, panel, navigator, sample_tree, qapp):
        navigator.go_to(sample_tree)
        qapp.processEvents()
        assert panel._up_btn.isEnabled()


# ── double click: open vs. descend ───────────────────────────────────────────

class TestDoubleClick:
    """_on_double_clicked is called directly with the index doubleClicked would
    carry -- a real double-click cannot be delivered to an offscreen widget."""

    def test_case_opens_and_does_not_descend(self, panel, navigator, sample_tree, qapp):
        navigator.go_to(sample_tree)
        qapp.processEvents()
        case1 = sample_tree / "case1"
        received: list[str] = []
        navigator.open_case_requested.connect(received.append)
        panel._on_double_clicked(navigator.model.index_for_path(case1))
        assert received == [str(case1)]
        assert navigator.current_dir == sample_tree

    def test_plain_folder_navigates_into_it(self, panel, navigator, sample_tree, qapp):
        navigator.go_to(sample_tree)
        qapp.processEvents()
        plain = sample_tree / "plain"
        received: list[str] = []
        navigator.location_changed.connect(received.append)
        panel._on_double_clicked(navigator.model.index_for_path(plain))
        assert received == [str(plain)]
        assert navigator.current_dir == plain


# ── context menu -> navigator signals ────────────────────────────────────────

class TestContextMenuSignals:
    def test_open_case(self, panel, navigator, sample_tree, qapp):
        navigator.go_to(sample_tree)
        qapp.processEvents()
        case1 = sample_tree / "case1"
        received: list[str] = []
        navigator.open_case_requested.connect(received.append)
        _choose_context_menu_action(
            panel, navigator.model.index_for_path(case1), tr("Open Case")
        )
        assert received == [str(case1)]

    def test_compare_with_case(self, panel, navigator, sample_tree, qapp):
        navigator.go_to(sample_tree)
        qapp.processEvents()
        case1 = sample_tree / "case1"
        received: list[str] = []
        navigator.compare_case_requested.connect(received.append)
        _choose_context_menu_action(
            panel, navigator.model.index_for_path(case1), tr("Compare with Case…")
        )
        assert received == [str(case1)]

    def test_duplicate_case(self, panel, navigator, sample_tree, qapp):
        navigator.go_to(sample_tree)
        qapp.processEvents()
        case1 = sample_tree / "case1"
        received: list[str] = []
        navigator.duplicate_case_requested.connect(received.append)
        _choose_context_menu_action(
            panel, navigator.model.index_for_path(case1), tr("Duplicate Case…")
        )
        assert received == [str(case1)]

    def test_rename(self, panel, navigator, sample_tree, qapp):
        navigator.go_to(sample_tree)
        qapp.processEvents()
        plain = sample_tree / "plain"
        received: list[str] = []
        navigator.rename_requested.connect(received.append)
        _choose_context_menu_action(
            panel, navigator.model.index_for_path(plain), tr("Rename…")
        )
        assert received == [str(plain)]

    def test_move(self, panel, navigator, sample_tree, qapp):
        navigator.go_to(sample_tree)
        qapp.processEvents()
        plain = sample_tree / "plain"
        received: list[str] = []
        navigator.move_requested.connect(received.append)
        _choose_context_menu_action(
            panel, navigator.model.index_for_path(plain), tr("Move…")
        )
        assert received == [str(plain)]

    def test_delete(self, panel, navigator, sample_tree, qapp):
        navigator.go_to(sample_tree)
        qapp.processEvents()
        plain = sample_tree / "plain"
        received: list[str] = []
        navigator.delete_requested.connect(received.append)
        _choose_context_menu_action(
            panel, navigator.model.index_for_path(plain), tr("Delete…")
        )
        assert received == [str(plain)]

    def test_new_folder(self, panel, navigator, sample_tree, qapp):
        navigator.go_to(sample_tree)
        qapp.processEvents()
        received: list[str] = []
        navigator.new_folder_requested.connect(received.append)
        # A right-click on empty space still offers New Folder, keyed off the
        # current directory rather than any particular row.
        _choose_context_menu_action(panel, QModelIndex(), tr("New Folder…"))
        assert received == [str(sample_tree)]


# ── location persistence ──────────────────────────────────────────────────────

class TestLocationPersistence:
    def test_go_to_writes_through_set_case_browser_dir(self, navigator, sample_tree, qapp):
        navigator.go_to(sample_tree)
        assert get_app_config().get_case_browser_dir() == str(sample_tree)

    def test_initial_location_returns_the_stored_location(self, sample_tree, qapp):
        get_app_config().set_case_browser_dir(str(sample_tree))
        fresh = CaseNavigator()
        try:
            assert fresh.initial_location() == sample_tree
        finally:
            fresh.deleteLater()

    def test_a_vanished_stored_location_falls_back_to_the_default_case_dir(self, tmp_path, qapp):
        get_app_config().set_case_browser_dir(str(tmp_path / "vanished"))
        default_dir = tmp_path / "default_case"
        default_dir.mkdir()
        get_app_config().set_default_case_dir(str(default_dir))
        fresh = CaseNavigator()
        try:
            assert fresh.initial_location() == default_dir
        finally:
            fresh.deleteLater()

    def test_vanished_stored_and_default_both_fall_back_to_home(self, tmp_path, qapp):
        get_app_config().set_case_browser_dir(str(tmp_path / "vanished"))
        get_app_config().set_default_case_dir(str(tmp_path / "also-gone"))
        fresh = CaseNavigator()
        try:
            assert fresh.initial_location() == Path.home()
        finally:
            fresh.deleteLater()


# ── long names elide rather than scrolling sideways ──────────────────────────
#
# Mirrors tests/ui/test_file_list_panel.py's TestLongPathsDoNotScrollSideways:
# turning the horizontal scrollbar off makes the view clamp and elide instead
# of truncating with no ellipsis, checked via the scrollbar's range rather than
# sizeHint(), which reports the same number whether or not anything overflowed.

_NARROW_WIDTH = 160


class TestLongNamesDoNotScrollSideways:
    def test_no_horizontal_scrollbar_at_narrow_width(self, panel, navigator, tmp_path, qapp):
        long_name = "a_very_long_openfoam_case_directory_name_that_cannot_possibly_fit"
        (tmp_path / long_name / "system").mkdir(parents=True)
        (tmp_path / long_name / "constant").mkdir()
        panel.resize(_NARROW_WIDTH, 300)
        panel.show()
        navigator.go_to(tmp_path)
        # The tree only recomputes its scrollbar range once it processes the
        # LayoutRequest queued by the fetchMore triggered from go_to.
        qapp.processEvents()
        assert panel._tree.horizontalScrollBar().maximum() == 0
