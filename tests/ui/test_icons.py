# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for ui/icons.py — theme-tinted SVG toolbar/menu icons.

The important one is the dark-mode guard: every SVG asset is authored black,
and the whole point of the alpha-mask tint in ``ui/icons.py`` is that a black
glyph never renders invisible against a dark theme. A test that only checked
"the icon is non-null" would pass even if the tint were silently ignored.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from contextlib import contextmanager
from pathlib import Path

import pytest
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from ui import theme
from ui.fonts import icon_pixel_size
from ui.icons import _ASSETS_DIR, ICON_NAMES, icon
from ui.theme import apply_theme, relative_luminance

_ASSET_FILES = sorted(p.stem for p in _ASSETS_DIR.glob("*.svg"))


@contextmanager
def _app_font(font: QFont):
    """Set the application font for one test and put the old one back.

    See tests/ui/test_fonts.py — the qapp fixture is session-scoped, so a
    test that changes the application font must restore it before the next
    test runs.
    """
    previous = QApplication.font()
    QApplication.setFont(font)
    try:
        yield
    finally:
        QApplication.setFont(previous)


@pytest.fixture(autouse=True)
def restore_theme(qapp):
    """Leave the process-wide theme/palette state as this module found it."""
    previous_mode = theme.active_mode()
    yield
    apply_theme(qapp, previous_mode)


# ── the icon set matches the asset directory, both directions ─────────────────

class TestIconNamesMatchTheDirectory:
    def test_every_declared_name_has_a_file(self):
        missing = [name for name in ICON_NAMES if name not in _ASSET_FILES]
        assert missing == []

    def test_every_file_is_a_declared_name(self):
        extra = [name for name in _ASSET_FILES if name not in ICON_NAMES]
        assert extra == []


# ── icon() loads every declared name ───────────────────────────────────────────

class TestIconLoading:
    @pytest.mark.parametrize("name", ICON_NAMES)
    def test_loads_a_non_null_icon_with_pixels(self, qapp, name):  # noqa: ARG002
        result = icon(name, size=16)
        assert not result.isNull()
        pixmap = result.pixmap(16, 16)
        assert not pixmap.isNull()
        assert pixmap.width() > 0 and pixmap.height() > 0

    def test_unknown_name_returns_a_null_icon(self, qapp):  # noqa: ARG002
        # A missing icon must degrade, never raise -- see the module docstring.
        assert icon("no-such-thing").isNull()


# ── the dark-mode guard ─────────────────────────────────────────────────────────

def _mean_luminance_of_opaque_pixels(pixmap) -> float:  # noqa: ANN001 (QPixmap)
    """Mean WCAG relative luminance over pixels with alpha > 0.

    Masking on alpha keeps the transparent background out of the mean; an
    icon that only fills a third of its square would otherwise read as "dim"
    regardless of the glyph's own colour.
    """
    image = pixmap.toImage()
    total = 0.0
    count = 0
    for y in range(image.height()):
        for x in range(image.width()):
            color = image.pixelColor(x, y)
            if color.alpha() > 0:
                total += relative_luminance(color)
                count += 1
    assert count > 0, "icon rendered fully transparent"
    return total / count


class TestDarkModeGuard:
    @pytest.mark.parametrize("name", ICON_NAMES)
    def test_icon_is_light_on_a_dark_theme(self, qapp, name):
        apply_theme(qapp, "dark")
        # No explicit tint: this exercises the same default resolution real
        # callers get, via ui.theme.icon_tint() reading the live palette.
        pixmap = icon(name, size=32).pixmap(32, 32)
        assert _mean_luminance_of_opaque_pixels(pixmap) > 0.5

    @pytest.mark.parametrize("name", ICON_NAMES)
    def test_icon_is_dark_on_a_light_theme(self, qapp, name):
        apply_theme(qapp, "light")
        pixmap = icon(name, size=32).pixmap(32, 32)
        assert _mean_luminance_of_opaque_pixels(pixmap) < 0.5


# ── size follows the application font ──────────────────────────────────────────

class TestIconSizeFollowsTheFont:
    def test_grows_with_the_application_font(self, qapp):  # noqa: ARG002
        with _app_font(QFont("Sans Serif", 9)):
            small = icon_pixel_size()
        with _app_font(QFont("Sans Serif", 16)):
            large = icon_pixel_size()
        assert large > small


# ── asset hygiene ────────────────────────────────────────────────────────────────

class TestAssets:
    @pytest.mark.parametrize("path", sorted(_ASSETS_DIR.glob("*.svg")), ids=lambda p: p.stem)
    def test_parses_as_xml(self, path: Path):
        ET.parse(path)

    @pytest.mark.parametrize("path", sorted(_ASSETS_DIR.glob("*.svg")), ids=lambda p: p.stem)
    def test_carries_the_spdx_header(self, path: Path):
        text = path.read_text(encoding="utf-8")
        assert "SPDX-License-Identifier: AGPL-3.0-or-later" in text
