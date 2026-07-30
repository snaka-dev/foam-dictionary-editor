# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
import pytest

from foam.parser import OpenFoamParser
from foam.writer import write_root

BLOCK_MESH_DICT = """
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      blockMeshDict;
}

scale 1;

vertices
(
    (0 0 0)
    (1 0 0)
    (1 1 0)
    (0 1 0)
    (0 0 1)
    (1 0 1)
    (1 1 1)
    (0 1 1)
);

blocks
(
    hex (0 1 2 3 4 5 6 7) (10 10 10) simpleGrading (1 1 1)
);

boundary
(
    inlet
    {
        type patch;
        faces
        (
            (0 4 7 3)
        );
    }
    outlet
    {
        type patch;
        faces
        (
            (1 2 6 5)
        );
    }
    walls
    {
        type wall;
        faces
        (
            (0 1 5 4)
            (3 7 6 2)
        );
    }
    frontAndBack
    {
        type empty;
        faces
        (
            (0 3 2 1)
            (4 5 6 7)
        );
    }
);
"""


def child_by_name(node, name):
    for child in node.children:
        if child.name == name:
            return child
    raise AssertionError(f"child not found: {name!r}")


def test_boundary_node_type():
    root = OpenFoamParser(BLOCK_MESH_DICT).parse()
    boundary = child_by_name(root, "boundary")
    assert boundary.node_type == "boundary_block"


def test_boundary_patch_count():
    root = OpenFoamParser(BLOCK_MESH_DICT).parse()
    boundary = child_by_name(root, "boundary")
    assert len(boundary.children) == 4


def test_boundary_patch_node_types():
    root = OpenFoamParser(BLOCK_MESH_DICT).parse()
    boundary = child_by_name(root, "boundary")
    for patch in boundary.children:
        assert patch.node_type == "boundary_entry", f"{patch.name} has wrong type {patch.node_type}"


def test_boundary_patch_names():
    root = OpenFoamParser(BLOCK_MESH_DICT).parse()
    boundary = child_by_name(root, "boundary")
    names = [p.name for p in boundary.children]
    assert names == ["inlet", "outlet", "walls", "frontAndBack"]


def test_boundary_patch_types():
    root = OpenFoamParser(BLOCK_MESH_DICT).parse()
    boundary = child_by_name(root, "boundary")
    expected = {"inlet": "patch", "outlet": "patch", "walls": "wall", "frontAndBack": "empty"}
    for patch in boundary.children:
        type_node = child_by_name(patch, "type")
        assert str(type_node.value) == expected[patch.name]


def test_boundary_patch_faces():
    root = OpenFoamParser(BLOCK_MESH_DICT).parse()
    boundary = child_by_name(root, "boundary")
    walls = next(p for p in boundary.children if p.name == "walls")
    faces_node = child_by_name(walls, "faces")
    assert faces_node.node_type == "raw_list"
    # raw_list value contains both face tuples
    assert "0 1 5 4" in str(faces_node.value)
    assert "3 7 6 2" in str(faces_node.value)


def test_boundary_roundtrip():
    root = OpenFoamParser(BLOCK_MESH_DICT).parse()
    out = write_root(root)
    assert "boundary" in out
    assert "inlet" in out
    assert "outlet" in out
    assert "walls" in out
    assert "frontAndBack" in out
    assert "type wall;" in out
    assert "type empty;" in out


BLOCK_MESH_DICT_INLINE_COMMENTS = """
FoamFile { version 2.0; format ascii; class dictionary; object blockMeshDict; }

convertToMeters 0.01;

vertices
(
    (-1.5 -5 -0.05) //0
    (1.5 -5 -0.05) //1
    (1.5 5 -0.05) //2
    (-1.5 5 -0.05) //3
    (-1.5 -5 0.05) //4
    (1.5 -5 0.05) //5
    (1.5  5 0.05) //6
    (-1.5 5 0.05) //7
);

blocks
(
    hex (0 1 2 3 4 5 6 7) (30 100 1) simpleGrading (1 1 1)
);

boundary ();
"""


