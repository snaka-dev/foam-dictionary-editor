# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""The About and Resources dialogs size their labels from the desktop font.

Six labels here used to pin a `font-size` in pixels (16, 12, 12, 12, 13, 13),
which stayed put however large the desktop font was set — see ui/fonts.py.
"""
from __future__ import annotations

import pytest
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QLabel

from ui.dialogs.about_dialog import _APP_NAME, AboutDialog
from ui.dialogs.openfoam_resources_dialog import OpenFOAMResourcesDialog
from ui.fonts import heading_point_size, small_point_size, ui_point_size

_APP_POINT_SIZE = 16  # deliberately larger than every pixel size these had


def _label(widget, needle: str) -> QLabel:
    for label in widget.findChildren(QLabel):
        if needle in label.text():
            return label
    raise AssertionError(f"no label containing {needle!r}")


@pytest.fixture
def big_app_font(qapp):  # noqa: ARG001 (qapp required by PySide6)
    previous = QApplication.font()
    QApplication.setFont(QFont("Sans Serif", _APP_POINT_SIZE))
    try:
        yield
    finally:
        QApplication.setFont(previous)


@pytest.fixture
def about(big_app_font):  # noqa: ARG001
    return AboutDialog()


class TestAboutDialog:
    def test_the_app_name_is_a_heading(self, about):
        assert _label(about, _APP_NAME).font().pointSizeF() == pytest.approx(
            heading_point_size()
        )

    def test_the_app_name_stays_bold(self, about):
        # The weight is a style and stayed in the stylesheet; only the size moved.
        assert "font-weight: bold" in _label(about, _APP_NAME).styleSheet()

    def test_the_version_is_secondary_text(self, about):
        assert _label(about, "Version").font().pointSizeF() == pytest.approx(
            small_point_size()
        )

    def test_the_licence_is_secondary_text(self, about):
        assert _label(about, "GNU").font().pointSizeF() == pytest.approx(
            small_point_size()
        )

    def test_the_disclaimer_is_body_text(self, about):
        # The one label here that should read as easily as the text around it.
        assert _label(about, "not approved or endorsed").font().pointSizeF() == pytest.approx(
            ui_point_size()
        )

    def test_no_label_pins_a_font_size(self, about):
        pinned = [lbl.text()[:30] for lbl in about.findChildren(QLabel)
                  if "font-size" in lbl.styleSheet()]
        assert pinned == []


class TestResourcesDialog:
    def test_the_disclaimer_is_body_text(self, big_app_font):  # noqa: ARG002
        dialog = OpenFOAMResourcesDialog()
        assert _label(dialog, "not approved or endorsed").font().pointSizeF() == pytest.approx(
            ui_point_size()
        )

    def test_no_label_pins_a_font_size(self, big_app_font):  # noqa: ARG002
        dialog = OpenFOAMResourcesDialog()
        pinned = [lbl.text()[:30] for lbl in dialog.findChildren(QLabel)
                  if "font-size" in lbl.styleSheet()]
        assert pinned == []
