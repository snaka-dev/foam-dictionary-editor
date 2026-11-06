# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tools > Run Solver…: RunToolDialog plus what only a solver run needs."""
from __future__ import annotations

import dataclasses
import os
from collections.abc import Sequence

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from i18n import tr
from services.solver_run import (
    is_valid_log_suffix,
    is_valid_solver_name,
    keep_log_prefix,
    next_part_suffix,
)
from services.tool_options import SOLVER_SPEC, ToolSpec
from ui.dialogs.run_tool_dialog import RunToolDialog


@dataclasses.dataclass(frozen=True)
class ExecutableChoice:
    """The editable solver field.

    ``current`` pre-fills it, ``suggestions`` fill its drop-down, and
    ``note`` (optional) is shown under it -- e.g. where ``current`` came from.
    """

    label: str
    current: str
    suggestions: Sequence[str] = ()
    note: str = ""


class RunSolverDialog(RunToolDialog):
    """RunToolDialog over ``SOLVER_SPEC``, whose executable the user picks.

    On top of the base dialog: an editable solver field, a "save all
    first" checkbox the caller reads back through :meth:`save_first` (only
    when ``save_first_label`` is given), an ``mpirun -np N … -parallel``
    checkbox (only when ``parallel_np`` is given), and -- while
    ``log.<solver>`` exists -- the choice to keep it as
    ``log.<solver>.<suffix>`` or overwrite it. A suffix that is invalid or
    names an existing log disables Run, so keeping one log never overwrites
    another.
    """

    def __init__(
        self,
        case_dir: str,
        executable: ExecutableChoice,
        last_values: dict | None = None,
        warning_text: str = "",
        parent: QWidget | None = None,
        *,
        parallel_np: int | None = None,
        parallel_default: bool = False,
        save_first_label: str = "",
    ) -> None:
        # Read by _build_extra_sections, which the base __init__ calls.
        self._executable = executable
        self._np = parallel_np
        self._parallel_default = parallel_default
        self._save_first_label = save_first_label
        super().__init__(
            SOLVER_SPEC,
            case_dir,
            last_values,
            warning_text,
            None,
            parent,
            title=tr("Run Solver"),
        )

    # ── results ───────────────────────────────────────────────────────────────

    def get_executable(self) -> str:
        return self._exe_combo.currentText().strip()

    def save_first(self) -> bool:
        """Whether the user asked for every unsaved file to be saved first."""
        return self._save_chk is not None and self._save_chk.isChecked()

    # ── RunToolDialog hooks ───────────────────────────────────────────────────

    def _build_extra_sections(self, layout: QVBoxLayout) -> None:
        self._build_solver_field(layout)

        self._save_chk: QCheckBox | None = None
        if self._save_first_label:
            self._save_chk = QCheckBox(self._save_first_label)
            self._save_chk.setChecked(True)
            layout.addWidget(self._save_chk)

        self._parallel_chk: QCheckBox | None = None
        if self._np is not None:
            self._parallel_chk = QCheckBox(
                tr("Run in parallel  (mpirun -np {n} … -parallel)").format(n=self._np)
            )
            self._parallel_chk.setChecked(self._parallel_default)
            self._parallel_chk.toggled.connect(self._update_preview)
            layout.addWidget(self._parallel_chk)

        if self._save_chk is not None or self._parallel_chk is not None:
            layout.addSpacing(4)

        self._build_log_box(layout)

    def _resolved_spec(self) -> tuple[ToolSpec | None, str]:
        name = self.get_executable()
        if not is_valid_solver_name(name):
            self._sync_log_box("")
            return None, tr("(enter a solver name: letters, digits, _ . + - only)")
        return dataclasses.replace(self._spec, name=name), ""

    def _run_prefix(self, spec: ToolSpec) -> tuple[str, str]:
        log_name = f"log.{spec.name}"
        problem = self._sync_log_box(log_name)
        if problem:
            return "", problem
        if self._log_exists and self._keep_radio.isChecked():
            kept = f"{log_name}.{self._suffix_edit.text().strip()}"
            return keep_log_prefix(log_name, kept), ""
        return "", ""

    def _parallel_np(self) -> int | None:
        if self._parallel_chk is not None and self._parallel_chk.isChecked():
            return self._np
        return None

    # ── sections ──────────────────────────────────────────────────────────────

    def _build_solver_field(self, layout: QVBoxLayout) -> None:
        exe = self._executable
        self._exe_combo = QComboBox()
        self._exe_combo.setEditable(True)
        self._exe_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        names = [exe.current] if exe.current else []
        names += [n for n in exe.suggestions if n not in names]
        self._exe_combo.addItems(names)
        self._exe_combo.setCurrentText(exe.current)
        self._exe_combo.editTextChanged.connect(self._update_preview)
        form = QFormLayout()
        form.addRow(exe.label, self._exe_combo)
        layout.addLayout(form)
        if exe.note:
            note = QLabel(exe.note)
            note.setWordWrap(True)
            note.setStyleSheet("font-style: italic;")
            layout.addWidget(note)
        layout.addSpacing(4)

    def _build_log_box(self, layout: QVBoxLayout) -> None:
        """The existing-log choice: keep under a suffix, or overwrite.

        Shown only while log.<solver> exists; re-checked on every preview
        update because the solver name is editable.
        """
        self._log_box = QWidget()
        self._log_header = QLabel()
        self._keep_radio = QRadioButton()
        self._overwrite_radio = QRadioButton(tr("Overwrite it"))
        self._suffix_edit = QLineEdit()
        # The suffix follows the solver name (part1 for log.simpleFoam, maybe
        # part3 for log.pimpleFoam) until the user types one of their own.
        self._suffix_typed = False
        self._suffix_for = ""
        self._log_exists = False

        box = QVBoxLayout(self._log_box)
        box.setContentsMargins(0, 0, 0, 0)
        box.addWidget(self._log_header)
        keep_row = QHBoxLayout()
        keep_row.addWidget(self._keep_radio)
        self._suffix_edit.setMaximumWidth(180)
        keep_row.addWidget(self._suffix_edit)
        keep_row.addStretch()
        box.addLayout(keep_row)
        box.addWidget(self._overwrite_radio)
        self._keep_radio.setChecked(True)
        self._keep_radio.toggled.connect(self._update_preview)
        self._suffix_edit.textEdited.connect(self._on_suffix_typed)
        self._suffix_edit.textChanged.connect(self._update_preview)
        layout.addWidget(self._log_box)
        layout.addSpacing(4)

    # ── internals ─────────────────────────────────────────────────────────────

    def _on_suffix_typed(self, _text: str) -> None:
        self._suffix_typed = True

    def _sync_log_box(self, log_name: str) -> str:
        """Show/hide the existing-log choice; return its problem ("" if none)."""
        exists = bool(log_name) and os.path.isfile(
            os.path.join(self._case_dir, log_name)
        )
        self._log_box.setVisible(exists)
        self._log_exists = exists
        if not exists:
            return ""
        self._log_header.setText(tr("Existing {log}:").format(log=log_name))
        self._keep_radio.setText(tr("Keep it as {log}.").format(log=log_name))
        if not self._suffix_typed and self._suffix_for != log_name:
            self._suffix_for = log_name
            self._suffix_edit.blockSignals(True)
            self._suffix_edit.setText(next_part_suffix(self._case_dir, log_name))
            self._suffix_edit.blockSignals(False)
        self._suffix_edit.setEnabled(self._keep_radio.isChecked())
        if not self._keep_radio.isChecked():
            return ""
        suffix = self._suffix_edit.text().strip()
        if not is_valid_log_suffix(suffix):
            return tr(
                "(enter a suffix for the kept log: letters, digits, _ . - only, "
                "not starting with .)"
            )
        kept = f"{log_name}.{suffix}"
        if os.path.exists(os.path.join(self._case_dir, kept)):
            return tr(
                "({log} already exists — choose another suffix so it is not "
                "overwritten)"
            ).format(log=kept)
        return ""
