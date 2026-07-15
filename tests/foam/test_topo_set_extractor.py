# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for topo_set_extractor: geometry extraction and $var / #eval resolution."""
from __future__ import annotations

import pytest

from foam.parser import OpenFoamParser
from foam.topo_set_extractor import TopoShape, extract_topo_set_data


def _parse(text: str):
    return OpenFoamParser(text).parse()


HEADER = """\
FoamFile { version 2.0; format ascii; class dictionary; object topoSetDict; }
"""


# ── helpers ───────────────────────────────────────────────────────────────────

def _action(text: str) -> str:
    return HEADER + "actions\n(\n" + text + "\n);\n"


def _entry(**kw) -> str:
    lines = "    {\n"
    for k, v in kw.items():
        lines += f"        {k}  {v};\n"
    return lines + "    }\n"


# ── basic extraction — typed values (no macros) ───────────────────────────────

def test_empty_no_action_list():
    root = _parse(HEADER)
    data = extract_topo_set_data(root)
    assert data.shapes == []


def test_entry_without_geometry_skipped():
    src = _action(_entry(name="s", type="cellSet", action="invert"))
    root = _parse(src)
    data = extract_topo_set_data(root)
    assert data.shapes == []


def test_box_plain():
    src = _action(_entry(
        name="heater", type="cellSet", action="new",
        source="boxToCell",
        box="(-0.01 0 -1) (0.01 0.01 1)",
    ))
    root = _parse(src)
    shapes = extract_topo_set_data(root).shapes
    assert len(shapes) == 1
    s = shapes[0]
    assert s.label == "heater"
    assert s.source == "boxToCell"
    assert s.action == "new"
    assert pytest.approx(s.geometry["box"][0]) == [-0.01, 0.0, -1.0]
    assert pytest.approx(s.geometry["box"][1]) == [0.01, 0.01, 1.0]


def test_sphere_plain():
    src = _action(_entry(
        name="ball", type="cellSet", action="add",
        source="sphereToCell",
        centre="(1 2 3)",
        radius="0.5",
    ))
    root = _parse(src)
    shapes = extract_topo_set_data(root).shapes
    assert len(shapes) == 1
    s = shapes[0]
    assert s.source == "sphereToCell"
    assert s.action == "add"
    assert pytest.approx(s.geometry["centre"]) == [1.0, 2.0, 3.0]
    assert pytest.approx(s.geometry["radius"]) == 0.5


def test_cylinder_plain():
    src = _action(_entry(
        name="tube", type="cellSet", action="subtract",
        source="cylinderToCell",
        p1="(0 0 -1)",
        p2="(0 0  1)",
        radius="0.1",
    ))
    root = _parse(src)
    shapes = extract_topo_set_data(root).shapes
    assert len(shapes) == 1
    s = shapes[0]
    assert s.source == "cylinderToCell"
    assert pytest.approx(s.geometry["p1"]) == [0.0, 0.0, -1.0]
    assert pytest.approx(s.geometry["p2"]) == [0.0, 0.0, 1.0]
    assert pytest.approx(s.geometry["radius"]) == 0.1


def test_multiple_entries():
    src = _action(
        _entry(name="a", type="cellSet", action="new", source="boxToCell", box="(0 0 0) (1 1 1)")
        + _entry(name="b", type="cellSet", action="add", source="sphereToCell",
                 centre="(0 0 0)", radius="1")
        + _entry(name="c", type="cellSet", action="invert")  # no geometry
    )
    root = _parse(src)
    shapes = extract_topo_set_data(root).shapes
    assert len(shapes) == 2
    assert shapes[0].label == "a"
    assert shapes[1].label == "b"


# ── $var resolution ───────────────────────────────────────────────────────────

VARS_HEADER = HEADER + "xMin -0.01;\nxMax  0.01;\nyMax  0.009;\nr     0.05;\n"


def test_box_with_scalar_vars():
    src = VARS_HEADER + "actions\n(\n" + _entry(
        name="h", type="cellSet", action="new", source="boxToCell",
        box="($xMin 0 -100) ($xMax $yMax 100)",
    ) + ");\n"
    root = _parse(src)
    shapes = extract_topo_set_data(root).shapes
    assert len(shapes) == 1
    p1, p2 = shapes[0].geometry["box"]
    assert pytest.approx(p1) == [-0.01, 0.0, -100.0]
    assert pytest.approx(p2) == [0.01, 0.009, 100.0]


