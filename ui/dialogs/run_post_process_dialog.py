# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tools > Run postProcess…: RunToolDialog plus the function and how to run it."""
from __future__ import annotations

import dataclasses
from collections.abc import Sequence

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from i18n import tr
from services.post_process import (
    ALL_FUNCTIONS,
    invocation,
    is_valid_function,
    needs_solver,
)
from services.tool_options import POST_PROCESS_SPEC, ToolSpec
from ui.dialogs.run_tool_dialog import RunToolDialog


class RunPostProcessDialog(RunToolDialog):
    """Run function objects on existing results.

    *functions* are the case's own (controlDict's ``#includeFunc`` names),
    *suggestions* common one-offs run straight from OpenFOAM's templates;
    the field stays editable for anything else. "Run through the solver"
    follows the chosen function -- ticked for one that needs the solver's
    models (services/post_process.py) -- until the user sets it by hand.
    *tool* is ``postProcess`` or ``foamPostProcess``; *application* and
    *module* come from controlDict, for the through-the-solver form.
    """

    def __init__(
        self,
        case_dir: str,
        tool: str,
        functions: Sequence[str],
        suggestions: Sequence[str],
        application: str | None,
        module: str | None,
        last_values: dict | None = None,
        warning_text: str = "",
        parent: QWidget | None = None,
        *,
        preset: str = ALL_FUNCTIONS,
        parallel_np: int | None = None,
        parallel_default: bool = False,
    ) -> None:
        # Read by _build_extra_sections, which the base __init__ calls.
        self._tool = tool
        self._functions = list(functions)
        self._suggestions = [s for s in suggestions if s not in functions]
        self._application = application
        self._module = module
        self._preset = preset
        self._np = parallel_np
        self._parallel_default = parallel_default
        self._solver_set_by_hand = False
        super().__init__(
            POST_PROCESS_SPEC,
            case_dir,
            last_values,
            warning_text,
            None,
            parent,
            title=tr("Run postProcess"),
        )

    # ── results ───────────────────────────────────────────────────────────────

    def function(self) -> str:
        text = self._func_combo.currentText().strip()
        return ALL_FUNCTIONS if text == self._all_label else text

    # ── RunToolDialog hooks ───────────────────────────────────────────────────

    def _build_extra_sections(self, layout: QVBoxLayout) -> None:
        self._all_label = tr("(every function in controlDict)")
        self._func_combo = QComboBox()
        self._func_combo.setEditable(True)
        self._func_combo.addItem(self._all_label)
        for name in self._functions:
            self._func_combo.addItem(name)
        if self._suggestions:
            self._func_combo.insertSeparator(self._func_combo.count())
            for name in self._suggestions:
                self._func_combo.addItem(name)
        self._func_combo.setCurrentText(self._preset or self._all_label)
        self._func_combo.editTextChanged.connect(self._on_function_changed)
        form = QFormLayout()
        form.addRow(tr("Function:"), self._func_combo)
        layout.addLayout(form)
        note = QLabel(
            tr(
                "The case's own function objects come first, then common ones "
                "OpenFOAM runs straight from its templates. Type any other "
                "name, with arguments if it takes them, e.g. mag(p)."
            )
        )
        note.setWordWrap(True)
        note.setStyleSheet("font-style: italic;")
        layout.addWidget(note)

        self._solver_chk = QCheckBox(self._solver_label())
        self._solver_chk.setToolTip(
            tr(
                "Functions such as yPlus, wallShearStress and forces need the "
                "solver's turbulence and transport models. Run plainly, they "
                "finish without error yet calculate nothing (“Unable to find "
                "turbulence model in the database”)."
            )
            + "\n"
            + tr(
                "Every function in controlDict at once needs it too: plain "
                "postProcess then loads no fields, and each sampling function "
                "reports “Cannot find registered field” and writes nothing."
            )
        )
        self._solver_chk.toggled.connect(self._on_solver_toggled)
        layout.addWidget(self._solver_chk)

        self._parallel_chk: QCheckBox | None = None
        if self._np is not None:
            self._parallel_chk = QCheckBox(
                tr("Run in parallel  (mpirun -np {n} … -parallel)").format(n=self._np)
            )
            self._parallel_chk.setChecked(self._parallel_default)
            self._parallel_chk.toggled.connect(self._update_preview)
            layout.addWidget(self._parallel_chk)
        layout.addSpacing(4)
        self._follow_function()

    def _resolved_spec(self) -> tuple[ToolSpec | None, str]:
        func = self.function()
        if func != ALL_FUNCTIONS and not is_valid_function(func):
            return None, tr("(enter a function name, e.g. probes or mag(U))")
        lead = invocation(self._tool, self._solver_chk.isChecked(), self._application, self._module)
        if lead is None:
            return None, tr(
                "(controlDict names no solver to run it through — untick "
                "“Run through the solver”)"
            )
        return dataclasses.replace(self._spec, name=lead[0]), ""

    def _lead_args(self) -> tuple[str, ...]:
        lead = invocation(self._tool, self._solver_chk.isChecked(), self._application, self._module)
        func = self.function()
        args = tuple(lead[1:]) if lead else ()
        return args + (("-func", func) if func != ALL_FUNCTIONS else ())

    def _log_name(self) -> str | None:
        # Never the solver's own log, even when run through the solver.
        return f"log.{self._tool}"

    def _parallel_np(self) -> int | None:
        if self._parallel_chk is not None and self._parallel_chk.isChecked():
            return self._np
        return None

    # ── internals ─────────────────────────────────────────────────────────────

    def _solver_label(self) -> str:
        if self._tool == "foamPostProcess":
            via = f"foamPostProcess -solver {self._module or '?'}"
        else:
            via = f"{self._application or '?'} -postProcess"
        return tr("Run through the solver  ({via})").format(via=via)

    def _on_function_changed(self, _text: str) -> None:
        self._follow_function()
        self._update_preview()

    def _on_solver_toggled(self, _checked: bool) -> None:
        # Only a user's click reaches here: _follow_function sets the box
        # with its signals blocked.
        self._solver_set_by_hand = True
        self._update_preview()

    def _follow_function(self) -> None:
        """Tick "through the solver" for a function that needs it, until set by hand."""
        if self._solver_set_by_hand:
            return
        # Only where a solver can be named: otherwise the plain run is the
        # one that can run at all, and the box stays clear rather than
        # disabling Run.
        possible = invocation(self._tool, True, self._application, self._module) is not None
        self._solver_chk.blockSignals(True)
        self._solver_chk.setChecked(possible and needs_solver(self._case_dir, self.function()))
        self._solver_chk.blockSignals(False)
