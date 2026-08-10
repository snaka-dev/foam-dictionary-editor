# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Cover the editor's zoom — ui/widgets/code_editor.py's font half."""
from __future__ import annotations

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent

from ui.fonts import ui_point_size
from ui.widgets.code_editor import (
    ZOOM_MAX_POINT_SIZE,
    ZOOM_MIN_POINT_SIZE,
    CodeEditor,
)


@pytest.fixture
def editor(qapp):  # noqa: ARG001 (qapp required by PySide6)
    ed = CodeEditor()
    ed.setPlainText("FoamFile\n{\n    version 2.0;\n}\n")
    return ed


def _wheel(delta: int, ctrl: bool) -> QWheelEvent:
    return QWheelEvent(
        QPointF(10.0, 10.0),
        QPointF(10.0, 10.0),
        QPoint(0, 0),
        QPoint(0, delta),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.ControlModifier if ctrl else Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )


class TestStartingSize:
    def test_starts_at_the_application_font_size(self, editor):
        assert editor.font().pointSizeF() == pytest.approx(ui_point_size())

    def test_starts_unzoomed(self, editor):
        assert editor.zoom_steps() == 0


class TestZoomSteps:
    def test_zoom_in_grows_the_font_by_a_point(self, editor):
        before = editor.font().pointSizeF()
        editor.zoom_in()
        assert editor.zoom_steps() == 1
        assert editor.font().pointSizeF() == pytest.approx(before + 1)

    def test_zoom_out_shrinks_the_font_by_a_point(self, editor):
        before = editor.font().pointSizeF()
        editor.zoom_out()
        assert editor.zoom_steps() == -1
        assert editor.font().pointSizeF() == pytest.approx(before - 1)

    def test_reset_returns_to_the_application_font_size(self, editor):
        editor.set_zoom_steps(6)
        editor.reset_zoom()
        assert editor.zoom_steps() == 0
        assert editor.font().pointSizeF() == pytest.approx(ui_point_size())

    def test_stays_within_the_upper_bound(self, editor):
        editor.set_zoom_steps(10_000)
        assert editor.font().pointSizeF() <= ZOOM_MAX_POINT_SIZE

    def test_stays_within_the_lower_bound(self, editor):
        editor.set_zoom_steps(-10_000)
        assert editor.font().pointSizeF() >= ZOOM_MIN_POINT_SIZE

    def test_clamping_does_not_bank_invisible_steps(self, editor):
        # Holding the key down must not leave a pile of steps that have to be
        # undone one by one before the text changes size again.
        editor.set_zoom_steps(10_000)
        pinned = editor.zoom_steps()
        editor.zoom_out()
        assert editor.zoom_steps() == pinned - 1

    def test_the_line_number_gutter_follows_the_font(self, editor):
        narrow = editor.line_number_area_width()
        editor.set_zoom_steps(12)
        assert editor.line_number_area_width() > narrow

    def test_the_tab_stop_follows_the_font(self, editor):
        narrow = editor.tabStopDistance()
        editor.set_zoom_steps(12)
        assert editor.tabStopDistance() > narrow


class TestWheel:
    def test_ctrl_wheel_up_zooms_in(self, editor):
        editor.wheelEvent(_wheel(120, ctrl=True))
        assert editor.zoom_steps() == 1

    def test_ctrl_wheel_down_zooms_out(self, editor):
        editor.wheelEvent(_wheel(-120, ctrl=True))
        assert editor.zoom_steps() == -1

    def test_plain_wheel_scrolls_rather_than_zooming(self, editor):
        editor.wheelEvent(_wheel(-120, ctrl=False))
        assert editor.zoom_steps() == 0
