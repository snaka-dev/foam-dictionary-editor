# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QVBoxLayout, QWidget

from ui._simple_terminal_widget import SimpleTerminalWidget
from ui._xterm_widget import _XTERM_AVAILABLE

if _XTERM_AVAILABLE:
    from ui._xterm_widget import XtermTerminalWidget


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

        self._xterm_chk = QCheckBox("xterm terminal  (hides BlockMesh 3-D panel)")
        self._xterm_chk.setEnabled(_XTERM_AVAILABLE)
        if not _XTERM_AVAILABLE:
            self._xterm_chk.setToolTip("Not available: QtWebEngine / PTY not installed")

        self._body = QVBoxLayout()
        self._body.setContentsMargins(0, 0, 0, 0)

        # Default to xterm when available; bypass the timer-delayed toggle path
        # by constructing the widget directly and setting the checkbox silently.
        if _XTERM_AVAILABLE:
            self._use_xterm = True
            self._xterm_chk.blockSignals(True)
            self._xterm_chk.setChecked(True)
            self._xterm_chk.blockSignals(False)
            self._widget: QWidget = XtermTerminalWidget(self)
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
        return "Terminal"

    def cleanup(self) -> None:
        cleanup = getattr(self._widget, "cleanup", None)
        if callable(cleanup):
            cleanup()

    def set_working_directory(self, path: str) -> None:
        self._cwd = path
        self._widget.set_working_directory(path)  # type: ignore[union-attr]

    # ── private ───────────────────────────────────────────────────────────────

    def _on_toggle(self, checked: bool) -> None:
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

    def _replace_widget(self, new_widget: QWidget) -> None:
        self._body.removeWidget(self._widget)
        cleanup = getattr(self._widget, "cleanup", None)
        if callable(cleanup):
            cleanup()
        self._widget.deleteLater()
        self._widget = new_widget
        self._body.addWidget(self._widget)
        if self._cwd:
            self._widget.set_working_directory(self._cwd)  # type: ignore[union-attr]

    def _switch_to_simple(self) -> None:
        self._replace_widget(SimpleTerminalWidget(self))
        self._use_xterm = False
        # Tell main_window to re-add the BlockMesh tab and re-init VTK.
        self.mode_changed.emit(False)
