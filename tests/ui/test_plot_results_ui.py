# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tools > Plot Results…: the window and its main-window wiring.

The reader, the spec and the script export are tests/services/test_plot_data.py
and tests/services/test_plot_script.py.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtWidgets import QMessageBox  # noqa: E402

from services.plot_spec import spec_from_json  # noqa: E402
from ui.dialogs.plot_results_dialog import PlotResultsDialog, writable_plot_path  # noqa: E402

PROBE = "postProcessing/probes/p"
GRAPH = "postProcessing/graph/line_p.xy"


def _case(root: Path, name: str, scale: float = 1.0) -> Path:
    case = root / name
    probes = case / "postProcessing" / "probes" / "0"
    probes.mkdir(parents=True)
    (probes / "p").write_text(
        "# Probe 0 (0 0 0)\n# Time 0\n" + "".join(f"{t} {scale * t}\n" for t in (1, 2, 3))
    )
    for t in ("0.1", "0.2"):
        d = case / "postProcessing" / "graph" / t
        d.mkdir(parents=True)
        (d / "line_p.xy").write_text(f"0 {t}\n1 {t}\n")
    (case / "log.simpleFoam").write_text(
        "Time = 1\nGAMG:  Solving for p, Initial residual = 1, Final\n"
        "Time = 2\nGAMG:  Solving for p, Initial residual = 0.01, Final\n"
    )
    return case


@pytest.fixture
def dialog(tmp_path, destroy_widget):
    dlg = PlotResultsDialog(str(_case(tmp_path, "caseA")))
    yield dlg
    destroy_widget(dlg)


def _lines(dlg: PlotResultsDialog):
    dlg.replot()
    return dlg.figure.axes[0].lines


def test_lists_the_cases_data_sets(dialog):
    case_item = dialog.tree.topLevelItem(0)
    assert case_item.text(0) == "caseA"
    titles = [case_item.child(i).text(0) for i in range(case_item.childCount())]
    assert titles == ["graph/line_p.xy", "probes/p", "log.simpleFoam"]


def test_ticking_a_column_plots_it(dialog):
    case = dialog.cases[0]
    dialog.tick(case, PROBE, "probe0")
    lines = _lines(dialog)
    assert len(lines) == 1
    assert list(lines[0].get_ydata()) == [1.0, 2.0, 3.0]
    assert dialog.copy_btn.isEnabled()
    dialog.tick(case, PROBE, "probe0", False)
    assert len(_lines(dialog)) == 0
    assert not dialog.copy_btn.isEnabled()


def test_residuals_switch_the_y_axis_to_log(dialog):
    dialog.tick(dialog.cases[0], "log.simpleFoam", "p")
    dialog.replot()
    assert dialog.y_fields.log.isChecked()
    assert dialog.figure.axes[0].get_yscale() == "log"


def test_the_automatic_log_axis_goes_when_the_residuals_do(dialog):
    case = dialog.cases[0]
    dialog.tick(case, "log.simpleFoam", "p")
    assert dialog.y_fields.log.isChecked()
    # Unticked, then a profile ticked: a linear axis again, or a velocity
    # profile going negative would lose half of itself.
    dialog.tick(case, "log.simpleFoam", "p", False)
    assert not dialog.y_fields.log.isChecked()
    dialog.tick(case, "log.simpleFoam", "p")
    dialog.tick(case, GRAPH, "p")  # mixed: no longer residuals only
    assert not dialog.y_fields.log.isChecked()


def test_a_log_axis_set_by_hand_stays(dialog):
    case = dialog.cases[0]
    dialog.tick(case, "log.simpleFoam", "p")
    dialog.y_fields.log.setChecked(False)
    dialog.y_fields.log.setChecked(True)  # the user's choice now
    dialog.tick(case, "log.simpleFoam", "p", False)
    assert dialog.y_fields.log.isChecked()


def test_the_default_file_name_comes_from_the_title(dialog):
    dialog.title_edit.setText("Velocity at x = 0.1 m / 速度")
    assert Path(dialog._default_name()).name == "Velocity_at_x_0.1_m_速度"
    dialog.title_edit.setText(" = ")
    assert Path(dialog._default_name()).name == "plot"


