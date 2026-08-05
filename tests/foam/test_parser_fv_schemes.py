# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from foam.parser import OpenFoamParser


def find_child(node, name):
    for child in node.children:
        if child.name == name:
            return child
    raise AssertionError(f"child not found: {name}")


def test_parse_fv_schemes_compound_values(fv_schemes_text):
    root = OpenFoamParser(fv_schemes_text).parse()

    grad_schemes = find_child(root, "gradSchemes")
    default = find_child(grad_schemes, "default")
    grad_p = find_child(grad_schemes, "grad(p)")

    assert default.node_type == "compound"
    assert default.value == "Gauss linear"

    assert grad_p.node_type == "compound"
    assert grad_p.value == "Gauss linear"

    laplacian_schemes = find_child(root, "laplacianSchemes")
    lap_default = find_child(laplacian_schemes, "default")
    assert lap_default.node_type == "compound"
    assert lap_default.value == "Gauss linear orthogonal"

def test_parse_fv_schemes_ddt_schemes(fv_schemes_text):
    """ddtSchemes block default entry is parsed correctly"""
    root = OpenFoamParser(fv_schemes_text).parse()
    ddt = find_child(root, "ddtSchemes")
    assert ddt.node_type == "dictionary"
    default = find_child(ddt, "default")
    assert default.value == "Euler"


def test_parse_fv_schemes_div_schemes(fv_schemes_text):
    """divSchemes block default and div(phi,U) entries are parsed correctly"""
    root = OpenFoamParser(fv_schemes_text).parse()
    div = find_child(root, "divSchemes")
    assert div.node_type == "dictionary"

    default = find_child(div, "default")
    assert default.value == "none"

    div_phi_u = find_child(div, "div(phi,U)")
    assert div_phi_u.node_type == "compound"
    assert div_phi_u.value == "Gauss linear"


def test_parse_fv_schemes_interpolation_and_sngrad(fv_schemes_text):
    """interpolationSchemes and snGradSchemes are parsed as dictionaries"""
    root = OpenFoamParser(fv_schemes_text).parse()

    interp = find_child(root, "interpolationSchemes")
    assert interp.node_type == "dictionary"
    interp_default = find_child(interp, "default")
    assert interp_default.value == "linear"

    sn_grad = find_child(root, "snGradSchemes")
    assert sn_grad.node_type == "dictionary"
    sn_default = find_child(sn_grad, "default")
    assert sn_default.value == "orthogonal"


def test_parse_fv_schemes_all_blocks_present(fv_schemes_text):
    """All expected blocks in fvSchemes are present as child nodes"""
    root = OpenFoamParser(fv_schemes_text).parse()
    expected_blocks = [
        "ddtSchemes", "gradSchemes", "divSchemes",
        "laplacianSchemes", "interpolationSchemes", "snGradSchemes",
    ]
    child_names = {child.name for child in root.children}
    for block in expected_blocks:
        assert block in child_names, f"expected block '{block}' not found"


def test_parse_stray_semicolon_is_not_an_error():
    """`divSchemes { … };` is tolerated by OpenFOAM, so it is not a parse failure.

    The ";" still becomes its own node -- the writer has to reproduce it -- but
    reporting it made ordinary tutorial files claim "1 unrecognized entries".
    """
    parser = OpenFoamParser("divSchemes\n{\n    default Gauss linear;\n};\n")
    root = parser.parse()

    assert parser.errors == []
    assert [c.node_type for c in root.children] == ["dictionary", "unknown_raw_entry"]
    assert root.children[1].value == ";"


_MULTIVARIATE = """\
divSchemes
{
    default         none;
    div(phi,U)      Gauss upwind;
    div(phi,Yi_h)   Gauss multivariateSelection
    {
        O2              limitedLinear01 1;
        h               limitedLinear 1;
    };
    div(Ji,Ii_h)    Gauss upwind;
}
"""


