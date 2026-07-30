# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

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


# ── positional block-list dispatch table (blocks) ─────────────────────────────

def test_paren_dispatch_contains_blocks_key():
    assert "blocks" in OpenFoamParser._POSITIONAL_BLOCK_PARAMS


def test_paren_dispatch_blocks_handler_differs_from_other_tables():
    assert "blocks" not in OpenFoamParser._FIELD_VALUE_KEYS
    assert "blocks" not in OpenFoamParser._NAMED_BLOCK_PARAMS
    assert "blocks" not in OpenFoamParser._ANONYMOUS_BLOCK_PARAMS
    assert "blocks" not in OpenFoamParser._OPTIONAL_NAMED_BLOCK_PARAMS
    assert OpenFoamParser._POSITIONAL_BLOCK_PARAMS["blocks"] == ("block_list", "block_entry")


def test_paren_dispatch_positional_block_params_extensible_at_runtime():
    original = dict(OpenFoamParser._POSITIONAL_BLOCK_PARAMS)
    try:
        OpenFoamParser._POSITIONAL_BLOCK_PARAMS["customShapes"] = (
            "custom_shape_list", "custom_shape_entry",
        )
        assert "customShapes" in OpenFoamParser._POSITIONAL_BLOCK_PARAMS
    finally:
        OpenFoamParser._POSITIONAL_BLOCK_PARAMS.clear()
        OpenFoamParser._POSITIONAL_BLOCK_PARAMS.update(original)


def test_dispatch_unchanged_behavior_blocks():
    text = (
        "FoamFile { version 2.0; format ascii; class dictionary; object blockMeshDict; }\n"
        "blocks\n"
        "(\n"
        "    hex (0 1 2 3 4 5 6 7) (1 1 1) simpleGrading (1 1 1)\n"
        ");\n"
    )
    root = OpenFoamParser(text).parse()
    node = next(c for c in root.children if c.name == "blocks")
    assert node.node_type == "block_list"


def test_dispatch_blocks_falls_back_to_raw_list_on_bare_word_list():
    text = (
        "FoamFile { version 2.0; format ascii; class dictionary; object blockMeshDict; }\n"
        "blocks ( $b1 $b2 );\n"
    )
    root = OpenFoamParser(text).parse()
    node = next(c for c in root.children if c.name == "blocks")
    assert node.node_type == "raw_list"
