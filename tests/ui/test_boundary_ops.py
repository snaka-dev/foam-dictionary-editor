# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for ui/mixins/_boundary_ops.py -- the boundary editor's cross-file operations.

The panel's own copy helpers are covered by test_boundary_view_copy.py; the mixin driving
it was not covered at all (17% of its statements, measured), which is the wrong way round:
these are the operations that write *several* field files from one click, so a mistake
costs `0/U`, `0/p` and `0/k` together rather than one file the user is looking at.
"""
from __future__ import annotations

import pytest

U = """\
FoamFile { version 2.0; format ascii; class volVectorField; object U; }
dimensions [0 1 -1 0 0 0 0];
internalField uniform (0 0 0);
boundaryField
{
    inlet   { type fixedValue; value uniform (1 0 0); }
    outlet  { type zeroGradient; }
    walls   { type noSlip; }
}
"""
P = """\
FoamFile { version 2.0; format ascii; class volScalarField; object p; }
dimensions [0 2 -2 0 0 0 0];
internalField uniform 0;
boundaryField
{
    inlet   { type zeroGradient; }
    outlet  { type fixedValue; value uniform 0; }
    walls   { type zeroGradient; }
}
"""
# No `walls`: the add-all/delete-all counts must be about the files that actually
# have (or lack) the patch, not about every field file.
K = """\
FoamFile { version 2.0; format ascii; class volScalarField; object k; }
dimensions [0 2 -2 0 0 0 0];
internalField uniform 0.1;
boundaryField
{
    inlet   { type fixedValue; value uniform 0.1; }
    outlet  { type zeroGradient; }
}
"""


@pytest.fixture
def case(tmp_path):
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "controlDict").write_text(
        "FoamFile { version 2.0; format ascii; class dictionary; object controlDict; }\n"
        "application icoFoam;\n", encoding="utf-8")
    zero = tmp_path / "0"
    zero.mkdir()
    for name, text in (("U", U), ("p", P), ("k", K)):
        (zero / name).write_text(text, encoding="utf-8")
    return tmp_path


@pytest.fixture
def win(main_window, case, monkeypatch):
    """A window with the case loaded and confirmations answered Yes."""
    main_window._load_case_dir(str(case))
    monkeypatch.setattr(type(main_window), "_confirm", lambda self, *a, **k: True)
    return main_window


def _patches(win, name):
    from model.boundary_model import extract_boundary

    path = str(win.state.current_case_dir) + f"/0/{name}"
    return sorted(extract_boundary(win.state.parsed_roots[path]))


def _raw_patch_names(win, name):
    """Every boundaryField child, in order, duplicates included.

    `extract_boundary` returns a dict keyed by patch name, so a patch added twice
    collapses to one entry there -- which makes it exactly the wrong thing to count
    duplicates with. Verified: an add-all that forgot to skip files already holding the
    patch was invisible to a dict-based assertion.
    """
    path = str(win.state.current_case_dir) + f"/0/{name}"
    root = win.state.parsed_roots[path]
    bf = next(c for c in root.children if c.name == "boundaryField")
    return [c.name for c in bf.children if c.node_type == "dictionary"]


class TestAvailableFieldDirs:
    def test_it_finds_the_zero_directory(self, win):
        assert "0" in win._available_field_dirs()

    def test_an_empty_region_subdir_is_not_offered(self, win, case):
        # A directory with no files in it has no boundary fields to show.
        (case / "0" / "emptyRegion").mkdir()
        assert "0/emptyRegion" not in win._available_field_dirs()

    def test_a_region_subdir_with_fields_is_offered(self, win, case):
        region = case / "0" / "fluid"
        region.mkdir()
        (region / "U").write_text(U, encoding="utf-8")
        assert "0/fluid" in win._available_field_dirs()

    def test_no_case_means_no_dirs(self, main_window):
        main_window.state.current_case_dir = None
        assert main_window._available_field_dirs() == []


class TestDeleteFromEveryFile:
    def test_it_removes_the_patch_from_every_file_that_has_it(self, win):
        assert "walls" in _patches(win, "U")
        assert "walls" in _patches(win, "p")

        win._on_patch_delete_all_requested("walls")

        assert "walls" not in _patches(win, "U")
        assert "walls" not in _patches(win, "p")

    def test_the_other_patches_are_left_alone(self, win):
        win._on_patch_delete_all_requested("walls")
        assert _patches(win, "U") == ["inlet", "outlet"]

    def test_a_file_without_the_patch_is_untouched(self, win):
        before = _raw_patch_names(win, "k")
        win._on_patch_delete_all_requested("walls")
        assert _raw_patch_names(win, "k") == before

    def test_the_confirmation_names_only_the_files_that_have_the_patch(self, win, monkeypatch):
        # The count and the file list in the prompt are the only place the "affected"
        # set is observable -- the write loop skips a file with no matching patch either
        # way, so a too-wide set corrupts nothing but does ask the user to approve
        # deleting from files that have nothing to delete.
        seen: list[str] = []
        monkeypatch.setattr(
            type(win), "_confirm", lambda self, title, message: seen.append(message) or True
        )
        win._on_patch_delete_all_requested("walls")
        assert len(seen) == 1
        assert "2 file" in seen[0], seen[0]
        assert "U" in seen[0] and "p" in seen[0]
        assert "k" not in seen[0], seen[0]

    def test_an_unknown_patch_does_nothing(self, win):
        before = {n: _patches(win, n) for n in ("U", "p", "k")}
        win._on_patch_delete_all_requested("nosuchpatch")
        assert {n: _patches(win, n) for n in ("U", "p", "k")} == before

    def test_declining_the_confirmation_changes_nothing(self, win, monkeypatch):
        monkeypatch.setattr(type(win), "_confirm", lambda self, *a, **k: False)
        before = _patches(win, "U")
        win._on_patch_delete_all_requested("walls")
        assert _patches(win, "U") == before

    def test_the_files_are_marked_dirty_not_written(self, win, case):
        on_disk = (case / "0" / "U").read_text(encoding="utf-8")
        win._on_patch_delete_all_requested("walls")
        assert win.state.file_dirty[str(case / "0" / "U")] is True
        # Edits live in the buffer until the user saves, as everywhere else.
        assert (case / "0" / "U").read_text(encoding="utf-8") == on_disk

    def test_one_undo_restores_every_file_it_touched(self, win):
        win._on_patch_delete_all_requested("walls")
        assert "walls" not in _patches(win, "U")
        win._tree_undo()
        assert "walls" in _patches(win, "U")
        assert "walls" in _patches(win, "p")


class TestAddToEveryFile:
    def test_it_adds_the_patch_only_where_it_is_missing(self, win):
        assert "walls" not in _patches(win, "k")
        win._on_patch_add_all_requested("walls")
        assert "walls" in _patches(win, "k")

    def test_a_file_that_already_has_it_is_not_duplicated(self, win):
        # Counted off the raw child list, not extract_boundary's dict, which would hide
        # a second entry under the same key.
        win._on_patch_add_all_requested("walls")
        assert _raw_patch_names(win, "U").count("walls") == 1

    def test_a_patch_every_file_already_has_does_nothing(self, win, case):
        before = {n: _raw_patch_names(win, n) for n in ("U", "p", "k")}
        win._on_patch_add_all_requested("inlet")
        assert {n: _raw_patch_names(win, n) for n in ("U", "p", "k")} == before

    def test_declining_the_confirmation_changes_nothing(self, win, monkeypatch):
        monkeypatch.setattr(type(win), "_confirm", lambda self, *a, **k: False)
        win._on_patch_add_all_requested("walls")
        assert "walls" not in _patches(win, "k")

    def test_one_undo_restores_it(self, win):
        win._on_patch_add_all_requested("walls")
        assert "walls" in _patches(win, "k")
        win._tree_undo()
        assert "walls" not in _patches(win, "k")


class TestSingleFilePatchOps:
    """The one-file operations behind the boundary table's context menu."""

    def test_delete_removes_one_patch_from_one_file(self, win, case):
        win._on_patch_delete_requested(str(case / "0" / "U"), "walls")
        assert "walls" not in _patches(win, "U")
        assert "walls" in _patches(win, "p")   # the other files are not touched

    def test_create_adds_one_patch_to_one_file(self, win, case, monkeypatch, stub_dialog):
        stub_dialog("ui.mixins._boundary_ops.BoundaryEditDialog", new_dict_text="type slip;")
        before_p = _patches(win, "p")
        win._on_patch_create_requested(str(case / "0" / "k"), "walls")
        assert "walls" in _patches(win, "k")
        assert _patches(win, "p") == before_p   # only the named file is written

    def test_create_writes_the_dialog_content(self, win, case, monkeypatch, stub_dialog):
        stub_dialog("ui.mixins._boundary_ops.BoundaryEditDialog", new_dict_text="type slip;")
        win._on_patch_create_requested(str(case / "0" / "k"), "walls")
        assert "slip" in win.state.file_buffers[str(case / "0" / "k")]

    def test_a_cancelled_dialog_adds_nothing(self, win, case, stub_dialog):
        stub_dialog(
            "ui.mixins._boundary_ops.BoundaryEditDialog",
            accepted=False, new_dict_text="type slip;",
        )
        win._on_patch_create_requested(str(case / "0" / "k"), "walls")
        assert "walls" not in _patches(win, "k")

    def test_paste_replaces_a_patch_body(self, win, case):
        path = str(case / "0" / "U")
        win._on_patch_paste_requested(path, "walls", "type slip;")
        assert "slip" in win.state.file_buffers[path]
