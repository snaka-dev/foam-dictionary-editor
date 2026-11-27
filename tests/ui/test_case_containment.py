# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Writes stay inside the case, through the real window's handlers.

Each test opens a case holding a symlink or a climbing ``#include`` that
leads to ``outside/``, the stand-in for the rest of the user's disk, does
what a user would, and checks that ``outside/`` is unchanged. The
containment rules themselves are tested in ``tests/services/test_case_paths.py``.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from PySide6.QtWidgets import QMessageBox

CONTROL_DICT = (
    "FoamFile { version 2.0; format ascii; class dictionary; object controlDict; }\n"
    "application icoFoam;\nendTime 1;\n"
)
SECRET = "FoamFile { object fvSolution; }\nsecret 1;\n"


@pytest.fixture
def layout(tmp_path):
    case = tmp_path / "case"
    (case / "system").mkdir(parents=True)
    (case / "system" / "controlDict").write_text(CONTROL_DICT, encoding="utf-8")
    (case / "0.orig").mkdir()
    outside = tmp_path / "outside"
    (outside / "dir").mkdir(parents=True)
    (outside / "secret").write_text(SECRET, encoding="utf-8")
    (outside / "dir" / "f").write_text(SECRET, encoding="utf-8")
    (outside / "dir" / "f.bak_20260101_000000").write_text(SECRET, encoding="utf-8")
    return case, outside


def _open(main_window, case, monkeypatch):
    main_window._load_case_dir(str(case))
    monkeypatch.setattr(type(main_window), "_error", lambda self, *a, **k: None)
    return main_window


def _untouched(outside: Path) -> None:
    assert (outside / "secret").read_text(encoding="utf-8") == SECRET
    assert (outside / "dir" / "f").read_text(encoding="utf-8") == SECRET
    assert sorted(p.name for p in outside.rglob("*")) == [
        "dir", "f", "f.bak_20260101_000000", "secret",
    ]


def _edit(win, path: str, text: str) -> None:
    """Make *path*'s buffer dirty, as an edit would, without going through the editor."""
    win.state.file_buffers[path] = text
    win.state.file_dirty[path] = True


class TestReadOnlyClassification:
    def test_linked_files_are_read_only(self, main_window, layout, monkeypatch):
        case, outside = layout
        (case / "system" / "fvSolution").symlink_to(outside / "secret")
        (case / "linkdir").symlink_to(outside / "dir")
        (case / ".foam-editor-files.json").write_text(
            '{"extra_files": ["linkdir/f"]}', encoding="utf-8"
        )
        win = _open(main_window, case, monkeypatch)
        ro = win.state.read_only_files
        assert str(case / "system" / "fvSolution") in ro
        assert str(case / "linkdir" / "f") in ro
        assert str(case / "system" / "controlDict") not in ro
        # The file list shows it read-only, which offers only Copy into case.
        assert win.file_list_panel._model.is_read_only(str(case / "system" / "fvSolution"))

    def test_a_climbing_include_is_read_only_without_any_link(
        self, main_window, layout, monkeypatch
    ):
        case, _ = layout
        (case / "system" / "controlDict").write_text(
            CONTROL_DICT + '#include "../../outside/secret"\n', encoding="utf-8"
        )
        win = _open(main_window, case, monkeypatch)
        ro = win.state.read_only_files
        assert any(p.endswith("outside/secret") and ".." in p for p in ro)


