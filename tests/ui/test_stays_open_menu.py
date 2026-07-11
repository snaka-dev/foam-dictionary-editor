# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for _StaysOpenMenu: checkable items toggle without closing the popup."""
from __future__ import annotations

import sys

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QAction, QMouseEvent
from PySide6.QtWidgets import QApplication

from ui.panels.block_mesh_panel import _StaysOpenMenu


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])
    return app


def _release_event() -> QMouseEvent:
    return QMouseEvent(
        QEvent.MouseButtonRelease,
        QPointF(0, 0),
        QPointF(0, 0),
        Qt.LeftButton,
        Qt.LeftButton,
        Qt.NoModifier,
    )


def test_checkable_enabled_action_toggles_without_closing(qapp):
    menu = _StaysOpenMenu()
    action = QAction("Shape", menu, checkable=True, checked=True)
    menu.addAction(action)
    menu.setActiveAction(action)
    menu.show()
    assert menu.isVisible()

    menu.mouseReleaseEvent(_release_event())

    assert action.isChecked() is False
    assert menu.isVisible()
    menu.close()


def test_repeated_clicks_toggle_each_time_without_closing(qapp):
    menu = _StaysOpenMenu()
    a = QAction("A", menu, checkable=True, checked=True)
    b = QAction("B", menu, checkable=True, checked=True)
    menu.addAction(a)
    menu.addAction(b)
    menu.show()

    menu.setActiveAction(a)
    menu.mouseReleaseEvent(_release_event())
    menu.setActiveAction(b)
    menu.mouseReleaseEvent(_release_event())

    assert a.isChecked() is False
    assert b.isChecked() is False
    assert menu.isVisible()
    menu.close()


def test_disabled_action_does_not_toggle(qapp):
    menu = _StaysOpenMenu()
    action = QAction("Legend", menu, checkable=True, checked=True)
    action.setEnabled(False)
    menu.addAction(action)
    menu.setActiveAction(action)
    menu.show()

    menu.mouseReleaseEvent(_release_event())

    assert action.isChecked() is True
    menu.close()


def test_non_checkable_action_falls_back_to_default_handling(qapp):
    menu = _StaysOpenMenu()
    triggered = []
    action = QAction("Load STL", menu)
    action.triggered.connect(lambda: triggered.append(True))
    menu.addAction(action)
    menu.setActiveAction(action)
    menu.show()

    # Default QMenu handling applies here (our override only special-cases
    # checkable, enabled actions); this should not raise.
    menu.mouseReleaseEvent(_release_event())
    menu.close()
