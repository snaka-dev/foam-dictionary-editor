# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""
Tests for ui/file_list_panel.py.

Covers load_files display, header markers, signal emission, and the
backup_file_requested signal from the file-item context menu.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from model.file_list_model import (
    INCLUDED_GROUP,
    ROOT_GROUP,
    FileListModel,
    _group_name,
    _group_sort_key,
)
from services.case_loader import PolyMeshInfo
from ui.panels.file_list_panel import (
    _EXTRA_FILE_ROLE,
    _HEADER_GROUP_ROLE,
    _INCLUDED_ROLE,
    _READ_ONLY_ROLE,
    _SYMLINK_ROLE,
    _TEXT_ONLY_ROLE,
    FileListPanel,
    _has_unlisted_files,
    _make_header,
    _make_item,
    _make_mesh_indicator,
    _make_time_dirs_indicator,
    display_file_name,
    group_display_name,
)
from ui.theme import colors


@pytest.fixture
def panel(qapp):
    p = FileListPanel()
    yield p
    p.deleteLater()


# ── display_file_name ─────────────────────────────────────────────────────────

class TestDisplayFileName:
    def test_returns_parent_slash_name(self):
        assert display_file_name("/case/system/controlDict") == "system/controlDict"

    def test_constant_dir_prefix(self):
        assert display_file_name("/case/constant/transportProperties") == "constant/transportProperties"


# ── group_display_name ────────────────────────────────────────────────────────

class TestGroupDisplayName:
    def test_root_group_shows_case_root(self):
        assert group_display_name(".") == "case root"

    def test_other_groups_pass_through(self):
        assert group_display_name("system") == "system"
        assert group_display_name("0.orig") == "0.orig"


# ── _make_header ──────────────────────────────────────────────────────────────

class TestMakeHeader:
    def test_header_text_no_marker(self):
        item = _make_header("system")
        assert item.text() == "system"

    def test_header_text_with_marker(self):
        item = _make_header("system", has_unlisted=True)
        assert item.text() == "system [+]"

    def test_header_stores_group_name(self):
        item = _make_header("constant")
        assert item.data(_HEADER_GROUP_ROLE) == "constant"

    def test_header_not_selectable(self):
        item = _make_header("system")
        assert not (item.flags() & Qt.ItemIsSelectable)

    def test_header_is_enabled(self):
        item = _make_header("system")
        assert item.flags() & Qt.ItemIsEnabled


# ── _make_item ────────────────────────────────────────────────────────────────

class TestMakeItem:
    def test_item_stores_path(self, tmp_path):
        path = str(tmp_path / "system" / "controlDict")
        item = _make_item(path)
        assert item.data(Qt.UserRole) == path

    def test_item_has_no_header_role(self, tmp_path):
        item = _make_item(str(tmp_path / "system" / "controlDict"))
        assert item.data(_HEADER_GROUP_ROLE) is None


# ── _has_unlisted_files ───────────────────────────────────────────────────────

class TestHasUnlistedFiles:
    def test_returns_false_when_case_dir_is_none(self):
        assert _has_unlisted_files(None, "system", set()) is False

    def test_returns_false_for_field_dirs(self, tmp_path):
        (tmp_path / "0").mkdir()
        (tmp_path / "0" / "U").write_text("", encoding="utf-8")
        # 0/ is always fully loaded — never show [+]
        assert _has_unlisted_files(str(tmp_path), "0", set()) is False

    def test_returns_true_when_file_not_in_loaded_set(self, tmp_path):
        (tmp_path / "system").mkdir()
        (tmp_path / "system" / "myDict").write_text("", encoding="utf-8")
        assert _has_unlisted_files(str(tmp_path), "system", set()) is True

    def test_returns_false_when_all_files_loaded(self, tmp_path):
        (tmp_path / "system").mkdir()
        path = str(tmp_path / "system" / "myDict")
        (tmp_path / "system" / "myDict").write_text("", encoding="utf-8")
        assert _has_unlisted_files(str(tmp_path), "system", {path}) is False

    def test_returns_false_when_dir_missing(self, tmp_path):
        assert _has_unlisted_files(str(tmp_path), "system", set()) is False


# ── FileListPanel.load_files ──────────────────────────────────────────────────

class TestLoadFiles:
    def test_loads_files_and_adds_headers(self, panel, tmp_path):
        (tmp_path / "system").mkdir()
        path = str(tmp_path / "system" / "controlDict")
        (tmp_path / "system" / "controlDict").write_text("", encoding="utf-8")
        panel.load_files([path])
        texts = [panel._list.item(i).text() for i in range(panel._list.count())]
        assert "system" in texts  # header

    def test_header_shows_marker_for_unlisted_files(self, panel, tmp_path):
        (tmp_path / "system").mkdir()
        (tmp_path / "system" / "controlDict").write_text("", encoding="utf-8")
        (tmp_path / "system" / "fvSchemes").write_text("", encoding="utf-8")
        # only load controlDict — fvSchemes is unlisted
        path = str(tmp_path / "system" / "controlDict")
        panel.load_files([path], case_dir=str(tmp_path))
        header = panel._list.item(0)
        assert header.text() == "system [+]"

    def test_header_no_marker_when_all_loaded(self, panel, tmp_path):
        (tmp_path / "system").mkdir()
        path = str(tmp_path / "system" / "controlDict")
        (tmp_path / "system" / "controlDict").write_text("", encoding="utf-8")
        panel.load_files([path], case_dir=str(tmp_path))
        header = panel._list.item(0)
        assert header.text() == "system"

    def test_clear_empties_list(self, panel, tmp_path):
        (tmp_path / "system").mkdir()
        (tmp_path / "system" / "controlDict").write_text("", encoding="utf-8")
        panel.load_files([str(tmp_path / "system" / "controlDict")])
        panel.clear()
        assert panel._list.count() == 0


