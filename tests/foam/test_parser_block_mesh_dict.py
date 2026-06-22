# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
import pytest
from foam.parser import OpenFoamParser
from foam.writer import write_root
from foam.block_mesh_extractor import extract_block_mesh_data


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


def test_extract_boundary_faces():
    root = OpenFoamParser(BLOCK_MESH_DICT).parse()
    data = extract_block_mesh_data(root)
    assert set(data.boundary_faces.keys()) == {"inlet", "outlet", "walls", "frontAndBack"}
    assert data.boundary_faces["inlet"] == ("patch", [[0, 4, 7, 3]])
    assert data.boundary_faces["outlet"] == ("patch", [[1, 2, 6, 5]])
    assert data.boundary_faces["walls"] == ("wall", [[0, 1, 5, 4], [3, 7, 6, 2]])
    assert data.boundary_faces["frontAndBack"] == ("empty", [[0, 3, 2, 1], [4, 5, 6, 7]])


def test_parse_vertices_public_api():
    from foam.block_mesh_extractor import parse_vertices
    raw = "(0 0 0) (1 0 0) (1 1 0) (0 1 0)"
    verts = parse_vertices(raw)
    assert len(verts) == 4
    assert verts[0] == [0.0, 0.0, 0.0]
    assert verts[2] == [1.0, 1.0, 0.0]


def test_parse_vertices_ignores_non_triplets():
    from foam.block_mesh_extractor import parse_vertices
    raw = "(0 0 0) (1 2) (1 1 1)"
    verts = parse_vertices(raw)
    assert len(verts) == 2


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


def test_vertices_with_inline_comments_extraction():
    root = OpenFoamParser(BLOCK_MESH_DICT_INLINE_COMMENTS).parse()
    data = extract_block_mesh_data(root)
    assert len(data.vertices) == 8
    # scale 0.01 applied
    assert data.vertices[0] == pytest.approx([-0.015, -0.05, -0.0005])
    assert data.vertices[6] == pytest.approx([0.015, 0.05, 0.0005])


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


def test_boundary_patch_comment_extraction():
    root = OpenFoamParser(BLOCK_MESH_DICT_PATCH_COMMENTS).parse()
    data = extract_block_mesh_data(root)
    assert data.boundary_faces["inlet"] == ("patch", [[0, 4, 7, 3]])
    assert data.boundary_faces["outlet"] == ("patch", [[1, 2, 6, 5]])


def test_read_parenthesized_text_skips_inline_comments():
    # Inline comments inside a parenthesised embedded value must not
    # pollute the parsed text (they were previously appended verbatim).
    from foam.parser import OpenFoamParser
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


def test_vertices_and_blocks_unaffected():
    root = OpenFoamParser(BLOCK_MESH_DICT).parse()
    data = extract_block_mesh_data(root)
    assert len(data.vertices) == 8
    assert data.vertices[0] == [0.0, 0.0, 0.0]
    assert data.vertices[6] == [1.0, 1.0, 1.0]
    assert len(data.hex_blocks) == 1
    assert data.hex_blocks[0] == [0, 1, 2, 3, 4, 5, 6, 7]


# ── variable resolution ───────────────────────────────────────────────────────

BLOCK_MESH_DICT_WITH_VARS = """
FoamFile { version 2.0; format ascii; class dictionary; object blockMeshDict; }

xMin -0.5;
xMax  0.5;
yMin -0.5;
yMax  0.5;
zMin  0.0;
zMax  1.0;
nX 10;
nY 10;
nZ 20;

scale 1;

vertices
(
    ($xMin $yMin $zMin)
    ($xMax $yMin $zMin)
    ($xMax $yMax $zMin)
    ($xMin $yMax $zMin)
    ($xMin $yMin $zMax)
    ($xMax $yMin $zMax)
    ($xMax $yMax $zMax)
    ($xMin $yMax $zMax)
);

blocks
(
    hex (0 1 2 3 4 5 6 7) ($nX $nY $nZ) simpleGrading (1 1 1)
);

boundary ();
"""


def test_variable_vertices_resolved():
    root = OpenFoamParser(BLOCK_MESH_DICT_WITH_VARS).parse()
    data = extract_block_mesh_data(root)
    assert len(data.vertices) == 8
    assert data.vertices[0] == [-0.5, -0.5, 0.0]
    assert data.vertices[6] == [0.5, 0.5, 1.0]


def test_variable_blocks_resolved():
    root = OpenFoamParser(BLOCK_MESH_DICT_WITH_VARS).parse()
    data = extract_block_mesh_data(root)
    assert len(data.hex_blocks) == 1
    assert data.hex_blocks[0] == [0, 1, 2, 3, 4, 5, 6, 7]


