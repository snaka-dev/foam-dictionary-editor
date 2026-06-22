# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path

from PySide6.QtWidgets import QMessageBox

from i18n import tr
from ui.dialogs.foam_monitor_dialog import FoamMonitorDialog


class _FoamMonitorOpsMixin:
    def _on_foam_monitor_clicked(self) -> None:
        if self.state.foam_monitor_proc is not None:
            self._stop_foam_monitor()
            return
        if not self.state.current_case_dir:
            return
        dlg = FoamMonitorDialog(
            self.state.current_case_dir,
            self.state.foam_monitor_last_file,
            self.state.foam_monitor_last_options,
            self,
        )
        if dlg.exec() != FoamMonitorDialog.Accepted:
            return
        file_path = dlg.get_file()
        if not file_path:
            return
        if not os.path.isfile(file_path):
            QMessageBox.warning(
                self,
                tr("File not found"),
                tr("File not found:") + f"\n{file_path}",
            )
            return
        self.state.foam_monitor_last_file = file_path
        self.state.foam_monitor_last_options = dlg.get_options()
        if sys.platform == "win32":
            return
        launcher = self._patched_foam_monitor()
        if launcher is None:
            QMessageBox.warning(
                self,
                tr("foamMonitor not found"),
                tr("foamMonitor could not be found on PATH."),
            )
            return
        self.state.foam_monitor_script_tmp = launcher
        self.state.foam_monitor_proc = subprocess.Popen(
            [launcher] + dlg.get_args() + [file_path],
            cwd=self.state.current_case_dir,
            start_new_session=True,
            stderr=subprocess.PIPE,
        )
        self._foam_monitor_timer.start()
        self._update_foam_monitor_btn()

    def _stop_foam_monitor(self) -> None:
        if self.state.foam_monitor_proc is not None:
            try:
                os.killpg(self.state.foam_monitor_proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            self.state.foam_monitor_proc = None
        self._foam_monitor_timer.stop()
        if self.state.foam_monitor_script_tmp is not None:
            try:
                os.unlink(self.state.foam_monitor_script_tmp)
            except OSError:
                pass
            self.state.foam_monitor_script_tmp = None
        self._update_foam_monitor_btn()

    def _on_foam_monitor_poll(self) -> None:
        proc = self.state.foam_monitor_proc
        if proc is None or proc.poll() is None:
            return
        stderr_text = ""
        if proc.stderr is not None:
            stderr_text = proc.stderr.read().decode("utf-8", errors="replace").strip()
        self.state.foam_monitor_proc = None
        self._foam_monitor_timer.stop()
        if self.state.foam_monitor_script_tmp is not None:
            try:
                os.unlink(self.state.foam_monitor_script_tmp)
            except OSError:
                pass
            self.state.foam_monitor_script_tmp = None
        self._update_foam_monitor_btn()
        if stderr_text:
            QMessageBox.warning(self, tr("foamMonitor error"), stderr_text)

    def _update_foam_monitor_btn(self) -> None:
        if self._foam_monitor_action is None:
            return
        running = self.state.foam_monitor_proc is not None
        self._foam_monitor_action.setText(
            tr("■ foamMonitor") if running else tr("foamMonitor…")
        )
        self._foam_monitor_action.setToolTip(
            tr("Click to stop foamMonitor and close the gnuplot window")
            if running else
            tr("Launch foamMonitor to plot residuals or other data with gnuplot")
        )
        self._foam_monitor_action.setEnabled(running or self.state.current_case_dir is not None)

    @staticmethod
    def _patched_foam_monitor() -> str | None:
        """Return path to a temp copy of foamMonitor with the gnuplot reread fix.

        Newer gnuplot versions deprecate `reread`.  The fix replaces it with
        `load ARG0` and changes the invocation to `gnuplot -e "load '$GPFILE'"`
        so that ARG0 is set to the script path before the loop starts.
        """
        import tempfile

        original = shutil.which("foamMonitor")
        if original is None:
            return None
        try:
            src = Path(original).read_text(encoding="utf-8")
        except OSError:
            return None

        src = src.replace(
            '$GNUPLOT "$GPFILE" &',
            '$GNUPLOT -e "load \'$GPFILE\'" &',
        )
        src = src.replace("\nreread\n", "\nload ARG0\n")

        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".sh", delete=False, encoding="utf-8"
        )
        tmp.write(src)
        tmp.close()
        os.chmod(tmp.name, 0o755)
        return tmp.name