# ── backup_file_requested signal ──────────────────────────────────────────────

class TestBackupFileRequestedSignal:
    def test_signal_defined(self, panel):
        assert hasattr(panel, "backup_file_requested")

    def test_signal_connected_and_emitted(self, panel, tmp_path):
        """backup_file_requested emits the correct path."""
        (tmp_path / "system").mkdir()
        path = str(tmp_path / "system" / "controlDict")
        (tmp_path / "system" / "controlDict").write_text("", encoding="utf-8")
        panel.load_files([path])

        received: list[str] = []
        panel.backup_file_requested.connect(received.append)

        panel.backup_file_requested.emit(path)

        assert received == [path]


# ── _make_item extra role ─────────────────────────────────────────────────────

class TestMakeItemExtraRole:
    def test_default_item_has_no_extra_role(self, tmp_path):
        path = str(tmp_path / "system" / "controlDict")
        item = _make_item(path)
        assert item.data(_EXTRA_FILE_ROLE) is False

    def test_extra_item_has_extra_role(self, tmp_path):
        path = str(tmp_path / "system" / "myDict")
        item = _make_item(path, is_extra=True)
        assert item.data(_EXTRA_FILE_ROLE) is True


# ── text-only (run log) rows ──────────────────────────────────────────────────

class TestTextOnlyRows:
    def test_log_item_is_dimmed(self, tmp_path):
        item = _make_item(str(tmp_path / "log.blockMesh"))
        assert item.data(_TEXT_ONLY_ROLE) is True
        assert item.foreground().color() == QColor(colors().file_text_only_fg)

    def test_log_grey_wins_over_extra_blue(self, tmp_path):
        item = _make_item(str(tmp_path / "log.blockMesh"), is_extra=True)
        assert item.foreground().color() == QColor(colors().file_text_only_fg)

    def test_dictionary_item_not_dimmed(self, tmp_path):
        item = _make_item(str(tmp_path / "system" / "controlDict"))
        assert item.data(_TEXT_ONLY_ROLE) is False

    def test_dim_restored_after_dirty_cleared(self, panel, tmp_path):
        path = str(tmp_path / "log.blockMesh")
        (tmp_path / "log.blockMesh").write_text("", encoding="utf-8")
        panel.load_files([path], case_dir=str(tmp_path))
        item = panel._find_item_by_path(path)
        panel.mark_dirty(path, True)
        assert item.foreground().color() != QColor(colors().file_text_only_fg)
        panel.mark_dirty(path, False)
        assert item.foreground().color() == QColor(colors().file_text_only_fg)


# ── extra files indicator ─────────────────────────────────────────────────────

class TestExtraFilesIndicator:
    def test_indicator_shown_with_manage_label_when_no_extra_files(self, panel, tmp_path):
        (tmp_path / "system").mkdir()
        path = str(tmp_path / "system" / "controlDict")
        (tmp_path / "system" / "controlDict").write_text("", encoding="utf-8")
        panel.load_files([path], case_dir=str(tmp_path))
        assert not panel._extra_btn.isHidden()
        assert "Manage" in panel._extra_btn.text()

    def test_indicator_shown_when_extra_files_exist(self, panel, tmp_path):
        (tmp_path / "system").mkdir()
        path = str(tmp_path / "system" / "myDict")
        (tmp_path / "system" / "myDict").write_text("", encoding="utf-8")
        panel.load_files([path], case_dir=str(tmp_path), extra_files=["system/myDict"])
        assert not panel._extra_btn.isHidden()

    def test_indicator_text_shows_count(self, panel, tmp_path):
        (tmp_path / "system").mkdir()
        path = str(tmp_path / "system" / "myDict")
        (tmp_path / "system" / "myDict").write_text("", encoding="utf-8")
        panel.load_files([path], case_dir=str(tmp_path), extra_files=["system/myDict"])
        assert "1" in panel._extra_btn.text()

    def test_indicator_hidden_after_clear(self, panel, tmp_path):
        (tmp_path / "system").mkdir()
        path = str(tmp_path / "system" / "myDict")
        (tmp_path / "system" / "myDict").write_text("", encoding="utf-8")
        panel.load_files([path], case_dir=str(tmp_path), extra_files=["system/myDict"])
        panel.clear()
        assert panel._extra_btn.isHidden()


# ── extra file items in load_files ────────────────────────────────────────────