def test_comparing_cases(dialog, tmp_path):
    other = _case(tmp_path, "caseB", scale=2.0)
    dialog.set_case_dir(str(other))
    assert [Path(c).name for c in dialog.cases] == ["caseA", "caseB"]
    # The newly opened case is the current one, in bold.
    assert dialog.tree.topLevelItem(1).font(0).bold()
    assert not dialog.tree.topLevelItem(0).font(0).bold()

    dialog.tick_in_all_cases(PROBE, "probe0", True)
    assert dialog._source_item(str(other), PROBE).isExpanded()
    lines = _lines(dialog)
    # The same column in two cases: the case is what tells the lines apart.
    assert [ln.get_label() for ln in lines] == ["caseA", "caseB"]
    assert dialog.figure.axes[0].get_ylabel() == "probe0"
    assert list(lines[1].get_ydata()) == [2.0, 4.0, 6.0]

    # Removing a case removes its lines.
    dialog.tree.setCurrentItem(dialog.tree.topLevelItem(1))
    dialog._on_remove_case()
    assert [Path(c).name for c in dialog.cases] == ["caseA"]
    assert len(_lines(dialog)) == 1


def test_a_lines_sample_time_is_chosen_in_line_settings(dialog):
    case = dialog.cases[0]
    dialog.tick(case, GRAPH, "p")
    assert list(_lines(dialog)[0].get_ydata()) == [0.2, 0.2]  # latest by default
    line_dialog = dialog.line_settings_dialog(case, GRAPH, "p")
    try:
        combo = line_dialog.time_combo
        assert [combo.itemText(i) for i in range(combo.count())] == ["Latest (0.2)", "0.2", "0.1"]
        combo.setCurrentIndex(2)
        line_dialog.apply_to(dialog._find_series(case, GRAPH, "p"))
    finally:
        line_dialog.deleteLater()
    assert list(_lines(dialog)[0].get_ydata()) == [0.1, 0.1]
    assert dialog.spec().series[0].time == "0.1"
    # The data set's file follows: Open File and Save as CSV name the shown one.
    assert dialog.source_files(case, GRAPH)[0].endswith("0.1/line_p.xy")
    # A time series has no sample time to choose.
    dialog.tick(case, PROBE, "probe0")
    line_dialog = dialog.line_settings_dialog(case, PROBE, "probe0")
    try:
        assert line_dialog.time_combo is None
    finally:
        line_dialog.deleteLater()


def test_settings_reach_the_plot(dialog):
    dialog.tick(dialog.cases[0], PROBE, "probe0")
    dialog.title_edit.setText("Pressure")
    dialog.x_fields.label.setText("t")
    dialog.x_fields.min.setText("1.5")
    dialog.x_fields.max.setText("not a number")
    dialog.y_fields.step.setText("0.5")
    dialog.grid_check.setChecked(False)
    dialog.replot()
    ax = dialog.figure.axes[0]
    assert ax.get_title() == "Pressure"
    assert ax.get_xlabel() == "t"
    assert ax.get_xlim()[0] == 1.5
    spec = dialog.spec()
    assert spec.x.max is None and spec.y.step == 0.5 and not spec.grid


def test_swap_x_and_y(dialog, tmp_path):
    case = str(_case(tmp_path, "scaled", scale=10.0))
    dialog.set_case_dir(case)
    dialog.tick(case, PROBE, "probe0")
    dialog.x_fields.min.setText("1.5")  # a Time range
    dialog.swap_check.setChecked(True)
    line = _lines(dialog)[0]
    assert list(line.get_xdata()) == [10.0, 20.0, 30.0]  # probe0 along x
    assert list(line.get_ydata()) == [1.0, 2.0, 3.0]  # Time along y
    ax = dialog.figure.axes[0]
    assert (ax.get_xlabel(), ax.get_ylabel()) == ("probe0", "Time")
    # The range moved with its quantity to the Y axis row.
    assert dialog.x_fields.min.text() == "" and dialog.y_fields.min.text() == "1.5"
    assert dialog.spec().swap_axes
    dialog.swap_check.setChecked(False)
    assert dialog.x_fields.min.text() == "1.5" and not dialog.spec().swap_axes


def test_legend_position_choice(dialog):
    dialog.tick(dialog.cases[0], PROBE, "probe0")
    dialog.legend_combo.setCurrentIndex(dialog.legend_combo.findData("lower left"))
    dialog.replot()
    assert dialog.spec().legend_loc == "lower left"
    assert dialog.figure.axes[0].get_legend()._loc == 3  # matplotlib's code for it
    dialog.legend_check.setChecked(False)
    assert not dialog.legend_combo.isEnabled()


