# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for ui/panels/editor_panel.py."""
from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QToolBar

from ui.fonts import icon_pixel_size
from ui.panels.editor_panel import EditorPanel


@pytest.fixture
def panel(qapp):
    return EditorPanel()


def _count_user_text_changed(panel: EditorPanel) -> list[int]:
    hits: list[int] = []
    panel.user_text_changed.connect(lambda: hits.append(1))
    return hits


def test_reload_highlighting_does_not_emit_user_text_changed(panel):
    """QSyntaxHighlighter.rehighlight() fires textChanged; the panel-level
    reload must suppress it so e.g. Generate OpenFOAM Keywords does not mark
    the current file dirty."""
    panel.set_text("application icoFoam;")
    hits = _count_user_text_changed(panel)
    panel.reload_highlighting()
    assert hits == []


def test_set_text_does_not_emit_user_text_changed(panel):
    hits = _count_user_text_changed(panel)
    panel.set_text("startTime 0;")
    assert hits == []


def test_typed_text_emits_user_text_changed(panel):
    """Direct document edits (what a human keystroke produces) still emit."""
    hits = _count_user_text_changed(panel)
    panel.editor.insertPlainText("deltaT 0.005;")
    assert hits != []


# ── Find toolbar (see EditorPanel._build_toolbar) ─────────────────────────────
#
# A real QToolBar rather than a QHBoxLayout of QToolButtons, for the same
# "looks like a tab bar" reason as ui/main_window.py's action toolbar: an
# autoRaise QToolButton paints flat until hovered, a QPushButton-shaped
# QToolButton never does.


def test_find_toolbar_is_a_real_toolbar(panel):
    toolbar = panel.findChild(QToolBar)
    assert toolbar is not None
    assert toolbar.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonTextBesideIcon
    assert toolbar.iconSize().width() == icon_pixel_size()
    # Order matters here as much as membership: it is the same left-to-right
    # reading the old layout gave.
    texts = [a.text() for a in toolbar.actions() if a.text()]
    assert texts == ["Find", "Find Prev", "Find Next", "Find in Tree", "Highlight"]


def test_highlight_action_is_checkable(panel):
    assert panel._highlight_action.isCheckable()


def test_highlight_action_round_trips_app_config(panel):
    """Toggling Highlight must still persist through get_feature/set_feature
    exactly as the old QToolButton did -- this is the one behaviour the
    QAction rewrite could not afford to lose."""
    from app_config import get_app_config

    cfg = get_app_config()
    assert panel._highlight_action.isChecked() == cfg.get_feature("syntax_highlighting", True)

    flipped = not panel._highlight_action.isChecked()
    panel._highlight_action.setChecked(flipped)
    assert cfg.get_feature("syntax_highlighting", True) == flipped
