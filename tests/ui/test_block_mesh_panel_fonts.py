# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""The BlockMesh panel's secondary labels and pinned button widths follow the
desktop font.

Two classes of bug, both from a size chosen once against one machine and
frozen in code: the labels used to carry `font-size: 11px` in their
stylesheet, which stayed 11 px however large the desktop font was set; the
label-size spin box and the camera-view buttons used to carry a
`setFixedWidth(...)` pixel figure, which caps as well as floors, so digits
and button text get cut the moment a larger font or a differently-padded
style needs more room than the number chosen. See ui/fonts.py.
"""
from __future__ import annotations

import pytest
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QSpinBox

from ui.fonts import button_pixel_width, small_point_size
from ui.panels import block_mesh_panel
from ui.panels.block_mesh_panel import (
    _LABEL_SPIN_MIN_WIDTH,
    _VIEW_BUTTON_MIN_WIDTH,
    BlockMeshPanel,
)

pytestmark = pytest.mark.skipif(
    not block_mesh_panel._PYVISTA_OK, reason="pyvista/pyvistaqt not installed"
)


def _label(panel: BlockMeshPanel, needle: str) -> QLabel:
    for label in panel.findChildren(QLabel):
        if needle in label.text():
            return label
    raise AssertionError(f"no label containing {needle!r}")


def _camera_buttons(panel: BlockMeshPanel) -> list[QPushButton]:
    """Return the seven +X/-X/…/Iso camera-view buttons."""
    names = {"+X", "-X", "+Y", "-Y", "+Z", "-Z", "Iso"}
    buttons = [b for b in panel.findChildren(QPushButton) if b.text() in names]
    assert len(buttons) == 7, f"expected 7 camera-view buttons, found {len(buttons)}"
    return buttons


@pytest.fixture
def panel(qapp):  # noqa: ARG001 (qapp required by PySide6)
    previous = QApplication.font()
    QApplication.setFont(QFont("Sans Serif", 16))
    try:
        yield BlockMeshPanel()
    finally:
        QApplication.setFont(previous)


@pytest.fixture
def default_font_panel(qapp):  # noqa: ARG001 (qapp required by PySide6)
    """A panel at the platform default font, not the enlarged 16 pt above."""
    return BlockMeshPanel()


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


class TestPinnedToolbarWidths:
    """The label-size spin box and the camera-view buttons floor their width
    from the active style and font rather than capping it below what it needs
    — see the module docstring and ui/fonts.py's button_pixel_width.
    """

    def test_the_spin_box_is_not_capped_below_its_own_size_hint(self, panel):
        # The spin box asks the style for its own hint (CT_SpinBox includes
        # the up/down button metrics), so it needs no helper of its own.
        spin = panel._label_font_size
        assert isinstance(spin, QSpinBox)
        assert spin.maximumWidth() >= spin.minimumSizeHint().width()

    def test_every_camera_button_is_not_capped_below_its_own_text(self, panel):
        for btn in _camera_buttons(panel):
            assert btn.maximumWidth() >= button_pixel_width(btn.text())

    def test_the_camera_buttons_all_share_one_width(self, panel):
        # One width for the whole row, not per button -- per-button sizing
        # goes ragged as the font grows ("+X" wants less room than "Iso").
        widths = {btn.maximumWidth() for btn in _camera_buttons(panel)}
        assert len(widths) == 1

    def test_the_default_font_floors_still_hold(self, default_font_panel):
        # Pins the half of the contract that must not change: at the platform
        # default these figures already left enough room, so the floor itself
        # -- not a wider computed value -- is still what wins.
        spin = default_font_panel._label_font_size
        assert spin.maximumWidth() == _LABEL_SPIN_MIN_WIDTH
        for btn in _camera_buttons(default_font_panel):
            assert btn.maximumWidth() == _VIEW_BUTTON_MIN_WIDTH