def test_parse_dictionary_inside_an_entry_value():
    """A value may end in a whole dictionary, as multivariateSelection does.

    `_read_value_text_until_semicolon` tracks brace depth but had no case for a
    ";" at depth > 0, so it failed at the first entry inside the block. The
    entry degraded to `unknown_raw_entry`, the block's own entries were stranded
    in the enclosing dictionary, and the closing "};" ended `divSchemes` early --
    leaving every later div(...) parsed as a top-level node.
    """
    parser = OpenFoamParser(_MULTIVARIATE)
    root = parser.parse()

    assert parser.errors == []
    # Nothing escaped to the top level.
    assert [c.name for c in root.children] == ["divSchemes"]

    div_schemes = find_child(root, "divSchemes")
    assert [c.name for c in div_schemes.children] == [
        "default", "div(phi,U)", "div(phi,Yi_h)", "div(Ji,Ii_h)",
    ]

    # The block is the entry's value, not a set of sibling nodes.
    embedded = find_child(div_schemes, "div(phi,Yi_h)")
    assert embedded.node_type == "compound"
    assert "multivariateSelection" in embedded.value
    assert "O2 limitedLinear01 1;" in embedded.value
    assert not embedded.children


def test_dictionary_inside_a_value_roundtrips_verbatim():
    from foam.writer import write_root
    assert write_root(OpenFoamParser(_MULTIVARIATE).parse()) == _MULTIVARIATE


_VALUELESS = """\
fluxRequired
{
    default         no;
    p;
    pcorr           ;
    "alpha.*";
}
"""


def test_parse_entry_with_no_value():
    """`fluxRequired { p; }` is a key with no value -- OpenFOAM reads a set of names.

    The value read raised "empty value before semicolon", so each entry became a
    nameless `unknown_raw_entry` and lost the field name that is its entire
    content.
    """
    parser = OpenFoamParser(_VALUELESS)
    root = parser.parse()

    assert parser.errors == []
    flux = find_child(root, "fluxRequired")
    assert [(c.name, c.node_type) for c in flux.children] == [
        ("default", "bool"),
        ("p", "valueless"),
        ("pcorr", "valueless"),
        ('"alpha.*"', "valueless"),
    ]
    assert all(c.value is None for c in flux.children if c.node_type == "valueless")


def test_valueless_entry_roundtrips_verbatim():
    from foam.writer import write_root
    assert write_root(OpenFoamParser(_VALUELESS).parse()) == _VALUELESS


_COMMENT_BEFORE_BRACE = """\
mixture // air at room temperature (293 K)
{
    specie
    {
        molWeight       28.9;
    }
}
"""


def test_comment_between_a_key_and_its_opening_brace():
    """`mixture // …` on the key's line, with the "{" on the next.

    `_skip_soft_trivia` covers whitespace and newlines but not comments, so the
    LBRACE check missed and the entry was read as a value that is not there.
    """
    parser = OpenFoamParser(_COMMENT_BEFORE_BRACE)
    root = parser.parse()

    assert parser.errors == []
    mixture = find_child(root, "mixture")
    assert mixture.node_type == "dictionary"
    assert "air at room temperature" in mixture.inline_comment
    assert find_child(mixture, "specie").node_type == "dictionary"


def test_comment_before_brace_roundtrips_verbatim():
    from foam.writer import write_root
    root = OpenFoamParser(_COMMENT_BEFORE_BRACE).parse()
    assert write_root(root) == _COMMENT_BEFORE_BRACE


def test_comment_before_brace_survives_regeneration():
    """Regenerating the block must keep the comment on the key's line."""
    from foam.writer import write_root

    root = OpenFoamParser(_COMMENT_BEFORE_BRACE).parse()
    find_child(root, "mixture").modified = True
    assert write_root(root).splitlines()[0] == "mixture // air at room temperature (293 K)"


def test_comment_not_before_a_brace_is_left_alone():
    """Only a comment followed by "{" is claimed; other paths are untouched."""
    parser = OpenFoamParser("divSchemes\n{\n    default Gauss linear; // note\n}\n")
    root = parser.parse()

    assert parser.errors == []
    default = find_child(find_child(root, "divSchemes"), "default")
    assert default.value == "Gauss linear"
    assert "note" in default.inline_comment


def test_valueless_entry_regenerates_without_a_stray_space():
    """A regenerated entry must be `p;`, not `p ;` -- there is no value to separate."""
    from foam.nodes import FoamNode
    from foam.writer import write_node

    assert write_node(FoamNode(name="p", node_type="valueless", value=None)) == "p;\n"


def test_parse_fv_schemes_roundtrip(fv_schemes_text):
    """Key entries are preserved after fvSchemes parse and write"""
    from foam.writer import write_root
    root = OpenFoamParser(fv_schemes_text).parse()
    out = write_root(root)
    assert "ddtSchemes" in out
    assert "gradSchemes" in out
    assert "divSchemes" in out
    assert "laplacianSchemes" in out
    assert "interpolationSchemes" in out
    assert "snGradSchemes" in out
