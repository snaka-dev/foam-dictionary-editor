# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""
Tests for ui/terminal_panel.py.

These tests cover the synchronous logic of SimpleTerminalWidget and TerminalPanel
without exercising event-driven I/O or the running shell process.
A module-scoped QApplication is created so that QProcess and QWidget can be
instantiated in the test environment.
"""
from __future__ import annotations

import sys

import pytest
from PySide6.QtWidgets import QApplication

from ui.terminal_panel import SimpleTerminalWidget, TerminalPanel, _XTERM_AVAILABLE


# ── QApplication fixture ──────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def qapp():
    """Module-scoped QApplication required by QProcess and QWidget."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])
    yield app


# ── per-test widget fixtures with cleanup ─────────────────────────────────────

@pytest.fixture
def simple_widget(qapp):
    widget = SimpleTerminalWidget()
    yield widget
    widget._cleanup()


@pytest.fixture
def terminal_panel(qapp):
    panel = TerminalPanel()
    yield panel
    if not _XTERM_AVAILABLE:
        panel._widget._cleanup()


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
    def test_cleanup_sets_closing_flag(self, qapp):
        """_cleanup sets _closing to True"""
        widget = SimpleTerminalWidget()
        assert widget._closing is False
        widget._cleanup()
        assert widget._closing is True

    def test_on_finished_does_not_restart_when_closing(self, qapp):
        """_on_finished returns early without appending a restart message when _closing is True"""
        widget = SimpleTerminalWidget()
        widget._closing = True
        widget._on_finished(0)
        assert "Restarting" not in widget._output.toPlainText()
        widget._cleanup()

    def test_on_finished_appends_restart_message_when_not_closing(self, qapp):
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
    def test_tab_label_starts_with_terminal(self, terminal_panel):
        """tab_label always begins with the string 'Terminal'"""
        assert terminal_panel.tab_label.startswith("Terminal")

    def test_tab_label_simple_when_no_xterm(self, terminal_panel):
        """tab_label is 'Terminal (Simple)' when xterm is unavailable"""
        if not _XTERM_AVAILABLE:
            assert terminal_panel.tab_label == "Terminal (Simple)"

    def test_tab_label_terminal_when_xterm_available(self, terminal_panel):
        """tab_label is 'Terminal' when xterm is available"""
        if _XTERM_AVAILABLE:
            assert terminal_panel.tab_label == "Terminal"

    def test_tab_label_matches_use_xterm(self, terminal_panel):
        """tab_label is consistent with xterm availability"""
        if _XTERM_AVAILABLE:
            assert terminal_panel.tab_label == "Terminal"
        else:
            assert "Simple" in terminal_panel.tab_label


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
