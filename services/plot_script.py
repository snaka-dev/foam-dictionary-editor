# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Write a Plot Results plot out as a script that reproduces it.

Two targets, deliberately different in kind:

- **Python (matplotlib)** re-reads the case's own files every time it runs,
  so a run that has written more since shows up. It can, because the reader
  it needs is copied in verbatim: :data:`READER_PATH` is self-contained, and
  its source is embedded between two marker lines. The plotting calls mirror
  :func:`services.plot_render.draw` one for one; the test that runs the
  script and compares figures is what holds them together.
- **gnuplot** cannot read ``(x y z)`` cells, restart segments or a header
  that names columns by position, so it gets a snapshot instead: a data file
  of exactly the plotted points, one ``index`` block per line, beside the
  ``.gp`` script.

Both are plain text builders with no Qt and no matplotlib import.
"""
from __future__ import annotations

import ast
import datetime as _dt
from pathlib import Path

from services.plot_spec import (
    Axis,
    PlotSpec,
    Resolved,
    font_kwargs,
    legend_kwargs,
    style_kwargs,
)

READER_PATH = Path(__file__).resolve().parent / "plot_data" / "_reader.py"
READER_BEGIN = "# ---- reader: copied verbatim from FoDE services/plot_data/_reader.py ----"
READER_END = "# ---- end of reader ----"


def reader_body() -> str:
    """The reader module's code without its licence header, docstring and
    ``from __future__`` line, which the script supplies once at its top."""
    source = READER_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    start = 0
    first = tree.body[0]
    if isinstance(first, ast.Expr) and isinstance(getattr(first, "value", None), ast.Constant):
        start = first.end_lineno or 0
    lines = source.splitlines()[start:]
    lines = [ln for ln in lines if ln.strip() != "from __future__ import annotations"]
    return "\n".join(lines).strip("\n") + "\n"


def _today() -> str:
    return _dt.date.today().isoformat()


def _float(v: float | None) -> str:
    return "None" if v is None else repr(float(v))


def python_script(
    spec: PlotSpec, resolved: Resolved, family: list[str] | None = None, stamp: str = ""
) -> str:
    """A standalone matplotlib script drawing *resolved* as *spec* says.

    *family* is the font list :func:`services.plot_render.font_family` chose,
    passed in so this module needs no matplotlib to decide it.
    """
    series = []
    for s in resolved.series:
        series.append(
            "    {\n"
            f"        \"label\": {s.label!r},\n"
            f"        \"kind\": {s.kind!r},\n"
            f"        \"column\": {s.series.column!r},\n"
            f"        \"x_column\": {s.x_name!r},\n"
            f"        \"style\": {style_kwargs(s.series)!r},\n"
            "        \"files\": [\n"
            + "".join(f"            {f!r},\n" for f in s.files)
            + "        ],\n"
            "    },\n"
        )
    title = spec.title or "FoDE plot"
    out = [
        "#!/usr/bin/env python3",
        f'"""{_doc_safe(title)} -- exported from FoDE\'s Plot Results on {_today()}.',
        "",
        "Reads the files listed in SERIES again every time it runs, so data a run",
        "has written since are included. Needs matplotlib.",
        "",
        "    python3 this_script.py            # open a window",
        "    python3 this_script.py out.png    # save an image (.png, .svg, .pdf, ...)",
        '"""',
        "from __future__ import annotations",
        "",
        "import sys",
        "",
        READER_BEGIN,
        reader_body().rstrip("\n"),
        READER_END,
        "",
        "",
        "SERIES = [",
        "".join(series).rstrip("\n"),
        "]",
        "",
        "",
        "def load(s):",
        '    """The (x, y) points of one entry of SERIES, as FoDE plotted them."""',
        '    if s["kind"] == "residuals":',
        '        table = read_log_residuals(s["files"][0])',
        '    elif s["kind"] == "profile":',
        '        table = read_table(s["files"][0])',
        "    else:",
        '        table = stitch([read_table(p) for p in s["files"]])',
        '    xs, ys = table.column(s["x_column"]), table.column(s["column"])',
        "    # Points where either coordinate is missing are dropped, joining the line.",
        "    keep = [(a, b) for a, b in zip(xs, ys) if not (math.isnan(a) or math.isnan(b))]",
        "    return [a for a, _ in keep], [b for _, b in keep]",
        "",
        "",
        "def draw(fig):",
        '    """Draw the plot on *fig*, a matplotlib Figure."""',
        "    import matplotlib",
        "    from matplotlib.ticker import MultipleLocator",
        "",
    ]
    body = []
    if family:
        body.append(f"matplotlib.rcParams[\"font.family\"] = {family!r}")
    body += [
        "ax = fig.add_subplot()",
        "for s in SERIES:",
        "    x, y = load(s)",
        "    ax.plot(x, y, label=s[\"label\"], **s[\"style\"])",
    ]
    if spec.title:
        body.append(f"ax.set_title({spec.title!r}{_kw(font_kwargs(spec.title_size))})")
    body.append(f"ax.set_xlabel({resolved.x_label!r}{_kw(font_kwargs(spec.label_size))})")
    body.append(f"ax.set_ylabel({resolved.y_label!r}{_kw(font_kwargs(spec.label_size))})")
    body += _axis_lines(spec)
    if spec.tick_size:
        body.append(f"ax.tick_params(labelsize={spec.tick_size!r})")
    if spec.grid:
        body.append("ax.grid(True)")
    if spec.legend and resolved.series:
        args = ", ".join(f"{k}={v!r}" for k, v in legend_kwargs(spec).items())
        body.append(f"ax.legend({args})")
    if stamp:
        # draw()'s time stamp: just above the axes' top-right corner.
        body += [
            f"ax.annotate({stamp!r}, xy=(1.0, 1.0), xycoords=\"axes fraction\", "
            "xytext=(0, 4),",
            "            textcoords=\"offset points\", ha=\"right\", va=\"bottom\""
            f"{_kw(font_kwargs(spec.tick_size))})",
        ]
    body += ["fig.tight_layout()"]
    out += ["    " + ln if ln else "" for ln in body]
    out += [
        "",
        "",
        "def main():",
        "    import matplotlib",
        "",
        "    if len(sys.argv) > 1:",
        '        matplotlib.use("Agg")  # saving only: no window, no display needed',
        "    import matplotlib.pyplot as plt",
        "",
        f"    fig = plt.figure(figsize=({spec.width!r}, {spec.height!r}))",
        "    draw(fig)",
        "    if len(sys.argv) > 1:",
        f"        fig.savefig(sys.argv[1], dpi={int(spec.dpi)})",
        "    else:",
        "        plt.show()",
        "",
        "",
        'if __name__ == "__main__":',
        "    main()",
        "",
    ]
    return "\n".join(out)


