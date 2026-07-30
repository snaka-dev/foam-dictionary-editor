# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for blockMeshDict's `blocks ( hex (...) ... hex ... );` explosion.

The parser explodes a pure `hex` list into a block_list container with one
block_entry child per hex, so the Tree view shows `block 0`...`block N-1`
matching the 3-D viewer's block indices. A non-consuming lookahead
(_looks_like_block_list, mirroring _looks_like_named_dict_list) degrades to
the ordinary raw_list path whenever the list is not pure hex.
"""
from __future__ import annotations

from foam.parser import OpenFoamParser
from foam.writer import write_root


def _parse(text: str):
    return OpenFoamParser(text).parse()


_PITZDAILY_SHAPED = """\
blocks
(
    hex (0 3 4 1 11 14 15 12) (18 30 1) simpleGrading (0.5 1 1)
    hex (3 2 5 4 14 13 16 15) (18 8 1) simpleGrading (0.5 1 1)
    hex (4 5 6 7 15 16 17 18) (30 8 1) simpleGrading (1 1 1)
    hex (7 8 9 6 18 19 20 17) (30 8 1) simpleGrading (2 1 1)
    hex (9 10 11 6 20 21 15 17) (10 8 1) simpleGrading (0.5 1 1)
);
"""


# ── pitzDaily-shaped explosion ─────────────────────────────────────────────

def test_pitzdaily_shaped_explodes_to_block_list():
    root = _parse(_PITZDAILY_SHAPED)
    blocks = root.children[0]
    assert blocks.node_type == "block_list"
    assert blocks.name == "blocks"
    assert len(blocks.children) == 5


def test_pitzdaily_shaped_entries_are_block_entry_anonymous_one_line():
    root = _parse(_PITZDAILY_SHAPED)
    blocks = root.children[0]
    for entry in blocks.children:
        assert entry.node_type == "block_entry"
        assert entry.name == ""
        assert "\n" not in entry.value


# ── degradation cases ───────────────────────────────────────────────────────

def test_empty_blocks_list_stays_raw_list():
    root = _parse("blocks ();\n")
    node = root.children[0]
    assert node.node_type == "raw_list"
    assert node.name == "blocks"


def test_bare_macro_word_list_stays_raw_list():
    root = _parse("blocks ( $b1 $b2 );\n")
    node = root.children[0]
    assert node.node_type == "raw_list"


def test_include_only_blocks_stays_raw_list():
    """Nothing but a directive: there are no blocks here to explode into rows."""
    text = 'blocks\n(\n    #include "blockData"\n);\n'
    root = _parse(text)
    node = root.children[0]
    assert node.node_type == "raw_list"


_BLOCKS_INCLUDE_THEN_HEX = (
    'blocks\n'
    '(\n'
    '    #include "blockMeshDict.caseBlocks"\n'
    '\n'
    '    hex (0 1 2 3 4 5 6 7) (1 1 1) simpleGrading (1 1 1)\n'
    '    hex (1 8 9 2 5 10 11 6) (2 2 2) simpleGrading (1 1 1)\n'
    ');\n'
)


def test_include_beside_hex_blocks_explodes_with_a_directive_child():
    root = _parse(_BLOCKS_INCLUDE_THEN_HEX)
    node = root.children[0]
    assert node.node_type == "block_list"
    assert [c.node_type for c in node.children] == [
        "directive_entry", "block_entry", "block_entry",
    ]
    assert node.children[0].value == '#include "blockMeshDict.caseBlocks"'
    assert node.children[1].value == "hex (0 1 2 3 4 5 6 7) (1 1 1) simpleGrading (1 1 1)"


def test_include_beside_hex_blocks_roundtrip_is_byte_identical():
    root = _parse(_BLOCKS_INCLUDE_THEN_HEX)
    assert write_root(root) == _BLOCKS_INCLUDE_THEN_HEX


def test_include_between_hex_blocks_explodes():
    """The directive need not lead the list."""
    text = (
        'blocks\n'
        '(\n'
        '    hex (0 1 2 3 4 5 6 7) (1 1 1) simpleGrading (1 1 1)\n'
        '    #include "more"\n'
        '    hex (1 8 9 2 5 10 11 6) (2 2 2) simpleGrading (1 1 1)\n'
        ');\n'
    )
    root = _parse(text)
    node = root.children[0]
    assert [c.node_type for c in node.children] == [
        "block_entry", "directive_entry", "block_entry",
    ]
    assert write_root(root) == text


def test_leading_hex2d_stays_raw_list():
    text = "blocks\n(\n    hex2D (0 1 2 3 4 5 6 7) (1 1 1) simpleGrading (1 1 1)\n);\n"
    root = _parse(text)
    node = root.children[0]
    assert node.node_type == "raw_list"


def test_leading_prism_stays_raw_list():
    text = "blocks\n(\n    prism (0 1 2 3 4 5) (1 1 1) simpleGrading (1 1 1)\n);\n"
    root = _parse(text)
    node = root.children[0]
    assert node.node_type == "raw_list"


# ── variant forms parse as one entry each ───────────────────────────────────

def test_zone_name_and_grading_keyword_one_entry():
    text = (
        "blocks\n(\n"
        "    hex (0 1 2 3 4 5 6 7) inlet ($nInlet $nHeight $nWidth) grading (1 1 1)\n"
        ");\n"
    )
    root = _parse(text)
    blocks = root.children[0]
    assert blocks.node_type == "block_list"
    assert len(blocks.children) == 1
    assert blocks.children[0].value == (
        "hex (0 1 2 3 4 5 6 7) inlet ($nInlet $nHeight $nWidth) grading (1 1 1)"
    )


def test_name_prefix_starts_its_own_entry():
    # blockMesh's `name <blockName> hex ( … )` form (mesh/blockMesh/pipe).
    text = (
        "blocks\n(\n"
        "    hex (v0 v1 v2 v3 v4 v5 v6 v7) (8 8 8) grading (1 1 1)\n"
        "    name sideBlock hex (v0 v3 v9 v8 v4 v7 v11 v10) (8 20 8) grading (1 1 1)\n"
        ");\n"
    )
    root = _parse(text)
    blocks = root.children[0]
    assert blocks.node_type == "block_list"
    assert len(blocks.children) == 2
    assert blocks.children[1].value == (
        "name sideBlock hex (v0 v3 v9 v8 v4 v7 v11 v10) (8 20 8) grading (1 1 1)"
    )


def test_bare_name_word_does_not_split_an_entry():
    # `name` without a shape word after it is ordinary trailing content.
    text = "blocks\n(\n    hex (0 1 2 3 4 5 6 7) name (1 1 1)\n);\n"
    root = _parse(text)
    blocks = root.children[0]
    assert blocks.node_type == "block_list"
    assert len(blocks.children) == 1


def test_comment_inside_a_block_is_dropped_from_the_value():
    # A comment between two content tokens must not become literal text in
    # the value: rewriting the entry on one line would comment out the cell
    # counts and grading that follow it.
    text = (
        "blocks\n(\n"
        "    hex (0 1 2 3 4 5 6 7)\n"
        "    // cells below\n"
        "    (10 20 30) simpleGrading (1 1 1)\n"
        ");\n"
    )
    root = _parse(text)
    entry = root.children[0].children[0]
    assert "//" not in entry.value
    assert entry.value == "hex (0 1 2 3 4 5 6 7) (10 20 30) simpleGrading (1 1 1)"


def test_rewriting_an_entry_with_an_inner_comment_keeps_cells_and_grading():
    text = (
        "blocks\n(\n"
        "    hex (0 1 2 3 4 5 6 7)\n"
        "    // cells below\n"
        "    (10 20 30) simpleGrading (1 1 1)\n"
        ");\n"
    )
    root = _parse(text)
    root.children[0].children[0].modified = True

    reparsed = _parse(write_root(root))
    assert reparsed.children[0].children[0].value == (
        "hex (0 1 2 3 4 5 6 7) (10 20 30) simpleGrading (1 1 1)"
    )


def test_unterminated_list_stays_on_the_ordinary_value_path():
    # The gate must confirm the list is closed by `);`, otherwise it accepts
    # and _parse_block_list then raises -- turning an entry the ordinary path
    # parses cleanly into an unknown_raw_entry plus a recorded parse error.
    parser = OpenFoamParser(
        "blocks ( hex (0 1 2 3 4 5 6 7) (1 1 1) simpleGrading (1 1 1) ) tail;\n"
    )
    root = parser.parse()
    assert root.children[0].node_type != "block_list"
    assert parser.errors == []


def test_name_prefix_survives_arbitrary_trivia_before_the_shape_word():
    text = (
        "blocks\n(\n"
        "    hex (0 1 2 3 4 5 6 7) (1 1 1) simpleGrading (1 1 1)\n"
        "    name\n"
        "    // comment one\n"
        "    // comment two\n"
        "    blockB hex (4 5 6 7 8 9 10 11) (1 1 1) simpleGrading (1 1 1)\n"
        ");\n"
    )
    root = _parse(text)
    blocks = root.children[0]
    assert len(blocks.children) == 2
    assert blocks.children[1].value.startswith("name blockB hex (4 5 6 7 8 9 10 11)")


def test_bare_macro_tail_one_entry():
    text = "blocks\n(\n    hex (1 0 4 5 9 8 12 13) $blockInfo\n);\n"
    root = _parse(text)
    blocks = root.children[0]
    assert blocks.node_type == "block_list"
    assert len(blocks.children) == 1
    assert blocks.children[0].value == "hex (1 0 4 5 9 8 12 13) $blockInfo"


def test_edge_grading_twelve_values_one_entry():
    text = (
        "blocks\n(\n"
        "    hex (0 1 2 3 4 5 6 7) (10 10 10) "
        "edgeGrading (1 1 1 1 1 1 1 1 1 1 1 1)\n"
        ");\n"
    )
    root = _parse(text)
    blocks = root.children[0]
    assert blocks.node_type == "block_list"
    assert len(blocks.children) == 1
    assert "edgeGrading (1 1 1 1 1 1 1 1 1 1 1 1)" in blocks.children[0].value


def test_block_split_over_three_lines_one_entry():
    text = (
        "blocks\n(\n"
        "    hex (0 3 4 1 11 14 15 12)\n"
        "    (18 30 1)\n"
        "    simpleGrading (0.5 1 1)\n"
        ");\n"
    )
    root = _parse(text)
    blocks = root.children[0]
    assert blocks.node_type == "block_list"
    assert len(blocks.children) == 1
    entry = blocks.children[0]
    assert entry.value == "hex (0 3 4 1 11 14 15 12) (18 30 1) simpleGrading (0.5 1 1)"


# ── comments ─────────────────────────────────────────────────────────────────

def test_inline_comment_on_block_line():
    text = (
        "blocks\n(\n"
        "    hex (0 1 2 3 4 5 6 7) (1 1 1) simpleGrading (1 1 1) // block 0\n"
        "    hex (1 8 9 2 5 10 11 6) (1 1 1) simpleGrading (1 1 1)\n"
        ");\n"
    )
    root = _parse(text)
    blocks = root.children[0]
    assert len(blocks.children) == 2
    assert blocks.children[0].inline_comment.strip() == "// block 0"
    assert blocks.children[1].inline_comment == ""


def test_standalone_comment_between_blocks_lands_in_next_leading_trivia():
    text = (
        "blocks\n(\n"
        "    hex (0 1 2 3 4 5 6 7) (1 1 1) simpleGrading (1 1 1)\n"
        "    // a standalone comment\n"
        "    hex (1 8 9 2 5 10 11 6) (1 1 1) simpleGrading (1 1 1)\n"
        ");\n"
    )
    root = _parse(text)
    blocks = root.children[0]
    assert len(blocks.children) == 2
    assert blocks.children[0].inline_comment == ""
    assert any("standalone comment" in t for t in blocks.children[1].leading_trivia)


# ── round trip ───────────────────────────────────────────────────────────────

def test_pitzdaily_shaped_unmodified_roundtrip_byte_identical():
    root = _parse(_PITZDAILY_SHAPED)
    assert write_root(root) == _PITZDAILY_SHAPED


def test_modifying_entry_2_leaves_siblings_verbatim_and_closing_paren_own_line():
    root = _parse(_PITZDAILY_SHAPED)
    blocks = root.children[0]
    original_raw = [c.raw_text for c in blocks.children]

    blocks.children[2].value = "hex (4 5 6 7 15 16 17 18) (30 8 1) simpleGrading (3 1 1)"
    blocks.children[2].modified = True

    out = write_root(root)

    # Siblings still carry their original raw_text (unaffected by the edit).
    for i, entry in enumerate(blocks.children):
        if i != 2:
            assert entry.raw_text == original_raw[i]
            assert entry.raw_text in out

    assert "simpleGrading (3 1 1)" in out
    assert out.rstrip("\n").endswith(");")

    reparsed = _parse(out).children[0]
    assert reparsed.node_type == "block_list"
    assert len(reparsed.children) == 5


def test_include_inside_blocks_is_resolvable_directive():
    """A directive inside `blocks ( … )` still parses as a resolvable include.

    Include support keys off node_type, not tree position, so a directive
    nested in a positional list must round-trip through the resolver too.
    """
    from foam.include_resolver import parse_include_directive

    root = _parse(_BLOCKS_INCLUDE_THEN_HEX)
    directive = root.children[0].children[0]
    assert directive.node_type == "directive_entry"

    ref = parse_include_directive(str(directive.value))
    assert ref is not None
    assert ref.kind == "include"
    assert ref.target == "blockMeshDict.caseBlocks"