class TestSave:
    def test_save_refuses_a_linked_file_and_keeps_it_dirty(
        self, main_window, layout, monkeypatch
    ):
        case, outside = layout
        link = case / "system" / "fvSolution"
        link.symlink_to(outside / "secret")
        win = _open(main_window, case, monkeypatch)
        # Even if the read-only set were bypassed, the save-time check refuses.
        win.state.read_only_files.clear()
        win.load_selected_file(str(link))
        win.editor_panel.set_text("changed 1;\n")
        win.state.text_dirty = True
        win.save_file()
        _untouched(outside)
        assert win.state.text_dirty

    def test_save_case_refuses_outside_files_and_names_them(
        self, main_window, layout, monkeypatch, answer_message_box
    ):
        case, outside = layout
        (case / "linkdir").symlink_to(outside / "dir")
        win = _open(main_window, case, monkeypatch)
        good = str(case / "system" / "controlDict")
        bad = str(case / "linkdir" / "f")
        _edit(win, good, CONTROL_DICT + "// edited\n")
        _edit(win, bad, "changed 1;\n")
        win.state.read_only_files.clear()  # as if the list predated the link
        monkeypatch.setattr(type(win), "_dirty_paths", lambda self: [good, bad])
        told = answer_message_box(QMessageBox.StandardButton.Ok)
        win.save_all_files()
        _untouched(outside)
        assert "// edited" in Path(good).read_text(encoding="utf-8")
        assert win.state.file_dirty[bad] is True
        assert told and "f" in told[0]

    def test_a_link_changed_after_the_list_loaded_is_caught_at_save(
        self, main_window, layout, monkeypatch
    ):
        case, outside = layout
        target = case / "system" / "fvSchemes"
        target.write_text("FoamFile { object fvSchemes; }\n", encoding="utf-8")
        win = _open(main_window, case, monkeypatch)
        win.load_selected_file(str(target))
        assert str(target) not in win.state.read_only_files
        target.unlink()
        target.symlink_to(outside / "secret")
        win.editor_panel.set_text("changed 1;\n")
        win.state.text_dirty = True
        win.save_file()
        _untouched(outside)

    def test_a_contained_include_with_dot_dot_still_saves(
        self, main_window, layout, monkeypatch
    ):
        case, _ = layout
        (case / "constant").mkdir()
        params = case / "constant" / "params"
        params.write_text("a 1;\n", encoding="utf-8")
        (case / "system" / "controlDict").write_text(
            CONTROL_DICT + '#include "../constant/params"\n', encoding="utf-8"
        )
        win = _open(main_window, case, monkeypatch)
        assert not any(p.endswith("params") for p in win.state.read_only_files)


