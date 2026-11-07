# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tools > Run postProcess…: the dialog, and the action that runs it."""
from __future__ import annotations

import pytest
from PySide6.QtWidgets import QDialog

from services.post_process import ALL_FUNCTIONS, COMMON_FUNCTIONS
from ui.dialogs.run_post_process_dialog import RunPostProcessDialog


@pytest.fixture
def make(qapp, tmp_path, destroy_widget):
    made = []

    def _make(tool="postProcess", application="simpleFoam", module=None, **kw):
        dlg = RunPostProcessDialog(
            str(tmp_path), tool, ["probes", "singleGraph"], COMMON_FUNCTIONS,
            application, module, **kw,
        )
        made.append(dlg)
        return dlg

    yield _make
    for dlg in made:
        destroy_widget(dlg)


def _command(dlg):
    command, problem = dlg._compose()
    return command if command is not None else problem


def test_every_function_by_default_goes_through_the_solver(make):
    # Plain postProcess with no -func loads no fields: every sampling
    # function would report "Cannot find registered field" and write nothing.
    dlg = make()
    assert dlg.function() == ALL_FUNCTIONS
    assert dlg._solver_chk.isChecked()
    assert _command(dlg) == "simpleFoam -postProcess -latestTime 2>&1 | tee log.postProcess"


def test_every_function_without_a_named_solver_stays_runnable(make):
    dlg = make(application=None)
    assert not dlg._solver_chk.isChecked()
    assert _command(dlg) == "postProcess -latestTime 2>&1 | tee log.postProcess"


def test_the_cases_functions_come_first(make):
    dlg = make()
    items = [dlg._func_combo.itemText(i) for i in range(dlg._func_combo.count())]
    assert items[:3] == ["(every function in controlDict)", "probes", "singleGraph"]
    assert "yPlus" in items and "mag(U)" in items


def test_a_preset_function(make):
    dlg = make(preset="probes")
    assert _command(dlg) == "postProcess -func probes -latestTime 2>&1 | tee log.postProcess"


def test_a_function_that_needs_the_solver_goes_through_it(make):
    dlg = make()
    dlg._func_combo.setCurrentText("yPlus")
    assert dlg._solver_chk.isChecked()
    assert _command(dlg) == (
        "simpleFoam -postProcess -func yPlus -latestTime 2>&1 | tee log.postProcess"
    )
    dlg._func_combo.setCurrentText("mag(U)")
    assert not dlg._solver_chk.isChecked()
    assert _command(dlg) == "postProcess -func 'mag(U)' -latestTime 2>&1 | tee log.postProcess"


def test_foundation_11_runs_the_solver_module(make):
    dlg = make(tool="foamPostProcess", application="foamRun", module="incompressibleFluid")
    dlg._func_combo.setCurrentText("wallShearStress")
    assert _command(dlg) == (
        "foamPostProcess -solver incompressibleFluid -func wallShearStress -latestTime "
        "2>&1 | tee log.foamPostProcess"
    )


def test_a_choice_made_by_hand_sticks(make):
    dlg = make()
    assert dlg._solver_chk.isChecked()  # every function: ticked by itself
    dlg._solver_chk.setChecked(False)  # the user's click
    dlg._func_combo.setCurrentText("yPlus")
    assert not dlg._solver_chk.isChecked()  # no longer follows the function


def test_no_solver_named_means_no_solver_run(make):
    dlg = make(application=None)
    dlg._func_combo.setCurrentText("yPlus")
    assert not dlg._solver_chk.isChecked()  # left clear rather than blocking Run
    dlg._solver_chk.setChecked(True)  # ticked by hand: then it says why not
    assert dlg._compose()[0] is None
    assert "untick" in dlg._compose()[1]


def test_an_invalid_function_disables_run(make):
    dlg = make()
    dlg._func_combo.setCurrentText("a; rm x")
    assert dlg._compose()[0] is None
    assert not dlg._run_btn.isEnabled()


def test_parallel(make):
    dlg = make(parallel_np=4, parallel_default=True, preset="probes")
    assert _command(dlg) == (
        "mpirun -np 4 postProcess -func probes -latestTime -parallel 2>&1 | tee log.postProcess"
    )


# ── the action ───────────────────────────────────────────────────────────────

_CONTROL = (
    "FoamFile { object controlDict; }\napplication simpleFoam;\n"
    "functions\n{\n    #includeFunc probes\n}\n"
)


@pytest.fixture
def case(main_window, tmp_path):
    from tests.ui.test_tools_busy_terminal import _Terminal

    case = tmp_path / "case"
    (case / "system").mkdir(parents=True)
    (case / "system" / "controlDict").write_text(_CONTROL)
    (case / "system" / "probes").write_text("fields (p);\nprobeLocations ((0 0 0));\n")
    (case / "0.5").mkdir()
    main_window._load_case_dir(str(case))
    main_window.terminal_panel = _Terminal()
    return case


def test_running_it(main_window, case, monkeypatch):
    seen = {}

    def fake_exec(dlg):
        seen["functions"] = dlg._functions
        dlg._func_combo.setCurrentText("probes")
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(RunPostProcessDialog, "exec", fake_exec)
    main_window._on_run_post_process_clicked()
    assert seen["functions"] == ["probes"]
    assert main_window.terminal_panel.commands == [
        "postProcess -func probes -latestTime 2>&1 | tee log.postProcess"
    ]


def test_refused_while_running(main_window, case, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    seen = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: seen.append(a[1]))
    main_window.terminal_panel.running = ["simpleFoam"]
    main_window._on_run_post_process_clicked()
    assert seen == ["Command still running"]
    assert main_window.terminal_panel.commands == []


def test_warnings_for_no_results_and_unsaved_edits(main_window, case, monkeypatch):
    import shutil

    from ui.dialogs.run_tool_dialog import RunToolDialog

    shutil.rmtree(case / "0.5")
    main_window.state.file_dirty[str(case / "system" / "probes")] = True
    seen = {}
    real_init = RunToolDialog.__init__

    def spy(self, spec, case_dir, last, warning, *a, **k):
        seen["warning"] = warning
        real_init(self, spec, case_dir, last, warning, *a, **k)

    monkeypatch.setattr(RunToolDialog, "__init__", spy)
    monkeypatch.setattr(RunPostProcessDialog, "exec", lambda dlg: QDialog.DialogCode.Rejected)
    main_window._on_run_post_process_clicked()
    assert "no results yet" in seen["warning"]
    assert "unsaved edits" in seen["warning"]


def test_a_function_files_right_click(main_window, case, monkeypatch):
    probes = str(case / "system" / "probes")
    item = next(
        main_window.file_list_panel._list.item(i)
        for i in range(main_window.file_list_panel._list.count())
        if main_window.file_list_panel._list.item(i).data(256) == probes
    )
    menu, actions = main_window.file_list_panel._build_context_menu(item)
    labels = [a.text() for a in actions]
    assert "Run postProcess with this…" in labels
    seen = []
    monkeypatch.setattr(
        type(main_window), "_on_run_post_process_clicked", lambda self, preset="": seen.append(preset)
    )
    actions_by_label = {a.text(): h for a, h in actions.items()}
    actions_by_label["Run postProcess with this…"]()
    assert seen == ["probes"]
