# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""What a Plot Results plot shows, as data: series, axes, title, size.

A :class:`PlotSpec` is the single description both outputs are made from --
the window draws it with :func:`services.plot_render.draw`, and the script
exporters (:mod:`services.plot_script`) write it out as code -- so an
exported script reproduces the window's plot by construction. It is plain
JSON-able data, so a spec can be saved and loaded.

:func:`resolve` turns a spec into :class:`ResolvedSeries`: the numbers, the
files they came from and the final legend label. Both outputs read the
resolved labels and axis titles rather than re-deriving them.
"""
from __future__ import annotations

import json
import math
import os
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from services.plot_data import Source, find_sources, load_source, profile_path


@dataclass
class Series:
    """One line: a column of one data set of one case."""

    case_dir: str
    key: str
    column: str
    # A profile's time directory; None plots the latest.
    time: str | None = None
    # The legend text; empty means automatic (see :func:`auto_labels`).
    label: str = ""
    # The column plotted along x; empty means the data set's first column
    # (time, or a sampled line's position).
    x_column: str = ""
    # Line style; each empty (or None) leaves it to matplotlib's defaults --
    # the colour cycle, a solid line, no markers, the default width.
    color: str = ""        # "#rrggbb"
    linestyle: str = ""    # one of LINESTYLES
    marker: str = ""       # one of MARKERS
    linewidth: float | None = None


# Line styles and markers a line may take, as matplotlib spells them.
# "none" draws no line, for markers only.
LINESTYLES = ("", "-", "--", ":", "-.", "none")
MARKERS = ("", "o", "s", "^", "v", "D", "x", "+", ".")
_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def style_kwargs(series: Series) -> dict[str, Any]:
    """The ``Axes.plot`` keyword arguments for *series*' style; only those set.

    Shared by the renderer and the exported script, so both draw alike.
    """
    out: dict[str, Any] = {}
    if series.color:
        out["color"] = series.color
    if series.linestyle:
        out["linestyle"] = series.linestyle
    if series.marker:
        out["marker"] = series.marker
    if series.linewidth:
        out["linewidth"] = series.linewidth
    return out


@dataclass
class Axis:
    label: str = ""
    min: float | None = None
    max: float | None = None
    log: bool = False
    # Spacing of the major ticks; None leaves it to the plotting library.
    step: float | None = None


# Where the legend goes. The first eleven are matplotlib's own ``loc``
# names; "outside right" puts it beside the axes; "custom" places its
# lower-left corner at ``PlotSpec.legend_at`` (axes fractions), which is
# where dragging it in the window leaves it.
LEGEND_LOCATIONS = (
    "best",
    "upper right",
    "upper left",
    "lower left",
    "lower right",
    "right",
    "center left",
    "center right",
    "lower center",
    "upper center",
    "center",
    "outside right",
    "custom",
)


@dataclass
class PlotSpec:
    series: list[Series] = field(default_factory=list)
    title: str = ""
    x: Axis = field(default_factory=Axis)
    y: Axis = field(default_factory=Axis)
    # Draw each line's column along x and its x column (time, position)
    # along y: a sampled line across a channel reads as ``y`` against ``Ux``.
    # ``x`` and ``y`` above stay the horizontal and vertical axes.
    swap_axes: bool = False
    grid: bool = True
    legend: bool = True
    legend_loc: str = "best"
    # The legend's lower-left corner in axes fractions, for "custom".
    legend_at: tuple[float, float] | None = None
    # Font sizes in points; None leaves matplotlib's default.
    title_size: float | None = None
    label_size: float | None = None   # the axis labels
    tick_size: float | None = None    # the numbers along the axes
    legend_size: float | None = None
    # Frames per second of a saved animation.
    fps: float = 5.0
    # Figure size in inches and the resolution saved images use.
    width: float = 8.0
    height: float = 5.0
    dpi: int = 150

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlotSpec:
        """Lenient: unknown keys are ignored, malformed parts fall back."""
        def axis(d: Any) -> Axis:
            if not isinstance(d, dict):
                return Axis()
            return Axis(
                label=str(d.get("label", "")),
                min=_opt_float(d.get("min")),
                max=_opt_float(d.get("max")),
                log=bool(d.get("log", False)),
                step=_opt_float(d.get("step")),
            )

        series = []
        for s in data.get("series", []) or []:
            if isinstance(s, dict) and {"case_dir", "key", "column"} <= s.keys():
                color = str(s.get("color") or "")
                linestyle = str(s.get("linestyle") or "")
                marker = str(s.get("marker") or "")
                series.append(Series(
                    case_dir=str(s["case_dir"]),
                    key=str(s["key"]),
                    column=str(s["column"]),
                    time=None if s.get("time") is None else str(s["time"]),
                    label=str(s.get("label", "")),
                    x_column=str(s.get("x_column") or ""),
                    color=color if _HEX_COLOR.match(color) else "",
                    linestyle=linestyle if linestyle in LINESTYLES else "",
                    marker=marker if marker in MARKERS else "",
                    linewidth=_opt_float(s.get("linewidth")),
                ))
        return cls(
            series=series,
            title=str(data.get("title", "")),
            x=axis(data.get("x")),
            y=axis(data.get("y")),
            swap_axes=bool(data.get("swap_axes", False)),
            grid=bool(data.get("grid", True)),
            legend=bool(data.get("legend", True)),
            legend_loc=loc if (loc := data.get("legend_loc")) in LEGEND_LOCATIONS else "best",
            legend_at=_opt_point(data.get("legend_at")),
            width=_opt_float(data.get("width")) or 8.0,
            height=_opt_float(data.get("height")) or 5.0,
            dpi=int(_opt_float(data.get("dpi")) or 150),
            fps=min(max(_opt_float(data.get("fps")) or 5.0, 0.2), 60.0),
            title_size=_opt_size(data.get("title_size")),
            label_size=_opt_size(data.get("label_size")),
            tick_size=_opt_size(data.get("tick_size")),
            legend_size=_opt_size(data.get("legend_size")),
        )


def _opt_point(value: Any) -> tuple[float, float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    x, y = (_opt_float(v) for v in value)
    return None if x is None or y is None else (x, y)


def legend_kwargs(spec: PlotSpec) -> dict[str, Any]:
    """The ``Axes.legend`` keyword arguments for *spec*'s legend: its place
    and font size.

    Shared by the renderer and the exported script, so both place it alike.
    """
    out: dict[str, Any]
    if spec.legend_loc == "custom" and spec.legend_at is not None:
        out = {"loc": tuple(round(v, 4) for v in spec.legend_at)}
    elif spec.legend_loc == "outside right":
        out = {"loc": "upper left", "bbox_to_anchor": (1.02, 1.0), "borderaxespad": 0.0}
    elif spec.legend_loc in LEGEND_LOCATIONS and spec.legend_loc != "custom":
        out = {"loc": spec.legend_loc}
    else:
        out = {"loc": "best"}
    if spec.legend_size:
        out["fontsize"] = spec.legend_size
    return out


def font_kwargs(size: float | None) -> dict[str, Any]:
    """``{"fontsize": size}`` when a size is set, else nothing."""
    return {"fontsize": size} if size else {}


def _opt_size(value: Any) -> float | None:
    """A font size: positive and sane, else None (the default)."""
    size = _opt_float(value)
    return size if size is not None and 1.0 <= size <= 200.0 else None


def _opt_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


@dataclass
class ResolvedSeries:
    series: Series
    kind: str
    # The files read, in the order the reader stitches them.
    files: tuple[str, ...]
    # The data set's x column (time, position), whichever axis it is drawn on.
    x_name: str
    label: str
    # The points as drawn: horizontal, vertical. With ``swap_axes`` these are
    # the column's values and the x column's, in that order.
    x: list[float]
    y: list[float]


@dataclass
class Resolved:
    series: list[ResolvedSeries]
    x_label: str
    y_label: str
    # Series whose data set or column no longer exists, as (series, reason).
    missing: list[tuple[Series, str]] = field(default_factory=list)
    # The spec's ``swap_axes``, for writers that name the drawn columns.
    swap_axes: bool = False


def case_label(case_dir: str) -> str:
    return os.path.basename(os.path.normpath(case_dir)) or case_dir


def _label_parts(series: Series, source: Source) -> tuple[str, str, str, str]:
    """(case, data set, sample time or "", column) of one line."""
    time = ""
    if source.kind == "profile":
        time = series.time if series.time in source.times else source.times[-1]
    return case_label(series.case_dir), source.title, time, series.column


def auto_labels(parts: list[tuple[str, str, str, str]]) -> list[str]:
    """Legend text for every line: ``<case>: <data set> @ <time>: <column>``,
    keeping only the parts that tell the lines apart.

    Comparing one column across cases, the data set and column are the same
    on every line and would bury the case names in repetition; they are
    left to the axis label. A lone line keeps its data set and column, since
    there is nothing to tell it apart from and the legend is then its only
    description. A part that does not vary is dropped only when something
    else still distinguishes the lines.
    """
    if len(parts) <= 1:
        return [f"{t}{f' @ {time}' if time else ''}: {c}" for _, t, time, c in parts]
    varies = [len({p[i] for p in parts}) > 1 for i in range(4)]
    if not any(varies):
        varies = [False, True, True, True]
    out = []
    for case, title, time, column in parts:
        pieces = [case] if varies[0] else []
        at = f"@ {time}" if time and varies[2] else ""
        if varies[1]:
            pieces.append(f"{title} {at}".strip())
        elif at:
            # Same data set, different sample time: the time goes with the case.
            if pieces:
                pieces[-1] = f"{pieces[-1]} {at}"
            else:
                pieces.append(at)
        if varies[3]:
            pieces.append(column)
        out.append(": ".join(pieces))
    return out


def files_for(series: Series, source: Source) -> tuple[str, ...]:
    if source.kind == "profile":
        return (profile_path(source, series.time),)
    return source.paths


def resolve(spec: PlotSpec, sources: dict[str, list[Source]] | None = None) -> Resolved:
    """Load every series of *spec*. *sources* caches ``find_sources`` per case."""
    sources = {} if sources is None else sources
    out: list[ResolvedSeries] = []
    parts: list[tuple[str, str, str, str]] = []
    missing: list[tuple[Series, str]] = []
    for s in spec.series:
        if s.case_dir not in sources:
            sources[s.case_dir] = find_sources(s.case_dir)
        source = next((src for src in sources[s.case_dir] if src.key == s.key), None)
        if source is None:
            missing.append((s, "source"))
            continue
        try:
            table = load_source(source, s.time)
        except OSError:
            missing.append((s, "unreadable"))
            continue
        x_name = s.x_column or (table.names[0] if table.names else "")
        if s.column not in table.names or x_name not in table.names:
            missing.append((s, "column"))
            continue
        x, y = finite_pairs(table.column(x_name), table.column(s.column))
        if spec.swap_axes:
            x, y = y, x
        out.append(ResolvedSeries(
            series=s,
            kind=source.kind,
            files=files_for(s, source),
            x_name=x_name,
            label=s.label,
            x=x,
            y=y,
        ))
        parts.append(_label_parts(s, source))
    # Labels last: which parts are shown depends on every line plotted.
    for r, label in zip(out, auto_labels(parts)):
        r.label = r.label or label
    along_x, along_y = default_x_label(out), default_y_label(out)
    if spec.swap_axes:
        along_x, along_y = along_y, along_x
    return Resolved(
        series=out,
        x_label=spec.x.label or along_x,
        y_label=spec.y.label or along_y,
        missing=missing,
        swap_axes=spec.swap_axes,
    )


def finite_pairs(xs: list[float], ys: list[float]) -> tuple[list[float], list[float]]:
    """Drop points where either coordinate is NaN.

    A residual column has gaps where its field was not solved in a step, and
    a stitched restart where a segment lacks the column; a NaN would break
    the line there instead of joining the points either side.
    """
    px: list[float] = []
    py: list[float] = []
    for a, b in zip(xs, ys):
        if not (math.isnan(a) or math.isnan(b)):
            px.append(a)
            py.append(b)
    return px, py


def default_x_label(series: list[ResolvedSeries]) -> str:
    names = {s.x_name for s in series}
    return names.pop() if len(names) == 1 else ""


def default_y_label(series: list[ResolvedSeries]) -> str:
    if series and all(s.kind == "residuals" for s in series):
        return "Initial residual"
    names = {s.series.column for s in series}
    return names.pop() if len(names) == 1 else ""


# ── saved plot settings ──────────────────────────────────────────────────────

SETTINGS_FORMAT = "fode-plot"
SETTINGS_VERSION = 1


def spec_to_json(spec: PlotSpec) -> str:
    """A plot's settings as the text of a ``.plot.json`` file."""
    return json.dumps(
        {"format": SETTINGS_FORMAT, "version": SETTINGS_VERSION, "plot": spec.to_dict()},
        indent=2, ensure_ascii=False,
    ) + "\n"


def spec_from_json(text: str) -> PlotSpec:
    """Read :func:`spec_to_json`'s text back; ``ValueError`` if it is not one.

    Lenient past the envelope, like :meth:`PlotSpec.from_dict`: an unknown
    field is ignored and a malformed one falls back to its default, so a
    file from a later FoDE still opens.
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"not JSON: {exc}") from exc
    if not isinstance(data, dict) or data.get("format") != SETTINGS_FORMAT:
        raise ValueError("not a FoDE plot settings file")
    plot = data.get("plot")
    if not isinstance(plot, dict):
        raise ValueError("the file holds no plot")
    return PlotSpec.from_dict(plot)
