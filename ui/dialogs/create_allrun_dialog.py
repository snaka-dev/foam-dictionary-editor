# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tools > Create Allrun from Logs…: review the steps, then see the scripts.

Modal. Holds no logic of its own: the proposal comes from
``services/allrun_create.propose``, and the preview is that module's
``render_allrun``/``render_split``/``render_allclean`` over the rows as they
now stand -- ticked or not, in the order the user dragged them to, with the
rows the user added. "Also create Allrun-parallel" splits the script the way
the tutorials do: the steps before the solver in a shared Allrun.pre, the
solver serially in Allrun and after decomposePar in parallel in
Allrun-parallel. The main window writes the files once the dialog is accepted.
"""
from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from i18n import tr
from services import allrun as ar
from services import allrun_create as ac
from ui.allrun_create_text import mark_label, note_text, row_detail, skip_text
from ui.fonts import monospace_font

_DIALOG_WIDTH = 820
_DIALOG_HEIGHT = 620
_STEP_ROLE = Qt.ItemDataRole.UserRole
# File names, the same in every language.
_ALLRUN = ac.SCRIPT_ALLRUN
_ALLCLEAN = "Allclean"
# Preview tab order.
_TAB_PRE, _TAB_ALLRUN, _TAB_PARALLEL, _TAB_ALLCLEAN = range(4)


class CreateAllrunDialog(QDialog):
    """The checklist of proposed steps beside a live preview of both scripts."""

    def __init__(
        self,
        proposal: ac.Proposal,
        *,
        allclean_exists: bool = False,
        existing: frozenset[str] = frozenset(),
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Create Allrun from Logs"))
        self.resize(_DIALOG_WIDTH, _DIALOG_HEIGHT)
        self._proposal = proposal

        # With no logs every row is a suggestion: the intro says so once, in
        # place of the note and of a [suggested] mark on every row -- the way
        # render_allrun puts one comment at the top instead of one per line.
        self._all_suggested = ac.NOTE_FROM_DICTIONARIES in proposal.notes

        layout = QVBoxLayout(self)
        intro = QLabel(
            note_text(ac.NOTE_FROM_DICTIONARIES)
            if self._all_suggested
            else tr("Untick a step to leave it out; drag a step, or use Up and Down, to move it.")
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        splitter = QSplitter(Qt.Orientation.Vertical)
        top = QWidget()
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)
        self._list = QListWidget()
        self._list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._list.setDefaultDropAction(Qt.DropAction.MoveAction)
        for step in proposal.steps:
            self._list.addItem(self._make_item(step))
        self._list.itemChanged.connect(lambda *_: self._update_preview())
        self._list.model().rowsMoved.connect(lambda *_: self._update_preview())
        self._list.currentItemChanged.connect(lambda *_: self._update_detail())
        top_layout.addWidget(self._list, 1)
        moves = QVBoxLayout()
        self._up_btn = QPushButton(tr("Up"))
        self._up_btn.clicked.connect(lambda: self._move(-1))
        self._down_btn = QPushButton(tr("Down"))
        self._down_btn.clicked.connect(lambda: self._move(1))
        self._add_btn = QPushButton(tr("Add Command…"))
        self._add_btn.setToolTip(tr(
            "Add a line to the script below the selected step. An OpenFOAM "
            "application is written with runApplication, so it gets a log."
        ))
        self._add_btn.clicked.connect(self._on_add_command)
        self._remove_btn = QPushButton(tr("Remove"))
        self._remove_btn.setToolTip(tr("Remove a command you added."))
        self._remove_btn.clicked.connect(self._on_remove)
        moves.addWidget(self._up_btn)
        moves.addWidget(self._down_btn)
        moves.addSpacing(12)
        moves.addWidget(self._add_btn)
        moves.addWidget(self._remove_btn)
        moves.addStretch()
        top_layout.addLayout(moves)
        splitter.addWidget(top)

        self._previews = QTabWidget()
        self._pre_view = self._preview_widget()
        self._allrun_view = self._preview_widget()
        self._parallel_view = self._preview_widget()
        self._allclean_view = self._preview_widget()
        self._previews.addTab(self._pre_view, ac.SCRIPT_PRE)
        self._previews.addTab(self._allrun_view, _ALLRUN)
        self._previews.addTab(self._parallel_view, ac.SCRIPT_PARALLEL)
        self._previews.addTab(self._allclean_view, _ALLCLEAN)
        splitter.addWidget(self._previews)
        splitter.setSizes([260, 260])
        layout.addWidget(splitter, 1)

        self._detail = QLabel()
        self._detail.setWordWrap(True)
        self._detail.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self._detail)

        notes = [note_text(n) for n in sorted(proposal.notes) if n != ac.NOTE_FROM_DICTIONARIES]
        if proposal.orig_twins:
            notes.append(tr("Allclean would delete: {files}.").format(
                files=", ".join(proposal.orig_twins)
            ))
        if proposal.skipped:
            notes.append(tr("Logs left out: {logs}.").format(
                logs="; ".join(skip_text(n, r) for n, r in proposal.skipped)
            ))
        self._notes = QLabel("\n".join("• " + n for n in notes))
        self._notes.setWordWrap(True)
        self._notes.setVisible(bool(notes))
        layout.addWidget(self._notes)

        self._mesh_note = QLabel()
        self._mesh_note.setWordWrap(True)
        layout.addWidget(self._mesh_note)

        self._split_note = QLabel()
        self._split_note.setWordWrap(True)
        layout.addWidget(self._split_note)

        n = proposal.decompose_n or max((s.nprocs for s in proposal.steps), default=0)
        self._parallel_box = QCheckBox(tr(
            "Also create Allrun-parallel ({n} processors): the steps before the "
            "solver go in an Allrun.pre that both scripts call"
        ).format(n=n))
        blocked = sorted(existing & {ac.SCRIPT_PRE, ac.SCRIPT_PARALLEL})
        splittable = ac.can_split(proposal) and not blocked
        self._parallel_box.setEnabled(splittable)
        if blocked:
            self._parallel_box.setToolTip(tr("The case already has {files}.").format(
                files=", ".join(blocked)
            ))
        elif not ac.can_split(proposal):
            self._parallel_box.setToolTip(tr(
                "Needs a solver step and a decomposeParDict with more than one subdomain."
            ))
        layout.addWidget(self._parallel_box)

        self._write_allclean = QCheckBox(tr("Also create Allclean"))
        self._write_allclean.setChecked(not allclean_exists)
        self._write_allclean.setEnabled(not allclean_exists)
        if allclean_exists:
            self._write_allclean.setText(tr("Also create Allclean (the case already has one)"))
        self._write_allclean.toggled.connect(lambda *_: self._update_preview())
        layout.addWidget(self._write_allclean)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self._create_btn = buttons.addButton(
            tr("Create"), QDialogButtonBox.ButtonRole.AcceptRole
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Ticked when the case has run in parallel; set before connecting, so
        # the parallel rows go in without a preview update per row.
        if splittable and ac.ran_in_parallel(proposal):
            self._parallel_box.setChecked(True)
            self._set_parallel_rows(True)
        self._parallel_box.toggled.connect(self._on_parallel_toggled)

        if self._list.count():
            self._list.setCurrentRow(0)
        self._update_preview()
        self._update_detail()

    # ── results ──────────────────────────────────────────────────────────────

    def steps(self) -> list[ac.Proposed]:
        """The rows in their current order, ticked as the user left them."""
        out: list[ac.Proposed] = []
        for row in range(self._list.count()):
            item = self._list.item(row)
            step = item.data(_STEP_ROLE)
            out.append(replace(step, checked=item.checkState() == Qt.CheckState.Checked))
        return out

    def splits(self) -> bool:
        """Whether Allrun-parallel (and Allrun.pre) are to be written."""
        return self._parallel_box.isChecked()

    def allrun_text(self) -> str:
        """The serial Allrun -- calling Allrun.pre when the script is split."""
        if self.splits():
            split = ac.render_split(self.steps(), self._proposal)
            if split is not None:
                return split.allrun
        return ac.render_allrun(self.steps(), self._proposal)

    def scripts(self) -> list[tuple[str, str]]:
        """``(file name, text)`` for every file to write, Allrun.pre first."""
        steps = self.steps()
        out: list[tuple[str, str]] = []
        split = ac.render_split(steps, self._proposal) if self.splits() else None
        if split is not None:
            if split.pre is not None:
                out.append((ac.SCRIPT_PRE, split.pre))
            out.append((_ALLRUN, split.allrun))
            out.append((ac.SCRIPT_PARALLEL, split.parallel))
        else:
            out.append((_ALLRUN, ac.render_allrun(steps, self._proposal)))
        clean = self.allclean_text()
        if clean is not None:
            out.append((_ALLCLEAN, clean))
        return out

    def allclean_text(self) -> str | None:
        """The Allclean to write, or None when it is not wanted."""
        if not self._write_allclean.isChecked():
            return None
        return ac.render_allclean(self.steps(), self._proposal)

    # ── internals ────────────────────────────────────────────────────────────

    @staticmethod
    def _preview_widget() -> QPlainTextEdit:
        view = QPlainTextEdit()
        view.setReadOnly(True)
        view.setFont(monospace_font())
        view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        return view

    def _make_item(self, step: ac.Proposed) -> QListWidgetItem:
        item = QListWidgetItem(self._row_text(step))
        item.setData(_STEP_ROLE, step)
        item.setFlags(
            item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsDragEnabled
        )
        item.setCheckState(Qt.CheckState.Checked if step.checked else Qt.CheckState.Unchecked)
        item.setToolTip(row_detail(step))
        return item

    def _solver_list_row(self) -> int | None:
        at = ac.solver_row(self.steps(), self._proposal.solver)
        if at is not None:
            return at
        # Unticked, still the place the parallel rows go around.
        return next(
            (i for i, s in enumerate(self.steps())
             if s.kind != ar.OTHER and s.app == self._proposal.solver),
            None,
        )

    def _set_parallel_rows(self, on: bool) -> None:
        """Add decomposePar and reconstructPar around the solver, or take them out."""
        self._list.blockSignals(True)
        try:
            if on:
                at = self._solver_list_row()
                if at is None:
                    return
                for step in ac.parallel_rows(replace(self._proposal, steps=tuple(self.steps()))):
                    row = at if step.app == "decomposePar" else at + 1
                    self._list.insertItem(row, self._make_item(step))
                    if step.app == "decomposePar":
                        at += 1
            else:
                for row in reversed(range(self._list.count())):
                    step = self._list.item(row).data(_STEP_ROLE)
                    if ac.MARK_PARALLEL_ONLY in step.marks:
                        self._list.takeItem(row)
        finally:
            self._list.blockSignals(False)

    def _on_parallel_toggled(self, on: bool) -> None:
        self._set_parallel_rows(on)
        self._update_preview()
        self._update_detail()

    def _on_add_command(self) -> None:
        text, ok = QInputDialog.getText(
            self, tr("Add Command"),
            tr("Command to add below the selected step (for example decomposePar):"),
        )
        if not ok:
            return
        step = ac.user_row(text, self._proposal.solver)
        if step is None:
            return
        row = self._list.currentRow()
        at = row + 1 if row >= 0 else self._list.count()
        self._list.insertItem(at, self._make_item(step))
        self._list.setCurrentRow(at)
        self._update_preview()

    def _on_remove(self) -> None:
        row = self._list.currentRow()
        item = self._list.item(row) if row >= 0 else None
        if item is None or item.data(_STEP_ROLE).source != ac.SOURCE_USER:
            return
        self._list.takeItem(row)
        self._update_preview()
        self._update_detail()

    def _row_text(self, step: ac.Proposed) -> str:
        line = ac.step_line(step, self._proposal.decompose_n)
        marks = [
            mark_label(m) for m in step.marks
            if not (self._all_suggested and m == ac.MARK_NO_LOG)
        ]
        return f"{line}    [{', '.join(marks)}]" if marks else line

    def _move(self, delta: int) -> None:
        row = self._list.currentRow()
        target = row + delta
        if row < 0 or not 0 <= target < self._list.count():
            return
        item = self._list.takeItem(row)
        self._list.insertItem(target, item)
        self._list.setCurrentRow(target)
        self._update_preview()

    def _update_detail(self) -> None:
        item = self._list.currentItem()
        row = self._list.currentRow()
        self._up_btn.setEnabled(row > 0)
        self._down_btn.setEnabled(0 <= row < self._list.count() - 1)
        self._remove_btn.setEnabled(
            item is not None and item.data(_STEP_ROLE).source == ac.SOURCE_USER
        )
        if item is None:
            self._detail.clear()
            return
        self._detail.setText(row_detail(item.data(_STEP_ROLE)))

    def _update_preview(self) -> None:
        steps = self.steps()
        split = ac.render_split(steps, self._proposal) if self.splits() else None
        if split is not None:
            self._pre_view.setPlainText(split.pre or "")
            self._allrun_view.setPlainText(split.allrun)
            self._parallel_view.setPlainText(split.parallel)
        else:
            self._allrun_view.setPlainText(ac.render_allrun(steps, self._proposal))
        self._previews.setTabVisible(_TAB_PRE, split is not None and split.pre is not None)
        self._previews.setTabVisible(_TAB_PARALLEL, split is not None)
        no_solver = self.splits() and split is None
        if no_solver:
            self._split_note.setText(tr(
                "Tick the {solver} step: Allrun.pre ends and Allrun-parallel starts there."
            ).format(solver=self._proposal.solver))
        self._split_note.setVisible(no_solver)
        clean = self.allclean_text()
        self._allclean_view.setPlainText(clean or "")
        self._previews.setTabEnabled(_TAB_ALLCLEAN, clean is not None)
        if clean is not None and not ac.makes_mesh(steps):
            self._mesh_note.setText(tr(
                "No ticked step makes the mesh, so the Allclean keeps constant/polyMesh "
                "instead of calling cleanCase, which would delete it."
            ))
            self._mesh_note.show()
        else:
            self._mesh_note.hide()
        self._create_btn.setEnabled(any(s.checked for s in steps) and not no_solver)
