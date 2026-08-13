# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for topoSet cone/frustum mesh construction in shape_mesh.py.

Regression guard: a cone must actually taper along its axis. The previous
implementation used ``pv.CylinderStructured`` with an array of radii, which
produces concentric shells of constant height (i.e. a cylinder), so cones and
frustums rendered as cylinders.

shape_mesh.py is Qt-free geometry construction split out of
block_mesh_renderer.py (see DEVELOPER.md's "Update candidates" era notes);
this file exercises only that module. Colour handling (_ACTION_COLORS and
friends) stays with the renderer and is covered by
tests/ui/test_block_mesh_renderer_colors.py instead.
"""
from __future__ import annotations

import ast
import gzip
import pathlib

import numpy as np
import pytest

pytest.importorskip("pyvista")

import pyvista as pv

from ui.panels.shape_mesh import (
    _CLIP_MARK_SUFFIX,
    _bounds_within,
    _clip_capped,
    _clip_to_bounds,
    _expanded_bounds,
    _make_annular_frustum_mesh,
    _make_frustum_mesh,
    _make_rotated_box_mesh,
    _mark_label,
    make_shape_mesh,
    read_surface_mesh,
)

_SHAPE_MESH_PATH = (
    pathlib.Path(__file__).resolve().parents[2] / "ui" / "panels" / "shape_mesh.py"
)


def _radius_profile(mesh, p1, p2):
    """Return (max radius at p1 end, max radius at p2 end) for an axial mesh."""
    p1 = np.asarray(p1, dtype=float)
    p2 = np.asarray(p2, dtype=float)
    axis = p2 - p1
    height = float(np.linalg.norm(axis))
    d = axis / height
    rel = mesh.points - p1
    t = rel @ d
    radial = np.linalg.norm(rel - np.outer(t, d), axis=1)

    def rmax(frac):
        mask = np.abs(t - frac * height) < 1e-6
        return float(radial[mask].max()) if mask.any() else None

    return rmax(0.0), rmax(1.0)


def test_true_cone_tapers_to_zero():
    p1, p2 = [2.3, 1.6, 0.2], [2.3, 1.6, 1.6]
    mesh = _make_frustum_mesh(p1, p2, 0.55, 0.0)
    r_base, r_tip = _radius_profile(mesh, p1, p2)
    assert r_base == pytest.approx(0.55, abs=1e-6)
    assert r_tip == pytest.approx(0.0, abs=1e-6)


def test_frustum_tapers_between_radii():
    p1, p2 = [1.4, 0.5, 1.6], [1.4, 0.5, 2.9]
    mesh = _make_frustum_mesh(p1, p2, 0.5, 0.15)
    r_base, r_tip = _radius_profile(mesh, p1, p2)
    assert r_base == pytest.approx(0.5, abs=1e-6)
    assert r_tip == pytest.approx(0.15, abs=1e-6)


def test_make_shape_mesh_cone_is_tapered():
    """The cone branch of make_shape_mesh must produce a real taper, not a cylinder."""
    geo = {"p1": [0.0, 0.0, 0.0], "p2": [0.0, 0.0, 2.0], "radius1": 1.0, "radius2": 0.0}
    mesh = make_shape_mesh("coneToCell", geo)
    assert mesh is not None
    r_base, r_tip = _radius_profile(mesh, geo["p1"], geo["p2"])
    assert r_base == pytest.approx(1.0, abs=1e-6)
    assert r_tip == pytest.approx(0.0, abs=1e-6)


def test_frustum_zero_height_returns_none():
    assert _make_frustum_mesh([1.0, 1.0, 1.0], [1.0, 1.0, 1.0], 0.5, 0.2) is None


def test_frustum_axis_off_principal_directions():
    """A diagonal axis still tapers correctly (basis construction is robust)."""
    p1, p2 = [0.0, 0.0, 0.0], [1.0, 1.0, 1.0]
    mesh = _make_frustum_mesh(p1, p2, 0.4, 0.1)
    r_base, r_tip = _radius_profile(mesh, p1, p2)
    assert r_base == pytest.approx(0.4, abs=1e-6)
    assert r_tip == pytest.approx(0.1, abs=1e-6)


def test_annular_cylinder_is_hollow():
    """A hollow cylinder must expose both an outer and a smaller inner radius."""
    p1, p2 = [0.0, 0.0, 0.0], [0.0, 0.0, 1.0]
    mesh = _make_annular_frustum_mesh(p1, p2, 0.5, 0.5, 0.25, 0.25)
    assert mesh is not None
    rel = mesh.points - np.asarray(p1)
    d = np.array([0.0, 0.0, 1.0])
    radial = np.linalg.norm(rel - np.outer(rel @ d, d), axis=1)
    assert radial.max() == pytest.approx(0.5, abs=1e-6)
    assert radial.min() == pytest.approx(0.25, abs=1e-6)


def test_annular_frustum_zero_height_returns_none():
    assert _make_annular_frustum_mesh(
        [1.0, 1.0, 1.0], [1.0, 1.0, 1.0], 0.5, 0.4, 0.2, 0.1
    ) is None


def test_make_shape_mesh_cylinder_annulus_is_hollow():
    geo = {
        "p1": [0.0, 0.0, 0.0], "p2": [0.0, 0.0, 1.0],
        "radius": 0.5, "innerRadius": 0.25,
    }
    mesh = make_shape_mesh("cylinderAnnulusToCell", geo)
    assert mesh is not None
    d = np.array([0.0, 0.0, 1.0])
    rel = mesh.points - np.asarray(geo["p1"])
    radial = np.linalg.norm(rel - np.outer(rel @ d, d), axis=1)
    assert radial.min() == pytest.approx(0.25, abs=1e-6)


def test_make_shape_mesh_cone_annulus_is_hollow():
    geo = {
        "p1": [0.0, 0.0, 0.0], "p2": [0.0, 0.0, 1.0],
        "radius1": 0.5, "radius2": 0.2,
        "innerRadius1": 0.25, "innerRadius2": 0.1,
    }
    mesh = make_shape_mesh("coneAnnulusToCell", geo)
    assert mesh is not None
    r_base, r_tip = _radius_profile(mesh, geo["p1"], geo["p2"])
    # Outer radii bound the mesh; the hole means points also exist at inner radii.
    assert r_base == pytest.approx(0.5, abs=1e-6)
    assert r_tip == pytest.approx(0.2, abs=1e-6)


def test_rotated_box_mesh_is_single_hex():
    mesh = _make_rotated_box_mesh([0, 0, 0], [1, 0, 0], [0, 2, 0], [0, 0, 3])
    assert mesh is not None
    assert mesh.n_points == 8
    assert mesh.n_cells == 1
    # Opposite corner of the parallelepiped is origin + i + j + k.
    assert mesh.bounds == pytest.approx((0.0, 1.0, 0.0, 2.0, 0.0, 3.0))


def test_make_shape_mesh_rotated_box():
    geo = {
        "origin": [0.0, 0.0, 0.0], "i": [1.0, 0.0, 0.0],
        "j": [0.0, 1.0, 0.0], "k": [0.0, 0.0, 1.0],
    }
    mesh = make_shape_mesh("rotatedBoxToCell", geo)
    assert mesh is not None
    assert mesh.n_points == 8


def test_make_shape_mesh_sphere_scalar_radius():
    geo = {"centre": [1.0, 2.0, 3.0], "radius": 0.5}
    mesh = make_shape_mesh("sphere", geo)
    assert mesh is not None
    # pv.Sphere's default tessellation only approximates the true bounds.
    assert mesh.bounds == pytest.approx(
        (0.5, 1.5, 1.5, 2.5, 2.5, 3.5), abs=5e-3
    )


def test_make_shape_mesh_sphere_vector_radius_is_ellipsoid():
    """snappyHexMesh's `sphere` type allows a per-axis radius (e.g. igloo domes)."""
    geo = {"centre": [3.0, 3.0, 0.0], "radius": [3.5, 3.5, 4.0]}
    mesh = make_shape_mesh("sphere", geo)
    assert mesh is not None
    xmin, xmax, ymin, ymax, zmin, zmax = mesh.bounds
    # Coarse default tessellation: check the ellipsoid's approximate extent
    # and centre rather than an exact radius match.
    assert (xmax - xmin) / 2 == pytest.approx(3.5, rel=0.02)
    assert (ymax - ymin) / 2 == pytest.approx(3.5, rel=0.02)
    assert (zmax - zmin) / 2 == pytest.approx(4.0, rel=0.02)
    assert (xmin + xmax) / 2 == pytest.approx(3.0, abs=1e-6)
    assert (zmin + zmax) / 2 == pytest.approx(0.0, abs=1e-6)


def test_make_shape_mesh_stl_path_reads_file(tmp_path):
    stl = tmp_path / "box.stl"
    stl.write_text(
        "solid box\n"
        "facet normal 0 0 1\n outer loop\n"
        "  vertex 0 0 0\n  vertex 1 0 0\n  vertex 0 1 0\n"
        " endloop\nendfacet\n"
        "endsolid box\n"
    )
    mesh = make_shape_mesh("triSurfaceMesh", {"stl_path": str(stl)})
    assert mesh is not None
    assert mesh.n_points == 3


def test_make_shape_mesh_stl_path_missing_file_returns_none():
    assert make_shape_mesh(
        "triSurfaceMesh", {"stl_path": "/nonexistent/does-not-exist.stl"}
    ) is None


_ASCII_STL = (
    "solid box\n"
    "facet normal 0 0 1\n outer loop\n"
    "  vertex 0 0 0\n  vertex 1 0 0\n  vertex 0 1 0\n"
    " endloop\nendfacet\n"
    "endsolid box\n"
)


def test_make_shape_mesh_reads_gzipped_stl(tmp_path):
    gz = tmp_path / "box.stl.gz"
    gz.write_bytes(gzip.compress(_ASCII_STL.encode("ascii")))
    mesh = make_shape_mesh("triSurfaceMesh", {"stl_path": str(gz)})
    assert mesh is not None
    assert mesh.n_points == 3


def test_read_surface_mesh_plain_passthrough(tmp_path):
    stl = tmp_path / "box.stl"
    stl.write_text(_ASCII_STL)
    mesh = read_surface_mesh(str(stl))
    assert mesh.n_points == 3


def test_make_shape_mesh_multi_box_merges_all():
    geo = {"boxes": [
        [[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]],
        [[2.0, 0.0, 0.0], [3.0, 1.0, 1.0]],
    ]}
    mesh = make_shape_mesh("boxToCell", geo)
    assert mesh is not None
    # The merged mesh spans both boxes, including the gap between them.
    assert mesh.bounds[0] == pytest.approx(0.0)
    assert mesh.bounds[1] == pytest.approx(3.0)
    # Two disjoint 8-corner boxes.
    assert mesh.n_points == 16


def test_make_shape_mesh_hollow_sphere_has_two_shells():
    solid = make_shape_mesh(
        "sphereToCell", {"centre": [0.0, 0.0, 0.0], "radius": 1.0}
    )
    hollow = make_shape_mesh(
        "sphereToCell", {"centre": [0.0, 0.0, 0.0], "radius": 1.0, "innerRadius": 0.4}
    )
    assert hollow.n_points > solid.n_points
    radii = np.linalg.norm(hollow.points, axis=1)
    assert radii.max() == pytest.approx(1.0, abs=1e-6)
    assert radii.min() == pytest.approx(0.4, abs=1e-6)


def test_make_shape_mesh_plane_disc_respects_plane_size():
    geo = {"planePoint": [1.0, 2.0, 3.0], "planeNormal": [0.0, 0.0, 1.0]}
    mesh = make_shape_mesh("planeToFaceZone", geo, plane_size=2.5)
    assert mesh is not None
    radial = np.linalg.norm(mesh.points - np.array([1.0, 2.0, 3.0]), axis=1)
    assert radial.max() == pytest.approx(2.5, abs=1e-6)
    # Flat: every point lies in the z = 3 plane.
    assert np.allclose(mesh.points[:, 2], 3.0)


def test_make_shape_mesh_points_returns_none():
    """Loose points carry no surface; they are rendered as markers instead."""
    assert make_shape_mesh(
        "nearestToCell", {"points": [[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]}
    ) is None


# ── overlay clipping (display-only limit to the block-mesh bounds) ────────────

_UNIT_CLIP = _expanded_bounds(np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]))


