# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import re
import shlex
import sys

from PySide6.QtCore import QEvent, QProcess, Qt
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

_ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


class SimpleTerminalWidget(QWidget):
    """QProcess-based terminal: plain text I/O, no WebEngine, no GPU dependency."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._cwd: str | None = None
        self._history: list[str] = []
        self._history_pos: int = 0
        self._closing = False

        font = QFont("Consolas" if sys.platform == "win32" else "Monospace", 10)

        self._output = QPlainTextEdit()
        self._output.setReadOnly(True)
        self._output.setFont(font)
        self._output.setMaximumBlockCount(5000)
        self._apply_dark_theme()

        self._input = QLineEdit()
        self._input.setFont(font)
        self._input.setPlaceholderText("Enter command and press Enter")
        self._input.returnPressed.connect(self._on_enter)
        self._input.installEventFilter(self)

        clear_btn = QToolButton()
        clear_btn.setText("Clear")
        clear_btn.clicked.connect(self._output.clear)

        input_row = QHBoxLayout()
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.setSpacing(4)
        input_row.addWidget(QLabel("$"))
        input_row.addWidget(self._input)
        input_row.addWidget(clear_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        layout.addWidget(self._output)
        layout.addLayout(input_row)

        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.MergedChannels)
        self._process.readyReadStandardOutput.connect(self._on_output)
        self._process.finished.connect(self._on_finished)
        self._start_shell()

        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._cleanup)

    def cleanup(self) -> None:
        self._cleanup()

    def _cleanup(self) -> None:
        self._closing = True
        if self._process.state() != QProcess.NotRunning:
            self._process.terminate()
            if not self._process.waitForFinished(3000):
                self._process.kill()

    def set_working_directory(self, path: str) -> None:
        self._cwd = path
        if self._process.state() == QProcess.Running:
            self._execute(f"cd {shlex.quote(path)}")

    def _apply_dark_theme(self) -> None:
        palette = self._output.palette()
        palette.setColor(QPalette.Base, QColor("#1e1e1e"))
        palette.setColor(QPalette.Text, QColor("#d4d4d4"))
        self._output.setPalette(palette)

    def _start_shell(self) -> None:
        if sys.platform == "win32":
            self._process.start("cmd.exe", ["/Q"])
        else:
            self._process.start("bash", ["--norc", "--noprofile"])

    def _on_enter(self) -> None:
        cmd = self._input.text().strip()
        if not cmd:
            return
        self._input.clear()
        self._history.append(cmd)
        self._history_pos = len(self._history)
        self._execute(cmd)

    def _execute(self, cmd: str) -> None:
        self._output.appendPlainText(f"$ {cmd}")
        self._process.write(f"{cmd}\n".encode())

    def _on_output(self) -> None:
        data = bytes(self._process.readAllStandardOutput())
        text = data.decode("utf-8", errors="replace")
        text = _ANSI_ESCAPE.sub("", text).rstrip()
        if text:
            self._output.appendPlainText(text)
        sb = self._output.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_finished(self, exit_code: int) -> None:
        if self._closing:
            return
        self._output.appendPlainText(
            f"\n[Shell exited with code {exit_code}. Restarting...]"
        )
        self._start_shell()
        if self._cwd:
            self._execute(f"cd {shlex.quote(self._cwd)}")

    def eventFilter(self, obj: object, event: QEvent) -> bool:
        if obj is self._input and event.type() == QEvent.KeyPress:
            key = event.key()
            if key == Qt.Key_Up and self._history:
                self._history_pos = max(0, self._history_pos - 1)
                self._input.setText(self._history[self._history_pos])
                return True
            if key == Qt.Key_Down:
                self._history_pos = min(len(self._history), self._history_pos + 1)
                if self._history_pos < len(self._history):
                    self._input.setText(self._history[self._history_pos])
                else:
                    self._input.clear()
                return True
        return super().eventFilter(obj, event)
