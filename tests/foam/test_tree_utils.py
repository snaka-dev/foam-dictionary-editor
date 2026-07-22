# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Direct tests for foam/tree_utils.py resolvers.

The extractor test files (test_topo_set_extractor.py, …) exercise these
helpers only indirectly through the full extraction paths; the cases here pin
down each resolver's own contract, using the parser to build realistic nodes.
"""
from __future__ import annotations

from foam.nodes import FoamNode
from foam.parser import OpenFoamParser
from foam.tree_utils import (
    expand_evals,
    find_child,
    find_child_any,
    resolve_box_geometry,
    resolve_cone_geometry,
    resolve_cylinder_geometry,
    resolve_point_list,
    resolve_scalar,
    resolve_sphere_geometry,
    resolve_vector,
)


def _entry(body: str) -> FoamNode:
    """Parse 'entry { body }' and return the entry dict node."""
    root = OpenFoamParser("entry\n{\n" + body + "\n}\n").parse()
    node = find_child(root, "entry")
    assert node is not None
    return node


def _child(body: str, key: str) -> FoamNode:
    node = find_child(_entry(body), key)
    assert node is not None
    return node


# ── find_child / find_child_any ───────────────────────────────────────────────

def test_find_child_present_and_absent():
    entry = _entry("radius 0.5;")
    assert find_child(entry, "radius") is not None
    assert find_child(entry, "missing") is None


def test_find_child_any_respects_alias_order():
    entry = _entry("p1 (0 0 0);\npoint1 (1 1 1);")
    node = find_child_any(entry, "point1", "p1")
    assert node is not None and node.name == "point1"
    node = find_child_any(entry, "p1", "point1")
    assert node is not None and node.name == "p1"


def test_find_child_any_none_when_no_alias_matches():
    assert find_child_any(_entry("radius 1;"), "a", "b") is None


# ── expand_evals ──────────────────────────────────────────────────────────────

def test_expand_evals_plain_text_untouched():
    assert expand_evals("1 2 3") == "1 2 3"


def test_expand_evals_expands_expression():
    assert expand_evals("#eval{2*3} 0 0") == "6.0 0 0"


def test_expand_evals_unresolvable_left_verbatim():
    text = "#eval{nonsense(} 0 0"
    assert expand_evals(text) == text


# ── resolve_scalar ────────────────────────────────────────────────────────────

def test_resolve_scalar_scalar_and_int():
    assert resolve_scalar(_child("radius 0.5;", "radius"), {}) == 0.5
    assert resolve_scalar(_child("radius 2;", "radius"), {}) == 2.0


def test_resolve_scalar_macro_via_var_map():
    node = _child("radius $r;", "radius")
    assert resolve_scalar(node, {"r": "0.25"}) == 0.25
    assert resolve_scalar(node, {}) is None


def test_resolve_scalar_braced_macro():
    node = _child("radius ${r};", "radius")
    assert resolve_scalar(node, {"r": "0.25"}) == 0.25


def test_resolve_scalar_word_with_eval():
    node = _child("radius #eval{0.5*4};", "radius")
    assert resolve_scalar(node, {}) == 2.0


def test_resolve_scalar_unresolvable_word_returns_none():
    assert resolve_scalar(_child("radius abc;", "radius"), {}) is None


# ── resolve_vector ────────────────────────────────────────────────────────────

def test_resolve_vector_vector_node():
    assert resolve_vector(_child("min (0 1 2);", "min"), {}) == [0.0, 1.0, 2.0]


def test_resolve_vector_raw_list_with_vars_and_eval():
    node = _child("min ($x 0 #eval{1+1});", "min")
    assert resolve_vector(node, {"x": "-1"}) == [-1.0, 0.0, 2.0]


def test_resolve_vector_wrong_arity_returns_none():
    assert resolve_vector(_child("min ($x 0);", "min"), {"x": "1"}) is None


def test_resolve_vector_non_numeric_returns_none():
    assert resolve_vector(_child("min ($x 0 0);", "min"), {"x": "abc"}) is None


# ── resolve_point_list ────────────────────────────────────────────────────────

def test_resolve_point_list_multiple_points():
    node = _child("points ((0 0 0) (1 2 3));", "points")
    assert resolve_point_list(node, {}) == [[0.0, 0.0, 0.0], [1.0, 2.0, 3.0]]


def test_resolve_point_list_with_var():
    node = _child("points (($x 0 0));", "points")
    assert resolve_point_list(node, {"x": "5"}) == [[5.0, 0.0, 0.0]]


def test_resolve_point_list_non_triple_returns_none():
    node = _child("points ((0 0) (1 1 1));", "points")
    assert resolve_point_list(node, {}) is None


def test_resolve_point_list_rejects_non_raw_list_node():
    assert resolve_point_list(_child("points (0 0 0);", "points"), {}) is None


# ── resolve_sphere_geometry ───────────────────────────────────────────────────

def test_sphere_origin_and_centre_aliases():
    for key in ("origin", "centre"):
        geo = resolve_sphere_geometry(_entry(f"{key} (0 0 0);\nradius 1;"), {})
        assert geo == {"centre": [0.0, 0.0, 0.0], "radius": 1.0}


def test_sphere_vector_radius_needs_flag():
    entry = _entry("origin (0 0 0);\nradius (1 2 3);")
    assert resolve_sphere_geometry(entry, {}) == {}
    geo = resolve_sphere_geometry(entry, {}, allow_vector_radius=True)
    assert geo["radius"] == [1.0, 2.0, 3.0]


def test_sphere_inner_radius_needs_flag():
    entry = _entry("origin (0 0 0);\nradius 2;\ninnerRadius 1;")
    assert "innerRadius" not in resolve_sphere_geometry(entry, {})
    geo = resolve_sphere_geometry(entry, {}, allow_inner_radius=True)
    assert geo["innerRadius"] == 1.0


def test_sphere_missing_radius_returns_empty():
    assert resolve_sphere_geometry(_entry("origin (0 0 0);"), {}) == {}


# ── resolve_cylinder_geometry ─────────────────────────────────────────────────

def test_cylinder_point_aliases_and_inner_radius():
    geo = resolve_cylinder_geometry(
        _entry("p1 (0 0 0);\np2 (0 0 1);\nradius 2;\ninnerRadius 1;"), {}
    )
    assert geo == {
        "p1": [0.0, 0.0, 0.0], "p2": [0.0, 0.0, 1.0],
        "radius": 2.0, "innerRadius": 1.0,
    }
    geo = resolve_cylinder_geometry(
        _entry("point1 (0 0 0);\npoint2 (0 0 1);\nradius 2;"), {}
    )
    assert geo["p1"] == [0.0, 0.0, 0.0] and "innerRadius" not in geo


def test_cylinder_missing_radius_returns_empty():
    assert resolve_cylinder_geometry(_entry("p1 (0 0 0);\np2 (0 0 1);"), {}) == {}


# ── resolve_cone_geometry ─────────────────────────────────────────────────────

def test_cone_full_set():
    geo = resolve_cone_geometry(
        _entry("p1 (0 0 0);\np2 (0 0 1);\nradius1 2;\nradius2 0.5;"), {}
    )
    assert geo["radius1"] == 2.0 and geo["radius2"] == 0.5


def test_cone_inner_radii_need_both_and_flag():
    body = "p1 (0 0 0);\np2 (0 0 1);\nradius1 2;\nradius2 1;\ninnerRadius1 0.5;"
    geo = resolve_cone_geometry(_entry(body), {}, allow_inner_radii=True)
    assert "innerRadius1" not in geo  # innerRadius2 missing
    body += "\ninnerRadius2 0.25;"
    assert "innerRadius1" not in resolve_cone_geometry(_entry(body), {})  # flag off
    geo = resolve_cone_geometry(_entry(body), {}, allow_inner_radii=True)
    assert geo["innerRadius1"] == 0.5 and geo["innerRadius2"] == 0.25


# ── resolve_box_geometry ──────────────────────────────────────────────────────

def test_box_min_max_default_flags():
    geo = resolve_box_geometry(_entry("min (0 0 0);\nmax (1 1 1);"), {})
    assert geo == {"box": [[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]}


def test_box_pair_form_needs_flag():
    entry = _entry("box (0 0 0) (1 1 1);")
    assert resolve_box_geometry(entry, {}) == {}
    geo = resolve_box_geometry(entry, {}, allow_box_pair=True)
    assert geo == {"box": [[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]}


def test_box_pair_var_form():
    entry = _entry("box ($xMin 0 0) (1 1 $zMax);")
    var_map = {"xMin": "0", "zMax": "1"}
    geo = resolve_box_geometry(entry, var_map, allow_box_pair=True)
    assert geo == {"box": [[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]}


def test_boxes_form_needs_flag():
    entry = _entry("boxes ((0 0 0) (1 1 1) (2 2 2) (3 3 3));")
    assert resolve_box_geometry(entry, {}) == {}
    geo = resolve_box_geometry(entry, {}, allow_multi=True)
    assert geo == {
        "boxes": [
            [[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]],
            [[2.0, 2.0, 2.0], [3.0, 3.0, 3.0]],
        ]
    }


def test_boxes_odd_vector_count_returns_empty():
    entry = _entry("boxes ((0 0 0) (1 1 1) (2 2 2));")
    assert resolve_box_geometry(entry, {}, allow_multi=True) == {}


def test_box_precedence_box_over_min_max_over_boxes():
    body = (
        "box (0 0 0) (1 1 1);\n"
        "min (2 2 2);\nmax (3 3 3);\n"
        "boxes ((4 4 4) (5 5 5));"
    )
    geo = resolve_box_geometry(_entry(body), {}, allow_box_pair=True, allow_multi=True)
    assert geo == {"box": [[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]}
    body_no_box = "min (2 2 2);\nmax (3 3 3);\nboxes ((4 4 4) (5 5 5));"
    geo = resolve_box_geometry(
        _entry(body_no_box), {}, allow_box_pair=True, allow_multi=True
    )
    assert geo == {"box": [[2.0, 2.0, 2.0], [3.0, 3.0, 3.0]]}


def test_box_unresolvable_var_returns_empty():
    entry = _entry("min ($x 0 0);\nmax (1 1 1);")
    assert resolve_box_geometry(entry, {}) == {}
