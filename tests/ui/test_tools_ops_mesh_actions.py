# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""
Tests for the Tools-menu "Run *" actions and _update_tools_actions' enablement
logic (ui/mixins/_tools_ops.py).

The tool actions (blockMesh, snappyHexMesh, topoSet, setFields, checkMesh) go
through RunToolDialog; these tests accept/reject the real dialog and pin down
the exact command string sent to the terminal -- a typo in the command or log
filename would otherwise ship silently.
"""
from __future__ import annotations

import pytest
from PySide6.QtWidgets import QDialog, QMessageBox, QWidget

from ui.dialogs.run_tool_dialog import RunToolDialog


class _FakeTerminalPanel(QWidget):
    """A real QWidget (bottom_tabs.indexOf() requires one) standing in for the
    terminal panel, recording run_command() calls instead of spawning a shell."""

    def __init__(self):
        super().__init__()
        self.commands: list[str] = []

    def running_commands(self) -> list[str]:

        return []  # idle; the busy case is tested in test_tools_busy_terminal.py


    def run_command(self, cmd: str) -> None:
        self.commands.append(cmd)

    def cleanup(self) -> None:
        """No-op: the main_window fixture's teardown calls this unconditionally."""


def _patch_run_dialog(monkeypatch, accept=True, tweak=None):
    """Make RunToolDialog.exec() return immediately instead of blocking.

    ``tweak(dialog)`` can adjust the (fully built) dialog's widgets first,
    standing in for the user editing options before pressing Run."""

    def fake_exec(self):
        if tweak is not None:
            tweak(self)
        return QDialog.Accepted if accept else QDialog.Rejected

    monkeypatch.setattr(RunToolDialog, "exec", fake_exec)


def test_run_blockmesh_sends_expected_command(main_window, tmp_path, monkeypatch):
    win = main_window
    win.state.current_case_dir = str(tmp_path)
    win.terminal_panel = _FakeTerminalPanel()

    _patch_run_dialog(monkeypatch)
    win._on_run_blockmesh_clicked()

    assert win.terminal_panel.commands == ["blockMesh 2>&1 | tee log.blockMesh"]


def test_run_snappyhexmesh_sends_expected_command(main_window, tmp_path, monkeypatch):
    win = main_window
    win.state.current_case_dir = str(tmp_path)
    win.terminal_panel = _FakeTerminalPanel()

    _patch_run_dialog(monkeypatch)
    win._on_run_snappyhexmesh_clicked()

    # -overwrite is a curated option that defaults to checked.
    assert win.terminal_panel.commands == [
        "snappyHexMesh -overwrite 2>&1 | tee log.snappyHexMesh"
    ]


def test_run_topo_set_sends_expected_command(main_window, tmp_path, monkeypatch):
    win = main_window
    win.state.current_case_dir = str(tmp_path)
    win.terminal_panel = _FakeTerminalPanel()

    _patch_run_dialog(monkeypatch)
    win._on_run_topo_set_clicked()

    assert win.terminal_panel.commands == ["topoSet 2>&1 | tee log.topoSet"]


def test_run_tool_cancelled_dialog_sends_nothing(main_window, tmp_path, monkeypatch):
    win = main_window
    win.state.current_case_dir = str(tmp_path)
    win.terminal_panel = _FakeTerminalPanel()

    _patch_run_dialog(monkeypatch, accept=False)
    win._on_run_snappyhexmesh_clicked()
    win._on_run_topo_set_clicked()
    win._on_run_blockmesh_clicked()
    assert win.terminal_panel.commands == []


def test_run_dialog_gets_rerun_warning_when_time_dirs_exist(
    main_window, tmp_path, monkeypatch
):
    (tmp_path / "0.5").mkdir()
    win = main_window
    win.state.current_case_dir = str(tmp_path)
    win.terminal_panel = _FakeTerminalPanel()

    captured = {}

    class _FakeDialog:
        def __init__(self, spec, case_dir, last_values=None, warning_text="",
                     prefix_option=None, parent=None):
            captured["warning"] = warning_text

        def exec(self):
            return QDialog.Rejected

    monkeypatch.setattr("ui.mixins._tools_ops.RunToolDialog", _FakeDialog)
    win._on_run_blockmesh_clicked()
    assert "0.5" in captured["warning"]

    (tmp_path / "0.5").rmdir()
    win._on_run_blockmesh_clicked()
    assert captured["warning"] == ""


