# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for ui/panels/editor_panel.py."""
from __future__ import annotations

import pytest

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