class TestExtraFileItems:
    def test_extra_file_item_has_extra_role(self, panel, tmp_path):
        (tmp_path / "system").mkdir()
        path = str(tmp_path / "system" / "myDict")
        (tmp_path / "system" / "myDict").write_text("", encoding="utf-8")
        panel.load_files([path], case_dir=str(tmp_path), extra_files=["system/myDict"])
        # find the file item (skip header)
        file_item = None
        for i in range(panel._list.count()):
            item = panel._list.item(i)
            if item.data(Qt.UserRole) == path:
                file_item = item
                break
        assert file_item is not None
        assert file_item.data(_EXTRA_FILE_ROLE) is True

    def test_default_file_item_has_no_extra_role(self, panel, tmp_path):
        (tmp_path / "system").mkdir()
        path = str(tmp_path / "system" / "controlDict")
        (tmp_path / "system" / "controlDict").write_text("", encoding="utf-8")
        panel.load_files([path], case_dir=str(tmp_path))
        file_item = None
        for i in range(panel._list.count()):
            item = panel._list.item(i)
            if item.data(Qt.UserRole) == path:
                file_item = item
                break
        assert file_item is not None
        assert file_item.data(_EXTRA_FILE_ROLE) is False


# ── manage / remove signals ───────────────────────────────────────────────────

class TestManageAndRemoveSignals:
    def test_manage_extra_files_requested_signal_defined(self, panel):
        assert hasattr(panel, "manage_extra_files_requested")

    def test_manage_extra_files_requested_emitted(self, panel):
        received: list[bool] = []
        panel.manage_extra_files_requested.connect(lambda: received.append(True))
        panel.manage_extra_files_requested.emit()
        assert received == [True]

    def test_remove_extra_file_requested_signal_defined(self, panel):
        assert hasattr(panel, "remove_extra_file_requested")

    def test_remove_extra_file_requested_emitted(self, panel, tmp_path):
        path = str(tmp_path / "system" / "myDict")
        received: list[str] = []
        panel.remove_extra_file_requested.connect(received.append)
        panel.remove_extra_file_requested.emit(path)
        assert received == [path]


# ── manual refresh ─────────────────────────────────────────────────────────────

class TestRefreshRequested:
    def test_refresh_requested_signal_defined(self, panel):
        assert hasattr(panel, "refresh_requested")

    def test_refresh_requested_emitted(self, panel):
        received: list[bool] = []
        panel.refresh_requested.connect(lambda: received.append(True))
        panel.refresh_requested.emit()
        assert received == [True]

    def test_refresh_button_click_emits_signal(self, panel):
        received: list[bool] = []
        panel.refresh_requested.connect(lambda: received.append(True))
        panel._refresh_btn.click()
        assert received == [True]

    def test_delete_dir_requested_signal_defined(self, panel):
        assert hasattr(panel, "delete_dir_requested")

    def test_delete_dir_requested_emitted(self, panel, tmp_path):
        received: list[tuple] = []
        panel.delete_dir_requested.connect(lambda c, g: received.append((c, g)))
        panel.delete_dir_requested.emit(str(tmp_path), "0")
        assert received == [(str(tmp_path), "0")]


# ── _group_name with case_dir ─────────────────────────────────────────────────

class TestGroupName:
    def test_single_level_group(self, tmp_path):
        path = str(tmp_path / "system" / "controlDict")
        assert _group_name(path, str(tmp_path)) == "system"

    def test_two_level_group(self, tmp_path):
        path = str(tmp_path / "system" / "region1" / "fvSchemes")
        assert _group_name(path, str(tmp_path)) == "system/region1"

    def test_constant_region(self, tmp_path):
        path = str(tmp_path / "constant" / "fluid" / "thermophysicalProperties")
        assert _group_name(path, str(tmp_path)) == "constant/fluid"

    def test_fallback_without_case_dir(self, tmp_path):
        path = str(tmp_path / "system" / "controlDict")
        assert _group_name(path) == "system"


# ── _group_sort_key ───────────────────────────────────────────────────────────

class TestGroupSortKey:
    def test_system_before_constant(self):
        assert _group_sort_key("system") < _group_sort_key("constant")

    def test_constant_before_field(self):
        assert _group_sort_key("constant") < _group_sort_key("0")

    def test_region_group_after_parent(self):
        assert _group_sort_key("system") < _group_sort_key("system/region1")

    def test_region_groups_sorted_by_name(self):
        assert _group_sort_key("system/air") < _group_sort_key("system/water")

    def test_system_regions_before_constant(self):
        assert _group_sort_key("system/region1") < _group_sort_key("constant")

    def test_constant_regions_before_field(self):
        assert _group_sort_key("constant/region1") < _group_sort_key("0")


# ── MultiRegion file list display ─────────────────────────────────────────────

