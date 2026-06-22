# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""
Tests for ui/manage_extra_files_dialog.py.
"""
from __future__ import annotations

import sys

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from ui.dialogs.manage_extra_files_dialog import ManageExtraFilesDialog


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])
    yield app


@pytest.fixture
def dialog(qapp):
    files = ["system/myDict", "constant/myProps"]
    dlg = ManageExtraFilesDialog(files)
    yield dlg
    dlg.deleteLater()


class TestManageExtraFilesDialogDisplay:
    def test_dialog_shows_all_files(self, dialog):
        items = [dialog._files_list.item(i).text() for i in range(dialog._files_list.count())]
        assert "system/myDict" in items
        assert "constant/myProps" in items

    def test_initial_removed_files_is_empty(self, dialog):
        assert dialog.removed_files == []

    def test_initial_check_state_is_unchecked(self, dialog):
        for i in range(dialog._files_list.count()):
            assert dialog._files_list.item(i).checkState() == Qt.Unchecked

    def test_empty_extra_files(self, qapp):
        dlg = ManageExtraFilesDialog([])
        assert dlg._files_list.count() == 0
        assert dlg.removed_files == []
        dlg.deleteLater()


class TestManageExtraFilesDialogRemoval:
    def test_remove_checked_updates_removed_files(self, qapp):
        dlg = ManageExtraFilesDialog(["system/myDict", "constant/myProps"])
        dlg._files_list.item(0).setCheckState(Qt.Checked)
        dlg._remove_checked_files()
        assert "system/myDict" in dlg.removed_files
        dlg.deleteLater()

    def test_remove_checked_removes_item_from_list(self, qapp):
        dlg = ManageExtraFilesDialog(["system/myDict", "constant/myProps"])
        dlg._files_list.item(0).setCheckState(Qt.Checked)
        dlg._remove_checked_files()
        items = [dlg._files_list.item(i).text() for i in range(dlg._files_list.count())]
        assert "system/myDict" not in items
        dlg.deleteLater()

    def test_remove_all_items(self, qapp):
        dlg = ManageExtraFilesDialog(["system/myDict"])
        dlg._files_list.item(0).setCheckState(Qt.Checked)
        dlg._remove_checked_files()
        assert dlg._files_list.count() == 0
        assert dlg.removed_files == ["system/myDict"]
        dlg.deleteLater()

    def test_remove_multiple_at_once(self, qapp):
        dlg = ManageExtraFilesDialog(["system/a", "system/b", "system/c"])
        dlg._files_list.item(0).setCheckState(Qt.Checked)
        dlg._files_list.item(1).setCheckState(Qt.Checked)
        dlg._remove_checked_files()
        assert len(dlg.removed_files) == 2
        assert dlg._files_list.count() == 1
        dlg.deleteLater()

    def test_remove_sequentially(self, qapp):
        dlg = ManageExtraFilesDialog(["system/a", "system/b", "system/c"])
        dlg._files_list.item(0).setCheckState(Qt.Checked)
        dlg._remove_checked_files()
        dlg._files_list.item(0).setCheckState(Qt.Checked)
        dlg._remove_checked_files()
        assert len(dlg.removed_files) == 2
        assert dlg._files_list.count() == 1
        dlg.deleteLater()

    def test_no_removal_leaves_removed_files_empty(self, qapp):
        dlg = ManageExtraFilesDialog(["system/myDict"])
        assert dlg.removed_files == []
        dlg.deleteLater()

    def test_select_all_checks_all_items(self, qapp):
        dlg = ManageExtraFilesDialog(["system/a", "system/b"])
        dlg._select_all_files()
        for i in range(dlg._files_list.count()):
            assert dlg._files_list.item(i).checkState() == Qt.Checked
        dlg.deleteLater()

    def test_deselect_all_unchecks_all_items(self, qapp):
        dlg = ManageExtraFilesDialog(["system/a", "system/b"])
        dlg._select_all_files()
        dlg._deselect_all_files()
        for i in range(dlg._files_list.count()):
            assert dlg._files_list.item(i).checkState() == Qt.Unchecked
        dlg.deleteLater()
