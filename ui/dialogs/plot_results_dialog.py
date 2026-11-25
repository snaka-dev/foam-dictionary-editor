# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tools > Plot Results…: plot what function objects and solvers wrote.

Non-modal, like View Log Summary, so it can sit beside the main window while a
run goes on. Left: every case added, its data sets (``postProcessing/`` files
and solver logs, from :mod:`services.plot_data`) and their columns, ticked to
plot. Right: the plot, its settings, and the ways out -- copy, save, export a
script.

Everything the plot shows is a :class:`services.plot_spec.PlotSpec` built
from the widgets; the canvas, a saved image and an exported script are all
made from that one object (see DEVELOPER.md's "Plot Results"). A saved image
and a script use the spec's own size and resolution rather than the canvas's,
so the two agree with each other whatever size the window is.

Imports matplotlib at module level: the mixin checks it is installed before
importing this module at all.
"""
from __future__ import annotations

import io
import math
import os
import re
from datetime import datetime
from pathlib import Path

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtCore import QPoint, QSignalBlocker, Qt, QTimer
from PySide6.QtGui import QGuiApplication, QImage, QPalette, QStandardItemModel
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSlider,
    QSpinBox,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from shiboken6 import isValid

from i18n import tr
from services.plot_animation import (
    FORMATS,
    AnimationWriter,
    ffmpeg_available,
    fixed_ranges,
    frame_spec,
    frame_times,
    frames_directory,
    latest_at,
    stamp_text,
)
from services.plot_data import Source, find_sources, load_source, profile_path
from services.plot_export import (
    PlottedLine,
    default_stem,
    free_csv_path,
    is_our_note,
    note_path,
    plotted_note,
    plotted_table,
    source_note,
    table_csv,
    table_tsv,
)
from services.plot_output import refusal, write_atomically
from services.plot_render import default_font_sizes, draw, font_family
from services.plot_script import gnuplot_data, gnuplot_script, python_script
from services.plot_spec import (
    LEGEND_LOCATIONS,
    Axis,
    PlotSpec,
    Resolved,
    Series,
    case_label,
    resolve,
    spec_from_json,
    spec_to_json,
)
from ui.dialogs.data_file_viewer import DataFileViewer, show_in_folder

_ROLE = Qt.ItemDataRole.UserRole
_REPLOT_DELAY_MS = 120
# Formats Figure.savefig writes without extra packages; .png leads, being
# the default. One combined filter, for the reason _view_image_export gives.
_IMAGE_SUFFIXES = (".png", ".svg", ".pdf", ".jpg", ".jpeg", ".eps", ".tif", ".tiff")


def writable_plot_path(path: str) -> str:
    """*path* with a suffix savefig understands: lowered, or ``.png`` added."""
    suffix = Path(path).suffix
    if suffix.lower() not in _IMAGE_SUFFIXES:
        return path + ".png"
    if suffix != suffix.lower():
        return str(Path(path).with_suffix(suffix.lower()))
    return path


def _parse_float(text: str) -> float | None:
    try:
        value = float(text.strip())
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def _legend_location_names() -> dict[str, str]:
    """Display names for ``LEGEND_LOCATIONS`` (built per call: ``tr`` at import freezes English)."""
    names = {
        "best": tr("Best"),
        "upper right": tr("Upper right"),
        "upper left": tr("Upper left"),
        "lower left": tr("Lower left"),
        "lower right": tr("Lower right"),
        "right": tr("Right"),
        "center left": tr("Center left"),
        "center right": tr("Center right"),
        "lower center": tr("Lower center"),
        "upper center": tr("Upper center"),
        "center": tr("Center"),
        "outside right": tr("Outside right"),
        "custom": tr("Where dragged"),
    }
    assert tuple(names) == LEGEND_LOCATIONS
    return names


# The figure's resolution when it simply fills the window: matplotlib's own
# default, which is what the canvas used before the preview existed.
_FILL_DPI = 100.0


# Auto-refresh: how often to look, and how much more slowly once the plotted
# files are large, since a changed file is read whole.
_REFRESH_MS = 2000
_SLOW_REFRESH_MS = 10000
_LARGE_BYTES = 50 * 1024 * 1024
# Every this many checks, every case is scanned for new data sets too.
_RESCAN_EVERY = 5


class _PreviewArea(QWidget):
    """Holds the canvas and decides its size: a preview of the saved image.

    In preview mode the figure is kept at the image's size in inches and
    drawn at whatever resolution makes it fit the space, centred -- so the
    view is the saved image scaled: the same aspect ratio, the same text
    sizes relative to the plot, the same ticks and legend placement. That
    works because matplotlib's Qt canvas, on a resize, sets the figure's
    size to the widget's pixels divided by the figure's dpi: setting the dpi
    first leaves the inches as they were. With "fit to window" the canvas
    fills the space at a fixed dpi, as a plain matplotlib window does.
    """

    def __init__(self, canvas: FigureCanvasQTAgg, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.canvas = canvas
        canvas.setParent(self)
        self.size_inches = (8.0, 5.0)
        self.fit_window = False
        # Shown scale of the preview, as pixels per inch on screen (logical).
        self.pixels_per_inch = _FILL_DPI
        self.setMinimumSize(200, 150)
        self.setAutoFillBackground(True)
        # Dark, not Mid: the desktop theme draws Mid near-white, and the white
        # figure then has no visible edge.
        self.setBackgroundRole(QPalette.ColorRole.Dark)

    def set_size_inches(self, width: float, height: float) -> None:
        self.size_inches = (width, height)
        self.relayout()

    def set_fit_window(self, fit: bool) -> None:
        self.fit_window = fit
        self.relayout()

    def _set_dpi(self, logical_dpi: float) -> None:
        # The figure's dpi is in physical pixels: logical dpi times the
        # screen's ratio. _original_dpi is what matplotlib rescales from when
        # the window moves to a screen with another ratio; left alone, that
        # move would undo the preview's scale.
        figure = self.canvas.figure
        figure._original_dpi = logical_dpi  # type: ignore[attr-defined]
        figure.dpi = logical_dpi * self.canvas.device_pixel_ratio

    def relayout(self) -> None:
        area = self.rect()
        if self.fit_window:
            self.pixels_per_inch = _FILL_DPI
            self._set_dpi(_FILL_DPI)
            self.canvas.setGeometry(area)
            return
        width, height = self.size_inches
        scale = max(1.0, min(area.width() / width, area.height() / height))
        w, h = round(width * scale), round(height * scale)
        self.pixels_per_inch = scale
        self._set_dpi(scale)
        self.canvas.setGeometry(
            area.x() + (area.width() - w) // 2, area.y() + (area.height() - h) // 2, w, h
        )
        # The canvas' own resize handler only runs when its size changed.
        self.canvas.figure.set_size_inches(width, height, forward=False)
        self.canvas.draw_idle()

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        self.relayout()


class _FontSizeSpin(QDoubleSpinBox):
    """A font size in points; 0 is "Default", matplotlib's own size.

    Stepping from Default starts at that real size -- up gives one point
    more, down one less -- rather than at 1 pt, which is where a plain spin
    box would go from 0. Default shows the size it stands for.
    """

    def __init__(self, default: float) -> None:
        super().__init__()
        self.default_size = default
        self.setRange(0.0, 72.0)
        self.setDecimals(0)
        self.setSingleStep(1.0)
        self.setSuffix(" pt")
        self.setSpecialValueText(tr("Default ({size} pt)").format(size=f"{default:g}"))

    def stepBy(self, steps: int) -> None:  # noqa: N802 (Qt override)
        if self.value() == 0.0:
            self.setValue(max(1.0, self.default_size + steps * self.singleStep()))
        else:
            super().stepBy(steps)

    def stepEnabled(self) -> QAbstractSpinBox.StepEnabledFlag:  # noqa: N802
        if self.value() == 0.0:
            # Both ways: down from Default is the default size less a point.
            return (QAbstractSpinBox.StepEnabledFlag.StepUpEnabled
                    | QAbstractSpinBox.StepEnabledFlag.StepDownEnabled)
        return super().stepEnabled()


class _AxisFields:
    """The label/min/max/step/log row of one axis."""

    def __init__(self, on_change) -> None:
        self.label = QLineEdit()
        self.min = QLineEdit()
        self.max = QLineEdit()
        self.step = QLineEdit()
        self.log = QCheckBox(tr("Log scale"))
        self.label.setPlaceholderText(tr("automatic"))
        for edit in (self.min, self.max, self.step):
            edit.setPlaceholderText(tr("auto"))
            edit.setMaximumWidth(110)
            edit.textChanged.connect(on_change)
        self.label.textChanged.connect(on_change)
        self.log.toggled.connect(on_change)

    def axis(self) -> Axis:
        return Axis(
            label=self.label.text(),
            min=_parse_float(self.min.text()),
            max=_parse_float(self.max.text()),
            log=self.log.isChecked(),
            step=_parse_float(self.step.text()),
        )

    def set_range(self, lo: float | None, hi: float | None) -> None:
        self.min.setText("" if lo is None else f"{lo:.6g}")
        self.max.setText("" if hi is None else f"{hi:.6g}")

    def set_axis(self, axis: Axis) -> None:
        """Show *axis* in the row; the exact inverse of :meth:`axis`."""
        self.label.setText(axis.label)
        self.min.setText("" if axis.min is None else repr(axis.min))
        self.max.setText("" if axis.max is None else repr(axis.max))
        self.step.setText("" if axis.step is None else repr(axis.step))
        self.log.setChecked(axis.log)


class PlotResultsDialog(QDialog):
    """Non-modal plot window over one or more cases' text output."""

    def __init__(self, case_dir: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Plot Results"))
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        # Non-modal and meant to sit beside the main window, so it is often
        # not the active one; Qt shows tooltips only in the active window, and
        # a data set's tooltip is where its files are named.
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips, True)
        self.resize(1100, 700)
        self._cases: list[str] = []
        self._current_case = ""
        self._sources: dict[str, list[Source]] = {}
        # Ticked columns in the order they were ticked: the legend's order.
        self._series: list[Series] = []
        self._populating = False
        self._last_resolved: Resolved | None = None
        # Where the legend was dragged to (axes fractions), for "custom".
        self._legend_at: tuple[float, float] | None = None
        # The legend's extent when a press landed on it, to tell a drag.
        self._legend_pressed: tuple[float, float, float, float] | None = None
        # True while the y axis is logarithmic because residuals were ticked
        # rather than because the user asked: undone when they are not all
        # the plot shows any more, or the next column (a velocity profile
        # that goes negative) would be drawn on a log axis and lose half of
        # itself. Ticking Log scale by hand makes it the user's.
        self._auto_log = False
        self._setting_log = False
        # Open data-file windows (Open File), so one file gets one window.
        self._viewers: list[DataFileViewer] = []
        self._replot_timer = QTimer(self)
        self._replot_timer.setSingleShot(True)
        self._replot_timer.setInterval(_REPLOT_DELAY_MS)
        self._replot_timer.timeout.connect(self.replot)
        # Auto-refresh: a cheap check on a timer, a redraw only on a change.
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(_REFRESH_MS)
        self._refresh_timer.timeout.connect(self.auto_refresh)
        self._refresh_ticks = 0
        self._file_signature: tuple = ()
        # The axes' limits as last drawn by FoDE, to tell a zoom from them.
        self._drawn_limits: tuple | None = None
        self._build_ui()
        self._on_image_size()
        if case_dir:
            self.set_case_dir(case_dir)
        self._refresh_timer.start()

    # ── construction ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_data_side())
        splitter.addWidget(self._build_plot_side())
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([320, 780])
        layout = QVBoxLayout(self)
        layout.addWidget(splitter)

    def _build_data_side(self) -> QWidget:
        side = QWidget()
        layout = QVBoxLayout(side)
        layout.setContentsMargins(0, 0, 0, 0)
        buttons = QHBoxLayout()
        self.add_case_btn = QPushButton(tr("Add Case…"))
        self.add_case_btn.setToolTip(tr("Add another case, to compare its data with this one's"))
        self.add_case_btn.clicked.connect(self._on_add_case)
        self.remove_case_btn = QPushButton(tr("Remove Case"))
        self.remove_case_btn.setToolTip(tr("Remove the selected case from this window"))
        self.remove_case_btn.clicked.connect(self._on_remove_case)
        self.reload_btn = QPushButton(tr("Reload"))
        self.reload_btn.setToolTip(tr("Read the files again, for data written since"))
        self.reload_btn.clicked.connect(self.reload)
        for b in (self.add_case_btn, self.remove_case_btn, self.reload_btn):
            buttons.addWidget(b)
        layout.addLayout(buttons)

        refresh = QHBoxLayout()
        self.auto_refresh_check = QCheckBox(tr("Auto-refresh"))
        self.auto_refresh_check.setChecked(True)
        self.auto_refresh_check.setToolTip(
            tr("Redraw by itself when a running case writes more, every few seconds")
        )
        self.auto_refresh_check.toggled.connect(self._on_auto_refresh_toggled)
        self.refresh_label = QLabel()
        refresh.addWidget(self.auto_refresh_check)
        refresh.addWidget(self.refresh_label, 1)
        layout.addLayout(refresh)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_tree_menu)
        self.tree.itemExpanded.connect(self._fill_columns)
        self.tree.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.tree, 1)


        self.hint = QLabel()
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)
        return side

    def _build_plot_side(self) -> QWidget:
        side = QWidget()
        layout = QVBoxLayout(side)
        layout.setContentsMargins(0, 0, 0, 0)
        self.figure = Figure()
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, side)
        self.canvas.mpl_connect("button_press_event", self._on_canvas_press)
        self.canvas.mpl_connect("button_release_event", self._on_canvas_release)
        self.preview = _PreviewArea(self.canvas)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.preview, 1)
        layout.addWidget(self._build_time_row())
        layout.addWidget(self._build_settings())

        out = QHBoxLayout()
        self.copy_btn = QPushButton(tr("Copy Image"))
        self.copy_btn.setToolTip(tr("Copy the plot to the clipboard as an image"))
        self.copy_btn.clicked.connect(self.copy_image)
        self.save_btn = QPushButton(tr("Save Image…"))
        self.save_btn.setToolTip(tr("Save the plot as PNG, SVG, PDF, …"))
        self.save_btn.clicked.connect(self._on_save_image)
        self.export_btn = QPushButton(tr("Export Script"))
        self.export_btn.setToolTip(
            tr("Write a script that draws this plot again outside FoDE")
        )
        menu = QMenu(self.export_btn)
        menu.addAction(tr("Python (matplotlib)…"), self._on_export_python)
        menu.addAction(tr("gnuplot…"), self._on_export_gnuplot)
        self.export_btn.setMenu(menu)
        self.export_data_btn = QPushButton(tr("Export Data…"))
        self.export_data_btn.setToolTip(
            tr("Save the plotted lines as a CSV with headings, and a note of where they came from")
        )
        self.export_data_btn.clicked.connect(self._on_export_data)
        close_btn = QPushButton(tr("Close"))
        close_btn.clicked.connect(self.close)
        for b in (self.copy_btn, self.save_btn, self.export_btn, self.export_data_btn):
            out.addWidget(b)
        out.addStretch(1)
        out.addWidget(close_btn)
        layout.addLayout(out)
        return side

    def _build_settings(self) -> QGroupBox:
        box = QGroupBox(tr("Plot settings"))
        grid = QGridLayout(box)
        self.title_edit = QLineEdit()
        self.title_edit.textChanged.connect(self._schedule_replot)
        grid.addWidget(QLabel(tr("Title:")), 0, 0)
        grid.addWidget(self.title_edit, 0, 1, 1, 6)
        self.x_fields = _AxisFields(self._schedule_replot)
        self.y_fields = _AxisFields(self._schedule_replot)
        self.y_fields.log.toggled.connect(self._on_y_log_toggled)
        headers = (tr("Label"), tr("Min"), tr("Max"), tr("Tick step"))
        for col, text in enumerate(headers, start=1):
            grid.addWidget(QLabel(text), 1, col)
        for row, (name, f) in enumerate(
            ((tr("X axis"), self.x_fields), (tr("Y axis"), self.y_fields)), start=2
        ):
            grid.addWidget(QLabel(name), row, 0)
            grid.addWidget(f.label, row, 1)
            grid.addWidget(f.min, row, 2)
            grid.addWidget(f.max, row, 3)
            grid.addWidget(f.step, row, 4)
            grid.addWidget(f.log, row, 5)
        grid.setColumnStretch(1, 1)

        extras = QHBoxLayout()
        self.grid_check = QCheckBox(tr("Grid"))
        self.grid_check.setChecked(True)
        self.legend_check = QCheckBox(tr("Legend"))
        self.legend_check.setChecked(True)
        for c in (self.grid_check, self.legend_check):
            c.toggled.connect(self._schedule_replot)
            extras.addWidget(c)
        self.legend_combo = QComboBox()
        for key, name in _legend_location_names().items():
            self.legend_combo.addItem(name, key)
        # Reached by dragging the legend, not by choosing it.
        model = self.legend_combo.model()
        assert isinstance(model, QStandardItemModel)
        custom = model.item(LEGEND_LOCATIONS.index("custom"))
        if custom is not None:
            custom.setEnabled(False)
        self.legend_combo.setToolTip(
            tr("Where the legend goes. You can also drag it on the plot.")
        )
        self.legend_combo.currentIndexChanged.connect(self._on_legend_location_chosen)
        self.legend_check.toggled.connect(self.legend_combo.setEnabled)
        extras.addWidget(self.legend_combo)
        self.use_view_btn = QPushButton(tr("Use Current View"))
        self.use_view_btn.setToolTip(
            tr("Copy the ranges you zoomed or panned to into Min and Max")
        )
        self.use_view_btn.clicked.connect(self._on_use_view)
        self.auto_range_btn = QPushButton(tr("Automatic Ranges"))
        self.auto_range_btn.setToolTip(tr("Clear Min and Max on both axes"))
        self.auto_range_btn.clicked.connect(self._on_auto_ranges)
        extras.addWidget(self.use_view_btn)
        extras.addWidget(self.auto_range_btn)
        extras.addStretch(1)

        size = QFormLayout()
        size_row = QHBoxLayout()
        self.width_spin = QDoubleSpinBox()
        self.height_spin = QDoubleSpinBox()
        for spin, value in ((self.width_spin, 8.0), (self.height_spin, 5.0)):
            spin.setRange(1.0, 40.0)
            spin.setSingleStep(0.5)
            spin.setDecimals(1)
            spin.setValue(value)
            spin.setSuffix(" in")
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(50, 1200)
        self.dpi_spin.setValue(150)
        self.dpi_spin.setSuffix(" dpi")
        self.width_spin.valueChanged.connect(self._on_image_size)
        self.height_spin.valueChanged.connect(self._on_image_size)
        self.dpi_spin.valueChanged.connect(self._on_image_size)
        size_row.addWidget(self.width_spin)
        size_row.addWidget(QLabel("×"))
        size_row.addWidget(self.height_spin)
        size_row.addWidget(self.dpi_spin)
        size.addRow(tr("Image size:"), size_row)
        size_row.addStretch(1)
        extras.addLayout(size)
        grid.addLayout(extras, 4, 0, 1, 7)

        fonts = QHBoxLayout()
        fonts.addWidget(QLabel(tr("Font sizes:")))
        defaults = default_font_sizes()
        self.title_size_spin = self._size_spin(defaults["title"])
        self.label_size_spin = self._size_spin(defaults["label"])
        self.tick_size_spin = self._size_spin(defaults["tick"])
        self.legend_size_spin = self._size_spin(defaults["legend"])
        for name, spin in (
            (tr("Title"), self.title_size_spin),
            (tr("Axis labels"), self.label_size_spin),
            (tr("Tick labels"), self.tick_size_spin),
            (tr("Legend"), self.legend_size_spin),
        ):
            fonts.addWidget(QLabel(name))
            fonts.addWidget(spin)
        fonts.addStretch(1)
        grid.addLayout(fonts, 5, 0, 1, 7)

        files = QHBoxLayout()
        self.save_settings_btn = QPushButton(tr("Save Settings…"))
        self.save_settings_btn.setToolTip(
            tr("Save what is plotted and how, to open again later or in another case")
        )
        self.save_settings_btn.clicked.connect(self._on_save_settings)
        self.load_settings_btn = QPushButton(tr("Load Settings…"))
        self.load_settings_btn.setToolTip(tr("Replace this plot with one saved earlier"))
        self.load_settings_btn.clicked.connect(self._on_load_settings)
        files.addWidget(self.save_settings_btn)
        files.addWidget(self.load_settings_btn)
        files.addStretch(1)
        self.preview_label = QLabel()
        self.preview_label.setToolTip(
            tr("The plot is shown as the saved image will look, scaled to fit the window")
        )
        self.fit_window_check = QCheckBox(tr("Fit to window"))
        self.fit_window_check.setToolTip(
            tr("Let the plot fill the window instead of previewing the image's shape and "
               "text sizes")
        )
        self.fit_window_check.toggled.connect(self._on_fit_window)
        files.addWidget(self.preview_label)
        files.addWidget(self.fit_window_check)
        grid.addLayout(files, 6, 0, 1, 7)
        return box

    def _build_time_row(self) -> QWidget:
        """Time slider, play, frame rate, Save Animation… -- for sampled lines.

        Position 0 is the ordinary plot, "Latest": each sampled line at its
        latest time, or the one its Line Settings chose. 1… are the
        animation's frames, shown exactly as they are saved -- and as Save
        Image, the scripts and Export Data write them.
        Hidden while the plot has no sampled line with two times or more.
        """
        self.time_row = QWidget()
        row = QHBoxLayout(self.time_row)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(QLabel(tr("Time:")))
        self.time_slider = QSlider(Qt.Orientation.Horizontal)
        self.time_slider.setRange(0, 0)
        self.time_slider.setToolTip(
            tr("Step the sampled lines through their output times, as the animation's frames")
        )
        self.time_slider.valueChanged.connect(self._on_frame_changed)
        self.frame_label = QLabel()
        self.frame_label.setMinimumWidth(120)
        self.play_btn = QPushButton(tr("Play"))
        self.play_btn.setCheckable(True)
        self.play_btn.toggled.connect(self._on_play)
        self.fps_spin = QDoubleSpinBox()
        self.fps_spin.setRange(0.2, 60.0)
        self.fps_spin.setDecimals(1)
        self.fps_spin.setValue(5.0)
        self.fps_spin.setSuffix(tr(" frames/s"))
        self.fps_spin.valueChanged.connect(self._on_fps_changed)
        self.save_anim_btn = QPushButton(tr("Save Animation…"))
        self.save_anim_btn.setToolTip(
            tr("Save the frames as a GIF, an MP4 video or numbered PNG images")
        )
        self.save_anim_btn.clicked.connect(self._on_save_animation)
        row.addWidget(self.time_slider, 1)
        row.addWidget(self.frame_label)
        row.addWidget(self.play_btn)
        row.addWidget(self.fps_spin)
        row.addWidget(self.save_anim_btn)
        self._frames: list[str] = []
        self._play_timer = QTimer(self)
        self._play_timer.timeout.connect(self._advance_frame)
        self.time_row.hide()
        return self.time_row

    def _size_spin(self, default: float) -> _FontSizeSpin:
        spin = _FontSizeSpin(default)
        spin.valueChanged.connect(self._schedule_replot)
        return spin

    # ── cases and the data tree ─────────────────────────────────────────────

    @property
    def cases(self) -> list[str]:
        return list(self._cases)

    @property
    def series(self) -> list[Series]:
        return list(self._series)

    def set_case_dir(self, case_dir: str) -> None:
        """Make *case_dir* the window's current case, adding it if new.

        Cases are never dropped here: opening another case in the main
        window is how a user most naturally gathers cases to compare, so the
        previous one, and whatever of it is ticked, stays.
        """
        if not case_dir:
            return
        case_dir = os.path.normpath(case_dir)
        self._current_case = case_dir
        if case_dir not in self._cases:
            self._add_case(case_dir)
        self._mark_current_case()

    def _add_case(self, case_dir: str) -> None:
        self._cases.append(case_dir)
        self._sources[case_dir] = find_sources(case_dir)
        self._populating = True
        try:
            self._add_case_item(case_dir)
        finally:
            self._populating = False
        self._update_hint()

    def _add_case_item(self, case_dir: str) -> QTreeWidgetItem:
        item = QTreeWidgetItem([case_label(case_dir)])
        item.setData(0, _ROLE, ("case", case_dir))
        item.setToolTip(0, case_dir)
        self.tree.addTopLevelItem(item)
        sources = self._sources[case_dir]
        if not sources:
            empty = QTreeWidgetItem([tr("(no postProcessing data or solver logs)")])
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            item.addChild(empty)
        for src in sources:
            child = QTreeWidgetItem([src.title])
            child.setData(0, _ROLE, ("source", case_dir, src.key))
            child.setToolTip(0, self._source_tooltip(case_dir, src))
            # A placeholder, so the row can be expanded before its file is read.
            child.addChild(QTreeWidgetItem())
            item.addChild(child)
            if any(s.case_dir == case_dir and s.key == src.key for s in self._series):
                self._fill_columns(child)
                child.setExpanded(True)
        item.setExpanded(True)
        return item

    def _source_tooltip(self, case_dir: str, src: Source) -> str:
        if src.kind == "residuals":
            what = tr("Initial residuals per time step, from the solver log {name}").format(
                name=src.key
            )
        elif src.kind == "profile":
            what = tr("Sampled line, written at {n} times: {first} … {last}").format(
                n=len(src.times), first=src.times[0], last=src.times[-1]
            )
        elif len(src.paths) > 1:
            what = tr("Time series in {n} restart segments, joined").format(n=len(src.paths))
        else:
            what = tr("Time series")
        files = "\n".join(
            os.path.relpath(p, case_dir) for p in self.source_files(case_dir, src.key)
        )
        return tr("{what}\nRead from:\n{files}").format(what=what, files=files)

    def data_set_time(self, case_dir: str, key: str) -> str | None:
        """The time a sampled line's data set is shown at now; None for the latest.

        The frame's, when the Time slider shows one (the latest at or before
        it); else the time chosen in Line Settings for a ticked column of
        it; else the latest. Open File, Save as CSV and the tooltips follow
        it, so they name what is on screen.
        """
        src = self._source(case_dir, key)
        if src is None or src.kind != "profile":
            return None
        frame = self.current_frame()
        if frame is not None:
            return latest_at(src.times, frame)
        return next(
            (s.time for s in self._series
             if s.case_dir == case_dir and s.key == key and s.time in src.times),
            None,
        )

    def source_files(self, case_dir: str, key: str) -> list[str]:
        """The files the data set *key* is plotted from now, in stitching order.

        A sampled line's file is the one of the time shown (data_set_time).
        """
        src = self._source(case_dir, key)
        if src is None:
            return []
        if src.kind == "profile":
            return [profile_path(src, self.data_set_time(case_dir, key))]
        return list(src.paths)

    # ── a data set as a table with headings ────────────────────────────────

    def _data_set_table(self, case_dir: str, key: str):
        """(source, table, time) for a data set as plotted, or None with a warning."""
        src = self._source(case_dir, key)
        if src is None:
            return None
        time = self.data_set_time(case_dir, key)
        try:
            table = load_source(src, time)
        except OSError as exc:
            QMessageBox.warning(
                self, tr("Cannot Read"), tr("Could not read {name}:\n{error}").format(
                    name=src.title, error=exc)
            )
            return None
        return src, table, time

    def copy_data_set(self, case_dir: str, key: str) -> None:
        """The whole data set on the clipboard, tab-separated, headings first."""
        got = self._data_set_table(case_dir, key)
        if got is not None:
            QGuiApplication.clipboard().setText(table_tsv(got[1]))

    def save_data_set_csv(self, case_dir: str, key: str) -> None:
        """Save a data set as ``<name>.csv`` plus ``<name>.source.txt``.

        The name offered is free (see services/plot_export.free_csv_path).
        The save dialog asks about the CSV it was given; the note is derived
        from that name, so it is checked here: one FoDE wrote is replaced
        with its CSV, anything else is asked about by name. Neither may land
        among the case's own files (services/plot_output.refusal).
        """
        got = self._data_set_table(case_dir, key)
        if got is None:
            return
        src, table, time = got
        chosen = self._ask_path(
            tr("Save Data as CSV"),
            free_csv_path(case_dir, default_stem(src, time)),
            f"{tr('CSV files')} (*.csv);;{tr('All files')} (*)",
        )
        if chosen is None:
            return
        path = chosen if chosen.lower().endswith(".csv") else chosen + ".csv"
        note = note_path(path)
        if self._refuse_unsafe(path, note) or not self._confirm_corrected(chosen, path):
            return
        if os.path.lexists(note) and not self._confirm_note(note, os.path.exists(path)):
            return
        from _version import get_version

        text = source_note(
            table, src, self.source_files(case_dir, key), time,
            os.path.basename(path), version=get_version(),
        )
        # The CSV last: a failure part-way leaves no table without its note.
        if self._write(note, text):
            self._write(path, table_csv(table))

    def _confirm_note(self, note: str, replacing_csv: bool) -> bool:
        """Ask before replacing an existing note, unless it is ours and goes with
        the CSV being replaced."""
        ours = is_our_note(note)
        if ours and replacing_csv:
            return True
        if ours:
            text = tr(
                "{path} already exists: the note of an earlier export.\n"
                "Replace it?"
            )
        else:
            text = tr(
                "{path} already exists, and FoDE did not write it.\n"
                "Replace it with this export's note?"
            )
        answer = QMessageBox.question(self, tr("Overwrite File?"), text.format(path=note))
        return answer == QMessageBox.StandardButton.Yes

    def open_data_file(self, path: str) -> DataFileViewer:
        """Show *path* read-only; a window already showing it is brought up."""
        # A closed viewer deletes itself (WA_DeleteOnClose).
        self._viewers = [v for v in self._viewers if isValid(v)]
        for viewer in self._viewers:
            if viewer.path == path:
                viewer.reload()
                viewer.show()
                viewer.raise_()
                viewer.activateWindow()
                return viewer
        viewer = DataFileViewer(path, self)
        self._viewers.append(viewer)
        viewer.show()
        return viewer

    def _top_items(self) -> list[QTreeWidgetItem]:
        items = (self.tree.topLevelItem(i) for i in range(self.tree.topLevelItemCount()))
        return [item for item in items if item is not None]

    def _mark_current_case(self) -> None:
        for item in self._top_items():
            font = item.font(0)
            font.setBold(item.data(0, _ROLE)[1] == self._current_case)
            item.setFont(0, font)

    def _source(self, case_dir: str, key: str) -> Source | None:
        return next((s for s in self._sources.get(case_dir, []) if s.key == key), None)

    def _fill_columns(self, item: QTreeWidgetItem) -> None:
        data = item.data(0, _ROLE)
        if not data or data[0] != "source":
            return
        if item.childCount() and item.child(0).data(0, _ROLE) is not None:
            return  # already filled
        _, case_dir, key = data
        src = self._source(case_dir, key)
        self._populating = True
        try:
            item.takeChildren()
            if src is None:
                return
            try:
                table = load_source(src)  # the columns, from the latest file
            except OSError as exc:
                bad = QTreeWidgetItem([tr("Cannot read: {error}").format(error=exc)])
                bad.setFlags(Qt.ItemFlag.NoItemFlags)
                item.addChild(bad)
                return
            names = [n for n in table.numeric_names() if table.names and n != table.names[0]]
            if not names:
                none = QTreeWidgetItem([tr("(no numeric columns)")])
                none.setFlags(Qt.ItemFlag.NoItemFlags)
                item.addChild(none)
            for name in names:
                col = QTreeWidgetItem([name])
                col.setData(0, _ROLE, ("column", case_dir, key, name))
                col.setFlags(col.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                ticked = any(
                    s.case_dir == case_dir and s.key == key and s.column == name
                    for s in self._series
                )
                col.setCheckState(0, Qt.CheckState.Checked if ticked else Qt.CheckState.Unchecked)
                item.addChild(col)
        finally:
            self._populating = False

    def _on_item_changed(self, item: QTreeWidgetItem, _column: int) -> None:
        if self._populating:
            return
        data = item.data(0, _ROLE)
        if not data or data[0] != "column":
            return
        _, case_dir, key, name = data
        self._set_ticked(case_dir, key, name, item.checkState(0) == Qt.CheckState.Checked)

    def _set_ticked(self, case_dir: str, key: str, name: str, ticked: bool) -> None:
        existing = [
            s for s in self._series
            if s.case_dir == case_dir and s.key == key and s.column == name
        ]
        if ticked and not existing:
            src = self._source(case_dir, key)
            if (src is not None and src.kind == "residuals" and not self._series
                    and not self.y_fields.log.isChecked()):
                # Residuals span decades; a linear axis shows only the first steps.
                self._set_log_automatically(True)
            self._series.append(Series(case_dir=case_dir, key=key, column=name))
        elif not ticked:
            for s in existing:
                self._series.remove(s)
        if self._auto_log and not self._only_residuals():
            self._set_log_automatically(False)
        self._schedule_replot()

    def _only_residuals(self) -> bool:
        kinds = {
            src.kind if (src := self._source(s.case_dir, s.key)) is not None else ""
            for s in self._series
        }
        return kinds == {"residuals"}

    def _set_log_automatically(self, on: bool) -> None:
        self._setting_log = True
        try:
            self.y_fields.log.setChecked(on)
        finally:
            self._setting_log = False
        self._auto_log = on

    def _on_y_log_toggled(self, _on: bool) -> None:
        if not self._setting_log:
            self._auto_log = False

    def tick(self, case_dir: str, key: str, column: str, ticked: bool = True) -> None:
        """Tick or untick a column, as a click on its box would."""
        item = self._column_item(case_dir, key, column)
        if item is None:
            return
        parent = item.parent()
        if ticked and parent is not None:
            parent.setExpanded(True)  # a tick made elsewhere should be visible
        item.setCheckState(0, Qt.CheckState.Checked if ticked else Qt.CheckState.Unchecked)

    def _case_item(self, case_dir: str) -> QTreeWidgetItem | None:
        for item in self._top_items():
            if item.data(0, _ROLE)[1] == case_dir:
                return item
        return None

    def _source_item(self, case_dir: str, key: str) -> QTreeWidgetItem | None:
        case_item = self._case_item(case_dir)
        if case_item is None:
            return None
        for i in range(case_item.childCount()):
            child = case_item.child(i)
            if child.data(0, _ROLE) == ("source", case_dir, key):
                return child
        return None

    def _column_item(self, case_dir: str, key: str, column: str) -> QTreeWidgetItem | None:
        src_item = self._source_item(case_dir, key)
        if src_item is None:
            return None
        self._fill_columns(src_item)
        for i in range(src_item.childCount()):
            child = src_item.child(i)
            if child.data(0, _ROLE) == ("column", case_dir, key, column):
                return child
        return None

    def _on_tree_menu(self, pos: QPoint) -> None:
        item = self.tree.itemAt(pos)
        data = item.data(0, _ROLE) if item is not None else None
        if not data or data[0] not in ("source", "column"):
            return
        if data[0] == "column":
            menu = self._build_column_menu(data[1], data[2], data[3])
        else:
            menu = self._build_source_menu(data[1], data[2])
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _build_column_menu(self, case_dir: str, key: str, column: str) -> QMenu:
        menu = QMenu(self)
        if self._find_series(case_dir, key, column) is not None:
            menu.addAction(tr("Line Settings…")).triggered.connect(
                lambda: self.edit_line(case_dir, key, column)
            )
            menu.addSeparator()
        tick_all = menu.addAction(tr("Plot This Column in Every Case"))
        tick_all.triggered.connect(lambda: self.tick_in_all_cases(key, column, True))
        untick_all = menu.addAction(tr("Remove This Column from Every Case"))
        untick_all.triggered.connect(lambda: self.tick_in_all_cases(key, column, False))
        menu.addSeparator()
        self._add_file_actions(menu, case_dir, key)
        return menu

    def _build_source_menu(self, case_dir: str, key: str) -> QMenu:
        menu = QMenu(self)
        self._add_file_actions(menu, case_dir, key)
        return menu

    def _add_file_actions(self, menu: QMenu, case_dir: str, key: str) -> None:
        """Save as CSV / Copy as Table, then Open File / Show in Folder (a
        submenu per file for a restarted series)."""
        files = self.source_files(case_dir, key)
        if not files:
            return
        menu.addAction(tr("Save as CSV…")).triggered.connect(
            lambda: self.save_data_set_csv(case_dir, key)
        )
        menu.addAction(tr("Copy as Table")).triggered.connect(
            lambda: self.copy_data_set(case_dir, key)
        )
        menu.addSeparator()
        if len(files) == 1:
            path = files[0]
            menu.addAction(tr("Open File")).triggered.connect(
                lambda: self.open_data_file(path)
            )
            menu.addAction(tr("Show in Folder")).triggered.connect(
                lambda: show_in_folder(path)
            )
            return
        # Parented explicitly: a submenu from addMenu(str) is not kept alive
        # by the menu holding it once its Python wrapper goes.
        open_menu = QMenu(tr("Open File"), menu)
        folder_menu = QMenu(tr("Show in Folder"), menu)
        menu.addMenu(open_menu)
        menu.addMenu(folder_menu)
        for path in files:
            rel = os.path.relpath(path, case_dir)
            open_menu.addAction(rel).triggered.connect(
                lambda _=False, p=path: self.open_data_file(p)
            )
            folder_menu.addAction(rel).triggered.connect(
                lambda _=False, p=path: show_in_folder(p)
            )

    def tick_in_all_cases(self, key: str, column: str, ticked: bool) -> None:
        """Tick *column* of the data set *key* in every case that has it."""
        for case_dir in self._cases:
            self.tick(case_dir, key, column, ticked)

    def _on_add_case(self) -> None:
        start = os.path.dirname(self._current_case) if self._current_case else ""
        path = QFileDialog.getExistingDirectory(self, tr("Add Case to Plot"), start)
        if not path:
            return
        path = os.path.normpath(path)
        if path in self._cases:
            return
        self._add_case(path)

    def _on_remove_case(self) -> None:
        item = self.tree.currentItem()
        while item is not None and item.parent() is not None:
            item = item.parent()
        if item is None:
            return
        case_dir = item.data(0, _ROLE)[1]
        self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(item))
        self._cases.remove(case_dir)
        self._sources.pop(case_dir, None)
        self._series = [s for s in self._series if s.case_dir != case_dir]
        self._update_hint()
        self._schedule_replot()

    def reload(self, keep_view: bool = False) -> None:
        """Find every case's data sets again and redraw from the files."""
        expanded = {
            child.data(0, _ROLE)
            for item in self._top_items()
            for child in (item.child(j) for j in range(item.childCount()))
            if child is not None and child.isExpanded()
        }
        self._populating = True
        try:
            self.tree.clear()
            for case_dir in self._cases:
                self._sources[case_dir] = find_sources(case_dir)
                case_item = self._add_case_item(case_dir)
                for j in range(case_item.childCount()):
                    child = case_item.child(j)
                    if child.data(0, _ROLE) in expanded:
                        self._fill_columns(child)
                        child.setExpanded(True)
        finally:
            self._populating = False
        self._mark_current_case()
        self.replot(keep_view=keep_view)

    # ── auto-refresh ────────────────────────────────────────────────────────

    def _on_auto_refresh_toggled(self, on: bool) -> None:
        if on:
            self._refresh_timer.start()
        else:
            self._refresh_timer.stop()
            self.refresh_label.setText("")

    def _ticked_files(self) -> list[str]:
        """Every file behind a ticked column, every segment and sampled time."""
        out: list[str] = []
        for s in self._series:
            src = self._source(s.case_dir, s.key)
            if src is not None:
                out += [p for p in src.paths if p not in out]
        return out

    def _signature(self, paths: list[str]) -> tuple:
        sig: list[tuple[str, int | None, int | None]] = []
        for p in paths:
            try:
                st = os.stat(p)
            except OSError:
                sig.append((p, None, None))
                continue
            sig.append((p, st.st_mtime_ns, st.st_size))
        return tuple(sig)

    def auto_refresh(self) -> bool:
        """One auto-refresh check; True when it redrew.

        Rescans the cases with ticked columns (a new output time, a restart
        segment), every so often all cases (a new data set for the tree),
        and redraws only when a plotted file or the data sets changed.
        Does nothing while the window is hidden or a mouse button is held:
        a legend drag or a zoom must not be redrawn from under the user.
        """
        if (not self.auto_refresh_check.isChecked() or not self.isVisible()
                or self.isMinimized()
                or QGuiApplication.mouseButtons() != Qt.MouseButton.NoButton):
            return False
        self._refresh_ticks += 1
        everything = self._refresh_ticks % _RESCAN_EVERY == 0
        cases = self._cases if everything else sorted({s.case_dir for s in self._series})
        sources_changed = tree_changed = False
        for case in cases:
            if not os.path.isdir(case):
                continue
            new = find_sources(case)
            old = self._sources.get(case, [])
            if [(s.key, s.paths) for s in new] != [(s.key, s.paths) for s in old]:
                sources_changed = True
                tree_changed |= {s.key for s in new} != {s.key for s in old}
                self._sources[case] = new
        signature = self._signature(self._ticked_files())
        files_changed = signature != self._file_signature
        self._file_signature = signature
        size = sum(entry[2] or 0 for entry in signature)
        self._refresh_timer.setInterval(_SLOW_REFRESH_MS if size > _LARGE_BYTES else _REFRESH_MS)
        if not (sources_changed or files_changed):
            return False
        if tree_changed:
            self.reload(keep_view=True)
        else:
            self.replot(keep_view=True)
        self.refresh_label.setText(
            tr("updated {time}").format(time=datetime.now().strftime("%H:%M:%S"))
        )
        return True

    # ── one line's settings ─────────────────────────────────────────────────

    def _find_series(self, case_dir: str, key: str, column: str) -> Series | None:
        return next(
            (s for s in self._series
             if s.case_dir == case_dir and s.key == key and s.column == column),
            None,
        )

    def line_settings_dialog(self, case_dir: str, key: str, column: str):
        """The Line Settings dialog for a ticked column, or None."""
        from ui.dialogs.line_settings_dialog import LineSettingsDialog

        series = self._find_series(case_dir, key, column)
        src = self._source(case_dir, key)
        if series is None or src is None:
            return None
        try:
            names = load_source(src, series.time).numeric_names()
        except OSError:
            names = []
        auto = ""
        if self._last_resolved is not None:
            auto = next((r.label for r in self._last_resolved.series if r.series == series
                         and not series.label), "")
        times = list(src.times) if src.kind == "profile" else None
        return LineSettingsDialog(series, names, auto or column, self, times)

    def edit_line(self, case_dir: str, key: str, column: str) -> None:
        """Line Settings…: legend text, x column and style of one ticked column."""
        dialog = self.line_settings_dialog(case_dir, key, column)
        series = self._find_series(case_dir, key, column)
        if dialog is None or series is None:
            return
        if dialog.exec() == QDialog.DialogCode.Accepted:
            dialog.apply_to(series)
            self._schedule_replot()
        dialog.deleteLater()

    # ── saved settings ──────────────────────────────────────────────────────

    def _on_save_settings(self) -> None:
        base = self._current_case or (self._cases[0] if self._cases else str(Path.home()))
        stem = Path(self._default_name()).name
        default = os.path.join(base, stem + ".plot.json")
        n = 2
        while os.path.lexists(default):
            default = os.path.join(base, f"{stem}_{n}.plot.json")
            n += 1
        chosen = self._ask_path(
            tr("Save Plot Settings"), default,
            f"{tr('Plot settings')} (*.plot.json *.json);;{tr('All files')} (*)",
        )
        if chosen is None:
            return
        path = chosen if chosen.endswith(".json") else chosen + ".plot.json"
        if self._refuse_unsafe(path) or not self._confirm_corrected(chosen, path):
            return
        self._write(path, spec_to_json(self.spec()))

    def _on_load_settings(self) -> None:
        start = self._current_case or (self._cases[0] if self._cases else "")
        path, _ = QFileDialog.getOpenFileName(
            self, tr("Load Plot Settings"), start,
            f"{tr('Plot settings')} (*.plot.json *.json);;{tr('All files')} (*)",
        )
        if path:
            self.load_settings(path)

    def load_settings(self, path: str) -> None:
        try:
            spec = spec_from_json(Path(path).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            QMessageBox.warning(
                self, tr("Cannot Load"),
                tr("Could not load plot settings from {path}:\n{error}").format(
                    path=path, error=exc),
            )
            return
        missing = self.apply_spec(spec)
        if missing:
            QMessageBox.information(
                self, tr("Plot Loaded"),
                tr("These lines were not found and are not plotted:\n{lines}").format(
                    lines="\n".join(missing)),
            )

    def apply_spec(self, spec: PlotSpec) -> list[str]:
        """Show *spec*: its cases, ticks, line settings and plot settings.

        Replaces what is ticked now. A case not in the window is added; one
        that no longer exists, a data set or a column it no longer has, is
        skipped and returned, as ``case: data set: column`` lines.
        """
        for s in list(self._series):
            self.tick(s.case_dir, s.key, s.column, False)
        missing: list[str] = []
        for want in spec.series:
            case = os.path.normpath(want.case_dir)
            where = f"{case_label(case)}: {want.key}: {want.column}"
            if not os.path.isdir(case):
                missing.append(where)
                continue
            if case not in self._cases:
                self._add_case(case)
            self.tick(case, want.key, want.column, True)
            got = self._find_series(case, want.key, want.column)
            if got is None:
                missing.append(where)
                continue
            for name in ("label", "x_column", "color", "linestyle", "marker", "linewidth"):
                setattr(got, name, getattr(want, name))
            got.time = want.time
        self.title_edit.setText(spec.title)
        self.x_fields.set_axis(spec.x)
        self._setting_log = True
        try:
            self.y_fields.set_axis(spec.y)
        finally:
            self._setting_log = False
        self._auto_log = False  # the file's choice, not an automatic one
        self.grid_check.setChecked(spec.grid)
        self.legend_check.setChecked(spec.legend)
        with QSignalBlocker(self.legend_combo):
            self.legend_combo.setCurrentIndex(max(self.legend_combo.findData(spec.legend_loc), 0))
        self._legend_at = spec.legend_at if spec.legend_loc == "custom" else None
        self.width_spin.setValue(spec.width)
        self.height_spin.setValue(spec.height)
        self.dpi_spin.setValue(spec.dpi)
        self.fps_spin.setValue(spec.fps)
        for spin, size in (
            (self.title_size_spin, spec.title_size),
            (self.label_size_spin, spec.label_size),
            (self.tick_size_spin, spec.tick_size),
            (self.legend_size_spin, spec.legend_size),
        ):
            spin.setValue(size or 0.0)
        self.replot()
        return missing

    # ── the plot ────────────────────────────────────────────────────────────

    def spec(self) -> PlotSpec:
        """The plot as the widgets describe it now."""
        return PlotSpec(
            series=[Series(**vars(s)) for s in self._series],
            title=self.title_edit.text(),
            x=self.x_fields.axis(),
            y=self.y_fields.axis(),
            grid=self.grid_check.isChecked(),
            legend=self.legend_check.isChecked(),
            legend_loc=self.legend_combo.currentData(),
            legend_at=self._legend_at,
            width=self.width_spin.value(),
            height=self.height_spin.value(),
            dpi=self.dpi_spin.value(),
            fps=self.fps_spin.value(),
            title_size=self.title_size_spin.value() or None,
            label_size=self.label_size_spin.value() or None,
            tick_size=self.tick_size_spin.value() or None,
            legend_size=self.legend_size_spin.value() or None,
        )

    def _schedule_replot(self, *_args) -> None:
        self._replot_timer.start()

    def replot(self, keep_view: bool = False) -> None:
        """Draw the plot again.

        *keep_view*: if the user zoomed or panned away from the limits FoDE
        last drew, put the view back where they left it (auto-refresh must
        not undo a zoom every few seconds).
        """
        self._replot_timer.stop()
        user_view = None
        if keep_view and self.figure.axes and self._drawn_limits is not None:
            ax = self.figure.axes[0]
            current = (ax.get_xlim(), ax.get_ylim())
            if current != self._drawn_limits:
                user_view = current
        self._update_frames(self.spec())
        spec, stamp = self.shown_spec()
        resolved = resolve(spec, self._sources)
        self._last_resolved = resolved
        try:
            draw(self.figure, spec, resolved, stamp)
        except ValueError as exc:
            # A log axis over only non-positive data, an inverted range, ...
            self.figure.clear()
            self.hint.setText(tr("Cannot draw this plot: {error}").format(error=exc))
            self.canvas.draw_idle()
            return
        legend = self.figure.axes[0].get_legend() if self.figure.axes else None
        if legend is not None:
            legend.set_draggable(True)
        if self.figure.axes:
            ax = self.figure.axes[0]
            self._drawn_limits = (ax.get_xlim(), ax.get_ylim())
            if user_view is not None:
                ax.set_xlim(*user_view[0])
                ax.set_ylim(*user_view[1])
        self.canvas.draw_idle()
        self._update_hint(resolved)
        self._refresh_tooltips()

    def _refresh_tooltips(self) -> None:
        """A sampled line's tooltip names the file shown, which moves with time."""
        for case_item in self._top_items():
            for i in range(case_item.childCount()):
                child = case_item.child(i)
                data = child.data(0, _ROLE)
                if not data or data[0] != "source":
                    continue
                src = self._source(data[1], data[2])
                if src is not None and src.kind == "profile":
                    child.setToolTip(0, self._source_tooltip(data[1], src))

    # ── animation ───────────────────────────────────────────────────────────

    def _update_frames(self, spec: PlotSpec) -> None:
        """Recompute the frames; keep the slider on the same time if it still exists."""
        frames = frame_times(spec, self._sources)
        current = self.current_frame()
        self._frames = frames
        self.time_row.setVisible(len(frames) > 1)
        with QSignalBlocker(self.time_slider):
            self.time_slider.setRange(0, len(frames) if len(frames) > 1 else 0)
            if current is not None:
                self.time_slider.setValue(frames.index(current) + 1 if current in frames else 0)
        self._update_frame_label()

    def shown_spec(self) -> tuple[PlotSpec, str]:
        """The plot as shown, and its time stamp ("" for the ordinary plot).

        On a frame of the Time slider, that frame -- fixed axes, pinned
        colours, the lines at the frame's time -- which is what Save Image,
        Copy Image, both scripts and Export Data write, so they match the
        view. Save Settings keeps :meth:`spec`, the plot as set up.
        """
        spec = self.spec()
        frame = self.current_frame()
        if frame is None:
            return spec, ""
        frames = frame_times(spec, self._sources)
        return (frame_spec(spec, frame, self._sources,
                           fixed_ranges(spec, frames, self._sources)),
                stamp_text(frame))

    def current_frame(self) -> str | None:
        """The frame's time shown, or None for the ordinary plot."""
        k = self.time_slider.value()
        return self._frames[k - 1] if 0 < k <= len(self._frames) else None

    def _update_frame_label(self) -> None:
        frame = self.current_frame()
        # Position 0: each sampled line at its latest time, or the one its
        # Line Settings chose.
        self.frame_label.setText(
            stamp_text(frame) if frame is not None
            else tr("Latest ({n} frames)").format(n=len(self._frames))
        )

    def _on_frame_changed(self, _value: int) -> None:
        self._update_frame_label()
        self.replot()

    def _on_play(self, playing: bool) -> None:
        self.play_btn.setText(tr("Stop") if playing else tr("Play"))
        if playing:
            # From the ordinary plot, or from the end: start at the first frame.
            if self.time_slider.value() in (0, self.time_slider.maximum()):
                self.time_slider.setValue(1)
            self._play_timer.start(round(1000 / self.fps_spin.value()))
        else:
            self._play_timer.stop()

    def _advance_frame(self) -> None:
        if self.time_slider.value() >= self.time_slider.maximum():
            self.play_btn.setChecked(False)
            return
        self.time_slider.setValue(self.time_slider.value() + 1)

    def _on_fps_changed(self, fps: float) -> None:
        if self._play_timer.isActive():
            self._play_timer.start(round(1000 / fps))

    def _on_save_animation(self) -> None:
        spec = self.spec()
        frames = frame_times(spec, self._sources)
        if len(frames) < 2:
            return
        self.play_btn.setChecked(False)
        base = self._current_case or (self._cases[0] if self._cases else str(Path.home()))
        stem = Path(self._default_name()).name
        default = os.path.join(base, stem + ".gif")
        n = 2
        while os.path.lexists(default):
            default = os.path.join(base, f"{stem}_{n}.gif")
            n += 1
        filters = [f"{tr('GIF animation')} (*.gif)"]
        if ffmpeg_available():
            filters.append(f"{tr('MP4 video')} (*.mp4)")
        filters.append(f"{tr('PNG frames, in a new folder')} (*.png)")
        chosen, chosen_filter = QFileDialog.getSaveFileName(
            self, tr("Save Animation"), default, ";;".join(filters)
        )
        if not chosen:
            return
        suffix = Path(chosen).suffix.lower().lstrip(".")
        if suffix not in FORMATS:
            suffix = "mp4" if "*.mp4" in chosen_filter else "png" if "*.png" in chosen_filter else "gif"
            chosen_corrected = chosen + "." + suffix
        else:
            chosen_corrected = chosen
        path = chosen_corrected
        if suffix == "mp4" and not ffmpeg_available():
            QMessageBox.warning(self, tr("Not Saved"), tr("MP4 needs ffmpeg, which is not installed."))
            return
        target = frames_directory(path) if suffix == "png" else path
        if self._refuse_unsafe(target):
            return
        if suffix == "png" and os.path.lexists(target):
            QMessageBox.warning(
                self, tr("Not Saved"),
                tr("{path} already exists. Choose another name: the frames go into a new folder."
                   ).format(path=target),
            )
            return
        if suffix != "png" and not self._confirm_corrected(chosen, path):
            return
        self.save_animation(path, suffix, spec, frames)

    def save_animation(self, path: str, fmt: str, spec: PlotSpec, frames: list[str]) -> str | None:
        """Draw every frame at the image size and write them; returns where, or None.

        A progress dialog with Cancel runs over the drawing; a cancelled or
        failed save leaves nothing behind (services/plot_animation).
        """
        from matplotlib.backends.backend_agg import FigureCanvasAgg

        ranges = fixed_ranges(spec, frames, self._sources)
        figure = Figure(figsize=(spec.width, spec.height), dpi=spec.dpi)
        canvas = FigureCanvasAgg(figure)
        progress = QProgressDialog(tr("Drawing frames…"), tr("Cancel"), 0, len(frames), self)
        progress.setWindowTitle(tr("Save Animation"))
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(300)
        try:
            writer = AnimationWriter(path, fmt, spec.fps)
        except OSError as exc:
            QMessageBox.warning(self, tr("Save Error"),
                                tr("Could not write {path}:\n{error}").format(path=path, error=exc))
            return None
        try:
            for i, frame in enumerate(frames):
                progress.setValue(i)
                if progress.wasCanceled():
                    writer.abort()
                    return None
                fspec = frame_spec(spec, frame, self._sources, ranges)
                draw(figure, fspec, resolve(fspec, self._sources), stamp_text(frame))
                canvas.draw()
                width, height = canvas.get_width_height()
                writer.add(bytes(canvas.buffer_rgba()), width, height)
            progress.setLabelText(tr("Writing the file…"))
            written = writer.finish()
        except (OSError, ValueError) as exc:
            writer.abort()
            QMessageBox.warning(self, tr("Save Error"),
                                tr("Could not write {path}:\n{error}").format(path=path, error=exc))
            return None
        finally:
            progress.setValue(len(frames))
            progress.close()
        return written

    def _update_hint(self, resolved: Resolved | None = None) -> None:
        has = bool(self._series)
        for b in (self.copy_btn, self.save_btn, self.export_btn, self.export_data_btn):
            b.setEnabled(has)
        if not self._cases:
            self.hint.setText(tr("Open a case, or add one with Add Case…"))
        elif not has:
            self.hint.setText(tr("Expand a data set and tick its columns to plot them."))
        elif resolved is not None and resolved.missing:
            names = ", ".join(f"{s.key}: {s.column}" for s, _ in resolved.missing)
            self.hint.setText(tr("No longer found, not drawn: {names}").format(names=names))
        else:
            self.hint.setText("")

    # ── the legend ──────────────────────────────────────────────────────────

    def _on_legend_location_chosen(self, _index: int) -> None:
        if self.legend_combo.currentData() != "custom":
            self._legend_at = None
        self._schedule_replot()

    def _legend_extent(self) -> tuple[float, float, float, float] | None:
        legend = self.figure.axes[0].get_legend() if self.figure.axes else None
        if legend is None:
            return None
        x0, y0, w, h = legend.get_window_extent().bounds
        return (x0, y0, w, h)

    def _on_canvas_press(self, event) -> None:
        legend = self.figure.axes[0].get_legend() if self.figure.axes else None
        hit = legend is not None and legend.contains(event)[0]
        self._legend_pressed = self._legend_extent() if hit else None

    def _on_canvas_release(self, _event) -> None:
        before, self._legend_pressed = self._legend_pressed, None
        after = self._legend_extent()
        if before is None or after is None:
            return
        if max(abs(a - b) for a, b in zip(before, after)) < 1.0:
            return  # a click, not a drag
        to_axes = self.figure.axes[0].transAxes.inverted()
        x0, y0 = to_axes.transform(after[:2])
        x1, y1 = to_axes.transform((after[0] + after[2], after[1] + after[3]))
        # Kept inside the axes: a legend dropped below or beside them makes
        # tight_layout shrink the plot to fit it in, which reads as the plot
        # collapsing. Outside right is the list's way to put it outside.
        x = min(max(x0, 0.0), max(1.0 - (x1 - x0), 0.0))
        y = min(max(y0, 0.0), max(1.0 - (y1 - y0), 0.0))
        self.set_legend_position(x, y)

    def set_legend_position(self, x: float, y: float) -> None:
        """Put the legend's lower-left corner at (*x*, *y*) in axes fractions."""
        self._legend_at = (float(x), float(y))
        with QSignalBlocker(self.legend_combo):
            self.legend_combo.setCurrentIndex(LEGEND_LOCATIONS.index("custom"))
        self._schedule_replot()

    # ── the preview ─────────────────────────────────────────────────────────

    def _on_image_size(self, *_args) -> None:
        self.preview.set_size_inches(self.width_spin.value(), self.height_spin.value())
        self._update_preview_label()

    def _on_fit_window(self, fit: bool) -> None:
        self.preview.set_fit_window(fit)
        self._update_preview_label()
        self._schedule_replot()

    def _update_preview_label(self) -> None:
        if self.preview.fit_window:
            self.preview_label.setText("")
            return
        # On screen, in physical pixels, against the saved image's pixels.
        shown = self.preview.pixels_per_inch * self.canvas.device_pixel_ratio
        self.preview_label.setText(tr("Preview at {percent} %").format(
            percent=round(100 * shown / self.dpi_spin.value())))

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        self._update_preview_label()

    def _on_use_view(self) -> None:
        if not self.figure.axes:
            return
        ax = self.figure.axes[0]
        self.x_fields.set_range(*ax.get_xlim())
        self.y_fields.set_range(*ax.get_ylim())

    def _on_auto_ranges(self) -> None:
        self.x_fields.set_range(None, None)
        self.y_fields.set_range(None, None)

    # ── output ──────────────────────────────────────────────────────────────

    def render_image(self, fmt: str = "png") -> bytes:
        """The plot as shown, at the spec's size and resolution, as *fmt* bytes."""
        spec, stamp = self.shown_spec()
        resolved = resolve(spec, self._sources)
        fig = Figure(figsize=(spec.width, spec.height))
        draw(fig, spec, resolved, stamp)
        buf = io.BytesIO()
        fig.savefig(buf, format=fmt, dpi=spec.dpi)
        return buf.getvalue()

    def copy_image(self) -> None:
        image = QImage.fromData(self.render_image("png"))
        QGuiApplication.clipboard().setImage(image)

    def _default_name(self) -> str:
        base = self._current_case or (self._cases[0] if self._cases else str(Path.home()))
        # The title as a file name: words kept (Japanese included), spaces and
        # punctuation such as "=" and "/" made underscores -- "Velocity at
        # x = 0.1 m" gives Velocity_at_x_0.1_m, not a name to quote in a shell.
        stem = re.sub(r"[^\w.-]+", "_", self.title_edit.text()).strip("_.") or "plot"
        return os.path.join(base, stem)

    def _ask_path(self, title: str, default: str, file_filter: str) -> str | None:
        path, _ = QFileDialog.getSaveFileName(self, title, default, file_filter)
        return path or None

    def _confirm_corrected(self, chosen: str, path: str) -> bool:
        """The dialog checked *chosen* for a clash, not the corrected *path*."""
        if path == chosen or not Path(path).exists():
            return True
        answer = QMessageBox.question(
            self,
            tr("Overwrite File?"),
            tr("{path} already exists.\nReplace it?").format(path=path),
        )
        return answer == QMessageBox.StandardButton.Yes

    def _plotted_files(self) -> frozenset[str]:
        """Every file any data set in the window reads: never written over."""
        return frozenset(
            p for sources in self._sources.values() for src in sources for p in src.paths
        )

    def _refuse_unsafe(self, *paths: str) -> bool:
        """Say why and return True when any of *paths* is case data (see services/plot_output)."""
        protected = self._plotted_files()
        for path in paths:
            code = refusal(path, protected, tuple(self._cases))
            if code is None:
                continue
            if code == "protected":
                why = tr("{path} is one of the data files this window plots.")
            elif code == "case_dir":
                why = tr(
                    "{path} is inside a directory of the case that OpenFOAM reads or "
                    "writes (system, constant, postProcessing, a time or processor "
                    "directory)."
                )
            else:
                why = tr("{path} is a log, script or other file of the case's own.")
            QMessageBox.warning(
                self,
                tr("Not Saved"),
                why.format(path=path)
                + "\n\n"
                + tr(
                    "Plot Results does not write among a case's files. Save at the "
                    "case's top level, in a folder of your own, or outside the case."
                ),
            )
            return True
        return False

    def _write(self, path: str, data: bytes | str) -> bool:
        try:
            write_atomically(path, data)
        except OSError as exc:
            QMessageBox.warning(
                self,
                tr("Save Error"),
                tr("Could not write {path}:\n{error}").format(path=path, error=exc),
            )
            return False
        return True

    def _on_save_image(self) -> None:
        patterns = " ".join("*" + s for s in _IMAGE_SUFFIXES)
        chosen = self._ask_path(
            tr("Save Plot as Image"),
            self._default_name() + ".png",
            f"{tr('Image files - PNG, SVG, PDF, JPEG, EPS, TIFF')} ({patterns});;"
            f"{tr('All files')} (*)",
        )
        if chosen is None:
            return
        path = writable_plot_path(chosen)
        if self._refuse_unsafe(path) or not self._confirm_corrected(chosen, path):
            return
        fmt = Path(path).suffix.lstrip(".")
        try:
            data = self.render_image(fmt)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(
                self,
                tr("Save Image Error"),
                tr("Could not save the image:\n{error}").format(error=exc),
            )
            return
        self._write(path, data)

    def _resolved_for_export(self) -> tuple[PlotSpec, Resolved, str]:
        """The plot as shown (see shown_spec), resolved, and its stamp."""
        spec, stamp = self.shown_spec()
        return spec, resolve(spec, self._sources), stamp

    def _on_export_python(self) -> None:
        chosen = self._ask_path(
            tr("Export Python Script"),
            self._default_name() + ".py",
            f"{tr('Python scripts')} (*.py);;{tr('All files')} (*)",
        )
        if chosen is None:
            return
        path = chosen if chosen.endswith(".py") else chosen + ".py"
        if self._refuse_unsafe(path) or not self._confirm_corrected(chosen, path):
            return
        spec, resolved, stamp = self._resolved_for_export()
        try:
            script = python_script(spec, resolved, font_family(spec, resolved), stamp)
        except OSError as exc:
            # The reader's source is missing: a frozen build packaged without it.
            QMessageBox.warning(
                self,
                tr("Save Error"),
                tr("Could not write {path}:\n{error}").format(path=path, error=exc),
            )
            return
        if self._write(path, script):
            os.chmod(path, 0o755)

    def plotted_lines(self) -> list[PlottedLine]:
        """Every line drawn now, with its full table (gaps kept, unlike the plot)."""
        spec, resolved, _stamp = self._resolved_for_export()
        out = []
        for r in resolved.series:
            s = r.series
            src = self._source(s.case_dir, s.key)
            if src is None:
                continue
            try:
                table = load_source(src, s.time)
            except OSError:
                continue
            out.append(PlottedLine(
                label=r.label, source=src, table=table, column=s.column,
                time=s.time if src.kind == "profile" else None, files=r.files,
                x_column=r.x_name,
            ))
        return out

    def _on_export_data(self) -> None:
        """The plotted lines as one CSV plus its ``.source.txt``.

        Same checks as Save as CSV: a free name offered, the case's own
        directories refused, an existing note asked about unless it is ours
        and goes with the CSV being replaced.
        """
        lines = self.plotted_lines()
        if not lines:
            return
        base = self._current_case or os.path.dirname(lines[0].source.case_dir)
        stem = Path(self._default_name()).name
        stem = "plot_data" if stem == "plot" else stem
        chosen = self._ask_path(
            tr("Export Plotted Data"),
            free_csv_path(base, stem),
            f"{tr('CSV files')} (*.csv);;{tr('All files')} (*)",
        )
        if chosen is None:
            return
        path = chosen if chosen.lower().endswith(".csv") else chosen + ".csv"
        note = note_path(path)
        if self._refuse_unsafe(path, note) or not self._confirm_corrected(chosen, path):
            return
        if os.path.lexists(note) and not self._confirm_note(note, os.path.exists(path)):
            return
        from _version import get_version

        table, shared = plotted_table(lines)
        text = plotted_note(lines, shared, os.path.basename(path), version=get_version())
        if self._write(note, text):
            self._write(path, table_csv(table))

    def _on_export_gnuplot(self) -> None:
        chosen = self._ask_path(
            tr("Export gnuplot Script"),
            self._default_name() + ".gp",
            f"{tr('gnuplot scripts')} (*.gp *.plt);;{tr('All files')} (*)",
        )
        if chosen is None:
            return
        path = chosen if chosen.endswith((".gp", ".plt")) else chosen + ".gp"
        data_path = str(Path(path).with_suffix(".dat"))
        if self._refuse_unsafe(path, data_path) or not self._confirm_corrected(chosen, path):
            return
        if Path(data_path).exists() and not self._confirm_corrected("", data_path):
            return
        spec, resolved, stamp = self._resolved_for_export()
        if self._write(data_path, gnuplot_data(resolved)):
            self._write(path, gnuplot_script(spec, resolved, Path(data_path).name, stamp))
