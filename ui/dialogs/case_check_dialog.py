# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tools > Check Case…: the findings of ``services/case_check`` as a list.

Non-modal, like ``log_summary_dialog``, so it can stay open while the user
fixes what it found and presses Check Again. Holds no check logic: the main
window runs the check (it knows the unsaved buffers and the installation) and
hands the result to ``set_result``; double-clicking a finding raises
``open_requested`` with the file and line to open.
"""
from __future__ import annotations

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
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
from services.case_check import ERROR, CaseCheck, Finding
from ui.case_check_text import finding_location, finding_message, severity_label, skip_message
from ui.theme import colors

_DIALOG_WIDTH = 760
_DIALOG_HEIGHT = 420
_FINDING_ROLE = Qt.ItemDataRole.UserRole


class CaseCheckDialog(QDialog):
    """Non-modal list of a case's pre-flight findings."""

    recheck_requested = Signal()
    # Absolute path and 1-based line (0: none) of a finding to open.
    open_requested = Signal(str, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Check Case"))
        self.resize(_DIALOG_WIDTH, _DIALOG_HEIGHT)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self._case_dir = ""

        layout = QVBoxLayout(self)
        self._summary = QLabel()
        self._summary.setWordWrap(True)
        layout.addWidget(self._summary)

        self._list = QTreeWidget()
        self._list.setColumnCount(3)
        self._list.setHeaderLabels([tr("Severity"), tr("Where"), tr("Problem")])
        self._list.setRootIsDecorated(False)
        self._list.setWordWrap(True)
        self._list.setUniformRowHeights(False)
        header = self._list.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setStretchLastSection(True)
        self._list.itemActivated.connect(self._on_item_activated)
        self._list.currentItemChanged.connect(self._on_current_changed)
        layout.addWidget(self._list, 1)

        # The full sentence of the selected problem: the list column elides
        # it, and the explanation is the point for a beginner.
        self._detail = QLabel()
        self._detail.setWordWrap(True)
        self._detail.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self._detail)

        self._skipped = QLabel()
        self._skipped.setWordWrap(True)
        layout.addWidget(self._skipped)

        hint = QLabel(tr("Double-click a problem to open the file at that line."))
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self._recheck_btn = QPushButton(tr("Check Again"))
        self._recheck_btn.clicked.connect(self.recheck_requested)
        buttons.addWidget(self._recheck_btn)
        close_btn = QPushButton(tr("Close"))
        close_btn.clicked.connect(self.close)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

    def set_result(self, case_dir: str, result: CaseCheck) -> None:
        self._case_dir = case_dir
        self._list.clear()
        errors = sum(1 for f in result.findings if f.severity == ERROR)
        warnings = len(result.findings) - errors
        if not result.findings:
            self._summary.setText(
                tr("No problems found in {case}.").format(case=os.path.basename(case_dir))
            )
        else:
            self._summary.setText(
                tr("{case}: {errors} error(s) that will stop a run, {warnings} warning(s).").format(
                    case=os.path.basename(case_dir), errors=errors, warnings=warnings
                )
            )
        palette = colors()
        for finding in result.findings:
            message = finding_message(finding)
            item = QTreeWidgetItem([
                severity_label(finding.severity), finding_location(finding), message,
            ])
            item.setToolTip(2, message)
            item.setData(0, _FINDING_ROLE, finding)
            if finding.severity == ERROR:
                item.setForeground(0, QColor(palette.warning_text))
            self._list.addTopLevelItem(item)
        self._list.setVisible(bool(result.findings))
        self._detail.setVisible(bool(result.findings))
        first = self._list.topLevelItem(0)
        if first is not None:
            self._list.setCurrentItem(first)
        else:
            self._detail.clear()
        notes = [skip_message(s) for s in result.skipped]
        self._skipped.setText("\n".join(notes))
        self._skipped.setVisible(bool(notes))

    def findings(self) -> list[Finding]:
        """The findings currently listed, in order (for tests)."""
        found = []
        for i in range(self._list.topLevelItemCount()):
            item = self._list.topLevelItem(i)
            if item is not None:
                found.append(item.data(0, _FINDING_ROLE))
        return found

    def _on_current_changed(self, item: QTreeWidgetItem | None, _previous) -> None:
        self._detail.setText(item.text(2) if item is not None else "")

    def _on_item_activated(self, item: QTreeWidgetItem, _column: int) -> None:
        finding = item.data(0, _FINDING_ROLE)
        if not isinstance(finding, Finding) or not finding.path or not self._case_dir:
            return
        self.open_requested.emit(os.path.join(self._case_dir, finding.path), finding.line)
