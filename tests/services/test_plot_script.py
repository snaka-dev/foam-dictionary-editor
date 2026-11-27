# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Plot Results' spec, renderer and script export.

The central promise is that an exported Python script draws the plot the
window drew. It is checked the only way that means anything: the script is
run, and its figure compared with services.plot_render.draw()'s, artist by
artist.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

matplotlib = pytest.importorskip("matplotlib")
from matplotlib.figure import Figure  # noqa: E402

from services.plot_render import draw, font_family  # noqa: E402
from services.plot_script import (  # noqa: E402
    READER_BEGIN,
    READER_END,
    gnuplot_data,
    gnuplot_script,
    python_script,
    reader_body,
)
from services.plot_spec import Axis, PlotSpec, Series, auto_labels, resolve  # noqa: E402


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


@pytest.fixture
def cases(tmp_path):
    a, b = tmp_path / "caseA", tmp_path / "caseB"
    for case, scale in ((a, 1.0), (b, 2.0)):
        rows = "".join(f"{t / 10} ({scale * t} 0 {t}) \n" for t in range(1, 6))
        _write(case / "postProcessing" / "probes" / "0" / "U",
               "# Probe 0 (0 0 0)\n# Time 0\n" + rows)
        # A restart, so the script has to stitch.
        _write(case / "postProcessing" / "probes" / "0.3" / "U",
               "# Probe 0 (0 0 0)\n# Time 0\n0.3 (9 0 0)\n0.6 (10 0 0)\n")
        for t in ("0.1", "0.2"):
            _write(case / "postProcessing" / "graph" / t / "line_p_U.xy",
                   f"0 {t} 1 0 0\n0.5 {t} 2 0 0\n1 {t} 3 0 0\n")
        _write(case / "log.icoFoam", (
            "Time = 0.1\nDILUPBiCG:  Solving for Ux, Initial residual = 1, Final\n"
            "Time = 0.2\nDILUPBiCG:  Solving for Ux, Initial residual = 0.01, Final\n"
        ))
    return a, b


def _spec(cases, **kw) -> PlotSpec:
    a, b = cases
    spec = PlotSpec(series=[
        Series(str(a), "postProcessing/probes/U", "probe0_x"),
        Series(str(b), "postProcessing/probes/U", "probe0_x", label="mine"),
        Series(str(a), "postProcessing/graph/line_p_U.xy", "U_x", time="0.1"),
    ], **kw)
    return spec


def _snapshot(fig: Figure) -> dict:
    ax = fig.axes[0]
    legend = ax.get_legend()
    return {
        "lines": [(ln.get_label(), list(ln.get_xdata()), list(ln.get_ydata()),
                   ln.get_color(), ln.get_linestyle(), ln.get_marker(), ln.get_linewidth())
                  for ln in ax.lines],
        "title": ax.get_title(),
        "texts": [(t.get_text(), t.get_fontsize()) for t in ax.texts],
        "sizes": (
            ax.title.get_fontsize(), ax.xaxis.label.get_fontsize(),
            ax.yaxis.label.get_fontsize(),
            [t.get_fontsize() for t in ax.get_xticklabels() + ax.get_yticklabels()],
            None if legend is None else [t.get_fontsize() for t in legend.get_texts()],
        ),
        "xlabel": ax.get_xlabel(),
        "ylabel": ax.get_ylabel(),
        "xscale": ax.get_xscale(),
        "yscale": ax.get_yscale(),
        "xlim": ax.get_xlim(),
        "ylim": ax.get_ylim(),
        "xticks": list(ax.get_xticks()),
        "yticks": list(ax.get_yticks()),
        "legend": None if legend is None else [t.get_text() for t in legend.get_texts()],
        # Where it is placed: matplotlib keeps no public getter for loc.
        "legend_loc": None if legend is None else legend._loc,
        "legend_anchor": None if legend is None else tuple(legend.get_bbox_to_anchor().bounds),
        "grid": ax.xaxis.get_gridlines()[0].get_visible() if ax.xaxis.get_gridlines() else None,
        "size": tuple(fig.get_size_inches()),
    }


