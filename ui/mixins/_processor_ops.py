# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tools > Delete processor* Directories…: the checks, the confirmation and the report.

The soundness checks themselves are Qt-free (services/solver_run.py,
services/field_integrity.py); the deletion runs in ui/processor_deletion.py's
worker thread. Split out of _tools_ops.py.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QDialog, QMessageBox

from foam.utils import format_size
from i18n import tr
from services.solver_run import (
    DeletionCheck,
    DeletionProblem,
    case_activity_problem,
    check_processor_deletion,
)
from ui.dialogs.processor_delete_dialog import ProcessorDeleteDialog
from ui.layout_constants import STATUS_NORMAL
from ui.processor_deletion import run_deletion_with_progress

if TYPE_CHECKING:
    from ui.mixins._protocol import MainWindowProtocol as _Base
else:
    _Base = object


class _ProcessorOpsMixin(_Base):
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
        busy = case_activity_problem(case_dir)
        if busy is not None:
            blocking = (busy,)
        if blocking:
            self._report_not_deleted(blocking)
            return
        dialog = self._processor_delete_box(whole, keep)
        try:
            accepted = dialog.exec() == QDialog.DialogCode.Accepted
            keeping = dialog.keep_checkbox is not None and dialog.keep_checkbox.isChecked()
            full_gz = dialog.full_gz_checkbox is not None and dialog.full_gz_checkbox.isChecked()
        finally:
            # Read everything first, then let Qt dispose of the dialog;
            # otherwise every confirmation stays behind as a hidden child of
            # the main window.
            dialog.deleteLater()
        if not accepted:
            return
        chosen = keep if keeping else whole
        if whole.problems:
            # Enforced here, not left to the locked checkbox: deleting
            # everything would lose data, whatever state a widget is in.
            chosen = keep
        result = run_deletion_with_progress(self, case_dir, chosen, full_gz=full_gz)
        self._reload_file_list()
        if result.problems:
            self._report_not_deleted(result.problems)
        elif result.failed:
            self._error(
                tr("Delete processor* directories"),
                tr("Some directories could not be deleted:\n{errors}").format(
                    errors="\n".join(result.failed)
                ),
            )
        elif result.stopped and result.done == 0:
            QMessageBox.information(
                self, tr("Deletion stopped"), tr("Stopped before anything was deleted.")
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

    def _report_not_deleted(self, problems) -> None:
        QMessageBox.warning(
            self,
            tr("processor* directories not deleted"),
            tr("Deleting them now could lose data:")
            + "\n\n"
            + self._problem_lines(problems)
            + "\n\n"
            + tr("Nothing was deleted."),
        )

    def _problem_lines(self, problems) -> str:
        lines = [self._describe_deletion_problem(p) for p in problems]
        if len(lines) > 12:
            lines = lines[:12] + [tr("… and {n} more.").format(n=len(lines) - 12)]
        return "\n".join("• " + line for line in lines)

    def _processor_delete_box(
        self, whole: DeletionCheck, keep: DeletionCheck
    ) -> ProcessorDeleteDialog:
        """The confirmation, with its "keep the latest time" and "read
        compressed files to the end" options when they apply.

        The text describes what will happen with the options as they stand --
        one action, one size -- and is rewritten whenever one is toggled. An
        earlier version listed both choices' sizes up front ("Keeping it
        frees …"), which read as a contradiction and pointed at a checkbox
        the reader had not reached yet.

        The keep checkbox starts ticked -- it deletes less, and spares a
        serial, memory-hungry decomposePar on exactly the cases where
        processor* is large -- except when the case root is already ahead of
        the processors, where the kept time would be an older restart point
        than the case. When deleting everything would lose data but keeping
        the latest time would not (the mesh exists only in processor*, say),
        it is ticked and locked, with the reason shown.

        The compressed-file option appears only when some ``.gz`` root file
        was read at its start only (see services/field_integrity.py), and
        starts ticked: the deletion cannot be undone and happens once, so the
        thorough check is the default and speed the opt-in.
        """
        dialog = ProcessorDeleteDialog(self)
        assurance = tr(
            "Everything that will be deleted also exists at the case root, "
            "checked file by file: each file is complete and matches the mesh. "
            "This cannot be undone."
        )
        keep_chk = None
        note = ""
        t = keep.kept_time
        if t is not None:
            keep_chk = dialog.add_option(
                tr("Keep the latest time ({t}) and the decomposed mesh").format(t=t)
            )
            dialog.keep_checkbox = keep_chk
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

        gz_chk = None
        if whole.unverified_gz:
            gz_chk = dialog.add_option("")
            gz_chk.setChecked(True)
            dialog.full_gz_checkbox = gz_chk

        def describe(*_args) -> None:
            keeping = keep_chk is not None and keep_chk.isChecked()
            check = keep if keeping else whole
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
            if gz_chk is not None:
                n = len(check.unverified_gz)
                size = format_size(check.unverified_gz_bytes)
                gz_chk.setText(
                    tr(
                        "Read compressed files to the end first ({n} .gz files, "
                        "{size} — this can take a few minutes)"
                    ).format(n=n, size=size)
                )
                gz_chk.setEnabled(n > 0)
                if n and not gz_chk.isChecked():
                    parts.append(
                        tr(
                            "{n} compressed files ({size}) will be checked at "
                            "their start only: one cut off part-way would not "
                            "be detected."
                        ).format(n=n, size=size)
                    )
            parts.append(assurance)
            dialog.setText("\n\n".join(parts))

        describe()
        for chk in (keep_chk, gz_chk):
            if chk is not None:
                chk.toggled.connect(describe)
        return dialog

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
        if problem.kind in ("files_cut_off", "files_bad_header", "files_wrong_size"):
            shown = ", ".join(problem.detail[:5])
            if len(problem.detail) > 5:
                shown += ", …"
            if problem.kind == "files_cut_off":
                text = tr(
                    "time {t}: {files} at the case root are cut off (incomplete) "
                    "— run reconstructPar -time {t} again"
                )
            elif problem.kind == "files_bad_header":
                text = tr(
                    "time {t}: {files} at the case root have no valid FoamFile "
                    "header — run reconstructPar -time {t} again"
                )
            else:
                text = tr(
                    "time {t}: {files} at the case root hold a different number "
                    "of values than the mesh (file ≠ mesh), left from another "
                    "mesh — run reconstructPar -time {t} again"
                )
            return text.format(t=problem.time, files=shown)
        if problem.kind == "processes_running":
            return tr(
                "{procs} is working in this case — wait for it to finish, "
                "since the files may still be changing"
            ).format(procs=", ".join(problem.detail))
        return tr("the meshes' cell counts could not be read, so they cannot be compared")
