# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QCheckBox, QDialog, QMessageBox

from foam.utils import format_size
from i18n import tr
from services.case_loader import detect_time_dirs
from services.solver_run import (
    COMMON_SOLVERS,
    DeletionCheck,
    DeletionProblem,
    SolverInfo,
    check_processor_deletion,
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
from ui.layout_constants import STATUS_NORMAL
from ui.processor_deletion import run_deletion_with_progress

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
        """
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

    def _on_delete_processor_dirs_clicked(self) -> None:
        if not self.state.current_case_dir:
            return
        case_dir = self.state.current_case_dir
        if self._refuse_while_running(tr("deleting processor* directories")):
            return
        whole = check_processor_deletion(case_dir)
        if not whole.dirs:
            QMessageBox.information(
                self,
                tr("Nothing to delete"),
                tr("This case has no processor* directories."),
            )
            return
        keep = check_processor_deletion(case_dir, keep_latest=True)
        # Keeping the latest time deletes a subset of what deleting everything
        # does, so if even that would lose data, nothing can go.
        blocking = keep.problems if keep.problems else None
        if whole.problems and keep.kept_time is None:
            blocking = whole.problems
        if blocking:
            QMessageBox.warning(
                self,
                tr("processor* directories not deleted"),
                tr("Deleting them would lose data that exists nowhere else:")
                + "\n\n"
                + self._problem_lines(blocking)
                + "\n\n"
                + tr("Nothing was deleted."),
            )
            return
        box, keep_chk = self._processor_delete_box(whole, keep)
        try:
            answer = QMessageBox.StandardButton(box.exec())
            keeping = keep_chk is not None and keep_chk.isChecked()
        finally:
            # Read everything first, then let Qt dispose of the box (and the
            # checkbox it owns); otherwise every confirmation stays behind as a
            # hidden child of the main window.
            box.deleteLater()
        if answer != QMessageBox.StandardButton.Yes:
            return
        chosen = keep if keeping else whole
        if whole.problems:
            # Enforced here, not left to the locked checkbox: deleting
            # everything would lose data, whatever state a widget is in.
            chosen = keep
        result = run_deletion_with_progress(self, case_dir, chosen)
        self._reload_file_list()
        if result.failed:
            self._error(
                tr("Delete processor* directories"),
                tr("Some directories could not be deleted:\n{errors}").format(
                    errors="\n".join(result.failed)
                ),
            )
        elif result.stopped:
            QMessageBox.information(
                self,
                tr("Deletion stopped"),
                tr(
                    "Stopped after {done} of {total} directories. Everything "
                    "deleted so far also exists at the case root, and nothing "
                    "else was changed; run the action again to finish."
                ).format(done=result.done, total=result.total),
            )
        elif chosen.keep_latest:
            self.statusBar().showMessage(
                tr("Deleted the processor* time directories except {t} ({size}).").format(
                    t=chosen.kept_time, size=format_size(chosen.total_bytes)
                ),
                STATUS_NORMAL,
            )
        else:
            self.statusBar().showMessage(
                tr("Deleted {n} processor* directories ({size}).").format(
                    n=len(chosen.dirs), size=format_size(chosen.total_bytes)
                ),
                STATUS_NORMAL,
            )

    def _problem_lines(self, problems) -> str:
        lines = [self._describe_deletion_problem(p) for p in problems]
        if len(lines) > 12:
            lines = lines[:12] + [tr("… and {n} more.").format(n=len(lines) - 12)]
        return "\n".join("• " + line for line in lines)

    def _processor_delete_box(
        self, whole: DeletionCheck, keep: DeletionCheck
    ) -> tuple[QMessageBox, QCheckBox | None]:
        """The confirmation, and its "keep the latest time" checkbox if offered.

        The text describes what will happen with the checkbox as it stands --
        one action, one size -- and is rewritten whenever it is toggled. An
        earlier version listed both choices' sizes up front ("Keeping it
        frees …"), which read as a contradiction and pointed at a checkbox
        the reader had not reached yet.

        The checkbox starts ticked -- it deletes less, and spares a serial,
        memory-hungry decomposePar on exactly the cases where processor* is
        large -- except when the case root is already ahead of the processors,
        where the kept time would be an older restart point than the case.
        When deleting everything would lose data but keeping the latest time
        would not (the mesh exists only in processor*, say), it is ticked and
        locked, with the reason shown.
        """
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle(tr("Delete processor* directories?"))
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        assurance = tr(
            "Everything that will be deleted also exists at the case root, "
            "checked file by file. This cannot be undone."
        )
        if keep.kept_time is None:
            box.setText(
                tr("Permanently delete the processor* directories entirely ({size})?").format(
                    size=format_size(whole.total_bytes)
                )
                + "\n\n"
                + tr("Continuing this run in parallel later will need decomposePar again.")
                + "\n\n"
                + assurance
            )
            return box, None

        t = keep.kept_time
        # Parented to the box at construction, not merely handed to
        # setCheckBox: PySide6's setCheckBox does not transfer ownership, so a
        # parentless QCheckBox stays owned by Python while Qt treats it as the
        # box's child -- two owners, and the garbage collector later destroys a
        # checkbox C++ has already freed (a SIGBUS crash, reproduced and
        # pinned by tests/ui/test_tools_busy_terminal.py).
        keep_chk = QCheckBox(
            tr("Keep the latest time ({t}) and the decomposed mesh").format(t=t), box
        )
        box.setCheckBox(keep_chk)
        note = ""
        if whole.problems:
            keep_chk.setChecked(True)
            keep_chk.setEnabled(False)
            note = (
                tr("Deleting everything would lose data that exists nowhere else:")
                + "\n"
                + self._problem_lines(whole.problems)
            )
        elif keep.latest_root_time is not None and float(keep.latest_root_time) > float(t):
            keep_chk.setChecked(False)
            note = tr(
                "The case root has a later time ({root}) than the processors "
                "({t}), so keeping {t} would leave a restart point older than "
                "the case."
            ).format(root=keep.latest_root_time, t=t)
        else:
            keep_chk.setChecked(True)

        def describe(keeping: bool) -> None:
            if keeping:
                parts = [
                    tr("Permanently delete {size} from the processor* directories?").format(
                        size=format_size(keep.total_bytes)
                    ),
                    tr(
                        "Kept: the latest time ({t}) and the decomposed mesh, so the "
                        "run can continue in parallel without decomposePar."
                    ).format(t=t),
                ]
            else:
                parts = [
                    tr("Permanently delete the processor* directories entirely ({size})?").format(
                        size=format_size(whole.total_bytes)
                    ),
                    tr("Continuing this run in parallel later will need decomposePar again."),
                ]
            if note:
                parts.append(note)
            parts.append(assurance)
            box.setText("\n\n".join(parts))

        describe(keep_chk.isChecked())
        keep_chk.toggled.connect(describe)
        return box, keep_chk

    @staticmethod
    def _describe_deletion_problem(problem: DeletionProblem) -> str:
        if problem.kind == "collated":
            return tr(
                "the data is in collated format (processorsN), which FoDE "
                "cannot check — delete it by hand if you are sure"
            )
        if problem.kind == "time_missing":
            return tr("time {t} exists only in processor*").format(t=problem.time)
        if problem.kind == "files_missing":
            shown = ", ".join(problem.detail[:5])
            if len(problem.detail) > 5:
                shown += ", …"
            return tr("time {t}: {files} exist only in processor*").format(
                t=problem.time, files=shown
            )
        if problem.kind == "mesh_missing":
            return tr(
                "the mesh exists only in processor* — run reconstructParMesh first"
            )
        if problem.kind == "mesh_differs":
            root, procs = problem.detail
            return tr(
                "the case-root mesh has {root} cells but the processors have "
                "{procs} — run reconstructParMesh first"
            ).format(root=root, procs=procs)
        if problem.kind == "sets_missing":
            return tr("sets {sets} exist only in processor*").format(
                sets=", ".join(problem.detail)
            )
        return tr("the meshes' cell counts could not be read, so they cannot be compared")

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
        # The editor's text, so an unsaved edit to `application` is what the
        # dialog pre-fills.
        text = self._current_text(os.path.join(case_dir, "system", "controlDict"))
        info = read_solver_info(text) if text is not None else None
        current = info.application if info is not None and info.application else ""
        note, warnings = self._solver_dialog_notes(case_dir, info)

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
        ):
            if action is not None:
                action.setEnabled(has_case)
