# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import hashlib
import os
import shlex
import signal
import struct
import sys
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from ui.fonts import css_pixel_size

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

# (local name, URL, SHA-256). The page these scripts run in has a QWebChannel bridge
# that writes straight to the shell, so whoever controls this JavaScript controls the
# user's account: a download is installed only if every file matches, and files already
# on disk are checked again before each load. The hashes were taken from the npm
# registry tarballs (verified against the registry's own sha512 integrity) and match
# what jsDelivr serves. Changing a version means updating its hash in the same commit.
_XTERM_FILES: tuple[tuple[str, str, str], ...] = (
    (
        "xterm.js",
        "https://cdn.jsdelivr.net/npm/@xterm/xterm@6.0.0/lib/xterm.js",
        "14903579ff54664cd72f8e8699e6961a6272c21863ec1c3b118cdc8af5d4a972",
    ),
    (
        "xterm.css",
        "https://cdn.jsdelivr.net/npm/@xterm/xterm@6.0.0/css/xterm.css",
        "854a7c0fb70e8b1a083c16797ab827299fb18744f5ad34f227b48337e33293c6",
    ),
    (
        "xterm-addon-fit.js",
        "https://cdn.jsdelivr.net/npm/@xterm/addon-fit@0.11.0/lib/addon-fit.js",
        "ba3ea256ce0620a0992a197d6c9baea64823fc93d8da07a9e366ca9943c18527",
    ),
)


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def xterm_files_valid(xterm_dir: Path) -> bool:
    """True when every xterm file in *xterm_dir* is present and has its pinned hash."""
    return all(_sha256(xterm_dir / name) == digest for name, _url, digest in _XTERM_FILES)


def download_xterm_files(
    xterm_dir: Path,
    fetch: Callable[[str, Path], object] | None = None,
) -> bool:
    """Download the xterm files into *xterm_dir*; True if a verified set is installed.

    Everything goes to a temporary directory first and replaces *xterm_dir* only when
    every file matches its pinned hash, so a failed or tampered download leaves no
    file behind that the page could load. *fetch(url, dest)* defaults to
    ``urllib.request.urlretrieve`` and is a parameter for the tests.
    """
    import shutil
    import tempfile
    import urllib.request

    if fetch is None:
        fetch = urllib.request.urlretrieve
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        for name, url, _digest in _XTERM_FILES:
            fetch(url, tmp_dir / name)
    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return False
    if not xterm_files_valid(tmp_dir):
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return False
    shutil.rmtree(xterm_dir, ignore_errors=True)
    shutil.move(str(tmp_dir), str(xterm_dir))
    (xterm_dir / "version.txt").write_text(_XTERM_VERSION, encoding="utf-8")
    return True

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
            self._notifier: QSocketNotifier | None = None

        @property
        def is_running(self) -> bool:
            return self._pid is not None

        @property
        def pid(self) -> int | None:
            """The shell's process id, while it runs."""
            return self._pid

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
            if self._master_fd is None:
                return
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
            self, backend: PtyBackend, parent: QObject | None = None
        ) -> None:
            super().__init__(parent)
            self._backend = backend
            self._pending_cwd: str | None = None
            self._pending_cmd: str | None = None
            backend.data_ready.connect(self.send_to_terminal)

        def set_pending_cwd(self, path: str) -> None:
            self._pending_cwd = path

        def set_pending_cmd(self, cmd: str) -> None:
            self._pending_cmd = cmd

        @Slot()
        def terminal_ready(self) -> None:
            self._backend.start_shell(self._pending_cwd)
            self._pending_cwd = None
            if self._pending_cmd:
                self._backend.write(f"{self._pending_cmd}\n".encode())
                self._pending_cmd = None

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

        def shell_pid(self) -> int | None:
            """The shell's process id, for TerminalPanel.running_commands."""
            return self._backend.pid

        def run_command(self, cmd: str) -> None:
            if self._backend.is_running:
                self._backend.write(f"{cmd}\n".encode())
            else:
                self._bridge.set_pending_cmd(cmd)

        def _load_terminal(self) -> None:
            ui_dir = Path(__file__).parent.parent
            xterm_dir = ui_dir / "xterm"

            # The hash check covers a stale version, a partial copy and a file
            # changed after it was downloaded, all of which earn a fresh download.
            if not xterm_files_valid(xterm_dir):
                download_xterm_files(xterm_dir)

            if xterm_files_valid(xterm_dir):
                css_tag, js_tags = _LOCAL_CSS, _LOCAL_JS
            else:
                self._view.setHtml(
                    "<body style='background:#1e1e1e;color:#d4d4d4;font-family:monospace'>"
                    "<p>Terminal unavailable: could not download a verified copy of "
                    "xterm.js.<br>Check the network connection, or use Simple mode.</p></body>"
                )
                return

            template = (ui_dir / "xterm_terminal.html").read_text(encoding="utf-8")
            # xterm.js sizes its font in CSS pixels, so the application font's
            # point size is converted rather than passed through.
            font_tag = f"<script>window.fodeFontSize = {css_pixel_size()};</script>"
            html = (
                template.replace("<!--XTERM_CSS-->", css_tag)
                .replace("<!--XTERM_JS-->", js_tags)
                .replace("<!--XTERM_FONT_SIZE-->", font_tag)
            )
            base_url = QUrl.fromLocalFile(str(ui_dir) + "/")
            self._view.setHtml(html, base_url)

        def cleanup(self) -> None:
            self._backend.stop()

        def _on_shell_stopped(self) -> None:
            self._bridge.send_to_terminal.emit(
                "\r\n\x1b[33m[Shell process ended.]\x1b[0m\r\n"
            )
