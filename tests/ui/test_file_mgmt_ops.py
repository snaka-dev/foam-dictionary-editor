# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for ui/mixins/_file_mgmt_ops.py -- the operations that delete the user's files.

The largest untested block in the codebase at 28% covered, and what is in it is backup,
delete-file, delete-directory and clean-backups: every one of them removes something from
disk, and `_on_delete_file_requested` says so in its own dialog ("This action cannot be
undone"). The safety rules here are worth pinning precisely because they are invisible --
`_on_delete_dir_requested` refuses to touch `0/` unless `0.orig/` exists, which no reader
of the call site would guess.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QMessageBox

CONTROL_DICT = (
    "FoamFile { version 2.0; format ascii; class dictionary; object controlDict; }\n"
    "application icoFoam;\nendTime 1;\n"
)


@pytest.fixture
def case(tmp_path):
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "controlDict").write_text(CONTROL_DICT, encoding="utf-8")
    (tmp_path / "0").mkdir()
    (tmp_path / "0" / "U").write_text(
        "FoamFile { version 2.0; format ascii; class volVectorField; object U; }\n"
        "boundaryField { walls { type noSlip; } }\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def win(main_window, case, monkeypatch):
    main_window._load_case_dir(str(case))
    monkeypatch.setattr(type(main_window), "_error", lambda self, *a, **k: None)
    return main_window


def _answer_delete_dialog(monkeypatch, choice: str) -> None:
    """Answer _on_delete_file_requested's QMessageBox without showing it.

    It is built by hand with three custom buttons rather than using a standard set, so
    the answer has to be given as one of its own button objects -- the handler compares
    `clickedButton()` by identity. Matched on text rather than position: the order is an
    implementation detail of how the dialog is assembled.
    """
    monkeypatch.setattr(QMessageBox, "exec", lambda self: 0)

    def clicked(self):
        for b in self.buttons():
            text = b.text().replace("&", "")
            if choice == "backup" and text.startswith("Backup"):
                return b
            if choice == "delete" and text == "Delete":
                return b
            if choice == "cancel" and "Cancel" in text:
                return b
        return None

    monkeypatch.setattr(QMessageBox, "clickedButton", clicked)


class TestBackup:
    def test_it_writes_a_timestamped_copy_beside_the_file(self, win, case):
        target = case / "system" / "controlDict"
        assert win._create_backup(str(target)) is True
        backups = list((case / "system").glob("controlDict.bak_*"))
        assert len(backups) == 1
        assert backups[0].read_text(encoding="utf-8") == CONTROL_DICT

    def test_it_backs_up_unsaved_edits_not_what_is_on_disk(self, win, case):
        # The point of offering a backup before a destructive action: the thing worth
        # keeping is what the user has in front of them, not the stale copy on disk.
        target = str(case / "system" / "controlDict")
        win.state.file_buffers[target] = CONTROL_DICT.replace("endTime 1;", "endTime 500;")
        win.state.file_dirty[target] = True

        win._create_backup(target)

        backup = next((case / "system").glob("controlDict.bak_*"))
        assert "endTime 500;" in backup.read_text(encoding="utf-8")

    def test_a_write_failure_reports_and_returns_false(self, win, case, monkeypatch):
        reported: list[str] = []
        monkeypatch.setattr(type(win), "_error", lambda self, t, m: reported.append(m))
        monkeypatch.setattr(
            Path, "write_text", lambda self, *a, **k: (_ for _ in ()).throw(OSError("read-only"))
        )
        assert win._create_backup(str(case / "system" / "controlDict")) is False
        assert reported


class TestDeleteFile:
    def test_cancel_leaves_the_file_alone(self, win, case, monkeypatch):
        _answer_delete_dialog(monkeypatch, "cancel")
        target = case / "system" / "controlDict"
        win._on_delete_file_requested(str(target))
        assert target.is_file()

    def test_delete_removes_it(self, win, case, monkeypatch):
        _answer_delete_dialog(monkeypatch, "delete")
        target = case / "system" / "controlDict"
        win._on_delete_file_requested(str(target))
        assert not target.exists()

    def test_backup_and_delete_leaves_the_backup_behind(self, win, case, monkeypatch):
        _answer_delete_dialog(monkeypatch, "backup")
        target = case / "system" / "controlDict"
        win._on_delete_file_requested(str(target))
        assert not target.exists()
        assert len(list((case / "system").glob("controlDict.bak_*"))) == 1

    def test_a_failed_backup_aborts_the_delete(self, win, case, monkeypatch):
        # Otherwise "Backup & Delete" would delete without the backup the user asked for,
        # which is strictly worse than either button on its own.
        _answer_delete_dialog(monkeypatch, "backup")
        monkeypatch.setattr(
            Path, "write_text", lambda self, *a, **k: (_ for _ in ()).throw(OSError("read-only"))
        )
        target = case / "system" / "controlDict"
        win._on_delete_file_requested(str(target))
        assert target.is_file(), "the file was deleted although its backup failed"

    def test_deleting_the_open_file_clears_the_editor(self, win, case, monkeypatch):
        target = str(case / "system" / "controlDict")
        win.load_selected_file(target)
        assert win.state.current_file == target
        _answer_delete_dialog(monkeypatch, "delete")
        win._on_delete_file_requested(target)
        assert win.state.current_file is None

    def test_a_failed_delete_is_reported_and_the_file_stays(self, win, case, monkeypatch):
        _answer_delete_dialog(monkeypatch, "delete")
        reported: list[str] = []
        monkeypatch.setattr(type(win), "_error", lambda self, t, m: reported.append(m))
        monkeypatch.setattr(
            Path, "unlink", lambda self, *a, **k: (_ for _ in ()).throw(OSError("busy"))
        )
        target = case / "system" / "controlDict"
        win._on_delete_file_requested(str(target))
        assert reported
        assert target.is_file()


class TestDeleteDirectory:
    """`0/` is refused unless `0.orig/` exists -- the rule that keeps a solver run's only
    copy of the initial conditions from being thrown away."""

    def test_it_refuses_when_there_is_no_orig_to_restore_from(
        self, win, case, monkeypatch, answer_message_box
    ):
        warned = answer_message_box(QMessageBox.StandardButton.No)
        win._on_delete_dir_requested(str(case), "0")
        assert (case / "0").is_dir(), "0/ was deleted with no 0.orig/ to restore from"
        assert warned and "0.orig" in warned[0]

    def test_with_orig_present_a_yes_deletes_it(self, win, case, monkeypatch, answer_message_box):
        (case / "0.orig").mkdir()
        answer_message_box(QMessageBox.StandardButton.Yes)
        win._on_delete_dir_requested(str(case), "0")
        assert not (case / "0").exists()

    def test_a_no_keeps_it(self, win, case, monkeypatch, answer_message_box):
        (case / "0.orig").mkdir()
        answer_message_box(QMessageBox.StandardButton.No)
        win._on_delete_dir_requested(str(case), "0")
        assert (case / "0" / "U").is_file()

    def test_buffers_for_deleted_files_are_purged(self, win, case, monkeypatch, answer_message_box):
        (case / "0.orig").mkdir()
        target = str(case / "0" / "U")
        win.load_selected_file(target)
        answer_message_box(QMessageBox.StandardButton.Yes)
        win._on_delete_dir_requested(str(case), "0")
        assert target not in win.state.file_buffers
        assert win.state.current_file is None



class TestCreateFile:
    def test_it_writes_a_foamfile_header_naming_the_file(self, win, case, monkeypatch):
        monkeypatch.setattr(
            type(win), "_prompt_new_filename",
            lambda self, *a, **k: case / "system" / "myDict",
        )
        win._on_create_file_requested(str(case), "system")
        text = (case / "system" / "myDict").read_text(encoding="utf-8")
        assert "FoamFile" in text
        assert "myDict" in text

    def test_a_cancelled_prompt_creates_nothing(self, win, case, monkeypatch):
        monkeypatch.setattr(type(win), "_prompt_new_filename", lambda self, *a, **k: None)
        before = sorted(p.name for p in (case / "system").iterdir())
        win._on_create_file_requested(str(case), "system")
        assert sorted(p.name for p in (case / "system").iterdir()) == before

    def test_a_write_failure_is_reported(self, win, case, monkeypatch):
        monkeypatch.setattr(
            type(win), "_prompt_new_filename",
            lambda self, *a, **k: case / "system" / "myDict",
        )
        reported: list[str] = []
        monkeypatch.setattr(type(win), "_error", lambda self, t, m: reported.append(m))
        monkeypatch.setattr(
            Path, "write_text", lambda self, *a, **k: (_ for _ in ()).throw(OSError("read-only"))
        )
        win._on_create_file_requested(str(case), "system")
        assert reported


class TestDuplicateFile:
    def test_the_object_entry_is_renamed_to_match_the_new_file(self, win, case, monkeypatch):
        # An OpenFOAM dictionary's `object` must match its filename; a copy that kept the
        # source's name would be read as the wrong dictionary.
        monkeypatch.setattr(
            type(win), "_prompt_new_filename",
            lambda self, *a, **k: case / "system" / "controlDict2",
        )
        win._on_duplicate_file_requested(str(case / "system" / "controlDict"))
        text = (case / "system" / "controlDict2").read_text(encoding="utf-8")
        assert "object      controlDict2;" in text or "object controlDict2;" in text
        assert "object controlDict;" not in text

    def test_a_cancelled_name_prompt_copies_nothing(self, win, case, monkeypatch):
        monkeypatch.setattr(type(win), "_prompt_new_filename", lambda self, *a, **k: None)
        win._on_duplicate_file_requested(str(case / "system" / "controlDict"))
        assert not (case / "system" / "controlDict2").exists()

    def test_an_unsaved_file_can_be_duplicated_with_its_edits(self, win, case, monkeypatch):
        src = str(case / "system" / "controlDict")
        win.state.file_buffers[src] = CONTROL_DICT.replace("endTime 1;", "endTime 42;")
        win.state.file_dirty[src] = True
        monkeypatch.setattr(
            type(win), "_prompt_new_filename",
            lambda self, *a, **k: case / "system" / "controlDict2",
        )
        # "Duplicate with Unsaved Changes" -- the middle button, an ActionRole.
        monkeypatch.setattr(QMessageBox, "exec", lambda self: 0)
        monkeypatch.setattr(
            QMessageBox, "clickedButton",
            lambda self: next(
                b for b in self.buttons()
                if self.buttonRole(b) == QMessageBox.ButtonRole.ActionRole
            ),
        )
        win._on_duplicate_file_requested(src)
        assert "endTime 42;" in (case / "system" / "controlDict2").read_text(encoding="utf-8")

    def test_cancelling_the_unsaved_prompt_copies_nothing(self, win, case, monkeypatch):
        src = str(case / "system" / "controlDict")
        win.state.file_dirty[src] = True
        monkeypatch.setattr(
            type(win), "_prompt_new_filename",
            lambda self, *a, **k: case / "system" / "controlDict2",
        )
        monkeypatch.setattr(QMessageBox, "exec", lambda self: 0)
        monkeypatch.setattr(
            QMessageBox, "clickedButton",
            lambda self: next(
                b for b in self.buttons()
                if self.buttonRole(b) == QMessageBox.ButtonRole.RejectRole
            ),
        )
        win._on_duplicate_file_requested(src)
        assert not (case / "system" / "controlDict2").exists()


class TestNewFilenamePrompt:
    """The three refusals every create/duplicate goes through."""

    @staticmethod
    def _answer(monkeypatch, text: str) -> None:
        import ui.mixins._file_mgmt_ops as fm

        monkeypatch.setattr(fm.QInputDialog, "getText", staticmethod(lambda *a, **k: (text, True)))

    def test_a_good_name_becomes_a_path(self, win, case, monkeypatch):
        self._answer(monkeypatch, "newDict")
        assert win._prompt_new_filename("t", "p", case / "system") == case / "system" / "newDict"

    def test_whitespace_is_trimmed(self, win, case, monkeypatch):
        self._answer(monkeypatch, "  newDict  ")
        assert win._prompt_new_filename("t", "p", case / "system").name == "newDict"

    @pytest.mark.parametrize("bad", ["", "   ", "sub/newDict", "sub\\newDict"])
    def test_an_unusable_name_is_refused(self, win, case, monkeypatch, bad):
        self._answer(monkeypatch, bad)
        assert win._prompt_new_filename("t", "p", case / "system") is None

    def test_an_existing_name_is_refused(self, win, case, monkeypatch):
        self._answer(monkeypatch, "controlDict")
        assert win._prompt_new_filename("t", "p", case / "system") is None

    def test_a_cancelled_dialog_is_refused(self, win, case, monkeypatch):
        import ui.mixins._file_mgmt_ops as fm

        monkeypatch.setattr(fm.QInputDialog, "getText", staticmethod(lambda *a, **k: ("x", False)))
        assert win._prompt_new_filename("t", "p", case / "system") is None


class TestCleanBackups:
    @pytest.fixture
    def with_backups(self, win, case):
        for name in ("controlDict.bak_20260101_000000", "controlDict.bak_20260102_000000"):
            (case / "system" / name).write_text("old\n", encoding="utf-8")
        return case

    def test_the_chosen_backups_are_deleted(self, win, with_backups, stub_dialog, monkeypatch):
        doomed = [str(with_backups / "system" / "controlDict.bak_20260101_000000")]
        stub_dialog("ui.mixins._file_mgmt_ops.CleanBackupsDialog", paths_to_delete=doomed)
        win._on_clean_backups()
        assert not Path(doomed[0]).exists()
        assert (with_backups / "system" / "controlDict.bak_20260102_000000").is_file()

    def test_a_cancelled_dialog_deletes_nothing(self, win, with_backups, stub_dialog, monkeypatch):
        doomed = [str(with_backups / "system" / "controlDict.bak_20260101_000000")]
        stub_dialog("ui.mixins._file_mgmt_ops.CleanBackupsDialog", accepted=False,
                    paths_to_delete=doomed)
        win._on_clean_backups()
        assert Path(doomed[0]).is_file()

    def test_choosing_nothing_deletes_nothing(self, win, with_backups, stub_dialog, monkeypatch):
        stub_dialog("ui.mixins._file_mgmt_ops.CleanBackupsDialog", paths_to_delete=[])
        win._on_clean_backups()
        assert len(list((with_backups / "system").glob("*.bak_*"))) == 2

    def test_a_failed_delete_is_reported_and_the_rest_still_go(
        self, win, with_backups, stub_dialog, monkeypatch
    , answer_message_box):
        one = with_backups / "system" / "controlDict.bak_20260101_000000"
        two = with_backups / "system" / "controlDict.bak_20260102_000000"
        stub_dialog("ui.mixins._file_mgmt_ops.CleanBackupsDialog",
                    paths_to_delete=[str(one), str(two)])
        real_unlink = Path.unlink

        def flaky(self, *a, **k):
            if self.name.endswith("20260101_000000"):
                raise OSError("busy")
            return real_unlink(self, *a, **k)

        monkeypatch.setattr(Path, "unlink", flaky)
        warned = answer_message_box(None)
        win._on_clean_backups()
        assert warned, "a failed deletion was not reported"
        assert not two.exists(), "one failure stopped the others"


class TestManageExtraFiles:
    def test_removing_an_entry_takes_it_out_of_the_config(self, win, case, stub_dialog, monkeypatch):
        win.state.case_files_config.add_file("system/extra1")
        win.state.case_files_config.save()
        stub_dialog(
            "ui.mixins._file_mgmt_ops.ManageExtraFilesDialog",
            removed_files=["system/extra1"], result_dirs=[],
        )
        win._on_manage_extra_files()
        assert "system/extra1" not in win.state.case_files_config.get_extra_files()

    def test_adding_a_directory_records_it(self, win, case, stub_dialog, monkeypatch):
        stub_dialog(
            "ui.mixins._file_mgmt_ops.ManageExtraFilesDialog",
            removed_files=[], result_dirs=[("postProcessing", True)],
        )
        win._on_manage_extra_files()
        assert ("postProcessing", True) in win.state.case_files_config.get_extra_dirs()

    def test_toggling_a_directory_updates_it_in_place(self, win, case, stub_dialog, monkeypatch):
        win.state.case_files_config.add_dir("postProcessing", False)
        win.state.case_files_config.save()
        stub_dialog(
            "ui.mixins._file_mgmt_ops.ManageExtraFilesDialog",
            removed_files=[], result_dirs=[("postProcessing", True)],
        )
        win._on_manage_extra_files()
        assert win.state.case_files_config.get_extra_dirs() == [("postProcessing", True)]

    def test_changing_nothing_writes_nothing(self, win, case, stub_dialog, monkeypatch):
        stub_dialog("ui.mixins._file_mgmt_ops.ManageExtraFilesDialog",
                    removed_files=[], result_dirs=[])
        saved: list[int] = []
        monkeypatch.setattr(
            type(win.state.case_files_config), "save",
            lambda self: saved.append(1),
        )
        win._on_manage_extra_files()
        assert saved == []
