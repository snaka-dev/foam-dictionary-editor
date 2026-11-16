# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tools > Create Allrun from Logs…: the words, the dialog, and writing the files."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMessageBox

from services import allrun as ar
from services import allrun_create as ac
from ui.allrun_create_text import mark_detail, mark_label, note_text, row_detail, skip_text
from ui.dialogs.allrun_steps_dialog import AllrunStepsDialog
from ui.dialogs.create_allrun_dialog import CreateAllrunDialog

HEADER = "Exec   : {exe}\nDate   : Nov 06 2026\nTime   : {time}\nnProcs : 1\n\nEnd\n"


@pytest.fixture
def case(tmp_path: Path) -> Path:
    (tmp_path / "system").mkdir()
    (tmp_path / "constant").mkdir()
    (tmp_path / "system" / "controlDict").write_text("application interFoam;\nendTime 1;\n")
    (tmp_path / "0.orig").mkdir()
    (tmp_path / "log.blockMesh").write_text(HEADER.format(exe="blockMesh", time="10:00:00"))
    (tmp_path / "log.checkMesh").write_text(HEADER.format(exe="checkMesh", time="10:00:01"))
    (tmp_path / "log.setFields").write_text(HEADER.format(exe="setFields", time="10:00:02"))
    (tmp_path / "log.interFoam").write_text(HEADER.format(exe="interFoam", time="10:00:03"))
    return tmp_path


def test_words_for_every_code():
    marks = (ac.MARK_FAILED, ac.MARK_INCOMPLETE, ac.MARK_READ_ONLY, ac.MARK_NO_LOG,
             ac.MARK_GUESSED, ac.MARK_MOVED, ac.MARK_RESTORE, ac.MARK_PARALLEL_ONLY, ac.MARK_USER)
    assert len({mark_label(m) for m in marks}) == len(marks)
    for mark in marks:
        if mark != ac.MARK_NO_LOG:   # the row's origin sentence says it
            assert mark_detail(mark) != mark
    for skip in (ac.SKIP_NO_HEADER, ac.SKIP_EARLIER_RUN):
        assert "log.x" in skip_text("log.x", skip) and skip_text("log.x", skip) != "log.x"
    for note in (ac.NOTE_FROM_DICTIONARIES, ac.NOTE_LIMITS, ac.NOTE_RESTORES_ZERO,
                 ac.NOTE_NO_ZERO_ORIG, ac.NOTE_ORIG_FILES):
        assert note_text(note) != note
    suggested = ac.Proposed(kind=ar.RUN, app="blockMesh", source=ac.SOURCE_DICT,
                            origin="system/blockMeshDict", marks=(ac.MARK_NO_LOG,))
    assert "system/blockMeshDict" in row_detail(suggested)


def test_dialog_preview_follows_ticks_and_order(qtbot, case: Path):
    proposal = ac.propose(str(case), ac.FORK_OPENCFD)
    dialog = CreateAllrunDialog(proposal)
    qtbot.addWidget(dialog)
    # checkMesh changes nothing: unticked, so not in the script.
    assert "checkMesh" not in dialog.allrun_text()
    assert "restore0Dir\n" in dialog.allrun_text()
    assert "cleanCase0" in dialog.allclean_text()
    # Untick blockMesh: the Allclean now keeps the mesh, and says why.
    item = dialog._list.item(0)
    assert "blockMesh" in item.text()
    item.setCheckState(Qt.CheckState.Unchecked)
    assert "runApplication blockMesh" not in dialog._allrun_view.toPlainText()
    assert "foamListTimes -rm" in dialog._allclean_view.toPlainText()
    assert dialog._mesh_note.isVisibleTo(dialog)
    # Move setFields above restore0Dir.
    rows = [dialog._list.item(i).text() for i in range(dialog._list.count())]
    set_fields = next(i for i, t in enumerate(rows) if "setFields" in t)
    dialog._list.setCurrentRow(set_fields)
    dialog._move(-1)
    text = dialog.allrun_text()
    assert text.index("setFields") < text.index("restore0Dir")
    assert "From log.setFields." in dialog._detail.text()