def test_dragging_the_legend_keeps_it_there(dialog):
    from matplotlib.backend_bases import MouseEvent

    dialog.resize(900, 700)
    dialog.tick(dialog.cases[0], PROBE, "probe0")
    dialog.replot()
    canvas = dialog.canvas
    canvas.draw()
    box = dialog.figure.axes[0].get_legend().get_window_extent()
    x, y = box.x0 + box.width / 2, box.y0 + box.height / 2
    MouseEvent("button_press_event", canvas, x, y, button=1)._process()
    MouseEvent("motion_notify_event", canvas, x + 40, y - 60, button=1)._process()
    MouseEvent("button_release_event", canvas, x + 40, y - 60, button=1)._process()
    spec = dialog.spec()
    assert spec.legend_loc == "custom" and spec.legend_at is not None
    # Redrawn from the spec, it is where it was dropped.
    dialog.replot()
    canvas.draw()
    moved = dialog.figure.axes[0].get_legend().get_window_extent()
    assert moved.x0 == pytest.approx(box.x0 + 40, abs=1)
    assert moved.y0 == pytest.approx(box.y0 - 60, abs=1)
    # Dropped below the axes, it is kept inside them.
    canvas.draw()
    box = dialog.figure.axes[0].get_legend().get_window_extent()
    x, y = box.x0 + box.width / 2, box.y0 + box.height / 2
    MouseEvent("button_press_event", canvas, x, y, button=1)._process()
    MouseEvent("motion_notify_event", canvas, x, y - 2000, button=1)._process()
    MouseEvent("button_release_event", canvas, x, y - 2000, button=1)._process()
    assert dialog.spec().legend_at[1] == 0.0
    # Choosing a position again forgets the dragged one.
    dialog.legend_combo.setCurrentIndex(dialog.legend_combo.findData("best"))
    assert dialog.spec().legend_at is None


def test_font_sizes_reach_the_plot(dialog):
    dialog.tick(dialog.cases[0], PROBE, "probe0")
    dialog.title_edit.setText("Sized")
    dialog.title_size_spin.setValue(20)
    dialog.tick_size_spin.setValue(6)
    dialog.replot()
    ax = dialog.figure.axes[0]
    assert ax.title.get_fontsize() == 20
    assert ax.get_xticklabels()[0].get_fontsize() == 6
    default = ax.xaxis.label.get_fontsize()  # untouched: matplotlib's own size
    assert dialog.spec().label_size is None and default > 0


def test_stepping_a_font_size_starts_at_its_real_default(dialog):
    from services.plot_render import default_font_sizes

    defaults = default_font_sizes()
    title, labels = dialog.title_size_spin, dialog.label_size_spin
    assert title.value() == 0 and title.text() == f"Default ({defaults['title']:g} pt)"
    # Up from Default: one point above matplotlib's own size, not 1 pt.
    title.stepUp()
    assert title.value() == defaults["title"] + 1
    title.stepUp()
    assert title.value() == defaults["title"] + 2
    # Down from Default works too, though Default is the box's minimum.
    assert labels.stepEnabled() & labels.StepEnabledFlag.StepDownEnabled
    labels.stepDown()
    assert labels.value() == defaults["label"] - 1
    # And the spec carries what is shown.
    assert dialog.spec().title_size == defaults["title"] + 2


def _layout(fig):
    """What the saved image and the preview must agree on, figure-relative."""
    ax = fig.axes[0]
    legend = ax.get_legend()
    renderer = fig.canvas.get_renderer()
    box = legend.get_window_extent(renderer)
    width, height = fig.bbox.width, fig.bbox.height
    return {
        "inches": tuple(round(v, 2) for v in fig.get_size_inches()),
        "axes": tuple(round(v, 3) for v in ax.get_position().bounds),
        "xticks": list(ax.get_xticks()),
        "yticks": list(ax.get_yticks()),
        "legend": tuple(round(v, 2) for v in (box.x0 / width, box.y0 / height,
                                               box.width / width, box.height / height)),
    }


