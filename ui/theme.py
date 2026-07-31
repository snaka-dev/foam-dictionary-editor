# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Central colour handling for the whole UI.

Three concerns live here:

1. **Theme mode** — ``system`` keeps the platform's native style and palette,
   ``light``/``dark`` force a Fusion palette so the result is identical on every
   OS.  The active mode is persisted by :mod:`app_config`.
2. **Selection contrast** — Qt takes ``Highlight`` from the desktop (on Windows
   that is the user's accent colour) but never checks it against
   ``HighlightedText``, so the light theme renders near-black text on a
   saturated fill.  :func:`apply_theme` recomputes the whole pair via
   :func:`readable_selection_pair`.
3. **Semantic colours** — every hard-coded hex value that used to be scattered
   across ``ui/`` and ``model/`` now resolves through :func:`colors`, so both
   themes stay consistent and there is one place to change.

Call :func:`colors` at paint/populate time rather than caching the result at
import time; that is what lets a theme change take effect without a restart.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

ThemeMode = Literal["system", "light", "dark"]

#: Selectable modes, in menu order.
THEME_MODES: tuple[ThemeMode, ...] = ("system", "light", "dark")

#: Minimum contrast ratio we try to reach for selected text against its fill.
#: 4.5:1 is WCAG AA for body text; item-view labels are small, so we aim there.
_MIN_CONTRAST = 4.5


# ── contrast maths ────────────────────────────────────────────────────────────

def _linearise(channel: int) -> float:
    c = channel / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(color: QColor) -> float:
    """WCAG 2.1 relative luminance of *color*, in 0.0 (black) .. 1.0 (white)."""
    r, g, b = color.red(), color.green(), color.blue()
    return 0.2126 * _linearise(r) + 0.7152 * _linearise(g) + 0.0722 * _linearise(b)


def contrast_ratio(a: QColor, b: QColor) -> float:
    """WCAG contrast ratio between two colours, in 1.0 .. 21.0."""
    la, lb = relative_luminance(a), relative_luminance(b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


#: A fill lighter than this reads naturally with dark text (yellow, pastels).
#: Below it, a saturated accent belongs under white text, as every desktop does.
_LIGHT_FILL_LUMINANCE = 0.45


def readable_selection_pair(fill: QColor) -> tuple[QColor, QColor]:
    """Return a ``(fill, text)`` pair for a selected row that is actually legible.

    Picking whichever of black/white scores higher is *not* good enough.  The
    default Windows 11 accent ``#0078d4`` scores 4.64:1 against black and
    4.53:1 against white, so a pure max-contrast rule chooses black — which is
    precisely the near-black-on-blue that is hard to read, and which no desktop
    actually does.  Around mid luminance the numeric winner flips on noise.

    So the rule is conventional rather than purely numeric:

    * white text whenever it clears the threshold — the near-universal treatment
      for an accent-coloured selection;
    * black text on a genuinely light fill, where dark text is the natural read;
    * otherwise keep white text and darken the fill (preserving hue and
      saturation) until it clears — this keeps the user's accent recognisable
      instead of inverting the text on them.
    """
    white, black = QColor("#ffffff"), QColor("#000000")

    if contrast_ratio(white, fill) >= _MIN_CONTRAST:
        return fill, white
    if relative_luminance(fill) > _LIGHT_FILL_LUMINANCE:
        return fill, black

    hue, saturation, alpha = fill.hue(), fill.saturation(), fill.alpha()
    for value in range(fill.value(), -1, -4):
        candidate = QColor.fromHsv(hue, saturation, value, alpha)
        if contrast_ratio(white, candidate) >= _MIN_CONTRAST:
            return candidate, white
    return black, white


# ── semantic colour table ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class ThemeColors:
    """Semantic colours for one theme. Field names describe the *role*."""

    # Tree — diff row backgrounds (model/tree_model.py)
    diff_changed: str
    diff_only_here: str
    diff_only_in_ref: str
    # Tree — unparsed entry text
    unknown_entry_fg: str

    # File list (ui/panels/file_list_panel.py)
    file_dirty_fg: str
    file_extra_fg: str
    file_extra_dir_header_fg: str
    file_text_only_fg: str
    file_read_only_fg: str
    file_diff_none_fg: str
    file_diff_has_fg: str

    # Editor gutter (ui/widgets/code_editor.py)
    gutter_bg: str
    gutter_separator: str
    gutter_number_fg: str
    fold_marker: str
    span_highlight_bg: str
    current_line_bg: str

    # Generic label text
    secondary_text: str
    hint_text: str
    warning_text: str
    #: Amber — needs the user's eye but is not an error.
    attention_text: str

    # Notice banners (BlockMesh preview banner)
    banner_bg: str
    banner_fg: str
    banner_border: str

    # Diff legend bar (ui/main_window.py). Deliberately *not* the banner colours:
    # the bar carries the three diff swatches, so its fill has to stay clear of
    # every ``diff_*`` value or the matching swatch disappears into it.
    legend_bg: str
    legend_fg: str
    legend_border: str

    # Read-only info boxes (About / OpenFOAM Resources disclaimers)
    info_box_bg: str
    info_box_border: str

    # Comparison panel header
    compare_header_bg: str
    compare_header_border: str

    # Thin 1px separators and legend swatch outlines
    separator: str

    # Disabled / inactive rows (ui/panels/boundary_view_panel.py)
    disabled_fg: str
    disabled_bg: str

    # Editor syntax highlighting (ui/widgets/_foam_highlighter.py)
    syntax_keyword: str
    syntax_value_keyword: str
    syntax_number: str
    syntax_directive: str
    syntax_macro: str
    syntax_string: str
    syntax_comment: str

    # Splitter handle (ui/main_window.py)
    splitter_bg: str
    splitter_edge_light: str
    splitter_edge_dark: str

    # 3-D viewer (ui/panels/block_mesh_panel.py, ui/panels/block_mesh_renderer.py).
    # VTK draws its own text and has no palette, so every colour it needs is
    # named here. ``viewport_geometry_opacity`` is a multiplier, not a colour:
    # translucent geometry blends toward the background, so the same alpha that
    # reads well on white goes muddy on a dark scene.
    viewport_bg: str
    viewport_text: str
    viewport_grid: str
    # The grid's tick labels and axis titles, kept separate from the grid lines
    # they sit on. A gridline is decoration and may stay faint, but the numbers
    # beside it have to be read, so the two want different contrast targets and
    # cannot share one value.
    viewport_grid_text: str
    viewport_label_fg: str
    viewport_label_bg: str
    viewport_vertex_label_fg: str
    viewport_block_label_fg: str
    # Outline for the block whose tree row is selected. Deliberately off the
    # tab10 ramp the blocks themselves are coloured from, and a different hue
    # from the selected vertex's cyan, so "which block" and "which vertex" do
    # not read as the same marker.
    viewport_selected_block: str
    viewport_geometry_opacity: float


_LIGHT = ThemeColors(
    diff_changed="#FFFACD",
    diff_only_here="#E3F2FD",
    diff_only_in_ref="#E8F5E9",
    unknown_entry_fg="#B8860B",
    file_dirty_fg="#CC6600",
    file_extra_fg="#2266AA",
    file_extra_dir_header_fg="#6644AA",
    file_text_only_fg="#888888",
    file_read_only_fg="#7A6A55",
    file_diff_none_fg="#888888",
    file_diff_has_fg="#BB7700",
    gutter_bg="#F5F5F5",
    gutter_separator="#D2D2D2",
    gutter_number_fg="#787878",
    fold_marker="#5A5A5A",
    span_highlight_bg="#FFFBBE",
    current_line_bg="#E8F2FE",
    secondary_text="#555555",
    hint_text="#888888",
    warning_text="#FF6600",
    attention_text="#BB7700",
    banner_bg="#FFF3CD",
    banner_fg="#856404",
    banner_border="#FFEEBA",
    legend_bg="#D5D5D5",
    legend_fg="#333333",
    legend_border="#B0B0B0",
    info_box_bg="#F8F8F8",
    info_box_border="#DDDDDD",
    compare_header_bg="#E8F5E9",
    compare_header_border="#A5D6A7",
    separator="#B8B8B8",
    disabled_fg="#AAAAAA",
    disabled_bg="#F5F5F5",
    syntax_keyword="#0000CC",
    syntax_value_keyword="#007070",
    syntax_number="#008080",
    syntax_directive="#800080",
    syntax_macro="#CC6600",
    syntax_string="#006400",
    syntax_comment="#808080",
    splitter_bg="#D6D6D6",
    splitter_edge_light="#EFEFEF",
    splitter_edge_dark="#B8B8B8",
    viewport_bg="#FFFFFF",
    viewport_text="#000000",
    viewport_grid="#808080",
    viewport_grid_text="#555555",
    viewport_label_fg="#000000",
    viewport_label_bg="#FFFFFF",
    viewport_vertex_label_fg="#000000",
    viewport_block_label_fg="#00008B",
    viewport_selected_block="#D6006E",
    viewport_geometry_opacity=1.0,
)

# Dark values are hue-matched to the light set but re-tuned for a dark Base:
# backgrounds become low-lightness tints, foregrounds become high-lightness.
_DARK = ThemeColors(
    diff_changed="#4A4526",
    diff_only_here="#1E3A4C",
    diff_only_in_ref="#24402A",
    unknown_entry_fg="#E0B44A",
    file_dirty_fg="#FFA24D",
    file_extra_fg="#6FB3E8",
    file_extra_dir_header_fg="#B08CE8",
    file_text_only_fg="#909090",
    file_read_only_fg="#B49B78",
    file_diff_none_fg="#909090",
    file_diff_has_fg="#E0A64A",
    gutter_bg="#2B2B2B",
    gutter_separator="#3C3C3C",
    gutter_number_fg="#9A9A9A",
    fold_marker="#B0B0B0",
    span_highlight_bg="#4A4526",
    current_line_bg="#2F3A46",
    secondary_text="#B4B4B4",
    hint_text="#909090",
    warning_text="#FF9A4D",
    attention_text="#E0A64A",
    banner_bg="#4A4526",
    banner_fg="#F0D89A",
    banner_border="#6B6236",
    legend_bg="#1C1C1C",
    legend_fg="#E6E6E6",
    legend_border="#3C3C3C",
    info_box_bg="#2B2B2B",
    info_box_border="#454545",
    compare_header_bg="#24402A",
    compare_header_border="#3C6144",
    separator="#4A4A4A",
    disabled_fg="#6E6E6E",
    disabled_bg="#2B2B2B",
    syntax_keyword="#79A6FF",
    syntax_value_keyword="#4EC9B0",
    syntax_number="#6FD0C4",
    syntax_directive="#C792EA",
    syntax_macro="#E8A867",
    syntax_string="#8FBF6A",
    syntax_comment="#8A8A8A",
    splitter_bg="#3C3C3C",
    splitter_edge_light="#4A4A4A",
    splitter_edge_dark="#2A2A2A",
    # Mid-dark blue-grey rather than the panel's near-black: the mesh is drawn
    # in saturated mid-tones, which lose their hue against a very dark scene.
    viewport_bg="#2E3238",
    viewport_text="#E6E6E6",
    viewport_grid="#9A9A9A",
    viewport_grid_text="#C8C8C8",
    viewport_label_fg="#141414",
    viewport_label_bg="#D8D8D8",
    viewport_vertex_label_fg="#FFFFFF",
    viewport_block_label_fg="#9FC8FF",
    viewport_selected_block="#FF5FB0",
    # Translucent faces blend toward the dark background, so lift the alpha.
    viewport_geometry_opacity=1.35,
)

_active_mode: ThemeMode = "system"
_active_is_dark: bool = False


def colors() -> ThemeColors:
    """Semantic colours for the active theme."""
    return _DARK if _active_is_dark else _LIGHT


def is_dark() -> bool:
    """True when the active theme renders on a dark background."""
    return _active_is_dark


def active_mode() -> ThemeMode:
    """The mode passed to the last :func:`apply_theme` call."""
    return _active_mode


# ── palettes ──────────────────────────────────────────────────────────────────

def _fusion_light_palette() -> QPalette:
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window, QColor("#EFEFEF"))
    p.setColor(QPalette.ColorRole.WindowText, QColor("#000000"))
    p.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
    p.setColor(QPalette.ColorRole.AlternateBase, QColor("#F7F7F7"))
    p.setColor(QPalette.ColorRole.Text, QColor("#000000"))
    p.setColor(QPalette.ColorRole.Button, QColor("#EFEFEF"))
    p.setColor(QPalette.ColorRole.ButtonText, QColor("#000000"))
    p.setColor(QPalette.ColorRole.ToolTipBase, QColor("#FFFFDC"))
    p.setColor(QPalette.ColorRole.ToolTipText, QColor("#000000"))
    p.setColor(QPalette.ColorRole.Highlight, QColor("#2A6FB8"))
    p.setColor(QPalette.ColorRole.Link, QColor("#1A5FA8"))
    return p


def _fusion_dark_palette() -> QPalette:
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window, QColor("#353535"))
    p.setColor(QPalette.ColorRole.WindowText, QColor("#E6E6E6"))
    p.setColor(QPalette.ColorRole.Base, QColor("#232323"))
    p.setColor(QPalette.ColorRole.AlternateBase, QColor("#2C2C2C"))
    p.setColor(QPalette.ColorRole.Text, QColor("#E6E6E6"))
    p.setColor(QPalette.ColorRole.Button, QColor("#353535"))
    p.setColor(QPalette.ColorRole.ButtonText, QColor("#E6E6E6"))
    p.setColor(QPalette.ColorRole.ToolTipBase, QColor("#3C3C3C"))
    p.setColor(QPalette.ColorRole.ToolTipText, QColor("#E6E6E6"))
    p.setColor(QPalette.ColorRole.Highlight, QColor("#3D7EBF"))
    p.setColor(QPalette.ColorRole.Link, QColor("#6FB3E8"))
    for group in (QPalette.ColorGroup.Disabled,):
        p.setColor(group, QPalette.ColorRole.WindowText, QColor("#7A7A7A"))
        p.setColor(group, QPalette.ColorRole.Text, QColor("#7A7A7A"))
        p.setColor(group, QPalette.ColorRole.ButtonText, QColor("#7A7A7A"))
    return p