def test_dialog_respects_an_existing_allclean(qtbot, case: Path):
    dialog = CreateAllrunDialog(ac.propose(str(case)), allclean_exists=True)
    qtbot.addWidget(dialog)
    assert not dialog._write_allclean.isEnabled()
    assert dialog.allclean_text() is None


def test_create_button_off_with_nothing_ticked(qtbot, case: Path):
    dialog = CreateAllrunDialog(ac.propose(str(case)))
    qtbot.addWidget(dialog)
    for i in range(dialog._list.count()):
        dialog._list.item(i).setCheckState(Qt.CheckState.Unchecked)
    assert not dialog._create_btn.isEnabled()


def test_steps_window_offers_creation_without_an_allrun(qtbot, tmp_path: Path):
    dialog = AllrunStepsDialog()
    qtbot.addWidget(dialog)
    dialog.set_plan(str(tmp_path), None)
    assert dialog._create_btn.isVisibleTo(dialog)
    assert not dialog._list.isVisibleTo(dialog)
    with qtbot.waitSignal(dialog.create_requested):
        dialog._create_btn.click()


def test_main_window_writes_and_opens_the_scripts(main_window, case: Path, monkeypatch):
    win = main_window
    win._load_case_dir(str(case))
    monkeypatch.setattr(CreateAllrunDialog, "exec", lambda self: CreateAllrunDialog.DialogCode.Accepted)
    win._on_create_allrun_clicked()
    allrun = case / "Allrun"
    assert allrun.is_file() and os.access(allrun, os.X_OK)
    assert (case / "Allclean").is_file()
    assert "runApplication setFields" in allrun.read_text()
    assert win.state.current_file == str(allrun)
    plan = ar.read_allrun(str(case))
    assert plan is not None and [s.app for s in plan.runs] == ["blockMesh", "setFields", "interFoam"]


def test_main_window_never_replaces_an_allrun(main_window, case: Path, monkeypatch):
    (case / "Allrun").write_text("#!/bin/sh\necho mine\n")
    win = main_window
    win._load_case_dir(str(case))
    told = []
    monkeypatch.setattr(QMessageBox, "information", lambda *a: told.append(a[2]))
    monkeypatch.setattr(CreateAllrunDialog, "exec", lambda self: pytest.fail("no dialog"))
    win._on_create_allrun_clicked()
    assert told and "already has an Allrun" in told[0]
    assert (case / "Allrun").read_text() == "#!/bin/sh\necho mine\n"


def test_action_enabled_with_a_case(main_window, case: Path):
    win = main_window
    win._update_tools_actions()
    assert not win._create_allrun_action.isEnabled()
    win._load_case_dir(str(case))
    win._update_tools_actions()
    assert win._create_allrun_action.isEnabled()


def test_nothing_to_propose_says_so(main_window, tmp_path: Path, monkeypatch):
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "controlDict").write_text("endTime 1;\n")
    (tmp_path / "0.orig").mkdir()   # a restore row alone is no Allrun
    win = main_window
    win._load_case_dir(str(tmp_path))
    told = []
    monkeypatch.setattr(QMessageBox, "information", lambda *a: told.append(a[2]))
    monkeypatch.setattr(CreateAllrunDialog, "exec", lambda self: pytest.fail("no dialog"))
    win._on_create_allrun_clicked()
    assert told and "Found no steps" in told[0]
    assert not (tmp_path / "Allrun").exists()