def test_variable_partial_substitution():
    """Variables that are defined resolve; undefined $refs are left as-is and skipped."""
    src = """
    FoamFile { version 2.0; format ascii; class dictionary; object blockMeshDict; }
    xMin -1.0;
    xMax  1.0;
    scale 1;
    vertices ( ($xMin 0 0) ($xMax 0 0) ($xMax 1 0) ($xMin 1 0)
               ($xMin 0 $zMax) ($xMax 0 $zMax) ($xMax 1 $zMax) ($xMin 1 $zMax) );
    blocks ();
    boundary ();
    """
    root = OpenFoamParser(src).parse()
    data = extract_block_mesh_data(root)
    # Vertices with unresolved $zMax cannot be parsed as float — silently skipped
    assert all(v[0] in (-1.0, 1.0) for v in data.vertices)
    assert all(len(v) == 3 for v in data.vertices)


def test_macro_variable_resolved_one_level():
    """Variables defined as macros (nx $nCell) are resolved via a second pass."""
    src = """
    FoamFile { version 2.0; format ascii; class dictionary; object blockMeshDict; }
    scale 1;
    length 10;
    nCell 20;
    nx $nCell; ny $nCell; nz 1;
    xMin 0; xMax $length;
    yMin 0; yMax $length;
    zMin 0; zMax $length;
    vertices
    (
        ($xMin $yMin $zMin)
        ($xMax $yMin $zMin)
        ($xMax $yMax $zMin)
        ($xMin $yMax $zMin)
        ($xMin $yMin $zMax)
        ($xMax $yMin $zMax)
        ($xMax $yMax $zMax)
        ($xMin $yMax $zMax)
    );
    blocks ( hex (0 1 2 3 4 5 6 7) ($nx $ny $nz) simpleGrading (1 1 1) );
    boundary ();
    """
    root = OpenFoamParser(src).parse()
    data = extract_block_mesh_data(root)
    assert len(data.vertices) == 8
    assert data.vertices[0] == [0.0, 0.0, 0.0]
    assert data.vertices[6] == [10.0, 10.0, 10.0]
    assert data.hex_blocks == [[0, 1, 2, 3, 4, 5, 6, 7]]


def test_braced_variable_syntax():
    """${varName} syntax is also resolved."""
    src = """
    FoamFile { version 2.0; format ascii; class dictionary; object blockMeshDict; }
    L 2.0;
    scale 1;
    vertices ( (0 0 0) (${L} 0 0) (${L} ${L} 0) (0 ${L} 0)
               (0 0 ${L}) (${L} 0 ${L}) (${L} ${L} ${L}) (0 ${L} ${L}) );
    blocks ();
    boundary ();
    """
    root = OpenFoamParser(src).parse()
    data = extract_block_mesh_data(root)
    assert len(data.vertices) == 8
    assert data.vertices[6] == [2.0, 2.0, 2.0]


def test_eval_expression_resolved():
    """#eval{ expr } entries are evaluated and usable in vertices."""
    src = """
    FoamFile { version 2.0; format ascii; class dictionary; object blockMeshDict; }
    scale 1;
    length 10.0;
    nCell 5;
    dz   #eval{ $length / $nCell };
    vertices
    (
        (0 0 0) (1 0 0) (1 1 0) (0 1 0)
        (0 0 $dz) (1 0 $dz) (1 1 $dz) (0 1 $dz)
    );
    blocks ();
    boundary ();
    """
    root = OpenFoamParser(src).parse()
    data = extract_block_mesh_data(root)
    assert len(data.vertices) == 8
    assert data.vertices[4] == pytest.approx([0.0, 0.0, 2.0])
    assert data.vertices[6] == pytest.approx([1.0, 1.0, 2.0])


def test_eval_expression_with_multiplication():
    """#eval{ expr } with multiplication and subtraction."""
    src = """
    FoamFile { version 2.0; format ascii; class dictionary; object blockMeshDict; }
    scale 1;
    L 4.0;
    half   #eval{ $L / 2.0 };
    neg    #eval{ -0.5 * $L };
    vertices
    (
        ($neg 0 0) ($half 0 0) ($half $half 0) ($neg $half 0)
        ($neg 0 1) ($half 0 1) ($half $half 1) ($neg $half 1)
    );
    blocks ();
    boundary ();
    """
    root = OpenFoamParser(src).parse()
    data = extract_block_mesh_data(root)
    assert len(data.vertices) == 8
    assert data.vertices[0] == pytest.approx([-2.0, 0.0, 0.0])
    assert data.vertices[2] == pytest.approx([2.0, 2.0, 0.0])