class TestMultiRegionDisplay:
    def _make_region(self, tmp_path, region: str):
        (tmp_path / "system" / region).mkdir(parents=True)
        (tmp_path / "constant" / region).mkdir(parents=True)
        (tmp_path / "system" / region / "fvSchemes").write_text("", encoding="utf-8")
        (tmp_path / "constant" / region / "thermophysicalProperties").write_text("", encoding="utf-8")

    def _get_header_texts(self, panel) -> list[str]:
        return [
            panel._list.item(i).text()
            for i in range(panel._list.count())
            if panel._list.item(i).data(_HEADER_GROUP_ROLE) is not None
        ]

    def test_region_groups_shown_as_headers(self, panel, tmp_path):
        self._make_region(tmp_path, "fluid")
        sys_path = str(tmp_path / "system" / "fluid" / "fvSchemes")
        const_path = str(tmp_path / "constant" / "fluid" / "thermophysicalProperties")
        panel.load_files([sys_path, const_path], case_dir=str(tmp_path))
        headers = self._get_header_texts(panel)
        assert "system/fluid" in headers
        assert "constant/fluid" in headers

    def test_region_files_under_correct_group(self, panel, tmp_path):
        self._make_region(tmp_path, "solid")
        path = str(tmp_path / "system" / "solid" / "fvSchemes")
        panel.load_files([path], case_dir=str(tmp_path))
        headers = self._get_header_texts(panel)
        assert "system/solid" in headers

    def test_system_region_before_constant_in_order(self, panel, tmp_path):
        self._make_region(tmp_path, "fluid")
        paths = [
            str(tmp_path / "constant" / "fluid" / "thermophysicalProperties"),
            str(tmp_path / "system" / "fluid" / "fvSchemes"),
        ]
        panel.load_files(paths, case_dir=str(tmp_path))
        headers = self._get_header_texts(panel)
        assert headers.index("system/fluid") < headers.index("constant/fluid")

    def test_two_regions_both_shown(self, panel, tmp_path):
        self._make_region(tmp_path, "region1")
        self._make_region(tmp_path, "region2")
        paths = [
            str(tmp_path / "system" / "region1" / "fvSchemes"),
            str(tmp_path / "system" / "region2" / "fvSchemes"),
        ]
        panel.load_files(paths, case_dir=str(tmp_path))
        headers = self._get_header_texts(panel)
        assert "system/region1" in headers
        assert "system/region2" in headers


# ── symlink items ─────────────────────────────────────────────────────────────

def _make_symlink(link: Path, target: Path):
    """Create a symlink; skip the test if the platform does not support it."""
    import pytest
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported on this platform/user account")


class TestSymlinkItems:
    def test_regular_item_symlink_role_false(self, tmp_path):
        path = str(tmp_path / "system" / "controlDict")
        item = _make_item(path)
        assert item.data(_SYMLINK_ROLE) is False

    def test_symlink_item_symlink_role_true(self, tmp_path):
        (tmp_path / "system").mkdir()
        target = tmp_path / "system" / "controlDict"
        target.write_text("", encoding="utf-8")
        link = tmp_path / "system" / "controlDictLink"
        _make_symlink(link, target)
        item = _make_item(str(link), is_symlink=True)
        assert item.data(_SYMLINK_ROLE) is True

    def test_symlink_item_has_marker_in_text(self, tmp_path):
        (tmp_path / "system").mkdir()
        target = tmp_path / "system" / "controlDict"
        target.write_text("", encoding="utf-8")
        link = tmp_path / "system" / "controlDictLink"
        _make_symlink(link, target)
        item = _make_item(str(link), is_symlink=True)
        assert "⇢" in item.text()

    def test_symlink_item_has_target_in_tooltip(self, tmp_path):
        (tmp_path / "system").mkdir()
        target = tmp_path / "system" / "controlDict"
        target.write_text("", encoding="utf-8")
        link = tmp_path / "system" / "controlDictLink"
        _make_symlink(link, target)
        item = _make_item(str(link), is_symlink=True)
        assert "⇢" in item.toolTip()

    def test_symlink_item_is_italic(self, tmp_path):
        (tmp_path / "system").mkdir()
        target = tmp_path / "system" / "controlDict"
        target.write_text("", encoding="utf-8")
        link = tmp_path / "system" / "controlDictLink"
        _make_symlink(link, target)
        item = _make_item(str(link), is_symlink=True)
        assert item.font().italic()

    def test_regular_item_not_italic(self, tmp_path):
        path = str(tmp_path / "system" / "controlDict")
        item = _make_item(path)
        assert not item.font().italic()

    def test_mark_dirty_preserves_symlink_marker(self, panel, tmp_path):
        (tmp_path / "system").mkdir()
        target = tmp_path / "system" / "controlDict"
        target.write_text("", encoding="utf-8")
        link = tmp_path / "system" / "controlDictLink"
        _make_symlink(link, target)
        panel.load_files([str(link)], case_dir=str(tmp_path))
        panel.mark_dirty(str(link), False)
        for i in range(panel._list.count()):
            item = panel._list.item(i)
            if item.data(Qt.UserRole) == str(link):
                assert "⇢" in item.text()
                return
        assert False, "symlink item not found"

    def test_mark_dirty_preserves_symlink_marker_when_dirty(self, panel, tmp_path):
        (tmp_path / "system").mkdir()
        target = tmp_path / "system" / "controlDict"
        target.write_text("", encoding="utf-8")
        link = tmp_path / "system" / "controlDictLink"
        _make_symlink(link, target)
        panel.load_files([str(link)], case_dir=str(tmp_path))
        panel.mark_dirty(str(link), True)
        for i in range(panel._list.count()):
            item = panel._list.item(i)
            if item.data(Qt.UserRole) == str(link):
                assert "⇢" in item.text()
                assert "*" in item.text()
                return
        assert False, "symlink item not found"

    def test_load_files_detects_symlink(self, panel, tmp_path):
        (tmp_path / "system").mkdir()
        target = tmp_path / "system" / "controlDict"
        target.write_text("", encoding="utf-8")
        link = tmp_path / "system" / "controlDictLink"
        _make_symlink(link, target)
        panel.load_files([str(link)], case_dir=str(tmp_path))
        for i in range(panel._list.count()):
            item = panel._list.item(i)
            if item.data(Qt.UserRole) == str(link):
                assert item.data(_SYMLINK_ROLE) is True
                assert "⇢" in item.text()
                return
        assert False, "symlink item not found in panel"


