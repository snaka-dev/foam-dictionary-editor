# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tools > Allrun Steps…: the case's Allrun as steps, each marked from its log.

Non-modal, like the Check Case window. Holds no run logic: the main window
reads the plan (``services/allrun``) and hands it over with ``set_plan``; the
buttons raise ``run_requested`` with the step index and whether to run on to
the end, and a double-click on a step with a log raises ``log_requested``.
With both an Allrun and an Allrun-parallel a picker above the list chooses
which one is shown (``script_changed``); the main window reads that one.
States are re-read on a timer while the window is visible, since a running
step rewrites its log in place and nothing else would notice.
"""
from __future__ import annotations

import os

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from i18n import tr
from services import allrun as ar
from services.process_tree import files_written_in
from ui.allrun_text import note_text, state_label, state_tooltip
from ui.theme import colors

_DIALOG_WIDTH = 720
_DIALOG_HEIGHT = 420
_REFRESH_MS = 2000
_INDEX_ROLE = Qt.ItemDataRole.UserRole


class AllrunStepsDialog(QDialog):
    """Non-modal list of an Allrun's steps and their states."""

    # (step index, run on to the end)
    run_requested = Signal(int, bool)
    # Absolute path of a step's log to summarize.
    log_requested = Signal(str)
    refresh_requested = Signal()
    # The case has no Allrun: write one (Tools > Create Allrun from Logs…).
    create_requested = Signal()
    # The picker chose another top-level script (file name).
    script_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Allrun Steps"))
        self.resize(_DIALOG_WIDTH, _DIALOG_HEIGHT)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self._case_dir = ""
        self._plan: ar.AllrunPlan | None = None
        self._can_run = True

        layout = QVBoxLayout(self)
        self._script_row = QWidget()
        script_layout = QHBoxLayout(self._script_row)
        script_layout.setContentsMargins(0, 0, 0, 0)
        script_layout.addWidget(QLabel(tr("Script:")))
        self._script_combo = QComboBox()
        self._script_combo.currentTextChanged.connect(self._on_script_chosen)
        script_layout.addWidget(self._script_combo)
        script_layout.addStretch()
        self._script_row.hide()
        layout.addWidget(self._script_row)

        self._summary = QLabel()
        self._summary.setWordWrap(True)
        layout.addWidget(self._summary)

        self._list = QTreeWidget()
        self._list.setColumnCount(3)
        self._list.setHeaderLabels([tr("State"), tr("Step"), tr("Log")])
        self._list.setRootIsDecorated(False)
        header = self._list.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._list.itemActivated.connect(self._on_activated)
        self._list.currentItemChanged.connect(lambda *_: self._update_buttons())
        layout.addWidget(self._list, 1)
        # Takes the list's room while it is hidden (no Allrun), so the one
        # sentence stays at the top instead of floating mid-window.
        self._no_list_space = QWidget()
        self._no_list_space.hide()
        layout.addWidget(self._no_list_space, 1)

        # What the selected row's state means and what to do about it: the
        # tooltip's text, shown where a beginner will read it.
        self._detail = QLabel()
        self._detail.setWordWrap(True)
        self._detail.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self._detail)

        self._notes = QLabel()
        self._notes.setWordWrap(True)
        layout.addWidget(self._notes)

        buttons = QHBoxLayout()
        self._run_btn = QPushButton(tr("Run This Step"))
        self._run_btn.clicked.connect(lambda: self._request_run(False))
        self._run_from_btn = QPushButton(tr("Run From Here"))
        self._run_from_btn.clicked.connect(lambda: self._request_run(True))
        self._log_btn = QPushButton(tr("Open Log"))
        self._log_btn.clicked.connect(self._open_current_log)
        buttons.addWidget(self._run_btn)
        buttons.addWidget(self._run_from_btn)
        buttons.addWidget(self._log_btn)
        self._create_btn = QPushButton(tr("Create Allrun from Logs…"))
        self._create_btn.setToolTip(tr(
            "Write an Allrun (and Allclean) for this case from its log files"
        ))
        self._create_btn.clicked.connect(self.create_requested)
        self._create_btn.hide()
        buttons.addWidget(self._create_btn)
        buttons.addStretch()
        refresh = QPushButton(tr("Refresh"))
        refresh.clicked.connect(self.refresh_requested)
        buttons.addWidget(refresh)
        close = QPushButton(tr("Close"))
        close.clicked.connect(self.close)
        buttons.addWidget(close)
        layout.addLayout(buttons)

        self._timer = QTimer(self)
        self._timer.setInterval(_REFRESH_MS)
        self._timer.timeout.connect(self.refresh_states)

    # ── content ──────────────────────────────────────────────────────────────

    def set_plan(
        self,
        case_dir: str,
        plan: ar.AllrunPlan | None,
        *,
        can_run: bool = True,
        scripts: tuple[str, ...] = (),
    ) -> None:
        """Show *plan* (None: the case has no Allrun). Keeps the selected row
        while the same script is shown. *scripts* are the top-level scripts
        the case has; with more than one, a picker chooses among them."""
        same_script = (
            self._plan is not None and plan is not None and self._plan.script == plan.script
            and case_dir == self._case_dir
        )
        current = self._current_index() if same_script else None
        self._script_combo.blockSignals(True)
        self._script_combo.clear()
        self._script_combo.addItems(list(scripts))
        if plan is not None:
            self._script_combo.setCurrentText(plan.script)
        self._script_combo.blockSignals(False)
        self._script_row.setVisible(len(scripts) > 1 and plan is not None)
        self._case_dir = case_dir
        self._plan = plan
        self._can_run = can_run
        self._list.clear()
        self._create_btn.setVisible(plan is None)
        self._no_list_space.setVisible(plan is None)
        for widget in (self._list, self._run_btn, self._run_from_btn, self._log_btn):
            widget.setVisible(plan is not None)
        if plan is None:
            self._summary.setText(tr(
                "{case} has no Allrun script. Tutorials keep their workflow in one; "
                "FoDE can write one from the case's log files."
            ).format(case=os.path.basename(case_dir)))
            self._notes.clear()
            self._notes.hide()
            self._update_buttons()
            return
        for index, step in enumerate(plan.steps):
            where = step.script if step.script != plan.script else ""
            text = step.text if not where else f"{step.text}    ({where})"
            item = QTreeWidgetItem(["", text, step.log])
            item.setData(0, _INDEX_ROLE, index)
            if step.kind == ar.OTHER:
                item.setForeground(1, QColor(colors().file_text_only_fg))
            self._list.addTopLevelItem(item)
        notes = [note_text(n) for n in sorted(plan.notes)]
        self._notes.setText("\n".join(notes))
        self._notes.setVisible(bool(notes))
        self.refresh_states()
        keep = self._list.topLevelItem(current) if current is not None else None
        if keep is not None:
            self._list.setCurrentItem(keep)
        else:
            first = self._first_unfinished()
            if first is not None:
                self._list.setCurrentItem(first)

    def refresh_states(self) -> None:
        """Re-read every step's log (cheap: the last 16 KB of each)."""
        plan = self._plan
        if plan is None:
            return
        statuses = self._statuses(plan)
        palette = colors()
        done = sum(1 for s in statuses if s.state == ar.DONE)
        total = sum(1 for s in statuses if s.state)
        for i, status in enumerate(statuses):
            item = self._list.topLevelItem(i)
            if item is None:
                continue
            step = plan.steps[i]
            item.setText(0, state_label(status))
            tip = state_tooltip(step, status)
            for col in range(3):
                item.setToolTip(col, tip)
            if status.state == ar.FAILED or status.suspect:
                item.setForeground(0, QColor(palette.warning_text))
            else:
                item.setForeground(0, QColor(palette.file_text_only_fg) if not status.state
                                   else self._list.palette().text().color())
        running = [plan.steps[i].app for i, s in enumerate(statuses) if s.state == ar.RUNNING]
        if running:
            self._summary.setText(tr("{script}: {done} of {total} steps done; {app} is running.").format(
                script=plan.script, done=done, total=total, app=running[0],
            ))
        else:
            self._summary.setText(tr("{script}: {done} of {total} steps done.").format(
                script=plan.script, done=done, total=total,
            ))
        self._update_buttons()

    @property
    def plan(self) -> ar.AllrunPlan | None:
        return self._plan

    @property
    def case_dir(self) -> str:
        return self._case_dir

    def chosen_script(self) -> str | None:
        """The script the picker shows, or None before any plan."""
        return self._plan.script if self._plan is not None else None

    # ── state for tests ──────────────────────────────────────────────────────

    def row_states(self) -> list[str]:
        return [
            item.text(0)
            for i in range(self._list.topLevelItemCount())
            if (item := self._list.topLevelItem(i)) is not None
        ]

    def select_row(self, index: int) -> None:
        item = self._list.topLevelItem(index)
        if item is not None:
            self._list.setCurrentItem(item)

    # ── internals ────────────────────────────────────────────────────────────

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._timer.start()

    def hideEvent(self, event) -> None:
        self._timer.stop()
        super().hideEvent(event)

    def _statuses(self, plan: ar.AllrunPlan) -> list[ar.StepStatus]:
        # Which logs are still being written tells Running from a stopped run.
        return ar.step_states(
            self._case_dir, plan, writing=files_written_in(self._case_dir)
        )

    def _current_index(self) -> int | None:
        item = self._list.currentItem()
        return item.data(0, _INDEX_ROLE) if item is not None else None

    def _current_step(self) -> ar.Step | None:
        index = self._current_index()
        if self._plan is None or index is None:
            return None
        return self._plan.steps[index]

    def _first_unfinished(self) -> QTreeWidgetItem | None:
        plan = self._plan
        if plan is None:
            return None
        statuses = self._statuses(plan)
        for i, status in enumerate(statuses):
            if status.state and (status.state != ar.DONE or status.suspect):
                return self._list.topLevelItem(i)
        return None

    def _update_buttons(self) -> None:
        item = self._list.currentItem()
        self._detail.setText(item.toolTip(0) if item is not None else "")
        self._detail.setVisible(item is not None)
        step = self._current_step()
        is_step = step is not None and step.kind != ar.OTHER
        self._run_btn.setEnabled(self._can_run and is_step and bool(step and step.app))
        self._run_from_btn.setEnabled(
            self._can_run and step is not None and self._plan is not None and self._plan.linear
        )
        has_log = is_step and step is not None and bool(step.log) and os.path.isfile(
            os.path.join(self._case_dir, step.log)
        )
        self._log_btn.setEnabled(has_log)

    def _request_run(self, onwards: bool) -> None:
        index = self._current_index()
        if index is not None:
            self.run_requested.emit(index, onwards)

    def _open_current_log(self) -> None:
        step = self._current_step()
        if step is None or not step.log:
            return
        path = os.path.join(self._case_dir, step.log)
        if os.path.isfile(path):
            self.log_requested.emit(path)

    def _on_activated(self, _item: QTreeWidgetItem, _column: int) -> None:
        self._open_current_log()

    def _on_script_chosen(self, name: str) -> None:
        if name and (self._plan is None or name != self._plan.script):
            self.script_changed.emit(name)