def test_expanded_bounds_pads_each_axis():
    pts = np.array([[0.0, 0.0, 0.0], [2.0, 1.0, 4.0]])
    assert _expanded_bounds(pts) == pytest.approx(
        [-0.2, 2.2, -0.1, 1.1, -0.4, 4.4]
    )


def test_expanded_bounds_degenerate_axis_gets_volume():
    # A 2-D mesh (flat in z) must still yield a clip box with z extent.
    pts = np.array([[0.0, 0.0, 0.5], [2.0, 1.0, 0.5]])
    b = _expanded_bounds(pts)
    assert b[5] > b[4]
    assert b[4] == pytest.approx(0.5 - 0.2)
    assert b[5] == pytest.approx(0.5 + 0.2)


def test_clip_fitting_shape_unchanged():
    mesh = pv.Sphere(radius=0.3, center=(0.5, 0.5, 0.5))
    clipped, mark = _clip_to_bounds(mesh, _UNIT_CLIP)
    assert mark == ""
    assert clipped is mesh


def test_clip_none_bounds_unchanged():
    mesh = pv.Sphere(radius=100.0)
    clipped, mark = _clip_to_bounds(mesh, None)
    assert mark == ""
    assert clipped is mesh


def test_clip_oversized_shape_is_limited():
    # The damBreak-style case: a region box far taller than the mesh.
    mesh = pv.Box(bounds=[0.2, 0.8, 0.2, 0.8, -10.0, 10.0])
    clipped, mark = _clip_to_bounds(mesh, _UNIT_CLIP)
    assert mark == "clipped"
    assert clipped.n_cells > 0
    b = clipped.bounds
    # VTK stores points as float32, so allow its rounding at the clip planes.
    for i in range(3):
        assert b[2 * i] >= _UNIT_CLIP[2 * i] - 1e-6
        assert b[2 * i + 1] <= _UNIT_CLIP[2 * i + 1] + 1e-6


