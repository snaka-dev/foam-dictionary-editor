# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for ui/mixins/_case_ops.py -- duplicating and saving-as a whole case.

These are the operations that copy, overwrite and delete whole directories of the user's
work: `_confirm_and_remove_existing_dir` runs `shutil.rmtree` on a directory the user
named, and `save_as_new_case` writes every dirty editor buffer into the copy. The mixin
sat at 16% covered, which is the wrong way round for the code that can destroy a case.
"""
from __future__ import annotations

from pathlib import Path

import pytest

CONTROL_DICT = (
    "FoamFile { version 2.0; format ascii; class dictionary; object controlDict; }\n"
    "application icoFoam;\nendTime 1;\n"
)


@pytest.fixture
def case(tmp_path):
    src = tmp_path / "src"
    (src / "system").mkdir(parents=True)
    (src / "system" / "controlDict").write_text(CONTROL_DICT, encoding="utf-8")
    (src / "system" / "fvSchemes").write_text(
        "FoamFile { version 2.0; format ascii; class dictionary; object fvSchemes; }\n"
        "ddtSchemes { default Euler; }\n", encoding="utf-8")
    # Not in TARGET_FILES and not registered as an extra: only a full copy takes it.
    (src / "notes.txt").write_text("scratch\n", encoding="utf-8")
    return src


@pytest.fixture
def win(main_window, case, monkeypatch):
    main_window._load_case_dir(str(case))
    # Default: say yes to everything. Individual tests narrow this.
    monkeypatch.setattr(type(main_window), "_confirm", lambda self, *a, **k: True)
    monkeypatch.setattr(type(main_window), "_error", lambda self, *a, **k: None)
    return main_window


class TestOverwriteGuard:
    """_confirm_and_remove_existing_dir -- the rmtree behind every copy destination."""

    def test_a_free_destination_needs_no_confirmation(self, win, tmp_path, monkeypatch):
        asked: list[str] = []
        monkeypatch.setattr(
            type(win), "_confirm", lambda self, t, m: asked.append(t) or True
        )
        assert win._confirm_and_remove_existing_dir(tmp_path / "new", "T") is True
        assert asked == []

    def test_an_existing_directory_is_removed_only_after_a_yes(self, win, tmp_path):
        dest = tmp_path / "existing"
        (dest / "system").mkdir(parents=True)
        assert win._confirm_and_remove_existing_dir(dest, "T") is True
        assert not dest.exists()

    def test_declining_leaves_the_directory_alone(self, win, tmp_path, monkeypatch):
        dest = tmp_path / "existing"
        (dest / "system").mkdir(parents=True)
        monkeypatch.setattr(type(win), "_confirm", lambda self, *a, **k: False)
        assert win._confirm_and_remove_existing_dir(dest, "T") is False
        assert (dest / "system").is_dir(), "the directory was removed despite a No"

    def test_the_prompt_names_the_directory_at_risk(self, win, tmp_path, monkeypatch):
        dest = tmp_path / "existing"
        dest.mkdir()
        seen: list[str] = []
        monkeypatch.setattr(
            type(win), "_confirm", lambda self, t, m: seen.append(m) or False
        )
        win._confirm_and_remove_existing_dir(dest, "T")
        assert str(dest) in seen[0]

    def test_a_failed_removal_refuses_rather_than_continuing(self, win, tmp_path, monkeypatch):
        import shutil

        dest = tmp_path / "existing"
        dest.mkdir()
        monkeypatch.setattr(
            shutil, "rmtree", lambda *a, **k: (_ for _ in ()).throw(OSError("busy"))
        )
        reported: list[str] = []
        monkeypatch.setattr(type(win), "_error", lambda self, t, m: reported.append(m))
        assert win._confirm_and_remove_existing_dir(dest, "T") is False
        assert reported, "a failed rmtree was not reported"


class TestDuplicate:
    def test_visible_only_leaves_untracked_files_behind(self, win, tmp_path):
        dest = tmp_path / "copy"
        win._run_duplicate(str(win.state.current_case_dir), dest, copy_all=False)
        assert (dest / "system" / "controlDict").is_file()
        assert not (dest / "notes.txt").exists()

    def test_copy_all_takes_everything(self, win, tmp_path):
        dest = tmp_path / "copy"
        win._run_duplicate(str(win.state.current_case_dir), dest, copy_all=True)
        assert (dest / "notes.txt").is_file()

    def test_a_declined_overwrite_copies_nothing(self, win, tmp_path, monkeypatch):
        dest = tmp_path / "copy"
        dest.mkdir()
        (dest / "marker").write_text("keep me\n", encoding="utf-8")
        monkeypatch.setattr(type(win), "_confirm", lambda self, *a, **k: False)
        win._run_duplicate(str(win.state.current_case_dir), dest, copy_all=True)
        assert (dest / "marker").read_text(encoding="utf-8") == "keep me\n"
        assert not (dest / "system").exists()

    def test_a_copy_failure_is_reported_and_does_not_open_the_case(
        self, win, tmp_path, monkeypatch
    ):
        import shutil

        before = win.state.current_case_dir
        monkeypatch.setattr(
            shutil, "copytree", lambda *a, **k: (_ for _ in ()).throw(OSError("no space"))
        )
        reported: list[str] = []
        monkeypatch.setattr(type(win), "_error", lambda self, t, m: reported.append(m))
        win._run_duplicate(str(before), tmp_path / "copy", copy_all=True)
        assert reported
        assert win.state.current_case_dir == before

    def test_saying_no_to_opening_it_leaves_the_current_case(self, win, tmp_path, monkeypatch):
        before = win.state.current_case_dir
        # A destination that does not exist skips the overwrite guard entirely, so the
        # only prompt reached is "open the duplicated case now?".
        monkeypatch.setattr(type(win), "_confirm", lambda self, *a, **k: False)
        win._run_duplicate(str(before), tmp_path / "copy", copy_all=False)
        assert (tmp_path / "copy" / "system" / "controlDict").is_file()
        assert win.state.current_case_dir == before


class TestSaveAsNewCase:
    """The half that is easy to get wrong: unsaved edits must reach the copy."""

    def test_an_unsaved_edit_is_written_into_the_copy(self, win, tmp_path, monkeypatch, stub_dialog):
        dest = tmp_path / "saved"
        path = str(Path(win.state.current_case_dir) / "system" / "controlDict")
        win.state.file_buffers[path] = CONTROL_DICT.replace("endTime 1;", "endTime 999;")
        win.state.file_dirty[path] = True
        stub_dialog("ui.mixins._case_ops.SaveAsNewCaseDialog", destination_path=dest, copy_all_files=False)

        win.save_as_new_case()

        assert "endTime 999;" in (dest / "system" / "controlDict").read_text(encoding="utf-8")

    def test_the_original_case_keeps_its_file_on_disk(self, win, tmp_path, monkeypatch, stub_dialog):
        dest = tmp_path / "saved"
        src_file = Path(win.state.current_case_dir) / "system" / "controlDict"
        path = str(src_file)
        win.state.file_buffers[path] = CONTROL_DICT.replace("endTime 1;", "endTime 999;")
        win.state.file_dirty[path] = True
        stub_dialog("ui.mixins._case_ops.SaveAsNewCaseDialog", destination_path=dest, copy_all_files=False)

        win.save_as_new_case()

        assert "endTime 1;" in src_file.read_text(encoding="utf-8")

    def test_a_clean_file_is_copied_not_rewritten(self, win, tmp_path, monkeypatch, stub_dialog):
        dest = tmp_path / "saved"
        stub_dialog("ui.mixins._case_ops.SaveAsNewCaseDialog", destination_path=dest, copy_all_files=False)
        win.save_as_new_case()
        assert (dest / "system" / "fvSchemes").read_text(encoding="utf-8").startswith("FoamFile")




class TestOpenCase:
    def test_a_valid_case_is_opened_and_remembered(
        self, win, case, tmp_path, monkeypatch, choose_directory, answer_message_box
    ):
        from PySide6.QtWidgets import QMessageBox as QMB

        from app_config import get_app_config

        other = tmp_path / "other"
        (other / "system").mkdir(parents=True)
        choose_directory(other)
        answer_message_box(QMB.StandardButton.Open)

        win.open_case()

        assert win.state.current_case_dir == str(other)
        # The *parent* is remembered, so the chooser reopens beside the case next time.
        assert get_app_config().get_default_case_dir() == str(tmp_path)

    def test_a_cancelled_chooser_changes_nothing(self, win, monkeypatch):
        import ui.mixins._case_ops as co

        before = win.state.current_case_dir
        monkeypatch.setattr(
            co.QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: "")
        )
        win.open_case()
        assert win.state.current_case_dir == before

    def test_a_directory_that_is_not_a_case_needs_confirming(
        self, win, tmp_path, monkeypatch, choose_directory, answer_message_box
    ):
        from PySide6.QtWidgets import QMessageBox as QMB

        plain = tmp_path / "not-a-case"
        plain.mkdir()
        before = win.state.current_case_dir
        choose_directory(plain)
        answer_message_box(QMB.StandardButton.Cancel)

        win.open_case()

        assert win.state.current_case_dir == before

    def test_confirming_opens_it_anyway(
        self, win, tmp_path, monkeypatch, choose_directory, answer_message_box
    ):
        from PySide6.QtWidgets import QMessageBox as QMB

        plain = tmp_path / "not-a-case"
        plain.mkdir()
        choose_directory(plain)
        answer_message_box(QMB.StandardButton.Open)

        win.open_case()

        assert win.state.current_case_dir == str(plain)


class TestConfirmOpenDir:
    def test_a_real_case_needs_no_question(self, win, case, monkeypatch):
        import ui.mixins._case_ops as co

        asked: list[int] = []
        monkeypatch.setattr(
            co.QMessageBox, "warning", staticmethod(lambda *a, **k: asked.append(1)))
        assert win._confirm_open_dir(str(case)) is True
        assert asked == []

    def test_a_bare_directory_is_questioned(self, win, tmp_path, monkeypatch, answer_message_box):
        from PySide6.QtWidgets import QMessageBox as QMB

        plain = tmp_path / "plain"
        plain.mkdir()
        answer_message_box(QMB.StandardButton.Cancel)
        assert win._confirm_open_dir(str(plain)) is False


class TestReloadCase:
    def test_a_clean_case_reloads_without_asking(self, win, case, monkeypatch):
        import ui.mixins._case_ops as co

        asked: list[int] = []
        monkeypatch.setattr(
            co.QMessageBox, "question", staticmethod(lambda *a, **k: asked.append(1)))
        win.reload_case()
        assert asked == []
        assert win.state.current_case_dir == str(case)

    def test_unsaved_changes_are_confirmed_before_discarding(
        self, win, case, monkeypatch, answer_message_box
    ):
        from PySide6.QtWidgets import QMessageBox as QMB

        target = str(Path(case) / "system" / "controlDict")
        win.state.file_buffers[target] = "edited\n"
        win.state.file_dirty[target] = True
        answer_message_box(QMB.StandardButton.No)

        win.reload_case()

        assert win.state.file_buffers[target] == "edited\n", "the edit was discarded after a No"

    def test_saying_yes_discards_them(self, win, case, monkeypatch, answer_message_box):
        from PySide6.QtWidgets import QMessageBox as QMB

        target = str(Path(case) / "system" / "controlDict")
        win.state.file_buffers[target] = "edited\n"
        win.state.file_dirty[target] = True
        answer_message_box(QMB.StandardButton.Yes)

        win.reload_case()

        assert win.state.file_buffers.get(target, CONTROL_DICT) != "edited\n"

    def test_with_no_case_open_it_says_so(self, main_window, monkeypatch):
        import ui.mixins._case_ops as co

        told: list[int] = []
        monkeypatch.setattr(
            co.QMessageBox, "information", staticmethod(lambda *a, **k: told.append(1)))
        main_window.state.current_case_dir = None
        main_window.reload_case()
        assert told, "reload with no case open reported nothing"


class TestCaseLibraryPicker:
    def test_an_empty_library_tells_the_user_instead_of_opening_a_chooser(
        self, win, monkeypatch
    ):
        import ui.mixins._case_ops as co
        from app_config import get_app_config

        for d in get_app_config().get_case_library_dirs():
            get_app_config().remove_case_library_dir(d)
        told: list[int] = []
        monkeypatch.setattr(
            co.QMessageBox, "information", staticmethod(lambda *a, **k: told.append(1)))
        opened: list[int] = []
        monkeypatch.setattr(
            co.QFileDialog, "getExistingDirectory",
            staticmethod(lambda *a, **k: opened.append(1) or ""))

        assert win._pick_case_from_library("t") is None
        assert told and not opened

    def test_a_single_library_is_browsed_without_asking_which(
        self, win, case, tmp_path, monkeypatch
    , choose_directory):
        import ui.mixins._case_ops as co
        from app_config import get_app_config

        get_app_config().add_case_library_dir(str(tmp_path))
        asked: list[int] = []
        monkeypatch.setattr(
            co.QInputDialog, "getItem", staticmethod(lambda *a, **k: asked.append(1) or ("", False)))
        choose_directory(case)

        assert win._pick_case_from_library("t") == str(case)
        assert asked == [], "asked which library when there is only one"

    def test_several_libraries_ask_which_one(self, win, case, tmp_path, monkeypatch, choose_directory):
        import ui.mixins._case_ops as co
        from app_config import get_app_config

        cfg = get_app_config()
        cfg.add_case_library_dir(str(tmp_path))
        cfg.add_case_library_dir(str(tmp_path / "second"))
        seen: list[list[str]] = []
        monkeypatch.setattr(
            co.QInputDialog, "getItem",
            staticmethod(lambda *a, **k: seen.append(list(a[3])) or (a[3][0], True)))
        choose_directory(case)

        assert win._pick_case_from_library("t") == str(case)
        assert seen and len(seen[0]) == 2

    def test_cancelling_the_library_choice_returns_nothing(self, win, tmp_path, monkeypatch):
        import ui.mixins._case_ops as co
        from app_config import get_app_config

        cfg = get_app_config()
        cfg.add_case_library_dir(str(tmp_path))
        cfg.add_case_library_dir(str(tmp_path / "second"))
        monkeypatch.setattr(
            co.QInputDialog, "getItem", staticmethod(lambda *a, **k: ("", False)))

        assert win._pick_case_from_library("t") is None


class TestSettingsActions:
    def test_setting_the_default_case_directory_persists_it(
        self, win, tmp_path, monkeypatch, choose_directory, answer_message_box
    ):
        from app_config import get_app_config

        choose_directory(tmp_path)
        answer_message_box(None)
        win.set_default_case_directory()
        assert get_app_config().get_default_case_dir() == str(tmp_path)

    def test_cancelling_leaves_it_alone(self, win, monkeypatch):
        import ui.mixins._case_ops as co
        from app_config import get_app_config

        before = get_app_config().get_default_case_dir()
        monkeypatch.setattr(
            co.QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: ""))
        win.set_default_case_directory()
        assert get_app_config().get_default_case_dir() == before

    def test_reset_window_size_restores_the_default(self, win, monkeypatch, answer_message_box):
        from app_config import get_app_config
        from app_config.defaults import DEFAULT_WINDOW_HEIGHT, DEFAULT_WINDOW_WIDTH

        win.resize(900, 640)
        monkeypatch.setattr(type(win), "_confirm", lambda self, *a, **k: True)
        answer_message_box(None)   # the Yes path ends in a modal "Size Reset" box
        win.reset_window_size()
        assert get_app_config().get_window_size() == [DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT]

    def test_reset_window_size_also_drops_the_saved_geometry(self, win, monkeypatch, answer_message_box):
        """Without this the reset does not survive a restart.

        `restore_session` reapplies the stored geometry blob, which wins over
        `window_size` -- so a reset that only rewrote `window_size` would be undone by
        the next launch and the window would come back the size just reset away from.
        The first version of this test asserted only the window_size half and passed
        happily with `clear_session_geometry()` deleted.
        """
        from app_config import get_app_config

        cfg = get_app_config()
        cfg.set_session_state({"geometry": "blob", "window_size": [900, 640], "upper_tab": "Tree"})
        monkeypatch.setattr(type(win), "_confirm", lambda self, *a, **k: True)
        answer_message_box(None)

        win.reset_window_size()

        state = cfg.get_session_state() or {}
        assert "geometry" not in state
        assert "window_size" not in state
        assert state.get("upper_tab") == "Tree", "unrelated layout was discarded too"

    def test_declining_the_reset_keeps_the_current_size(self, win, monkeypatch):
        from app_config import get_app_config

        get_app_config().set_window_size(900, 640)
        monkeypatch.setattr(type(win), "_confirm", lambda self, *a, **k: False)
        win.reset_window_size()
        assert get_app_config().get_window_size() == [900, 640]
