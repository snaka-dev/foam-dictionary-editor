# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for ui/widgets/flow_layout.py (the wrapping BlockMesh toolbar layout).

The layout must report the widest single item as its minimum width (not the
sum of all items) and wrap items onto extra lines when narrowed, so the
BlockMesh 3-D panel can be resized well below its one-line toolbar width.
"""
from __future__ import annotations

from PySide6.QtWidgets import QPushButton, QWidget

from ui.widgets.flow_layout import FlowLayout


def _make_container(qapp, widths=(80, 120, 60)) -> tuple[QWidget, FlowLayout, list]:
    container = QWidget()
    layout = FlowLayout(container)
    buttons = []
    for w in widths:
        btn = QPushButton("x")
        btn.setFixedWidth(w)
        layout.addWidget(btn)
        buttons.append(btn)
    return container, layout, buttons


def test_minimum_width_is_widest_item(qapp):
    container, layout, buttons = _make_container(qapp)
    widest = max(b.minimumSize().width() for b in buttons)
    assert layout.minimumSize().width() == widest


def test_items_wrap_when_narrow(qapp):
    container, layout, buttons = _make_container(qapp)
    assert layout.hasHeightForWidth()
    single_line_height = layout.heightForWidth(10_000)  # everything fits
    # At 130 px only the widest item fits per line: three lines.
    narrow_height = layout.heightForWidth(130)
    assert narrow_height == 3 * single_line_height + 2 * layout._v_spacing


def test_wrapped_items_keep_order_and_positions(qapp):
    container, layout, buttons = _make_container(qapp)
    container.resize(150, 200)  # forces the 120-px button onto its own line
    container.show()
    qapp.processEvents()
    ys = [b.geometry().y() for b in buttons]
    xs = [b.geometry().x() for b in buttons]
    # First button starts the first line; second wraps below it.
    assert ys[1] > ys[0]
    assert xs[0] == xs[1]  # both lines start at the left edge
    container.hide()


def test_take_at_removes_items(qapp):
    container, layout, buttons = _make_container(qapp)
    assert layout.count() == 3
    item = layout.takeAt(1)
    assert item is not None and item.widget() is buttons[1]
    assert layout.count() == 2
    assert layout.itemAt(5) is None
    assert layout.takeAt(5) is None