def test_run_tool_remembers_last_options(main_window, tmp_path, monkeypatch):
    win = main_window
    win.state.current_case_dir = str(tmp_path)
    win.terminal_panel = _FakeTerminalPanel()

    _patch_run_dialog(
        monkeypatch, tweak=lambda dlg: dlg._extra_edit.setText("-latestTime")
    )
    win._on_run_checkmesh_clicked()
    assert win.terminal_panel.commands == [
        "checkMesh -latestTime 2>&1 | tee log.checkMesh"
    ]

    # A fresh dialog restores the previous options from AppState.
    _patch_run_dialog(monkeypatch)
    win._on_run_checkmesh_clicked()
    assert win.terminal_panel.commands[-1] == (
        "checkMesh -latestTime 2>&1 | tee log.checkMesh"
    )


def test_run_checkmesh_sends_expected_command(main_window, tmp_path, monkeypatch):
    win = main_window
    win.state.current_case_dir = str(tmp_path)
    win.terminal_panel = _FakeTerminalPanel()

    _patch_run_dialog(monkeypatch)
    win._on_run_checkmesh_clicked()

    assert win.terminal_panel.commands == ["checkMesh 2>&1 | tee log.checkMesh"]


def test_run_setfields_without_0orig_has_no_restore_checkbox(
    main_window, tmp_path, monkeypatch
):
    win = main_window
    win.state.current_case_dir = str(tmp_path)
    win.terminal_panel = _FakeTerminalPanel()

    seen = {}
    _patch_run_dialog(
        monkeypatch, tweak=lambda dlg: seen.update(chk=dlg._prefix_chk)
    )
    win._on_run_setfields_clicked()
    assert seen["chk"] is None
    assert win.terminal_panel.commands == ["setFields 2>&1 | tee log.setFields"]


def test_run_setfields_restore_first_with_0orig(main_window, tmp_path, monkeypatch):
    (tmp_path / "0.orig").mkdir()
    win = main_window
    win.state.current_case_dir = str(tmp_path)
    win.terminal_panel = _FakeTerminalPanel()

    # The restore checkbox exists and defaults to checked when 0.orig/ exists.
    _patch_run_dialog(monkeypatch)
    win._on_run_setfields_clicked()
    assert win.terminal_panel.commands == [
        "rm -rf 0 && cp -r 0.orig 0 && setFields 2>&1 | tee log.setFields"
    ]


def test_run_setfields_run_anyway_with_0orig(main_window, tmp_path, monkeypatch):
    (tmp_path / "0.orig").mkdir()
    win = main_window
    win.state.current_case_dir = str(tmp_path)
    win.terminal_panel = _FakeTerminalPanel()

    _patch_run_dialog(monkeypatch, tweak=lambda dlg: dlg._prefix_chk.setChecked(False))
    win._on_run_setfields_clicked()
    assert win.terminal_panel.commands == ["setFields 2>&1 | tee log.setFields"]


def test_run_setfields_cancel_with_0orig(main_window, tmp_path, monkeypatch):
    (tmp_path / "0.orig").mkdir()
    win = main_window
    win.state.current_case_dir = str(tmp_path)
    win.terminal_panel = _FakeTerminalPanel()

    _patch_run_dialog(monkeypatch, accept=False)
    win._on_run_setfields_clicked()
    assert win.terminal_panel.commands == []


def test_run_allrun_warns_when_script_missing(main_window, tmp_path, monkeypatch):
    win = main_window
    win.state.current_case_dir = str(tmp_path)
    win.terminal_panel = _FakeTerminalPanel()

    warnings = []
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *a, **k: warnings.append(a) or QMessageBox.Ok
    )
    win._on_run_allrun_clicked()

    assert len(warnings) == 1
    assert win.terminal_panel.commands == []