def test_the_view_previews_the_saved_image(dialog):
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    from services.plot_render import draw
    from services.plot_spec import resolve

    dialog.resize(1100, 700)
    dialog.show()
    QGuiApplication.processEvents()
    dialog.tick(dialog.cases[0], PROBE, "probe0")
    dialog.title_edit.setText("Preview")
    dialog.title_size_spin.setValue(20)
    dialog.width_spin.setValue(4.0)
    dialog.height_spin.setValue(4.0)
    QGuiApplication.processEvents()
    dialog.replot()
    dialog.canvas.draw()
    # The canvas takes the image's shape, centred in the space it has.
    canvas, area = dialog.canvas, dialog.preview
    assert abs(canvas.width() - canvas.height()) <= 1
    assert canvas.height() == area.height() or canvas.width() == area.width()

    spec = dialog.spec()
    saved = Figure(figsize=(spec.width, spec.height), dpi=spec.dpi)
    FigureCanvasAgg(saved)
    draw(saved, spec, resolve(spec))
    saved.canvas.draw()
    # Text is measured at the resolution it is drawn at, and glyph widths
    # round to whole pixels: the preview's tight layout agrees with the file's
    # to within about a percent of the figure, not exactly.
    view, file = _layout(dialog.figure), _layout(saved)
    assert view["inches"] == file["inches"]
    assert view["xticks"] == file["xticks"] and view["yticks"] == file["yticks"]
    for key in ("axes", "legend"):
        assert view[key] == pytest.approx(file[key], abs=0.015), key
    assert dialog.preview_label.text().startswith("Preview at ")

    # Fit to window: the canvas fills the space again, at its own dpi.
    dialog.fit_window_check.setChecked(True)
    QGuiApplication.processEvents()
    assert canvas.geometry() == area.rect()
    assert dialog.preview_label.text() == ""
    dialog.fit_window_check.setChecked(False)
    dialog.width_spin.setValue(8.0)
    QGuiApplication.processEvents()
    assert canvas.width() > canvas.height()


def test_use_current_view_and_automatic_ranges(dialog):
    dialog.tick(dialog.cases[0], PROBE, "probe0")
    dialog.replot()
    dialog.figure.axes[0].set_xlim(1.25, 2.5)
    dialog._on_use_view()
    assert dialog.spec().x.min == 1.25 and dialog.spec().x.max == 2.5
    dialog._on_auto_ranges()
    assert dialog.spec().x.min is None and dialog.spec().y.max is None


def test_copy_image_puts_an_image_on_the_clipboard(dialog):
    dialog.tick(dialog.cases[0], PROBE, "probe0")
    dialog.width_spin.setValue(4.0)
    dialog.height_spin.setValue(2.0)
    dialog.dpi_spin.setValue(50)
    dialog.copy_image()
    image = QGuiApplication.clipboard().image()
    assert (image.width(), image.height()) == (200, 100)


def test_save_image_and_export_scripts(dialog, tmp_path, monkeypatch):
    dialog.tick(dialog.cases[0], PROBE, "probe0")
    answers = iter([
        str(tmp_path / "out" / "plot.SVG"),
        str(tmp_path / "out" / "plot"),
        str(tmp_path / "out" / "plot.gp"),
    ])
    (tmp_path / "out").mkdir()
    monkeypatch.setattr(
        "ui.dialogs.plot_results_dialog.QFileDialog.getSaveFileName",
        lambda *a, **k: (next(answers), ""),
    )
    dialog._on_save_image()
    assert (tmp_path / "out" / "plot.svg").read_text().lstrip().startswith("<?xml")
    dialog._on_export_python()
    script = tmp_path / "out" / "plot.py"
    assert "def draw(fig):" in script.read_text()
    assert script.stat().st_mode & 0o111
    dialog._on_export_gnuplot()
    assert (tmp_path / "out" / "plot.dat").exists()
    assert "datafile = 'plot.dat'" in (tmp_path / "out" / "plot.gp").read_text()


def test_a_corrected_name_that_exists_asks_first(dialog, tmp_path, monkeypatch, answer_message_box):
    dialog.tick(dialog.cases[0], PROBE, "probe0")
    existing = tmp_path / "plot.txt.png"
    existing.write_text("keep me")
    monkeypatch.setattr(
        "ui.dialogs.plot_results_dialog.QFileDialog.getSaveFileName",
        lambda *a, **k: (str(tmp_path / "plot.txt"), ""),
    )
    asked = answer_message_box(QMessageBox.StandardButton.No)
    dialog._on_save_image()
    assert existing.read_text() == "keep me"
    assert asked and str(existing) in asked[0]


