# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QDialog, QMessageBox

from i18n import tr
from services.case_loader import detect_time_dirs
from services.tool_options import TOOL_SPECS
from ui.dialogs.find_examples_dialog import FindExamplesDialog
from ui.dialogs.log_summary_dialog import LogSummaryDialog
from ui.dialogs.run_tool_dialog import RunToolDialog

if TYPE_CHECKING:
    from ui.mixins._protocol import MainWindowProtocol as _Base
else:
    _Base = object


class _ToolsOpsMixin(_Base):
    # ── shared helpers ────────────────────────────────────────────────────────

    def _run_in_terminal(self, cmd: str) -> None:
        """Send cmd to the terminal panel and bring the terminal tab to front."""
        # Every caller already checked `self.terminal_panel is not None`.
        assert self.terminal_panel is not None
        self.terminal_panel.run_command(cmd)
        idx = self.bottom_tabs.indexOf(self.terminal_panel)
        if idx != -1:
            self.bottom_tabs.setCurrentIndex(idx)

    def _rerun_over_results_warning(self, sentence: str) -> str:
        """Pre-flight warning text for the run dialog when time-dir results exist.

        Returns an empty string when the case has no time-dir results yet.
        """
        # Every caller already checked `self.state.current_case_dir` truthy.
        assert self.state.current_case_dir is not None
        time_dirs = detect_time_dirs(self.state.current_case_dir)
        if not time_dirs:
            return ""
        return (
            tr("This case already has results in: {dirs}.").format(
                dirs=", ".join(time_dirs)
            )
            + "\n"
            + sentence
        )

    def _run_tool_with_options(
        self,
        tool: str,
        warning_text: str = "",
        prefix_option: tuple[str, str, bool] | None = None,
    ) -> None:
        """Show the options dialog for ``tool`` and send the composed command."""
        # Every caller already checked `self.state.current_case_dir` truthy.
        assert self.state.current_case_dir is not None
        dlg = RunToolDialog(
            TOOL_SPECS[tool],
            self.state.current_case_dir,
            self.state.run_tool_options.get(tool),
            warning_text,
            prefix_option,
            self,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        self.state.run_tool_options[tool] = dlg.get_values()
        self._run_in_terminal(dlg.get_command())

    # ── Tools-menu actions ────────────────────────────────────────────────────

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
        if not self._confirm(
            tr("Restore 0/ from 0.orig/?"),
            tr(
                "This will delete 0/ and replace it with a fresh copy of "
                "0.orig/, discarding any edits made directly to 0/. Continue?"
            ),
        ):
            return
        self._run_in_terminal("rm -rf 0 && cp -r 0.orig 0")

    def _on_run_blockmesh_clicked(self) -> None:
        if not self.state.current_case_dir or self.terminal_panel is None:
            return
        self._run_tool_with_options(
            "blockMesh",
            self._rerun_over_results_warning(
                tr(
                    "Re-running blockMesh will regenerate the mesh and may "
                    "invalidate those results."
                )
            ),
        )

    def _on_run_snappyhexmesh_clicked(self) -> None:
        if not self.state.current_case_dir or self.terminal_panel is None:
            return
        self._run_tool_with_options(
            "snappyHexMesh",
            self._rerun_over_results_warning(
                tr(
                    "Re-running snappyHexMesh will regenerate the mesh and may "
                    "invalidate those results."
                )
            ),
        )

    def _on_run_topo_set_clicked(self) -> None:
        if not self.state.current_case_dir or self.terminal_panel is None:
            return
        self._run_tool_with_options(
            "topoSet",
            self._rerun_over_results_warning(
                tr(
                    "Re-running topoSet will regenerate cell/face sets and may "
                    "invalidate those results."
                )
            ),
        )

    def _on_run_setfields_clicked(self) -> None:
        if not self.state.current_case_dir or self.terminal_panel is None:
            return
        warning = tr(
            "setFields modifies the field files in 0/ in place, so re-running "
            "it on already-set fields compounds the values."
        )
        prefix_option: tuple[str, str, bool] | None = None
        if os.path.isdir(os.path.join(self.state.current_case_dir, "0.orig")):
            # Offer the standard remedy: start from a fresh 0/ copy.
            prefix_option = (
                tr("Restore 0/ from 0.orig/ first (start from clean initial fields)"),
                "rm -rf 0 && cp -r 0.orig 0 && ",
                True,
            )
        else:
            warning += "\n" + tr("This case has no 0.orig/ backup to restore from.")
        self._run_tool_with_options("setFields", warning, prefix_option)

    def _on_run_checkmesh_clicked(self) -> None:
        # checkMesh only reads the mesh, so its dialog has no pre-flight warning.
        if not self.state.current_case_dir or self.terminal_panel is None:
            return
        self._run_tool_with_options("checkMesh")

    def _on_run_allrun_clicked(self) -> None:
        if not self.state.current_case_dir or self.terminal_panel is None:
            return
        case_dir = self.state.current_case_dir
        if not os.path.isfile(os.path.join(case_dir, "Allrun")):
            QMessageBox.warning(
                self,
                tr("No Allrun script"),
                tr("This case has no Allrun script to run."),
            )
            return
        logs = sorted(
            name
            for name in os.listdir(case_dir)
            if name.startswith("log.")
            and os.path.isfile(os.path.join(case_dir, name))
        )
        if logs:
            # runApplication/runParallel skip any step whose log.<app> already
            # exists ("already run: remove log file to re-run"), so an Allrun
            # on a case with logs can silently do nothing. Offer the standard
            # remedy (clean first) instead of leaving the user puzzled.
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Question)
            box.setWindowTitle(tr("Case already run?"))
            box.setText(
                tr(
                    "This case already has log files: {logs}.\n"
                    "OpenFOAM's Allrun helpers skip any step whose log.* file "
                    "exists, so those steps will not re-run.\n"
                    "Clean the case first to re-run the whole workflow?"
                ).format(logs=", ".join(logs))
            )
            clean_btn = box.addButton(tr("Clean, then run"), QMessageBox.ButtonRole.YesRole)
            box.addButton(tr("Run anyway"), QMessageBox.ButtonRole.NoRole)
            cancel_btn = box.addButton(QMessageBox.StandardButton.Cancel)
            box.setDefaultButton(cancel_btn)
            box.exec()
            clicked = box.clickedButton()
            if clicked is None or clicked is cancel_btn:
                return
            if clicked is clean_btn:
                cmd = "foamCleanTutorials && ./Allrun"
            else:
                cmd = "./Allrun"
        else:
            if not self._confirm(
                tr("Run Allrun script?"),
                tr(
                    "This runs the case's full workflow, which may include a "
                    "long-running solver. In Simple terminal mode a running "
                    "job cannot be interrupted. Continue?"
                ),
            ):
                return
            cmd = "./Allrun"
        self._run_in_terminal(cmd)

    def _on_run_allclean_clicked(self) -> None:
        if not self.state.current_case_dir or self.terminal_panel is None:
            return
        case_dir = self.state.current_case_dir
        if not os.path.isfile(os.path.join(case_dir, "Allclean")):
            QMessageBox.warning(
                self,
                tr("No Allclean script"),
                tr("This case has no Allclean script to run."),
            )
            return
        if not self._confirm(
            tr("Run Allclean script?"),
            tr(
                "This removes the generated mesh, time directories, log files "
                "and other results from the case. Continue?"
            ),
        ):
            return
        self._run_in_terminal("./Allclean")

    def _on_clean_case_clicked(self) -> None:
        if not self.state.current_case_dir or self.terminal_panel is None:
            return
        case_dir = self.state.current_case_dir
        message = tr(
            "This cleans the case with foamCleanTutorials, removing the "
            "generated mesh, time directories, processor*/ decompositions, "
            "postProcessing/ and log.* files."
        )
        if os.path.isfile(os.path.join(case_dir, "Allwclean")) or os.path.isfile(
            os.path.join(case_dir, "Allclean")
        ):
            message += "\n" + tr(
                "This case has its own Allclean script, which will be run instead."
            )
        elif os.path.isdir(os.path.join(case_dir, "0.orig")):
            message += "\n" + tr(
                "0/ will also be removed because 0.orig/ exists "
                "(use 'Restore 0/ from 0.orig' to recreate it)."
            )
        if not self._confirm(tr("Clean case?"), message + "\n" + tr("Continue?")):
            return
        self._run_in_terminal("foamCleanTutorials")

    def _show_cached_dialog(self, attr: str, factory) -> None:
        """Get-or-create a non-modal dialog cached on ``self.<attr>``.

        Shared by the log-summary and find-examples launchers below: an
        existing instance is re-shown/raised/activated (closing it only
        hides it, since neither dialog sets WA_DeleteOnClose), otherwise
        *factory* builds one, which is cached and torn down via its
        ``destroyed`` signal. See DEVELOPER.md.
        """
        existing = getattr(self, attr)
        if existing is not None:
            existing.show()
            existing.raise_()
            existing.activateWindow()
            return
        dialog = factory()
        dialog.destroyed.connect(lambda: setattr(self, attr, None))
        setattr(self, attr, dialog)
        dialog.show()

    def _on_view_log_summary_clicked(self) -> None:
        if not self.state.current_case_dir:
            return
        self._show_cached_dialog(
            "_log_summary_dialog",
            lambda: LogSummaryDialog(self.state.current_case_dir, parent=self),
        )

    def _on_find_examples_clicked(self) -> None:
        def _make_find_examples_dialog() -> FindExamplesDialog:
            dialog = FindExamplesDialog(parent=self)
            dialog.compare_requested.connect(self._on_example_compare_requested)
            dialog.duplicate_requested.connect(self._on_example_duplicate_requested)
            return dialog

        self._show_cached_dialog("_find_examples_dialog", _make_find_examples_dialog)

    def _on_example_compare_requested(self, case_dir: str) -> None:
        if not self.state.current_case_dir:
            QMessageBox.information(
                self,
                tr("No case open"),
                tr("Open a case first, then compare it with the example case."),
            )
            return
        self._start_comparison_with(case_dir)
        self.raise_()
        self.activateWindow()

    def _on_example_duplicate_requested(self, case_dir: str) -> None:
        # Tutorial cases live inside the OpenFOAM installation, so never
        # offer their (usually read-only) parent as the destination.
        self._duplicate_case_from(case_dir, fallback_dest_parent=str(Path.home()))

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
        terminal_actions = (
            self._restore_0dir_action,
            self._run_blockmesh_action,
            self._run_snappyhexmesh_action,
            self._run_topo_set_action,
            self._run_setfields_action,
            self._run_checkmesh_action,
            self._run_allrun_action,
            self._run_allclean_action,
            self._clean_case_action,
        )
        for action in terminal_actions:
            if action is not None:
                action.setEnabled(has_case and has_terminal)
        for action in (self._open_paraview_action, self._view_log_summary_action):
            if action is not None:
                action.setEnabled(has_case)