def _open_edge_count(mesh) -> int:
    """Boundary edges belonging to one face only — i.e. holes in the surface."""
    surface = mesh if isinstance(mesh, pv.PolyData) else mesh.extract_surface()
    return surface.extract_feature_edges(
        boundary_edges=True,
        feature_edges=False,
        manifold_edges=False,
        non_manifold_edges=False,
    ).n_cells


def test_clip_seals_the_cut_faces():
    # Regression: a shape mesh is a hollow surface, so clipping away both of a
    # box's z faces used to leave a tube. damBreak's setFieldsDict box spans
    # z -1..1 against a mesh 0.0146 deep, and the front view — the only angle
    # the case is recognisable from — looked straight through it.
    mesh = pv.Box(bounds=[0.2, 0.8, 0.2, 0.8, -10.0, 10.0])
    clipped, mark = _clip_to_bounds(mesh, _UNIT_CLIP)
    assert mark == "clipped"
    assert _open_edge_count(clipped) == 0


def test_clip_seals_a_cylinder_cut_through_both_ends():
    # A cylinder's seam carries duplicate points that read as non-manifold, so
    # the capped clip only accepts it once they are merged.
    mesh = pv.Cylinder(center=(0.5, 0.5, 0.5), direction=(0, 0, 1), radius=0.3, height=20)
    clipped, mark = _clip_to_bounds(mesh, _UNIT_CLIP)
    assert mark == "clipped"
    assert _open_edge_count(clipped) == 0


