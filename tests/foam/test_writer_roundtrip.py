# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
import pytest

from foam.nodes import FoamNode
from foam.parser import OpenFoamParser
from foam.writer import write_root


def find_child(node, name):
    for child in node.children:
        if child.name == name:
            return child
    raise AssertionError(f"child not found: {name}")


def test_writer_roundtrip_control_dict(control_dict_text):
    root = OpenFoamParser(control_dict_text).parse()
    out = write_root(root)

    assert "application     interFoam;" in out
    assert "deltaT          0.005;" in out
    assert "runTimeModifiable true;" in out


def test_writer_after_edit(control_dict_text):
    root = OpenFoamParser(control_dict_text).parse()
    delta_t = find_child(root, "deltaT")
    delta_t.value = 0.01
    delta_t.modified = True

    out = write_root(root)
    assert "deltaT 0.01;" in out or "deltaT          0.01;" in out

def test_writer_unmodified_node_uses_raw_text(control_dict_text):
    """Unmodified nodes are written using their original raw_text"""
    root = OpenFoamParser(control_dict_text).parse()
    out = write_root(root)
    # no modifications, so original text entries should be preserved
    assert "interFoam" in out
    assert "runTimeModifiable" in out
    assert "timeStep" in out


def test_writer_modified_word_node(control_dict_text):
    """Writing a modified word node outputs the new value"""
    root = OpenFoamParser(control_dict_text).parse()
    app = find_child(root, "application")
    app.value = "simpleFoam"
    app.modified = True
    out = write_root(root)
    assert "simpleFoam" in out


def test_writer_modified_int_node(control_dict_text):
    """Writing a modified int node outputs the new integer value"""
    root = OpenFoamParser(control_dict_text).parse()
    write_interval = find_child(root, "writeInterval")
    write_interval.value = 50
    write_interval.modified = True
    out = write_root(root)
    assert "50" in out


def test_writer_modified_scalar_node(control_dict_text):
    """Writing a modified scalar node outputs the new floating-point value"""
    root = OpenFoamParser(control_dict_text).parse()
    delta_t = find_child(root, "deltaT")
    delta_t.value = 0.001
    delta_t.modified = True
    out = write_root(root)
    assert "0.001" in out


def test_writer_directive_entry_preserved():
    """directive_entry is preserved in the written output"""
    text = """
application interFoam;
functions
{
    #includeFunc residuals
}
"""
    root = OpenFoamParser(text).parse()
    out = write_root(root)
    assert "functions" in out
    # directive content must appear in the output
    assert "#includeFunc" in out or "residuals" in out


def test_writer_unknown_raw_entry_preserved():
    """unknown_raw_entry content is preserved in the written output"""
    text = """
someWeirdEntry this is not standard foam;
"""
    root = OpenFoamParser(text).parse()
    out = write_root(root)
    assert "someWeirdEntry" in out


def test_writer_macro_entry_preserved():
    """macro_entry is reproduced with a semicolon in the written output"""
    text = """
solvers
{
    pFinal
    {
        $p;
        relTol 0;
    }
}
"""
    root = OpenFoamParser(text).parse()
    out = write_root(root)
    assert "$p" in out


def test_writer_vector_node():
    """vector node value is written in (x y z) format"""
    text = """
gravity (0 -9.81 0);
"""
    root = OpenFoamParser(text).parse()
    out = write_root(root)
    assert "gravity" in out
    assert "9.81" in out


def test_writer_nested_dictionary():
    """Nested dictionary is written with correct indentation"""
    text = """
outer
{
    inner
    {
        key value;
    }
}
"""
    root = OpenFoamParser(text).parse()
    # set modified flag to force regeneration
    for child in root.children:
        child.modified = True
    out = write_root(root)
    assert "outer" in out
    assert "inner" in out
    assert "key" in out


def test_writer_fv_schemes_roundtrip(fv_schemes_text):
    """All blocks are preserved after fvSchemes parse and write"""
    root = OpenFoamParser(fv_schemes_text).parse()
    out = write_root(root)
    for block in [
        "ddtSchemes", "gradSchemes", "divSchemes",
        "laplacianSchemes", "interpolationSchemes", "snGradSchemes",
    ]:
        assert block in out, f"'{block}' not found in output"
    assert "Euler" in out
    assert "Gauss linear" in out
    assert "orthogonal" in out