def test_run_allrun_confirms_and_sends_command(main_window, tmp_path, monkeypatch):
    (tmp_path / "Allrun").write_text("#!/bin/sh\n")
    win = main_window
    win.state.current_case_dir = str(tmp_path)
    win.terminal_panel = _FakeTerminalPanel()

    monkeypatch.setattr(QMessageBox, "exec", lambda self: QMessageBox.StandardButton.No.value)
    win._on_run_allrun_clicked()
    assert win.terminal_panel.commands == []

    monkeypatch.setattr(QMessageBox, "exec", lambda self: QMessageBox.StandardButton.Yes.value)
    win._on_run_allrun_clicked()
    assert win.terminal_panel.commands == ["./Allrun"]


def _patch_allrun_preflight_choice(monkeypatch, label):
    """Make the custom-button pre-flight QMessageBox 'click' the given button:
    a label string for the added buttons, or QMessageBox.Cancel."""
    monkeypatch.setattr(QMessageBox, "exec", lambda self: 0)
    if label is QMessageBox.Cancel:
        monkeypatch.setattr(
            QMessageBox, "clickedButton", lambda self: self.button(QMessageBox.Cancel)
        )
    else:
        monkeypatch.setattr(
            QMessageBox,
            "clickedButton",
            lambda self: next(b for b in self.buttons() if b.text() == label),
        )


def test_run_allrun_preflight_clean_then_run_when_logs_exist(
    main_window, tmp_path, monkeypatch
):
    (tmp_path / "Allrun").write_text("#!/bin/sh\n")
    (tmp_path / "log.blockMesh").write_text("")
    win = main_window
    win.state.current_case_dir = str(tmp_path)
    win.terminal_panel = _FakeTerminalPanel()

    _patch_allrun_preflight_choice(monkeypatch, "Clean, then run")
    win._on_run_allrun_clicked()
    assert win.terminal_panel.commands == ["foamCleanTutorials && ./Allrun"]


def test_run_allrun_preflight_run_anyway_when_logs_exist(
    main_window, tmp_path, monkeypatch
):
    (tmp_path / "Allrun").write_text("#!/bin/sh\n")
    (tmp_path / "log.icoFoam").write_text("")
    win = main_window
    win.state.current_case_dir = str(tmp_path)
    win.terminal_panel = _FakeTerminalPanel()

    _patch_allrun_preflight_choice(monkeypatch, "Run anyway")
    win._on_run_allrun_clicked()
    assert win.terminal_panel.commands == ["./Allrun"]


def test_run_allrun_preflight_cancel_when_logs_exist(
    main_window, tmp_path, monkeypatch
):
    (tmp_path / "Allrun").write_text("#!/bin/sh\n")
    (tmp_path / "log.icoFoam").write_text("")
    win = main_window
    win.state.current_case_dir = str(tmp_path)
    win.terminal_panel = _FakeTerminalPanel()

    _patch_allrun_preflight_choice(monkeypatch, QMessageBox.Cancel)
    win._on_run_allrun_clicked()
    assert win.terminal_panel.commands == []


def test_run_allclean_warns_when_script_missing(main_window, tmp_path, monkeypatch):
    win = main_window
    win.state.current_case_dir = str(tmp_path)
    win.terminal_panel = _FakeTerminalPanel()

    warnings = []
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *a, **k: warnings.append(a) or QMessageBox.Ok
    )
    win._on_run_allclean_clicked()

    assert len(warnings) == 1
    assert win.terminal_panel.commands == []


def test_run_allclean_confirms_and_sends_command(main_window, tmp_path, monkeypatch):
    (tmp_path / "Allclean").write_text("#!/bin/sh\n")
    win = main_window
    win.state.current_case_dir = str(tmp_path)
    win.terminal_panel = _FakeTerminalPanel()

    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.No)
    win._on_run_allclean_clicked()
    assert win.terminal_panel.commands == []

    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
    win._on_run_allclean_clicked()
    assert win.terminal_panel.commands == ["./Allclean"]


def test_clean_case_confirms_and_sends_command(main_window, tmp_path, monkeypatch):
    win = main_window
    win.state.current_case_dir = str(tmp_path)
    win.terminal_panel = _FakeTerminalPanel()

    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.No)
    win._on_clean_case_clicked()
    assert win.terminal_panel.commands == []

    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
    win._on_clean_case_clicked()
    assert win.terminal_panel.commands == ["foamCleanTutorials"]


