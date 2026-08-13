# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Theme-tinted toolbar/menu icons, loaded from hand-authored SVGs.

Every SVG under ``ui/assets/icons/`` is authored in black — there is no
``currentColor`` to switch on, since Qt's SVG Tiny 1.2 renderer has no CSS
cascade and would not resolve it. Instead the black glyph is rendered to a
transparent :class:`QImage` and the tint is composited through it as an alpha
mask (``CompositionMode_SourceIn``): the tint colour fills the whole image,
then everything outside the glyph's own alpha is erased again. That makes a
black icon going invisible against a dark theme structurally impossible
rather than a rule to remember — there is no colour string to get wrong,
only the glyph's shape survives.

:func:`icon` reads the size and tint at call time (:func:`ui.fonts.icon_pixel_size`
and :func:`ui.theme.icon_tint`), never at import — the same rule
``ui/theme.py`` and ``ui/fonts.py`` follow, for the same reason: the desktop
font and the active theme are both settled after this module is imported.
The module-level cache below is keyed on ``(name, size, tint)``, so it is
*not* the kind of import-time caching that rule forbids: the theme and font
are inputs to the key, not something baked in ahead of a value that could
change under it. A stale entry is unreachable, not stale.

The app must always be able to start without icons. Every failure mode —
the file is missing, ``PySide6.QtSvg`` cannot be imported, the SVG fails to
parse — returns a null :class:`QIcon` rather than raising; a null icon
renders as nothing, which is a visual regression, not a crash.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

from ui import fonts, theme

try:
    from PySide6.QtSvg import QSvgRenderer

    _QTSVG_AVAILABLE = True
except ImportError:  # pragma: no cover - QtSvg ships with this project's PySide6
    _QTSVG_AVAILABLE = False

#: The stems every SVG under assets/icons/ must have, and the only valid
#: ``icon()`` names. Tested both directions against the directory listing so
#: the list and the files on disk cannot drift apart.
ICON_NAMES: tuple[str, ...] = (
    "open-case",
    "save-file",
    "save-case",
    "reload-case",
    "find",
    "find-previous",
    "find-next",
    "find-in-tree",
    "highlight",
)

# __file__-relative, not sys._MEIPASS-aware: this is the same pattern
# ui/widgets/_xterm_widget.py and ui/widgets/_foam_highlighter.py already use,
# and it is what lets the PyInstaller onedir bundle find the assets without a
# frozen-build special case.
_ASSETS_DIR = Path(__file__).parent / "assets" / "icons"

_cache: dict[tuple[str, int, str], QIcon] = {}


def _device_pixel_ratio() -> float:
    """The primary screen's device pixel ratio, or 1.0 with no screen to ask."""
    screen = QApplication.primaryScreen()
    return screen.devicePixelRatio() if screen is not None else 1.0


def icon(name: str, size: int | None = None, tint: str | None = None) -> QIcon:
    """Return *name* tinted for the active theme, or a null icon on any failure.

    *size* defaults to :func:`ui.fonts.icon_pixel_size` and *tint* to
    :func:`ui.theme.icon_tint`, both resolved at call time so a later theme or
    font change is picked up by the next call rather than baked in here.
    """
    if not _QTSVG_AVAILABLE:
        return QIcon()
    if size is None:
        size = fonts.icon_pixel_size()
    if tint is None:
        tint = theme.icon_tint()

    key = (name, size, tint)
    cached = _cache.get(key)
    if cached is not None:
        return cached

    result = _render(name, size, tint)
    _cache[key] = result
    return result


def _render(name: str, size: int, tint: str) -> QIcon:
    path = _ASSETS_DIR / f"{name}.svg"
    if not path.is_file():
        return QIcon()

    renderer = QSvgRenderer(str(path))
    if not renderer.isValid():
        return QIcon()

    dpr = _device_pixel_ratio()
    pixel_size = max(1, round(size * dpr))
    image = QImage(pixel_size, pixel_size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    renderer.render(painter)
    # SourceIn keeps only the tint colour where the glyph already left alpha,
    # and erases everything else -- an alpha mask, not a colour substitution.
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(image.rect(), QColor(tint))
    painter.end()

    image.setDevicePixelRatio(dpr)
    return QIcon(QPixmap.fromImage(image))
