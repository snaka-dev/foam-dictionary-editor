# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import pytest
from model.file_list_model import FileListModel


@pytest.fixture()
def model():
    return FileListModel()


@pytest.fixture()
def case_dir(tmp_path):
    (tmp_path / "system").mkdir()
    (tmp_path / "constant").mkdir()
    (tmp_path / "0").mkdir()
    return str(tmp_path)


def _paths(case_dir, *rel):
    from pathlib import Path
    return [str(Path(case_dir) / r) for r in rel]


class TestLoad:
    def test_case_dir_stored(self, model, case_dir):
        model.load([], case_dir)
        assert model.case_dir == case_dir

    def test_clears_previous_state(self, model, case_dir):
        model.load(_paths(case_dir, "system/controlDict"), case_dir)
        model.mark_dirty(_paths(case_dir, "system/controlDict")[0], True)
        model.load([], case_dir)
        assert model.sorted_groups() == []
        path = _paths(case_dir, "system/controlDict")[0]
        assert not model.is_dirty(path)

    def test_no_case_dir(self, model):
        model.load(["a/b"], None)
        assert model.case_dir is None
        groups = model.sorted_groups()
        assert len(groups) == 1
        assert groups[0][0] == "a"


class TestSortedGroups:
    def test_groups_in_order(self, model, case_dir):
        paths = _paths(case_dir, "0/U", "system/controlDict", "constant/transportProperties")
        model.load(paths, case_dir)
        groups = model.sorted_groups()
        group_names = [g for g, _ in groups]
        assert group_names == ["system", "constant", "0"]

    def test_paths_sorted_within_group(self, model, case_dir):
        paths = _paths(case_dir, "system/fvSolution", "system/controlDict", "system/fvSchemes")
        model.load(paths, case_dir)
        groups = dict(model.sorted_groups())
        names = [__import__("pathlib").Path(p).name for p in groups["system"]]
        assert names == sorted(names)

    def test_empty_paths(self, model, case_dir):
        model.load([], case_dir)
        assert model.sorted_groups() == []


class TestDirtyState:
    def test_mark_and_query(self, model, case_dir):
        path = _paths(case_dir, "system/controlDict")[0]
        model.load([path], case_dir)
        assert not model.is_dirty(path)
        model.mark_dirty(path, True)
        assert model.is_dirty(path)
        model.mark_dirty(path, False)
        assert not model.is_dirty(path)

    def test_unknown_path_is_clean(self, model, case_dir):
        model.load([], case_dir)
        assert not model.is_dirty("/nonexistent/file")


class TestDiffState:
    def test_mark_and_query(self, model, case_dir):
        path = _paths(case_dir, "system/controlDict")[0]
        model.load([path], case_dir)
        assert model.diff_count(path) is None
        model.mark_diff(path, 3)
        assert model.diff_count(path) == 3

    def test_clear_diff_marks(self, model, case_dir):
        p1, p2 = _paths(case_dir, "system/controlDict", "system/fvSchemes")
        model.load([p1, p2], case_dir)
        model.mark_diff(p1, 2)
        model.mark_diff(p2, 0)
        model.clear_diff_marks()
        assert model.diff_count(p1) is None
        assert model.diff_count(p2) is None

    def test_unknown_path_returns_none(self, model, case_dir):
        model.load([], case_dir)
        assert model.diff_count("/nonexistent") is None


class TestExtraFiles:
    def test_is_extra_file(self, model, case_dir):
        path = _paths(case_dir, "system/myExtra")[0]
        model.load([path], case_dir, extra_files=["system/myExtra"])
        assert model.is_extra_file(path)

    def test_non_extra_file(self, model, case_dir):
        path = _paths(case_dir, "system/controlDict")[0]
        model.load([path], case_dir, extra_files=[])
        assert not model.is_extra_file(path)

    def test_is_extra_dir(self, model, case_dir):
        model.load([], case_dir, extra_dirs=["myRegion"])
        assert model.is_extra_dir("myRegion")
        assert not model.is_extra_dir("system")

    def test_extra_counts(self, model, case_dir):
        path = _paths(case_dir, "system/myExtra")[0]
        model.load([path], case_dir, extra_files=["system/myExtra"], extra_dirs=["r1", "r2"])
        assert model.extra_file_count == 1
        assert model.extra_dir_count == 2


class TestClear:
    def test_clear_resets_all(self, model, case_dir):
        path = _paths(case_dir, "system/controlDict")[0]
        model.load([path], case_dir, extra_files=["system/controlDict"], extra_dirs=["myDir"])
        model.mark_dirty(path, True)
        model.mark_diff(path, 5)
        model.clear()
        assert model.case_dir is None
        assert model.sorted_groups() == []
        assert not model.is_dirty(path)
        assert model.diff_count(path) is None
        assert model.extra_file_count == 0
        assert model.extra_dir_count == 0
