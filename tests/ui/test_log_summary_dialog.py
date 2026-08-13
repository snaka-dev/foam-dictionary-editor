# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""
Tests for ui/dialogs/log_summary_dialog.py.
"""
from __future__ import annotations

import pytest
from PySide6.QtCore import Qt

from ui.dialogs.log_summary_dialog import LogSummaryDialog

_BLOCK_MESH_LOG = """\
Exec   : blockMesh

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
----------------
Mesh Information
----------------
  nPoints: 10
  nCells: 5
----------------
Patches
----------------
  patch 0 (start: 0 size: 1) name: top

End
"""


@pytest.fixture
def case_dir(tmp_path):
    log_path = tmp_path / "log.blockMesh"
    log_path.write_text(_BLOCK_MESH_LOG)
    return tmp_path


def test_dialog_is_non_modal(qapp, case_dir):
    dlg = LogSummaryDialog(str(case_dir))
    assert dlg.windowModality() == Qt.WindowModality.NonModal
    dlg.deleteLater()


def test_dialog_defaults_to_most_recent_log_and_shows_summary(qapp, case_dir):
    dlg = LogSummaryDialog(str(case_dir))
    assert dlg._file_edit.text() == str(case_dir / "log.blockMesh")
    assert "nCells: 5" in dlg._summary_text.toPlainText()
    assert "Result: OK" in dlg._summary_text.toPlainText()
    assert "Mesh Information" in dlg._raw_text.toPlainText()
    dlg.deleteLater()


def test_changing_file_field_reparses_summary(qapp, case_dir, tmp_path):
    other_log = tmp_path / "log.other"
    other_log.write_text("Exec   : checkMesh\n\n// * * * //\nsome output line\n")
    dlg = LogSummaryDialog(str(case_dir))
    dlg._file_edit.setText(str(other_log))
    dlg._reload()
    assert "some output line" in dlg._raw_text.toPlainText()
    dlg.deleteLater()


def test_no_log_files_leaves_file_field_empty(qapp, tmp_path):
    empty_dir = tmp_path / "empty_case"
    empty_dir.mkdir()
    dlg = LogSummaryDialog(str(empty_dir))
    assert dlg._file_edit.text() == ""
    assert "Select a log file" in dlg._summary_text.toPlainText()
    dlg.deleteLater()
