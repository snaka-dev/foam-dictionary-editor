# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""The Detail pane doesn't clip its last wrapped label -- ui/panels/detail_panel.py.

Same failure `ui/label_fit.py` documents for the About/Resources dialogs: a
wrapped QLabel's sizeHint is measured at a width Qt guesses, not the one it
gets, so the widget is handed too little height and the last lines never
draw. The Detail pane is a harder case than those two dialogs, though --
it repopulates on every tree selection and its width changes whenever the
`right_upper` splitter is dragged, so a one-shot `showEvent` fit (what the
dialogs use) is not enough; `DetailPanel` instead re-fits from every
`_populate_*` and from `resizeEvent`.

`_choice_hint_label` ("Select a suggested value or type a custom value.") is
the label that was actually observed clipped, so it is what these tests
target. Reaching it means selecting a node whose schema has choices --
`fvSchemes`' `ddtSchemes/default` is used because, on top of the choices, it
carries a real description/supported-in text, giving the page the fullest
set of visible wrapped labels it can show at once.

Per this repo's recorded lesson on measuring Qt pane overflow: assert via the
scroll area's scrollbar range, not `sizeHint()`, which reports the same
(wrong) number regardless of what actually got clipped on screen.
"""
from __future__ import annotations

import pytest
from PySide6.QtCore import QPoint
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QLabel, QScrollArea

from foam.nodes import FoamNode
from model.tree_model import FoamTreeModel
from ui.panels.detail_panel import DetailPanel

# 9 pt never clipped the choice-hint label in manual testing; 11 pt is a
# common desktop size; 16 pt is the size that first reported the bug.
FONT_SIZES = [9, 11, 16]

# Narrow enough that every wrapped label in the normal page needs several
# lines -- the width the right_upper splitter can be dragged down to.
_NARROW_WIDTH = 220


def _ddt_default_node() -> tuple[FoamTreeModel, FoamNode]:
    """A `ddtSchemes/default` node: real schema, with choices and a description."""
    root = FoamNode(name="root", node_type="dictionary")
    ddt_schemes = FoamNode(name="ddtSchemes", node_type="dictionary")
    default = FoamNode(name="default", node_type="word", value="Euler")
    root.add_child(ddt_schemes)
    ddt_schemes.add_child(default)
    return FoamTreeModel(root), default


@pytest.fixture
def app_font(qapp, request):  # noqa: ARG001 (qapp required by PySide6)
    previous = QApplication.font()
    QApplication.setFont(QFont("Sans Serif", request.param))
    try:
        yield request.param
    finally:
        QApplication.setFont(previous)


def _populate_narrow() -> DetailPanel:
    panel = DetailPanel()
    panel.resize(_NARROW_WIDTH, 300)
    panel.show()
    model, node = _ddt_default_node()
    panel.show_for_node(node, model, "case/system/fvSchemes")
    return panel


@pytest.mark.parametrize("app_font", FONT_SIZES, indirect=True)
class TestNothingIsClipped:
    def test_scrolling_to_the_bottom_exposes_the_full_choice_hint(self, app_font):
        panel = _populate_narrow()
        scroll = panel.findChild(QScrollArea)
        label = panel._choice_hint_label
        assert label.isVisible(), "choice hint should be showing for a key with choices"

        # Bottom edge of the label, in the coordinate space of the scrolled
        # widget (label's parent is the normal page, several layers below
        # scroll.widget(), so this has to go through mapTo rather than
        # reading label.geometry() directly).
        label_bottom = label.mapTo(scroll.widget(), QPoint(0, label.height())).y()
        bar = scroll.verticalScrollBar()
        reachable_bottom = bar.maximum() + scroll.viewport().height()
        assert reachable_bottom >= label_bottom

    def test_every_wrapped_label_gets_the_height_it_needs(self, app_font):
        panel = _populate_narrow()
        wrapped = [lbl for lbl in panel.findChildren(QLabel) if lbl.wordWrap() and lbl.width() > 0]
        assert wrapped, "the normal page should have wrapped labels to check"
        for label in wrapped:
            assert label.height() >= label.heightForWidth(label.width()), (
                f"{label.text()[:40]!r} is clipped: height {label.height()} < "
                f"needed {label.heightForWidth(label.width())}"
            )


class TestRefitsOnResize:
    def test_narrowing_after_populate_still_fits(self, qapp):  # noqa: ARG002
        """Populate at a wide width, then narrow -- exercises resizeEvent.

        The `_populate_*` fit call alone would leave a stale (too-small)
        minimum from the wide layout, since fit_wrapped_labels only ever
        raises a minimum. resizeEvent's own re-fit is what catches this.
        """
        panel = DetailPanel()
        panel.resize(700, 300)
        panel.show()
        model, node = _ddt_default_node()
        panel.show_for_node(node, model, "case/system/fvSchemes")

        panel.resize(_NARROW_WIDTH, 300)

        scroll = panel.findChild(QScrollArea)
        label = panel._choice_hint_label
        label_bottom = label.mapTo(scroll.widget(), QPoint(0, label.height())).y()
        bar = scroll.verticalScrollBar()
        reachable_bottom = bar.maximum() + scroll.viewport().height()
        assert reachable_bottom >= label_bottom
