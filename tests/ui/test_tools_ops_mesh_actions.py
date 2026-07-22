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

from PySide6.QtWidgets import QDialog, QMessageBox, QWidget

from ui.dialogs.run_tool_dialog import RunToolDialog


class _FakeTerminalPanel(QWidget):
    """A real QWidget (bottom_tabs.indexOf() requires one) standing in for the
    terminal panel, recording run_command() calls instead of spawning a shell."""

    def __init__(self):
        super().__init__()
        self.commands: list[str] = []

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

    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.No)
    win._on_run_allrun_clicked()
    assert win.terminal_panel.commands == []

    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
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