def test_radius_macro():
    src = VARS_HEADER + "actions\n(\n" + _entry(
        name="ball", type="cellSet", action="add", source="sphereToCell",
        centre="(0 0 0)", radius="$r",
    ) + ");\n"
    root = _parse(src)
    shapes = extract_topo_set_data(root).shapes
    assert len(shapes) == 1
    assert pytest.approx(shapes[0].geometry["radius"]) == 0.05


def test_cylinder_vector_vars():
    src = VARS_HEADER + "actions\n(\n" + _entry(
        name="tube", type="cellSet", action="new", source="cylinderToCell",
        p1="($xMin 0 -1)", p2="($xMax 0 1)", radius="$r",
    ) + ");\n"
    root = _parse(src)
    shapes = extract_topo_set_data(root).shapes
    assert len(shapes) == 1
    assert pytest.approx(shapes[0].geometry["p1"]) == [-0.01, 0.0, -1.0]
    assert pytest.approx(shapes[0].geometry["p2"]) == [0.01, 0.0, 1.0]
    assert pytest.approx(shapes[0].geometry["radius"]) == 0.05


# ── #eval resolution ──────────────────────────────────────────────────────────

def test_box_with_eval_in_vector():
    src = VARS_HEADER + "actions\n(\n" + _entry(
        name="h", type="cellSet", action="new", source="boxToCell",
        box="(#eval{-$xMax} 0 -100) ($xMax $yMax 100)",
    ) + ");\n"
    root = _parse(src)
    shapes = extract_topo_set_data(root).shapes
    assert len(shapes) == 1
    p1, p2 = shapes[0].geometry["box"]
    assert pytest.approx(p1[0]) == -0.01
    assert pytest.approx(p2[0]) == 0.01


def test_chained_eval_var():
    src = (
        HEADER
        + "r  0.1;\nrHalf  #eval{ $r / 2 };\n"
        + "actions\n(\n"
        + _entry(name="ball", type="cellSet", action="new", source="sphereToCell",
                 centre="(0 0 0)", radius="$rHalf")
        + ");\n"
    )
    root = _parse(src)
    shapes = extract_topo_set_data(root).shapes
    assert len(shapes) == 1
    assert pytest.approx(shapes[0].geometry["radius"]) == 0.05


# ── unresolvable vars → shape skipped ────────────────────────────────────────

def test_unresolvable_var_skips_shape():
    src = _action(_entry(
        name="h", type="cellSet", action="new", source="sphereToCell",
        centre="(0 0 0)", radius="$undeclared",
    ))
    root = _parse(src)
    shapes = extract_topo_set_data(root).shapes
    assert shapes == []


# ── face/point variants treated same as cell ──────────────────────────────────

@pytest.mark.parametrize("source", ["boxToFace", "boxToPoint"])
def test_box_face_point_variants(source):
    src = _action(_entry(
        name="s", type="faceSet", action="new",
        source=source, box="(0 0 0) (1 1 1)",
    ))
    root = _parse(src)
    shapes = extract_topo_set_data(root).shapes
    assert len(shapes) == 1
    assert shapes[0].source == source


@pytest.mark.parametrize("source", ["sphereToFace", "sphereToPoint"])
def test_sphere_face_point_variants(source):
    src = _action(_entry(
        name="s", type="faceSet", action="new",
        source=source, centre="(0 0 0)", radius="0.1",
    ))
    root = _parse(src)
    shapes = extract_topo_set_data(root).shapes
    assert len(shapes) == 1
    assert shapes[0].source == source


@pytest.mark.parametrize("source", ["cylinderToFace", "cylinderToPoint", "cylinderAnnulusToCell"])
def test_cylinder_variants(source):
    src = _action(_entry(
        name="s", type="faceSet", action="new",
        source=source, p1="(0 0 -1)", p2="(0 0 1)", radius="0.1",
    ))
    root = _parse(src)
    shapes = extract_topo_set_data(root).shapes
    assert len(shapes) == 1
    assert shapes[0].source == source


# ── cone family ───────────────────────────────────────────────────────────────