def test_clean_case_dialog_mentions_allclean_or_0orig(
    main_window, tmp_path, monkeypatch
):
    win = main_window
    win.state.current_case_dir = str(tmp_path)
    win.terminal_panel = _FakeTerminalPanel()

    texts = []

    def record_question(parent, title, text, *a, **k):
        texts.append(text)
        return QMessageBox.No

    monkeypatch.setattr(QMessageBox, "question", record_question)

    (tmp_path / "0.orig").mkdir()
    win._on_clean_case_clicked()
    assert "0/ will also be removed" in texts[-1]

    # An Allclean script takes precedence over the -auto 0/ note.
    (tmp_path / "Allclean").write_text("#!/bin/sh\n")
    win._on_clean_case_clicked()
    assert "Allclean script" in texts[-1]
    assert "0/ will also be removed" not in texts[-1]


def test_mesh_actions_disabled_without_case_or_terminal(main_window):
    win = main_window
    win.state.current_case_dir = None
    win.terminal_panel = None
    win._update_tools_actions()

    assert win._run_snappyhexmesh_action.isEnabled() is False
    assert win._run_topo_set_action.isEnabled() is False
    assert win._run_setfields_action.isEnabled() is False
    assert win._run_checkmesh_action.isEnabled() is False
    assert win._run_allrun_action.isEnabled() is False
    assert win._run_allclean_action.isEnabled() is False
    assert win._clean_case_action.isEnabled() is False
    assert win._view_log_summary_action.isEnabled() is False


def test_mesh_actions_enabled_with_case_and_terminal(main_window, tmp_path):
    win = main_window
    win.state.current_case_dir = str(tmp_path)
    win.terminal_panel = _FakeTerminalPanel()
    win._update_tools_actions()

    assert win._run_snappyhexmesh_action.isEnabled() is True
    assert win._run_topo_set_action.isEnabled() is True
    assert win._run_setfields_action.isEnabled() is True
    assert win._run_checkmesh_action.isEnabled() is True
    assert win._run_allrun_action.isEnabled() is True
    assert win._run_allclean_action.isEnabled() is True
    assert win._clean_case_action.isEnabled() is True
    # View Log Summary only needs a case, not a terminal.
    assert win._view_log_summary_action.isEnabled() is True


def test_view_log_summary_enabled_without_terminal(main_window, tmp_path):
    win = main_window
    win.state.current_case_dir = str(tmp_path)
    win.terminal_panel = None
    win._update_tools_actions()

    assert win._run_snappyhexmesh_action.isEnabled() is False
    assert win._view_log_summary_action.isEnabled() is True


# ── Run decomposePar… / Run Solver… ──────────────────────────────────────────


def _solver_case(tmp_path, control_dict="application simpleFoam;\n", subdomains=None):
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "controlDict").write_text(control_dict)
    (tmp_path / "constant" / "polyMesh").mkdir(parents=True)
    if subdomains is not None:
        (tmp_path / "system" / "decomposeParDict").write_text(
            f"numberOfSubdomains {subdomains};\nmethod scotch;\n"
        )
    return tmp_path


def _capture_dialog(monkeypatch, accept=True, tweak=None):
    """Patch exec() and return a dict that receives the built dialog."""
    seen = {}

    def fake_exec(self):
        seen["dlg"] = self
        if tweak is not None:
            tweak(self)
        return QDialog.Accepted if accept else QDialog.Rejected

    monkeypatch.setattr(RunToolDialog, "exec", fake_exec)
    return seen


def test_run_solver_prefills_from_control_dict(main_window, tmp_path, monkeypatch):
    win = main_window
    win.state.current_case_dir = str(_solver_case(tmp_path))
    win.terminal_panel = _FakeTerminalPanel()

    seen = _capture_dialog(monkeypatch)
    win._on_run_solver_clicked()

    assert seen["dlg"].windowTitle() == "Run Solver"
    assert win.terminal_panel.commands == ["simpleFoam 2>&1 | tee log.simpleFoam"]


def test_run_solver_uses_retyped_name(main_window, tmp_path, monkeypatch):
    win = main_window
    win.state.current_case_dir = str(_solver_case(tmp_path))
    win.terminal_panel = _FakeTerminalPanel()

    _capture_dialog(monkeypatch, tweak=lambda d: d._exe_combo.setEditText("pimpleFoam"))
    win._on_run_solver_clicked()
    assert win.terminal_panel.commands == ["pimpleFoam 2>&1 | tee log.pimpleFoam"]

    # The override is not remembered: the next dialog starts from controlDict.
    _capture_dialog(monkeypatch)
    win._on_run_solver_clicked()
    assert win.terminal_panel.commands[-1] == "simpleFoam 2>&1 | tee log.simpleFoam"


