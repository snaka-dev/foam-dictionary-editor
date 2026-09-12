# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for model/case_tree_model.py.

Covers lazy population via canFetchMore/fetchMore, the "do not descend into a
case" rule that is this model's reason for existing rather than being a
QFileSystemModel (see CASE_BROWSER_PLAN.md), display roles (the CASE_MARKER
glyph, the injected describe() tooltip, the open-case bold font), path/index
navigation, and refresh-from-disk. No QApplication is needed for most of this
model (it holds no widgets and QColor/dataclass lookups don't need one); the
two FontRole tests request pytest-qt's qapp defensively since they are the
only place here constructing a QFont.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QModelIndex, Qt

from model.case_tree_model import CASE_MARKER, CaseTreeModel
from services.case_scan import DirEntry

# ── fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def case_tree(tmp_path: Path) -> Path:
    """A directory tree exercising every DirEntry classification the model must handle.

    Names are chosen so case-sensitive ASCII order ('Beta' < 'alpha' < 'delta_empty'
    < 'gamma_plain') differs from the case-insensitive order the model must produce.
    """
    root = tmp_path / "root"

    case_with_both = root / "Beta"
    (case_with_both / "system").mkdir(parents=True)
    (case_with_both / "constant").mkdir()

    case_constant_only = root / "alpha"
    (case_constant_only / "constant").mkdir(parents=True)

    plain_with_subdir = root / "gamma_plain"
    (plain_with_subdir / "child").mkdir(parents=True)

    empty_dir = root / "delta_empty"
    empty_dir.mkdir(parents=True)

    (root / "loose.txt").write_text("not a directory")

    return root


@pytest.fixture
def model(case_tree: Path) -> CaseTreeModel:
    """A model rooted at case_tree, nothing fetched yet."""
    m = CaseTreeModel()
    m.set_root(case_tree)
    return m


def _fetch_root(model: CaseTreeModel) -> None:
    model.fetchMore(QModelIndex())


def _child_index(
    model: CaseTreeModel, name: str, parent: QModelIndex = QModelIndex()
) -> QModelIndex:
    """Find the row under *parent* whose entry name is *name*, fetching first if needed."""
    if model.canFetchMore(parent):
        model.fetchMore(parent)
    for row in range(model.rowCount(parent)):
        index = model.index(row, 0, parent)
        entry = model.entry_for_index(index)
        if entry is not None and entry.name == name:
            return index
    raise AssertionError(f"no child named {name!r} under {parent}")


# ── population and laziness ─────────────────────────────────────────────────


class TestPopulationAndLaziness:
    def test_row_count_zero_before_fetch(self, model: CaseTreeModel) -> None:
        assert model.rowCount() == 0

    def test_can_fetch_more_true_before_fetch(self, model: CaseTreeModel) -> None:
        assert model.canFetchMore(QModelIndex()) is True

    def test_fetch_more_populates_top_level_subdirectories(self, model: CaseTreeModel) -> None:
        _fetch_root(model)
        names = {model.entry_for_index(model.index(row, 0)).name for row in range(model.rowCount())}
        assert names == {"Beta", "alpha", "gamma_plain", "delta_empty"}

    def test_loose_files_are_never_rows(self, model: CaseTreeModel) -> None:
        _fetch_root(model)
        names = [model.entry_for_index(model.index(row, 0)).name for row in range(model.rowCount())]
        assert "loose.txt" not in names
        assert model.rowCount() == 4

    def test_rows_sorted_case_insensitively(self, model: CaseTreeModel) -> None:
        _fetch_root(model)
        names = [model.entry_for_index(model.index(row, 0)).name for row in range(model.rowCount())]
        assert names == ["alpha", "Beta", "delta_empty", "gamma_plain"]


# ── the "do not descend into a case" rule ───────────────────────────────────


class TestDoNotDescendIntoCase:
    def test_has_children_false_for_a_case_with_system_and_constant(self, model: CaseTreeModel) -> None:
        beta_index = _child_index(model, "Beta")
        assert model.hasChildren(beta_index) is False

    def test_has_children_false_for_a_case_with_constant_only(self, model: CaseTreeModel) -> None:
        alpha_index = _child_index(model, "alpha")
        assert model.hasChildren(alpha_index) is False

    def test_can_fetch_more_false_for_a_case(self, model: CaseTreeModel) -> None:
        beta_index = _child_index(model, "Beta")
        assert model.canFetchMore(beta_index) is False

    def test_has_children_true_for_a_plain_directory_with_a_subdirectory(
        self, model: CaseTreeModel
    ) -> None:
        plain_index = _child_index(model, "gamma_plain")
        assert model.hasChildren(plain_index) is True

    def test_has_children_false_for_an_empty_directory(self, model: CaseTreeModel) -> None:
        empty_index = _child_index(model, "delta_empty")
        assert model.hasChildren(empty_index) is False

    def test_descend_override_true_makes_a_case_expandable(
        self, model: CaseTreeModel, case_tree: Path
    ) -> None:
        beta_path = case_tree / "Beta"
        model.set_descend_override(beta_path, True)
        beta_index = model.index_for_path(beta_path)
        assert model.hasChildren(beta_index) is True
        # set_descend_override() calls refresh(), which eagerly fetches when
        # canFetchMore() is now true as a side effect of the override -- so
        # the children are already populated by the time we get here.
        assert model.canFetchMore(beta_index) is False
        names = {
            model.entry_for_index(model.index(row, 0, beta_index)).name
            for row in range(model.rowCount(beta_index))
        }
        assert names == {"system", "constant"}

    def test_descend_override_false_reverses_it(self, model: CaseTreeModel, case_tree: Path) -> None:
        beta_path = case_tree / "Beta"
        model.set_descend_override(beta_path, True)
        beta_index = model.index_for_path(beta_path)
        model.fetchMore(beta_index)

        model.set_descend_override(beta_path, False)
        beta_index = model.index_for_path(beta_path)
        assert model.hasChildren(beta_index) is False
        assert model.rowCount(beta_index) == 0


# ── display ──────────────────────────────────────────────────────────────────


class TestDisplay:
    def test_display_role_for_a_case_uses_the_marker(self, model: CaseTreeModel) -> None:
        beta_index = _child_index(model, "Beta")
        assert model.data(beta_index, Qt.ItemDataRole.DisplayRole) == f"{CASE_MARKER}Beta"

    def test_display_role_for_a_plain_directory_is_the_bare_name(self, model: CaseTreeModel) -> None:
        plain_index = _child_index(model, "gamma_plain")
        assert model.data(plain_index, Qt.ItemDataRole.DisplayRole) == "gamma_plain"

    def test_entry_role_returns_the_dir_entry(self, model: CaseTreeModel, case_tree: Path) -> None:
        beta_index = _child_index(model, "Beta")
        entry = model.data(beta_index, CaseTreeModel.ENTRY_ROLE)
        assert isinstance(entry, DirEntry)
        assert entry.path == case_tree / "Beta"
        assert entry.is_case is True

    def test_font_role_bold_only_for_the_open_case(
        self, qapp, model: CaseTreeModel, case_tree: Path
    ) -> None:
        beta_path = case_tree / "Beta"
        model.set_open_case(str(beta_path))
        beta_index = _child_index(model, "Beta")
        alpha_index = _child_index(model, "alpha")

        beta_font = model.data(beta_index, Qt.ItemDataRole.FontRole)
        assert beta_font is not None
        assert beta_font.bold() is True
        assert model.data(alpha_index, Qt.ItemDataRole.FontRole) is None

    def test_font_role_moves_when_the_open_case_changes(
        self, qapp, model: CaseTreeModel, case_tree: Path
    ) -> None:
        beta_index = _child_index(model, "Beta")
        alpha_index = _child_index(model, "alpha")

        model.set_open_case(str(case_tree / "Beta"))
        assert model.data(beta_index, Qt.ItemDataRole.FontRole) is not None
        assert model.data(alpha_index, Qt.ItemDataRole.FontRole) is None

        model.set_open_case(str(case_tree / "alpha"))
        assert model.data(beta_index, Qt.ItemDataRole.FontRole) is None
        assert model.data(alpha_index, Qt.ItemDataRole.FontRole) is not None

    def test_tooltip_role_defaults_to_str_path(self, model: CaseTreeModel, case_tree: Path) -> None:
        beta_index = _child_index(model, "Beta")
        assert model.data(beta_index, Qt.ItemDataRole.ToolTipRole) == str(case_tree / "Beta")

    def test_tooltip_role_uses_injected_describe(self, case_tree: Path) -> None:
        m = CaseTreeModel(describe=lambda entry: f"described:{entry.name}")
        m.set_root(case_tree)
        beta_index = _child_index(m, "Beta")
        assert m.data(beta_index, Qt.ItemDataRole.ToolTipRole) == "described:Beta"


# ── navigation ───────────────────────────────────────────────────────────────


class TestNavigation:
    def test_index_for_path_resolves_a_deep_path_fetching_on_the_way(
        self, model: CaseTreeModel, case_tree: Path
    ) -> None:
        deep = case_tree / "gamma_plain" / "child"
        index = model.index_for_path(deep)
        assert index.isValid()
        assert model.entry_for_index(index).name == "child"

    def test_index_for_path_on_the_root_itself_is_invalid(
        self, model: CaseTreeModel, case_tree: Path
    ) -> None:
        assert model.index_for_path(case_tree).isValid() is False

    def test_index_for_path_outside_root_is_invalid(self, model: CaseTreeModel, tmp_path: Path) -> None:
        outside = tmp_path / "elsewhere"
        outside.mkdir()
        assert model.index_for_path(outside).isValid() is False

    def test_path_for_index_round_trips(self, model: CaseTreeModel, case_tree: Path) -> None:
        beta_path = case_tree / "Beta"
        index = model.index_for_path(beta_path)
        assert model.path_for_index(index) == beta_path

    def test_path_for_index_on_root_returns_root_path(
        self, model: CaseTreeModel, case_tree: Path
    ) -> None:
        assert model.path_for_index(QModelIndex()) == case_tree

    def test_parent_returns_the_correct_parent_index(
        self, model: CaseTreeModel, case_tree: Path
    ) -> None:
        deep = case_tree / "gamma_plain" / "child"
        child_index = model.index_for_path(deep)
        parent_index = model.parent(child_index)
        assert model.entry_for_index(parent_index).name == "gamma_plain"

    def test_parent_of_a_top_level_row_is_invalid(self, model: CaseTreeModel) -> None:
        plain_index = _child_index(model, "gamma_plain")
        assert model.parent(plain_index).isValid() is False

    def test_entry_for_index_on_invalid_index_is_none(self, model: CaseTreeModel) -> None:
        assert model.entry_for_index(QModelIndex()) is None


# ── refresh ──────────────────────────────────────────────────────────────────


class TestRefresh:
    def test_refresh_picks_up_a_newly_created_directory(
        self, model: CaseTreeModel, case_tree: Path
    ) -> None:
        _fetch_root(model)
        (case_tree / "new_case").mkdir()
        model.refresh()
        names = {model.entry_for_index(model.index(row, 0)).name for row in range(model.rowCount())}
        assert "new_case" in names

    def test_refresh_drops_a_deleted_directory(self, model: CaseTreeModel, case_tree: Path) -> None:
        _fetch_root(model)
        import shutil

        shutil.rmtree(case_tree / "delta_empty")
        model.refresh()
        names = {model.entry_for_index(model.index(row, 0)).name for row in range(model.rowCount())}
        assert "delta_empty" not in names

    def test_set_root_replaces_contents(self, model: CaseTreeModel, tmp_path: Path) -> None:
        _fetch_root(model)
        other_root = tmp_path / "other"
        (other_root / "only_child").mkdir(parents=True)

        model.set_root(other_root)
        assert model.rowCount() == 0
        _fetch_root(model)
        names = {model.entry_for_index(model.index(row, 0)).name for row in range(model.rowCount())}
        assert names == {"only_child"}


# ── edge cases ───────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_nonexistent_root_does_not_raise(self, tmp_path: Path) -> None:
        m = CaseTreeModel()
        m.set_root(tmp_path / "does_not_exist")
        m.fetchMore(QModelIndex())
        assert m.rowCount() == 0

    def test_empty_root_yields_no_rows(self, tmp_path: Path) -> None:
        empty_root = tmp_path / "empty_root"
        empty_root.mkdir()
        m = CaseTreeModel()
        m.set_root(empty_root)
        m.fetchMore(QModelIndex())
        assert m.rowCount() == 0

    def test_rootless_model_reports_no_children(self) -> None:
        """A CaseTreeModel with no set_root() call yet.

        This pins the fix for a real bug found while writing this file: before
        the fix, hasChildren(QModelIndex()) returned True unconditionally for
        the root node (even with no DirEntry set), so canFetchMore() promised
        children that fetchMore() would then have to go and get. hasChildren()
        now returns False whenever the node has no entry, closing that gap.
        """
        m = CaseTreeModel()
        assert m.rowCount() == 0
        assert m.hasChildren(QModelIndex()) is False
        assert m.canFetchMore(QModelIndex()) is False

    def test_rootless_model_fetch_more_does_not_raise(self) -> None:
        """fetchMore carries the same has-an-entry guard as hasChildren.

        A caller that reaches fetchMore without asking canFetchMore first --
        and QTreeView does exactly that in some paths -- must get a no-op
        rather than the AssertionError _Node.path would otherwise raise.
        """
        m = CaseTreeModel()
        m.fetchMore(QModelIndex())
        assert m.rowCount() == 0