def test_vertices_with_inline_comments_node_type():
    root = OpenFoamParser(BLOCK_MESH_DICT_INLINE_COMMENTS).parse()
    vertices = child_by_name(root, "vertices")
    assert vertices.node_type == "raw_list", (
        f"expected raw_list but got {vertices.node_type!r} — "
        "inline comments inside vertices block likely caused a ParseError"
    )


BLOCK_MESH_DICT_PATCH_COMMENTS = """
FoamFile { version 2.0; format ascii; class dictionary; object blockMeshDict; }
scale 1;
vertices ( (0 0 0) (1 0 0) (1 1 0) (0 1 0) (0 0 1) (1 0 1) (1 1 1) (0 1 1) );
blocks ( hex (0 1 2 3 4 5 6 7) (1 1 1) simpleGrading (1 1 1) );
boundary
(
    inlet // the inlet patch
    {
        type patch;
        faces ( (0 4 7 3) );
    }
    outlet /* the outlet */ {
        type patch;
        faces ( (1 2 6 5) );
    }
);
"""


def test_boundary_patch_comment_between_name_and_brace():
    root = OpenFoamParser(BLOCK_MESH_DICT_PATCH_COMMENTS).parse()
    boundary = child_by_name(root, "boundary")
    assert boundary.node_type == "boundary_block"
    names = [p.name for p in boundary.children]
    assert names == ["inlet", "outlet"]


BLOCK_MESH_DICT_BOUNDARY_INCLUDE = """FoamFile { version 2.0; format ascii; class dictionary; \
object blockMeshDict; }
scale 1;
vertices ( (0 0 0) (1 0 0) (1 1 0) (0 1 0) (0 0 1) (1 0 1) (1 1 1) (0 1 1) );
blocks ( hex (0 1 2 3 4 5 6 7) (1 1 1) simpleGrading (1 1 1) );

boundary
(
    #include "blockMeshDict.caseBoundary"

    outlet
    {
        type patch;
        faces ( (1 2 6 5) );
    }

    sides
    {
        type symmetry;
        faces ( (0 4 7 3) );
    }
);
"""


def test_boundary_leading_include_keeps_structured_parse():
    """A directive standing among the patches (helmholtzResonance in the
    tutorials) must not degrade the whole block to unknown_raw_entry."""
    parser = OpenFoamParser(BLOCK_MESH_DICT_BOUNDARY_INCLUDE)
    root = parser.parse()
    assert parser.errors == []
    boundary = child_by_name(root, "boundary")
    assert boundary.node_type == "boundary_block"


def test_boundary_leading_include_becomes_directive_child():
    root = OpenFoamParser(BLOCK_MESH_DICT_BOUNDARY_INCLUDE).parse()
    boundary = child_by_name(root, "boundary")
    types = [(c.node_type, c.name) for c in boundary.children]
    assert types == [
        ("directive_entry", ""),
        ("boundary_entry", "outlet"),
        ("boundary_entry", "sides"),
    ]
    assert boundary.children[0].value == '#include "blockMeshDict.caseBoundary"'


def test_boundary_leading_include_roundtrip_is_byte_identical():
    root = OpenFoamParser(BLOCK_MESH_DICT_BOUNDARY_INCLUDE).parse()
    assert write_root(root) == BLOCK_MESH_DICT_BOUNDARY_INCLUDE


def test_read_parenthesized_text_skips_inline_comments():
    # Inline comments inside a parenthesised embedded value must not
    # pollute the parsed text (they were previously appended verbatim).
    src = """
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
    root = OpenFoamParser(src).parse()
    block = child_by_name(root, "defaultFieldValues")
    assert block.node_type == "field_value_block"
    item = block.value[0]
    assert item.value["value_type"] == "vector"
    assert item.value["value"] == pytest.approx([0.0, 0.0, 1.0])