def test_run_solver_invalid_name_disables_run(main_window, tmp_path, monkeypatch):
    win = main_window
    win.state.current_case_dir = str(_solver_case(tmp_path))
    win.terminal_panel = _FakeTerminalPanel()

    def tweak(dlg):
        dlg._exe_combo.setEditText("simpleFoam; rm -rf /")
        assert not dlg._run_btn.isEnabled()
        dlg._exe_combo.setEditText("")
        assert not dlg._run_btn.isEnabled()

    _capture_dialog(monkeypatch, accept=False, tweak=tweak)
    win._on_run_solver_clicked()
    assert win.terminal_panel.commands == []


def test_run_solver_reads_unsaved_editor_text(main_window, tmp_path, monkeypatch):
    win = main_window
    case = _solver_case(tmp_path)
    win.state.current_case_dir = str(case)
    win.terminal_panel = _FakeTerminalPanel()
    path = str(case / "system" / "controlDict")
    win.state.current_file = path
    win.editor_panel.set_text("application icoFoam;\n")

    seen = _capture_dialog(monkeypatch, accept=False)
    win._on_run_solver_clicked()
    assert seen["dlg"].get_executable() == "icoFoam"


def test_run_solver_foam_run_note(main_window, tmp_path, monkeypatch):
    win = main_window
    win.state.current_case_dir = str(
        _solver_case(tmp_path, "application foamRun;\nsolver incompressibleFluid;\n")
    )
    win.terminal_panel = _FakeTerminalPanel()

    seen = _capture_dialog(monkeypatch)
    win._on_run_solver_clicked()
    from PySide6.QtWidgets import QLabel

    texts = " ".join(lbl.text() for lbl in seen["dlg"].findChildren(QLabel))
    assert "incompressibleFluid" in texts
    assert win.terminal_panel.commands == ["foamRun 2>&1 | tee log.foamRun"]


def test_run_solver_parallel_defaults_on_when_decomposed(
    main_window, tmp_path, monkeypatch
):
    win = main_window
    case = _solver_case(tmp_path, subdomains=4)
    for n in range(4):
        (case / f"processor{n}").mkdir()
    win.state.current_case_dir = str(case)
    win.terminal_panel = _FakeTerminalPanel()

    _capture_dialog(monkeypatch)
    win._on_run_solver_clicked()
    assert win.terminal_panel.commands == [
        "mpirun -np 4 simpleFoam -parallel 2>&1 | tee log.simpleFoam"
    ]


def test_run_solver_parallel_off_and_warned_when_not_decomposed(
    main_window, tmp_path, monkeypatch
):
    win = main_window
    win.state.current_case_dir = str(_solver_case(tmp_path, subdomains=4))
    win.terminal_panel = _FakeTerminalPanel()

    seen = _capture_dialog(monkeypatch)
    win._on_run_solver_clicked()
    dlg = seen["dlg"]
    assert dlg._parallel_chk is not None and not dlg._parallel_chk.isChecked()
    assert win.terminal_panel.commands == ["simpleFoam 2>&1 | tee log.simpleFoam"]


def test_run_solver_no_parallel_checkbox_without_decompose_dict(
    main_window, tmp_path, monkeypatch
):
    win = main_window
    win.state.current_case_dir = str(_solver_case(tmp_path))
    win.terminal_panel = _FakeTerminalPanel()

    seen = _capture_dialog(monkeypatch, accept=False)
    win._on_run_solver_clicked()
    assert seen["dlg"]._parallel_chk is None


