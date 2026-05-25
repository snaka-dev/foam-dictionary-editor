# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import os
import re
import shlex
import signal
import struct
import sys
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QProcess, Qt, Signal, Slot
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

_ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

# ── optional imports for xterm.js / WebEngine terminal ───────────────────────
_XTERM_AVAILABLE = False
if sys.platform != "win32":
    try:
        import fcntl
        import pty
        import termios

        from PySide6.QtCore import QSocketNotifier, QUrl
        from PySide6.QtWebChannel import QWebChannel
        from PySide6.QtWebEngineWidgets import QWebEngineView

        _XTERM_AVAILABLE = True
    except ImportError:
        pass

_XTERM_VERSION = "6.0.0"
_LOCAL_CSS = '<link rel="stylesheet" href="xterm/xterm.css">'
_LOCAL_JS = (
    '<script src="xterm/xterm.js"></script>\n'
    '<script src="xterm/xterm-addon-fit.js"></script>'
)

# ── PTY backend (Unix only) ───────────────────────────────────────────────────

if _XTERM_AVAILABLE:

    class PtyBackend(QObject):
        data_ready = Signal(str)
        stopped = Signal()

        def __init__(self, parent: QObject | None = None) -> None:
            super().__init__(parent)
            self._master_fd: int | None = None
            self._pid: int | None = None
            self._notifier: "QSocketNotifier | None" = None

        @property
        def is_running(self) -> bool:
            return self._pid is not None

        def start_shell(self, cwd: str | None = None) -> None:
            master_fd, slave_fd = pty.openpty()
            self._master_fd = master_fd

            pid = os.fork()
            if pid == 0:
                os.close(master_fd)
                os.setsid()
                fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
                for fd in (0, 1, 2):
                    os.dup2(slave_fd, fd)
                if slave_fd > 2:
                    os.close(slave_fd)
                env = os.environ.copy()
                env["TERM"] = "xterm-256color"
                if cwd:
                    try:
                        os.chdir(cwd)
                    except OSError:
                        pass
                shell = env.get("SHELL", "/bin/bash")
                try:
                    os.execvpe(shell, [shell], env)
                except OSError:
                    pass
                os._exit(1)
            else:
                os.close(slave_fd)
                self._pid = pid
                self._notifier = QSocketNotifier(
                    master_fd, QSocketNotifier.Type.Read, self
                )
                self._notifier.activated.connect(self._on_readable)

        def write(self, data: bytes) -> None:
            if self._master_fd is not None:
                try:
                    os.write(self._master_fd, data)
                except OSError:
                    pass

        def resize(self, cols: int, rows: int) -> None:
            if self._master_fd is not None:
                try:
                    winsize = struct.pack("HHHH", rows, cols, 0, 0)
                    fcntl.ioctl(self._master_fd, termios.TIOCSWINSZ, winsize)
                except OSError:
                    pass

        def stop(self) -> None:
            self._cleanup()

        def _on_readable(self) -> None:
            try:
                data = os.read(self._master_fd, 4096)
                if data:
                    self.data_ready.emit(data.decode("utf-8", errors="replace"))
                else:
                    self._cleanup()
                    self.stopped.emit()
            except OSError:
                self._cleanup()
                self.stopped.emit()

        def _cleanup(self) -> None:
            if self._notifier:
                self._notifier.setEnabled(False)
                self._notifier = None
            if self._pid is not None:
                try:
                    os.kill(self._pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    os.waitpid(self._pid, os.WNOHANG)
                except ChildProcessError:
                    pass
                self._pid = None
            if self._master_fd is not None:
                try:
                    os.close(self._master_fd)
                except OSError:
                    pass
                self._master_fd = None


# ── QWebChannel bridge ────────────────────────────────────────────────────────

if _XTERM_AVAILABLE:

    class TerminalBridge(QObject):
        send_to_terminal = Signal(str)

        def __init__(
            self, backend: "PtyBackend", parent: QObject | None = None
        ) -> None:
            super().__init__(parent)
            self._backend = backend
            self._pending_cwd: str | None = None
            backend.data_ready.connect(self.send_to_terminal)

        def set_pending_cwd(self, path: str) -> None:
            self._pending_cwd = path

        @Slot()
        def terminal_ready(self) -> None:
            self._backend.start_shell(self._pending_cwd)
            self._pending_cwd = None

        @Slot(str)
        def on_input(self, text: str) -> None:
            self._backend.write(text.encode("utf-8"))

        @Slot(int, int)
        def on_resize(self, cols: int, rows: int) -> None:
            self._backend.resize(cols, rows)


# ── xterm.js terminal widget ──────────────────────────────────────────────────

if _XTERM_AVAILABLE:

    class XtermTerminalWidget(QWidget):
        def __init__(self, parent: QWidget | None = None) -> None:
            super().__init__(parent)

            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)

            self._backend = PtyBackend(self)
            self._bridge = TerminalBridge(self._backend, self)
            self._backend.stopped.connect(self._on_shell_stopped)

            self._channel = QWebChannel(self)
            self._channel.registerObject("bridge", self._bridge)

            self._view = QWebEngineView(self)
            self._view.page().setWebChannel(self._channel)
            layout.addWidget(self._view)

            self._load_terminal()

            app = QApplication.instance()
            if app is not None:
                app.aboutToQuit.connect(self._backend.stop)

        def set_working_directory(self, path: str) -> None:
            if self._backend.is_running:
                self._backend.write(f"cd {shlex.quote(path)}\n".encode())
            else:
                self._bridge.set_pending_cwd(path)

        def _load_terminal(self) -> None:
            ui_dir = Path(__file__).parent
            xterm_dir = ui_dir / "xterm"

            version_file = xterm_dir / "version.txt"
            needs_download = (
                not (xterm_dir / "xterm.js").exists()
                or not version_file.exists()
                or version_file.read_text(encoding="utf-8").strip() != _XTERM_VERSION
            )
            if needs_download:
                self._download_xterm_files(xterm_dir)

            if (xterm_dir / "xterm.js").exists():
                css_tag, js_tags = _LOCAL_CSS, _LOCAL_JS
            else:
                self._view.setHtml(
                    "<body style='background:#1e1e1e;color:#d4d4d4;font-family:monospace'>"
                    "<p>Terminal unavailable: could not download xterm.js.<br>"
                    "Place xterm.js, xterm.css, and xterm-addon-fit.js in ui/xterm/.</p></body>"
                )
                return

            template = (ui_dir / "xterm_terminal.html").read_text(encoding="utf-8")
            html = template.replace("<!--XTERM_CSS-->", css_tag).replace(
                "<!--XTERM_JS-->", js_tags
            )
            base_url = QUrl.fromLocalFile(str(ui_dir) + "/")
            self._view.setHtml(html, base_url)

        @staticmethod
        def _download_xterm_files(xterm_dir: Path) -> None:
            import shutil
            import tempfile
            import urllib.request

            downloads = [
                (
                    "xterm.js",
                    "https://cdn.jsdelivr.net/npm/@xterm/xterm@6.0.0/lib/xterm.js",
                ),
                (
                    "xterm.css",
                    "https://cdn.jsdelivr.net/npm/@xterm/xterm@6.0.0/css/xterm.css",
                ),
                (
                    "xterm-addon-fit.js",
                    "https://cdn.jsdelivr.net/npm/@xterm/addon-fit@0.11.0/lib/addon-fit.js",
                ),
            ]
            tmp_dir = Path(tempfile.mkdtemp())
            try:
                for name, url in downloads:
                    urllib.request.urlretrieve(url, tmp_dir / name)
            except Exception:
                shutil.rmtree(tmp_dir, ignore_errors=True)
                return
            shutil.rmtree(xterm_dir, ignore_errors=True)
            shutil.move(str(tmp_dir), str(xterm_dir))
            (xterm_dir / "version.txt").write_text(_XTERM_VERSION, encoding="utf-8")

        def cleanup(self) -> None:
            self._backend.stop()

        def _on_shell_stopped(self) -> None:
            self._bridge.send_to_terminal.emit(
                "\r\n\x1b[33m[Shell process ended.]\x1b[0m\r\n"
            )


# ── SimpleTerminalWidget (QProcess-based, no WebEngine) ───────────────────────

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


# ── TerminalPanel ─────────────────────────────────────────────────────────────

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
        from PySide6.QtCore import QTimer
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