def test_cone_plain():
    src = _action(_entry(
        name="nozzle", type="cellSet", action="new",
        source="coneToCell",
        point1="(0 0 0)", point2="(0 0 1)",
        radius1="0.1", radius2="0.3",
    ))
    root = _parse(src)
    shapes = extract_topo_set_data(root).shapes
    assert len(shapes) == 1
    s = shapes[0]
    assert s.source == "coneToCell"
    assert pytest.approx(s.geometry["p1"]) == [0.0, 0.0, 0.0]
    assert pytest.approx(s.geometry["p2"]) == [0.0, 0.0, 1.0]
    assert pytest.approx(s.geometry["radius1"]) == 0.1
    assert pytest.approx(s.geometry["radius2"]) == 0.3


def test_true_cone_zero_radius():
    src = _action(_entry(
        name="tip", type="cellSet", action="add",
        source="coneToCell",
        point1="(0 0 0)", point2="(0 0 2)",
        radius1="0.5", radius2="0",
    ))
    root = _parse(src)
    shapes = extract_topo_set_data(root).shapes
    assert len(shapes) == 1
    assert pytest.approx(shapes[0].geometry["radius2"]) == 0.0


@pytest.mark.parametrize("source", ["coneToFace", "coneToPoint", "coneAnnulusToCell"])
def test_cone_variants(source):
    src = _action(_entry(
        name="s", type="faceSet", action="new",
        source=source, point1="(0 0 0)", point2="(0 0 1)",
        radius1="0.1", radius2="0.2",
    ))
    root = _parse(src)
    shapes = extract_topo_set_data(root).shapes
    assert len(shapes) == 1
    assert shapes[0].source == source


def test_cone_missing_radius_skipped():
    src = _action(_entry(
        name="s", type="cellSet", action="new",
        source="coneToCell", point1="(0 0 0)", point2="(0 0 1)", radius1="0.1",
    ))
    root = _parse(src)
    assert extract_topo_set_data(root).shapes == []


def test_cone_with_macros():
    src = VARS_HEADER + "actions\n(\n" + _entry(
        name="nozzle", type="cellSet", action="new", source="coneToCell",
        point1="($xMin 0 0)", point2="($xMax 0 #eval{ $r * 2 })",
        radius1="$r", radius2="#eval{ $r / 2 }",
    ) + ");\n"
    root = _parse(src)
    shapes = extract_topo_set_data(root).shapes
    assert len(shapes) == 1
    s = shapes[0]
    assert pytest.approx(s.geometry["p1"]) == [-0.01, 0.0, 0.0]
    assert pytest.approx(s.geometry["p2"]) == [0.01, 0.0, 0.1]
    assert pytest.approx(s.geometry["radius1"]) == 0.05
    assert pytest.approx(s.geometry["radius2"]) == 0.025


# ── point1/point2 key aliases (modern OpenFOAM) accepted for cylinder ──────────

def test_cylinder_point1_alias():
    src = _action(_entry(
        name="tube", type="cellSet", action="new",
        source="cylinderToCell",
        point1="(0 0 -1)", point2="(0 0 1)", radius="0.1",
    ))
    root = _parse(src)
    shapes = extract_topo_set_data(root).shapes
    assert len(shapes) == 1
    assert pytest.approx(shapes[0].geometry["p1"]) == [0.0, 0.0, -1.0]
    assert pytest.approx(shapes[0].geometry["p2"]) == [0.0, 0.0, 1.0]


# ── annulus inner radii ────────────────────────────────────────────────────────

def test_cylinder_annulus_inner_radius():
    src = _action(_entry(
        name="ring", type="cellSet", action="new",
        source="cylinderAnnulusToCell",
        point1="(0 0 0)", point2="(0 0 1)", radius="0.5", innerRadius="0.25",
    ))
    root = _parse(src)
    shapes = extract_topo_set_data(root).shapes
    assert len(shapes) == 1
    assert pytest.approx(shapes[0].geometry["radius"]) == 0.5
    assert pytest.approx(shapes[0].geometry["innerRadius"]) == 0.25


def test_cone_annulus_inner_radii():
    src = _action(_entry(
        name="coneRing", type="cellSet", action="new",
        source="coneAnnulusToCell",
        point1="(0 0 0)", point2="(0 0 1)",
        radius1="0.5", radius2="0.2", innerRadius1="0.25", innerRadius2="0.1",
    ))
    root = _parse(src)
    shapes = extract_topo_set_data(root).shapes
    assert len(shapes) == 1
    g = shapes[0].geometry
    assert pytest.approx(g["innerRadius1"]) == 0.25
    assert pytest.approx(g["innerRadius2"]) == 0.1