def test_run_solver_save_first_checkbox_only_when_dirty(
    main_window, tmp_path, monkeypatch
):
    win = main_window
    case = _solver_case(tmp_path)
    win.state.current_case_dir = str(case)
    win.terminal_panel = _FakeTerminalPanel()

    seen = _capture_dialog(monkeypatch, accept=False)
    win._on_run_solver_clicked()
    assert seen["dlg"]._save_chk is None

    other = str(case / "system" / "fvSchemes")
    win.state.file_buffers[other] = "ddtSchemes { default steadyState; }\n"
    win.state.file_dirty[other] = True
    seen = _capture_dialog(monkeypatch)
    win._on_run_solver_clicked()
    assert seen["dlg"].save_first()
    # Saved to disk before the command went out.
    assert (case / "system" / "fvSchemes").read_text().startswith("ddtSchemes")
    assert not win.state.file_dirty[other]
    assert win.terminal_panel.commands == ["simpleFoam 2>&1 | tee log.simpleFoam"]


def test_run_solver_warns_about_missing_mesh_and_results(
    main_window, tmp_path, monkeypatch
):
    win = main_window
    case = _solver_case(tmp_path, "application simpleFoam;\nstartFrom latestTime;\n")
    (case / "constant" / "polyMesh").rmdir()
    (case / "0").mkdir()
    (case / "100").mkdir()
    win.state.current_case_dir = str(case)
    win.terminal_panel = _FakeTerminalPanel()

    seen = _capture_dialog(monkeypatch, accept=False)
    win._on_run_solver_clicked()
    from PySide6.QtWidgets import QLabel

    texts = " ".join(lbl.text() for lbl in seen["dlg"].findChildren(QLabel))
    assert "No mesh found" in texts
    assert "continues from 100" in texts


def test_run_decomposepar_refuses_without_dict(main_window, tmp_path, monkeypatch):
    win = main_window
    win.state.current_case_dir = str(tmp_path)
    win.terminal_panel = _FakeTerminalPanel()
    warned = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warned.append(a))

    win._on_run_decomposepar_clicked()
    assert warned and win.terminal_panel.commands == []


def test_run_decomposepar_forces_when_already_decomposed(
    main_window, tmp_path, monkeypatch
):
    win = main_window
    case = _solver_case(tmp_path, subdomains=2)
    win.state.current_case_dir = str(case)
    win.terminal_panel = _FakeTerminalPanel()

    _capture_dialog(monkeypatch)
    win._on_run_decomposepar_clicked()
    assert win.terminal_panel.commands == ["decomposePar 2>&1 | tee log.decomposePar"]

    (case / "processor0").mkdir()
    _capture_dialog(monkeypatch)
    win._on_run_decomposepar_clicked()
    assert win.terminal_panel.commands[-1] == (
        "decomposePar -force 2>&1 | tee log.decomposePar"
    )


# ── existing log: keep under a suffix, or overwrite ──────────────────────────


def test_run_solver_no_log_choice_without_existing_log(main_window, tmp_path, monkeypatch):
    win = main_window
    win.state.current_case_dir = str(_solver_case(tmp_path))
    win.terminal_panel = _FakeTerminalPanel()

    seen = _capture_dialog(monkeypatch)
    win._on_run_solver_clicked()
    assert not seen["dlg"]._log_box.isVisibleTo(seen["dlg"])
    assert win.terminal_panel.commands == ["simpleFoam 2>&1 | tee log.simpleFoam"]


def test_run_solver_keeps_existing_log_as_next_part(main_window, tmp_path, monkeypatch):
    win = main_window
    case = _solver_case(tmp_path)
    (case / "log.simpleFoam").write_text("run 3")
    (case / "log.simpleFoam.part1").write_text("run 1")
    (case / "log.simpleFoam.part2").write_text("run 2")
    win.state.current_case_dir = str(case)
    win.terminal_panel = _FakeTerminalPanel()

    _capture_dialog(monkeypatch)
    win._on_run_solver_clicked()
    assert win.terminal_panel.commands == [
        "mv log.simpleFoam log.simpleFoam.part3 && simpleFoam 2>&1 | tee log.simpleFoam"
    ]


def test_run_solver_keeps_log_under_typed_suffix(main_window, tmp_path, monkeypatch):
    win = main_window
    case = _solver_case(tmp_path)
    (case / "log.simpleFoam").write_text("x")
    win.state.current_case_dir = str(case)
    win.terminal_panel = _FakeTerminalPanel()

    def tweak(dlg):
        dlg._suffix_edit.setText("before-refine")
        dlg._suffix_typed = True

    _capture_dialog(monkeypatch, tweak=tweak)
    win._on_run_solver_clicked()
    assert win.terminal_panel.commands == [
        "mv log.simpleFoam log.simpleFoam.before-refine && "
        "simpleFoam 2>&1 | tee log.simpleFoam"
    ]