class TestCreateAndDelete:
    def test_new_file_in_a_linked_directory_is_refused(self, main_window, layout, monkeypatch):
        case, outside = layout
        (case / "linkdir").symlink_to(outside / "dir")
        win = _open(main_window, case, monkeypatch)
        monkeypatch.setattr(
            type(win), "_prompt_new_filename", lambda self, *a, **k: case / "linkdir" / "new"
        )
        win._on_create_file_requested(str(case), "linkdir")
        _untouched(outside)

    def test_new_file_over_a_dangling_link_is_refused(self, main_window, layout, monkeypatch):
        case, outside = layout
        (case / "system" / "new").symlink_to(outside / "created")
        win = _open(main_window, case, monkeypatch)
        monkeypatch.setattr(
            type(win), "_prompt_new_filename", lambda self, *a, **k: case / "system" / "new"
        )
        win._on_create_file_requested(str(case), "system")
        _untouched(outside)

    def test_new_file_with_missing_parents_still_works(self, main_window, layout, monkeypatch):
        case, _ = layout
        win = _open(main_window, case, monkeypatch)
        target = case / "constant" / "deep" / "myDict"
        monkeypatch.setattr(type(win), "_prompt_new_filename", lambda self, *a, **k: target)
        win._on_create_file_requested(str(case), "constant/deep")
        assert target.is_file()

    def test_backup_of_a_file_in_a_linked_directory_is_refused(
        self, main_window, layout, monkeypatch
    ):
        case, outside = layout
        (case / "linkdir").symlink_to(outside / "dir")
        win = _open(main_window, case, monkeypatch)
        win.state.read_only_files.clear()
        assert win._create_backup(str(case / "linkdir" / "f")) is False
        _untouched(outside)

    def test_gzip_backup_and_duplicate_keep_their_format(self, main_window, layout, monkeypatch):
        import gzip

        from foam.utils import write_foam_file

        case, _ = layout
        (case / "0").mkdir()
        u = case / "0" / "U.gz"
        write_foam_file(u, "FoamFile { object U; }\n")
        win = _open(main_window, case, monkeypatch)
        assert win._create_backup(str(u)) is True
        backup = next((case / "0").glob("U.gz.bak_*"))
        assert gzip.decompress(backup.read_bytes()).startswith(b"FoamFile")

    def test_delete_of_a_file_under_a_linked_directory_is_refused(
        self, main_window, layout, monkeypatch
    ):
        case, outside = layout
        (case / "linkdir").symlink_to(outside / "dir")
        win = _open(main_window, case, monkeypatch)
        win.state.read_only_files.clear()
        monkeypatch.setattr(QMessageBox, "exec", lambda self: 0)
        monkeypatch.setattr(
            QMessageBox, "clickedButton",
            lambda self: next(b for b in self.buttons() if b.text().replace("&", "") == "Delete"),
        )
        win._on_delete_file_requested(str(case / "linkdir" / "f"))
        _untouched(outside)

    def test_deleting_a_linked_row_removes_only_the_link(self, main_window, layout, monkeypatch):
        case, outside = layout
        link = case / "system" / "fvSolution"
        link.symlink_to(outside / "secret")
        win = _open(main_window, case, monkeypatch)
        win.state.read_only_files.clear()
        monkeypatch.setattr(QMessageBox, "exec", lambda self: 0)
        monkeypatch.setattr(
            QMessageBox, "clickedButton",
            lambda self: next(b for b in self.buttons() if b.text().replace("&", "") == "Delete"),
        )
        win._on_delete_file_requested(str(link))
        assert not os.path.lexists(link)
        _untouched(outside)

    def test_delete_directory_refuses_a_linked_directory(
        self, main_window, layout, monkeypatch, answer_message_box
    ):
        case, outside = layout
        (case / "0").symlink_to(outside / "dir")
        win = _open(main_window, case, monkeypatch)
        answer_message_box(QMessageBox.StandardButton.Yes)
        win._on_delete_dir_requested(str(case), "0")
        _untouched(outside)

    def test_clean_backups_skips_a_backup_under_a_linked_directory(
        self, main_window, layout, monkeypatch, stub_dialog, answer_message_box
    ):
        case, outside = layout
        (case / "linkdir").symlink_to(outside / "dir")
        win = _open(main_window, case, monkeypatch)
        stub_dialog("ui.mixins._file_mgmt_ops.CleanBackupsDialog",
                    paths_to_delete=[str(case / "linkdir" / "f.bak_20260101_000000")])
        answer_message_box(QMessageBox.StandardButton.Ok)
        win._on_clean_backups()
        _untouched(outside)

    def test_duplicate_directory_keeps_links_and_refuses_a_linked_source(
        self, main_window, layout, monkeypatch
    ):
        case, outside = layout
        (case / "0.orig" / "U").write_text("FoamFile { object U; }\n", encoding="utf-8")
        (case / "0.orig" / "p").symlink_to(outside / "secret")
        (case / "linkdir").symlink_to(outside / "dir")
        win = _open(main_window, case, monkeypatch)
        monkeypatch.setattr(type(win), "_confirm", lambda self, *a, **k: True)
        win._on_duplicate_dir_requested(str(case), "0.orig", "0")
        assert (case / "0" / "p").is_symlink()  # a link, not a copy of the contents
        win._on_duplicate_dir_requested(str(case), "linkdir", "copied")
        assert not (case / "copied").exists()
        _untouched(outside)


class TestCopyIntoCase:
    def test_a_linked_row_is_replaced_by_a_copy(self, main_window, layout, monkeypatch):
        import ui.mixins._file_mgmt_ops as fm

        case, outside = layout
        link = case / "system" / "fvSolution"
        link.symlink_to(outside / "secret")
        win = _open(main_window, case, monkeypatch)
        monkeypatch.setattr(type(win), "_confirm", lambda self, *a, **k: True)
        monkeypatch.setattr(
            fm.QInputDialog, "getText",
            staticmethod(lambda *a, **k: ("system/fvSolution", True)),
        )
        win._on_copy_into_case_requested(str(link))
        assert not link.is_symlink()
        assert link.read_text(encoding="utf-8") == SECRET
        _untouched(outside)
        assert str(link) not in win.state.read_only_files

    def test_copy_into_case_will_not_land_on_a_dangling_link(
        self, main_window, layout, monkeypatch
    ):
        import ui.mixins._file_mgmt_ops as fm

        case, outside = layout
        (case / "system" / "controlDict").write_text(
            CONTROL_DICT + '#include "../../outside/secret"\n', encoding="utf-8"
        )
        (case / "system" / "planted").symlink_to(outside / "created")
        win = _open(main_window, case, monkeypatch)
        src = next(p for p in win.state.read_only_files if p.endswith("secret"))
        monkeypatch.setattr(
            fm.QInputDialog, "getText", staticmethod(lambda *a, **k: ("system/planted", True))
        )
        win._on_copy_into_case_requested(src)
        _untouched(outside)