def test_exports_refuse_to_write_among_the_cases_files(dialog, monkeypatch, answer_message_box):
    case = Path(dialog.cases[0])
    (case / "system").mkdir()
    dialog.tick(str(case), PROBE, "probe0")
    data = case / "postProcessing" / "probes" / "0" / "p"
    before = data.read_text()
    # A gnuplot script beside the data names its snapshot p.dat; the script
    # itself would land in postProcessing/, which the next scan would list.
    monkeypatch.setattr(
        "ui.dialogs.plot_results_dialog.QFileDialog.getSaveFileName",
        lambda *a, **k: (str(data.with_suffix(".gp")), ""),
    )
    warned = answer_message_box(QMessageBox.StandardButton.Ok)
    dialog._on_export_gnuplot()
    assert warned and "postProcessing" in warned[0]
    assert sorted(p.name for p in data.parent.iterdir()) == ["p"]
    assert data.read_text() == before
    # The run's log at the case root is not replaced either, even when asked.
    log = case / "log.simpleFoam"
    monkeypatch.setattr(
        "ui.dialogs.plot_results_dialog.QFileDialog.getSaveFileName",
        lambda *a, **k: (str(log) + ".py", ""),
    )
    dialog._on_export_python()  # log.simpleFoam.py: a new file, allowed
    assert (case / "log.simpleFoam.py").exists()
    monkeypatch.setattr(dialog, "_ask_path", lambda *a: str(log))
    monkeypatch.setattr("ui.dialogs.plot_results_dialog.writable_plot_path", lambda p: p)
    dialog._on_save_image()
    assert log.read_text().startswith("Time = 1")


def test_reload_picks_up_new_data_and_keeps_ticks(dialog):
    case = Path(dialog.cases[0])
    dialog.tick(str(case), PROBE, "probe0")
    with open(case / "postProcessing" / "probes" / "0" / "p", "a") as fh:
        fh.write("4 4\n")
    (case / "postProcessing" / "new" / "0").mkdir(parents=True)
    (case / "postProcessing" / "new" / "0" / "a.dat").write_text("# Time a\n1 2\n")
    dialog.reload()
    assert list(dialog.figure.axes[0].lines[0].get_ydata()) == [1.0, 2.0, 3.0, 4.0]
    item = dialog._column_item(str(case), PROBE, "probe0")
    assert item is not None and item.checkState(0) == Qt.CheckState.Checked
    assert dialog._source_item(str(case), "postProcessing/new/a.dat") is not None


def _actions(menu):
    return {a.text(): a for a in menu.actions() if a.text()}


def test_data_set_tooltip_names_its_files(dialog):
    case = dialog.cases[0]
    probe = dialog._source_item(case, PROBE)
    assert "postProcessing/probes/0/p" in probe.toolTip(0)
    graph = dialog._source_item(case, GRAPH)
    assert "graph/0.2/line_p.xy" in graph.toolTip(0)
    dialog.tick(case, GRAPH, "p")
    dialog._find_series(case, GRAPH, "p").time = "0.1"
    dialog.replot()
    assert "graph/0.1/line_p.xy" in graph.toolTip(0)


def test_open_file_shows_the_data_read_only(dialog, destroy_widget):
    case = dialog.cases[0]
    actions = _actions(dialog._build_source_menu(case, PROBE))
    assert {"Open File", "Show in Folder", "Save as CSV…", "Copy as Table"} == set(actions)
    actions["Open File"].trigger()
    viewer = dialog._viewers[0]
    try:
        assert viewer.path == str(Path(case) / "postProcessing/probes/0/p")
        assert viewer.text.isReadOnly()
        assert viewer.text.toPlainText().startswith("# Probe 0 (0 0 0)")
        # Opening it again brings up the same window, re-read.
        with open(viewer.path, "a") as fh:
            fh.write("4 4\n")
        assert dialog.open_data_file(viewer.path) is viewer
        assert viewer.text.toPlainText().endswith("4 4\n")
        # A column's menu offers the same, after its own entries.
        column_menu = _actions(dialog._build_column_menu(case, PROBE, "probe0"))
        assert {"Open File", "Show in Folder"} <= set(column_menu)
    finally:
        destroy_widget(viewer)


def test_a_restarted_series_offers_each_file(dialog, monkeypatch):
    case = Path(dialog.cases[0])
    later = case / "postProcessing" / "probes" / "2"
    later.mkdir()
    (later / "p").write_text("# Probe 0 (0 0 0)\n# Time 0\n2 5\n3 6\n")
    dialog.reload()
    menu = dialog._build_source_menu(str(case), PROBE)
    submenus = {a.text(): a.menu() for a in menu.actions()}
    assert [a.text() for a in submenus["Open File"].actions()] == [
        "postProcessing/probes/0/p", "postProcessing/probes/2/p",
    ]
    opened = []
    monkeypatch.setattr(
        "ui.dialogs.data_file_viewer.QDesktopServices.openUrl",
        lambda url: opened.append(url.toLocalFile()),
    )
    submenus["Show in Folder"].actions()[1].trigger()
    assert opened == [str(later)]


