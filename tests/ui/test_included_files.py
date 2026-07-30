# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""End-to-end tests for `#include` support in MainWindow.

Exercises the whole chain the user sees: the include scan populating the file
list on case load, the read-only contract for a target outside the case
directory, "Open Included File", and "Copy into case...".

Each test builds a case plus a fake OpenFOAM `etc` tree on tmp_path and points
`services.include_scan.foam_etc_dirs` at it, so results never depend on the
machine having OpenFOAM installed. The shared `main_window` fixture
(tests/conftest.py) disables the terminal and blockmesh features.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import Qt

from model.file_list_model import INCLUDED_GROUP
from model.tree_model import FoamTreeModel
from services import include_scan
from ui.panels.file_list_panel import _INCLUDED_ROLE, _READ_ONLY_ROLE

_HEADER = """FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      controlDict;
}
"""


@pytest.fixture(autouse=True)
def _clear_scan_caches():
    include_scan.clear_scan_cache()
    include_scan.clear_foam_etc_cache()
    yield
    include_scan.clear_scan_cache()
    include_scan.clear_foam_etc_cache()


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _build_case(tmp_path: Path, control_dict_body: str) -> tuple[Path, Path]:
    """Return (case_dir, etc_root) with a controlDict holding the given body."""
    case = tmp_path / "case"
    _write(case / "system" / "controlDict", _HEADER + control_dict_body)
    etc = tmp_path / "install" / "etc"
    _write(etc / "caseDicts" / "setConstraintTypes", _HEADER + "constraint { type empty; }\n")
    return case, etc


def _use_etc(monkeypatch, etc: Path) -> None:
    monkeypatch.setattr(include_scan, "foam_etc_dirs", lambda: (etc,))


def _row(win, path) -> object | None:
    lst = win.file_list_panel._list
    for i in range(lst.count()):
        if lst.item(i).data(Qt.ItemDataRole.UserRole) == str(path):
            return lst.item(i)
    return None


def _headers(win) -> list[str]:
    from ui.panels.file_list_panel import _HEADER_GROUP_ROLE

    lst = win.file_list_panel._list
    return [
        lst.item(i).data(_HEADER_GROUP_ROLE)
        for i in range(lst.count())
        if lst.item(i).data(_HEADER_GROUP_ROLE) is not None
    ]


# ── the file list ─────────────────────────────────────────────────────────────


class TestIncludedFileList:
    def test_out_of_case_include_gets_included_group(self, main_window, tmp_path, monkeypatch):
        case, etc = _build_case(tmp_path, '#includeEtc "caseDicts/setConstraintTypes"\n')
        _use_etc(monkeypatch, etc)
        main_window._load_case_dir(str(case))

        target = etc / "caseDicts" / "setConstraintTypes"
        assert INCLUDED_GROUP in _headers(main_window)
        row = _row(main_window, target)
        assert row is not None
        assert row.data(_INCLUDED_ROLE) is True
        assert row.data(_READ_ONLY_ROLE) is True
        assert str(target) in main_window.state.read_only_files

    def test_in_case_include_joins_natural_group(self, main_window, tmp_path, monkeypatch):
        case, etc = _build_case(tmp_path, '#include "extraSettings"\n')
        target = _write(case / "system" / "extraSettings", _HEADER + "foo 1;\n")
        _use_etc(monkeypatch, etc)
        main_window._load_case_dir(str(case))

        assert INCLUDED_GROUP not in _headers(main_window)
        row = _row(main_window, target)
        assert row is not None
        assert row.data(_INCLUDED_ROLE) is True
        assert row.data(_READ_ONLY_ROLE) is False
        assert main_window.state.read_only_files == set()

    def test_already_listed_target_not_marked_included(self, main_window, tmp_path, monkeypatch):
        # system/fvSchemes is a TARGET_FILES entry, so it is listed anyway.
        case, etc = _build_case(tmp_path, '#include "fvSchemes"\n')
        target = _write(case / "system" / "fvSchemes", _HEADER + "ddtSchemes { default Euler; }\n")
        _use_etc(monkeypatch, etc)
        main_window._load_case_dir(str(case))

        row = _row(main_window, target)
        assert row is not None
        assert row.data(_INCLUDED_ROLE) is False

    def test_case_without_includes_is_unchanged(self, main_window, tmp_path, monkeypatch):
        case, etc = _build_case(tmp_path, "application simpleFoam;\n")
        _use_etc(monkeypatch, etc)
        main_window._load_case_dir(str(case))
        assert INCLUDED_GROUP not in _headers(main_window)
        assert main_window.state.read_only_files == set()

    def test_missing_include_is_not_listed(self, main_window, tmp_path, monkeypatch):
        case, etc = _build_case(tmp_path, '#include "nowhere"\n')
        _use_etc(monkeypatch, etc)
        main_window._load_case_dir(str(case))
        assert INCLUDED_GROUP not in _headers(main_window)


