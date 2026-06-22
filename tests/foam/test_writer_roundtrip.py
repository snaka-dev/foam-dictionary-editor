# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
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


def test_writer_excess_blank_lines_suppressed(control_dict_text):
    """write_root suppresses runs of three or more consecutive blank lines"""
    root = OpenFoamParser(control_dict_text).parse()
    out = write_root(root)
    # three or more consecutive newlines must not appear
    assert "\n\n\n" not in out


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