def _normalise_selection(palette: QPalette) -> QPalette:
    """Recompute the ``Highlight``/``HighlightedText`` pair in every colour group.

    Qt inherits the two colours from the desktop independently: on Windows the
    fill follows the user's accent colour while the text does not, and nothing
    checks the result.  The pair is therefore always recomputed rather than only
    when it fails a threshold — the default Windows accent technically *passes*
    4.5:1 against black while still being the unreadable combination the user
    sees.  See :func:`readable_selection_pair` for the rule.
    """
    for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive, QPalette.ColorGroup.Disabled):
        fill, text = readable_selection_pair(palette.color(group, QPalette.ColorRole.Highlight))
        palette.setColor(group, QPalette.ColorRole.Highlight, fill)
        palette.setColor(group, QPalette.ColorRole.HighlightedText, text)
    return palette


def _resolve_system_darkness(palette: QPalette) -> bool:
    """True when the desktop palette is a dark one."""
    return relative_luminance(palette.color(QPalette.ColorRole.Window)) < 0.4


# ── stylesheet ────────────────────────────────────────────────────────────────

def item_view_qss(palette: QPalette) -> str:
    """Selection rules pinned onto item views.

    Styles differ in how they paint ``CE_ItemViewItem`` — the Windows 11 style
    in particular does not simply fill with ``Highlight`` — so setting the
    palette alone is not enough to guarantee the pair actually used.  Naming
    both the fill and the text in a stylesheet makes the outcome identical
    across styles.
    """
    fill = palette.color(QPalette.ColorGroup.Active, QPalette.ColorRole.Highlight)
    text = palette.color(QPalette.ColorGroup.Active, QPalette.ColorRole.HighlightedText)
    inactive_fill = palette.color(QPalette.ColorGroup.Inactive, QPalette.ColorRole.Highlight)
    inactive_text = palette.color(QPalette.ColorGroup.Inactive, QPalette.ColorRole.HighlightedText)
    return f"""
        QTreeView::item:selected, QListWidget::item:selected,
        QListView::item:selected, QTableView::item:selected {{
            background-color: {fill.name()};
            color: {text.name()};
        }}
        QTreeView::item:selected:!active, QListWidget::item:selected:!active,
        QListView::item:selected:!active, QTableView::item:selected:!active {{
            background-color: {inactive_fill.name()};
            color: {inactive_text.name()};
        }}
    """


