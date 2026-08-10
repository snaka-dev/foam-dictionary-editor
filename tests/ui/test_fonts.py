# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Cover ui/fonts.py — the monospace sizes the editor and terminals derive."""
from __future__ import annotations

from contextlib import contextmanager

import pytest
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from ui.fonts import (
    FALLBACK_POINT_SIZE,
    MONOSPACE_FAMILIES,
    SMALL_TEXT_MIN_POINT_SIZE,
    css_pixel_size,
    heading_font,
    heading_point_size,
    monospace_font,
    small_font,
    small_point_size,
    ui_point_size,
)


@contextmanager
def _app_font(font: QFont):
    """Set the application font for one test and put the old one back.

    The qapp fixture is shared for the whole session, so a test that changes the
    application font and leaves it changed would silently reach every test that
    runs after it.
    """
    previous = QApplication.font()
    QApplication.setFont(font)
    try:
        yield
    finally:
        QApplication.setFont(previous)


class TestUiPointSize:
    def test_follows_the_application_font(self, qapp):  # noqa: ARG002 (Qt needs it)
        with _app_font(QFont("Sans Serif", 17)):
            assert ui_point_size() == pytest.approx(17.0)

    def test_pixel_sized_application_font_still_yields_a_point_size(self, qapp):  # noqa: ARG002
        # Some platform themes specify their font in pixels, and such a font
        # reports -1 for its point size until it has been resolved.
        font = QFont("Sans Serif")
        font.setPixelSize(24)
        with _app_font(font):
            assert ui_point_size() > 0


class TestMonospaceFont:
    def test_defaults_to_the_application_font_size(self, qapp):  # noqa: ARG002
        with _app_font(QFont("Sans Serif", 13)):
            assert monospace_font().pointSizeF() == pytest.approx(13.0)

    def test_explicit_size_wins(self, qapp):  # noqa: ARG002
        with _app_font(QFont("Sans Serif", 13)):
            assert monospace_font(20.0).pointSizeF() == pytest.approx(20.0)

    def test_asks_for_the_monospace_families_in_order(self, qapp):  # noqa: ARG002
        assert monospace_font().families() == list(MONOSPACE_FAMILIES)

    def test_is_fixed_pitch(self, qapp):  # noqa: ARG002
        assert monospace_font().fixedPitch()


class TestSmallText:
    def test_is_smaller_than_the_application_font(self, qapp):  # noqa: ARG002
        with _app_font(QFont("Sans Serif", 12)):
            assert small_point_size() < 12.0

    def test_grows_with_the_application_font(self, qapp):  # noqa: ARG002
        with _app_font(QFont("Sans Serif", 12)):
            small = small_point_size()
        with _app_font(QFont("Sans Serif", 20)):
            assert small_point_size() > small

    def test_never_falls_below_the_floor(self, qapp):  # noqa: ARG002
        # A desktop font that is already small must not take the hints with it.
        with _app_font(QFont("Sans Serif", 6)):
            assert small_point_size() == pytest.approx(SMALL_TEXT_MIN_POINT_SIZE)

    def test_small_font_keeps_the_application_family(self, qapp):  # noqa: ARG002
        with _app_font(QFont("Sans Serif", 12)):
            assert small_font().family() == "Sans Serif"

    def test_small_font_is_upright_by_default(self, qapp):  # noqa: ARG002
        assert not small_font().italic()

    def test_small_font_can_be_italic(self, qapp):  # noqa: ARG002
        assert small_font(italic=True).italic()


class TestHeadingText:
    def test_is_larger_than_the_application_font(self, qapp):  # noqa: ARG002
        with _app_font(QFont("Sans Serif", 12)):
            assert heading_point_size() > 12.0

    def test_grows_with_the_application_font(self, qapp):  # noqa: ARG002
        with _app_font(QFont("Sans Serif", 12)):
            small = heading_point_size()
        with _app_font(QFont("Sans Serif", 20)):
            assert heading_point_size() > small

    def test_heading_font_keeps_the_application_family(self, qapp):  # noqa: ARG002
        with _app_font(QFont("Sans Serif", 12)):
            assert heading_font().family() == "Sans Serif"

    def test_weight_is_left_to_the_caller(self, qapp):  # noqa: ARG002
        # Bold is a style, and stays in the stylesheet of whoever wants it.
        assert heading_font().weight() == QFont.Weight.Normal


class TestCssPixelSize:
    def test_converts_points_at_96_over_72(self, qapp):  # noqa: ARG002
        assert css_pixel_size(12.0) == 16
        assert css_pixel_size(9.0) == 12

    def test_defaults_to_the_application_font_size(self, qapp):  # noqa: ARG002
        with _app_font(QFont("Sans Serif", 12)):
            assert css_pixel_size() == 16

    def test_never_returns_zero(self, qapp):  # noqa: ARG002
        # xterm.js given a fontSize of 0 draws nothing at all.
        assert css_pixel_size(0.1) >= 1


class TestFallback:
    def test_fallback_is_a_usable_size(self):
        # Reached only when there is no QApplication to ask; a widget built then
        # must still come out at a size someone could read.
        assert 6.0 <= FALLBACK_POINT_SIZE <= 14.0