# ── included items ────────────────────────────────────────────────────────────

def _find_row(panel, path: Path | str):
    for i in range(panel._list.count()):
        item = panel._list.item(i)
        if item.data(Qt.UserRole) == str(path):
            return item
    return None


class TestIncludedItems:
    def test_regular_item_included_role_false(self, tmp_path):
        item = _make_item(str(tmp_path / "system" / "controlDict"))
        assert item.data(_INCLUDED_ROLE) is False
        assert item.data(_READ_ONLY_ROLE) is False

    def test_included_item_has_marker_in_text(self, tmp_path):
        item = _make_item(str(tmp_path / "constant" / "caseSettings"), is_included=True)
        assert "↳" in item.text()

    def test_included_item_tooltip_names_origin(self, tmp_path):
        item = _make_item(
            str(tmp_path / "constant" / "caseSettings"),
            is_included=True,
            origin="system/controlDict",
        )
        assert "system/controlDict" in item.toolTip()

    def test_read_only_item_is_italic(self, tmp_path):
        item = _make_item(str(tmp_path / "etc" / "x"), is_included=True, is_read_only=True)
        assert item.font().italic() is True

    def test_read_only_item_tooltip_says_why(self, tmp_path):
        item = _make_item(str(tmp_path / "etc" / "x"), is_included=True, is_read_only=True)
        assert "read-only" in item.toolTip()

    def test_read_only_item_uses_its_own_colour(self, tmp_path):
        item = _make_item(str(tmp_path / "etc" / "x"), is_included=True, is_read_only=True)
        assert item.foreground().color() == QColor(colors().file_read_only_fg)

    def test_in_case_include_is_not_read_only(self, tmp_path):
        (tmp_path / "constant").mkdir()
        target = tmp_path / "constant" / "caseSettings"
        target.write_text("", encoding="utf-8")
        panel_model = FileListModel()
        panel_model.load(
            [str(target)],
            case_dir=str(tmp_path),
            included_files={str(target): "system/controlDict"},
        )
        assert panel_model.is_included(str(target)) is True
        assert panel_model.is_read_only(str(target)) is False

    def test_mark_dirty_preserves_included_marker(self, panel, tmp_path):
        (tmp_path / "constant").mkdir()
        target = tmp_path / "constant" / "caseSettings"
        target.write_text("", encoding="utf-8")
        panel.load_files(
            [str(target)],
            case_dir=str(tmp_path),
            included_files={str(target): "system/controlDict"},
        )
        panel.mark_dirty(str(target), True)
        item = _find_row(panel, target)
        assert item is not None
        assert "↳" in item.text()
        assert "*" in item.text()

    def test_out_of_case_include_lands_in_included_group(self, panel, tmp_path):
        case = tmp_path / "case"
        (case / "system").mkdir(parents=True)
        outside = tmp_path / "install" / "etc" / "caseDicts" / "setConstraintTypes"
        outside.parent.mkdir(parents=True)
        outside.write_text("", encoding="utf-8")
        panel.load_files(
            [str(outside)],
            case_dir=str(case),
            included_files={str(outside): "0/U"},
        )
        headers = [
            panel._list.item(i).data(_HEADER_GROUP_ROLE)
            for i in range(panel._list.count())
            if panel._list.item(i).data(_HEADER_GROUP_ROLE) is not None
        ]
        assert INCLUDED_GROUP in headers
        item = _find_row(panel, outside)
        assert item is not None
        assert item.data(_READ_ONLY_ROLE) is True

    def test_included_group_display_name(self):
        assert group_display_name(INCLUDED_GROUP) == "included files"

    def test_included_group_has_no_plus_marker(self, tmp_path):
        # It is a bucket, not a directory — [+] would be meaningless.
        assert _has_unlisted_files(str(tmp_path), INCLUDED_GROUP, set()) is False

    def test_included_group_sorts_after_case_root(self):
        assert _group_sort_key(INCLUDED_GROUP) > _group_sort_key(ROOT_GROUP)
        assert _group_sort_key(INCLUDED_GROUP) > _group_sort_key("system")


# ── mark_dirty preserves extra-file color ─────────────────────────────────────