def splitter_qss() -> str:
    """Vertical splitter handle styling for the active theme."""
    c = colors()
    return f"""
        QSplitter::handle:vertical {{
            background-color: {c.splitter_bg};
            border-top: 1px solid {c.splitter_edge_dark};
            border-bottom: 1px solid {c.splitter_edge_light};
            height: 7px;
        }}
    """


# ── entry point ───────────────────────────────────────────────────────────────

def apply_theme(app: QApplication, mode: ThemeMode = "system") -> None:
    """Install *mode*'s style, palette, and selection stylesheet on *app*.

    ``system`` keeps the native style and desktop palette and only repairs the
    selection contrast; ``light``/``dark`` switch to Fusion so the result does
    not depend on the platform style.
    """
    global _active_mode, _active_is_dark

    if mode not in THEME_MODES:
        mode = "system"
    _active_mode = mode

    if mode == "system":
        # Keep the platform style and the desktop's own palette — copying
        # app.palette() rather than style().standardPalette() preserves the
        # user's accent colour and any other desktop customisation.
        palette = QPalette(app.palette())
        _active_is_dark = _resolve_system_darkness(palette)
    else:
        app.setStyle("Fusion")
        palette = _fusion_dark_palette() if mode == "dark" else _fusion_light_palette()
        _active_is_dark = mode == "dark"

    app.setPalette(_normalise_selection(palette))
    app.setStyleSheet(item_view_qss(app.palette()))