def test_save_as_csv_writes_the_table_and_its_note(dialog, tmp_path, monkeypatch):
    case = dialog.cases[0]
    offered = []

    def ask(*a, **k):
        offered.append(a[2])
        return (str(tmp_path / "out" / "probe"), "")

    (tmp_path / "out").mkdir()
    monkeypatch.setattr("ui.dialogs.plot_results_dialog.QFileDialog.getSaveFileName", ask)
    assert {"Save as CSV…", "Copy as Table"} <= set(_actions(dialog._build_source_menu(case, PROBE)))
    dialog.save_data_set_csv(case, PROBE)
    assert offered == [str(Path(case) / "probes_p.csv")]
    assert (tmp_path / "out/probe.csv").read_text().splitlines()[:2] == ["Time,probe0", "1,1"]
    assert "probes/0/p" in (tmp_path / "out/probe.source.txt").read_text()


def test_an_existing_note_is_asked_about_unless_it_goes_with_the_csv(
    dialog, tmp_path, monkeypatch, answer_message_box
):
    case = dialog.cases[0]
    monkeypatch.setattr(
        "ui.dialogs.plot_results_dialog.QFileDialog.getSaveFileName",
        lambda *a, **k: (str(tmp_path / "probe.csv"), ""),
    )
    # Someone else's file where the note would go: asked, and No keeps it.
    (tmp_path / "probe.source.txt").write_text("my own notes\n")
    asked = answer_message_box(QMessageBox.StandardButton.No)
    dialog.save_data_set_csv(case, PROBE)
    assert asked and "did not write" in asked[0]
    assert (tmp_path / "probe.source.txt").read_text() == "my own notes\n"
    assert not (tmp_path / "probe.csv").exists()
    # Our own note beside the CSV being replaced (the dialog already asked
    # about the CSV): replaced together, no further question.
    (tmp_path / "probe.source.txt").unlink()
    asked.clear()
    answer_message_box(QMessageBox.StandardButton.Yes)
    dialog.save_data_set_csv(case, PROBE)
    asked.clear()
    dialog.save_data_set_csv(case, PROBE)
    assert asked == []
    assert (tmp_path / "probe.csv").exists()


def test_data_never_goes_among_the_cases_files(dialog, monkeypatch, answer_message_box):
    case = Path(dialog.cases[0])
    monkeypatch.setattr(
        "ui.dialogs.plot_results_dialog.QFileDialog.getSaveFileName",
        lambda *a, **k: (str(case / "postProcessing/probes/0/p.csv"), ""),
    )
    answer_message_box(QMessageBox.StandardButton.Ok)
    dialog.save_data_set_csv(str(case), PROBE)
    assert sorted(p.name for p in (case / "postProcessing/probes/0").iterdir()) == ["p"]


def test_export_data_writes_what_is_plotted(dialog, tmp_path, monkeypatch, answer_message_box):
    other = _case(tmp_path, "caseB", scale=2.0)
    dialog.set_case_dir(str(other))
    assert not dialog.export_data_btn.isEnabled()
    dialog.tick_in_all_cases(PROBE, "probe0", True)
    dialog.replot()
    assert dialog.export_data_btn.isEnabled()
    out = tmp_path / "out"
    out.mkdir()
    monkeypatch.setattr(
        "ui.dialogs.plot_results_dialog.QFileDialog.getSaveFileName",
        lambda *a, **k: (str(out / "both"), ""),
    )
    dialog._on_export_data()
    rows = (out / "both.csv").read_text().splitlines()
    # Two cases: each line its own pair, headed by its legend label.
    assert rows[0] == "caseA: Time,caseA: probe0,caseB: Time,caseB: probe0"
    assert rows[1] == "1,1,1,2"
    note = (out / "both.source.txt").read_text()
    assert "Line 2:    caseB" in note and "probes/0/p" in note


def test_copy_as_table_puts_tab_separated_rows_on_the_clipboard(dialog):
    dialog.copy_data_set(dialog.cases[0], PROBE)
    assert QGuiApplication.clipboard().text().splitlines()[:2] == ["Time\tprobe0", "1\t1"]