def _run_exported(script: str, tmp_path: Path, spec: PlotSpec) -> Figure:
    path = tmp_path / "exported_plot.py"
    path.write_text(script)
    module_spec = importlib.util.spec_from_file_location("exported_plot", path)
    module = importlib.util.module_from_spec(module_spec)
    # The embedded reader's dataclasses look their module up while defined.
    sys.modules["exported_plot"] = module
    try:
        module_spec.loader.exec_module(module)
    finally:
        del sys.modules["exported_plot"]
    fig = Figure(figsize=(spec.width, spec.height))
    module.draw(fig)
    return fig


@pytest.mark.parametrize(
    "variant",
    ["plain", "settings", "log", "legend outside", "legend dragged", "styled", "fonts",
     "frame", "swapped"],
)
def test_exported_python_script_draws_the_same_figure(cases, tmp_path, variant):
    spec = _spec(cases)
    if variant == "settings":
        spec.title = "Probe U"
        spec.x = Axis(label="t [s]", min=0.0, max=0.6, step=0.2)
        spec.y = Axis(min=-1.0, step=2.5)
        spec.grid = False
        spec.legend = False
    elif variant == "log":
        spec.y = Axis(log=True, step=5.0)  # a step is ignored on a log axis
        spec.width, spec.height = 4.0, 3.0
    elif variant == "legend outside":
        spec.legend_loc = "outside right"
    elif variant == "legend dragged":
        spec.legend_loc, spec.legend_at = "custom", (0.123456789, 0.5)
    elif variant == "fonts":
        spec.title = "Sized"
        spec.title_size, spec.label_size, spec.tick_size, spec.legend_size = 18, 14, 7, 6
    elif variant == "styled":
        a = spec.series[0]
        a.color, a.linestyle, a.marker, a.linewidth = "#d62728", "--", "o", 2.5
        spec.series[1].linestyle, spec.series[1].marker = "none", "s"
        spec.series[2].x_column = "U_y"  # a profile plotted against another column
    elif variant == "swapped":
        spec.swap_axes = True
        spec.y = Axis(min=0.0, step=0.2)  # now the time/position axis
    stamp = ""
    if variant == "frame":
        # An animation frame: pinned "C<n>" colours, fixed axes, the stamp.
        from services.plot_animation import fixed_ranges, frame_spec, frame_times

        sources: dict = {}
        frames = frame_times(spec, sources)
        spec = frame_spec(spec, frames[0], sources, fixed_ranges(spec, frames, sources))
        spec.tick_size, stamp = 8, f"t = {frames[0]}"
    resolved = resolve(spec)
    assert not resolved.missing

    app_fig = Figure(figsize=(spec.width, spec.height))
    draw(app_fig, spec, resolved, stamp)
    script_fig = _run_exported(python_script(spec, resolved, None, stamp), tmp_path, spec)
    assert _snapshot(script_fig) == _snapshot(app_fig)


def test_restart_and_profile_time_reach_the_plot(cases):
    resolved = resolve(_spec(cases))
    probe_a, probe_b, profile = resolved.series
    assert probe_a.x == [0.1, 0.2, 0.3, 0.6]
    assert probe_a.y == [1.0, 2.0, 9.0, 10.0]
    assert probe_b.label == "mine"
    assert profile.label == "caseA: graph/line_p_U.xy @ 0.1: U_x"
    assert profile.files[0].endswith("0.1/line_p_U.xy")


def test_labels_name_the_case_only_when_cases_differ(cases):
    a, _ = cases
    spec = PlotSpec(series=[Series(str(a), "log.icoFoam", "Ux")])
    resolved = resolve(spec)
    assert resolved.series[0].label == "log.icoFoam: Ux"
    assert resolved.x_label == "Time" and resolved.y_label == "Initial residual"


@pytest.mark.parametrize("parts, expected", [
    # A lone line: its data set and column describe it.
    ([("A", "probes/p", "", "probe0")], ["probes/p: probe0"]),
    # One column across cases: only the case (and its sample time) differ.
    ([("A", "line.xy", "281", "U_x"), ("B", "line.xy", "381", "U_x")],
     ["A @ 281", "B @ 381"]),
    ([("A", "probes/p", "", "probe0"), ("B", "probes/p", "", "probe0")], ["A", "B"]),
    # Two columns of one data set.
    ([("A", "log", "", "Ux"), ("A", "log", "", "p")], ["Ux", "p"]),
    # Everything differs.
    ([("A", "probes/p", "", "probe0"), ("B", "line.xy", "0.1", "U_x")],
     ["A: probes/p: probe0", "B: line.xy @ 0.1: U_x"]),
    # The same line twice: nothing to tell apart, so the full description.
    ([("A", "log", "", "p"), ("A", "log", "", "p")], ["log: p", "log: p"]),
])
def test_automatic_labels_keep_what_tells_lines_apart(parts, expected):
    assert auto_labels(parts) == expected


