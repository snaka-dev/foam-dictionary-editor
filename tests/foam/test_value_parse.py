# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for foam/value_parse.py: Qt-free text -> typed-value validation.

Mirrors the setData scenarios in tests/model/test_tree_model.py (int/scalar
edit + rejection + promotion) and tests/model/test_bool_nonuniform.py (bool
editing), but exercises the moved functions directly without a QAbstractItemModel.
"""
from __future__ import annotations

from foam.nodes import FoamNode
from foam.value_parse import (
    parse_parenthesized_numbers,
    parse_text_for_node_type,
    set_node_value,
)

# ── parse_parenthesized_numbers ─────────────────────────────────────────────


def test_parse_parenthesized_numbers_floats():
    assert parse_parenthesized_numbers("(1 2.5 3)") == [1.0, 2.5, 3.0]


def test_parse_parenthesized_numbers_force_int():
    assert parse_parenthesized_numbers("(1 2 3)", force_int=True) == [1, 2, 3]


def test_parse_parenthesized_numbers_force_int_rejects_float():
    assert parse_parenthesized_numbers("(1 2.5 3)", force_int=True) is None


def test_parse_parenthesized_numbers_empty_parens():
    assert parse_parenthesized_numbers("()") == []


def test_parse_parenthesized_numbers_not_parenthesized():
    assert parse_parenthesized_numbers("1 2 3") is None


def test_parse_parenthesized_numbers_non_numeric_element():
    assert parse_parenthesized_numbers("(1 foo 3)") is None


# ── parse_text_for_node_type ────────────────────────────────────────────────


def test_parse_text_int_accept():
    assert parse_text_for_node_type("int", "100") == ("int", 100)


def test_parse_text_int_reject_non_numeric():
    assert parse_text_for_node_type("int", "notanumber") == (None, None)


def test_parse_text_int_promotes_to_scalar():
    """A float-looking string on an int node promotes node_type to scalar."""
    assert parse_text_for_node_type("int", "0.5") == ("scalar", 0.5)


def test_parse_text_scalar_accept():
    assert parse_text_for_node_type("scalar", "0.001") == ("scalar", 0.001)


def test_parse_text_scalar_reject_non_numeric():
    assert parse_text_for_node_type("scalar", "notanumber") == (None, None)


def test_parse_text_vector_accept():
    assert parse_text_for_node_type("vector", "(1 2 3)") == ("vector", [1.0, 2.0, 3.0])


def test_parse_text_vector_reject_wrong_arity():
    assert parse_text_for_node_type("vector", "(1 2)") == (None, None)


def test_parse_text_vector_reject_non_numeric():
    assert parse_text_for_node_type("vector", "(1 x 3)") == (None, None)


def test_parse_text_box_pair_accept():
    node_type, value = parse_text_for_node_type("box_pair", "(0 0 0) (1 1 1)")
    assert node_type == "box_pair"
    assert value == [[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]


def test_parse_text_box_pair_reject():
    assert parse_text_for_node_type("box_pair", "not a box") == (None, None)


def test_parse_text_int_list_accept():
    assert parse_text_for_node_type("int_list", "(1 2 3)") == ("int_list", [1, 2, 3])


def test_parse_text_int_list_reject_float_element():
    assert parse_text_for_node_type("int_list", "(1 2.5 3)") == (None, None)


def test_parse_text_scalar_list_accept():
    assert parse_text_for_node_type("scalar_list", "(1 2.5 3)") == (
        "scalar_list",
        [1.0, 2.5, 3.0],
    )


def test_parse_text_scalar_list_reject_non_numeric():
    assert parse_text_for_node_type("scalar_list", "(1 foo 3)") == (None, None)


def test_parse_text_raw_list_strips_parens():
    assert parse_text_for_node_type("raw_list", "(setA setB)") == ("raw_list", "setA setB")


def test_parse_text_raw_list_passes_through_non_parenthesized():
    assert parse_text_for_node_type("raw_list", "setA setB") == ("raw_list", "setA setB")


def test_parse_text_bool_accept_case_insensitive():
    assert parse_text_for_node_type("bool", "TRUE") == ("bool", "true")
    assert parse_text_for_node_type("bool", "off") == ("bool", "off")


def test_parse_text_bool_reject():
    assert parse_text_for_node_type("bool", "maybe") == (None, None)


def test_parse_text_string_types_accept_any_text():
    for node_type in ("word", "string", "macro", "compound"):
        assert parse_text_for_node_type(node_type, "anything at all") == (
            node_type,
            "anything at all",
        )


def test_parse_text_unsupported_node_type_rejected():
    """A structural node_type (no editing path) always rejects."""
    assert parse_text_for_node_type("dictionary", "irrelevant") == (None, None)


# ── block_entry ──────────────────────────────────────────────────────────────


def test_parse_text_block_entry_accept_and_normalise():
    text = "hex   (0 1 2 3 4 5 6 7)   (10 10 10)   simpleGrading (1 1 1)"
    node_type, value = parse_text_for_node_type("block_entry", text)
    assert node_type == "block_entry"
    assert value == "hex (0 1 2 3 4 5 6 7) (10 10 10) simpleGrading (1 1 1)"


def test_parse_text_block_entry_accept_posy_style_macro_grading():
    text = "hex (0 3 4 1 11 14 15 12) (18 30 1) simpleGrading (0.5 $posY 1)"
    assert parse_text_for_node_type("block_entry", text) == ("block_entry", text)


def test_parse_text_block_entry_accept_bare_macro_tail():
    text = "hex (1 0 4 5 9 8 12 13) $blockInfo"
    assert parse_text_for_node_type("block_entry", text) == ("block_entry", text)


def test_parse_text_block_entry_accept_macro_vertex_group():
    # A macro can stand in for the vertex list, so there is nothing to count.
    text = "hex $verts (1 1 1) simpleGrading (1 1 1)"
    assert parse_text_for_node_type("block_entry", text) == ("block_entry", text)


def test_parse_text_block_entry_accept_name_prefix():
    text = "name sideBlock hex (0 1 2 3 4 5 6 7) (1 1 1) grading (1 1 1)"
    assert parse_text_for_node_type("block_entry", text) == ("block_entry", text)


def test_parse_text_block_entry_reject_comment_marker():
    # The value is written back on one line, so a comment would swallow the
    # rest of the block.
    text = "hex (0 1 2 3 4 5 6 7) // note\n(1 1 1)"
    assert parse_text_for_node_type("block_entry", text) == (None, None)


def test_parse_text_block_entry_reject_too_few_vertices():
    assert parse_text_for_node_type("block_entry", "hex (0 1 2)") == (None, None)


def test_parse_text_block_entry_reject_non_hex_shape_word():
    assert parse_text_for_node_type("block_entry", "foo (0 1 2 3 4 5 6 7)") == (None, None)


def test_parse_text_block_entry_reject_unbalanced_parens():
    assert parse_text_for_node_type("block_entry", "hex (0 1 2 3 4 5 6 7") == (None, None)


def test_set_node_value_block_entry_rejected_edit_leaves_node_untouched():
    node = FoamNode(name="", node_type="block_entry", value="hex (0 1 2 3 4 5 6 7) (1 1 1)")
    ok = set_node_value(node, "hex (0 1 2)")
    assert ok is False
    assert node.node_type == "block_entry"
    assert node.value == "hex (0 1 2 3 4 5 6 7) (1 1 1)"
    assert node.modified is False


def test_set_node_value_block_entry_accepted_edit():
    node = FoamNode(name="", node_type="block_entry", value="hex (0 1 2 3 4 5 6 7) (1 1 1)")
    ok = set_node_value(node, "hex (0 1 2 3 4 5 6 7) (2 2 2)")
    assert ok is True
    assert node.value == "hex (0 1 2 3 4 5 6 7) (2 2 2)"
    assert node.modified is True


# ── set_node_value ──────────────────────────────────────────────────────────


def test_set_node_value_int_accept():
    node = FoamNode(name="writeInterval", node_type="int", value=1)
    ok = set_node_value(node, "100")
    assert ok is True
    assert node.node_type == "int"
    assert node.value == 100
    assert node.modified is True


def test_set_node_value_int_reject_leaves_node_unchanged():
    node = FoamNode(name="writeInterval", node_type="int", value=1)
    ok = set_node_value(node, "notanumber")
    assert ok is False
    assert node.node_type == "int"
    assert node.value == 1
    assert node.modified is False


def test_set_node_value_int_promotes_to_scalar():
    node = FoamNode(name="writeInterval", node_type="int", value=1)
    ok = set_node_value(node, "0.5")
    assert ok is True
    assert node.node_type == "scalar"
    assert node.value == 0.5
    assert node.modified is True


def test_set_node_value_scalar_reject():
    node = FoamNode(name="deltaT", node_type="scalar", value=0.001)
    ok = set_node_value(node, "notanumber")
    assert ok is False
    assert node.value == 0.001
    assert node.modified is False


def test_set_node_value_vector_accept():
    node = FoamNode(name="g", node_type="vector", value=[0.0, 0.0, -9.81])
    ok = set_node_value(node, "(1 2 3)")
    assert ok is True
    assert node.value == [1.0, 2.0, 3.0]
    assert node.modified is True


def test_set_node_value_bool_case_insensitive():
    node = FoamNode(name="adjustTimeStep", node_type="bool", value="no")
    ok = set_node_value(node, "YES")
    assert ok is True
    assert node.node_type == "bool"
    assert node.value == "yes"
    assert node.modified is True


def test_set_node_value_word_accept():
    node = FoamNode(name="application", node_type="word", value="icoFoam")
    ok = set_node_value(node, "simpleFoam")
    assert ok is True
    assert node.value == "simpleFoam"
    assert node.modified is True


def test_set_node_value_directive_entry_always_accepts():
    node = FoamNode(name="", node_type="directive_entry", value="#include \"foo\"")
    ok = set_node_value(node, '#include "bar"')
    assert ok is True
    assert node.value == '#include "bar"'
    assert node.modified is True


def test_set_node_value_unknown_raw_entry_always_accepts():
    node = FoamNode(name="", node_type="unknown_raw_entry", value="garbled;")
    ok = set_node_value(node, "still garbled;")
    assert ok is True
    assert node.value == "still garbled;"
    assert node.modified is True


def test_set_node_value_field_value_scalar():
    """field_value nodes route through classify_simple_value, not node_type."""
    node = FoamNode(
        name="inlet",
        node_type="field_value",
        value={
            "field_type": "uniform",
            "field_name": "inlet",
            "value_type": "scalar",
            "value": 0.0,
            "raw_value": "0",
        },
    )
    ok = set_node_value(node, "1.5")
    assert ok is True
    assert node.node_type == "field_value"  # field_value itself never changes
    assert node.value["value_type"] == "scalar"
    assert node.value["value"] == 1.5
    assert node.value["raw_value"] == "1.5"
    assert node.modified is True


def test_set_node_value_field_value_vector():
    node = FoamNode(
        name="inlet",
        node_type="field_value",
        value={
            "field_type": "uniform",
            "field_name": "inlet",
            "value_type": "vector",
            "value": [0.0, 0.0, 0.0],
            "raw_value": "(0 0 0)",
        },
    )
    ok = set_node_value(node, "(1 2 3)")
    assert ok is True
    assert node.value["value_type"] == "vector"
    assert node.value["value"] == [1.0, 2.0, 3.0]
    assert node.modified is True


def test_set_node_value_field_value_word_fallback():
    """classify_simple_value falls back to 'word' for non-numeric, non-parenthesized text."""
    node = FoamNode(
        name="inlet",
        node_type="field_value",
        value={
            "field_type": "uniform",
            "field_name": "inlet",
            "value_type": "word",
            "value": "calculated",
            "raw_value": "calculated",
        },
    )
    ok = set_node_value(node, "fixedValue")
    assert ok is True
    assert node.value["value_type"] == "word"
    assert node.value["value"] == "fixedValue"
