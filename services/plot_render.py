# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Draw a resolved :class:`~services.plot_spec.PlotSpec` on a matplotlib Figure.

Qt-free and pyplot-free (a ``matplotlib.figure.Figure`` carries no global
state), so the window's canvas and the tests share it. The matplotlib
script :mod:`services.plot_script` writes performs the same calls in the
same order; ``tests/services/test_plot_script.py`` runs that script and
compares its figure with this one, which is what keeps the two in step.
Change one, change the other.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from services.plot_spec import PlotSpec, Resolved, font_kwargs, legend_kwargs, style_kwargs

if TYPE_CHECKING:
    from matplotlib.figure import Figure

# Tried in order for text the default font has no glyphs for; the first one
# installed is appended to the family list (matplotlib >= 3.6 falls back
# glyph by glyph). Without it a Japanese label draws as empty boxes.
CJK_FONTS = (
    "Noto Sans CJK JP",
    "Noto Sans JP",
    "IPAexGothic",
    "IPAGothic",
    "TakaoGothic",
    "VL Gothic",
    "Yu Gothic",
    "Meiryo",
    "MS Gothic",
    "Hiragino Sans",
)


def matplotlib_available() -> bool:
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        return False
    return True


def default_font_sizes() -> dict[str, float]:
    """matplotlib's own sizes, in points, for the text Plot Results can size.

    Read from its settings rather than written down here: they are relative
    ("large", "medium") to ``font.size``, which a matplotlibrc may change.
    Keyed like :class:`~services.plot_spec.PlotSpec`'s ``*_size`` fields.
    """
    import matplotlib
    from matplotlib.font_manager import FontProperties

    # Any: matplotlib types the keys as a Literal union a plain str misses.
    rc: Any = matplotlib.rcParams
    keys = {
        "title": "axes.titlesize",
        "label": "axes.labelsize",
        "tick": "xtick.labelsize",
        "legend": "legend.fontsize",
    }
    return {name: FontProperties(size=rc[key]).get_size_in_points() for name, key in keys.items()}


def needs_cjk(spec: PlotSpec, resolved: Resolved) -> bool:
    texts = [spec.title, resolved.x_label, resolved.y_label]
    texts += [s.label for s in resolved.series]
    return any(not t.isascii() for t in texts)


def font_family(spec: PlotSpec, resolved: Resolved) -> list[str] | None:
    """The ``font.family`` list to draw with, or None for matplotlib's default."""
    if not needs_cjk(spec, resolved):
        return None
    from matplotlib import font_manager

    installed = {f.name for f in font_manager.fontManager.ttflist}
    for name in CJK_FONTS:
        if name in installed:
            return ["DejaVu Sans", name]
    return None


def draw(fig: Figure, spec: PlotSpec, resolved: Resolved, stamp: str = "") -> None:
    """Clear *fig* and draw *resolved* on it as *spec* says.

    *stamp* -- an animation frame's time -- goes just above the top-right
    corner of the axes: never over the data or the legend, and clear of a
    centred title.
    """
    import matplotlib
    from matplotlib.ticker import MultipleLocator

    family = font_family(spec, resolved)
    # Any: matplotlib types the rc keys as a Literal union a plain dict misses.
    rc: Any = {"font.family": family} if family else {}
    fig.clear()
    with matplotlib.rc_context(rc):
        ax = fig.add_subplot()
        for s in resolved.series:
            ax.plot(s.x, s.y, label=s.label, **style_kwargs(s.series))
        if spec.title:
            ax.set_title(spec.title, **font_kwargs(spec.title_size))
        ax.set_xlabel(resolved.x_label, **font_kwargs(spec.label_size))
        ax.set_ylabel(resolved.y_label, **font_kwargs(spec.label_size))
        if spec.x.log:
            ax.set_xscale("log")
        if spec.y.log:
            ax.set_yscale("log")
        if spec.x.min is not None or spec.x.max is not None:
            ax.set_xlim(spec.x.min, spec.x.max)
        if spec.y.min is not None or spec.y.max is not None:
            ax.set_ylim(spec.y.min, spec.y.max)
        if spec.x.step and not spec.x.log:
            ax.xaxis.set_major_locator(MultipleLocator(spec.x.step))
        if spec.y.step and not spec.y.log:
            ax.yaxis.set_major_locator(MultipleLocator(spec.y.step))
        if spec.tick_size:
            ax.tick_params(labelsize=spec.tick_size)
        if spec.grid:
            ax.grid(True)
        if spec.legend and resolved.series:
            ax.legend(**legend_kwargs(spec))
        if stamp:
            ax.annotate(
                stamp, xy=(1.0, 1.0), xycoords="axes fraction", xytext=(0, 4),
                textcoords="offset points", ha="right", va="bottom",
                **font_kwargs(spec.tick_size),
            )
        fig.tight_layout()
