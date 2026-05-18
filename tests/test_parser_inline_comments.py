# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
import pytest
from foam.parser import OpenFoamParser


def child_by_name(node, name):
    for child in node.children:
        if child.name == name:
            return child
    raise AssertionError(f"child not found: {name!r}")


# ── Bug 1: inline comments inside a parenthesised list ───────────────────────
# LINE_COMMENT at depth > 0 previously raised ParseError in
# _read_value_text_until_semicolon, so the vertices node fell back to
# unknown_raw_entry instead of raw_list.

VERTICES_WITH_COMMENTS = """
FoamFile { version 2.0; format ascii; class dictionary; object blockMeshDict; }
scale 1;
vertices
(
    (0 0 0) //0
    (1 0 0) //1
    (1 1 0) //2
    (0 1 0) //3
    (0 0 1) //4
    (1 0 1) //5
    (1 1 1) //6
    (0 1 1) //7
);
blocks ( hex (0 1 2 3 4 5 6 7) (1 1 1) simpleGrading (1 1 1) );
boundary ();
"""


def test_vertices_inline_comments_node_type():
    root = OpenFoamParser(VERTICES_WITH_COMMENTS).parse()
    vertices = child_by_name(root, "vertices")
    assert vertices.node_type == "raw_list", (
        f"expected raw_list but got {vertices.node_type!r} — "
        "inline comments inside vertices block likely caused a ParseError"
    )


def test_vertices_inline_comments_value_contains_coords():
    root = OpenFoamParser(VERTICES_WITH_COMMENTS).parse()
    vertices = child_by_name(root, "vertices")
    val = str(vertices.value)
    assert "0 0 0" in val
    assert "1 1 1" in val


# ── Bug 2: comment between region name and its opening brace ─────────────────
# _skip_soft_trivia() after the region name did not consume comments, so
# _check("LBRACE") saw LINE_COMMENT and raised ParseError, losing the whole
# region_block.

SET_FIELDS_WITH_COMMENTS = """
FoamFile { version 2.0; format ascii; class dictionary; object setFieldsDict; }
defaultFieldValues ( volScalarFieldValue p 0 );
regions
(
    boxToCell // the refinement box
    {
        box (0 0 0) (1 1 1);
        fieldValues ( volScalarFieldValue p 1 );
    }
    boxToCell /* another box */
    {
        box (2 2 2) (3 3 3);
        fieldValues ( volScalarFieldValue p 2 );
    }
);
"""


def test_regions_comment_between_name_and_brace_node_type():
    root = OpenFoamParser(SET_FIELDS_WITH_COMMENTS).parse()
    regions = child_by_name(root, "regions")
    assert regions.node_type == "region_block"


def test_regions_comment_between_name_and_brace_children():
    root = OpenFoamParser(SET_FIELDS_WITH_COMMENTS).parse()
    regions = child_by_name(root, "regions")
    assert len(regions.children) == 2
    for child in regions.children:
        assert child.node_type == "region_entry"


# ── Bug 3: inline comments inside a parenthesised embedded value ─────────────
# The catch-all parts.append(tok.text) in _read_parenthesized_text included
# comment text verbatim, corrupting values like per-component annotated vectors.

FIELD_VALUE_WITH_COMMENTS = """
FoamFile { version 2.0; format ascii; class dictionary; object setFieldsDict; }
defaultFieldValues
(
    volVectorFieldValue U (
        0  // x
        0  // y
        1  // z
    )
);
"""


def test_embedded_vector_inline_comments_type():
    root = OpenFoamParser(FIELD_VALUE_WITH_COMMENTS).parse()
    block = child_by_name(root, "defaultFieldValues")
    assert block.node_type == "field_value_block"
    item = block.value[0]
    assert item.value["value_type"] == "vector"


def test_embedded_vector_inline_comments_value():
    root = OpenFoamParser(FIELD_VALUE_WITH_COMMENTS).parse()
    block = child_by_name(root, "defaultFieldValues")
    item = block.value[0]
    assert item.value["value"] == pytest.approx([0.0, 0.0, 1.0])