def test_writer_fv_solution_roundtrip(fv_solution_text):
    """Key entries are preserved after fvSolution parse and write"""
    root = OpenFoamParser(fv_solution_text).parse()
    out = write_root(root)
    assert "solvers" in out
    assert "PIMPLE" in out
    assert "GAMG" in out
    assert "nCorrectors" in out
    assert "smoothSolver" in out


def test_writer_preserves_runs_of_blank_lines(control_dict_text):
    """Blank-line runs survive verbatim -- the writer does not tidy on save.

    write_root used to collapse every run of 3+ newlines to 2 and strip
    trailing newlines off each node's leading_trivia. Both were band-aids over
    the double-counted newline fixed in _join, and both silently rewrote blank
    lines the user never touched.
    """
    text = control_dict_text.replace(
        "application     interFoam;", "\n\napplication     interFoam;",
    )
    out = write_root(OpenFoamParser(text).parse())
    assert out == text
    assert "\n\n\n\napplication" in out


def test_writer_field_value_block_roundtrip():
    """volScalarFieldValue is preserved after field_value_block parse and write"""
    text = """
defaultFieldValues
(
    volScalarFieldValue alpha.water 0
);
"""
    root = OpenFoamParser(text).parse()
    out = write_root(root)
    assert "defaultFieldValues" in out
    assert "volScalarFieldValue alpha.water 0" in out


def test_writer_region_block_roundtrip():
    """regions/boxToCell structure is preserved after region_block parse and write"""
    text = """
regions
(
    boxToCell
    {
        box (0 0 -1) (0.1 0.2 1);
        fieldValues
        (
            volScalarFieldValue alpha.water 1
        );
    }
);
"""
    root = OpenFoamParser(text).parse()
    out = write_root(root)
    assert "regions" in out
    assert "boxToCell" in out
    assert "box" in out
    assert "fieldValues" in out
    assert "volScalarFieldValue alpha.water 1" in out


def test_writer_modified_field_value_in_region():
    """Writing a modified field_value inside a region outputs the new value"""
    text = """
regions
(
    boxToCell
    {
        box (0 0 -1) (0.1 0.2 1);
        fieldValues
        (
            volScalarFieldValue alpha.water 0
        );
    }
);
"""
    root = OpenFoamParser(text).parse()

    # navigate regions > boxToCell > fieldValues > field_value and change the value
    regions = None
    for child in root.children:
        if child.name == "regions":
            regions = child
            break
    assert regions is not None

    box_to_cell = regions.children[0]
    field_values = None
    for child in box_to_cell.children:
        if child.name == "fieldValues":
            field_values = child
            break
    assert field_values is not None

    item = field_values.value[0]
    item.value["value"] = 1
    item.value["raw_value"] = "1"
    item.modified = True
    field_values.modified = True

    out = write_root(root)
    assert "volScalarFieldValue alpha.water 1" in out


def test_writer_modified_region_entry_keeps_sibling_names():
    """Regression: regenerating one region entry must not drop sibling names.

    Entry raw_text used to start at the "{" (the name token was outside the
    captured span), so unmodified siblings of a modified entry lost their
    names on write.
    """
    text = (
        "regions\n(\n"
        "    boxToCell\n    {\n        box (0 0 -1) (1 1 1);\n"
        "        fieldValues ( volScalarFieldValue alpha.water 1 );\n    }\n"
        "    sphereToCell\n    {\n        centre (0.5 0.5 0.5);\n"
        "        radius 0.1;\n"
        "        fieldValues ( volScalarFieldValue alpha.water 1 );\n    }\n"
        ");\n"
    )
    root = OpenFoamParser(text).parse()
    regions = root.children[0]
    assert regions.children[0].raw_text.startswith("boxToCell")
    regions.children[0].modified = True
    out = write_root(root)
    assert "sphereToCell" in out
    reparsed = OpenFoamParser(out).parse().children[0]
    assert reparsed.node_type == "region_block"
    assert [c.name for c in reparsed.children] == ["boxToCell", "sphereToCell"]


# ── block_list (blockMeshDict blocks) ────────────────────────────────────────

_PITZDAILY_SHAPED_BLOCKS = """\
blocks
(
    hex (0 3 4 1 11 14 15 12) (18 30 1) simpleGrading (0.5 1 1)
    hex (3 2 5 4 14 13 16 15) (18 8 1) simpleGrading (0.5 1 1)
    hex (4 5 6 7 15 16 17 18) (30 8 1) simpleGrading (1 1 1)
    hex (7 8 9 6 18 19 20 17) (30 8 1) simpleGrading (2 1 1)
    hex (9 10 11 6 20 21 15 17) (10 8 1) simpleGrading (0.5 1 1)
);
"""


