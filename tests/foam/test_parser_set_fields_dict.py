# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from foam.parser import OpenFoamParser
from foam.writer import write_root


def child_by_name(node, name):
    for child in node.children:
        if child.name == name:
            return child
    raise AssertionError(f"child not found: {name}")


def test_parse_set_fields_dict():
    text = """
defaultFieldValues
(
    volScalarFieldValue alpha.water 0
);

regions
(
    boxToCell
    {
        box (0 0 -1) (0.1461 0.292 1);
        fieldValues
        (
            volScalarFieldValue alpha.water 1
        );
    }
);
"""

    root = OpenFoamParser(text).parse()

    defaults = child_by_name(root, "defaultFieldValues")
    assert defaults.node_type == "field_value_block"
    assert len(defaults.value) == 1

    fv0 = defaults.value[0]
    assert fv0.node_type == "field_value"
    assert fv0.value["field_type"] == "volScalarFieldValue"
    assert fv0.value["field_name"] == "alpha.water"
    assert fv0.value["value_type"] == "int"
    assert fv0.value["value"] == 0

    regions = child_by_name(root, "regions")
    assert regions.node_type == "region_block"
    assert len(regions.children) == 1

    box_to_cell = regions.children[0]
    assert box_to_cell.name == "boxToCell"
    assert box_to_cell.node_type == "region_entry"

    box_entry = child_by_name(box_to_cell, "box")
    assert box_entry.node_type == "box_pair"
    assert box_entry.value == [[0.0, 0.0, -1.0], [0.1461, 0.292, 1.0]]

    field_values = child_by_name(box_to_cell, "fieldValues")
    assert field_values.node_type == "field_value_block"
    assert len(field_values.value) == 1

    fv1 = field_values.value[0]
    assert fv1.node_type == "field_value"
    assert fv1.value["field_type"] == "volScalarFieldValue"
    assert fv1.value["field_name"] == "alpha.water"
    assert fv1.value["value_type"] == "int"
    assert fv1.value["value"] == 1


def test_parse_set_fields_dict_with_vector_value():
    text = """
defaultFieldValues
(
    volScalarFieldValue alpha.water 0
    volVectorFieldValue U (0 -0.5 0)
);
"""

    root = OpenFoamParser(text).parse()
    defaults = child_by_name(root, "defaultFieldValues")

    assert defaults.node_type == "field_value_block"
    assert len(defaults.value) == 2

    vel = defaults.value[1]
    assert vel.node_type == "field_value"
    assert vel.value["field_type"] == "volVectorFieldValue"
    assert vel.value["field_name"] == "U"
    assert vel.value["value_type"] == "vector"
    assert vel.value["value"] == [0.0, -0.5, 0.0]


def test_parse_box_pair_value():
    text = """
regions
(
    boxToCell
    {
        box (0 0 -1) (0.146 0.292 1);
        fieldValues
        (
            volScalarFieldValue alpha.water 1
        );
    }
);
"""
    root = OpenFoamParser(text).parse()
    regions = child_by_name(root, "regions")
    box_to_cell = regions.children[0]
    box_entry = child_by_name(box_to_cell, "box")

    assert box_entry.node_type == "box_pair"
    assert box_entry.value == [[0.0, 0.0, -1.0], [0.146, 0.292, 1.0]]

    out = write_root(root)
    assert "box (0 0 -1) (0.146 0.292 1);" in out


def test_write_set_fields_dict_roundtrip():
    text = """
defaultFieldValues
(
    volScalarFieldValue alpha.water 0
);

regions
(
    boxToCell
    {
        box (0 0 -1) (0.1461 0.292 1);
        fieldValues
        (
            volScalarFieldValue alpha.water 1
        );
    }
);
"""

    root = OpenFoamParser(text).parse()
    out = write_root(root)

    assert "defaultFieldValues" in out
    assert "regions" in out
    assert "boxToCell" in out
    assert "fieldValues" in out
    assert "volScalarFieldValue alpha.water 1" in out
    assert "box (0 0 -1) (0.1461 0.292 1);" in out


def test_write_modified_set_fields_field_value():
    text = """
defaultFieldValues
(
    volScalarFieldValue alpha.water 0
);
"""

    root = OpenFoamParser(text).parse()
    defaults = child_by_name(root, "defaultFieldValues")
    item = defaults.value[0]

    item.value["value"] = 1
    item.value["raw_value"] = "1"
    item.modified = True
    defaults.modified = True

    out = write_root(root)

    assert "volScalarFieldValue alpha.water 1" in out
