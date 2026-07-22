# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for RunToolDialog (Tools-menu "Run *" options dialog)."""
from __future__ import annotations

import sys

import pytest
from PySide6.QtWidgets import QApplication, QFileDialog

from services.tool_options import TOOL_SPECS
from ui.dialogs.run_tool_dialog import RunToolDialog


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])
    return app


def test_preview_shows_default_command(qapp, tmp_path):
    dlg = RunToolDialog(TOOL_SPECS["checkMesh"], str(tmp_path))
    assert dlg._preview.text() == "checkMesh 2>&1 | tee log.checkMesh"
    assert dlg.get_command() == "checkMesh 2>&1 | tee log.checkMesh"


def test_checkbox_updates_preview_and_command(qapp, tmp_path):
    dlg = RunToolDialog(TOOL_SPECS["checkMesh"], str(tmp_path))
    dlg._checks["-allGeometry"].setChecked(True)
    assert dlg.get_command() == "checkMesh -allGeometry 2>&1 | tee log.checkMesh"
    assert dlg._preview.text() == dlg.get_command()


def test_value_edit_updates_command(qapp, tmp_path):
    dlg = RunToolDialog(TOOL_SPECS["blockMesh"], str(tmp_path))
    dlg._edits["-region"].setText("fluid")
    assert dlg.get_command() == "blockMesh -region fluid 2>&1 | tee log.blockMesh"


def test_last_values_are_restored(qapp, tmp_path):
    last = {"-overwrite": False, "-dict": "system/other", "extra": "-profiling"}
    dlg = RunToolDialog(TOOL_SPECS["snappyHexMesh"], str(tmp_path), last)
    assert dlg._checks["-overwrite"].isChecked() is False
    assert dlg._edits["-dict"].text() == "system/other"
    assert dlg._extra_edit.text() == "-profiling"
    assert dlg.get_command() == (
        "snappyHexMesh -dict system/other -profiling "
        "2>&1 | tee log.snappyHexMesh"
    )


def test_get_values_round_trips_into_new_dialog(qapp, tmp_path):
    dlg = RunToolDialog(TOOL_SPECS["snappyHexMesh"], str(tmp_path))
    dlg._checks["-overwrite"].setChecked(False)
    dlg._extra_edit.setText("-checkGeometry")
    values = dlg.get_values()

    dlg2 = RunToolDialog(TOOL_SPECS["snappyHexMesh"], str(tmp_path), values)
    assert dlg2.get_command() == dlg.get_command()


def test_invalid_extra_disables_run(qapp, tmp_path):
    dlg = RunToolDialog(TOOL_SPECS["topoSet"], str(tmp_path))
    dlg._extra_edit.setText("-y '[0:1]")
    assert dlg._run_btn.isEnabled() is False
    dlg._extra_edit.setText("-y '[0:1]'")
    assert dlg._run_btn.isEnabled() is True


def test_prefix_checkbox_prepends_command(qapp, tmp_path):
    dlg = RunToolDialog(
        TOOL_SPECS["setFields"],
        str(tmp_path),
        prefix_option=("Restore 0/ first", "rm -rf 0 && cp -r 0.orig 0 && ", True),
    )
    assert dlg.get_command() == (
        "rm -rf 0 && cp -r 0.orig 0 && setFields 2>&1 | tee log.setFields"
    )
    dlg._prefix_chk.setChecked(False)
    assert dlg.get_command() == "setFields 2>&1 | tee log.setFields"


def test_browse_inserts_case_relative_path(qapp, tmp_path, monkeypatch):
    inside = tmp_path / "system" / "blockMeshDict.fine"
    inside.parent.mkdir(parents=True, exist_ok=True)
    inside.write_text("")
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        staticmethod(lambda *a, **k: (str(inside), "")),
    )
    dlg = RunToolDialog(TOOL_SPECS["blockMesh"], str(tmp_path))
    dlg._browse(dlg._edits["-dict"])
    assert dlg._edits["-dict"].text() == "system/blockMeshDict.fine"


def test_browse_keeps_absolute_path_outside_case(qapp, tmp_path, monkeypatch):
    outside = tmp_path / "elsewhere" / "dict"
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.write_text("")
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        staticmethod(lambda *a, **k: (str(outside), "")),
    )
    dlg = RunToolDialog(TOOL_SPECS["blockMesh"], str(case_dir))
    dlg._browse(dlg._edits["-dict"])
    assert dlg._edits["-dict"].text() == str(outside)