def test_no_logs_is_said_once(qtbot, tmp_path: Path):
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "controlDict").write_text("application interFoam;\n")
    (tmp_path / "system" / "blockMeshDict").write_text("\n")
    proposal = ac.propose(str(tmp_path))
    dialog = CreateAllrunDialog(proposal)
    qtbot.addWidget(dialog)
    said = note_text(ac.NOTE_FROM_DICTIONARIES)
    labels = [w.text() for w in dialog.findChildren(QLabel)]
    assert labels.count(said) == 1          # the intro, not also a note
    assert said not in dialog._notes.text()
    suggested = mark_label(ac.MARK_NO_LOG)
    rows = [dialog._list.item(i).text() for i in range(dialog._list.count())]
    assert rows and not any(suggested in r for r in rows)
    # The row detail still says why it is there.
    assert "system/blockMeshDict" in dialog._detail.text()


# ── Allrun-parallel, typed commands, choosing the script ─────────────────────

@pytest.fixture
def cavity(tmp_path: Path) -> Path:
    """The tutorial cavity: a decomposeParDict it never uses, no logs."""
    (tmp_path / "system").mkdir()
    (tmp_path / "constant").mkdir()
    (tmp_path / "system" / "controlDict").write_text("application icoFoam;\n")
    (tmp_path / "system" / "blockMeshDict").write_text("\n")
    (tmp_path / "system" / "decomposeParDict").write_text("numberOfSubdomains 9;\n")
    return tmp_path


def _apps(dialog: CreateAllrunDialog) -> list[str]:
    return [s.app or s.text for s in dialog.steps()]


def test_parallel_box_adds_rows_and_scripts(qtbot, cavity: Path):
    dialog = CreateAllrunDialog(ac.propose(str(cavity), ac.FORK_OPENCFD))
    qtbot.addWidget(dialog)
    box = dialog._parallel_box
    assert box.isEnabled() and not box.isChecked()   # serial unless it ran in parallel
    assert "9 processors" in box.text()
    assert [name for name, _ in dialog.scripts()] == ["Allrun", "Allclean"]
    box.setChecked(True)
    assert _apps(dialog) == ["blockMesh", "decomposePar", "icoFoam", "reconstructPar"]
    assert [name for name, _ in dialog.scripts()] == [
        "Allrun.pre", "Allrun", "Allrun-parallel", "Allclean",
    ]
    assert dialog._previews.isTabVisible(0) and dialog._previews.isTabVisible(2)
    assert "./Allrun.pre" in dialog.allrun_text()
    assert "decomposePar" not in dialog.allrun_text()
    box.setChecked(False)
    assert _apps(dialog) == ["blockMesh", "icoFoam"]
    assert not dialog._previews.isTabVisible(0) and not dialog._previews.isTabVisible(2)


def test_parallel_box_ticked_when_the_case_ran_in_parallel(qtbot, cavity: Path):
    (cavity / "processor0").mkdir()
    dialog = CreateAllrunDialog(ac.propose(str(cavity), ac.FORK_OPENCFD))
    qtbot.addWidget(dialog)
    assert dialog._parallel_box.isChecked()
    assert [name for name, _ in dialog.scripts()][:3] == ["Allrun.pre", "Allrun", "Allrun-parallel"]


def test_parallel_box_off_when_a_script_exists(qtbot, cavity: Path):
    dialog = CreateAllrunDialog(
        ac.propose(str(cavity)), existing=frozenset({"Allrun-parallel"})
    )
    qtbot.addWidget(dialog)
    assert not dialog._parallel_box.isEnabled()
    assert "Allrun-parallel" in dialog._parallel_box.toolTip()


def test_unticked_solver_blocks_the_split(qtbot, cavity: Path):
    dialog = CreateAllrunDialog(ac.propose(str(cavity)))
    qtbot.addWidget(dialog)
    dialog._parallel_box.setChecked(True)
    row = _apps(dialog).index("icoFoam")
    dialog._list.item(row).setCheckState(Qt.CheckState.Unchecked)
    assert not dialog._create_btn.isEnabled()
    assert dialog._split_note.isVisibleTo(dialog) and "icoFoam" in dialog._split_note.text()