def test_clip_keeps_box_side_faces_unsplit():
    # The wireframe pass is drawn over the clipped mesh, so triangulating the
    # box would draw a diagonal across all six faces. The two caps VTK seals
    # the cut with are triangle pairs; the four side faces stay whole quads.
    mesh = pv.Box(bounds=[0.2, 0.8, 0.2, 0.8, -10.0, 10.0])
    clipped, _mark = _clip_to_bounds(mesh, _UNIT_CLIP)
    sizes = sorted(clipped.get_cell(i).n_points for i in range(clipped.n_cells))
    assert sizes == [3, 3, 3, 3, 4, 4, 4, 4]


def test_clip_capped_declines_a_non_manifold_shape():
    # A plane disc has no volume to seal, so the capped path must decline and
    # let _clip_to_bounds fall back rather than raise.
    disc = pv.Plane(center=(0.5, 0.5, 0.5), direction=(0, 0, 1), i_size=10, j_size=10)
    assert _clip_capped(disc, _UNIT_CLIP) is None
    clipped, mark = _clip_to_bounds(disc, _UNIT_CLIP)
    assert mark == "clipped"
    assert clipped.n_cells > 0
    assert _bounds_within(clipped.bounds, _UNIT_CLIP)


def test_clip_shape_fully_outside_kept_and_marked():
    mesh = pv.Sphere(radius=0.5, center=(10.0, 0.0, 0.0))
    clipped, mark = _clip_to_bounds(mesh, _UNIT_CLIP)
    assert mark == "outside"
    assert clipped is mesh


def test_clip_enclosing_shape_gets_stand_in_box():
    # Surface entirely outside but volume encloses the scene: clip_box would
    # yield an empty mesh, so the AABB overlap stands in.
    mesh = pv.Box(bounds=[-50.0, 50.0, -50.0, 50.0, -50.0, 50.0])
    clipped, mark = _clip_to_bounds(mesh, _UNIT_CLIP)
    assert mark == "clipped"
    assert clipped.n_cells > 0
    assert clipped.bounds == pytest.approx(_UNIT_CLIP)