class TestCaseCopies:
    @pytest.fixture
    def win(self, main_window, layout, monkeypatch):
        case, outside = layout
        (case / "system" / "fvSolution").symlink_to(outside / "secret")
        (case / "linkdir").symlink_to(outside / "dir")
        (case / ".foam-editor-files.json").write_text(
            '{"extra_files": ["linkdir/f"]}', encoding="utf-8"
        )
        win = _open(main_window, case, monkeypatch)
        monkeypatch.setattr(type(win), "_confirm", lambda self, *a, **k: True)
        return win

    @pytest.mark.parametrize("copy_all", [False, True])
    def test_duplicate_never_copies_outside_contents(self, win, layout, tmp_path, copy_all):
        case, outside = layout
        dest = tmp_path / "dup"
        win._run_duplicate(str(case), dest, copy_all)
        for p in dest.rglob("*"):
            if p.is_file() and not p.is_symlink() and not any(
                q.is_symlink() for q in p.relative_to(dest).parents if str(q) != "."
                for q in [dest / q]
            ):
                assert "secret 1;" not in p.read_text(encoding="utf-8"), p
        if copy_all:
            assert (dest / "system" / "fvSolution").is_symlink()
        else:
            assert not os.path.lexists(dest / "system" / "fvSolution")
        _untouched(outside)

    @pytest.mark.parametrize("copy_all", [False, True])
    def test_save_as_never_writes_a_buffer_through_a_link(
        self, win, layout, tmp_path, stub_dialog, answer_message_box, copy_all
    ):
        case, outside = layout
        good = str(case / "system" / "controlDict")
        _edit(win, good, CONTROL_DICT + "// edited\n")
        _edit(win, str(case / "system" / "fvSolution"), "changed 1;\n")
        _edit(win, str(case / "linkdir" / "f"), "changed 1;\n")
        dest = tmp_path / "saved"
        stub_dialog("ui.mixins._case_ops.SaveAsNewCaseDialog",
                    destination_path=dest, copy_all_files=copy_all)
        told = answer_message_box(QMessageBox.StandardButton.Ok)
        win.save_as_new_case()
        _untouched(outside)
        assert "// edited" in (dest / "system" / "controlDict").read_text(encoding="utf-8")
        assert told and "fvSolution" in told[0] and "linkdir" in told[0]

    @pytest.mark.parametrize("name", ["case", "..", "case/system/inner"])
    def test_an_overlapping_destination_is_refused_before_anything_is_removed(
        self, win, layout, tmp_path, name
    ):
        case, _ = layout
        before = sorted(str(p) for p in tmp_path.rglob("*"))
        win._run_duplicate(str(case), tmp_path / name, True)
        assert (case / "system" / "controlDict").is_file()
        assert sorted(str(p) for p in tmp_path.rglob("*")) == before

    def test_an_overlap_through_an_alias_is_refused(self, win, layout, tmp_path):
        case, _ = layout
        (tmp_path / "alias").symlink_to(case)
        win._run_duplicate(str(case), tmp_path / "alias", True)
        assert (case / "system" / "controlDict").is_file()
        assert (tmp_path / "alias").is_symlink()


FIELD = (
    "FoamFile {{ version 2.0; format ascii; class volScalarField; object {name}; }}\n"
    "dimensions [0 0 0 0 0 0 0];\ninternalField uniform 0;\n"
    "boundaryField\n{{\n    inlet {{ type zeroGradient; }}\n}}\n"
)


