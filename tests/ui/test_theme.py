# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for ui/theme.py — contrast maths, palette repair, and the colour table."""
from __future__ import annotations

import dataclasses

import pytest
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from ui import theme
from ui.theme import (
    _DARK,
    _LIGHT,
    _MIN_CONTRAST,
    THEME_MODES,
    ThemeColors,
    apply_theme,
    colors,
    contrast_ratio,
    readable_selection_pair,
    relative_luminance,
)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def restore_theme(app):
    """Leave the process-wide theme state as we found it."""
    previous = theme.active_mode()
    saved_palette = QPalette(app.palette())
    saved_qss = app.styleSheet()
    yield
    apply_theme(app, previous)
    app.setPalette(saved_palette)
    app.setStyleSheet(saved_qss)


# ── contrast maths ────────────────────────────────────────────────────────────

def test_relative_luminance_endpoints():
    assert relative_luminance(QColor("#000000")) == pytest.approx(0.0)
    assert relative_luminance(QColor("#ffffff")) == pytest.approx(1.0)


def test_contrast_ratio_is_symmetric_and_bounded():
    black, white = QColor("#000000"), QColor("#ffffff")
    assert contrast_ratio(black, white) == pytest.approx(21.0)
    assert contrast_ratio(white, black) == pytest.approx(21.0)
    assert contrast_ratio(white, white) == pytest.approx(1.0)


# ── selection pair ────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "accent, expected_text",
    [
        ("#0078d4", "#ffffff"),  # Windows 11 default accent — the reported case
        ("#000080", "#ffffff"),  # navy
        ("#2a6fb8", "#ffffff"),  # our own light-theme Highlight
        ("#d13438", "#ffffff"),  # Windows red accent
        ("#808080", "#ffffff"),  # mid grey
        ("#ffff00", "#000000"),  # yellow — genuinely light, dark text is natural
        ("#e0e0e0", "#000000"),  # pale grey
    ],
)
def test_selection_text_follows_desktop_convention(accent, expected_text):
    _, text = readable_selection_pair(QColor(accent))
    assert text.name() == expected_text


def test_default_windows_accent_gets_white_despite_scoring_lower():
    """The regression this whole change exists for.

    ``#0078d4`` scores *higher* against black (4.64) than white (4.53), so a
    naive max-contrast rule reproduces the unreadable dark-on-blue. The pair
    must come out white regardless.
    """
    accent = QColor("#0078d4")
    assert contrast_ratio(QColor("#000000"), accent) > contrast_ratio(QColor("#ffffff"), accent)
    fill, text = readable_selection_pair(accent)
    assert text.name() == "#ffffff"
    assert fill == accent  # accent itself is left untouched


def test_dark_saturated_accent_is_darkened_rather_than_inverted():
    """When white does not clear on the accent as-is, darken the fill, keep white."""
    accent = QColor("#7a9cc6")  # too light for white, too dark to want black
    assert contrast_ratio(QColor("#ffffff"), accent) < _MIN_CONTRAST
    fill, text = readable_selection_pair(accent)
    assert text.name() == "#ffffff"
    assert contrast_ratio(text, fill) >= _MIN_CONTRAST
    assert fill.hue() == accent.hue()          # accent hue preserved
    assert fill.value() < accent.value()       # achieved by darkening


def test_every_accent_yields_a_readable_pair():
    """No accent a user can pick may produce an illegible selection."""
    for r in range(0, 256, 37):
        for g in range(0, 256, 37):
            for b in range(0, 256, 37):
                fill, text = readable_selection_pair(QColor(r, g, b))
                ratio = contrast_ratio(text, fill)
                assert ratio >= _MIN_CONTRAST, f"rgb({r},{g},{b}) -> {ratio:.2f}:1"


# ── palette repair ────────────────────────────────────────────────────────────

def test_windows_style_palette_is_repaired_in_every_group():
    """Reproduces the Windows 11 palette: accent fill, near-black selected text."""
    palette = QPalette()
    groups = (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive, QPalette.ColorGroup.Disabled)
    for group in groups:
        palette.setColor(group, QPalette.ColorRole.Highlight, QColor("#0078d4"))
        palette.setColor(group, QPalette.ColorRole.HighlightedText, QColor("#000000"))

    fixed = theme._normalise_selection(palette)
    for group in groups:
        fill = fixed.color(group, QPalette.ColorRole.Highlight)
        text = fixed.color(group, QPalette.ColorRole.HighlightedText)
        assert text.name() == "#ffffff", group
        assert contrast_ratio(text, fill) >= _MIN_CONTRAST, group


# ── apply_theme ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("mode", THEME_MODES)
def test_apply_theme_guarantees_readable_selection(app, mode):
    apply_theme(app, mode)
    palette = app.palette()
    for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive):
        fill = palette.color(group, QPalette.ColorRole.Highlight)
        text = palette.color(group, QPalette.ColorRole.HighlightedText)
        assert contrast_ratio(text, fill) >= _MIN_CONTRAST, f"{mode}/{group}"


def test_apply_theme_sets_mode_and_darkness(app):
    apply_theme(app, "dark")
    assert theme.active_mode() == "dark"
    assert theme.is_dark() is True
    assert colors() is _DARK

    apply_theme(app, "light")
    assert theme.active_mode() == "light"
    assert theme.is_dark() is False
    assert colors() is _LIGHT


def test_unknown_mode_falls_back_to_system(app):
    apply_theme(app, "chartreuse")  # type: ignore[arg-type]
    assert theme.active_mode() == "system"