class TestMarkDirtyExtraFileColor:
    def _load_extra(self, panel, tmp_path) -> str:
        (tmp_path / "system").mkdir(exist_ok=True)
        path = str(tmp_path / "system" / "myDict")
        (tmp_path / "system" / "myDict").write_text("", encoding="utf-8")
        panel.load_files([path], case_dir=str(tmp_path), extra_files=["system/myDict"])
        return path

    def _find_item(self, panel, path: str):
        for i in range(panel._list.count()):
            item = panel._list.item(i)
            if item.data(Qt.UserRole) == path:
                return item
        return None

    def test_extra_file_keeps_blue_color_after_mark_dirty_false(self, panel, tmp_path):
        """mark_dirty(False) must restore the extra-file blue color, not clear it."""
        path = self._load_extra(panel, tmp_path)
        panel.mark_dirty(path, False)
        item = self._find_item(panel, path)
        assert item is not None
        assert item.foreground().color() == QColor(colors().file_extra_fg)

    def test_extra_file_turns_orange_when_dirty(self, panel, tmp_path):
        """mark_dirty(True) overrides extra-file color with the dirty orange."""
        from PySide6.QtGui import QColor
        path = self._load_extra(panel, tmp_path)
        panel.mark_dirty(path, True)
        item = self._find_item(panel, path)
        assert item is not None
        assert item.foreground().color() == QColor("#CC6600")

    def test_extra_file_restores_blue_after_dirty_cleared(self, panel, tmp_path):
        """After dirty is set then cleared, blue color is restored for extra files."""
        path = self._load_extra(panel, tmp_path)
        panel.mark_dirty(path, True)
        panel.mark_dirty(path, False)
        item = self._find_item(panel, path)
        assert item is not None
        assert item.foreground().color() == QColor(colors().file_extra_fg)

    def test_regular_file_color_cleared_after_mark_dirty_false(self, panel, tmp_path):
        """mark_dirty(False) on a non-extra file clears the foreground color."""
        (tmp_path / "system").mkdir(exist_ok=True)
        path = str(tmp_path / "system" / "controlDict")
        (tmp_path / "system" / "controlDict").write_text("", encoding="utf-8")
        panel.load_files([path], case_dir=str(tmp_path))
        panel.mark_dirty(path, True)
        panel.mark_dirty(path, False)
        item = self._find_item(panel, path)
        assert item is not None
        # QBrush with no color set returns a default-constructed brush
        assert item.data(Qt.ForegroundRole) is None


# ── _make_time_dirs_indicator ─────────────────────────────────────────────────

class TestMakeTimeDirsIndicator:
    def test_label_starts_with_results(self):
        item = _make_time_dirs_indicator(["1", "2"])
        assert item.text().startswith("Results:")

    def test_label_contains_dir_names(self):
        item = _make_time_dirs_indicator(["0.5", "1", "2"])
        text = item.text()
        assert "0.5" in text
        assert "1" in text
        assert "2" in text

    def test_label_truncates_beyond_six(self):
        dirs = ["1", "2", "3", "4", "5", "6", "7", "8"]
        item = _make_time_dirs_indicator(dirs)
        assert "(+2 more)" in item.text()
        assert "7" not in item.text()
        assert "8" not in item.text()

    def test_label_no_truncation_at_six(self):
        dirs = ["1", "2", "3", "4", "5", "6"]
        item = _make_time_dirs_indicator(dirs)
        assert "more" not in item.text()

    def test_item_is_bold(self):
        item = _make_time_dirs_indicator(["1"])
        assert item.font().bold()

    def test_item_is_not_selectable(self):
        item = _make_time_dirs_indicator(["1"])
        assert not (item.flags() & Qt.ItemIsSelectable)

    def test_item_is_enabled(self):
        item = _make_time_dirs_indicator(["1"])
        assert item.flags() & Qt.ItemIsEnabled

    def test_tooltip_single_dir(self):
        item = _make_time_dirs_indicator(["1"])
        tip = item.toolTip()
        assert "1" in tip
        assert "result dir" in tip

    def test_tooltip_multiple_dirs_shows_range(self):
        item = _make_time_dirs_indicator(["0.5", "1", "2"])
        tip = item.toolTip()
        assert "0.5" in tip
        assert "2" in tip

    def test_tooltip_shows_count(self):
        item = _make_time_dirs_indicator(["1", "2", "3"])
        assert "3" in item.toolTip()


# ── time-dirs indicator in FileListPanel.load_files ───────────────────────────

class TestTimeDirsInPanel:
    def _make_case(self, tmp_path):
        (tmp_path / "system").mkdir()
        (tmp_path / "system" / "controlDict").write_text("", encoding="utf-8")
        return str(tmp_path / "system" / "controlDict")

    def test_indicator_added_when_time_dirs_exist(self, panel, tmp_path):
        path = self._make_case(tmp_path)
        (tmp_path / "1").mkdir()
        panel.load_files([path], case_dir=str(tmp_path))
        texts = [panel._list.item(i).text() for i in range(panel._list.count())]
        assert any(t.startswith("Results:") for t in texts)

    def test_indicator_not_added_when_no_time_dirs(self, panel, tmp_path):
        path = self._make_case(tmp_path)
        panel.load_files([path], case_dir=str(tmp_path))
        texts = [panel._list.item(i).text() for i in range(panel._list.count())]
        assert not any(t.startswith("Results:") for t in texts)

    def test_indicator_not_added_when_only_field_dirs_exist(self, panel, tmp_path):
        path = self._make_case(tmp_path)
        (tmp_path / "0").mkdir()
        (tmp_path / "0.orig").mkdir()
        panel.load_files([path], case_dir=str(tmp_path))
        texts = [panel._list.item(i).text() for i in range(panel._list.count())]
        assert not any(t.startswith("Results:") for t in texts)

    def test_indicator_shows_multiple_time_dirs(self, panel, tmp_path):
        path = self._make_case(tmp_path)
        (tmp_path / "0.5").mkdir()
        (tmp_path / "1").mkdir()
        panel.load_files([path], case_dir=str(tmp_path))
        texts = [panel._list.item(i).text() for i in range(panel._list.count())]
        indicator = next(t for t in texts if t.startswith("Results:"))
        assert "0.5" in indicator
        assert "1" in indicator

    def test_indicator_not_added_without_case_dir(self, panel, tmp_path):
        """Without case_dir, detect_time_dirs cannot run; no indicator shown."""
        (tmp_path / "system").mkdir()
        path = str(tmp_path / "system" / "controlDict")
        (tmp_path / "system" / "controlDict").write_text("", encoding="utf-8")
        panel.load_files([path])  # no case_dir
        texts = [panel._list.item(i).text() for i in range(panel._list.count())]
        assert not any(t.startswith("Results:") for t in texts)


