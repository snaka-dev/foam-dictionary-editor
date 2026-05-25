# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests that parser sets source_line / source_end_line on FoamNode."""
from __future__ import annotations

import pytest
from foam.parser import OpenFoamParser


def parse(text: str):
    return OpenFoamParser(text).parse()


def test_simple_scalar_source_line():
    root = parse("nu 1e-5;\n")
    node = root.children[0]
    assert node.name == "nu"
    assert node.source_line == 1
    assert node.source_end_line == 1


def test_multiline_dictionary_source_lines():
    text = "solver\n{\n    nIter 100;\n}\n"
    root = parse(text)
    node = root.children[0]
    assert node.name == "solver"
    assert node.source_line == 1
    assert node.source_end_line == 4


def test_entries_on_separate_lines():
    text = "a 1;\nb 2;\nc 3;\n"
    root = parse(text)
    assert root.children[0].source_line == 1
    assert root.children[1].source_line == 2
    assert root.children[2].source_line == 3


def test_directive_entry_source_line():
    text = "#include \"someFile\"\na 1;\n"
    root = parse(text)
    directive = root.children[0]
    assert directive.node_type == "directive_entry"
    assert directive.source_line == 1


def test_macro_entry_source_line():
    text = "a 1;\n$macro;\nb 2;\n"
    root = parse(text)
    macro_node = next(n for n in root.children if n.node_type == "macro_entry")
    assert macro_node.source_line == 2


def test_nested_dict_child_source_lines():
    text = "outer\n{\n    inner\n    {\n        x 5;\n    }\n}\n"
    root = parse(text)
    outer = root.children[0]
    inner = outer.children[0]
    assert outer.source_line == 1
    assert inner.source_line == 3
    assert inner.source_end_line == 6


def test_source_end_line_equals_source_line_for_single_line():
    text = "key (1 2 3);\n"
    root = parse(text)
    node = root.children[0]
    assert node.source_line == node.source_end_line == 1


def test_vector_on_one_line():
    text = "U (0 0 1);\n"
    root = parse(text)
    node = root.children[0]
    assert node.source_line == 1
    assert node.source_end_line == 1


def test_source_line_zero_never_negative():
    # Even for empty-ish input, source_line must be >= 0.
    root = parse("")
    assert all(n.source_line >= 0 for n in root.children)


# ── _find_deepest ─────────────────────────────────────────────────────────────

class _FakeWindow:
    """Minimal stand-in for MainWindow to call _find_deepest without Qt."""

    from ui._tree_ops import _TreeOpsMixin

    _find_deepest = _TreeOpsMixin._find_deepest


_finder = _FakeWindow()


def _node(name, start, end, children=None, node_type="word"):
    from foam.nodes import FoamNode
    n = FoamNode(name=name, node_type=node_type)
    n.source_line = start
    n.source_end_line = end
    n.children = children or []
    return n


def test_find_deepest_single_match():
    child = _node("a", 2, 2)
    root = _node("root", 0, 0, [child], node_type="dictionary")
    assert _finder._find_deepest(root, 2) is child


def test_find_deepest_no_match_returns_none():
    child = _node("a", 3, 3)
    root = _node("root", 0, 0, [child], node_type="dictionary")
    assert _finder._find_deepest(root, 10) is None


def test_find_deepest_prefers_innermost():
    inner = _node("inner", 3, 4)
    outer = _node("outer", 1, 6, [inner], node_type="dictionary")
    root = _node("root", 0, 0, [outer], node_type="dictionary")
    assert _finder._find_deepest(root, 3) is inner


def test_find_deepest_falls_back_to_outer_when_line_between_children():
    child_a = _node("a", 2, 2)
    child_b = _node("b", 5, 5)
    outer = _node("outer", 1, 6, [child_a, child_b], node_type="dictionary")
    root = _node("root", 0, 0, [outer], node_type="dictionary")
    # Line 4 is inside outer but between a and b — should return outer.
    assert _finder._find_deepest(root, 4) is outer


def test_find_deepest_zero_source_line_skipped():
    no_src = _node("nosrc", 0, 0)  # unset source lines
    root = _node("root", 0, 0, [no_src], node_type="dictionary")
    assert _finder._find_deepest(root, 1) is None


# ── boundary_block / region_block source lines ────────────────────────────────

_BOUNDARY_TEXT = "boundary\n(\n    inlet\n    {\n        type patch;\n    }\n);\n"


def test_boundary_block_source_lines_set():
    root = parse(_BOUNDARY_TEXT)
    boundary = root.children[0]
    assert boundary.node_type == "boundary_block"
    assert boundary.source_line == 1
    assert boundary.source_end_line == 7


def test_boundary_entry_source_lines_set():
    root = parse(_BOUNDARY_TEXT)
    boundary = root.children[0]
    patch = boundary.children[0]
    assert patch.node_type == "boundary_entry"
    assert patch.source_line == 4
    assert patch.source_end_line == 6


def test_region_block_source_lines_set():
    text = "regions\n(\n    boxToCell\n    {\n        box (0 0 0) (1 1 1);\n        fieldValues ( volScalarFieldValue alpha 1 );\n    }\n);\n"
    root = parse(text)
    regions = root.children[0]
    assert regions.node_type == "region_block"
    assert regions.source_line == 1
    assert regions.source_end_line == 8


def test_find_deepest_descends_into_boundary_block():
    # Regression: boundary_block/region_block nodes with source_line==0 were
    # silently skipped, so Find in Tree never reached their children.
    root = parse(_BOUNDARY_TEXT)
    boundary = root.children[0]
    patch = boundary.children[0]
    result = _finder._find_deepest(root, patch.source_line)
    assert result is not None
    assert result.source_line > 0