def test_multilevel_variable_chain():
    """Multi-level chains like z1=#eval{...}; z001=$z1; resolve correctly.

    The macro pass for z001 cannot succeed until the #eval pass has computed z1.
    The iterative approach handles this by re-running both passes until stable.
    """
    src = """
    FoamFile { version 2.0; format ascii; class dictionary; object blockMeshDict; }
    scale 1;
    dz0 10; dz1 5;
    z0 0;
    z1 #eval{$z0+$dz0};
    z2 #eval{$z1+$dz1};
    // vertex z-coords are macro refs to the #eval results
    z000 $z0; z001 $z1; z002 $z2;
    x0 0; x1 1;
    vertices
    (
        ($x0 0 $z000) ($x1 0 $z000)
        ($x0 0 $z001) ($x1 0 $z001)
        ($x0 0 $z002) ($x1 0 $z002)
        ($x0 0 $z002) ($x1 0 $z002)
    );
    blocks ();
    boundary ();
    """
    root = OpenFoamParser(src).parse()
    data = extract_block_mesh_data(root)
    assert len(data.vertices) == 8
    # z000=0, z001=10, z002=15
    assert data.vertices[0] == pytest.approx([0.0, 0.0, 0.0])
    assert data.vertices[2] == pytest.approx([0.0, 0.0, 10.0])
    assert data.vertices[4] == pytest.approx([0.0, 0.0, 15.0])


# ── compact (blockIndex, faceIndex) boundary notation ────────────────────────

BLOCK_MESH_DICT_COMPACT_FACES = """
FoamFile { version 2.0; format ascii; class dictionary; object blockMeshDict; }
scale 1;
vertices
(
    (0 0 0) (1 0 0) (1 1 0) (0 1 0)
    (0 0 1) (1 0 1) (1 1 1) (0 1 1)
);
blocks
(
    hex (0 1 2 3 4 5 6 7) (10 10 10) simpleGrading (1 1 1)
);
boundary
(
    xMin { type patch; faces ( (0 0) ); }
    xMax { type patch; faces ( (0 1) ); }
    yMin { type patch; faces ( (0 2) ); }
    yMax { type patch; faces ( (0 3) ); }
    zMin { type patch; faces ( (0 4) ); }
    zMax { type patch; faces ( (0 5) ); }
);
"""


def test_compact_face_notation_expands_to_vertices():
    """(blockIdx, faceIdx) entries are expanded to 4-vertex lists."""
    root = OpenFoamParser(BLOCK_MESH_DICT_COMPACT_FACES).parse()
    data = extract_block_mesh_data(root)
    assert data.boundary_faces["xMin"] == ("patch", [[0, 4, 7, 3]])
    assert data.boundary_faces["xMax"] == ("patch", [[1, 2, 6, 5]])
    assert data.boundary_faces["yMin"] == ("patch", [[0, 1, 5, 4]])
    assert data.boundary_faces["yMax"] == ("patch", [[2, 3, 7, 6]])
    assert data.boundary_faces["zMin"] == ("patch", [[0, 3, 2, 1]])
    assert data.boundary_faces["zMax"] == ("patch", [[4, 5, 6, 7]])


def test_compact_face_notation_with_negated_macro_vars():
    """Compact faces work together with negated-macro vertex variables."""
    src = """
    FoamFile { version 2.0; format ascii; class dictionary; object blockMeshDict; }
    xMax 1; yMax $xMax; zMax $xMax;
    xMin -$xMax; yMin -$yMax; zMin -$zMax;
    scale 1;
    vertices
    (
        ($xMin $yMin $zMin) ($xMax $yMin $zMin)
        ($xMax $yMax $zMin) ($xMin $yMax $zMin)
        ($xMin $yMin $zMax) ($xMax $yMin $zMax)
        ($xMax $yMax $zMax) ($xMin $yMax $zMax)
    );
    blocks ( hex (0 1 2 3 4 5 6 7) (10 10 10) simpleGrading (1 1 1) );
    boundary
    (
        xMin { type patch; faces ( (0 0) ); }
        xMax { type patch; faces ( (0 1) ); }
    );
    """
    root = OpenFoamParser(src).parse()
    data = extract_block_mesh_data(root)
    assert len(data.vertices) == 8
    assert data.boundary_faces["xMin"] == ("patch", [[0, 4, 7, 3]])
    assert data.boundary_faces["xMax"] == ("patch", [[1, 2, 6, 5]])
