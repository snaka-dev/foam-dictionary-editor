# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for topoSet cone/frustum mesh construction in block_mesh_renderer.

Regression guard: a cone must actually taper along its axis. The previous
implementation used ``pv.CylinderStructured`` with an array of radii, which
produces concentric shells of constant height (i.e. a cylinder), so cones and
frustums rendered as cylinders.
"""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("pyvista")

from ui.panels.block_mesh_renderer import (
    _ACTION_COLORS,
    BlockMeshRenderer,
    _make_annular_frustum_mesh,
    _make_frustum_mesh,
    _make_rotated_box_mesh,
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


def test_make_topo_mesh_cone_is_tapered():
    """The cone branch of _make_topo_mesh must produce a real taper, not a cylinder."""
    geo = {"p1": [0.0, 0.0, 0.0], "p2": [0.0, 0.0, 2.0], "radius1": 1.0, "radius2": 0.0}
    mesh = BlockMeshRenderer._make_topo_mesh("coneToCell", geo)
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


def test_make_topo_mesh_cylinder_annulus_is_hollow():
    geo = {
        "p1": [0.0, 0.0, 0.0], "p2": [0.0, 0.0, 1.0],
        "radius": 0.5, "innerRadius": 0.25,
    }
    mesh = BlockMeshRenderer._make_topo_mesh("cylinderAnnulusToCell", geo)
    assert mesh is not None
    d = np.array([0.0, 0.0, 1.0])
    rel = mesh.points - np.asarray(geo["p1"])
    radial = np.linalg.norm(rel - np.outer(rel @ d, d), axis=1)
    assert radial.min() == pytest.approx(0.25, abs=1e-6)


def test_make_topo_mesh_cone_annulus_is_hollow():
    geo = {
        "p1": [0.0, 0.0, 0.0], "p2": [0.0, 0.0, 1.0],
        "radius1": 0.5, "radius2": 0.2,
        "innerRadius1": 0.25, "innerRadius2": 0.1,
    }
    mesh = BlockMeshRenderer._make_topo_mesh("coneAnnulusToCell", geo)
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


def test_make_topo_mesh_rotated_box():
    geo = {
        "origin": [0.0, 0.0, 0.0], "i": [1.0, 0.0, 0.0],
        "j": [0.0, 1.0, 0.0], "k": [0.0, 0.0, 1.0],
    }
    mesh = BlockMeshRenderer._make_topo_mesh("rotatedBoxToCell", geo)
    assert mesh is not None
    assert mesh.n_points == 8


def test_element_removal_actions_are_coloured():
    """`subtract` is the canonical element-removal action; `delete` is its alias.

    OpenFOAM's `remove` deletes the whole set (no source geometry), so it must
    not be the key used to colour removed regions.
    """
    assert "subtract" in _ACTION_COLORS
    assert _ACTION_COLORS["delete"] == _ACTION_COLORS["subtract"]
    assert "subset" in _ACTION_COLORS
    assert "remove" not in _ACTION_COLORS
