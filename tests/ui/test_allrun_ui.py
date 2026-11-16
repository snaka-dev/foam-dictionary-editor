# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tools > Allrun Steps…: the words, the window, and running a step."""
from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QMessageBox, QWidget

from services import allrun as ar
from ui.allrun_text import note_text, state_label, state_tooltip
from ui.dialogs.allrun_steps_dialog import AllrunStepsDialog

HEAD = '#!/bin/sh\ncd "${0%/*}" || exit\n. ${WM_PROJECT_DIR:?}/bin/tools/RunFunctions\n'


@pytest.fixture
def case(tmp_path: Path) -> Path:
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "controlDict").write_text("application interFoam;\nendTime 1;\n")
    (tmp_path / "Allrun").write_text(HEAD + "restore0Dir\nrunApplication blockMesh\n"
                                     "runApplication setFields\nrunApplication $(getApplication)\n")
    (tmp_path / "log.blockMesh").write_text("End\n")
    (tmp_path / "log.setFields").write_text("--> FOAM FATAL IO ERROR:\nUnknown\n")
    return tmp_path


def test_words_for_every_state_and_note():
    step = ar.Step(ar.RUN, "runApplication x", "Allrun", 1, "x", "log.x")
    for state in (ar.NOT_RUN, ar.DONE, ar.FAILED, ar.INCOMPLETE, ar.RUNNING):
        status = ar.StepStatus(state)
        assert state_label(status)
        assert "log.x" in state_tooltip(step, status)
    assert state_label(ar.StepStatus(ar.RUNNING)) != state_label(ar.StepStatus(ar.INCOMPLETE))
    # Seen to have no writer, an incomplete step was stopped -- not "still running".
    watched = state_tooltip(step, ar.StepStatus(ar.INCOMPLETE, watched=True))
    assert watched != state_tooltip(step, ar.StepStatus(ar.INCOMPLETE))
    assert "skips" not in state_tooltip(step, ar.StepStatus(ar.RUNNING))
    for suspect in (ar.SUSPECT_AFTER_FAILURE, ar.SUSPECT_OUTDATED):
        assert state_label(ar.StepStatus(ar.DONE, suspect)) != state_label(ar.StepStatus(ar.DONE))
        assert "again" in state_tooltip(step, ar.StepStatus(ar.DONE, suspect))
    for note in (ar.NOTE_BRANCHES, ar.NOTE_SUBDIRECTORY, ar.NOTE_UNRESOLVED_APP):
        assert note_text(note) != note


def test_window_lists_steps_with_states(qtbot, case: Path):
    dialog = AllrunStepsDialog()
    qtbot.addWidget(dialog)
    dialog.set_plan(str(case), ar.read_allrun(str(case)))
    assert dialog.row_states() == ["", "Done", "Failed", "Not run"]
    assert "1 of 3" in dialog._summary.text()
    # The first unfinished step is selected: setFields.
    assert dialog._current_index() == 2
    assert "log.setFields holds an error" in dialog._detail.text()
    assert dialog._run_btn.isEnabled() and dialog._run_from_btn.isEnabled()
    dialog.select_row(0)  # restore0Dir: not a step
    assert not dialog._run_btn.isEnabled() and dialog._run_from_btn.isEnabled()
    assert not dialog._log_btn.isEnabled()


def test_window_without_allrun(qtbot, tmp_path: Path):
    dialog = AllrunStepsDialog()
    qtbot.addWidget(dialog)
    dialog.set_plan(str(tmp_path), None)
    assert "no Allrun" in dialog._summary.text()
    assert not dialog._run_btn.isEnabled()


def test_window_signals(qtbot, case: Path):
    dialog = AllrunStepsDialog()
    qtbot.addWidget(dialog)
    dialog.set_plan(str(case), ar.read_allrun(str(case)))
    runs, logs = [], []
    dialog.run_requested.connect(lambda i, onwards: runs.append((i, onwards)))
    dialog.log_requested.connect(logs.append)
    dialog.select_row(2)
    dialog._run_from_btn.click()
    dialog._log_btn.click()
    assert runs == [(2, True)]
    assert logs == [str(case / "log.setFields")]


def test_no_terminal_means_no_running(qtbot, case: Path):
    dialog = AllrunStepsDialog()
    qtbot.addWidget(dialog)
    dialog.set_plan(str(case), ar.read_allrun(str(case)), can_run=False)
    assert not dialog._run_btn.isEnabled() and not dialog._run_from_btn.isEnabled()


class _FakeTerminal(QWidget):
    def __init__(self):
        super().__init__()
        self.commands: list[str] = []

    def running_commands(self) -> list[str]:
        return []

    def run_command(self, cmd: str) -> None:
        self.commands.append(cmd)

    def cleanup(self) -> None:
        pass


def test_main_window_runs_a_step(main_window, case: Path, monkeypatch):
    win = main_window
    win._load_case_dir(str(case))
    win.terminal_panel = _FakeTerminal()
    win._on_allrun_steps_clicked()
    dialog = win._allrun_steps_dialog
    assert dialog is not None and dialog.plan is not None
    asked = []

    def fake_exec(box):
        asked.append(box.text())
        box.done(0)
        run = next(b for b in box.buttons() if b.text() == "Run")
        box._clicked = run
        return 0

    monkeypatch.setattr(QMessageBox, "exec", fake_exec)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda box: box._clicked)
    win._on_allrun_run_requested(2, False)  # setFields, which has a log
    assert win.terminal_panel.commands == [ar.RUN_FUNCTIONS + " && runApplication -o setFields"]
    assert "log.setFields" in asked[0]


def test_solver_step_shows_check_case_errors(main_window, case: Path, monkeypatch):
    win = main_window
    (case / "0.orig").mkdir()  # no 0/: Check Case's no_start_dir error
    win._load_case_dir(str(case))
    win.terminal_panel = _FakeTerminal()
    win._on_allrun_steps_clicked()
    asked = []

    def fake_exec(box):
        asked.append(box.text())
        box._clicked = None
        return 0

    monkeypatch.setattr(QMessageBox, "exec", fake_exec)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda box: box._clicked)
    win._on_allrun_run_requested(3, False)  # interFoam
    assert "Check Case found problems" in asked[0]
    assert win.terminal_panel.commands == []  # cancelled


def test_open_log_goes_to_log_summary(main_window, case: Path):
    win = main_window
    win._load_case_dir(str(case))
    win._on_allrun_log_requested(str(case / "log.setFields"))
    assert win._log_summary_dialog is not None
    assert win._log_summary_dialog._file_edit.text() == str(case / "log.setFields")


def test_action_and_case_switch(main_window, case: Path):
    win = main_window
    win._update_tools_actions()
    assert not win._allrun_steps_action.isEnabled()
    win._load_case_dir(str(case))
    win._update_tools_actions()
    assert win._allrun_steps_action.isEnabled()
    win._on_allrun_steps_clicked()
    win._close_case()
    assert not win._allrun_steps_dialog.isVisible()
