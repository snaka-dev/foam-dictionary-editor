# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import os
import signal

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QMessageBox, QVBoxLayout, QWidget

from i18n import tr
from services.process_tree import follower_pids, running_command_names
from ui.widgets._simple_terminal_widget import SimpleTerminalWidget
from ui.widgets._xterm_widget import _XTERM_AVAILABLE

if _XTERM_AVAILABLE:
    from ui.widgets._xterm_widget import XtermTerminalWidget


class TerminalPanel(QWidget):
    """Bottom-panel terminal.

    Starts in Simple mode (QProcess, no GPU dependency).  On Linux/macOS with
    QtWebEngine available the user can switch to the full xterm.js terminal at
    runtime; this hides the BlockMesh 3-D panel (and vice versa) to avoid the
    WebEngine / VTK OpenGL context conflict.

    Switch-to-xterm sequence (order matters for OpenGL safety):
      1. mode_changed(True) fires → main_window shuts down VTK synchronously.
      2. 400 ms timer fires → XtermTerminalWidget is created (WebEngine starts).
    Switch-to-simple sequence:
      1. XtermTerminalWidget is cleaned up and deleted.
      2. SimpleTerminalWidget takes its place.
      3. mode_changed(False) fires → main_window re-inits VTK after 300 ms.
    """

    # True = switched to xterm (BlockMesh should hide); False = back to Simple
    mode_changed = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cwd: str | None = None

        self._xterm_chk = QCheckBox(tr("xterm terminal  (hides BlockMesh 3-D panel)"))
        self._xterm_chk.setEnabled(_XTERM_AVAILABLE)
        if not _XTERM_AVAILABLE:
            self._xterm_chk.setToolTip(tr("Not available: QtWebEngine / PTY not installed"))

        self._body = QVBoxLayout()
        self._body.setContentsMargins(0, 0, 0, 0)

        # Default to xterm when available; bypass the timer-delayed toggle path
        # by constructing the widget directly and setting the checkbox silently.
        if _XTERM_AVAILABLE:
            self._use_xterm = True
            self._xterm_chk.blockSignals(True)
            self._xterm_chk.setChecked(True)
            self._xterm_chk.blockSignals(False)
            self._widget: SimpleTerminalWidget | XtermTerminalWidget = XtermTerminalWidget(self)
        else:
            self._use_xterm = False
            self._widget = SimpleTerminalWidget(self)
        self._body.addWidget(self._widget)

        self._xterm_chk.toggled.connect(self._on_toggle)

        header = QHBoxLayout()
        header.setContentsMargins(4, 2, 4, 0)
        header.addWidget(self._xterm_chk)
        header.addStretch()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addLayout(header)
        root.addLayout(self._body, 1)

    @property
    def use_xterm(self) -> bool:
        return self._use_xterm

    @property
    def tab_label(self) -> str:
        return tr("Terminal")

    def set_use_xterm(self, use_xterm: bool) -> None:
        """Switch backend as if the user had clicked the checkbox.

        Goes through the same toggle path, so ``mode_changed`` still fires and
        the BlockMesh panel is hidden/re-shown exactly as on a real click.
        Switching to xterm is asynchronous (see ``_on_toggle``); switching back
        to Simple completes before this returns. A request for xterm where it is
        unavailable is ignored, as the disabled checkbox would.
        """
        if use_xterm and not _XTERM_AVAILABLE:
            return
        if use_xterm == self._use_xterm:
            return
        self._xterm_chk.setChecked(use_xterm)

    def cleanup(self) -> None:
        cleanup = getattr(self._widget, "cleanup", None)
        if callable(cleanup):
            cleanup()

    def set_working_directory(self, path: str) -> None:
        self._cwd = path
        self._widget.set_working_directory(path)

    def run_command(self, cmd: str) -> None:
        # A `tail -F` following a background run holds the shell until it
        # ends; stop it so the command runs now. The run itself is detached
        # and untouched. The command is read once the tail has gone -- the
        # terminal buffers it meanwhile, and tail never reads its input.
        for pid in follower_pids(self._shell_pid(), job_control=self._use_xterm):
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
        self._widget.run_command(cmd)

    def _shell_pid(self) -> int | None:
        shell_pid = getattr(self._widget, "shell_pid", None)
        return shell_pid() if callable(shell_pid) else None

    def running_commands(self) -> list[str]:
        """What the shell is still running (``["simpleFoam"]``), or [] when idle.

        Anything that ends the shell -- closing the window, switching
        terminal mode -- ends these with it, so both ask first.
        """
        return running_command_names(
            self._shell_pid(),
            # The xterm shell is interactive, with job control -- see
            # running_command_names for why that changes the test.
            job_control=self._use_xterm,
        )

    def confirm_stop_running(self, parent: QWidget, action: str) -> bool:
        """Ask before *action* ends a running command; True to go ahead.

        True straight away when nothing is running. The question defaults to
        No: answering it by reflex must not cost a long run.
        """
        names = self.running_commands()
        if not names:
            return True
        reply = QMessageBox.question(
            parent,
            tr("Command still running"),
            tr(
                "{names} is still running in the Terminal tab.\n"
                "{action} stops it, and a solver stopped this way does not "
                "write its current time step.\n\nContinue anyway?"
            ).format(names=", ".join(names), action=action),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    # ── private ───────────────────────────────────────────────────────────────

    def _on_toggle(self, checked: bool) -> None:
        # Switching mode replaces the shell, and whatever it is running with it.
        if not self.confirm_stop_running(self, tr("Switching the terminal mode")):
            self._xterm_chk.blockSignals(True)
            self._xterm_chk.setChecked(not checked)
            self._xterm_chk.blockSignals(False)
            return
        if checked:
            # Disable checkbox during transition to prevent double-clicks.
            self._xterm_chk.setEnabled(False)
            # Step 1: tell main_window to shut down VTK (synchronous signal).
            self.mode_changed.emit(True)
            # Step 2: wait for VTK's OpenGL context to fully release, then
            # create WebEngine.  400 ms is conservative; one event-loop tick
            # would suffice if deleteLater fires cleanly, but GPU teardown
            # can be slower.
            QTimer.singleShot(400, self._finish_switch_to_xterm)
        else:
            self._switch_to_simple()

    def _finish_switch_to_xterm(self) -> None:
        self._replace_widget(XtermTerminalWidget(self))
        self._use_xterm = True
        self._xterm_chk.setEnabled(True)

    def _replace_widget(self, new_widget: SimpleTerminalWidget | XtermTerminalWidget) -> None:
        self._body.removeWidget(self._widget)
        cleanup = getattr(self._widget, "cleanup", None)
        if callable(cleanup):
            cleanup()
        self._widget.deleteLater()
        self._widget = new_widget
        self._body.addWidget(self._widget)
        if self._cwd:
            self._widget.set_working_directory(self._cwd)

    def _switch_to_simple(self) -> None:
        self._replace_widget(SimpleTerminalWidget(self))
        self._use_xterm = False
        # Tell main_window to re-add the BlockMesh tab and re-init VTK.
        self.mode_changed.emit(False)
