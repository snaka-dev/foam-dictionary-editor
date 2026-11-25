# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Plot Results' Line Settings…: one line's legend text, x column and style.

Modal and small: it edits one :class:`services.plot_spec.Series` and holds
no plotting logic. Every field has a default state -- an empty label is the
automatic legend text, the default colour is matplotlib's colour cycle --
and the dialog writes the empty value for it, so a saved plot keeps
following the defaults rather than freezing them.
"""
from __future__ import annotations

from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from i18n import tr
from services.plot_spec import LINESTYLES, MARKERS, Series


def _linestyle_names() -> dict[str, str]:
    names = {
        "": tr("Default (solid)"),
        "-": tr("Solid"),
        "--": tr("Dashed"),
        ":": tr("Dotted"),
        "-.": tr("Dash-dot"),
        "none": tr("None (markers only)"),
    }
    assert tuple(names) == LINESTYLES
    return names


def _marker_names() -> dict[str, str]:
    names = {
        "": tr("None"),
        "o": tr("Circle"),
        "s": tr("Square"),
        "^": tr("Triangle up"),
        "v": tr("Triangle down"),
        "D": tr("Diamond"),
        "x": tr("Cross"),
        "+": tr("Plus"),
        ".": tr("Point"),
    }
    assert tuple(names) == MARKERS
    return names


class LineSettingsDialog(QDialog):
    """Edit one plotted line; :meth:`apply_to` writes the result back."""

    def __init__(
        self,
        series: Series,
        x_choices: list[str],
        automatic_label: str,
        parent: QWidget | None = None,
        times: list[str] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Line Settings"))
        self.setMinimumWidth(420)
        self._color = series.color
        form = QFormLayout()

        self.label_edit = QLineEdit(series.label)
        self.label_edit.setPlaceholderText(automatic_label)
        self.label_edit.setToolTip(tr("Leave empty for the automatic legend text"))
        form.addRow(tr("Legend label:"), self.label_edit)

        self.x_combo = QComboBox()
        first = x_choices[0] if x_choices else ""
        self.x_combo.addItem(tr("{name} (the first column)").format(name=first), "")
        for name in x_choices[1:]:
            if name != series.column:
                self.x_combo.addItem(name, name)
        index = self.x_combo.findData(series.x_column if series.x_column != first else "")
        self.x_combo.setCurrentIndex(max(index, 0))
        form.addRow(tr("X column:"), self.x_combo)

        # A sampled line's written times, latest first; empty data is
        # "Latest", which follows the run as it writes more.
        self.time_combo: QComboBox | None = None
        if times:
            self.time_combo = QComboBox()
            self.time_combo.addItem(tr("Latest ({time})").format(time=times[-1]), "")
            for t in reversed(times):
                self.time_combo.addItem(t, t)
            index = self.time_combo.findData(series.time or "")
            self.time_combo.setCurrentIndex(max(index, 0))
            self.time_combo.setToolTip(
                tr("Which written time of this sampled line to plot. The Time slider "
                   "below the plot moves every sampled line together instead.")
            )
            form.addRow(tr("Sample time:"), self.time_combo)

        color_row = QHBoxLayout()
        self.color_btn = QPushButton()
        self.color_btn.clicked.connect(self._choose_color)
        self.auto_color_btn = QPushButton(tr("Default"))
        self.auto_color_btn.clicked.connect(lambda: self._set_color(""))
        color_row.addWidget(self.color_btn, 1)
        color_row.addWidget(self.auto_color_btn)
        form.addRow(tr("Colour:"), color_row)
        self._set_color(series.color)

        self.style_combo = QComboBox()
        for key, name in _linestyle_names().items():
            self.style_combo.addItem(name, key)
        self.style_combo.setCurrentIndex(max(self.style_combo.findData(series.linestyle), 0))
        form.addRow(tr("Line style:"), self.style_combo)

        self.marker_combo = QComboBox()
        for key, name in _marker_names().items():
            self.marker_combo.addItem(name, key)
        self.marker_combo.setCurrentIndex(max(self.marker_combo.findData(series.marker), 0))
        form.addRow(tr("Marker:"), self.marker_combo)

        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(0.0, 10.0)
        self.width_spin.setSingleStep(0.5)
        self.width_spin.setDecimals(1)
        # 0 reads "Default": matplotlib's default width.
        self.width_spin.setSpecialValueText(tr("Default"))
        self.width_spin.setValue(series.linewidth or 0.0)
        form.addRow(tr("Line width:"), self.width_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _set_color(self, color: str) -> None:
        # A swatch icon rather than a stylesheet background: a style paints
        # its own gradient over a button's background, and #d62728 came out
        # a washed-out pink.
        self._color = color
        if color:
            swatch = QPixmap(28, 14)
            swatch.fill(QColor(color))
            self.color_btn.setIcon(QIcon(swatch))
            self.color_btn.setText(color)
        else:
            self.color_btn.setIcon(QIcon())
            self.color_btn.setText(tr("Default (the colour cycle)"))

    def _choose_color(self) -> None:
        chosen = QColorDialog.getColor(QColor(self._color or "#1f77b4"), self, tr("Line Colour"))
        if chosen.isValid():
            self._set_color(chosen.name())

    def apply_to(self, series: Series) -> None:
        """Write the dialog's values into *series*."""
        series.label = self.label_edit.text().strip()
        series.x_column = self.x_combo.currentData() or ""
        if self.time_combo is not None:
            series.time = self.time_combo.currentData() or None
        series.color = self._color
        series.linestyle = self.style_combo.currentData() or ""
        series.marker = self.marker_combo.currentData() or ""
        # A line with no line and no marker would draw nothing at all.
        if series.linestyle == "none" and not series.marker:
            series.marker = "o"
        series.linewidth = self.width_spin.value() or None