# ── _make_mesh_indicator ───────────────────────────────────────────────────────

class TestMakeMeshIndicator:
    def test_label_shows_cell_count(self):
        info = PolyMeshInfo(n_points=9261, n_cells=8000, n_faces=25200, stale=False)
        item = _make_mesh_indicator(info)
        assert "constant/polyMesh" in item.text()
        assert "8,000 cells" in item.text()

    def test_label_present_only_when_counts_unavailable(self):
        info = PolyMeshInfo(n_points=None, n_cells=None, n_faces=None, stale=False)
        item = _make_mesh_indicator(info)
        assert "present" in item.text()

    def test_stale_label_flagged(self):
        info = PolyMeshInfo(n_points=9261, n_cells=8000, n_faces=25200, stale=True)
        item = _make_mesh_indicator(info)
        assert "stale" in item.text()

    def test_fresh_not_flagged_stale(self):
        info = PolyMeshInfo(n_points=9261, n_cells=8000, n_faces=25200, stale=False)
        item = _make_mesh_indicator(info)
        assert "stale" not in item.text()

    def test_item_is_bold(self):
        info = PolyMeshInfo(n_points=1, n_cells=1, n_faces=1, stale=False)
        assert _make_mesh_indicator(info).font().bold()

    def test_item_is_not_selectable(self):
        info = PolyMeshInfo(n_points=1, n_cells=1, n_faces=1, stale=False)
        item = _make_mesh_indicator(info)
        assert not (item.flags() & Qt.ItemIsSelectable)

    def test_item_is_enabled(self):
        info = PolyMeshInfo(n_points=1, n_cells=1, n_faces=1, stale=False)
        assert _make_mesh_indicator(info).flags() & Qt.ItemIsEnabled

    def test_tooltip_shows_counts(self):
        info = PolyMeshInfo(n_points=9261, n_cells=8000, n_faces=25200, stale=False)
        tip = _make_mesh_indicator(info).toolTip()
        assert "9,261" in tip
        assert "8,000" in tip
        assert "25,200" in tip


# ── mesh indicator in FileListPanel.load_files ────────────────────────────────

class TestMeshIndicatorInPanel:
    def _make_case(self, tmp_path):
        (tmp_path / "system").mkdir()
        (tmp_path / "system" / "controlDict").write_text("", encoding="utf-8")
        return str(tmp_path / "system" / "controlDict")

    def _write_owner(self, tmp_path):
        poly_mesh = tmp_path / "constant" / "polyMesh"
        poly_mesh.mkdir(parents=True)
        (poly_mesh / "owner").write_text(
            'FoamFile\n{\n    note        "nPoints:9261  nCells:8000  '
            'nFaces:25200  nInternalFaces:22800";\n}\n',
            encoding="utf-8",
        )

    def test_indicator_added_when_mesh_exists(self, panel, tmp_path):
        path = self._make_case(tmp_path)
        self._write_owner(tmp_path)
        panel.load_files([path], case_dir=str(tmp_path))
        texts = [panel._list.item(i).text() for i in range(panel._list.count())]
        assert any("constant/polyMesh" in t for t in texts)

    def test_indicator_not_added_when_no_mesh(self, panel, tmp_path):
        path = self._make_case(tmp_path)
        panel.load_files([path], case_dir=str(tmp_path))
        texts = [panel._list.item(i).text() for i in range(panel._list.count())]
        assert not any("constant/polyMesh" in t for t in texts)

    def test_indicator_not_added_without_case_dir(self, panel, tmp_path):
        """Without case_dir, detect_poly_mesh cannot run; no indicator shown."""
        path = self._make_case(tmp_path)
        self._write_owner(tmp_path)
        panel.load_files([path])  # no case_dir
        texts = [panel._list.item(i).text() for i in range(panel._list.count())]
        assert not any("constant/polyMesh" in t for t in texts)


# ── "Changed files only" diff filter ─────────────────────────────────────────

