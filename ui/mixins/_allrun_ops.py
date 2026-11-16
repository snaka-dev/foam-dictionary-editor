# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tools > Allrun Steps… and Tools > Create Allrun from Logs….

Allrun Steps shows the case's Allrun as steps and runs them one at a time.
Reading the script and judging each step is Qt-free (services/allrun.py);
this mixin supplies the unsaved buffers, sends a step to the terminal with the
same confirmation every other run gets, runs Check Case before a solver step,
and opens a step's log in View Log Summary.

Create Allrun from Logs writes an Allrun (and Allclean) for a case without
one, from the steps services/allrun_create.py proposes and the user reviews;
it never replaces an existing script.
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMessageBox

from i18n import tr
from services import allrun as ar
from services import allrun_create as ac
from services.case_check import installation_info
from services.solver_run import MODULE_RUNNERS, read_solver_info
from ui.case_check_text import finding_location, finding_message
from ui.dialogs.allrun_steps_dialog import AllrunStepsDialog
from ui.dialogs.create_allrun_dialog import CreateAllrunDialog
from ui.mixins._function_object_ops import _installation

if TYPE_CHECKING:
    from ui.mixins._protocol import MainWindowProtocol as _Base
else:
    _Base = object

# How many Check Case errors the run confirmation lists.
_MAX_FINDINGS = 4


