# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for case_scan: directory-tree scanning for the Case Browser/Cases tab.

Covers is-a-case detection, directory-only listing, sort order, hidden-entry
filtering, unreadable/symlinked children, the case summary, and the
ancestors_to() chain builder — see CASE_BROWSER_PLAN.md for the feature this
supports.
"""
from __future__ import annotations

import os

import pytest

from services.case_scan import DirEntry, ancestors_to, case_summary, list_subdirectories


class TestListSubdirectoriesCaseDetection:
    def test_system_dir_makes_a_case(self, tmp_path):
        (tmp_path / "caseA" / "system").mkdir(parents=True)
        entries = list_subdirectories(tmp_path)
        assert entries == [
            DirEntry(
                path=tmp_path / "caseA",
                name="caseA",
                is_case=True,
                is_symlink=False,
                readable=True,
                has_subdirs=True,
            )
        ]

    def test_constant_dir_makes_a_case(self, tmp_path):
        (tmp_path / "caseB" / "constant").mkdir(parents=True)
        entries = list_subdirectories(tmp_path)
        assert entries[0].is_case is True

    def test_bare_directory_is_not_a_case(self, tmp_path):
        (tmp_path / "plain").mkdir()
        entries = list_subdirectories(tmp_path)
        assert entries[0].is_case is False


class TestListSubdirectoriesFiltering:
    def test_files_are_not_listed(self, tmp_path):
        (tmp_path / "aDir").mkdir()
        (tmp_path / "aFile.txt").write_text("hello", encoding="utf-8")
        entries = list_subdirectories(tmp_path)
        assert [e.name for e in entries] == ["aDir"]

    def test_sort_order_is_case_insensitive(self, tmp_path):
        for name in ("Charlie", "alpha", "Bravo"):
            (tmp_path / name).mkdir()
        entries = list_subdirectories(tmp_path)
        assert [e.name for e in entries] == ["alpha", "Bravo", "Charlie"]

    def test_hidden_directories_excluded_by_default(self, tmp_path):
        (tmp_path / ".hidden").mkdir()
        (tmp_path / "visible").mkdir()
        entries = list_subdirectories(tmp_path)
        assert [e.name for e in entries] == ["visible"]

    def test_hidden_directories_included_with_flag(self, tmp_path):
        (tmp_path / ".hidden").mkdir()
        (tmp_path / "visible").mkdir()
        entries = list_subdirectories(tmp_path, include_hidden=True)
        assert {e.name for e in entries} == {".hidden", "visible"}

    def test_empty_directory_returns_empty_list(self, tmp_path):
        assert list_subdirectories(tmp_path) == []

    def test_nonexistent_directory_returns_empty_list(self, tmp_path):
        assert list_subdirectories(tmp_path / "does_not_exist") == []


class TestListSubdirectoriesHasSubdirs:
    def test_true_when_child_directory_exists(self, tmp_path):
        (tmp_path / "outer" / "inner").mkdir(parents=True)
        entries = list_subdirectories(tmp_path)
        assert entries[0].has_subdirs is True

    def test_false_when_only_files_inside(self, tmp_path):
        outer = tmp_path / "outer"
        outer.mkdir()
        (outer / "leaf.txt").write_text("x", encoding="utf-8")
        entries = list_subdirectories(tmp_path)
        assert entries[0].has_subdirs is False

    def test_false_when_directory_is_empty(self, tmp_path):
        (tmp_path / "outer").mkdir()
        entries = list_subdirectories(tmp_path)
        assert entries[0].has_subdirs is False


class TestListSubdirectoriesSymlinksAndPermissions:
    def test_symlinked_directory_reported(self, tmp_path):
        target = tmp_path / "realDir"
        target.mkdir()
        link = tmp_path / "linkDir"
        link.symlink_to(target, target_is_directory=True)
        entries = list_subdirectories(tmp_path)
        by_name = {e.name: e for e in entries}
        assert by_name["linkDir"].is_symlink is True
        assert by_name["realDir"].is_symlink is False

    @pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory permission bits")
    def test_unreadable_child_still_listed_as_unreadable(self, tmp_path):
        locked = tmp_path / "locked"
        locked.mkdir()
        original_mode = locked.stat().st_mode
        locked.chmod(0o000)
        try:
            entries = list_subdirectories(tmp_path)
        finally:
            locked.chmod(original_mode)
        assert len(entries) == 1
        assert entries[0].name == "locked"
        assert entries[0].readable is False


class TestCaseSummary:
    def test_reports_time_dirs_and_mesh_info(self, tmp_path):
        (tmp_path / "system").mkdir()
        (tmp_path / "constant").mkdir()
        (tmp_path / "0").mkdir()
        (tmp_path / "1").mkdir()
        poly_mesh = tmp_path / "constant" / "polyMesh"
        poly_mesh.mkdir()
        (poly_mesh / "owner").write_text(
            'FoamFile\n{\n    note        "nPoints:9261  nCells:8000  '
            'nFaces:25200  nInternalFaces:22800";\n}\n',
            encoding="utf-8",
        )

        summary = case_summary(tmp_path)

        assert summary.time_dirs == ("1",)
        assert summary.has_system is True
        assert summary.has_constant is True
        assert summary.has_zero is True
        assert summary.mesh is not None
        assert summary.mesh.n_points == 9261
        assert summary.mesh.n_cells == 8000
        assert summary.mesh.n_faces == 25200

    def test_no_mesh_no_zero_dir(self, tmp_path):
        (tmp_path / "system").mkdir()
        summary = case_summary(tmp_path)
        assert summary.mesh is None
        assert summary.has_zero is False
        assert summary.has_constant is False
        assert summary.time_dirs == ()


class TestAncestorsTo:
    def test_chain_from_stop_to_path(self, tmp_path):
        c = tmp_path / "a" / "b" / "c"
        c.mkdir(parents=True)
        a = tmp_path / "a"
        b = tmp_path / "a" / "b"
        assert ancestors_to(c, stop=tmp_path) == [tmp_path, a, b, c]

    def test_path_equal_to_stop_returns_single_element(self, tmp_path):
        assert ancestors_to(tmp_path, stop=tmp_path) == [tmp_path]

    def test_without_stop_reaches_filesystem_root(self, tmp_path):
        chain = ancestors_to(tmp_path)
        assert str(chain[0]) == tmp_path.anchor
        assert chain[-1] == tmp_path

    def test_stop_not_an_ancestor_falls_back_to_root(self, tmp_path):
        c = tmp_path / "a" / "b"
        c.mkdir(parents=True)
        chain = ancestors_to(c, stop=None)
        chain_with_bad_stop = ancestors_to(c, stop=tmp_path / "unrelated_not_an_ancestor")
        assert chain == chain_with_bad_stop
        assert str(chain[0]) == tmp_path.anchor