def test_apply_theme_installs_selection_stylesheet(app):
    apply_theme(app, "dark")
    qss = app.styleSheet()
    fill = app.palette().color(QPalette.ColorGroup.Active, QPalette.ColorRole.Highlight)
    text = app.palette().color(QPalette.ColorGroup.Active, QPalette.ColorRole.HighlightedText)
    # Both halves of the pair must be named, or the platform style is free to
    # substitute its own text colour — which is the bug this guards against.
    assert f"background-color: {fill.name()}" in qss
    assert f"color: {text.name()}" in qss
    assert "QTreeView::item:selected" in qss


# ── colour table ──────────────────────────────────────────────────────────────

def test_both_themes_define_every_field():
    # ThemeColors is almost all colours; the handful of non-str fields (scale
    # factors) are checked separately, so filter by the declared type rather
    # than handing a float to QColor, which accepts it as a GlobalColor index.
    fields = {f.name for f in dataclasses.fields(ThemeColors) if f.type == "str"}
    for table in (_LIGHT, _DARK):
        for name in fields:
            value = getattr(table, name)
            assert QColor(value).isValid(), f"{name}={value!r}"


def test_geometry_opacity_scale_is_sane():
    for table in (_LIGHT, _DARK):
        assert table.viewport_geometry_opacity >= 1.0
        # The renderer clamps to 1.0, but a wild factor would flatten every
        # translucent face to opaque and hide the mesh behind its overlays.
        assert table.viewport_geometry_opacity <= 2.0


def test_themes_differ_on_backgrounds():
    """Guards against a copy-paste that leaves dark reusing light's values."""
    assert _LIGHT.gutter_bg != _DARK.gutter_bg
    assert _LIGHT.diff_changed != _DARK.diff_changed


@pytest.mark.parametrize("table, base", [(_LIGHT, "#ffffff"), (_DARK, "#232323")])
def test_foregrounds_are_legible_on_their_base(table, base):
    """Every text colour must clear 3:1 against the theme's own Base colour.

    3:1 is WCAG AA for large/bold text; these are status tints on small labels,
    so this is a floor that catches an unusable value, not a full audit.
    """
    text_fields = [
        "unknown_entry_fg", "file_dirty_fg", "file_extra_fg", "file_extra_dir_header_fg",
        "file_text_only_fg", "file_diff_none_fg", "file_diff_has_fg",
        "gutter_number_fg", "secondary_text", "hint_text", "attention_text",
        "syntax_keyword", "syntax_value_keyword", "syntax_number",
        "syntax_directive", "syntax_macro", "syntax_string", "syntax_comment",
    ]
    for name in text_fields:
        ratio = contrast_ratio(QColor(getattr(table, name)), QColor(base))
        assert ratio >= 3.0, f"{name}={getattr(table, name)} on {base} is {ratio:.2f}:1"


_DIFF_FIELDS = ("diff_changed", "diff_only_here", "diff_only_in_ref")


@pytest.mark.parametrize("table", [_LIGHT, _DARK], ids=["light", "dark"])
def test_diff_swatches_are_visible_on_the_legend_bar(table):
    """The legend bar must not reuse any diff colour as its own fill.

    ui/main_window.py draws the three diff swatches on the legend bar. When the
    bar's fill equals one of them that swatch becomes invisible — which is what
    happened while the bar was styled with ``banner_bg``: in dark mode both it
    and ``diff_changed`` were #4A4526, so the "changed" swatch vanished.
    """
    for name in _DIFF_FIELDS:
        swatch = QColor(getattr(table, name))
        ratio = contrast_ratio(swatch, QColor(table.legend_bg))
        assert ratio >= 1.25, (
            f"{name}={getattr(table, name)} is indistinguishable from "
            f"legend_bg={table.legend_bg} ({ratio:.3f}:1)"
        )


@pytest.mark.parametrize("table", [_LIGHT, _DARK], ids=["light", "dark"])
def test_diff_row_colours_are_distinct_from_each_other(table):
    """Three statuses share one tree; two matching tints would merge them."""
    for i, a in enumerate(_DIFF_FIELDS):
        for b in _DIFF_FIELDS[i + 1:]:
            assert getattr(table, a) != getattr(table, b), f"{a} == {b}"


@pytest.mark.parametrize("table", [_LIGHT, _DARK], ids=["light", "dark"])
def test_viewport_text_is_legible_on_the_viewport(table):
    """VTK has no palette, so the 3-D scene's text is themed by hand."""
    bg = QColor(table.viewport_bg)
    # 3.0 is the threshold for lines and other non-text marks. viewport_grid is
    # in this group because it paints gridlines; the text sitting on those lines
    # is viewport_grid_text, which is held to the stricter target below.
    for name in ("viewport_grid",):
        ratio = contrast_ratio(QColor(getattr(table, name)), bg)
        assert ratio >= 3.0, (
            f"{name}={getattr(table, name)} on viewport_bg={table.viewport_bg} "
            f"is {ratio:.2f}:1"
        )
    for name in ("viewport_text", "viewport_grid_text", "viewport_vertex_label_fg",
                 "viewport_block_label_fg"):
        ratio = contrast_ratio(QColor(getattr(table, name)), bg)
        assert ratio >= 4.5, (
            f"{name}={getattr(table, name)} on viewport_bg={table.viewport_bg} "
            f"is {ratio:.2f}:1"
        )
    # Badge labels carry their own fill, so they pair against that instead.
    badge = contrast_ratio(QColor(table.viewport_label_fg), QColor(table.viewport_label_bg))
    assert badge >= 4.5, f"viewport label pair is {badge:.2f}:1"