def test_a_vanished_series_is_reported_not_raised(cases):
    a, _ = cases
    spec = PlotSpec(series=[
        Series(str(a), "postProcessing/nothing/here.dat", "a"),
        Series(str(a), "log.icoFoam", "nope"),
    ])
    resolved = resolve(spec)
    assert resolved.series == []
    assert [why for _, why in resolved.missing] == ["source", "column"]


def test_exported_script_runs_standalone_and_saves(cases, tmp_path):
    spec = _spec(cases)
    script = tmp_path / "plot.py"
    script.write_text(python_script(spec, resolve(spec)))
    out = tmp_path / "plot.png"
    # -I: no FoDE on the path, as on a machine without it.
    subprocess.run([sys.executable, "-I", str(script), str(out)], check=True, cwd=tmp_path)
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_script_embeds_the_reader_verbatim(cases):
    spec = _spec(cases)
    script = python_script(spec, resolve(spec))
    embedded = script.split(READER_BEGIN + "\n", 1)[1].split("\n" + READER_END, 1)[0]
    assert embedded + "\n" == reader_body()
    assert script.count("from __future__ import annotations") == 1


def test_cjk_labels_choose_a_fallback_font(cases):
    spec = _spec(cases, title="速度")
    resolved = resolve(spec)
    family = font_family(spec, resolved)
    from matplotlib import font_manager

    installed = {f.name for f in font_manager.fontManager.ttflist}
    if family is None:
        assert not any(n in installed for n in ("Noto Sans CJK JP", "IPAexGothic"))
    else:
        assert family[0] == "DejaVu Sans" and family[1] in installed
        assert f"{family!r}" in python_script(spec, resolved, family)
    assert font_family(_spec(cases), resolve(_spec(cases))) is None


def test_a_chosen_x_column_reaches_the_plot_and_its_label(cases):
    a, _ = cases
    spec = PlotSpec(series=[Series(str(a), "postProcessing/graph/line_p_U.xy", "U_x",
                                   time="0.1", x_column="p")])
    resolved = resolve(spec)
    assert resolved.series[0].x == [0.1, 0.1, 0.1] and resolved.series[0].y == [1, 2, 3]
    assert resolved.x_label == "p"
    spec.series[0].x_column = "nonexistent"
    assert [why for _, why in resolve(spec).missing] == ["column"]


def test_swapped_axes_draw_the_column_along_x(cases):
    a, _ = cases
    spec = PlotSpec(series=[Series(str(a), "postProcessing/graph/line_p_U.xy", "U_x",
                                   time="0.1", x_column="p")], swap_axes=True)
    resolved = resolve(spec)
    assert resolved.series[0].x == [1, 2, 3] and resolved.series[0].y == [0.1, 0.1, 0.1]
    assert (resolved.x_label, resolved.y_label) == ("U_x", "p")
    # The axis rows are the drawn axes: a label set there is used as is.
    spec.x = Axis(label="Ux [m/s]")
    assert resolve(spec).x_label == "Ux [m/s]"
    # The gnuplot snapshot names its two columns in the order they are drawn.
    assert "# U_x\tp\n" in gnuplot_data(resolved)
    assert PlotSpec.from_dict(spec.to_dict()).swap_axes is True
    assert PlotSpec.from_dict({}).swap_axes is False


def test_settings_file_round_trips_and_refuses_strangers(cases, tmp_path):
    from services.plot_spec import spec_from_json, spec_to_json

    spec = _spec(cases, title="t", legend_loc="custom", legend_at=(0.2, 0.3))
    spec.series[0].color, spec.series[0].marker, spec.series[0].x_column = "#123abc", "^", "x"
    assert spec_from_json(spec_to_json(spec)) == spec
    for text in ("not json", "[]", '{"format": "other"}', '{"format": "fode-plot"}'):
        with pytest.raises(ValueError):
            spec_from_json(text)
    # A malformed style falls back rather than failing the whole file.
    odd = spec_from_json('{"format": "fode-plot", "plot": {"series": [{"case_dir": "c", '
                         '"key": "k", "column": "a", "color": "red", "linestyle": "~", '
                         '"marker": "?", "linewidth": "x"}]}}')
    s = odd.series[0]
    assert (s.color, s.linestyle, s.marker, s.linewidth) == ("", "", "", None)