# ── read-only contract ────────────────────────────────────────────────────────


class TestReadOnlyIncludedFile:
    @pytest.fixture()
    def opened(self, main_window, tmp_path, monkeypatch):
        """Load a case and open its out-of-case include. Returns (win, target)."""
        case, etc = _build_case(tmp_path, '#includeEtc "caseDicts/setConstraintTypes"\n')
        _use_etc(monkeypatch, etc)
        main_window._load_case_dir(str(case))
        target = str(etc / "caseDicts" / "setConstraintTypes")
        main_window.load_selected_file(target)
        return main_window, target

    def test_predicate_reports_read_only(self, opened):
        win, target = opened
        assert win._is_read_only(target) is True
        assert win._is_read_only(str(Path(target).name)) is False

    def test_editor_is_read_only(self, opened):
        win, _target = opened
        assert win.editor_panel.editor.isReadOnly() is True

    def test_tree_model_withholds_editable_flag(self, opened):
        win, _target = opened
        model = win.state.current_model
        assert model.read_only is True
        index = model.index(0, FoamTreeModel.COL_VALUE)
        assert not (model.flags(index) & Qt.ItemFlag.ItemIsEditable)

    def test_mark_dirty_is_a_noop(self, opened):
        win, target = opened
        win._mark_dirty()
        assert win.state.text_dirty is False
        assert win.state.file_dirty.get(target, False) is False

    def test_save_file_refuses(self, opened):
        win, target = opened
        before = Path(target).read_text(encoding="utf-8")
        win.state.file_buffers[target] = "clobbered"
        win.save_file()
        assert Path(target).read_text(encoding="utf-8") == before

    def test_save_all_files_skips_it(self, opened):
        win, target = opened
        before = Path(target).read_text(encoding="utf-8")
        # Force the flag past _mark_dirty to prove the save path guards too.
        win.state.file_dirty[target] = True
        win.state.file_buffers[target] = "clobbered"
        win.save_all_files()
        assert Path(target).read_text(encoding="utf-8") == before

    def test_backup_refuses(self, opened):
        win, target = opened
        assert win._create_backup(target) is False
        assert list(Path(target).parent.glob("*.bak_*")) == []

    def test_apply_text_to_tree_refuses(self, opened):
        win, _target = opened
        win.editor_panel._editor.setReadOnly(False)
        win.editor_panel.set_text(_HEADER + "injected 1;\n")
        win.apply_text_to_tree()
        keys = [c.name for c in win.state.current_root.children]
        assert "injected" not in keys

    def test_editor_read_only_cleared_on_next_file(self, opened):
        win, _target = opened
        win.load_selected_file(str(Path(win.state.current_case_dir) / "system" / "controlDict"))
        assert win.editor_panel.editor.isReadOnly() is False
        assert win.state.current_model.read_only is False


# ── opening an included file from the tree ────────────────────────────────────


class TestOpenIncludedFile:
    def test_open_included_target_selects_file(self, main_window, tmp_path, monkeypatch):
        case, etc = _build_case(tmp_path, '#includeEtc "caseDicts/setConstraintTypes"\n')
        _use_etc(monkeypatch, etc)
        main_window._load_case_dir(str(case))
        main_window.load_selected_file(str(case / "system" / "controlDict"))

        main_window._open_included_target('#includeEtc "caseDicts/setConstraintTypes"')
        assert main_window.state.current_file == str(etc / "caseDicts" / "setConstraintTypes")

    def test_open_in_case_include(self, main_window, tmp_path, monkeypatch):
        case, etc = _build_case(tmp_path, '#include "extraSettings"\n')
        target = _write(case / "system" / "extraSettings", _HEADER + "foo 1;\n")
        _use_etc(monkeypatch, etc)
        main_window._load_case_dir(str(case))
        main_window.load_selected_file(str(case / "system" / "controlDict"))

        main_window._open_included_target('#include "extraSettings"')
        assert main_window.state.current_file == str(target)

    def test_unresolvable_include_reports_and_does_not_switch(
        self, main_window, tmp_path, monkeypatch
    ):
        case, etc = _build_case(tmp_path, '#include "nowhere"\n')
        _use_etc(monkeypatch, etc)
        main_window._load_case_dir(str(case))
        control = str(case / "system" / "controlDict")
        main_window.load_selected_file(control)

        main_window._open_included_target('#include "nowhere"')
        assert main_window.state.current_file == control
        assert "not found" in main_window.statusBar().currentMessage()

    def test_optional_missing_include_is_not_a_warning(self, main_window, tmp_path, monkeypatch):
        case, etc = _build_case(tmp_path, '#sinclude "nowhere"\n')
        _use_etc(monkeypatch, etc)
        main_window._load_case_dir(str(case))
        main_window.load_selected_file(str(case / "system" / "controlDict"))

        main_window._open_included_target('#sinclude "nowhere"')
        assert "Optional include" in main_window.statusBar().currentMessage()

    def test_non_include_directive_is_ignored(self, main_window, tmp_path, monkeypatch):
        case, etc = _build_case(tmp_path, "#eval{1+2}\n")
        _use_etc(monkeypatch, etc)
        main_window._load_case_dir(str(case))
        control = str(case / "system" / "controlDict")
        main_window.load_selected_file(control)

        main_window._open_included_target("#eval{1+2}")
        assert main_window.state.current_file == control

    def test_include_note_reaches_the_tree_tooltip(self, main_window, tmp_path, monkeypatch):
        case, etc = _build_case(tmp_path, '#includeEtc "caseDicts/setConstraintTypes"\n')
        _use_etc(monkeypatch, etc)
        main_window._load_case_dir(str(case))
        main_window.load_selected_file(str(case / "system" / "controlDict"))

        model = main_window.state.current_model
        directive = next(
            c for c in main_window.state.current_root.children if c.node_type == "directive_entry"
        )
        assert "setConstraintTypes" in (model.include_note(directive) or "")

    def test_missing_include_note_says_not_found(self, main_window, tmp_path, monkeypatch):
        case, etc = _build_case(tmp_path, '#include "nowhere"\n')
        _use_etc(monkeypatch, etc)
        main_window._load_case_dir(str(case))
        main_window.load_selected_file(str(case / "system" / "controlDict"))

        model = main_window.state.current_model
        directive = next(
            c for c in main_window.state.current_root.children if c.node_type == "directive_entry"
        )
        assert "not found" in (model.include_note(directive) or "")


