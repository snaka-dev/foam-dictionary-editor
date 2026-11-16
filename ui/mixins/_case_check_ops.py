# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tools > Check Case…, and the same findings among Run Solver's warnings.

The checks are Qt-free (services/case_check.py) and the sentences live in
ui/case_check_text.py; this mixin only supplies what the service cannot know
-- the unsaved editor buffers, the OpenFOAM installation -- and opens a
finding's file at its line.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from i18n import tr
from services.case_check import PROCESSOR_COUNT, STOP_AT_LEFT, CaseCheck, check_case
from services.include_scan import foam_etc_dirs
from ui.case_check_text import finding_location, finding_message
from ui.dialogs.case_check_dialog import CaseCheckDialog
from ui.mixins._function_object_ops import _installation

if TYPE_CHECKING:
    from ui.mixins._protocol import MainWindowProtocol as _Base
else:
    _Base = object

# Run Solver already warns about these itself, in its own words
# (_tools_ops._on_run_solver_clicked / _parallel_setup).
_RUN_SOLVER_OWN = frozenset({STOP_AT_LEFT, PROCESSOR_COUNT})
# How many findings Run Solver lists before pointing at Check Case.
_RUN_SOLVER_MAX = 4


class _CaseCheckOpsMixin(_Base):
    def _run_case_check(self, case_dir: str) -> CaseCheck:
        """Check *case_dir* as the user currently sees it, unsaved edits included."""
        return check_case(
            case_dir,
            # No fallback: a file without a buffer is read from disk by the
            # service itself, compressed fields included.
            read_text=lambda path: self._current_text(path, fallback=False),
            etc_dirs=[str(d) for d in foam_etc_dirs()],
            installation=_installation(),
        )

    def _on_check_case_clicked(self) -> None:
        if not self.state.current_case_dir:
            return

        def _make() -> CaseCheckDialog:
            dialog = CaseCheckDialog(parent=self)
            dialog.recheck_requested.connect(self._refresh_case_check)
            dialog.open_requested.connect(self._open_file_at_line)
            return dialog

        self._show_cached_dialog("_case_check_dialog", _make)
        self._refresh_case_check()

    def _refresh_case_check(self) -> None:
        """Re-run the check into the open dialog, or clear it with no case."""
        dialog = self._case_check_dialog
        if dialog is None:
            return
        case_dir = self.state.current_case_dir
        if not case_dir:
            dialog.hide()
            return
        dialog.set_result(case_dir, self._run_case_check(case_dir))

    def _case_check_solver_warnings(self, case_dir: str) -> list[str]:
        """Check Case's findings, as lines for Run Solver's pre-flight warnings."""
        findings = [
            f for f in self._run_case_check(case_dir).findings
            if f.code not in _RUN_SOLVER_OWN
        ]
        lines = []
        for finding in findings[:_RUN_SOLVER_MAX]:
            where = finding_location(finding)
            message = finding_message(finding)
            lines.append(f"{where}: {message}" if where else message)
        if len(findings) > _RUN_SOLVER_MAX:
            lines.append(
                tr("…and {n} more — see Tools > Check Case….").format(
                    n=len(findings) - _RUN_SOLVER_MAX
                )
            )
        return lines