def test_writer_pitzdaily_shaped_blocks_unmodified_roundtrip():
    root = OpenFoamParser(_PITZDAILY_SHAPED_BLOCKS).parse()
    assert write_root(root) == _PITZDAILY_SHAPED_BLOCKS


def test_writer_single_block_edit_keeps_siblings_byte_identical():
    root = OpenFoamParser(_PITZDAILY_SHAPED_BLOCKS).parse()
    blocks = root.children[0]
    original_raw = [c.raw_text for c in blocks.children]

    blocks.children[3].value = "hex (7 8 9 6 18 19 20 17) (25 15 1) simpleGrading (2 1 1)"
    blocks.children[3].modified = True

    out = write_root(root)

    for i, entry in enumerate(blocks.children):
        if i != 3:
            assert entry.raw_text == original_raw[i]
            assert entry.raw_text in out
    assert "(25 15 1)" in out
    # closing paren stays on its own line, not glued to the last block
    assert "\n);\n" in out


# ── byte-identical round-trip (corpus-shaped) ────────────────────────────────

# Shaped exactly like a real tutorial system/blockMeshDict, carrying every
# whitespace feature the in-repo fixtures happened to lack -- which is why
# write_root could rewrite blank lines in all 441 tutorial blockMeshDicts
# while every test here still passed:
#   * the "// * * *" banner between the FoamFile block and the first entry,
#     followed by a blank line
#   * a two-blank-line gap between entries
#   * the trailing "// ****" footer banner, preceded by two blank lines
_CORPUS_SHAPED_DICT = """\
/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      blockMeshDict;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

scale   0.001;

vertices
(
    (0 0 0)
    (1 0 0)
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
        faces ( (0 1 2 3) );
    }
);


// ************************************************************************* //
"""


def test_writer_corpus_shaped_dict_roundtrips_byte_identically():
    """An unmodified tree must reproduce its source byte for byte.

    Regression: opening a tutorial case and hitting Save rewrote blank lines
    the user never touched -- the blank line after the "// * * *" banner moved
    to before it, two-blank-line gaps collapsed to none, and the trailing
    "// ****" footer banner was dropped outright.
    """
    root = OpenFoamParser(_CORPUS_SHAPED_DICT).parse()
    assert write_root(root) == _CORPUS_SHAPED_DICT


def test_writer_preserves_trailing_footer_banner():
    """The footer banner has no node to attach to; the root must carry it."""
    root = OpenFoamParser(_CORPUS_SHAPED_DICT).parse()
    assert "".join(root.trailing_trivia) == (
        "\n\n\n// ************************************************************************* //\n"
    )
    assert write_root(root).endswith(
        ");\n\n\n// ************************************************************************* //\n"
    )


def test_writer_keeps_blank_line_after_banner_not_before():
    """The banner belongs to the next entry's leading_trivia, blank line last."""
    out = write_root(OpenFoamParser(_CORPUS_SHAPED_DICT).parse())
    assert "}\n// * * *" in out
    assert "* //\n\nscale   0.001;" in out


def test_writer_keeps_double_blank_line_between_entries():
    out = write_root(OpenFoamParser(_CORPUS_SHAPED_DICT).parse())
    assert ");\n\n\nblocks\n" in out


def test_writer_editing_one_entry_leaves_the_rest_byte_identical():
    """The user-visible promise: saving rewrites only what was edited."""
    root = OpenFoamParser(_CORPUS_SHAPED_DICT).parse()
    scale = find_child(root, "scale")
    scale.value = 0.01
    scale.modified = True

    out = write_root(root)
    assert "scale 0.01;" in out
    # everything except the edited line is untouched
    changed = [
        (a, b) for a, b in zip(
            _CORPUS_SHAPED_DICT.splitlines(), out.splitlines(), strict=True,
        ) if a != b
    ]
    assert changed == [("scale   0.001;", "scale 0.01;")]


def test_writer_preserves_missing_final_newline():
    """A source that does not end with a newline must not gain one."""
    text = "scale   0.001;"
    assert write_root(OpenFoamParser(text).parse()) == text