def test_cylinder_without_inner_radius_has_no_key():
    src = _action(_entry(
        name="tube", type="cellSet", action="new",
        source="cylinderToCell",
        point1="(0 0 0)", point2="(0 0 1)", radius="0.5",
    ))
    root = _parse(src)
    shapes = extract_topo_set_data(root).shapes
    assert "innerRadius" not in shapes[0].geometry


# ── rotatedBox ─────────────────────────────────────────────────────────────────

def test_rotated_box():
    src = _action(_entry(
        name="tilted", type="cellSet", action="add",
        source="rotatedBoxToCell",
        origin="(0 0 0)", i="(1 0 0)", j="(0 2 0)", k="(0 0 3)",
    ))
    root = _parse(src)
    shapes = extract_topo_set_data(root).shapes
    assert len(shapes) == 1
    g = shapes[0].geometry
    assert pytest.approx(g["origin"]) == [0.0, 0.0, 0.0]
    assert pytest.approx(g["i"]) == [1.0, 0.0, 0.0]
    assert pytest.approx(g["j"]) == [0.0, 2.0, 0.0]
    assert pytest.approx(g["k"]) == [0.0, 0.0, 3.0]


def test_rotated_box_missing_vector_skipped():
    src = _action(_entry(
        name="tilted", type="cellSet", action="add",
        source="rotatedBoxToCell",
        origin="(0 0 0)", i="(1 0 0)", j="(0 2 0)",  # no k
    ))
    root = _parse(src)
    data = extract_topo_set_data(root)
    assert data.shapes == []


# ── non-geometric sources ──────────────────────────────────────────────────────

def test_non_geometric_source_listed_not_drawn():
    src = _action(
        _entry(name="a", type="cellSet", action="new", source="boxToCell", box="(0 0 0) (1 1 1)")
        + _entry(name="faces", type="faceSet", action="new", source="cellToFace", set="a")
    )
    root = _parse(src)
    data = extract_topo_set_data(root)
    assert len(data.shapes) == 1
    assert len(data.non_geometric) == 1
    ng = data.non_geometric[0]
    assert ng.label == "faces"
    assert ng.source == "cellToFace"
    assert ng.geometry == {}


def test_unresolvable_geometric_source_not_listed_as_non_geometric():
    # A geometric source that fails to resolve must not appear as non-geometric.
    src = _action(_entry(
        name="ball", type="cellSet", action="new",
        source="sphereToCell", centre="($missing $missing $missing)", radius="1",
    ))
    root = _parse(src)
    data = extract_topo_set_data(root)
    assert data.shapes == []
    assert data.non_geometric == []


# ── box syntax variants ────────────────────────────────────────────────────────

def test_box_min_max():
    src = _action(_entry(
        name="slab", type="cellSet", action="new", source="boxToCell",
        min="(0 0 0)", max="(1 2 3)",
    ))
    shapes = extract_topo_set_data(_parse(src)).shapes
    assert len(shapes) == 1
    assert shapes[0].geometry["box"] == [[0.0, 0.0, 0.0], [1.0, 2.0, 3.0]]


def test_box_min_without_max_skipped():
    src = _action(_entry(
        name="slab", type="cellSet", action="new", source="boxToCell",
        min="(0 0 0)",
    ))
    data = extract_topo_set_data(_parse(src))
    assert data.shapes == []
    assert data.non_geometric == []


def test_boxes_list():
    src = _action(_entry(
        name="twin", type="cellSet", action="new", source="boxToCell",
        boxes="( (0 0 0) (1 1 1)  (2 0 0) (3 1 1) )",
    ))
    shapes = extract_topo_set_data(_parse(src)).shapes
    assert len(shapes) == 1
    assert shapes[0].geometry["boxes"] == [
        [[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]],
        [[2.0, 0.0, 0.0], [3.0, 1.0, 1.0]],
    ]


def test_boxes_list_odd_vector_count_skipped():
    src = _action(_entry(
        name="twin", type="cellSet", action="new", source="boxToCell",
        boxes="( (0 0 0) (1 1 1)  (2 0 0) )",
    ))
    data = extract_topo_set_data(_parse(src))
    assert data.shapes == []
    assert data.non_geometric == []


