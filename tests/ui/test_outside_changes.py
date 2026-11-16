# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Files changed outside FoDE: the save guard and Reload File from Disk.

The case watcher sees entries added and removed, never a file rewritten in
place, so a buffer can go stale; these pin down that saving over such a file
asks first and that Reload File from Disk brings the outside version in.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

CONTROL = "FoamFile { version 2.0; format ascii; class dictionary; object controlDict; }\nendTime 1;\n"
FV = "FoamFile { version 2.0; format ascii; class dictionary; object fvSolution; }\nsolvers {}\n"


@pytest.fixture
def case(tmp_path: Path) -> Path:
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "controlDict").write_text(CONTROL)
    (tmp_path / "system" / "fvSolution").write_text(FV)
    return tmp_path


def outside_write(path: Path, text: str) -> None:
    """Another program rewriting *path* in place, a second later."""
    path.write_text(text)
    st = path.stat()
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))


def open_and_edit(win, path: Path, old: str, new: str) -> None:
    win.load_selected_file(str(path))
    win.editor_panel.set_text(win.editor_panel.get_text().replace(old, new))
    win.state.text_dirty = True
    win.state.file_dirty[str(path)] = True


class TestSaveFile:
    def test_unchanged_file_saves_without_asking(self, main_window, case, monkeypatch):
        win = main_window
        win._load_case_dir(str(case))
        path = case / "system" / "controlDict"
        open_and_edit(win, path, "endTime 1", "endTime 5")
        monkeypatch.setattr(win, "_confirm", lambda *a: pytest.fail("asked"))
        win.save_file()
        assert "endTime 5" in path.read_text()

    def test_changed_file_asks_and_cancel_keeps_the_outside_version(self, main_window, case, monkeypatch):
        win = main_window
        win._load_case_dir(str(case))
        path = case / "system" / "controlDict"
        open_and_edit(win, path, "endTime 1", "endTime 5")
        outside_write(path, CONTROL.replace("endTime 1", "endTime 7"))
        asked = []
        monkeypatch.setattr(win, "_confirm", lambda title, msg: asked.append(msg) or False)
        win.save_file()
        assert "endTime 7" in path.read_text()
        assert os.path.join("system", "controlDict") in asked[0]
        assert win.state.text_dirty  # the edit is still there, unsaved

    def test_changed_file_overwritten_when_confirmed(self, main_window, case, monkeypatch):
        win = main_window
        win._load_case_dir(str(case))
        path = case / "system" / "controlDict"
        open_and_edit(win, path, "endTime 1", "endTime 5")
        outside_write(path, CONTROL.replace("endTime 1", "endTime 7"))
        monkeypatch.setattr(win, "_confirm", lambda *a: True)
        win.save_file()
        assert "endTime 5" in path.read_text()
        # Saved: the next save of the same file asks nothing.
        monkeypatch.setattr(win, "_confirm", lambda *a: pytest.fail("asked again"))
        open_and_edit(win, path, "endTime 5", "endTime 6")
        win.save_file()

    def test_deleted_file_is_reported(self, main_window, case, monkeypatch):
        win = main_window
        win._load_case_dir(str(case))
        path = case / "system" / "controlDict"
        open_and_edit(win, path, "endTime 1", "endTime 5")
        path.unlink()
        asked = []
        monkeypatch.setattr(win, "_confirm", lambda title, msg: asked.append(msg) or False)
        win.save_file()
        assert "(deleted)" in asked[0]
        assert not path.exists()


class TestSaveCase:
    def test_save_the_others_only(self, main_window, case, monkeypatch):
        win = main_window
        win._load_case_dir(str(case))
        control = case / "system" / "controlDict"
        fv = case / "system" / "fvSolution"
        open_and_edit(win, control, "endTime 1", "endTime 5")
        open_and_edit(win, fv, "solvers {}", "solvers { p {} }")
        outside_write(control, CONTROL.replace("endTime 1", "endTime 7"))
        seen = {}
        monkeypatch.setattr(win, "_ask_overwrite_many", lambda changed: seen.update(changed) or False)
        win.save_all_files()
        assert list(seen) == [str(control)]
        assert "endTime 7" in control.read_text()
        assert "p {}" in fv.read_text()
        assert win.state.file_dirty[str(control)]

    def test_cancel_saves_nothing(self, main_window, case, monkeypatch):
        win = main_window
        win._load_case_dir(str(case))
        control = case / "system" / "controlDict"
        fv = case / "system" / "fvSolution"
        open_and_edit(win, control, "endTime 1", "endTime 5")
        open_and_edit(win, fv, "solvers {}", "solvers { p {} }")
        outside_write(control, CONTROL.replace("endTime 1", "endTime 7"))
        monkeypatch.setattr(win, "_ask_overwrite_many", lambda changed: None)
        win.save_all_files()
        assert "p {}" not in fv.read_text()

    def test_overwrite_them(self, main_window, case, monkeypatch):
        win = main_window
        win._load_case_dir(str(case))
        control = case / "system" / "controlDict"
        open_and_edit(win, control, "endTime 1", "endTime 5")
        outside_write(control, CONTROL.replace("endTime 1", "endTime 7"))
        monkeypatch.setattr(win, "_ask_overwrite_many", lambda changed: True)
        win.save_all_files()
        assert "endTime 5" in control.read_text()


