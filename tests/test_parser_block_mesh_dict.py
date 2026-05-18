# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
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
        assert patch.node_type == "boundary_entry", (
            f"{patch.name} has wrong type {patch.node_type}"
        )


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
    outlet /* the outlet */
    {
        type patch;
        faces ( (1 2 6 5) );
    }
);
"""


def test_boundary_comment_between_name_and_brace_node_type():
    root = OpenFoamParser(BLOCK_MESH_DICT_PATCH_COMMENTS).parse()
    boundary = child_by_name(root, "boundary")
    assert boundary.node_type == "boundary_block"


def test_boundary_comment_between_name_and_brace_names():
    root = OpenFoamParser(BLOCK_MESH_DICT_PATCH_COMMENTS).parse()
    boundary = child_by_name(root, "boundary")
    assert [p.name for p in boundary.children] == ["inlet", "outlet"]