def test_line_settings_change_one_line(dialog):
    case = dialog.cases[0]
    dialog.tick(case, GRAPH, "p")
    # Offered only for a ticked column.
    assert "Line Settings…" in _actions(dialog._build_column_menu(case, GRAPH, "p"))
    assert "Line Settings…" not in _actions(dialog._build_column_menu(case, PROBE, "probe0"))
    dialog.replot()
    line_dialog = dialog.line_settings_dialog(case, GRAPH, "p")
    try:
        assert line_dialog.label_edit.placeholderText() == "graph/line_p.xy @ 0.2: p"
        line_dialog.label_edit.setText("pressure")
        line_dialog._set_color("#2ca02c")
        line_dialog.style_combo.setCurrentIndex(line_dialog.style_combo.findData("none"))
        line_dialog.width_spin.setValue(3.0)
        line_dialog.apply_to(dialog._find_series(case, GRAPH, "p"))
    finally:
        line_dialog.deleteLater()
    line = _lines(dialog)[0]
    assert line.get_label() == "pressure"
    assert line.get_color() == "#2ca02c" and line.get_linestyle() == "None"
    assert line.get_marker() == "o"  # markers only: one is supplied
    assert line.get_linewidth() == 3.0


def test_settings_save_and_load_again(dialog, tmp_path, monkeypatch, answer_message_box):
    case = dialog.cases[0]
    other = _case(tmp_path, "caseB", scale=2.0)
    dialog.set_case_dir(str(other))
    dialog.tick_in_all_cases(PROBE, "probe0", True)
    dialog._find_series(str(other), PROBE, "probe0").color = "#ff0000"
    dialog.title_edit.setText("Two cases")
    dialog.y_fields.step.setText("0.5")
    dialog.legend_combo.setCurrentIndex(dialog.legend_combo.findData("lower right"))
    dialog.legend_size_spin.setValue(8)
    dialog.swap_check.setChecked(True)
    saved = dialog.spec()
    path = tmp_path / "out.plot.json"
    monkeypatch.setattr(dialog, "_ask_path", lambda *a: str(path))
    dialog._on_save_settings()

    # A fresh window, on the first case only, loads it back whole.
    fresh = PlotResultsDialog(case)
    try:
        assert fresh.apply_spec(spec_from_json(path.read_text())) == []
        assert fresh.spec() == saved
        assert [Path(c).name for c in fresh.cases] == ["caseA", "caseB"]
        # A case that has gone is reported, the rest still loads.
        shutil.rmtree(other)
        told = answer_message_box(QMessageBox.StandardButton.Ok)
        fresh.load_settings(str(path))
        assert told and "caseB" in told[0]
        assert len(fresh.spec().series) == 1
    finally:
        fresh.close()
        fresh.deleteLater()


def test_the_time_row_previews_frames(dialog):
    case = dialog.cases[0]
    dialog.replot()
    assert dialog.time_row.isHidden()  # nothing to animate yet
    dialog.tick(case, GRAPH, "p")  # written at 0.1 and 0.2
    dialog.replot()
    assert not dialog.time_row.isHidden()
    assert dialog.frame_label.text() == "Latest (2 frames)" and dialog.current_frame() is None
    dialog.time_slider.setValue(1)
    ax = dialog.figure.axes[0]
    assert dialog.current_frame() == "0.1"
    assert [t.get_text() for t in ax.texts] == ["t = 0.1"]
    assert list(ax.lines[0].get_ydata()) == [0.1, 0.1]
    ylim = ax.get_ylim()
    dialog.time_slider.setValue(2)
    ax = dialog.figure.axes[0]
    assert list(ax.lines[0].get_ydata()) == [0.2, 0.2]
    assert ax.get_ylim() == ylim  # the axes hold still between frames
    # Every output follows the frame shown, not the ordinary plot.
    dialog.time_slider.setValue(1)
    spec, resolved, stamp = dialog._resolved_for_export()
    assert stamp == "t = 0.1" and resolved.series[0].series.time == "0.1"
    assert resolved.series[0].y == [0.1, 0.1]
    assert dialog.source_files(case, GRAPH)[0].endswith("0.1/line_p.xy")
    assert dialog.plotted_lines()[0].time == "0.1"
    assert dialog.spec().series[0].time is None  # Save Settings keeps the set-up plot
    dialog.time_slider.setValue(0)
    assert dialog.frame_label.text() == "Latest (2 frames)"
    assert len(dialog.figure.axes[0].texts) == 0


def test_playing_steps_through_and_stops_at_the_end(dialog):
    dialog.tick(dialog.cases[0], GRAPH, "p")
    dialog.replot()
    dialog.play_btn.setChecked(True)
    assert dialog.time_slider.value() == 1
    dialog._advance_frame()
    assert dialog.time_slider.value() == 2
    dialog._advance_frame()
    assert not dialog.play_btn.isChecked()