def test_run_solver_overwrite_choice_sends_no_mv(main_window, tmp_path, monkeypatch):
    win = main_window
    case = _solver_case(tmp_path)
    (case / "log.simpleFoam").write_text("x")
    win.state.current_case_dir = str(case)
    win.terminal_panel = _FakeTerminalPanel()

    _capture_dialog(monkeypatch, tweak=lambda d: d._overwrite_radio.setChecked(True))
    win._on_run_solver_clicked()
    assert win.terminal_panel.commands == ["simpleFoam 2>&1 | tee log.simpleFoam"]


@pytest.mark.parametrize("suffix", ["", ".hidden", "a b", "a/b", "x;rm", "$(x)"])
def test_run_solver_bad_suffix_disables_run(main_window, tmp_path, monkeypatch, suffix):
    win = main_window
    case = _solver_case(tmp_path)
    (case / "log.simpleFoam").write_text("x")
    win.state.current_case_dir = str(case)
    win.terminal_panel = _FakeTerminalPanel()

    def tweak(dlg):
        dlg._suffix_edit.setText(suffix)
        assert not dlg._run_btn.isEnabled()
        assert "suffix" in dlg._preview.text()

    _capture_dialog(monkeypatch, accept=False, tweak=tweak)
    win._on_run_solver_clicked()


def test_run_solver_suffix_collision_disables_run(main_window, tmp_path, monkeypatch):
    win = main_window
    case = _solver_case(tmp_path)
    (case / "log.simpleFoam").write_text("x")
    (case / "log.simpleFoam.part1").write_text("older run")
    win.state.current_case_dir = str(case)
    win.terminal_panel = _FakeTerminalPanel()

    def tweak(dlg):
        assert dlg._suffix_edit.text() == "part2"
        assert dlg._run_btn.isEnabled()
        dlg._suffix_edit.setText("part1")
        assert not dlg._run_btn.isEnabled()
        assert "log.simpleFoam.part1 already exists" in dlg._preview.text()
        # Overwriting the *current* log is an explicit, separate choice.
        dlg._overwrite_radio.setChecked(True)
        assert dlg._run_btn.isEnabled()

    _capture_dialog(monkeypatch, accept=False, tweak=tweak)
    win._on_run_solver_clicked()


def test_run_solver_log_choice_follows_solver_name(main_window, tmp_path, monkeypatch):
    win = main_window
    case = _solver_case(tmp_path)
    (case / "log.pimpleFoam").write_text("x")
    (case / "log.pimpleFoam.part1").write_text("x")
    win.state.current_case_dir = str(case)
    win.terminal_panel = _FakeTerminalPanel()

    def tweak(dlg):
        # log.simpleFoam does not exist: no choice to make.
        assert not dlg._log_exists
        dlg._exe_combo.setEditText("pimpleFoam")
        assert dlg._log_exists
        assert dlg._suffix_edit.text() == "part2"

    _capture_dialog(monkeypatch, tweak=tweak)
    win._on_run_solver_clicked()
    assert win.terminal_panel.commands == [
        "mv log.pimpleFoam log.pimpleFoam.part2 && pimpleFoam 2>&1 | tee log.pimpleFoam"
    ]


def test_run_solver_parallel_keeps_log_too(main_window, tmp_path, monkeypatch):
    win = main_window
    case = _solver_case(tmp_path, subdomains=2)
    for n in range(2):
        (case / f"processor{n}").mkdir()
    (case / "log.simpleFoam").write_text("x")
    win.state.current_case_dir = str(case)
    win.terminal_panel = _FakeTerminalPanel()

    _capture_dialog(monkeypatch)
    win._on_run_solver_clicked()
    assert win.terminal_panel.commands == [
        "mv log.simpleFoam log.simpleFoam.part1 && "
        "mpirun -np 2 simpleFoam -parallel 2>&1 | tee log.simpleFoam"
    ]


# ── parallel safeguards ───────────────────────────────────────────────────────


def _labels(dlg):
    from PySide6.QtWidgets import QLabel

    return " ".join(lbl.text() for lbl in dlg.findChildren(QLabel))


