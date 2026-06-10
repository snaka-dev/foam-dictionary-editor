# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import os
import shlex
import signal
import struct
import sys
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

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
