# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""The Delete processor* Directories confirmation.

A QDialog rather than a QMessageBox because it can carry two options -- keep
the latest time, and read compressed files to their end -- and a QMessageBox
has room for one checkbox. Every widget is parented through its layout, so
Qt alone owns it: QMessageBox.setCheckBox does not transfer ownership in
PySide6, and the checkbox it was once handed was double-freed (a SIGBUS,
pinned by tests/ui/test_tools_busy_terminal.py).
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from i18n import tr
from ui.label_fit import fit_wrapped_labels


class ProcessorDeleteDialog(QDialog):
    """Question icon, text, optional checkboxes, Yes/No with No the default."""

    def __init__(self, parent: QWidget | None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Delete processor* directories?"))
        self.setMinimumWidth(520)
        self._labels_fitted = False

        layout = self._layout = QVBoxLayout(self)
        row = QHBoxLayout()
        icon = QLabel()
        size = self.style().pixelMetric(QStyle.PixelMetric.PM_MessageBoxIconSize)
        icon.setPixmap(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxQuestion).pixmap(size)
        )
        icon.setFixedWidth(size + 12)
        row.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)
        self._label = QLabel()
        self._label.setWordWrap(True)
        row.addWidget(self._label, 1)
        layout.addLayout(row)

        self._options = QVBoxLayout()
        layout.addLayout(self._options)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.No
        )
        self.yes_button = buttons.button(QDialogButtonBox.StandardButton.Yes)
        no = buttons.button(QDialogButtonBox.StandardButton.No)
        no.setDefault(True)
        no.setFocus()
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.keep_checkbox: QCheckBox | None = None
        self.full_gz_checkbox: QCheckBox | None = None

    def text(self) -> str:
        return self._label.text()

    def setText(self, text: str) -> None:  # noqa: N802 -- QMessageBox's name
        self._label.setText(text)
        if self._labels_fitted:
            self._fit()

    def add_option(self, label: str) -> QCheckBox:
        chk = QCheckBox(label)
        self._options.addWidget(chk)
        return chk

    def showEvent(self, event) -> None:  # noqa: N802 -- Qt override
        super().showEvent(event)
        if not self._labels_fitted:
            self._labels_fitted = True
            self._fit()

    def _fit(self) -> None:
        # The text changes when an option is toggled, so the label's minimum
        # is reset before fitting rather than only ever raised.
        self._label.setMinimumHeight(0)
        fit_wrapped_labels(self)
        self._layout.activate()
        self.resize(self.width(), self.sizeHint().height())