class TestDiffFilter:
    def _load_two_files(self, panel, tmp_path) -> tuple[str, str]:
        (tmp_path / "system").mkdir()
        p1 = str(tmp_path / "system" / "controlDict")
        p2 = str(tmp_path / "system" / "fvSchemes")
        (tmp_path / "system" / "controlDict").write_text("", encoding="utf-8")
        (tmp_path / "system" / "fvSchemes").write_text("", encoding="utf-8")
        panel.load_files([p1, p2], case_dir=str(tmp_path))
        return p1, p2

    def test_checkbox_hidden_by_default(self, panel):
        assert panel._changed_only_cb.isHidden()

    def test_set_diff_filter_enabled_shows_checkbox(self, panel, tmp_path):
        self._load_two_files(panel, tmp_path)
        panel.set_diff_filter_enabled(True)
        assert not panel._changed_only_cb.isHidden()

    def test_set_diff_filter_enabled_false_hides_checkbox(self, panel, tmp_path):
        self._load_two_files(panel, tmp_path)
        panel.set_diff_filter_enabled(True)
        panel.set_diff_filter_enabled(False)
        assert panel._changed_only_cb.isHidden()

    def test_set_diff_filter_enabled_false_unchecks_checkbox(self, panel, tmp_path):
        self._load_two_files(panel, tmp_path)
        panel.set_diff_filter_enabled(True)
        panel._changed_only_cb.setChecked(True)
        panel.set_diff_filter_enabled(False)
        assert not panel._changed_only_cb.isChecked()

    def test_filter_hides_zero_diff_items(self, panel, tmp_path):
        p1, p2 = self._load_two_files(panel, tmp_path)
        panel.mark_diff(p1, 0)
        panel.mark_diff(p2, 3)
        panel.set_diff_filter_enabled(True)
        panel._changed_only_cb.setChecked(True)
        item1 = panel._find_item_by_path(p1)
        item2 = panel._find_item_by_path(p2)
        assert item1.isHidden()
        assert not item2.isHidden()

    def test_filter_shows_all_when_unchecked(self, panel, tmp_path):
        p1, p2 = self._load_two_files(panel, tmp_path)
        panel.mark_diff(p1, 0)
        panel.mark_diff(p2, 3)
        panel.set_diff_filter_enabled(True)
        panel._changed_only_cb.setChecked(True)
        panel._changed_only_cb.setChecked(False)
        item1 = panel._find_item_by_path(p1)
        assert not item1.isHidden()

    def test_filter_never_hides_headers(self, panel, tmp_path):
        self._load_two_files(panel, tmp_path)
        panel.set_diff_filter_enabled(True)
        panel._changed_only_cb.setChecked(True)
        for i in range(panel._list.count()):
            item = panel._list.item(i)
            if item.data(_HEADER_GROUP_ROLE) is not None:
                assert not item.isHidden()

    def test_mark_diff_updates_visibility_when_filter_active(self, panel, tmp_path):
        p1, _ = self._load_two_files(panel, tmp_path)
        panel.set_diff_filter_enabled(True)
        panel._changed_only_cb.setChecked(True)
        panel.mark_diff(p1, 0)
        item = panel._find_item_by_path(p1)
        assert item.isHidden()
        panel.mark_diff(p1, 5)
        assert not item.isHidden()


# ── long paths elide instead of scrolling sideways ──────────────────────────
#
# `constant/transportProperties` used to render as `constant/transportPropertie`
# behind a horizontal scrollbar: QListWidget had no elide mode and nothing
# turned the scrollbar off. Turning the horizontal bar off makes QListView
# clamp item width to the viewport and elide instead -- per this repo's
# recorded lesson on measuring Qt pane overflow, checked via the scrollbar's
# range, not sizeHint(), which reports the same number whether or not
# anything on screen actually got truncated.

# Narrow enough that "constant/transportProperties" cannot fit unelided.
_NARROW_WIDTH = 160


class TestLongPathsDoNotScrollSideways:
    def test_no_horizontal_scrollbar_at_narrow_width(self, panel, tmp_path, qapp):
        (tmp_path / "constant").mkdir()
        path = tmp_path / "constant" / "transportProperties"
        path.write_text("", encoding="utf-8")
        panel.resize(_NARROW_WIDTH, 300)
        panel.show()
        panel.load_files([str(path)], case_dir=str(tmp_path))
        # QListView only recomputes its scrollbar range once it processes the
        # LayoutRequest queued by load_files -- read too early and maximum()
        # reports a stale 0 regardless of whether the row actually overflows.
        qapp.processEvents()
        assert panel._list.horizontalScrollBar().maximum() == 0

    def test_item_tooltip_still_carries_the_untruncated_text(self, panel, tmp_path):
        (tmp_path / "constant").mkdir()
        path = tmp_path / "constant" / "transportProperties"
        path.write_text("", encoding="utf-8")
        panel.resize(_NARROW_WIDTH, 300)
        panel.show()
        panel.load_files([str(path)], case_dir=str(tmp_path))
        item = panel._find_item_by_path(str(path))
        assert item.toolTip() == str(path)

    def test_group_header_also_carries_a_tooltip(self, panel, tmp_path):
        """Every other row kind already had a full-text tooltip; only the
        group header didn't -- and with the horizontal scrollbar off, a
        narrow panel can now elide even a header's own (normally short) text."""
        (tmp_path / "constant").mkdir()
        path = tmp_path / "constant" / "transportProperties"
        path.write_text("", encoding="utf-8")
        panel.load_files([str(path)], case_dir=str(tmp_path))
        header = panel._list.item(0)
        assert header.data(_HEADER_GROUP_ROLE) == "constant"
        assert header.toolTip() == header.text()