def test_boxes_list_with_vars():
    src = VARS_HEADER + "actions\n(\n" + _entry(
        name="twin", type="cellSet", action="new", source="boxToCell",
        boxes="( ($xMin 0 0) ($xMax $yMax 1) )",
    ) + ");\n"
    shapes = extract_topo_set_data(_parse(src)).shapes
    assert len(shapes) == 1
    assert shapes[0].geometry["boxes"] == [[[-0.01, 0.0, 0.0], [0.01, 0.009, 1.0]]]


# ── sphere syntax variants ─────────────────────────────────────────────────────

def test_sphere_origin_alias_stored_as_centre():
    src = _action(_entry(
        name="ball", type="cellSet", action="new", source="sphereToCell",
        origin="(1 2 3)", radius="0.5",
    ))
    shapes = extract_topo_set_data(_parse(src)).shapes
    assert len(shapes) == 1
    g = shapes[0].geometry
    assert pytest.approx(g["centre"]) == [1.0, 2.0, 3.0]
    assert "origin" not in g          # must not clash with rotatedBox dispatch


def test_sphere_inner_radius():
    src = _action(_entry(
        name="shell", type="cellSet", action="new", source="sphereToCell",
        origin="(0 0 0)", radius="0.5", innerRadius="0.2",
    ))
    shapes = extract_topo_set_data(_parse(src)).shapes
    assert shapes[0].geometry["innerRadius"] == pytest.approx(0.2)


def test_sphere_without_inner_radius_has_no_key():
    src = _action(_entry(
        name="ball", type="cellSet", action="new", source="sphereToCell",
        centre="(0 0 0)", radius="0.5",
    ))
    shapes = extract_topo_set_data(_parse(src)).shapes
    assert "innerRadius" not in shapes[0].geometry


# ── point-carrying sources ─────────────────────────────────────────────────────

@pytest.mark.parametrize("source", ["nearestToCell", "nearestToPoint"])
def test_nearest_points(source):
    src = _action(_entry(
        name="near", type="cellSet", action="new", source=source,
        points="( (0 0 0) (1 1 1) )",
    ))
    shapes = extract_topo_set_data(_parse(src)).shapes
    assert len(shapes) == 1
    assert shapes[0].geometry["points"] == [[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]


def test_region_to_cell_inside_points():
    src = _action(_entry(
        name="region", type="cellSet", action="new", source="regionToCell",
        insidePoints="( (0.5 0.5 0.5) )", set="other",
    ))
    shapes = extract_topo_set_data(_parse(src)).shapes
    assert len(shapes) == 1
    assert shapes[0].geometry["points"] == [[0.5, 0.5, 0.5]]


def test_region_to_cell_single_inside_point():
    src = _action(_entry(
        name="region", type="cellSet", action="new", source="regionToCell",
        insidePoint="(0.5 0.5 0.5)",
    ))
    shapes = extract_topo_set_data(_parse(src)).shapes
    assert len(shapes) == 1
    assert shapes[0].geometry["points"] == [[0.5, 0.5, 0.5]]


def test_region_to_face_near_point():
    src = _action(_entry(
        name="regionFace", type="faceSet", action="new", source="regionToFace",
        set="someFaces", nearPoint="(1 0 0)",
    ))
    shapes = extract_topo_set_data(_parse(src)).shapes
    assert len(shapes) == 1
    assert shapes[0].geometry["points"] == [[1.0, 0.0, 0.0]]


def test_point_source_without_points_dropped():
    src = _action(_entry(
        name="near", type="cellSet", action="new", source="nearestToCell",
    ))
    data = extract_topo_set_data(_parse(src))
    assert data.shapes == []
    assert data.non_geometric == []


# ── planeToFaceZone ────────────────────────────────────────────────────────────

def test_plane_to_face_zone():
    src = _action(_entry(
        name="mid", type="faceZoneSet", action="new", source="planeToFaceZone",
        point="(0.05 0 0)", normal="(1 0 0)", option="closest",
    ))
    shapes = extract_topo_set_data(_parse(src)).shapes
    assert len(shapes) == 1
    g = shapes[0].geometry
    assert pytest.approx(g["planePoint"]) == [0.05, 0.0, 0.0]
    assert pytest.approx(g["planeNormal"]) == [1.0, 0.0, 0.0]


def test_plane_missing_normal_dropped():
    src = _action(_entry(
        name="mid", type="faceZoneSet", action="new", source="planeToFaceZone",
        point="(0.05 0 0)",
    ))
    data = extract_topo_set_data(_parse(src))
    assert data.shapes == []
    assert data.non_geometric == []
