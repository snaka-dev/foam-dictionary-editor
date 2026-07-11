# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import os
import shutil
import subprocess

from PySide6.QtWidgets import QMessageBox

from i18n import tr
from services.case_loader import detect_time_dirs


class _ToolsOpsMixin:
    def _on_restore_0dir_clicked(self) -> None:
        if not self.state.current_case_dir or self.terminal_panel is None:
            return
        case_dir = self.state.current_case_dir
        if not os.path.isdir(os.path.join(case_dir, "0.orig")):
            QMessageBox.warning(
                self,
                tr("No 0.orig/ to restore"),
                tr("This case has no 0.orig/ directory to restore 0/ from."),
            )
            return
        reply = QMessageBox.question(
            self,
            tr("Restore 0/ from 0.orig/?"),
            tr(
                "This will delete 0/ and replace it with a fresh copy of "
                "0.orig/, discarding any edits made directly to 0/. Continue?"
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self.terminal_panel.run_command("rm -rf 0 && cp -r 0.orig 0")
        idx = self.bottom_tabs.indexOf(self.terminal_panel)
        if idx != -1:
            self.bottom_tabs.setCurrentIndex(idx)

    def _on_run_blockmesh_clicked(self) -> None:
        if not self.state.current_case_dir or self.terminal_panel is None:
            return
        case_dir = self.state.current_case_dir
        time_dirs = detect_time_dirs(case_dir)
        if time_dirs:
            reply = QMessageBox.question(
                self,
                tr("Re-run blockMesh?"),
                tr(
                    "This case already has results in: {dirs}.\n"
                    "Re-running blockMesh will regenerate the mesh and may "
                    "invalidate those results. Continue?"
                ).format(dirs=", ".join(time_dirs)),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        self.terminal_panel.run_command("blockMesh 2>&1 | tee log.blockMesh")
        idx = self.bottom_tabs.indexOf(self.terminal_panel)
        if idx != -1:
            self.bottom_tabs.setCurrentIndex(idx)

    def _on_open_paraview_clicked(self) -> None:
        if not self.state.current_case_dir:
            return
        case_dir = self.state.current_case_dir
        launcher = shutil.which("paraFoam")
        if launcher is not None:
            args = [launcher, "-case", case_dir]
        else:
            launcher = shutil.which("paraview")
            if launcher is None:
                QMessageBox.warning(
                    self,
                    tr("ParaView not found"),
                    tr("Neither paraFoam nor paraview could be found on PATH."),
                )
                return
            args = [launcher]
        subprocess.Popen(args, cwd=case_dir, start_new_session=True)

    def _update_tools_actions(self) -> None:
        has_case = self.state.current_case_dir is not None
        has_terminal = self.terminal_panel is not None
        if self._restore_0dir_action is not None:
            self._restore_0dir_action.setEnabled(has_case and has_terminal)
        if self._run_blockmesh_action is not None:
            self._run_blockmesh_action.setEnabled(has_case and has_terminal)
        if self._open_paraview_action is not None:
            self._open_paraview_action.setEnabled(has_case)