def test_writer_preserves_multiple_entries_on_one_line():
    """Regression: the inter-entry separator can be a space, not a newline.

    A naive "break the line when the previous part did not end with one" rule
    exploded these onto separate lines.
    """
    text = "x1  14; x2   6; x3  20; // X divisions\n"
    assert write_root(OpenFoamParser(text).parse()) == text


def test_writer_new_node_without_trivia_still_gets_its_own_line():
    """Nodes added in the tree carry no trivia, so _join must space them."""
    root = OpenFoamParser("scale   0.001;\n").parse()
    added = FoamNode(name="tolerance", node_type="scalar", value=1e-6, modified=True)
    root.add_child(added)

    out = write_root(root)
    assert out.splitlines() == ["scale   0.001;", "tolerance 1e-06;"]


def test_writer_keeps_a_stray_semicolon_on_the_brace_line():
    """`divSchemes { … };` -- the ";" is its own entry but not its own line.

    It abuts the "}" with no whitespace at all, so it reaches the writer with
    empty leading_trivia, which used to be read as "synthetic node, give it a
    fresh line". 47 v2512 tutorial dictionaries were rewritten to "}\\n;" on
    save because of it.
    """
    text = "divSchemes\n{\n    default Gauss linear;\n};\n\nfoo bar;\n"
    assert write_root(OpenFoamParser(text).parse()) == text


def test_writer_stray_semicolon_nested_is_not_indented():
    """The ";" continues the "}" line, so it must not take that line's indent."""
    text = "solvers\n{\n    p\n    {\n        solver PCG;\n    };\n}\n"
    root = OpenFoamParser(text).parse()
    # Force regeneration so the ";" goes through _write_inline_entry rather
    # than the raw_text passthrough.
    semicolon = root.children[0].children[1]
    assert semicolon.node_type == "unknown_raw_entry"
    semicolon.modified = True

    out = write_root(root)
    assert "    };\n" in out
    assert "}    ;" not in out


# ── indentation of a regenerated node's own first line ───────────────────────

# Regenerating a *nested* entry used to indent its first line twice: the node's
# leading_trivia already ends with the source's own indentation, and the writer
# prepended _indent() on top of it. Editing `nCorrectors` inside `PIMPLE {}`
# moved it from 4 spaces to 8. Every renderer that starts a line was affected;
# only _write_block_entry compensated, which is why nothing caught it.
_NESTED = {
    "dictionary":        ("outer\n{\n    p\n    {\n        a b;\n    }\n}\n", (0, 0)),
    "simple entry":      ("outer\n{\n    a b;\n}\n", (0, 0)),
    "directive_entry":   ("outer\n{\n    #includeFunc residuals\n}\n", (0, 0)),
    "macro_entry":       ("outer\n{\n    $p;\n}\n", (0, 0)),
    "macro_entry (no ;)": ("outer\n{\n    $p\n}\n", (0, 0)),
    "macro_entry (braced)": ("outer\n{\n    ${../p};\n}\n", (0, 0)),
    "region_entry":      ("regions\n(\n    boxToCell\n    {\n        a b;\n    }\n);\n", (0, 0)),
    "action_entry":      ("actions\n(\n    {\n        name c0;\n    }\n);\n", (0, 0)),
    "field_value_block": (
        "outer\n{\n    fieldValues\n    (\n        volScalarFieldValue alpha 1\n    );\n}\n",
        (0, 0),
    ),
    "deeply nested":     (
        "a\n{\n    b\n    {\n        c\n        {\n            d e;\n        }\n    }\n}\n",
        (0, 0, 0),
    ),
}


@pytest.mark.parametrize("text,path", _NESTED.values(), ids=list(_NESTED))
def test_writer_regenerated_nested_node_keeps_its_indent(text, path):
    root = OpenFoamParser(text).parse()
    node = root
    for i in path:
        node = node.children[i]
    node.modified = True

    # Nothing about the node changed, so forcing regeneration must reproduce
    # the source exactly -- including the indentation of its own first line.
    assert write_root(root) == text


def test_writer_regenerated_node_at_left_margin_gets_the_generated_indent():
    """The trivia-ends-in-whitespace rule must not swallow a needed indent.

    A source that put a nested entry at column 0 has trivia ending in "\\n", so
    the writer supplies the indent itself -- otherwise "Add Entry After" inside
    a dictionary would emit unindented lines.
    """
    root = OpenFoamParser("outer\n{\na b;\n}\n").parse()
    root.children[0].children[0].modified = True

    assert write_root(root) == "outer\n{\n    a b;\n}\n"


