# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Guard test: the shipped tutorials/samplingShapes case extracts fully.

The sampling counterpart of test_topo_set_shapes_tutorial.py. The demo case
covers every renderable sampling kind (probe points, a span-based line, a
point cloud, and both plane spellings) across all three places FoDE reads
sampling from, plus a non-geometric source and a non-sampling function object.
None of that should be able to break silently.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from foam.parser import OpenFoamParser
from foam.sampling_extractor import extract_sampling_data

_CASE = Path(__file__).resolve().parents[2] / "tutorials" / "samplingShapes"
_DOMAIN = 3.0


def _data(name):
    root = OpenFoamParser((_CASE / "system" / name).read_text()).parse()
    return extract_sampling_data(root)


@pytest.fixture(scope="module")
def control_dict():
    return _data("controlDict")


@pytest.fixture(scope="module")
def sample():
    return _data("sample")


@pytest.fixture(scope="module")
def surfaces():
    return _data("surfaces")


def _by_label(shapes, label):
    matches = [s for s in shapes if s.label == label]
    assert len(matches) == 1, f"expected exactly one {label!r}, got {len(matches)}"
    return matches[0]


def test_probes_come_from_the_control_dict_functions_block(control_dict):
    probes = _by_label(control_dict.shapes, "nearWallProbes")
    assert probes.kind == "probes"
    assert len(probes.geometry["points"]) == 3


def test_a_non_sampling_function_object_is_ignored_entirely(control_dict):
    # fieldMinMax is not a sampling function object, so it is neither drawn nor
    # listed as a source without geometry — unlike outerWall below.
    assert len(control_dict.shapes) == 1
    assert control_dict.non_geometric == []


def test_the_dictionary_form_member_list_is_read(sample):
    assert sorted(s.label for s in sample.shapes) == ["riser", "scatter", "topSpan"]


def test_span_sets_carry_start_and_end(sample):
    for label in ("topSpan", "riser"):
        geom = _by_label(sample.shapes, label).geometry
        assert "start" in geom and "end" in geom


def test_a_cloud_carries_points_rather_than_a_span(sample):
    scatter = _by_label(sample.shapes, "scatter")
    assert scatter.kind == "cloud"
    assert "start" not in scatter.geometry
    assert len(scatter.geometry["points"]) == 3


def test_the_parenthesised_form_member_list_is_read(surfaces):
    assert sorted(s.label for s in surfaces.shapes) == ["lowCut", "midCut"]


def test_both_plane_spellings_resolve(surfaces):
    # Direct point/normal, and the nested pointAndNormalDict form.
    mid = _by_label(surfaces.shapes, "midCut")
    assert mid.kind == "cuttingPlane"
    assert pytest.approx(mid.geometry["planeNormal"]) == [0.0, 1.0, 0.0]
    low = _by_label(surfaces.shapes, "lowCut")
    assert low.kind == "plane"
    assert pytest.approx(low.geometry["planePoint"]) == [1.5, 1.5, 0.5]
    assert pytest.approx(low.geometry["planeNormal"]) == [0.0, 0.0, 1.0]


def test_a_patch_surface_is_listed_as_non_geometric(surfaces):
    assert [s.label for s in surfaces.non_geometric] == ["outerWall"]


def test_every_drawable_kind_is_covered(control_dict, sample, surfaces):
    kinds = {s.kind for s in (*control_dict.shapes, *sample.shapes, *surfaces.shapes)}
    assert kinds == {"probes", "lineUniform", "face", "cloud", "cuttingPlane", "plane"}


def test_shapes_lie_within_the_domain(control_dict, sample, surfaces):
    """Every named point falls inside the 3x3x3 blockMesh domain.

    A plane's drawn disc is deliberately larger — that is what its "(clipped)"
    badge reports — but the point defining it still has to be inside.
    """
    for data in (control_dict, sample, surfaces):
        for shape in data.shapes:
            points = list(shape.geometry.get("points", []))
            for key in ("start", "end", "planePoint"):
                if key in shape.geometry:
                    points.append(shape.geometry[key])
            for pt in points:
                assert all(-1e-9 <= c <= _DOMAIN + 1e-9 for c in pt), (shape.label, pt)


def test_badge_positions_stay_apart_in_the_gallery_view():
    """The shot is only legible while the shapes' centres project apart.

    Moving one shape in the case can hide another's badge behind it — that is
    how this case was first built, with two of the six invisible. The camera is
    the one pinned in tools/screenshot_specs.json.
    """
    import numpy as np

    pos = np.array([6.31, -3.49, 4.71])
    focal = np.array([1.5, 1.5, 1.5])
    forward = focal - pos
    forward /= np.linalg.norm(forward)
    right = np.cross(forward, [0.0, 0.0, 1.0])
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)

    def screen(point):
        v = np.asarray(point, float) - pos
        return np.array([(v @ right) / (v @ forward), (v @ up) / (v @ forward)])

    middle = np.array([_DOMAIN / 2] * 3)

    def centre(shape):
        if "points" in shape.geometry:
            return np.mean(shape.geometry["points"], axis=0)
        if "start" in shape.geometry:
            return np.mean([shape.geometry["start"], shape.geometry["end"]], axis=0)
        # A plane's disc is clipped to the mesh before its badge is placed, so
        # the badge does not sit at the point the dict names: it sits at the
        # centre of what is left, which is the domain centre projected onto the
        # plane. Approximate, but it is what separates the two plane badges.
        normal = np.asarray(shape.geometry["planeNormal"], float)
        normal /= np.linalg.norm(normal)
        offset = (middle - np.asarray(shape.geometry["planePoint"], float)) @ normal
        return middle - offset * normal

    badges = {}
    for name in ("controlDict", "sample", "surfaces"):
        for shape in _data(name).shapes:
            badges[shape.label] = screen(centre(shape))

    assert len(badges) == 6
    for a, pa in badges.items():
        for b, pb in badges.items():
            if a < b:
                assert np.linalg.norm(pa - pb) > 0.05, f"{a} and {b} badges overlap"