class _AllrunOpsMixin(_Base):
    def _read_allrun_plan(self, case_dir: str, script: str | None = None) -> ar.AllrunPlan | None:
        return ar.read_allrun(
            case_dir, read_text=lambda path: self._current_text(path, fallback=False),
            script=script,
        )

    def _on_allrun_steps_clicked(self) -> None:
        if not self.state.current_case_dir:
            return

        def _make() -> AllrunStepsDialog:
            dialog = AllrunStepsDialog(parent=self)
            dialog.run_requested.connect(self._on_allrun_run_requested)
            dialog.log_requested.connect(self._on_allrun_log_requested)
            dialog.refresh_requested.connect(self._refresh_allrun_steps)
            dialog.create_requested.connect(self._on_create_allrun_clicked)
            dialog.script_changed.connect(lambda name: self._refresh_allrun_steps(name))
            return dialog

        self._show_cached_dialog("_allrun_steps_dialog", _make)
        self._refresh_allrun_steps()

    def _refresh_allrun_steps(self, script: str | None = None) -> None:
        """Re-read the script into the open window, or hide it with no case.

        *script* picks Allrun or Allrun-parallel; by default the one shown
        stays, while this case has it.
        """
        dialog = self._allrun_steps_dialog
        if dialog is None:
            return
        case_dir = self.state.current_case_dir
        if not case_dir:
            dialog.hide()
            return
        if script is None and dialog.case_dir == case_dir:
            script = dialog.chosen_script()
        dialog.set_plan(
            case_dir, self._read_allrun_plan(case_dir, script),
            can_run=self.terminal_panel is not None,
            scripts=ar.available_scripts(case_dir),
        )

    def _on_allrun_run_requested(self, index: int, onwards: bool) -> None:
        dialog = self._allrun_steps_dialog
        case_dir = self.state.current_case_dir
        if dialog is None or dialog.plan is None or not case_dir or self.terminal_panel is None:
            return
        if self._refuse_while_running(tr("running an Allrun step")):
            return
        plan = dialog.plan
        if not 0 <= index < len(plan.steps):
            return
        step = plan.steps[index]
        if onwards:
            command = ar.run_from_command(case_dir, plan, index)
            covered = list(plan.steps[index:])
        else:
            command = ar.step_command(case_dir, step) if step.kind != ar.OTHER and step.app else None
            covered = [step]
        if command is None:
            return
        if not self._confirm_allrun_command(case_dir, command, covered, onwards):
            return
        self._run_in_terminal(command)
        dialog.refresh_states()

    def _confirm_allrun_command(
        self, case_dir: str, command: str, covered: list[ar.Step], onwards: bool
    ) -> bool:
        """Ask before sending *command*: what it overwrites, what Check Case found."""
        parts = [
            tr("FoDE will send this to the terminal:") + "\n\n" + command,
        ]
        rerun = [s.log for s in covered if s.log and os.path.exists(os.path.join(case_dir, s.log))]
        if rerun:
            parts.append(tr(
                "These logs exist and will be overwritten, so the steps run again: {logs}."
            ).format(logs=", ".join(rerun)))
        if self._runs_the_solver(case_dir, covered):
            errors = [f for f in self._run_case_check(case_dir).errors]
            if errors:
                lines = [
                    f"{finding_location(f)}: {finding_message(f)}" if finding_location(f)
                    else finding_message(f)
                    for f in errors[:_MAX_FINDINGS]
                ]
                parts.append(
                    tr("Check Case found problems that will stop the solver:") + "\n"
                    + "\n".join("• " + line for line in lines)
                )
        dirty = self._dirty_paths()
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle(tr("Run From Here") if onwards else tr("Run This Step"))
        box.setText("\n\n".join(parts))
        save_and_run = None
        if dirty:
            box.setInformativeText(tr(
                "Some files have unsaved changes; the step reads its files from disk."
            ))
            save_and_run = box.addButton(tr("Save All and Run"), QMessageBox.ButtonRole.AcceptRole)
        run = box.addButton(tr("Run"), QMessageBox.ButtonRole.AcceptRole)
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.setDefaultButton(save_and_run or run)
        box.exec()
        clicked = box.clickedButton()
        if clicked is save_and_run and save_and_run is not None:
            self.save_all_files()
            if self._dirty_paths():
                return False  # a save failed or was declined: do not run on stale files
            return True
        return clicked is run

    def _runs_the_solver(self, case_dir: str, steps: list[ar.Step]) -> bool:
        text = self._current_text(os.path.join(case_dir, "system", "controlDict"))
        application = read_solver_info(text).application if text else None
        return any(
            s.app and (s.app == application or s.app in MODULE_RUNNERS) for s in steps
        )

    def _on_allrun_log_requested(self, path: str) -> None:
        self._on_view_log_summary_clicked()
        if self._log_summary_dialog is not None:
            self._log_summary_dialog.show_log(path)

    # ── Create Allrun from Logs ──────────────────────────────────────────────

    def _on_create_allrun_clicked(self) -> None:
        case_dir = self.state.current_case_dir
        if not case_dir:
            return
        allrun = os.path.join(case_dir, "Allrun")
        if os.path.exists(allrun):
            QMessageBox.information(self, tr("Create Allrun from Logs"), tr(
                "This case already has an Allrun; FoDE never replaces one. "
                "Tools > Allrun Steps… shows its steps."
            ))
            return
        info = installation_info(_installation())
        proposal = ac.propose(case_dir, info.fork if info else None)
        if not any(step.kind != ar.OTHER for step in proposal.steps):
            QMessageBox.information(self, tr("Create Allrun from Logs"), tr(
                "Found no steps: the case has no log.* files from OpenFOAM "
                "applications, and no blockMeshDict or controlDict application "
                "to suggest them from."
            ))
            return
        existing = frozenset(
            name for name in ("Allclean", ac.SCRIPT_PRE, ac.SCRIPT_PARALLEL)
            if os.path.exists(os.path.join(case_dir, name))
        )
        dialog = CreateAllrunDialog(
            proposal, allclean_exists="Allclean" in existing, existing=existing, parent=self
        )
        if dialog.exec() != CreateAllrunDialog.DialogCode.Accepted:
            return
        self._write_new_scripts(case_dir, dialog.scripts())

    def _write_new_scripts(self, case_dir: str, scripts: list[tuple[str, str]]) -> None:
        """Write *scripts* (never over an existing file) and open the Allrun.

        Stops at the first file that cannot be written: Allrun.pre comes
        first, so an Allrun is never left calling a script that is missing.
        """
        allrun = os.path.join(case_dir, ac.SCRIPT_ALLRUN)
        written: list[str] = []
        try:
            for name, text in scripts:
                ac.write_script(os.path.join(case_dir, name), text)
                written.append(name)
        except FileExistsError as exc:
            self._error(tr("Create Allrun from Logs"), tr(
                "{file} appeared while the dialog was open and was left as it is."
            ).format(file=os.path.basename(exc.filename or "")))
        except OSError as exc:
            self._error(tr("Create Allrun from Logs"), tr("Could not write the script: {error}").format(
                error=exc
            ))
        if not written:
            return
        self._reload_file_list()
        if ac.SCRIPT_ALLRUN in written:
            self._open_file_at_line(allrun, 0)
        self._refresh_allrun_steps()
        self.statusBar().showMessage(
            tr("Created {files}.").format(files=", ".join(written)), 5000
        )
