# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
import pytest

from foam.block_mesh_extractor import extract_block_mesh_data
from foam.parser import OpenFoamParser

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


def test_extract_boundary_faces():
    root = OpenFoamParser(BLOCK_MESH_DICT).parse()
    data = extract_block_mesh_data(root)
    assert set(data.boundary_faces.keys()) == {"inlet", "outlet", "walls", "frontAndBack"}
    assert data.boundary_faces["inlet"] == ("patch", [[0, 4, 7, 3]])
    assert data.boundary_faces["outlet"] == ("patch", [[1, 2, 6, 5]])
    assert data.boundary_faces["walls"] == ("wall", [[0, 1, 5, 4], [3, 7, 6, 2]])
    assert data.boundary_faces["frontAndBack"] == ("empty", [[0, 3, 2, 1], [4, 5, 6, 7]])


def test_default_faces_empty_when_boundary_covers_all():
    root = OpenFoamParser(BLOCK_MESH_DICT).parse()
    data = extract_block_mesh_data(root)
    assert data.default_faces == []


def test_default_faces_collects_unassigned_exterior_faces():
    # Drop the frontAndBack patch: its two faces become blockMesh's implicit
    # defaultFaces and must be reported so the 3-D viewer can draw them.
    src = BLOCK_MESH_DICT.replace(
        """    frontAndBack
    {
        type empty;
        faces
        (
            (0 3 2 1)
            (4 5 6 7)
        );
    }
""",
        "",
    )
    data = extract_block_mesh_data(OpenFoamParser(src).parse())
    assert "frontAndBack" not in data.boundary_faces
    assert {frozenset(f) for f in data.default_faces} == {
        frozenset({0, 1, 2, 3}),
        frozenset({4, 5, 6, 7}),
    }


def test_default_faces_claimed_in_any_rotation():
    # A boundary face listed with a different vertex ordering/rotation than the
    # canonical hex face table must still count as claimed.
    src = BLOCK_MESH_DICT.replace("(0 3 2 1)", "(1 0 3 2)")
    data = extract_block_mesh_data(OpenFoamParser(src).parse())
    assert data.default_faces == []


def test_default_faces_skip_interior_faces():
    src = """
FoamFile { version 2.0; format ascii; class dictionary; object blockMeshDict; }
vertices
(
    (0 0 0) (1 0 0) (1 1 0) (0 1 0)
    (0 0 1) (1 0 1) (1 1 1) (0 1 1)
    (2 0 0) (2 1 0) (2 0 1) (2 1 1)
);
blocks
(
    hex (0 1 2 3 4 5 6 7) (1 1 1) simpleGrading (1 1 1)
    hex (1 8 9 2 5 10 11 6) (1 1 1) simpleGrading (1 1 1)
);
boundary
(
);
"""
    data = extract_block_mesh_data(OpenFoamParser(src).parse())
    # 12 block faces total, the shared one (1 2 6 5) appears twice → interior.
    assert len(data.default_faces) == 10
    assert frozenset({1, 2, 6, 5}) not in {frozenset(f) for f in data.default_faces}


def test_default_faces_no_boundary_at_all():
    src = BLOCK_MESH_DICT.split("boundary")[0]
    data = extract_block_mesh_data(OpenFoamParser(src).parse())
    assert len(data.default_faces) == 6


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


def test_boundary_patch_comment_extraction():
    root = OpenFoamParser(BLOCK_MESH_DICT_PATCH_COMMENTS).parse()
    data = extract_block_mesh_data(root)
    assert data.boundary_faces["inlet"] == ("patch", [[0, 4, 7, 3]])
    assert data.boundary_faces["outlet"] == ("patch", [[1, 2, 6, 5]])


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


# ── block_list explosion (Phase 3 canary) ────────────────────────────────────

BLOCK_MESH_DICT_PITZDAILY_SHAPED = """
FoamFile { version 2.0; format ascii; class dictionary; object blockMeshDict; }
posY 0.5;
scale 1;
vertices
(
    (0 0 0) (1 0 0) (1 1 0) (0 1 0)
    (0 0 1) (1 0 1) (1 1 1) (0 1 1)
    (2 0 0) (2 1 0) (2 0 1) (2 1 1)
    (3 0 0) (3 1 0) (3 0 1) (3 1 1)
    (4 0 0) (4 1 0) (4 0 1) (4 1 1)
    (5 0 0) (5 1 0) (5 0 1) (5 1 1)
);
blocks
(
    hex (0 1 2 3 4 5 6 7) (18 30 1) simpleGrading (0.5 $posY 1)
    hex (1 8 9 2 5 10 11 6) (18 8 1) simpleGrading (0.5 1 1)
    hex (8 12 13 9 10 14 15 11) (30 8 1) simpleGrading (1 1 1)
    hex (12 16 17 13 14 18 19 15) (30 8 1) simpleGrading (2 1 1)
    hex (16 20 21 17 18 22 23 19) (10 8 1) simpleGrading (0.5 1 1)
);
boundary ();
"""


