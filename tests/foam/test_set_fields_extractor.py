# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for set_fields_extractor: regions geometry and fieldValues labels."""
from __future__ import annotations

from foam.parser import OpenFoamParser
from foam.set_fields_extractor import extract_set_fields_data


def _parse(text: str):
    return OpenFoamParser(text).parse()


HEADER = """\
FoamFile { version 2.0; format ascii; class dictionary; object setFieldsDict; }
"""

FIELD_VALUES = """\
        fieldValues
        (
            volScalarFieldValue alpha.water 1
        );
"""


def _regions(*entries: str) -> str:
    return HEADER + "regions\n(\n" + "\n".join(entries) + "\n);\n"


def _entry(source: str, body: str, field_values: str = FIELD_VALUES) -> str:
    return f"    {source}\n    {{\n{body}{field_values}    }}\n"


def test_empty_no_region_block():
    data = extract_set_fields_data(_parse(HEADER))
    assert data.shapes == []
    assert data.non_geometric == []


def test_box_to_cell():
    src = _regions(_entry("boxToCell", "        box (0 0 -1) (0.1461 0.292 1);\n"))
    data = extract_set_fields_data(_parse(src))
    assert len(data.shapes) == 1
    s = data.shapes[0]
    assert s.kind == "boxToCell"
    assert s.geometry == {"box": [[0.0, 0.0, -1.0], [0.1461, 0.292, 1.0]]}
    assert s.label == "alpha.water=1"


def test_sphere_to_cell():
    src = _regions(_entry(
        "sphereToCell",
        "        centre (0.5 0.5 0);\n        radius 0.1;\n",
    ))
    data = extract_set_fields_data(_parse(src))
    assert len(data.shapes) == 1
    s = data.shapes[0]
    assert s.kind == "sphereToCell"
    assert s.geometry == {"centre": [0.5, 0.5, 0.0], "radius": 0.1}


def test_cylinder_to_cell():
    src = _regions(_entry(
        "cylinderToCell",
        "        p1 (0 0 0);\n        p2 (0 0 1);\n        radius 0.25;\n",
    ))
    data = extract_set_fields_data(_parse(src))
    assert len(data.shapes) == 1
    s = data.shapes[0]
    assert s.geometry == {"p1": [0.0, 0.0, 0.0], "p2": [0.0, 0.0, 1.0], "radius": 0.25}


def test_multiple_regions():
    src = _regions(
        _entry("boxToCell", "        box (0 0 0) (1 1 1);\n"),
        _entry("sphereToCell", "        centre (2 0 0);\n        radius 0.5;\n"),
    )
    data = extract_set_fields_data(_parse(src))
    assert [s.kind for s in data.shapes] == ["boxToCell", "sphereToCell"]


def test_non_geometric_source_listed():
    src = _regions(_entry("zoneToCell", "        zone  hotZone;\n"))
    data = extract_set_fields_data(_parse(src))
    assert data.shapes == []
    assert len(data.non_geometric) == 1
    assert data.non_geometric[0].kind == "zoneToCell"
    assert data.non_geometric[0].label == "alpha.water=1"


def test_field_values_label_multiple_and_vector():
    field_values = (
        "        fieldValues\n"
        "        (\n"
        "            volScalarFieldValue alpha.water 1\n"
        "            volVectorFieldValue U (0 -0.5 0)\n"
        "        );\n"
    )
    src = _regions(_entry("boxToCell", "        box (0 0 0) (1 1 1);\n", field_values))
    data = extract_set_fields_data(_parse(src))
    assert data.shapes[0].label == "alpha.water=1, U=(0 -0.5 0)"


def test_missing_field_values_gives_empty_label():
    src = _regions(_entry("boxToCell", "        box (0 0 0) (1 1 1);\n", ""))
    data = extract_set_fields_data(_parse(src))
    assert len(data.shapes) == 1
    assert data.shapes[0].label == ""


def test_variable_resolution():
    src = (
        HEADER
        + "waterLevel 0.292;\n"
        + "regions\n(\n"
        + _entry("boxToCell", "        box (0 0 -1) (0.1461 $waterLevel 1);\n")
        + "\n);\n"
    )
    data = extract_set_fields_data(_parse(src))
    assert len(data.shapes) == 1
    assert data.shapes[0].geometry["box"][1][1] == 0.292


def test_unresolvable_geometric_source_not_mislabelled():
    # A geometric source whose geometry fails to resolve must not appear in
    # non_geometric (mirrors topo_set_extractor behaviour).
    src = _regions(_entry("boxToCell", ""))
    data = extract_set_fields_data(_parse(src))
    assert data.shapes == []
    assert data.non_geometric == []