def test_spec_round_trips_and_reads_leniently(cases):
    spec = _spec(cases, title="t", legend_loc="custom", legend_at=(0.25, 0.75))
    spec.x = Axis(label="x", min=1.0, log=True)
    assert PlotSpec.from_dict(spec.to_dict()) == spec
    assert PlotSpec.from_dict(json.loads(json.dumps(spec.to_dict()))) == spec
    odd = PlotSpec.from_dict({
        "series": [{"case_dir": "c", "key": "k"}, "junk", {"case_dir": "c", "key": "k", "column": "a"}],
        "x": "nonsense", "y": {"min": "abc", "max": "inf"}, "dpi": "x", "extra": 1,
        "legend_loc": "somewhere", "legend_at": [1, "x"],
        "title_size": "big", "tick_size": -3, "legend_size": 1e9, "label_size": 12,
    })
    assert (odd.title_size, odd.tick_size, odd.legend_size, odd.label_size) == (
        None, None, None, 12.0)
    assert odd.legend_loc == "best" and odd.legend_at is None
    assert [s.column for s in odd.series] == ["a"]
    assert odd.x == Axis() and odd.y.min is None and odd.y.max is None
    assert odd.dpi == 150


def test_gnuplot_export(cases, tmp_path):
    spec = _spec(cases, title="it's U")
    spec.y = Axis(log=True, min=0.5)
    spec.x = Axis(step=0.25)
    resolved = resolve(spec)
    data = gnuplot_data(resolved)
    script = gnuplot_script(spec, resolved, "plot.dat")
    # One index block per series, separated by two blank lines.
    assert data.count("\n\n\n") == len(resolved.series) - 1
    assert "set title 'it''s U'" in script
    assert "set logscale y" in script and "set yrange [0.5:*]" in script
    assert "set xtics 0.25" in script
    assert script.count("datafile index") == 3
    styled = _spec(cases)
    styled.series[0].color, styled.series[0].linestyle = "#d62728", "--"
    styled.series[1].linestyle, styled.series[1].marker = "none", "s"
    styled.series[2].marker, styled.series[2].linewidth = "o", 2.0
    gp = gnuplot_script(styled, resolve(styled), "plot.dat")
    assert "with lines lc rgb '#d62728' dt 2 title" in gp
    assert "with points pt 5 title" in gp
    assert "with linespoints lw 2.0 pt 7 title" in gp
    sized = _spec(cases, title="T", title_size=16, label_size=12.5, tick_size=9, legend_size=8)
    gp = gnuplot_script(sized, resolve(sized), "plot.dat")
    xlabel = next(ln for ln in gp.splitlines() if ln.startswith("set xlabel"))
    assert "set title 'T' font ',16'" in gp and xlabel.endswith("font ',12.5'")
    assert "set tics font ',9'" in gp and "set key font ',8'" in gp
    framed = _spec(cases)
    framed.series[0].color = "C1"  # an animation frame's pinned cycle colour
    gp = gnuplot_script(framed, resolve(framed), "plot.dat", "t = 0.1")
    assert "lc rgb '#ff7f0e'" in gp
    assert "set label 1 't = 0.1' at graph 1, graph 1 right" in gp
    assert "set key outside right top" in gnuplot_script(
        _spec(cases, legend_loc="outside right"), resolved, "plot.dat")
    # A dragged legend: its lower-left corner at the same axes fractions.
    script = script.replace("set key\n", "set key at graph 0.3, graph 0.6 left bottom\n")
    assert "set key at graph" in script  # so the gnuplot run below checks its syntax
    assert "set key at graph 0.3, graph 0.6 left bottom" in gnuplot_script(
        _spec(cases, title="it's U", legend_loc="custom", legend_at=(0.3, 0.6),
              x=spec.x, y=spec.y), resolved, "plot.dat")
    if shutil.which("gnuplot") is None:
        pytest.skip("gnuplot not installed; text checks only")
    (tmp_path / "plot.dat").write_text(data)
    (tmp_path / "plot.gp").write_text(
        script.replace("# set terminal pngcairo", "set terminal pngcairo")
    )
    run = subprocess.run(["gnuplot", "plot.gp"], cwd=tmp_path, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    assert (tmp_path / "plot.png").stat().st_size > 0
