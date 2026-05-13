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
