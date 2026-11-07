# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""
Tests for ui/terminal_panel.py.

These tests cover the synchronous logic of SimpleTerminalWidget and TerminalPanel
without exercising event-driven I/O or the running shell process.
"""
from __future__ import annotations

import pytest

from ui.panels.terminal_panel import _XTERM_AVAILABLE, SimpleTerminalWidget, TerminalPanel

# ── per-test widget fixtures with cleanup ─────────────────────────────────────

@pytest.fixture
def shell_cwd(tmp_path, monkeypatch):
    """Run the widgets' shell in a throwaway directory.

    Both widgets start a real shell in their constructor, and every command a
    test sends is really executed by it -- so a command with a side effect
    writes into whatever directory the test process was launched from, i.e. the
    repository root. ``log.blockMesh`` used to appear there after a run.

    The shell inherits the cwd it is forked with, and the fork happens inside
    the constructor, so the chdir has to come first. Deliberately not
    ``set_working_directory``, which the tests below assert on.
    """
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def simple_widget(qapp, shell_cwd, destroy_widget):
    widget = SimpleTerminalWidget()
    yield widget
    widget._cleanup()  # owns a PTY; must run while the widget lives
    destroy_widget(widget)


@pytest.fixture
def terminal_panel(qapp, shell_cwd, destroy_widget):
    panel = TerminalPanel()
    yield panel
    if not _XTERM_AVAILABLE:
        panel._widget._cleanup()  # owns a PTY; must run while the widget lives
    destroy_widget(panel)


# ── SimpleTerminalWidget: initial state ───────────────────────────────────────

class TestSimpleTerminalWidgetInitialState:
    def test_closing_flag_starts_false(self, simple_widget):
        """_closing is False immediately after construction"""
        assert simple_widget._closing is False

    def test_history_starts_empty(self, simple_widget):
        """Command history is empty on construction"""
        assert simple_widget._history == []

    def test_history_pos_starts_at_zero(self, simple_widget):
        """History position is 0 on construction"""
        assert simple_widget._history_pos == 0

    def test_cwd_starts_as_none(self, simple_widget):
        """Working directory is None before set_working_directory is called"""
        assert simple_widget._cwd is None


# ── SimpleTerminalWidget: working directory ───────────────────────────────────

class TestSimpleTerminalWidgetWorkingDirectory:
    def test_set_working_directory_stores_path(self, simple_widget):
        """set_working_directory records the path in _cwd"""
        simple_widget.set_working_directory("/tmp/test_case")
        assert simple_widget._cwd == "/tmp/test_case"

    def test_set_working_directory_overwrites_previous(self, simple_widget):
        """Calling set_working_directory twice keeps the latest path"""
        simple_widget.set_working_directory("/tmp/case_a")
        simple_widget.set_working_directory("/tmp/case_b")
        assert simple_widget._cwd == "/tmp/case_b"


# ── SimpleTerminalWidget: cleanup ─────────────────────────────────────────────

class TestSimpleTerminalWidgetCleanup:
    def test_cleanup_sets_closing_flag(self, qapp, shell_cwd):
        """_cleanup sets _closing to True"""
        widget = SimpleTerminalWidget()
        assert widget._closing is False
        widget._cleanup()
        assert widget._closing is True

    def test_on_finished_does_not_restart_when_closing(self, qapp, shell_cwd):
        """_on_finished returns early without appending a restart message when _closing is True"""
        widget = SimpleTerminalWidget()
        widget._closing = True
        widget._on_finished(0)
        assert "Restarting" not in widget._output.toPlainText()
        widget._cleanup()

    def test_on_finished_appends_restart_message_when_not_closing(self, qapp, shell_cwd):
        """_on_finished appends a restart message when _closing is False"""
        widget = SimpleTerminalWidget()
        widget._on_finished(1)
        assert "Restarting" in widget._output.toPlainText()
        widget._cleanup()


# ── SimpleTerminalWidget: command history ─────────────────────────────────────

class TestSimpleTerminalWidgetHistory:
    def test_command_added_to_history(self, simple_widget):
        """A non-empty command entered via _on_enter is appended to history"""
        simple_widget._input.setText("ls -la")
        simple_widget._on_enter()
        assert "ls -la" in simple_widget._history

    def test_history_pos_advances_after_command(self, simple_widget):
        """history_pos equals len(history) after entering a new command"""
        simple_widget._input.setText("pwd")
        simple_widget._on_enter()
        assert simple_widget._history_pos == len(simple_widget._history)

    def test_empty_input_not_added_to_history(self, simple_widget):
        """An empty or whitespace-only input is not added to history"""
        before = len(simple_widget._history)
        simple_widget._input.setText("   ")
        simple_widget._on_enter()
        assert len(simple_widget._history) == before

    def test_input_cleared_after_enter(self, simple_widget):
        """The input field is cleared after pressing Enter"""
        simple_widget._input.setText("echo hello")
        simple_widget._on_enter()
        assert simple_widget._input.text() == ""

    def test_multiple_commands_in_history(self, simple_widget):
        """Multiple commands are all present in history in order"""
        for cmd in ["cmd1", "cmd2", "cmd3"]:
            simple_widget._input.setText(cmd)
            simple_widget._on_enter()
        history = simple_widget._history
        assert history[-3:] == ["cmd1", "cmd2", "cmd3"]


# ── TerminalPanel: tab_label ──────────────────────────────────────────────────

class TestTerminalPanelTabLabel:
    def test_tab_label_is_terminal(self, terminal_panel):
        """tab_label is always 'Terminal' regardless of backend"""
        assert terminal_panel.tab_label == "Terminal"


# ── TerminalPanel: set_working_directory delegation ──────────────────────────

class TestTerminalPanelWorkingDirectory:
    def test_set_working_directory_stored_in_simple_widget(self, terminal_panel):
        """set_working_directory is forwarded to SimpleTerminalWidget._cwd when not using xterm"""
        if not _XTERM_AVAILABLE:
            terminal_panel.set_working_directory("/tmp/foam_case")
            assert terminal_panel._widget._cwd == "/tmp/foam_case"

    def test_set_working_directory_does_not_raise_with_xterm(self, terminal_panel):
        """set_working_directory does not raise when XtermTerminalWidget is active"""
        if _XTERM_AVAILABLE:
            terminal_panel.set_working_directory("/tmp/foam_case")


# ── SimpleTerminalWidget: run_command ─────────────────────────────────────────

class TestSimpleTerminalWidgetRunCommand:
    def test_run_command_echoes_to_output(self, simple_widget):
        """run_command echoes the command into the output pane, like a typed one"""
        simple_widget.run_command("blockMesh 2>&1 | tee log.blockMesh")
        assert "$ blockMesh 2>&1 | tee log.blockMesh" in simple_widget._output.toPlainText()


# ── TerminalPanel: run_command delegation ─────────────────────────────────────

class TestTerminalPanelRunCommand:
    def test_run_command_forwarded_to_simple_widget(self, terminal_panel):
        """run_command is forwarded to SimpleTerminalWidget when not using xterm"""
        if not _XTERM_AVAILABLE:
            terminal_panel.run_command("blockMesh")
            assert "$ blockMesh" in terminal_panel._widget._output.toPlainText()

    def test_run_command_does_not_raise_with_xterm(self, terminal_panel):
        """run_command does not raise when XtermTerminalWidget is active"""
        if _XTERM_AVAILABLE:
            terminal_panel.run_command("blockMesh")


# ── running-command guard (closing / switching mode ends the shell) ──────────


def test_a_command_sent_to_the_shell_is_reported_running(simple_widget, qapp):
    import sys
    import time

    from services.process_tree import running_command_names

    if not sys.platform.startswith("linux"):
        pytest.skip("reads /proc")
    simple_widget.run_command("sleep 30")
    deadline = time.monotonic() + 5
    names: list[str] = []
    while time.monotonic() < deadline and not names:
        qapp.processEvents()
        names = running_command_names(simple_widget.shell_pid())
        time.sleep(0.05)
    assert names == ["sleep"]


def test_confirm_does_not_ask_when_idle(terminal_panel, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(terminal_panel, "running_commands", lambda: [])
    asked = []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: asked.append(a))
    assert terminal_panel.confirm_stop_running(terminal_panel, "Closing FoDE")
    assert asked == []


@pytest.mark.parametrize("answer, expected", [("Yes", True), ("No", False)])
def test_confirm_names_the_command_and_defaults_to_no(
    terminal_panel, monkeypatch, answer, expected
):
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(terminal_panel, "running_commands", lambda: ["simpleFoam"])
    seen = {}

    def fake_question(parent, title, text, buttons, default):
        seen.update(text=text, default=default)
        return getattr(QMessageBox.StandardButton, answer)

    monkeypatch.setattr(QMessageBox, "question", fake_question)
    assert terminal_panel.confirm_stop_running(terminal_panel, "Closing FoDE") is expected
    assert "simpleFoam" in seen["text"] and "Closing FoDE" in seen["text"]
    assert seen["default"] == QMessageBox.StandardButton.No


def test_declined_mode_switch_keeps_the_shell(terminal_panel, monkeypatch):
    monkeypatch.setattr(terminal_panel, "confirm_stop_running", lambda *a: False)
    widget = terminal_panel._widget
    was_xterm = terminal_panel.use_xterm
    terminal_panel._xterm_chk.setChecked(not was_xterm)
    assert terminal_panel._widget is widget
    assert terminal_panel.use_xterm == was_xterm
    assert terminal_panel._xterm_chk.isChecked() == was_xterm


@pytest.mark.skipif(not _XTERM_AVAILABLE, reason="needs the PTY backend")
def test_the_xterm_shell_reports_a_running_command(qapp, shell_cwd):
    """The xterm path runs an interactive bash on a PTY -- check it for real."""
    import time

    from services.process_tree import running_command_names
    from ui.widgets._xterm_widget import PtyBackend

    backend = PtyBackend()
    backend.start_shell(str(shell_cwd))
    try:
        backend.write(b"sleep 30\n")
        deadline = time.monotonic() + 5
        names: list[str] = []
        while time.monotonic() < deadline and not names:
            qapp.processEvents()
            names = running_command_names(backend.pid, job_control=True)
            time.sleep(0.05)
        assert names == ["sleep"]
    finally:
        backend.stop()


def _wait_for(qapp, condition, seconds=10):
    import time

    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline and not condition():
        qapp.processEvents()
        time.sleep(0.05)
    return condition()


def test_a_following_tail_is_stopped_before_a_command(terminal_panel, qapp, shell_cwd):
    """Simple mode: the tail of a background run must not swallow the next command."""
    import sys

    from services.process_tree import follower_pids

    if not sys.platform.startswith("linux"):
        pytest.skip("reads /proc")
    if terminal_panel._use_xterm:
        terminal_panel._xterm_chk.setChecked(False)  # to the Simple shell
    terminal_panel.run_command("tail -f /dev/null")
    assert _wait_for(qapp, lambda: follower_pids(terminal_panel._shell_pid()))
    assert terminal_panel.running_commands() == []  # closing would not ask
    terminal_panel.run_command("echo ran > marker")
    assert _wait_for(qapp, lambda: (shell_cwd / "marker").exists())
    assert _wait_for(qapp, lambda: (shell_cwd / "marker").read_text() == "ran\n")


def test_xterm_reads_a_command_typed_behind_a_stopped_tail(qapp, shell_cwd):
    """xterm mode: under job control the tail is a foreground job of its own;
    once it is stopped, bash reads what was typed meanwhile."""
    import os
    import signal
    import sys

    from services.process_tree import follower_pids
    from ui.widgets._xterm_widget import PtyBackend

    if not sys.platform.startswith("linux"):
        pytest.skip("reads /proc")
    backend = PtyBackend()
    backend.start_shell(str(shell_cwd))
    try:
        backend.write(b"tail -f /dev/null\n")
        assert _wait_for(qapp, lambda: follower_pids(backend.pid, job_control=True))
        # TerminalPanel.run_command's order: stop the followers, then type.
        for pid in follower_pids(backend.pid, job_control=True):
            os.kill(pid, signal.SIGTERM)
        backend.write(b"echo ran > marker\n")
        assert _wait_for(qapp, lambda: (shell_cwd / "marker").exists())
    finally:
        backend.stop()
