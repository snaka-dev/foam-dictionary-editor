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
from services.background_run import (
    STOPPING_VALUES,
    active_run,
    background_command,
    background_supported,
    read_stop_at,
)
from services.case_loader import detect_time_dirs
from services.solver_run import (
    COMMON_SOLVERS,
    SolverInfo,
    decomposed_count,
    has_mesh,
    processor_dirs,
    read_solver_info,
    read_subdomain_count,
    stale_decomposition,
    unreconstructed_times,
)
from services.tool_options import TOOL_SPECS
from ui.dialogs.find_examples_dialog import FindExamplesDialog
from ui.dialogs.log_summary_dialog import LogSummaryDialog
from ui.dialogs.run_solver_dialog import ExecutableChoice, RunSolverDialog
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
        values: dict | None = None,
    ) -> None:
        """Show the options dialog for ``tool`` and send the composed command.

        ``values`` overrides the remembered starting values when given.
        """
        # Every caller already checked `self.state.current_case_dir` truthy.
        assert self.state.current_case_dir is not None
        if self._refuse_while_running(tr("running another command")):
            return
        if values is None:
            values = self.state.run_tool_options.get(tool)
        dlg = RunToolDialog(
            TOOL_SPECS[tool],
            self.state.current_case_dir,
            values,
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
        if self._refuse_while_running(tr("running another command")):
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

    def _on_run_decomposepar_clicked(self) -> None:
        if not self.state.current_case_dir or self.terminal_panel is None:
            return
        case_dir = self.state.current_case_dir
        if not os.path.isfile(os.path.join(case_dir, "system", "decomposeParDict")):
            QMessageBox.warning(
                self,
                tr("No decomposeParDict"),
                tr(
                    "This case has no system/decomposeParDict, which "
                    "decomposePar needs to split the case."
                ),
            )
            return
        last = dict(self.state.run_tool_options.get("decomposePar") or {})
        warning = ""
        existing = processor_dirs(case_dir)
        unreconstructed = unreconstructed_times(case_dir)
        if unreconstructed:
            # -force would delete parallel-run results that exist nowhere
            # else. Never pre-tick it here: a decomposePar that refuses to
            # run is the safe failure.
            warning = tr(
                "The processor* directories hold results that have not been "
                "reconstructed: {times}. -force deletes them for good — run "
                "Tools > Run reconstructPar… first to keep them."
            ).format(times=", ".join(unreconstructed))
            last["-force"] = False
        elif existing:
            warning = tr(
                "This case is already decomposed ({dirs}). decomposePar "
                "refuses to overwrite them unless -force is given."
            ).format(dirs=", ".join(existing))
            # Without -force the run would only fail, so start ticked.
            last["-force"] = True
        self._run_tool_with_options("decomposePar", warning, values=last)

    def _refuse_while_running(self, what: str) -> bool:
        """Refuse *what* while the Terminal tab is busy; True if refused.

        A command sent now would only queue behind the running one -- or, in
        the xterm terminal, be typed into it (mpirun reads its input) -- and
        anything that reads the case meanwhile sees a time step half written.
        A background run in this case refuses the same way, even after FoDE
        was restarted: it writes the case just the same, only out of sight.
        """
        run = active_run(self.state.current_case_dir) if self.state.current_case_dir else None
        if run is not None:
            QMessageBox.warning(
                self,
                tr("Background run in progress"),
                tr(
                    "{name} is running in the background in this case (pid "
                    "{pid}). Wait for it to finish before {what}, or stop it "
                    "with Tools > Stop Background Run."
                ).format(name=run.label, pid=run.pid, what=what),
            )
            return True
        names = self.terminal_panel.running_commands() if self.terminal_panel else []
        if not names:
            return False
        QMessageBox.warning(
            self,
            tr("Command still running"),
            tr("{names} is still running in the Terminal tab. Wait for it to "
               "finish before {what}.").format(names=", ".join(names), what=what),
        )
        return True

    def _on_run_reconstructpar_clicked(self) -> None:
        if not self.state.current_case_dir or self.terminal_panel is None:
            return
        case_dir = self.state.current_case_dir
        if not processor_dirs(case_dir):
            QMessageBox.warning(
                self,
                tr("Case not decomposed"),
                tr("This case has no processor* directories to reconstruct from."),
            )
            return
        if self._refuse_while_running(tr("reconstructing the case")):
            return
        pending = unreconstructed_times(case_dir)
        if pending:
            warning = tr("Not yet at the case root: {times}.").format(
                times=", ".join(pending)
            )
        else:
            warning = tr(
                "Every time in processor* is already at the case root, so with "
                "-newTimes there is nothing new to reconstruct."
            )
        self._run_tool_with_options("reconstructPar", warning)

    def _solver_dialog_notes(
        self, case_dir: str, info: SolverInfo | None
    ) -> tuple[str, list[str]]:
        """The note under the solver field, and the pre-flight warnings.

        ``info`` is None when the case has no controlDict.
        """
        if info is None:
            note = tr("system/controlDict not found — type the solver name.")
        elif info.application is None:
            note = tr(
                "controlDict has no application entry — type the solver name."
            )
        elif info.module is not None:
            note = tr(
                "From system/controlDict: application {app}, solver module "
                "{module} (foamRun reads it from controlDict itself)."
            ).format(app=info.application, module=info.module)
        elif info.region_modules:
            note = tr(
                "From system/controlDict: application {app}, region solvers "
                "{regions}."
            ).format(
                app=info.application,
                regions=", ".join(f"{r}: {m}" for r, m in info.region_modules),
            )
        else:
            note = tr("From system/controlDict: application {app}.").format(
                app=info.application
            )

        warnings: list[str] = []
        if not has_mesh(case_dir):
            warnings.append(
                tr(
                    "No mesh found (constant/polyMesh) — run blockMesh or "
                    "snappyHexMesh first."
                )
            )
        time_dirs = [d for d in detect_time_dirs(case_dir) if d != "0"]
        if time_dirs:
            start_from = info.start_from if info is not None else None
            if start_from == "latestTime":
                detail = tr(
                    "startFrom is latestTime, so the run continues from {t}."
                ).format(t=time_dirs[-1])
            elif start_from is not None:
                detail = tr(
                    "startFrom is {mode}, so existing results may be "
                    "overwritten."
                ).format(mode=start_from)
            else:
                detail = tr("Existing results may be overwritten.")
            warnings.append(
                tr("This case already has results in: {dirs}.").format(
                    dirs=", ".join(time_dirs)
                )
                + " "
                + detail
            )
        return note, warnings

    def _parallel_setup(
        self, case_dir: str, unsaved: bool
    ) -> tuple[int | None, bool, list[str]]:
        """``-np`` for the parallel checkbox, its default, and its warnings.

        A parallel run starts only when the processor count, the processor
        directories and decomposeParDict's numberOfSubdomains all agree, and
        it reads processor*/ rather than the case root -- each mismatch below
        is a run that fails at startup or, worse, silently ignores an edit.
        """
        warnings: list[str] = []
        count = decomposed_count(case_dir)
        dpd = self._current_text(os.path.join(case_dir, "system", "decomposeParDict"))
        wanted = read_subdomain_count(dpd) if dpd is not None else None
        if count is None:
            if wanted is not None:
                warnings.append(
                    tr(
                        "Parallel runs need a decomposed case — run "
                        "Tools > Run decomposePar… first."
                    )
                )
            return wanted, False, warnings
        default = True
        if wanted is not None and wanted != count:
            warnings.append(
                tr(
                    "decomposeParDict asks for {wanted} subdomains but the case "
                    "is decomposed into {count}, so a parallel run would stop "
                    "at startup — re-run decomposePar."
                ).format(wanted=wanted, count=count)
            )
            default = False
        stale = stale_decomposition(case_dir, self._dirty_paths() if unsaved else ())
        if stale:
            warnings.append(
                tr(
                    "{dirs} changed after the case was decomposed. A parallel "
                    "run reads processor*/, not these, so it would not see the "
                    "changes — re-run decomposePar first."
                ).format(dirs=", ".join(d + "/" for d in stale))
            )
            default = False
        return count, default, warnings

    def _on_run_solver_clicked(self) -> None:
        if not self.state.current_case_dir or self.terminal_panel is None:
            return
        if self._refuse_while_running(tr("running another command")):
            return
        case_dir = self.state.current_case_dir
        self._poll_background_run()
        # The editor's text, so an unsaved edit to `application` is what the
        # dialog pre-fills.
        text = self._current_text(os.path.join(case_dir, "system", "controlDict"))
        info = read_solver_info(text) if text is not None else None
        current = info.application if info is not None and info.application else ""
        note, warnings = self._solver_dialog_notes(case_dir, info)
        stop_at = read_stop_at(text) if text is not None else None
        if stop_at in STOPPING_VALUES:
            warnings.append(
                tr(
                    "controlDict has stopAt {value}, so the solver will stop "
                    "right after it starts — set it back (usually endTime) first."
                ).format(value=stop_at)
            )

        unsaved = bool(self._dirty_paths())
        parallel_np, parallel_default, parallel_warnings = self._parallel_setup(
            case_dir, unsaved
        )
        warnings += parallel_warnings

        dlg = RunSolverDialog(
            case_dir,
            ExecutableChoice(tr("Solver:"), current, COMMON_SOLVERS, note),
            self.state.run_tool_options.get("solver"),
            "\n".join(warnings),
            self,
            parallel_np=parallel_np,
            parallel_default=parallel_default,
            save_first_label=(
                tr("Save all unsaved files first (the solver reads them from disk)")
                if unsaved
                else ""
            ),
            background_available=background_supported(),
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        # Options only: the solver name is re-read from controlDict every
        # time, so a one-off override never silently sticks to later runs.
        self.state.run_tool_options["solver"] = dlg.get_values()
        if dlg.save_first():
            self.save_all_files()
            if self._dirty_paths():
                QMessageBox.warning(
                    self,
                    tr("Solver not started"),
                    tr(
                        "Some files could not be saved, so the solver was not "
                        "started."
                    ),
                )
                return
        self._run_in_terminal(dlg.get_command())
        if dlg.runs_in_background():
            self._background_cases.add(case_dir)
            self._background_run_timer.start()

    def _on_run_allrun_clicked(self) -> None:
        if not self.state.current_case_dir or self.terminal_panel is None:
            return
        if self._refuse_while_running(tr("running another command")):
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
            background = self._background_checkbox(box)
            try:
                box.exec()
                clicked = box.clickedButton()
                detach = background is not None and background.isChecked()
            finally:
                box.deleteLater()
            if clicked is None or clicked is cancel_btn:
                return
            prefix = "foamCleanTutorials && " if clicked is clean_btn else ""
        else:
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Question)
            box.setWindowTitle(tr("Run Allrun script?"))
            box.setText(
                tr(
                    "This runs the case's full workflow, which may include a "
                    "long-running solver. In Simple terminal mode a running "
                    "job cannot be interrupted. Continue?"
                )
            )
            box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            box.setDefaultButton(QMessageBox.StandardButton.No)
            background = self._background_checkbox(box)
            try:
                answer = QMessageBox.StandardButton(box.exec())
                detach = background is not None and background.isChecked()
            finally:
                box.deleteLater()
            if answer != QMessageBox.StandardButton.Yes:
                return
            prefix = ""
        if detach:
            cmd = background_command(["./Allrun"], "log.Allrun", "Allrun", prefix)
        else:
            cmd = f"{prefix}./Allrun"
        self._run_in_terminal(cmd)
        if detach:
            self._background_cases.add(case_dir)
            self._background_run_timer.start()

    def _reload_clean_file_from_disk(self, path: str) -> None:
        """Drop FoDE's copy of *path*, unless edited, so it is read afresh."""
        if path not in self.state.file_buffers or self.state.file_dirty.get(path):
            return
        was_current = path == self.state.current_file
        if was_current:
            self._clear_current_file()
        self._purge_file_caches(path)
        if was_current:
            self.load_selected_file(path)

    def _on_run_allclean_clicked(self) -> None:
        if not self.state.current_case_dir or self.terminal_panel is None:
            return
        if self._refuse_while_running(tr("running another command")):
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
        if self._refuse_while_running(tr("running another command")):
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
            self._run_decomposepar_action,
            self._run_solver_action,
            self._run_post_process_action,
            self._run_reconstructpar_action,
            self._run_allrun_action,
            self._run_allclean_action,
            self._clean_case_action,
        )
        for action in terminal_actions:
            if action is not None:
                action.setEnabled(has_case and has_terminal)
        for action in (
            self._open_paraview_action,
            self._view_log_summary_action,
            self._delete_processor_dirs_action,
            self._stop_background_run_action,
            self._add_function_object_action,
        ):
            if action is not None:
                action.setEnabled(has_case)