class TestBoundaryEditsLeaveReadOnlyFilesAlone:
    """A linked field file is never saved, so a boundary operation must not
    change its buffer either: the edit would show in the panel and go nowhere."""

    @pytest.fixture
    def fields(self, main_window, layout, monkeypatch):
        case, outside = layout
        (case / "0").mkdir()
        (case / "0" / "p").write_text(FIELD.format(name="p"), encoding="utf-8")
        (outside / "T").write_text(FIELD.format(name="T"), encoding="utf-8")
        (case / "0" / "T").symlink_to(outside / "T")
        win = _open(main_window, case, monkeypatch)
        own, linked = str(case / "0" / "p"), str(case / "0" / "T")
        for path in (own, linked):
            assert win._cache_parsed_root(path) is not None
        assert win._is_read_only(linked) and not win._is_read_only(own)
        return win, own, linked, outside

    @staticmethod
    def _unchanged(win, linked, outside):
        assert "inlet" in win._current_text(linked)
        assert "outlet" not in win._current_text(linked)
        assert not win.state.file_dirty.get(linked, False)
        assert (outside / "T").read_text(encoding="utf-8") == FIELD.format(name="T")

    def test_single_file_operations_are_refused(self, fields):
        win, _, linked, outside = fields
        win._on_patch_create_requested(linked, "outlet")
        win._on_patch_paste_requested(linked, "inlet", "type fixedValue; value uniform 1;")
        win._on_patch_delete_requested(linked, "inlet")
        win._on_patch_edit_requested(linked, "inlet", None)
        assert "fixedValue" not in win._current_text(linked)
        self._unchanged(win, linked, outside)

    def test_add_to_all_skips_it(self, fields, answer_message_box):
        win, own, linked, outside = fields
        answer_message_box(QMessageBox.StandardButton.Yes)
        win._on_patch_add_all_requested("outlet")
        assert "outlet" in win._current_text(own)
        self._unchanged(win, linked, outside)

    def test_delete_from_all_skips_it_and_says_so(self, fields, answer_message_box):
        win, own, linked, outside = fields
        answer_message_box(QMessageBox.StandardButton.Yes)
        win._on_patch_delete_all_requested("inlet")
        assert "inlet" not in win._current_text(own)
        self._unchanged(win, linked, outside)
        assert "T" in win.statusBar().currentMessage()


class TestSaveAsKeepsUnwrittenEdits:
    """Opening the new case clears every buffer, so an edit Save As could not
    carry over must leave the original case open."""

    def test_the_original_stays_open_when_an_edit_was_not_written(
        self, main_window, layout, tmp_path, monkeypatch, stub_dialog, answer_message_box
    ):
        case, outside = layout
        (case / "system" / "fvSolution").symlink_to(outside / "secret")
        win = _open(main_window, case, monkeypatch)
        link = str(case / "system" / "fvSolution")
        _edit(win, link, "changed 1;\n")
        dest = tmp_path / "saved"
        stub_dialog("ui.mixins._case_ops.SaveAsNewCaseDialog",
                    destination_path=dest, copy_all_files=True)
        told = answer_message_box(QMessageBox.StandardButton.Ok)
        win.save_as_new_case()
        assert win.state.current_case_dir == str(case)
        assert win.state.file_buffers[link] == "changed 1;\n"
        assert win.state.file_dirty[link]
        assert told and "stays open" in told[0]
        _untouched(outside)

    def test_the_new_case_opens_when_every_edit_was_written(
        self, main_window, layout, tmp_path, monkeypatch, stub_dialog
    ):
        case, _ = layout
        win = _open(main_window, case, monkeypatch)
        _edit(win, str(case / "system" / "controlDict"), CONTROL_DICT + "// edited\n")
        dest = tmp_path / "saved"
        stub_dialog("ui.mixins._case_ops.SaveAsNewCaseDialog",
                    destination_path=dest, copy_all_files=False)
        win.save_as_new_case()
        assert win.state.current_case_dir == str(dest)

    def test_an_include_spelled_with_dots_is_carried_over(
        self, main_window, layout, tmp_path, monkeypatch, stub_dialog
    ):
        case, _ = layout
        (case / "constant").mkdir()
        (case / "constant" / "shared").write_text("a 1;\n", encoding="utf-8")
        win = _open(main_window, case, monkeypatch)
        listed = str(case / "system" / ".." / "constant" / "shared")
        _edit(win, listed, "a 2;\n")
        dest = tmp_path / "saved"
        stub_dialog("ui.mixins._case_ops.SaveAsNewCaseDialog",
                    destination_path=dest, copy_all_files=True)
        win.save_as_new_case()
        assert (dest / "constant" / "shared").read_text(encoding="utf-8") == "a 2;\n"
        assert win.state.current_case_dir == str(dest)

    def test_dots_after_a_link_are_not_folded_away(
        self, main_window, layout, tmp_path, monkeypatch, stub_dialog, answer_message_box
    ):
        case, outside = layout
        (case / "linkdir").symlink_to(outside / "dir")
        (case / "secret").write_text("inside 1;\n", encoding="utf-8")
        win = _open(main_window, case, monkeypatch)
        # Names outside/secret on disk; folded as text it would read case/secret.
        _edit(win, str(case / "linkdir" / ".." / "secret"), "changed 1;\n")
        dest = tmp_path / "saved"
        stub_dialog("ui.mixins._case_ops.SaveAsNewCaseDialog",
                    destination_path=dest, copy_all_files=True)
        answer_message_box(QMessageBox.StandardButton.Ok)
        win.save_as_new_case()
        assert (dest / "secret").read_text(encoding="utf-8") == "inside 1;\n"
        assert win.state.current_case_dir == str(case)
        _untouched(outside)


