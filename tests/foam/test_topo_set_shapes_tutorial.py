# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Guard test: the shipped tutorials/topoSetShapes/system/topoSetDict extracts fully.

Ensures the demo case that showcases every renderable topoSetDict geometry source
(box, sphere, cylinder, cylinderAnnulus, cone frustum, true cone, coneAnnulus) plus
$variable / #eval resolution cannot silently break.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from foam.parser import OpenFoamParser
from foam.topo_set_extractor import extract_topo_set_data

_TOPO_SET_DICT = (
    Path(__file__).resolve().parents[2]
    / "tutorials" / "topoSetShapes" / "system" / "topoSetDict"
)


@pytest.fixture(scope="module")
def shapes():
    root = OpenFoamParser(_TOPO_SET_DICT.read_text()).parse()
    return extract_topo_set_data(root).shapes


def _by_label(shapes, label):
    matches = [s for s in shapes if s.label == label]
    assert len(matches) == 1, f"expected exactly one {label!r}, got {len(matches)}"
    return matches[0]


def test_all_shapes_extracted(shapes):
    assert len(shapes) == 14


def test_every_geometry_source_covered(shapes):
    sources = sorted(s.kind for s in shapes)
    assert sources == [
        "boxToCell",
        "boxToCell",
        "boxToCell",        # min/max form
        "boxToCell",        # boxes-list form
        "coneAnnulusToCell",
        "coneToCell",
        "coneToCell",
        "cylinderAnnulusToCell",
        "cylinderToCell",
        "nearestToCell",
        "planeToFaceZone",
        "rotatedBoxToCell",
        "sphereToCell",
        "sphereToCell",     # origin + innerRadius form
    ]


def test_annuli_carry_inner_radii(shapes):
    ring = _by_label(shapes, "ring")
    assert ring.geometry["innerRadius"] == pytest.approx(0.25)
    cone_ring = _by_label(shapes, "coneRing")
    assert cone_ring.geometry["innerRadius1"] == pytest.approx(0.25)
    assert cone_ring.geometry["innerRadius2"] == pytest.approx(0.1)


def test_rotated_box_extracted(shapes):
    tilted = _by_label(shapes, "tilted")
    assert tilted.kind == "rotatedBoxToCell"
    assert pytest.approx(tilted.geometry["origin"]) == [0.5, 1.6, 0.3]
    assert pytest.approx(tilted.geometry["i"]) == [0.7, 0.4, 0.0]


def test_non_geometric_source_listed():
    root = OpenFoamParser(_TOPO_SET_DICT.read_text()).parse()
    non_geo = extract_topo_set_data(root).non_geometric
    assert [s.kind for s in non_geo] == ["cellToFace"]


def test_sphere_uses_variable_resolution(shapes):
    ball = _by_label(shapes, "ball")
    assert ball.kind == "sphereToCell"
    assert ball.action == "add"
    assert pytest.approx(ball.geometry["centre"]) == [2.2, 0.8, 0.8]
    assert ball.geometry["radius"] == pytest.approx(0.5)


def test_true_cone_uses_eval_and_zero_radius(shapes):
    spike = _by_label(shapes, "spike")
    assert spike.kind == "coneToCell"
    assert spike.action == "subtract"
    assert spike.geometry["radius2"] == pytest.approx(0.0)
    # point2 z is #eval{ 0.2 + 1.4 } == 1.6
    assert spike.geometry["p2"][2] == pytest.approx(1.6)


def test_frustum_is_truncated(shapes):
    frustum = _by_label(shapes, "frustum")
    assert frustum.kind == "coneToCell"
    assert frustum.action == "invert"
    assert frustum.geometry["radius2"] == pytest.approx(0.15)


def test_box_min_max_form(shapes):
    slab = _by_label(shapes, "slab")
    assert slab.geometry["box"] == [[1.4, 1.4, 0.2], [2.0, 2.0, 0.8]]


def test_boxes_list_form(shapes):
    twin = _by_label(shapes, "twinBoxes")
    assert twin.geometry["boxes"] == [
        [[0.2, 2.3, 2.2], [0.7, 2.8, 2.7]],
        [[0.9, 2.3, 2.2], [1.2, 2.8, 2.7]],
    ]


def test_hollow_sphere_via_origin(shapes):
    shell = _by_label(shapes, "shell")
    assert pytest.approx(shell.geometry["centre"]) == [1.6, 2.5, 1.6]
    assert shell.geometry["innerRadius"] == pytest.approx(0.2)


def test_nearest_points_extracted(shapes):
    probes = _by_label(shapes, "probes")
    assert probes.geometry["points"] == [
        [0.3, 0.3, 2.8], [2.8, 0.3, 2.8], [2.8, 2.8, 2.8],
    ]


def test_plane_extracted(shapes):
    plane = _by_label(shapes, "midPlane")
    assert pytest.approx(plane.geometry["planePoint"]) == [1.5, 1.5, 1.5]
    assert pytest.approx(plane.geometry["planeNormal"]) == [0.0, 0.0, 1.0]


def test_shapes_lie_within_domain(shapes):
    """Every parsed point/centre falls inside the 3x3x3 blockMesh domain."""
    def _points(geom):
        for key in ("box", "points"):
            if key in geom:
                yield from geom[key]
        for pair in geom.get("boxes", []):
            yield from pair
        for key in ("centre", "p1", "p2", "planePoint"):
            if key in geom:
                yield geom[key]
        if "origin" in geom:
            o = geom["origin"]
            # All 8 corners of the oriented box: origin + any subset of i/j/k.
            for a in (0.0, 1.0):
                for b in (0.0, 1.0):
                    for c in (0.0, 1.0):
                        yield [
                            o[n] + a * geom["i"][n] + b * geom["j"][n] + c * geom["k"][n]
                            for n in range(3)
                        ]

    for s in shapes:
        for pt in _points(s.geometry):
            assert all(-1e-9 <= c <= 3.0 + 1e-9 for c in pt), (s.label, pt)
