# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tools > Plot Results…: open the plot window over the current case.

The window (ui/dialogs/plot_results_dialog.py) imports matplotlib at module
level, so it is imported here only once matplotlib is known to be installed;
without it the action explains what to install instead of failing.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMessageBox

from i18n import tr
from services.plot_render import matplotlib_available

if TYPE_CHECKING:
    from ui.mixins._protocol import MainWindowProtocol as _Base
else:
    _Base = object


class _PlotOpsMixin(_Base):
    def _on_plot_results_clicked(self) -> None:
        if not matplotlib_available():
            QMessageBox.information(
                self,
                tr("matplotlib Not Installed"),
                tr(
                    "Plot Results draws with matplotlib, which is not installed "
                    "in the Python FoDE runs with.\n\nInstall it with:\n"
                    "pip install matplotlib"
                ),
            )
            return
        from ui.dialogs.plot_results_dialog import PlotResultsDialog

        case_dir = self.state.current_case_dir or ""

        def _make() -> PlotResultsDialog:
            return PlotResultsDialog(case_dir, parent=self)

        existed = self._plot_results_dialog is not None
        self._show_cached_dialog("_plot_results_dialog", _make)
        if existed and self._plot_results_dialog is not None:
            self._plot_results_dialog.set_case_dir(case_dir)
            self._plot_results_dialog.reload()

    def _plot_results_case_changed(self, case_dir: str) -> None:
        """Add a newly opened case to an existing plot window."""
        if self._plot_results_dialog is not None and case_dir:
            self._plot_results_dialog.set_case_dir(case_dir)