class TestRecheckAfterThePrompt:
    """A prompt can stay open for any length of time. What was checked before
    it is checked again after it, before anything is written or removed."""

    def test_save_rechecks_after_the_changed_on_disk_prompt(
        self, main_window, layout, monkeypatch
    ):
        case, outside = layout
        win = _open(main_window, case, monkeypatch)
        path = case / "system" / "controlDict"
        win.load_selected_file(str(path))

        def swap(self, paths):
            path.unlink()
            path.symlink_to(outside / "secret")
            return True

        monkeypatch.setattr(type(win), "_changed_outside", lambda self, paths: list(paths))
        monkeypatch.setattr(type(win), "_confirm_overwrite", swap)
        win.save_file()
        _untouched(outside)

    def test_overwrite_rechecks_the_destination(self, main_window, layout, tmp_path, monkeypatch):
        """While the prompt is open the destination's parent becomes an alias
        of the case's own parent: the overwrite would now remove the case."""
        case, outside = layout
        win = _open(main_window, case, monkeypatch)
        parent = tmp_path / "a"
        dest = parent / "case"
        dest.mkdir(parents=True)

        def swap(self, *a, **k):
            dest.rmdir()
            parent.rmdir()
            parent.symlink_to(tmp_path)
            return True

        monkeypatch.setattr(type(win), "_confirm", swap)
        win._run_duplicate(str(case), dest, True)
        assert (case / "system" / "controlDict").read_text(encoding="utf-8") == CONTROL_DICT
        _untouched(outside)

    def test_duplicate_directory_rechecks_the_destination(
        self, main_window, layout, monkeypatch
    ):
        case, outside = layout
        (case / "sub").mkdir()
        win = _open(main_window, case, monkeypatch)

        def swap(self, *a, **k):
            (case / "sub").rmdir()
            (case / "sub").symlink_to(outside / "dir")
            return True

        monkeypatch.setattr(type(win), "_confirm", swap)
        win._on_duplicate_dir_requested(str(case), "system", "sub/copy")
        _untouched(outside)