def test_save_animation_writes_one_frame_per_time(dialog, tmp_path):
    from PIL import Image

    dialog.tick(dialog.cases[0], GRAPH, "p")
    dialog.width_spin.setValue(2.0)
    dialog.height_spin.setValue(1.5)
    dialog.dpi_spin.setValue(50)
    spec = dialog.spec()
    path = str(tmp_path / "anim.gif")
    written = dialog.save_animation(path, "gif", spec, ["0.1", "0.2"])
    assert written == path
    with Image.open(path) as gif:
        assert gif.n_frames == 2 and gif.size == (100, 75)


def test_auto_refresh_redraws_only_when_the_run_writes(dialog):
    case = Path(dialog.cases[0])
    dialog.show()
    dialog.tick(str(case), PROBE, "probe0")
    dialog.replot()
    dialog.auto_refresh()  # takes the files' first signature
    assert not dialog.auto_refresh()  # nothing written: no redraw
    with open(case / "postProcessing/probes/0/p", "a") as fh:
        fh.write("4 4\n")
    assert dialog.auto_refresh()
    assert list(dialog.figure.axes[0].lines[0].get_ydata()) == [1.0, 2.0, 3.0, 4.0]
    assert dialog.refresh_label.text().startswith("updated ")
    # Off, or hidden: no reading at all.
    with open(case / "postProcessing/probes/0/p", "a") as fh:
        fh.write("5 5\n")
    dialog.auto_refresh_check.setChecked(False)
    assert not dialog.auto_refresh()
    dialog.auto_refresh_check.setChecked(True)
    dialog.hide()
    assert not dialog.auto_refresh()
    dialog.show()
    assert dialog.auto_refresh()


def test_auto_refresh_keeps_a_zoom_and_picks_up_new_times(dialog):
    case = Path(dialog.cases[0])
    dialog.show()
    dialog.tick(str(case), GRAPH, "p")
    dialog.replot()
    dialog.auto_refresh()
    ax = dialog.figure.axes[0]
    ax.set_xlim(0.25, 0.75)  # the user zooms in
    later = case / "postProcessing" / "graph" / "0.3"
    later.mkdir()
    (later / "line_p.xy").write_text("0 0.3\n1 0.3\n")
    assert dialog.auto_refresh()
    ax = dialog.figure.axes[0]
    assert list(ax.lines[0].get_ydata()) == [0.3, 0.3]  # the new latest time
    assert ax.get_xlim() == (0.25, 0.75)  # the zoom survived
    assert dialog.frame_label.text() == "Latest (3 frames)"


def test_auto_refresh_finds_a_new_data_set_for_the_tree(dialog, monkeypatch):
    case = Path(dialog.cases[0])
    dialog.show()
    monkeypatch.setattr("ui.dialogs.plot_results_dialog._RESCAN_EVERY", 1)
    dialog.auto_refresh()
    new = case / "postProcessing" / "fieldMinMax" / "0"
    new.mkdir(parents=True)
    (new / "fieldMinMax.dat").write_text("# Time min max\n1 0 1\n")
    assert dialog.auto_refresh()
    assert dialog._source_item(str(case), "postProcessing/fieldMinMax/fieldMinMax.dat")


def test_writable_plot_path():
    assert writable_plot_path("/a/b.PNG") == "/a/b.png"
    assert writable_plot_path("/a/b.txt") == "/a/b.txt.png"
    assert writable_plot_path("/a/b.pdf") == "/a/b.pdf"


# ── main-window wiring ──────────────────────────────────────────────────────

def test_action_follows_the_case(main_window, tmp_path):
    win = main_window
    win._update_tools_actions()
    assert not win._plot_results_action.isEnabled()
    win.state.current_case_dir = str(tmp_path)
    win._update_tools_actions()
    assert win._plot_results_action.isEnabled()


def test_opening_another_case_adds_it_to_the_window(main_window, tmp_path, destroy_widget):
    win = main_window
    a, b = _case(tmp_path, "caseA"), _case(tmp_path, "caseB")
    win._load_case_dir(str(a))
    win._on_plot_results_clicked()
    dialog = win._plot_results_dialog
    try:
        assert dialog is not None and dialog.isVisible()
        win._load_case_dir(str(b))
        assert [Path(c).name for c in dialog.cases] == ["caseA", "caseB"]
    finally:
        destroy_widget(dialog)


def test_without_matplotlib_the_action_explains(main_window, monkeypatch, answer_message_box):
    win = main_window
    monkeypatch.setattr("ui.mixins._plot_ops.matplotlib_available", lambda: False)
    calls = answer_message_box(QMessageBox.StandardButton.Ok)
    win._on_plot_results_clicked()
    assert win._plot_results_dialog is None
    assert "pip install matplotlib" in calls[0]
