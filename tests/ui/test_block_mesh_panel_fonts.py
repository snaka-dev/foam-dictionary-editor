# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""The BlockMesh panel's secondary labels follow the desktop font.

Both used to carry `font-size: 11px` in their stylesheet, which stayed 11 px
however large the desktop font was set — see ui/fonts.py.
"""
from __future__ import annotations

import sys

import pytest
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QLabel

from ui.fonts import small_point_size
from ui.panels import block_mesh_panel
from ui.panels.block_mesh_panel import BlockMeshPanel

pytestmark = pytest.mark.skipif(
    not block_mesh_panel._PYVISTA_OK, reason="pyvista/pyvistaqt not installed"
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])
    return app


def _label(panel: BlockMeshPanel, needle: str) -> QLabel:
    for label in panel.findChildren(QLabel):
        if needle in label.text():
            return label
    raise AssertionError(f"no label containing {needle!r}")


@pytest.fixture
def panel(qapp):  # noqa: ARG001 (qapp required by PySide6)
    previous = QApplication.font()
    QApplication.setFont(QFont("Sans Serif", 16))
    try:
        yield BlockMeshPanel()
    finally:
        QApplication.setFont(previous)


class TestSecondaryLabels:
    def test_the_mouse_hint_follows_the_application_font(self, panel):
        hint = _label(panel, "drag")
        assert hint.font().pointSizeF() == pytest.approx(small_point_size())
        assert hint.font().pointSizeF() > 11.0  # what the pinned 11 px was worth

    def test_the_mouse_hint_stays_italic(self, panel):
        # The stylesheet used to carry the italics along with the size; only
        # the size moved to the font.
        assert _label(panel, "drag").font().italic()

    def test_the_variable_badge_follows_the_application_font(self, panel):
        badge = _label(panel, "Variable-based")
        assert badge.font().pointSizeF() == pytest.approx(small_point_size())

    def test_the_badge_keeps_its_stylesheet(self, panel):
        # Colour, padding and the rounded corner stay in the stylesheet; a
        # font-size there would override the font set above it.
        style = _label(panel, "Variable-based").styleSheet()
        assert "border-radius" in style
        assert "font-size" not in style
