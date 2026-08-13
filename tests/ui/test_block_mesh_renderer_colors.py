# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for block_mesh_renderer.py's colour handling and drawn-text safety.

Split off from the former test_block_mesh_renderer_topo.py when its geometry
tests moved to tests/ui/test_shape_mesh.py alongside the Qt-free module they
now cover (ui/panels/shape_mesh.py). What is left here depends on
ui.theme-adjacent colour tables that stayed in the renderer per
DEVELOPER.md's "Update candidates" note.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

pytest.importorskip("pyvista")

from ui.panels.block_mesh_renderer import _ACTION_COLORS

_RENDERER_PATH = (
    pathlib.Path(__file__).resolve().parents[2] / "ui" / "panels" / "block_mesh_renderer.py"
)


def test_element_removal_actions_are_coloured():
    """`subtract` is the canonical element-removal action; `delete` is its alias.

    OpenFOAM's `remove` deletes the whole set (no source geometry), so it must
    not be the key used to colour removed regions.
    """
    assert "subtract" in _ACTION_COLORS
    assert _ACTION_COLORS["delete"] == _ACTION_COLORS["subtract"]
    assert "subset" in _ACTION_COLORS
    assert "remove" not in _ACTION_COLORS


def _string_literals(path):
    """Yield (line, value) for every non-docstring string literal in a module."""
    tree = ast.parse(pathlib.Path(path).read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                and isinstance(body[0].value.value, str):
            docstrings.add(id(body[0].value))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                and id(node) not in docstrings:
            yield node.lineno, node.value


def test_every_string_this_module_can_draw_is_ascii():
    """Regression: the Dimensions bounds readout's → reached the scene as nothing.

    Text in this module is drawn by VTK, not Qt. VTK's built-in label font has
    no glyph for → (nor for the ✂/⚠ that used to live in this file's
    _CLIP_MARK_SUFFIX, since moved to shape_mesh.py — see that module's own
    copy of this test) and draws *nothing* for it — not even a .notdef box —
    so the separator was invisible while the surrounding text still reserved
    its width; the bounds readout read "X  0   3  (3 m)" where it meant
    "0 → 3". The whole module is checked rather than just the one f-string,
    because a per-constant test would have walked straight past an inline
    f-string. Docstrings are exempt: prose arrows are fine in text that is
    never drawn. Note this catches a character that *cannot* be drawn, not one
    that merely looks wrong, so new scene text still wants a look on screen —
    a missing glyph is invisible to assert.
    """
    offenders = [
        (line, value) for line, value in _string_literals(_RENDERER_PATH)
        if not value.isascii()
    ]
    assert not offenders, "non-ASCII string literals in VTK-drawn module: " + "; ".join(
        f"line {line}: {value!r}" for line, value in offenders
    )