class TestReplacingALinkKeepsItOnFailure:
    def _replace(self, win, case, monkeypatch):
        import ui.mixins._file_mgmt_ops as fm

        link = case / "system" / "fvSolution"
        monkeypatch.setattr(type(win), "_confirm", lambda self, *a, **k: True)
        monkeypatch.setattr(
            fm.QInputDialog, "getText", staticmethod(lambda *a, **k: ("system/fvSolution", True))
        )
        win._on_copy_into_case_requested(str(link))
        return link

    def test_a_failed_copy_leaves_the_link_and_no_temp(self, main_window, layout, monkeypatch):
        import ui.mixins._file_mgmt_ops as fm

        case, outside = layout
        (case / "system" / "fvSolution").symlink_to(outside / "secret")
        win = _open(main_window, case, monkeypatch)

        def fail(*a, **k):
            raise OSError("disk full")

        monkeypatch.setattr(fm.shutil, "copyfileobj", fail)
        link = self._replace(win, case, monkeypatch)
        assert link.is_symlink() and link.read_text(encoding="utf-8") == SECRET
        assert sorted(p.name for p in (case / "system").iterdir()) == ["controlDict", "fvSolution"]
        _untouched(outside)

    def test_the_copy_is_a_writable_regular_file(self, main_window, layout, monkeypatch):
        case, outside = layout
        (outside / "secret").chmod(0o444)
        (case / "system" / "fvSolution").symlink_to(outside / "secret")
        win = _open(main_window, case, monkeypatch)
        link = self._replace(win, case, monkeypatch)
        assert not link.is_symlink() and link.read_text(encoding="utf-8") == SECRET
        assert os.access(link, os.W_OK)
        assert sorted(p.name for p in (case / "system").iterdir()) == ["controlDict", "fvSolution"]
        _untouched(outside)


class TestTwoBuffersOneFile:
    """Two listed names can be one file on disk. Their buffers are never
    written one over the other: neither is, and both stay unsaved."""

    @pytest.fixture
    def win(self, main_window, layout, monkeypatch):
        case, _ = layout
        (case / "system" / "alias").symlink_to(case / "system" / "controlDict")
        return _open(main_window, case, monkeypatch)

    def _edit_both(self, win, case):
        a, b = str(case / "system" / "controlDict"), str(case / "system" / "alias")
        _edit(win, a, CONTROL_DICT + "// one\n")
        _edit(win, b, CONTROL_DICT + "// two\n")
        return a, b

    def test_save_case_writes_neither(self, win, layout, answer_message_box):
        case, _ = layout
        a, b = self._edit_both(win, case)
        told = answer_message_box(QMessageBox.StandardButton.Ok)
        win.save_all_files()
        assert (case / "system" / "controlDict").read_text(encoding="utf-8") == CONTROL_DICT
        assert win.state.file_dirty[a] and win.state.file_dirty[b]
        assert told and "same file" in told[0]

    def test_save_as_writes_neither_and_keeps_the_case_open(
        self, win, layout, tmp_path, stub_dialog, answer_message_box
    ):
        case, _ = layout
        a, b = self._edit_both(win, case)
        dest = tmp_path / "saved"
        stub_dialog("ui.mixins._case_ops.SaveAsNewCaseDialog",
                    destination_path=dest, copy_all_files=True)
        told = answer_message_box(QMessageBox.StandardButton.Ok)
        win.save_as_new_case()
        assert (dest / "system" / "controlDict").read_text(encoding="utf-8") == CONTROL_DICT
        assert win.state.current_case_dir == str(case)
        assert win.state.file_dirty[a] and win.state.file_dirty[b]
        assert told and "same file" in told[0]


def test_copy_into_case_stops_when_the_link_changed_during_the_question(
    main_window, layout, monkeypatch
):
    import ui.mixins._file_mgmt_ops as fm

    case, outside = layout
    link = case / "system" / "fvSolution"
    link.symlink_to(outside / "secret")
    win = _open(main_window, case, monkeypatch)

    def retarget(self, *a, **k):
        link.unlink()
        link.symlink_to(outside / "dir" / "f.bak_20260101_000000")
        return True

    monkeypatch.setattr(type(win), "_confirm", retarget)
    monkeypatch.setattr(
        fm.QInputDialog, "getText", staticmethod(lambda *a, **k: ("system/fvSolution", True))
    )
    win._on_copy_into_case_requested(str(link))
    assert link.is_symlink()
    _untouched(outside)