def test_buffer_built_from_a_parse_read_is_guarded(main_window, case, monkeypatch):
    """Boundary edits and the like parse an unopened file, then write a buffer."""
    win = main_window
    win._load_case_dir(str(case))
    control = case / "system" / "controlDict"
    root = win._cache_parsed_root(str(control))
    win._write_root_to_buffer(str(control), root)
    outside_write(control, CONTROL.replace("endTime 1", "endTime 7"))
    assert win._changed_outside([str(control)]) == {str(control): "changed"}


class TestReload:
    def test_reload_clean_open_file(self, main_window, case):
        win = main_window
        win._load_case_dir(str(case))
        control = case / "system" / "controlDict"
        win.load_selected_file(str(control))
        outside_write(control, CONTROL.replace("endTime 1", "endTime 7"))
        win.reload_file_from_disk()
        assert "endTime 7" in win.editor_panel.get_text()
        assert win.state.current_file == str(control)
        assert not win.state.text_dirty
        assert win._changed_outside([str(control)]) == {}

    def test_reload_dirty_file_asks_first(self, main_window, case, monkeypatch):
        win = main_window
        win._load_case_dir(str(case))
        control = case / "system" / "controlDict"
        open_and_edit(win, control, "endTime 1", "endTime 5")
        outside_write(control, CONTROL.replace("endTime 1", "endTime 7"))
        monkeypatch.setattr(win, "_confirm", lambda *a: False)
        win.reload_file_from_disk()
        assert "endTime 5" in win.editor_panel.get_text()
        monkeypatch.setattr(win, "_confirm", lambda *a: True)
        win.reload_file_from_disk()
        assert "endTime 7" in win.editor_panel.get_text()
        assert not win.state.file_dirty.get(str(control))

    def test_reload_is_undoable(self, main_window, case, monkeypatch):
        win = main_window
        win._load_case_dir(str(case))
        control = case / "system" / "controlDict"
        open_and_edit(win, control, "endTime 1", "endTime 5")
        outside_write(control, CONTROL.replace("endTime 1", "endTime 7"))
        monkeypatch.setattr(win, "_confirm", lambda *a: True)
        win.reload_file_from_disk()
        win._end_undo_op()
        win._tree_undo()
        assert "endTime 5" in win.editor_panel.get_text()

    def test_reload_a_file_that_is_not_open(self, main_window, case):
        win = main_window
        win._load_case_dir(str(case))
        control = case / "system" / "controlDict"
        fv = case / "system" / "fvSolution"
        win.load_selected_file(str(control))
        win.load_selected_file(str(fv))
        outside_write(control, CONTROL.replace("endTime 1", "endTime 7"))
        win.reload_file_from_disk(str(control))
        assert str(control) not in win.state.file_buffers  # read afresh when opened
        assert win.state.current_file == str(fv)
        win.load_selected_file(str(control))
        assert "endTime 7" in win.editor_panel.get_text()

    def test_reload_a_deleted_file(self, main_window, case, monkeypatch):
        win = main_window
        win._load_case_dir(str(case))
        control = case / "system" / "controlDict"
        win.load_selected_file(str(control))
        control.unlink()
        errors = []
        monkeypatch.setattr(win, "_error", lambda title, msg: errors.append(msg))
        win.reload_file_from_disk()
        assert "no longer exists" in errors[0]
        assert win.state.current_file == str(control)


def test_case_switch_drops_the_stamps(main_window, case, tmp_path):
    win = main_window
    win._load_case_dir(str(case))
    win.load_selected_file(str(case / "system" / "controlDict"))
    assert win.state.disk_stamps
    win._close_case()
    assert win.state.disk_stamps == {}


def test_file_menu_offers_reload(main_window, case):
    win = main_window
    win._load_case_dir(str(case))
    panel = win.file_list_panel
    control = str(case / "system" / "controlDict")
    item = next(
        panel._list.item(i) for i in range(panel._list.count())
        if panel._list.item(i).data(256) == control
    )
    menu, handlers = panel._build_context_menu(item)
    reload_action = next(a for a in handlers if a.text() == "Reload from Disk")
    got = []
    panel.reload_file_requested.connect(got.append)
    handlers[reload_action]()
    assert got == [control]


def test_f5_is_reload_file_from_disk(main_window):
    actions = [a for a in main_window.findChildren(type(main_window._save_file_action))
               if a.shortcut().toString() == "F5"]
    assert [a.text() for a in actions] == ["Reload File from Disk"]
