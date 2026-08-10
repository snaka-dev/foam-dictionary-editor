# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Word-wrapped labels get the height they need — ui/label_fit.py.

Both dialogs are a fixed width full of wrapped labels, and a wrapped QLabel's
sizeHint is measured at a width Qt guesses rather than the one it gets. The
guess was optimistic enough to cut the last lines off the About dialog's
acknowledgements and the second paragraph off both disclaimer boxes, at a
desktop font as ordinary as 11 pt.
"""
from __future__ import annotations

import pytest
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QLabel, QWidget

from ui.dialogs.about_dialog import AboutDialog
from ui.dialogs.openfoam_resources_dialog import OpenFOAMResourcesDialog
from ui.label_fit import fit_wrapped_labels

DIALOGS = [AboutDialog, OpenFOAMResourcesDialog]
# 9 pt never clipped; 11 pt is a common desktop size and clipped one label;
# 16 pt clipped five across the two dialogs.
FONT_SIZES = [9, 11, 16]


def _clipped(dialog: QWidget) -> list[tuple[str, int, int]]:
    """Wrapped labels whose allocated height is less than the text needs."""
    return [
        (label.text()[:30], label.height(), label.heightForWidth(label.width()))
        for label in dialog.findChildren(QLabel)
        if label.wordWrap()
        and label.width() > 0
        and label.heightForWidth(label.width()) > label.height()
    ]


@pytest.fixture
def app_font(qapp, request):  # noqa: ARG001 (qapp required by PySide6)
    previous = QApplication.font()
    QApplication.setFont(QFont("Sans Serif", request.param))
    try:
        yield request.param
    finally:
        QApplication.setFont(previous)


@pytest.mark.parametrize("app_font", FONT_SIZES, indirect=True)
@pytest.mark.parametrize("dialog_class", DIALOGS)
class TestNothingIsClipped:
    def test_every_wrapped_label_gets_the_height_it_needs(self, app_font, dialog_class):
        dialog = dialog_class()
        dialog.show()
        assert _clipped(dialog) == []

    def test_the_dialog_is_tall_enough_for_its_layout(self, app_font, dialog_class):
        dialog = dialog_class()
        dialog.show()
        assert dialog.height() >= dialog.layout().minimumSize().height()


class TestFittingHappensOnce:
    def test_a_second_show_does_not_resize_the_dialog(self, qapp):  # noqa: ARG002
        # The height is the user's once the dialog is up; re-fitting on every
        # show would take it back each time.
        dialog = AboutDialog()
        dialog.show()
        dialog.resize(dialog.width(), dialog.height() + 120)
        taller = dialog.height()
        dialog.hide()
        dialog.show()
        assert dialog.height() == taller


class TestHelper:
    def test_skips_labels_with_no_width(self, qapp):  # noqa: ARG002
        # A height derived from a zero width is not a height.
        parent = QWidget()
        label = QLabel("wrapped text that would need several lines to fit", parent)
        label.setWordWrap(True)
        label.resize(0, 10)
        fit_wrapped_labels(parent)
        assert label.minimumHeight() == 0

    def test_raises_the_minimum_to_what_the_width_needs(self, qapp):  # noqa: ARG002
        parent = QWidget()
        label = QLabel("wrapped text that needs several lines at this width", parent)
        label.setWordWrap(True)
        label.resize(80, 10)
        fit_wrapped_labels(parent)
        assert label.minimumHeight() == label.heightForWidth(80)

    def test_never_lowers_a_minimum_that_is_already_larger(self, qapp):  # noqa: ARG002
        parent = QWidget()
        label = QLabel("wrapped text", parent)
        label.setWordWrap(True)
        label.resize(400, 10)
        label.setMinimumHeight(500)
        fit_wrapped_labels(parent)
        assert label.minimumHeight() == 500

    def test_leaves_labels_that_do_not_wrap_alone(self, qapp):  # noqa: ARG002
        parent = QWidget()
        label = QLabel("one line", parent)
        parent.resize(300, 100)
        parent.show()
        fit_wrapped_labels(parent)
        assert label.minimumHeight() == 0
