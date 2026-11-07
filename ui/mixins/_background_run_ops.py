# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Runs that outlive FoDE: the background option, Stop Background Run, and following a run.

The detaching, the pid file and the stopAt rewrite are Qt-free
(services/background_run.py); this is the toolbar badge, the stop report,
the close reminder and the polling. Split out of _tools_ops.py.
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QCheckBox, QMessageBox

from app_config import get_app_config
from i18n import tr
from services.background_run import (
    StopReport,
    active_run,
    background_supported,
    finish_stop,
    pending_restore,
    request_stop,
    run_time_modifiable,
    stop_requested_at,
)
from ui.layout_constants import STATUS_NORMAL
from ui.theme import colors

if TYPE_CHECKING:
    from ui.mixins._protocol import MainWindowProtocol as _Base
else:
    _Base = object


class _BackgroundRunOpsMixin(_Base):
    def _background_checkbox(self, box: QMessageBox) -> QCheckBox | None:
        """A "keep running after FoDE closes" option on *box*, where supported.

        Constructed with *box* as its parent: PySide6's setCheckBox does not
        transfer ownership, and a Python-owned checkbox in a Qt-owned box is
        double-freed (see ui/dialogs/processor_delete_dialog.py).
        """
        if not background_supported():
            return None
        chk = QCheckBox(tr("Keep running after FoDE closes (run in the background)"), box)
        box.setCheckBox(chk)
        return chk

    def _on_stop_background_run_clicked(self) -> None:
        if not self.state.current_case_dir:
            return
        case_dir = self.state.current_case_dir
        run = active_run(case_dir)
        if run is None:
            QMessageBox.information(
                self,
                tr("No background run"),
                tr("No background run started from FoDE is going in this case."),
            )
            return
        control_dict = os.path.join(case_dir, "system", "controlDict")
        if self.state.file_dirty.get(control_dict):
            QMessageBox.warning(
                self,
                tr("Stop Background Run"),
                tr(
                    "system/controlDict has unsaved edits. Save or reload it "
                    "first, so the stop request and your edits do not "
                    "overwrite each other."
                ),
            )
            return
        try:
            with open(control_dict, encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            self._error(tr("Stop Background Run"), str(e))
            return
        if not run_time_modifiable(text):
            QMessageBox.warning(
                self,
                tr("Stop Background Run"),
                tr(
                    "controlDict sets runTimeModifiable off, so the running "
                    "solver never re-reads it and cannot be asked to stop. "
                    "To end it anyway, run kill -- -{pid} in a terminal (the "
                    "minus before the pid ends the whole run, mpirun and "
                    "solver included) — the current time step is then lost."
                ).format(pid=run.pid),
            )
            return
        if not self._confirm(
            tr("Stop Background Run"),
            tr(
                "Ask {name} (pid {pid}) to write the current time and stop?\n\n"
                "This sets stopAt writeNow in system/controlDict, which the "
                "running solver re-reads. FoDE puts the original stopAt back "
                "once the run has ended — when it is next open on this case, "
                "if it is closed before then."
            ).format(name=run.label, pid=run.pid),
        ):
            return
        error = request_stop(case_dir, run)
        if error is not None:
            self._error(tr("Stop Background Run"), error)
            return
        self._reload_clean_file_from_disk(control_dict)
        self._reload_file_list()  # the row now reads "Stopping …"
        self._update_background_badge()
        self.statusBar().showMessage(
            tr(
                "Asked {name} to stop: it writes the current time at its next "
                "step and exits. FoDE tells you when it has."
            ).format(name=run.label),
            STATUS_NORMAL,
        )
        self._background_run_timer.start()

    def _poll_background_run(self) -> None:
        """Follow the open case's background run, then show where it stands."""
        try:
            self._follow_background_run()
        finally:
            self._update_background_badge()

    def _remind_background_runs(self) -> None:
        """On close: the background runs that keep going, and how to find them.

        Information only, with OK: closing does not affect them, so asking
        "close anyway?" would suggest a risk that is not there and train
        people to click through the warning that does matter (a run in the
        Terminal tab). What it says is what nothing on screen will once the
        window has gone: that the run exists, where to look for it again, and
        the one thing that still ends it. "Don't remind me again" turns it off
        until Settings > Reset Settings.
        """
        cfg = get_app_config()
        if not cfg.get_remind_background_runs():
            return
        cases = set(self._background_cases)
        if self.state.current_case_dir:
            cases.add(self.state.current_case_dir)
        runs = [(c, r) for c in sorted(cases) if (r := active_run(c)) is not None]
        if not runs:
            return
        lines = "\n".join(
            "• " + tr("{name} in {case} (pid {pid})").format(
                name=run.label, case=os.path.basename(os.path.normpath(case)), pid=run.pid
            )
            for case, run in runs
        )
        text = (
            tr("Still running in the background, and it keeps going after FoDE closes:")
            + "\n"
            + lines
            + "\n\n"
            + tr(
                "To check on a run or stop it, open its case in FoDE again: a "
                "badge beside the case name shows the run."
            )
            + "\n\n"
            + tr("Shutting down or logging out of the computer ends it.")
        )
        box = QMessageBox(
            QMessageBox.Icon.Information,
            tr("Background runs continue"),
            text,
            QMessageBox.StandardButton.Ok,
            self,
        )
        # Parented at construction: setCheckBox does not transfer ownership.
        quiet = QCheckBox(tr("Don't remind me again"), box)
        box.setCheckBox(quiet)
        try:
            box.exec()
            stop_reminding = quiet.isChecked()
        finally:
            box.deleteLater()
        if stop_reminding:
            cfg.set_remind_background_runs(False)

    def _update_background_badge(self) -> None:
        """The toolbar badge and window title for the open case's background run.

        Hidden when there is none. While a stop is pending it turns amber and
        says so, until the run has gone.
        """
        case_dir = self.state.current_case_dir
        run = active_run(case_dir) if case_dir else None
        if run is None or case_dir is None:
            self._background_badge_action.setVisible(False)
            self._background_title = ""
        else:
            requested = stop_requested_at(case_dir)
            btn = self.background_run_btn
            if requested is None:
                btn.setText(tr("● {name} running in background").format(name=run.label))
                color = self.palette().color(QPalette.ColorRole.Highlight).name()
                self._background_title = tr("{name} running").format(name=run.label)
            else:
                btn.setText(tr("■ Stopping {name}…").format(name=run.label))
                color = colors().attention_text
                self._background_title = tr("stopping {name}").format(name=run.label)
            btn.setStyleSheet(f"color: {color}; font-weight: bold;")
            btn.setToolTip(
                tr(
                    "{name} (pid {pid}) is running in the background in this case, "
                    "writing {log}; it keeps going if FoDE closes. Click to stop "
                    "it or view its log summary."
                ).format(name=run.label, pid=run.pid, log=run.log_name)
            )
            self._background_badge_action.setVisible(True)
        self._update_window_title()

    def _follow_background_run(self) -> None:
        """Follow the open case's background run: its start, its stop, its end.

        Polled by ``_background_run_timer`` while a run is going or a stop is
        pending, and called when a case is opened, so a run started -- or a
        stop requested -- in an earlier session is followed too. When the run
        has gone: a stop is reported in a message and its ``stopAt`` put back
        (waiting while controlDict has unsaved edits in FoDE); a run that just
        finished gets a status-bar line, since nobody is waiting on it.
        """
        case_dir = self.state.current_case_dir
        if not case_dir:
            self._background_run_timer.stop()
            self._background_seen = None
            return
        run = active_run(case_dir)
        if run is not None:
            self._background_cases.add(case_dir)
            if self._background_seen != (case_dir, run):
                self._background_seen = (case_dir, run)
                self._reload_file_list()
            self._background_run_timer.start()
            return
        seen, self._background_seen = self._background_seen, None
        if pending_restore(case_dir):
            control_dict = os.path.join(case_dir, "system", "controlDict")
            if self.state.file_dirty.get(control_dict):
                self._background_run_timer.start()
                return
            self._background_run_timer.stop()
            report = finish_stop(case_dir)
            if report is not None:
                self._reload_clean_file_from_disk(control_dict)
                self._reload_file_list()
                self._show_stop_report(report)
            return
        self._background_run_timer.stop()
        if seen is not None and seen[0] == case_dir:
            self._reload_file_list()
            self.statusBar().showMessage(
                tr("{name} has finished in the background; its output is in {log}.").format(
                    name=seen[1].label, log=seen[1].log_name
                ),
                STATUS_NORMAL,
            )

    @staticmethod
    def _stop_report_text(report: StopReport) -> tuple[bool, str]:
        """Whether the stop went wrong, and the message that says how it went."""
        name = report.label or tr("The background run")
        if report.clean is False and report.last_time is None:
            text = tr(
                "{name} ended without finishing cleanly: its log has no final "
                "End line, so it may have crashed or been killed. No time "
                "directory was written. Check {log}."
            ).format(name=name, log=report.log_name)
        elif report.clean is False:
            text = tr(
                "{name} ended without finishing cleanly: its log has no final "
                "End line, so it may have crashed or been killed, and the last "
                "time written ({t}) may be incomplete. Check {log}."
            ).format(name=name, t=report.last_time, log=report.log_name)
        elif report.last_time is not None:
            text = tr("{name} has stopped. Last time written: {t}.").format(
                name=name, t=report.last_time
            )
        else:
            text = tr("{name} has stopped. No time directory was written.").format(name=name)
        if report.restored is not None:
            text += "\n\n" + tr("stopAt in controlDict is back to {value}.").format(
                value=report.restored
            )
        else:
            text += "\n\n" + tr(
                "stopAt in controlDict was changed while the run stopped, so FoDE "
                "left it as it is."
            )
        return report.clean is False, text

    def _show_stop_report(self, report: StopReport) -> None:
        """The result of Stop Background Run, in a message that waits for OK.

        Non-modal: it arrives from a timer, possibly while the user is busy
        in another dialog, and must not block what they are doing.
        """
        failed, text = self._stop_report_text(report)
        box = QMessageBox(
            QMessageBox.Icon.Warning if failed else QMessageBox.Icon.Information,
            tr("Background run stopped"),
            text,
            QMessageBox.StandardButton.Ok,
            self,
        )
        box.setWindowModality(Qt.WindowModality.NonModal)
        box.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        box.show()
        self.statusBar().showMessage(text.split("\n")[0], STATUS_NORMAL)