def test_add_and_remove_a_typed_command(qtbot, cavity: Path, monkeypatch):
    from PySide6.QtWidgets import QInputDialog
    dialog = CreateAllrunDialog(ac.propose(str(cavity)))
    qtbot.addWidget(dialog)
    dialog._list.setCurrentRow(0)   # blockMesh
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("checkMesh", True))
    dialog._add_btn.click()
    assert _apps(dialog) == ["blockMesh", "checkMesh", "icoFoam"]
    assert "runApplication checkMesh" in dialog.allrun_text()
    assert dialog._remove_btn.isEnabled()
    dialog._remove_btn.click()
    assert _apps(dialog) == ["blockMesh", "icoFoam"]
    dialog._list.setCurrentRow(0)
    assert not dialog._remove_btn.isEnabled()   # only what you added


def test_main_window_writes_the_split_scripts(main_window, cavity: Path, monkeypatch):
    win = main_window
    win._load_case_dir(str(cavity))

    def accept(self):
        self._parallel_box.setChecked(True)
        return CreateAllrunDialog.DialogCode.Accepted

    monkeypatch.setattr(CreateAllrunDialog, "exec", accept)
    win._on_create_allrun_clicked()
    for name in ("Allrun.pre", "Allrun", "Allrun-parallel", "Allclean"):
        assert os.access(cavity / name, os.X_OK), name
    assert "runParallel icoFoam" in (cavity / "Allrun-parallel").read_text()
    plan = ar.read_allrun(str(cavity))
    assert plan is not None and plan.script == "Allrun"
    assert [s.app for s in plan.runs] == ["blockMesh", "icoFoam"]   # followed into Allrun.pre
    parallel = ar.read_allrun(str(cavity), script="Allrun-parallel")
    assert parallel is not None
    assert [s.app for s in parallel.runs] == ["blockMesh", "decomposePar", "icoFoam", "reconstructPar"]


def test_steps_window_picks_the_script(main_window, cavity: Path, monkeypatch):
    win = main_window
    (cavity / "Allrun").write_text("#!/bin/sh\nrunApplication blockMesh\nrunApplication icoFoam\n")
    (cavity / "Allrun-parallel").write_text(
        "#!/bin/sh\nrunApplication decomposePar\nrunParallel icoFoam\n"
    )
    win._load_case_dir(str(cavity))
    win._on_allrun_steps_clicked()
    dialog = win._allrun_steps_dialog
    assert dialog is not None and dialog.plan is not None
    assert dialog.plan.script == "Allrun"
    assert dialog._script_row.isVisibleTo(dialog)
    dialog._script_combo.setCurrentText("Allrun-parallel")
    assert dialog.plan.script == "Allrun-parallel"
    win._refresh_allrun_steps()   # the 2 s refresh keeps the choice
    assert dialog.plan.script == "Allrun-parallel"
    (cavity / "Allrun-parallel").unlink()
    win._refresh_allrun_steps()
    assert dialog.plan.script == "Allrun" and not dialog._script_row.isVisibleTo(dialog)
    dialog.close()


def test_run_allrun_asks_only_with_both_scripts(main_window, cavity: Path, monkeypatch):
    win = main_window
    told = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a: told.append(a[2]))
    assert win._choose_allrun_script(str(cavity)) is None and told
    (cavity / "Allrun-parallel").write_text("#!/bin/sh\n")
    assert win._choose_allrun_script(str(cavity)) == "Allrun-parallel"
    (cavity / "Allrun").write_text("#!/bin/sh\n")
    asked = []

    def pick_parallel(box):
        asked.append(box.text())
        for button in box.buttons():
            if button.text() == "Allrun-parallel":
                button.click()

    monkeypatch.setattr(QMessageBox, "exec", pick_parallel)
    assert win._choose_allrun_script(str(cavity)) == "Allrun-parallel"
    assert asked and "Allrun-parallel" in asked[0]
