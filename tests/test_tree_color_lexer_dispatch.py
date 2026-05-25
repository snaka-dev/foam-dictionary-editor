# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from foam.lexer import OpenFoamLexer
from foam.parser import OpenFoamParser
from model.tree_model import FoamTreeModel


# ── unknown_raw_entry amber colour (#3) ───────────────────────────────────────

def test_unknown_raw_entry_foreground_is_amber():
    text = "} orphan_brace\ngoodKey 1;\n"
    root = OpenFoamParser(text).parse()
    unknown = next(c for c in root.children if c.node_type == "unknown_raw_entry")
    model = FoamTreeModel(root)
    row = root.children.index(unknown)
    idx = model.index(row, FoamTreeModel.COL_KEY)
    colour = model.data(idx, Qt.ForegroundRole)
    assert isinstance(colour, QColor)
    assert colour.name().lower() == "#b8860b"


def test_normal_nodes_have_no_foreground_role():
    root = OpenFoamParser("key 1;\n").parse()
    model = FoamTreeModel(root)
    idx = model.index(0, FoamTreeModel.COL_KEY)
    assert model.data(idx, Qt.ForegroundRole) is None


# ── lexer // behaviour (#5) ───────────────────────────────────────────────────

def test_lexer_double_slash_in_quoted_string_is_not_comment():
    # A double-slash inside a quoted string must NOT start a comment.
    tokens = OpenFoamLexer('"path//value"').tokenize()
    word_tokens = [t for t in tokens if t.kind == "STRING"]
    assert len(word_tokens) == 1
    assert word_tokens[0].text == '"path//value"'


def test_lexer_double_slash_after_whitespace_is_comment():
    tokens = OpenFoamLexer("value // comment\n").tokenize()
    kinds = [t.kind for t in tokens]
    assert "LINE_COMMENT" in kinds
    word_tokens = [t for t in tokens if t.kind == "WORD"]
    assert any(t.text == "value" for t in word_tokens)
    assert not any("comment" in t.text for t in word_tokens)


def test_lexer_double_slash_standalone_starts_comment():
    tokens = OpenFoamLexer("// entire line\n").tokenize()
    assert tokens[0].kind == "LINE_COMMENT"


# ── parser dispatch table (#8) ────────────────────────────────────────────────

def test_paren_dispatch_contains_expected_keys():
    for key in ("defaultFieldValues", "default", "fieldValues"):
        assert key in OpenFoamParser._FIELD_VALUE_KEYS
    for key in ("regions", "boundary"):
        assert key in OpenFoamParser._NAMED_BLOCK_PARAMS


def test_paren_dispatch_field_value_keys_use_same_handler():
    # All three keys are in the same frozenset — they share the field-value path.
    assert {"defaultFieldValues", "default", "fieldValues"} <= OpenFoamParser._FIELD_VALUE_KEYS


def test_paren_dispatch_regions_handler_differs():
    assert "regions" not in OpenFoamParser._FIELD_VALUE_KEYS
    assert "regions" in OpenFoamParser._NAMED_BLOCK_PARAMS


def test_paren_dispatch_boundary_handler_differs():
    assert "boundary" not in OpenFoamParser._FIELD_VALUE_KEYS
    assert OpenFoamParser._NAMED_BLOCK_PARAMS["boundary"] != OpenFoamParser._NAMED_BLOCK_PARAMS["regions"]


def test_paren_dispatch_extensible_at_runtime():
    original = dict(OpenFoamParser._NAMED_BLOCK_PARAMS)
    try:
        OpenFoamParser._NAMED_BLOCK_PARAMS["customBlock"] = ("custom_block", "custom_entry")
        assert "customBlock" in OpenFoamParser._NAMED_BLOCK_PARAMS
    finally:
        OpenFoamParser._NAMED_BLOCK_PARAMS.clear()
        OpenFoamParser._NAMED_BLOCK_PARAMS.update(original)


def test_dispatch_unchanged_behavior_field_values():
    text = (
        "FoamFile { version 2.0; format ascii; class dictionary; object setFieldsDict; }\n"
        "defaultFieldValues\n"
        "(\n"
        "    volScalarFieldValue alpha.water 0\n"
        ");\n"
    )
    root = OpenFoamParser(text).parse()
    node = next(c for c in root.children if c.name == "defaultFieldValues")
    assert node.node_type == "field_value_block"


def test_dispatch_unchanged_behavior_regions():
    text = (
        "FoamFile { version 2.0; format ascii; class dictionary; object setFieldsDict; }\n"
        "regions\n"
        "(\n"
        "    boxToCell { box (0 0 0) (1 1 1); }\n"
        ");\n"
    )
    root = OpenFoamParser(text).parse()
    node = next(c for c in root.children if c.name == "regions")
    assert node.node_type == "region_block"
