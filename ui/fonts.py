# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Monospace fonts sized from the desktop's own font, not pinned in code.

The editor and the two terminals all want a fixed-pitch font, and all three used
to name a size outright — 10 pt, 10 pt, and 13 CSS px. A hardcoded point size is
not a high-DPI bug (Qt converts points against the screen, so the text keeps its
physical size when the display scales), but it ignores the one setting a user
reaches for first: the desktop's font size. Someone who raises that to read a
dense screen sees the menus and the tree grow while the editor and terminal stay
exactly as they were — and those two are where the text actually is.

So every size here is derived from ``QApplication.font()``. Nothing is cached:
the application font is settled by the platform theme before the first widget is
built, and ``ui/theme.py`` sets the same precedent of reading at construction
time rather than at import.

``css_pixel_size`` exists for the xterm.js page, whose ``fontSize`` is CSS
pixels rather than points. The conversion is the fixed 96/72 — under Qt 6 the
logical DPI is pinned at 96 and scaling is carried by the device pixel ratio,
which the WebEngine page applies to its CSS pixels as well, so both sides scale
together and the ratio between them stays constant.
"""
from __future__ import annotations

from PySide6.QtGui import QFont, QFontInfo
from PySide6.QtWidgets import QApplication

# Preference order, not alternatives: setFamilies falls through to the first one
# present. Consolas is Windows, Menlo/Monaco macOS, DejaVu Sans Mono the usual
# Linux one, and "monospace" the generic that Qt maps to whatever is configured.
MONOSPACE_FAMILIES = (
    "Consolas",
    "Menlo",
    "Monaco",
    "DejaVu Sans Mono",
    "monospace",
)

# Used only when there is no QApplication to ask — under a bare unit test, say.
# Qt's own cross-platform default, so a widget built without an application
# comes out the size it would have had anyway.
FALLBACK_POINT_SIZE = 9.0

_CSS_PIXELS_PER_POINT = 96.0 / 72.0

# Secondary text — hint lines and badges — as a fraction of the application
# font, with a floor below which it stops being readable at all.
SMALL_TEXT_RATIO = 0.85
SMALL_TEXT_MIN_POINT_SIZE = 7.0

# Headings — a dialog's title line. One conventional step up; the weight that
# usually goes with it is a style, and stays in the stylesheet.
HEADING_TEXT_RATIO = 1.25

# Toolbar/menu icons, as a multiple of the CSS pixel size text renders at. 1.30
# of the 9 pt default's 12 px comes to 16 — the conventional small-icon size —
# and grows with the desktop font the same as everything else here, rather
# than pinning 16px outright and leaving icons behind when text grows.
ICON_TO_TEXT_RATIO = 1.30
ICON_MIN_PIXEL_SIZE = 12


def ui_point_size() -> float:
    """Return the application font's size in points.

    The point size as *set* is preferred over the resolved one: ``QFontInfo``
    reports the size of the font that was actually matched, which fontconfig
    quantises to whole pixels — 13 pt at 96 dpi comes back as 12.75. Rounding a
    size the user chose, on every widget that asks, is not this function's job.
    ``QFontInfo`` is still the fallback, because a font whose size was set in
    pixels — which is how some platform themes specify theirs — has no point
    size of its own to report.
    """
    if QApplication.instance() is None:
        return FALLBACK_POINT_SIZE
    # The static QApplication.font(), not the instance's: the instance is typed
    # as QCoreApplication, which has no fonts to speak of.
    font = QApplication.font()
    size = font.pointSizeF()
    if size > 0:
        return size
    size = QFontInfo(font).pointSizeF()
    return size if size > 0 else FALLBACK_POINT_SIZE


def monospace_font(point_size: float | None = None) -> QFont:
    """Return a fixed-pitch font at *point_size*, or the application font's size."""
    font = QFont()
    font.setFamilies(list(MONOSPACE_FAMILIES))
    font.setFixedPitch(True)
    font.setPointSizeF(point_size if point_size is not None else ui_point_size())
    return font


def small_point_size() -> float:
    """Return the point size for secondary text — hints, badges, captions.

    A ratio of the application font rather than a size of its own, for the same
    reason as everything else here: text pinned at 11 px stayed 11 px when the
    user raised the desktop font, which is precisely when a hint line most
    needs to grow with what it sits beside. The floor keeps it legible on a
    desktop whose font is already small — 0.85 of 8 pt is not text any more.
    """
    return max(SMALL_TEXT_MIN_POINT_SIZE, ui_point_size() * SMALL_TEXT_RATIO)


def small_font(italic: bool = False) -> QFont:
    """Return the application font at :func:`small_point_size`.

    Sizing through the font rather than a ``font-size`` in the stylesheet: a
    stylesheet overrides only the properties it names, so the colour, padding
    and italics stay where they are and only the size moves here.
    """
    font = _base_font()
    font.setPointSizeF(small_point_size())
    font.setItalic(italic)
    return font


def _base_font() -> QFont:
    """The application font to derive from, or a bare default without one."""
    if QApplication.instance() is None:
        return QFont()
    return QFont(QApplication.font())


def heading_point_size() -> float:
    """Return the point size for a heading — a dialog's title line."""
    return ui_point_size() * HEADING_TEXT_RATIO


def heading_font() -> QFont:
    """Return the application font at :func:`heading_point_size`."""
    font = _base_font()
    font.setPointSizeF(heading_point_size())
    return font


def css_pixel_size(point_size: float | None = None) -> int:
    """Return *point_size* (default: the application font's) as whole CSS pixels."""
    if point_size is None:
        point_size = ui_point_size()
    return max(1, round(point_size * _CSS_PIXELS_PER_POINT))


def icon_pixel_size() -> int:
    """Return the side length, in pixels, for a toolbar/menu icon.

    Routed through :func:`css_pixel_size` rather than a pinned 16: the rule
    here is size through the font, style through the stylesheet (see
    DEVELOPER.md's "Font sizes and display scaling"), and an icon sized apart
    from the text beside it would be exactly the kind of thing that rule
    exists to prevent. The floor keeps an icon usable on a desktop font small
    enough that the ratio alone would shrink it past recognition.
    """
    return max(ICON_MIN_PIXEL_SIZE, round(css_pixel_size() * ICON_TO_TEXT_RATIO))