def _kw(kwargs: dict) -> str:
    """``, key=value`` for each keyword argument, to append to a call."""
    return "".join(f", {k}={v!r}" for k, v in kwargs.items())


def _axis_lines(spec: PlotSpec) -> list[str]:
    """Scales, then limits, then tick spacing -- draw()'s order."""
    axes = (("x", spec.x), ("y", spec.y))
    lines = [f"ax.set_{n}scale(\"log\")" for n, a in axes if a.log]
    lines += [
        f"ax.set_{n}lim({_float(a.min)}, {_float(a.max)})"
        for n, a in axes if a.min is not None or a.max is not None
    ]
    lines += [
        f"ax.{n}axis.set_major_locator(MultipleLocator({a.step!r}))"
        for n, a in axes if a.step and not a.log
    ]
    return lines


def _doc_safe(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"""', "'''")


# ── gnuplot ─────────────────────────────────────────────────────────────────

# gnuplot's nearest ``set key`` for each legend position; "best" has no
# equivalent and keeps gnuplot's default corner (top right).
_GP_KEY = {
    "best": "set key",
    "upper right": "set key top right",
    "upper left": "set key top left",
    "lower left": "set key bottom left",
    "lower right": "set key bottom right",
    "right": "set key center right",
    "center left": "set key center left",
    "center right": "set key center right",
    "lower center": "set key bottom center",
    "upper center": "set key top center",
    "center": "set key center center",
    "outside right": "set key outside right top",
}


# gnuplot's nearest dash type and point type for matplotlib's line styles
# and markers. Point types follow the common terminals (pngcairo, qt, wxt).
_GP_DASH = {"--": 2, ":": 3, "-.": 4}
_GP_POINT = {"o": 7, "s": 5, "^": 9, "v": 11, "D": 13, "x": 2, "+": 1, ".": 0}


# matplotlib's default colour cycle (tab10), for "C<n>" colours -- an
# animation frame pins each line to its cycle colour that way -- which
# gnuplot does not know.
_TAB10 = ("#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
          "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf")


def _gp_color(color: str) -> str:
    if color[:1] == "C" and color[1:].isdigit():
        return _TAB10[int(color[1:]) % len(_TAB10)]
    return color


def _gp_style(series) -> str:
    """``with lines``/``points``/``linespoints`` and the rest of a line's style."""
    line = series.linestyle != "none"
    point = bool(series.marker)
    out = ["with " + ("linespoints" if line and point else "points" if point else "lines")]
    if series.color:
        out.append(f"lc rgb '{_gp_color(series.color)}'")
    if series.linestyle in _GP_DASH:
        out.append(f"dt {_GP_DASH[series.linestyle]}")
    if series.linewidth:
        out.append(f"lw {series.linewidth!r}")
    if point:
        out.append(f"pt {_GP_POINT.get(series.marker, 7)}")
    return " ".join(out)


def _gp_font(size: float | None) -> str:
    """`` font ',<size>'``: the terminal's own font at *size* points."""
    return f" font ',{size:g}'" if size else ""


def _gp_key(spec: PlotSpec) -> str:
    if not spec.legend:
        return "unset key"
    if spec.legend_loc == "custom" and spec.legend_at is not None:
        x, y = legend_kwargs(spec)["loc"]
        return f"set key at graph {x!r}, graph {y!r} left bottom"
    return _GP_KEY.get(spec.legend_loc, "set key")


def _gp_str(text: str) -> str:
    """A gnuplot single-quoted string: only ``'`` needs escaping, by doubling."""
    return "'" + text.replace("'", "''") + "'"


def _gp_range(axis: Axis) -> str | None:
    if axis.min is None and axis.max is None:
        return None
    lo = "*" if axis.min is None else repr(float(axis.min))
    hi = "*" if axis.max is None else repr(float(axis.max))
    return f"[{lo}:{hi}]"


def gnuplot_data(resolved: Resolved) -> str:
    """The plotted points, one gnuplot ``index`` block per series."""
    blocks = []
    for i, s in enumerate(resolved.series):
        lines = [f"# index {i}: {s.label}"]
        lines += [f"# from {f}" for f in s.files]
        lines.append(f"# {s.x_name}\t{s.series.column}")
        lines += [f"{x!r}\t{y!r}" for x, y in zip(s.x, s.y)]
        blocks.append("\n".join(lines))
    # Two blank lines end an index block in gnuplot.
    return "\n\n\n".join(blocks) + "\n"


def gnuplot_script(spec: PlotSpec, resolved: Resolved, data_name: str, stamp: str = "") -> str:
    """A gnuplot script plotting the snapshot written by :func:`gnuplot_data`."""
    w, h = round(spec.width * 100), round(spec.height * 100)
    out = [
        f"# {spec.title or 'FoDE plot'} -- exported from FoDE's Plot Results on {_today()}.",
        f"# The data are a snapshot taken then, in {data_name}; export again for newer data.",
        "#",
        "#   gnuplot -p this_script.gp     (run it in the directory that holds both files)",
        "#",
        "# For an image instead of a window, uncomment:",
        f"# set terminal pngcairo size {w},{h}; set output 'plot.png'",
        "",
        f"datafile = {_gp_str(data_name)}",
        "# Labels are shown as written: no _ subscripts or ^ superscripts.",
        "set termoption noenhanced",
    ]
    if spec.title:
        out.append(f"set title {_gp_str(spec.title)}{_gp_font(spec.title_size)}")
    out.append(f"set xlabel {_gp_str(resolved.x_label)}{_gp_font(spec.label_size)}")
    out.append(f"set ylabel {_gp_str(resolved.y_label)}{_gp_font(spec.label_size)}")
    if spec.tick_size:
        out.append(f"set tics font ',{spec.tick_size:g}'")
    for name, axis in (("x", spec.x), ("y", spec.y)):
        if axis.log:
            out.append(f"set logscale {name}")
        rng = _gp_range(axis)
        if rng:
            out.append(f"set {name}range {rng}")
        if axis.step and not axis.log:
            out.append(f"set {name}tics {axis.step!r}")
    out.append("set grid" if spec.grid else "unset grid")
    if stamp:
        out.append(f"set label 1 {_gp_str(stamp)} at graph 1, graph 1 right offset 0, char 0.6"
                   f"{_gp_font(spec.tick_size)}")
    out.append(_gp_key(spec) + (_gp_font(spec.legend_size) if spec.legend else ""))
    plots = [
        f"datafile index {i} using 1:2 {_gp_style(s.series)} title {_gp_str(s.label)}"
        for i, s in enumerate(resolved.series)
    ]
    if plots:
        out.append("plot " + ", \\\n     ".join(plots))
    return "\n".join(out) + "\n"