def test_clip_asymmetric_enclosure_gets_stand_in_box():
    # Regression: floatingObject setFieldsDict box 1 — a hollow shell that
    # encloses the scene in x/y but is cut by a z face inside the clip range.
    # vtkBoxClipDataSet returns a non-empty *degenerate* result whose bounds
    # still span the huge unclipped extent, so the plain n_cells==0 fallback
    # never fires and the shape used to render huge while labelled "clipped".
    mesh = pv.Box(bounds=[-100.0, 100.0, -100.0, 100.0, -100.0, 0.5368])
    clipped, mark = _clip_to_bounds(mesh, _UNIT_CLIP)
    assert mark == "clipped"
    assert clipped.n_cells > 0
    assert clipped.bounds == pytest.approx(
        [-0.1, 1.1, -0.1, 1.1, -0.1, 0.5368], abs=1e-4
    )


def test_clip_asymmetric_partial_still_genuinely_clipped():
    # floatingObject setFieldsDict box 2 — partially overlapping, genuinely
    # clippable. Must stay a real clip (not the AABB stand-in) and its bounds
    # must lie honestly within the clip box.
    mesh = pv.Box(bounds=[0.7, 100.0, 0.8, 100.0, -100.0, 0.65])
    clipped, mark = _clip_to_bounds(mesh, _UNIT_CLIP)
    assert mark == "clipped"
    assert clipped.n_cells > 0
    b = clipped.bounds
    for i in range(3):
        assert b[2 * i] >= _UNIT_CLIP[2 * i] - 1e-4
        assert b[2 * i + 1] <= _UNIT_CLIP[2 * i + 1] + 1e-4


def _string_literals(path):
    """Yield (line, value) for every non-docstring string literal in a module."""
    tree = ast.parse(pathlib.Path(path).read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                and isinstance(body[0].value.value, str):
            docstrings.add(id(body[0].value))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                and id(node) not in docstrings:
            yield node.lineno, node.value


def test_every_string_this_module_can_draw_is_ascii():
    """Regression: ✂, ⚠ and → all reached the 3-D scene as nothing at all.

    Text ultimately drawn by VTK (via block_mesh_renderer.py's _mark_label
    calls, fed by this module's _CLIP_MARK_SUFFIX) is not Qt text. VTK's
    built-in label font has no glyph for those characters and draws
    *nothing* for them — not even a .notdef box — so the mark or separator
    was invisible while the surrounding text still reserved its width.
    _CLIP_MARK_SUFFIX shipped that way until 2026-07-30 (✂/⚠); see
    block_mesh_renderer.py's own ASCII test (in
    tests/ui/test_block_mesh_renderer_colors.py) for the → bounds-readout
    half of the same regression. Docstrings are exempt: prose arrows are
    fine in text that is never drawn.
    """
    offenders = [
        (line, value) for line, value in _string_literals(_SHAPE_MESH_PATH)
        if not value.isascii()
    ]
    assert not offenders, "non-ASCII string literals in VTK-drawn module: " + "; ".join(
        f"line {line}: {value!r}" for line, value in offenders
    )


def test_clip_marks_are_printable_ascii():
    for mark, suffix in _CLIP_MARK_SUFFIX.items():
        assert suffix.isascii(), f"{mark}: {suffix!r} is not ASCII"
        assert suffix.isprintable(), f"{mark}: {suffix!r} is not printable"


def test_mark_label_appends_the_suffix():
    assert _mark_label("midPlane", "clipped") == "midPlane  (clipped)"
    assert _mark_label("midPlane", "outside") == "midPlane  (outside block mesh)"


def test_mark_label_unmarked_shape_keeps_its_name_alone():
    assert _mark_label("box0", "") == "box0"


def test_bounds_within_helper():
    outer = [0.0, 1.0, 0.0, 1.0, 0.0, 1.0]
    # Fully inside.
    assert _bounds_within([0.1, 0.9, 0.1, 0.9, 0.1, 0.9], outer)
    # Overshoots one face by far more than the float32-scale epsilon.
    assert not _bounds_within([0.1, 0.9, 0.1, 0.9, 0.1, 2.0], outer)
    # Overshoots within the float32-scale epsilon (unit scale ~1e-4 slack).
    assert _bounds_within([0.1, 0.9, 0.1, 0.9, 0.1, 1.0 + 1e-6], outer)