def test_block_list_extraction_yields_five_hex_blocks():
    root = OpenFoamParser(BLOCK_MESH_DICT_PITZDAILY_SHAPED).parse()
    blocks_node = next(c for c in root.children if c.name == "blocks")
    assert blocks_node.node_type == "block_list"

    data = extract_block_mesh_data(root)
    assert len(data.hex_blocks) == 5


def test_block_list_extraction_index_parity_with_block_entry_children():
    root = OpenFoamParser(BLOCK_MESH_DICT_PITZDAILY_SHAPED).parse()
    blocks_node = next(c for c in root.children if c.name == "blocks")
    data = extract_block_mesh_data(root)

    assert len(data.hex_blocks) == len(blocks_node.children)
    for hex_block, entry in zip(data.hex_blocks, blocks_node.children):
        assert " ".join(str(v) for v in hex_block) in entry.value


def test_block_list_extraction_macro_grading_does_not_disturb_vertices():
    """$posY inside a block_entry's grading group must not break hex extraction."""
    root = OpenFoamParser(BLOCK_MESH_DICT_PITZDAILY_SHAPED).parse()
    data = extract_block_mesh_data(root)
    assert data.hex_blocks[0] == [0, 1, 2, 3, 4, 5, 6, 7]


BLOCK_MESH_DICT_BOUNDARY_INCLUDE = """
FoamFile { version 2.0; format ascii; class dictionary; object blockMeshDict; }
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


def test_boundary_leading_include_keeps_patch_names():
    """Regression: the directive used to break the structured parse, and the
    raw-text fallback then read "include" as a patch name and gave it the
    *following* patch's faces -- so outlet vanished from the viewer."""
    data = extract_block_mesh_data(
        OpenFoamParser(BLOCK_MESH_DICT_BOUNDARY_INCLUDE).parse()
    )
    assert set(data.boundary_faces) == {"outlet", "sides"}
    assert data.boundary_faces["outlet"] == ("patch", [[1, 2, 6, 5]])
    assert data.boundary_faces["sides"] == ("symmetry", [[0, 4, 7, 3]])


_BLOCKS_WITH_INCLUDE = """
FoamFile { version 2.0; format ascii; class dictionary; object blockMeshDict; }
scale 1;
vertices ( (0 0 0) (1 0 0) (1 1 0) (0 1 0) (0 0 1) (1 0 1) (1 1 1) (0 1 1)
           (2 0 0) (2 1 0) (2 0 1) (2 1 1) );
blocks
(
    #include "blockMeshDict.caseBlocks"

    hex (0 1 2 3 4 5 6 7) (1 1 1) simpleGrading (1 1 1)
    hex (1 8 9 2 5 10 11 6) (1 1 1) simpleGrading (1 1 1)
);
boundary ();
"""


def test_blocks_with_include_still_extract_hex_blocks():
    """An #include among the blocks (like helmholtzResonance in the tutorials)
    no longer degrades the list to raw_list: it becomes a directive_entry
    sibling of the block_entry rows. The directive contributes no hex, so the
    viewer's block indices still count the blocks written in this file only."""
    root = OpenFoamParser(_BLOCKS_WITH_INCLUDE).parse()
    blocks_node = next(c for c in root.children if c.name == "blocks")
    assert blocks_node.node_type == "block_list"

    data = extract_block_mesh_data(root)
    assert data.hex_blocks == [
        [0, 1, 2, 3, 4, 5, 6, 7],
        [1, 8, 9, 2, 5, 10, 11, 6],
    ]


def test_raw_list_fallback_still_extracts_hex_blocks():
    """A list the block lookahead rejects (here a leading non-hex shape) stays
    raw_list, and hex_blocks extraction -- which regex-scans the raw text --
    must still find every hex entry in it."""
    src = _BLOCKS_WITH_INCLUDE.replace(
        '#include "blockMeshDict.caseBlocks"',
        "prism (0 1 2 3 4 5) (1 1 1) simpleGrading (1 1 1)",
    )
    root = OpenFoamParser(src).parse()
    blocks_node = next(c for c in root.children if c.name == "blocks")
    assert blocks_node.node_type == "raw_list"

    data = extract_block_mesh_data(root)
    assert data.hex_blocks == [
        [0, 1, 2, 3, 4, 5, 6, 7],
        [1, 8, 9, 2, 5, 10, 11, 6],
    ]