def test_run_solver_subdomain_mismatch_warns_and_unticks(main_window, tmp_path, monkeypatch):
    win = main_window
    case = _solver_case(tmp_path, subdomains=8)
    for n in range(4):
        (case / f"processor{n}").mkdir()
    win.state.current_case_dir = str(case)
    win.terminal_panel = _FakeTerminalPanel()

    seen = _capture_dialog(monkeypatch, accept=False)
    win._on_run_solver_clicked()
    dlg = seen["dlg"]
    assert "asks for 8 subdomains but the case is decomposed into 4" in _labels(dlg)
    assert not dlg._parallel_chk.isChecked()
    # -np follows the decomposition, which is what mpirun must match.
    assert "-np 4" in dlg._parallel_chk.text()


def test_run_solver_stale_zero_dir_warns_and_unticks(main_window, tmp_path, monkeypatch):
    import os

    win = main_window
    case = _solver_case(tmp_path, subdomains=2)
    for n in range(2):
        (case / f"processor{n}" / "0").mkdir(parents=True)
        (case / f"processor{n}" / "0" / "U").write_text("decomposed")
    (case / "0").mkdir()
    (case / "0" / "U").write_text("edited later")
    old = os.path.getmtime(case / "processor0" / "0" / "U")
    os.utime(case / "0" / "U", (old + 60, old + 60))
    win.state.current_case_dir = str(case)
    win.terminal_panel = _FakeTerminalPanel()

    seen = _capture_dialog(monkeypatch, accept=False)
    win._on_run_solver_clicked()
    dlg = seen["dlg"]
    assert "0/ changed after the case was decomposed" in _labels(dlg)
    assert not dlg._parallel_chk.isChecked()


def test_run_solver_unsaved_zero_field_counts_as_stale(main_window, tmp_path, monkeypatch):
    import os

    win = main_window
    case = _solver_case(tmp_path, subdomains=2)
    (case / "0").mkdir()
    (case / "0" / "U").write_text("original")
    for n in range(2):
        (case / f"processor{n}" / "0").mkdir(parents=True)
        (case / f"processor{n}" / "0" / "U").write_text("decomposed")
    old = os.path.getmtime(case / "processor0" / "0" / "U")
    os.utime(case / "0" / "U", (old - 60, old - 60))
    path = str(case / "0" / "U")
    win.state.file_buffers[path] = "edited, not saved"
    win.state.file_dirty[path] = True
    win.state.current_case_dir = str(case)
    win.terminal_panel = _FakeTerminalPanel()

    seen = _capture_dialog(monkeypatch, accept=False)
    win._on_run_solver_clicked()
    assert "0/ changed after the case was decomposed" in _labels(seen["dlg"])


# ── decomposePar -force safeguard ─────────────────────────────────────────────


def test_run_decomposepar_never_forces_over_unreconstructed_results(
    main_window, tmp_path, monkeypatch
):
    win = main_window
    case = _solver_case(tmp_path, subdomains=2)
    for n in range(2):
        (case / f"processor{n}" / "0.5").mkdir(parents=True)
    win.state.current_case_dir = str(case)
    win.terminal_panel = _FakeTerminalPanel()
    # Even a remembered -force from an earlier run is overridden.
    win.state.run_tool_options["decomposePar"] = {"-force": True}

    seen = _capture_dialog(monkeypatch)
    win._on_run_decomposepar_clicked()
    assert "not been reconstructed: 0.5" in _labels(seen["dlg"])
    assert win.terminal_panel.commands == ["decomposePar 2>&1 | tee log.decomposePar"]


def test_run_decomposepar_reconstructed_times_are_not_flagged(
    main_window, tmp_path, monkeypatch
):
    win = main_window
    case = _solver_case(tmp_path, subdomains=2)
    for n in range(2):
        (case / f"processor{n}" / "0.5").mkdir(parents=True)
    (case / "0.5").mkdir()
    win.state.current_case_dir = str(case)
    win.terminal_panel = _FakeTerminalPanel()

    _capture_dialog(monkeypatch)
    win._on_run_decomposepar_clicked()
    assert win.terminal_panel.commands == [
        "decomposePar -force 2>&1 | tee log.decomposePar"
    ]
