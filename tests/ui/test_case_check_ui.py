# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tools > Check Case…: the sentences, the dialog and the main-window wiring.

The checks themselves are tests/services/test_case_check.py.
"""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtWidgets import QDialog, QLabel, QWidget

from services import case_check as cc
from ui.case_check_text import finding_location, finding_message, skip_message
from ui.dialogs.case_check_dialog import CaseCheckDialog
from ui.dialogs.run_tool_dialog import RunToolDialog

_ARGS = {
    "field": "U", "patches": "inlet", "entries": "inlett", "patch": "frontAndBack",
    "patch_type": "empty", "field_type": "zeroGradient", "interval": "100", "unit": "steps",
    "run": "50", "delta_t": "1", "start": "0.5", "end": "0.5", "value": "writeNow",
    "n": "2 1 1", "product": "2", "count": "4", "method": "simple", "pieces": "2",
    "name": "transportProperties", "solver": "icoFoam", "have": "physicalProperties",
    "want": "transportProperties",
}


def test_every_finding_code_has_a_sentence():
    for code in cc.FINDING_CODES:
        message = finding_message(cc.Finding(code, cc.ERROR, "0/U", 3, dict(_ARGS)))
        assert message and message != code, code
        assert "{" not in message, (code, message)


def test_constraint_mismatch_wording_follows_the_patch_type():
    on_empty = finding_message(cc.Finding(cc.CONSTRAINT_MISMATCH, cc.ERROR, "0/p", 1, dict(_ARGS)))
    on_wall = finding_message(cc.Finding(
        cc.CONSTRAINT_MISMATCH, cc.ERROR, "0/p", 1, {**_ARGS, "patch_type": "wall", "field_type": "empty"},
    ))
    assert on_empty != on_wall
    assert "blockMeshDict" in on_wall


def test_every_skip_code_has_a_sentence():
    for code in cc.SKIP_CODES:
        message = skip_message(cc.Skip(code, "0/U", {"field": "U"}))
        assert message and message != code, code


def test_location():
    assert finding_location(cc.Finding(cc.MISSING_PATCH_ENTRY, cc.ERROR, "0/U", 21)) == "0/U:21"
    assert finding_location(cc.Finding(cc.NO_START_DIR, cc.ERROR, "0.orig")) == "0.orig"


# ── the dialog ───────────────────────────────────────────────────────────────

def test_dialog_lists_findings_and_opens_one(qtbot, tmp_path: Path):
    dialog = CaseCheckDialog()
    qtbot.addWidget(dialog)
    findings = (
        cc.Finding(cc.MISSING_PATCH_ENTRY, cc.ERROR, os.path.join("0", "U"), 21,
                   {"field": "U", "patches": "inlet"}),
        cc.Finding(cc.NOTHING_WRITTEN, cc.WARNING, os.path.join("system", "controlDict"), 31,
                   {"interval": "1", "unit": "time", "run": "0.5"}),
    )
    dialog.set_result(str(tmp_path), cc.CaseCheck(findings, (cc.Skip(cc.SKIP_NO_MESH),)))
    assert dialog.findings() == list(findings)
    assert "1 error" in dialog._summary.text()
    assert not dialog._skipped.isHidden()
    # The first problem is selected and shown in full under the list.
    assert dialog._detail.text() == finding_message(findings[0])
    dialog._list.setCurrentItem(dialog._list.topLevelItem(1))
    assert dialog._detail.text() == finding_message(findings[1])

    opened = []
    dialog.open_requested.connect(lambda path, line: opened.append((path, line)))
    dialog._list.itemActivated.emit(dialog._list.topLevelItem(0), 0)
    assert opened == [(str(tmp_path / "0" / "U"), 21)]


def test_dialog_with_no_findings(qtbot, tmp_path: Path):
    dialog = CaseCheckDialog()
    qtbot.addWidget(dialog)
    dialog.set_result(str(tmp_path), cc.CaseCheck())
    assert dialog._list.isHidden()
    assert dialog._skipped.isHidden()
    assert "No problems" in dialog._summary.text()


# ── main window ──────────────────────────────────────────────────────────────

def _broken_case(tmp_path: Path) -> Path:
    case = tmp_path / "case"
    (case / "system").mkdir(parents=True)
    (case / "system" / "controlDict").write_text(
        "application icoFoam;\nstartFrom startTime;\nstartTime 0;\nendTime 1;\n"
        "deltaT 0.1;\nwriteControl timeStep;\nwriteInterval 5;\n"
    )
    (case / "constant" / "polyMesh").mkdir(parents=True)
    (case / "constant" / "polyMesh" / "boundary").write_text(
        "1\n(\n    inlet { type patch; nFaces 1; startFace 0; }\n)\n"
    )
    (case / "constant" / "transportProperties").write_text("nu 0.01;\n")
    (case / "0").mkdir()
    (case / "0" / "U").write_text(
        "FoamFile\n{\n    class volVectorField;\n    object U;\n}\n"
        "internalField uniform (0 0 0);\nboundaryField\n{\n    inlett { type zeroGradient; }\n}\n"
    )
    return case


def test_check_case_action_follows_the_case(main_window, tmp_path: Path):
    win = main_window
    win._update_tools_actions()
    assert not win._check_case_action.isEnabled()
    win.state.current_case_dir = str(tmp_path)
    win._update_tools_actions()
    assert win._check_case_action.isEnabled()


def test_check_case_shows_the_findings(main_window, tmp_path: Path):
    win = main_window
    case = _broken_case(tmp_path)
    win._load_case_dir(str(case))
    win._on_check_case_clicked()
    dialog = win._case_check_dialog
    assert dialog is not None and dialog.isVisible()
    assert [f.code for f in dialog.findings()] == [cc.MISSING_PATCH_ENTRY, cc.UNMATCHED_PATCH_ENTRY]

    # Fixing the file and checking again clears it.
    (case / "0" / "U").write_text((case / "0" / "U").read_text().replace("inlett", "inlet"))
    dialog.recheck_requested.emit()
    assert dialog.findings() == []

    win._close_case()
    assert not dialog.isVisible()


def test_unsaved_edit_counts(main_window, tmp_path: Path):
    win = main_window
    case = _broken_case(tmp_path)
    (case / "0" / "U").write_text((case / "0" / "U").read_text().replace("inlett", "inlet"))
    win._load_case_dir(str(case))
    path = str(case / "0" / "U")
    win.load_selected_file(path)
    win.editor_panel.set_text(win.editor_panel.get_text().replace("inlet {", "outlet {"))
    codes = [f.code for f in win._run_case_check(str(case)).findings]
    assert cc.MISSING_PATCH_ENTRY in codes


def test_opening_a_finding_loads_its_file(main_window, tmp_path: Path):
    win = main_window
    case = _broken_case(tmp_path)
    win._load_case_dir(str(case))
    path = str(case / "0" / "U")
    win._open_file_at_line(path, 9)
    assert win.state.current_file == path
    assert win.editor_panel.current_line_number() == 9
    # A directory finding opens nothing.
    win._open_file_at_line(str(case / "constant"), 0)
    assert win.state.current_file == path


class _FakeTerminalPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.commands: list[str] = []

    def running_commands(self) -> list[str]:
        return []

    def run_command(self, cmd: str) -> None:
        self.commands.append(cmd)

    def cleanup(self) -> None:
        pass


def test_run_solver_lists_the_findings(main_window, tmp_path: Path, monkeypatch):
    win = main_window
    case = _broken_case(tmp_path)
    win.state.current_case_dir = str(case)
    win.terminal_panel = _FakeTerminalPanel()
    seen = {}

    def fake_exec(self):
        seen["dlg"] = self
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(RunToolDialog, "exec", fake_exec)
    win._on_run_solver_clicked()
    labels = "\n".join(label.text() for label in seen["dlg"].findChildren(QLabel))
    assert "Cannot find patchField entry" in labels
    assert os.path.join("0", "U") + ":" in labels


def test_run_solver_caps_the_list(main_window, tmp_path: Path):
    win = main_window
    case = _broken_case(tmp_path)
    for name in ("p", "k", "omega", "nut", "T"):
        (case / "0" / name).write_text(
            (case / "0" / "U").read_text().replace("volVectorField", "volScalarField")
        )
    lines = win._case_check_solver_warnings(str(case))
    assert len(lines) == 5
    assert "Check Case" in lines[-1]
    assert lines[0].startswith(os.path.join("0", "T") + ":")