# ── copy into case ────────────────────────────────────────────────────────────


class TestCopyIntoCase:
    def _prepare(self, main_window, tmp_path, monkeypatch, dest_name):
        case, etc = _build_case(tmp_path, '#includeEtc "caseDicts/setConstraintTypes"\n')
        _use_etc(monkeypatch, etc)
        main_window._load_case_dir(str(case))
        target = str(etc / "caseDicts" / "setConstraintTypes")

        from ui.mixins import _file_mgmt_ops

        monkeypatch.setattr(
            _file_mgmt_ops.QInputDialog, "getText", staticmethod(lambda *a, **k: (dest_name, True))
        )
        return case, target

    def test_creates_file_in_system(self, main_window, tmp_path, monkeypatch):
        case, target = self._prepare(
            main_window, tmp_path, monkeypatch, "system/setConstraintTypes"
        )
        main_window._on_copy_into_case_requested(target)

        dest = case / "system" / "setConstraintTypes"
        assert dest.is_file()
        assert dest.read_text(encoding="utf-8") == Path(target).read_text(encoding="utf-8")

    def test_copy_is_editable(self, main_window, tmp_path, monkeypatch):
        case, target = self._prepare(
            main_window, tmp_path, monkeypatch, "system/setConstraintTypes"
        )
        main_window._on_copy_into_case_requested(target)

        dest = str(case / "system" / "setConstraintTypes")
        assert main_window._is_read_only(dest) is False
        row = _row(main_window, dest)
        assert row is not None
        assert row.data(_READ_ONLY_ROLE) is False

    def test_registers_extra_file(self, main_window, tmp_path, monkeypatch):
        case, target = self._prepare(
            main_window, tmp_path, monkeypatch, "system/setConstraintTypes"
        )
        main_window._on_copy_into_case_requested(target)
        assert "system/setConstraintTypes" in (
            main_window.state.case_files_config.get_extra_files()
        )

    def test_refuses_existing_name(self, main_window, tmp_path, monkeypatch):
        case, target = self._prepare(main_window, tmp_path, monkeypatch, "system/controlDict")
        before = (case / "system" / "controlDict").read_text(encoding="utf-8")
        main_window._on_copy_into_case_requested(target)
        assert (case / "system" / "controlDict").read_text(encoding="utf-8") == before

    def test_refuses_destination_outside_the_case(self, main_window, tmp_path, monkeypatch):
        _case, target = self._prepare(main_window, tmp_path, monkeypatch, "../escaped")
        main_window._on_copy_into_case_requested(target)
        assert not (tmp_path / "escaped").exists()

    def test_preserves_other_buffers(self, main_window, tmp_path, monkeypatch):
        case, target = self._prepare(
            main_window, tmp_path, monkeypatch, "system/setConstraintTypes"
        )
        control = str(case / "system" / "controlDict")
        main_window.load_selected_file(control)
        # An unsaved edit lives in the editor, which _save_current_buffer
        # flushes on every file switch — so edit there, not in file_buffers.
        edited = _HEADER + "application editedByHand;\n"
        main_window.editor_panel.set_text(edited)
        main_window._mark_dirty()

        main_window._on_copy_into_case_requested(target)
        # _reload_file_list keeps buffers; _load_case_dir would have dropped them.
        assert main_window.state.file_buffers[control] == edited
        assert main_window.state.file_dirty[control] is True