class TestCaseFolderReplaced:
    """The folder is renamed away and another put at its name while the case
    is open. The edits in memory belong to the first one."""

    @pytest.fixture
    def win(self, main_window, layout, monkeypatch):
        case, _ = layout
        win = _open(main_window, case, monkeypatch)
        win.load_selected_file(str(case / "system" / "controlDict"))
        case.rename(case.with_name("case.old"))
        (case / "system").mkdir(parents=True)
        # Byte-identical, so the changed-on-disk question has nothing to see.
        (case / "system" / "controlDict").write_text(CONTROL_DICT, encoding="utf-8")
        return win

    def test_save_does_not_write_into_the_new_folder(self, win, layout):
        case, _ = layout
        win.editor_panel.set_text(CONTROL_DICT + "// edited\n")
        win.state.text_dirty = True
        win.save_file()
        assert (case / "system" / "controlDict").read_text(encoding="utf-8") == CONTROL_DICT
        assert "replaced on disk" in win.statusBar().currentMessage()
        assert win.state.text_dirty

    def test_save_case_and_new_file_do_not_either(self, win, layout, answer_message_box):
        case, _ = layout
        path = str(case / "system" / "controlDict")
        win.editor_panel.set_text(CONTROL_DICT + "// edited\n")
        win.state.text_dirty = True
        told = answer_message_box(QMessageBox.StandardButton.Ok)
        win.save_all_files()
        assert (case / "system" / "controlDict").read_text(encoding="utf-8") == CONTROL_DICT
        assert win.state.file_dirty[path]
        assert told and "replaced on disk" in told[0]
        assert win._create_refused(case / "system" / "new")

    def test_reloading_the_case_takes_the_new_folder(self, win, layout):
        case, _ = layout
        win._load_case_dir(str(case))
        assert not win._edit_refused(str(case / "system" / "controlDict"))

    def test_reset_file_list_and_add_files_leave_the_new_folder_alone(
        self, win, layout, monkeypatch
    ):
        case, _ = layout
        planted = case / ".foam-editor-files.json"
        planted.write_text('{"extra_files": ["theirs"]}', encoding="utf-8")
        path = str(case.with_name("case") / "system" / "controlDict")
        _edit(win, path, CONTROL_DICT + "// edited\n")
        monkeypatch.setattr(type(win), "_confirm", lambda self, *a, **k: True)
        win.reset_file_list()
        win._on_add_file_requested(str(case), "system")
        assert planted.read_text(encoding="utf-8") == '{"extra_files": ["theirs"]}'
        # Not reloaded either: the edits are still there, the folder still refused.
        assert win.state.file_buffers[path] == CONTROL_DICT + "// edited\n"
        assert win._edit_refused(path)


def test_save_as_stops_two_buffers_that_are_one_file_in_the_new_case(
    main_window, layout, tmp_path, monkeypatch, stub_dialog, answer_message_box
):
    """Two source files, one file in the destination -- as names differing in
    letter case become on a filesystem that ignores it. Stood in for by a
    copy step that leaves the two names hard-linked."""
    import ui.mixins._case_ops as co

    case, _ = layout
    (case / "system" / "fvSolution").write_text("a 1;\n", encoding="utf-8")
    (case / "system" / "fvSchemes").write_text("a 1;\n", encoding="utf-8")
    win = _open(main_window, case, monkeypatch)
    a, b = str(case / "system" / "fvSolution"), str(case / "system" / "fvSchemes")
    _edit(win, a, "one 1;\n")
    _edit(win, b, "two 2;\n")
    dest = tmp_path / "saved"

    def merging_copy(self, source_dir, dest, copy_all):
        (dest / "system").mkdir(parents=True)
        (dest / "system" / "fvSolution").write_text("a 1;\n", encoding="utf-8")
        os.link(dest / "system" / "fvSolution", dest / "system" / "fvSchemes")
        return []

    monkeypatch.setattr(co._CaseOpsMixin, "_copy_case", merging_copy)
    stub_dialog("ui.mixins._case_ops.SaveAsNewCaseDialog",
                destination_path=dest, copy_all_files=True)
    told = answer_message_box(QMessageBox.StandardButton.Ok)
    win.save_as_new_case()
    assert (dest / "system" / "fvSolution").read_text(encoding="utf-8") == "a 1;\n"
    assert win.state.current_case_dir == str(case)
    assert told and "same file" in told[0]