def test_writer_region_block_newline_normalisation_regression():
    """Regression: an unmodified last child's raw_text has no trailing '\\n'
    ('}' from _parse_dictionary_entry), so a region_block forced to
    regenerate (because a sibling was modified) used to glue the closing
    ');' onto the last child's line -- '    });' instead of '    }\\n);'.
    """
    text = (
        "regions\n(\n"
        "    boxToCell\n    {\n        box (0 0 -1) (1 1 1);\n    }\n"
        "    sphereToCell\n    {\n        centre (0.5 0.5 0.5);\n"
        "        radius 0.1;\n    }\n"
        ");\n"
    )
    root = OpenFoamParser(text).parse()
    regions = root.children[0]
    # Modify the FIRST entry so the last (sphereToCell) stays unmodified and
    # is written via its raw_text early-return path.
    regions.children[0].modified = True

    out = write_root(root)
    assert "});" not in out
    assert "}\n);\n" in out


# ── macro entries: braced references and the optional semicolon ───────────────
#
# OpenFOAM writes a macro statement two ways -- `$p;` and a bare `$p` -- and the
# reference itself may be braced with a scope path (`${../_bladeForces}`). Both
# used to be parse failures: the lexer ended a word at `{`, leaving a stray `$`,
# and the parser required the `;`. Together they were all 38 of the remaining
# ParseErrors across the v2512 tutorials.

def _entries(text: str, *path: int):
    node = OpenFoamParser(text).parse()
    for i in path:
        node = node.children[i]
    return node


def test_braced_macro_parses_as_macro_entry():
    node = _entries("blade0\n{\n    ${../_bladeForces};\n}\n", 0, 0)
    assert node.node_type == "macro_entry"
    assert node.value == "${../_bladeForces}"


def test_macro_without_semicolon_parses_as_macro_entry():
    node = _entries("maxX\n{\n    $minX\n}\n", 0, 0)
    assert node.node_type == "macro_entry"
    assert node.value == "$minX"


def test_macro_without_semicolon_is_not_a_parse_error():
    parser = OpenFoamParser("maxX\n{\n    $minX\n}\n")
    parser.parse()
    assert parser.errors == []


def test_macro_without_semicolon_leaves_following_entry_intact():
    # The trivia after the macro belongs to the next entry, so peeking for the
    # `;` must not consume it.
    dict_node = _entries('"pcorr.*"\n{\n    $p\n    tolerance 0.02;\n}\n', 0)
    assert [c.node_type for c in dict_node.children] == ["macro_entry", "scalar"]
    assert dict_node.children[1].name == "tolerance"


@pytest.mark.parametrize("text", [
    "maxX\n{\n    $minX\n}\n",
    "blade0\n{\n    ${../_bladeForces};\n}\n",
    "blade0\n{\n    ${../_bladeForces}\n}\n",
    "a\n{\n    $p;   // keep\n}\n",
    "a\n{\n    $p   // keep\n}\n",
], ids=["bare", "braced", "braced bare", "semicolon+comment", "bare+comment"])
def test_macro_forms_round_trip_unchanged(text):
    assert write_root(OpenFoamParser(text).parse()) == text


@pytest.mark.parametrize("text,expected", [
    ("a\n{\n    $p;\n}\n", "$p;"),
    ("a\n{\n    $p\n}\n", "$p"),
    ("a\n{\n    $p;   // keep\n}\n", "$p;"),
    ("a\n{\n    $p   // keep\n}\n", "$p"),
], ids=["semicolon", "bare", "semicolon+comment", "bare+comment"])
def test_regenerated_macro_keeps_its_own_terminator(text, expected):
    """An edited macro must not gain or lose the `;` the source had."""
    root = OpenFoamParser(text).parse()
    node = root.children[0].children[0]
    node.modified = True
    out = write_root(root)
    assert expected in out
    assert out == text


def test_new_macro_entry_defaults_to_a_semicolon():
    # A node the app builds has no raw_text to consult.
    root = OpenFoamParser("a\n{\n}\n").parse()
    root.children[0].add_child(FoamNode(name="", node_type="macro_entry", value="$p"))
    root.children[0].modified = True
    assert "$p;" in write_root(root)
