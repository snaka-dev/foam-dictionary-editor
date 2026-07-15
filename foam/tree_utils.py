# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Generic FoamNode tree-walking and value-resolution helpers.

Shared by the topoSetDict and snappyHexMeshDict geometry extractors, which both
need to pull typed values (points, scalars) out of nested dictionary blocks
while resolving $variable references and #eval{} expressions. Also hosts the
shared sphere/cylinder/cone geometry resolvers those extractors use to build
the geometry dicts consumed by BlockMeshRenderer._make_shape_mesh.
"""
from __future__ import annotations

import re

from foam.nodes import FoamNode
from foam.var_resolver import eval_foam_expr, substitute_vars

# Matches #eval{...} fragments inside a substituted string.
_INLINE_EVAL_RE = re.compile(r'#eval\s*\{([^}]+)\}')


def find_child(entry: FoamNode, key: str) -> FoamNode | None:
    for child in entry.children:
        if child.name == key:
            return child
    return None


def find_child_any(entry: FoamNode, *keys: str) -> FoamNode | None:
    """Return the first child matching any of the given key aliases."""
    for key in keys:
        node = find_child(entry, key)
        if node is not None:
            return node
    return None


def expand_evals(text: str) -> str:
    """Evaluate any #eval{...} fragments in an already-var-substituted string."""
    def _repl(m: re.Match) -> str:
        result = eval_foam_expr(m.group(1))
        return result if result is not None else m.group(0)
    return _INLINE_EVAL_RE.sub(_repl, text)


def resolve_scalar(node: FoamNode, var_map: dict[str, str]) -> float | None:
    """Return a float from a scalar/int/macro/word node, resolving $vars."""
    if node.node_type in ("scalar", "int"):
        return float(node.value)
    if node.node_type == "macro":
        ref = str(node.value).lstrip("$").strip("{}")
        val = var_map.get(ref)
        if val is not None:
            return float(val)
    if node.node_type in ("word", "compound"):
        text = expand_evals(substitute_vars(str(node.value), var_map))
        result = eval_foam_expr(text)
        if result is not None:
            return float(result)
    return None


def resolve_vector(node: FoamNode, var_map: dict[str, str]) -> list[float] | None:
    """Return [x, y, z] from a vector/raw_list node, resolving $vars."""
    if node.node_type == "vector":
        return node.value
    if node.node_type == "raw_list":
        text = expand_evals(substitute_vars(str(node.value), var_map))
        parts = text.split()
        if len(parts) == 3:
            try:
                return [float(p) for p in parts]
            except ValueError:
                pass
    return None


def resolve_sphere_geometry(
    entry: FoamNode,
    var_map: dict[str, str],
    *,
    allow_vector_radius: bool = False,
    allow_inner_radius: bool = False,
) -> dict:
    """Resolve a sphere entry into {"centre", "radius"[, "innerRadius"]}.

    "origin" is the primary OpenFOAM keyword; "centre" the compat alias.
    Stored as "centre" so the renderer's "origin" key stays rotated-box only.
    ``allow_vector_radius`` accepts snappyHexMesh's per-axis radius (ellipsoid);
    ``allow_inner_radius`` reads topoSet's hollow-sphere innerRadius.
    Returns {} when any required part is missing or unresolvable.
    """
    geometry: dict = {}
    c_node = find_child_any(entry, "origin", "centre")
    r_node = find_child(entry, "radius")
    if c_node is None or r_node is None:
        return geometry
    centre = resolve_vector(c_node, var_map)
    if allow_vector_radius and r_node.node_type == "vector":
        radius: list[float] | float | None = resolve_vector(r_node, var_map)
    else:
        radius = resolve_scalar(r_node, var_map)
    if centre is None or radius is None:
        return geometry
    geometry["centre"] = centre
    geometry["radius"] = radius
    if allow_inner_radius:
        inner_node = find_child(entry, "innerRadius")
        if inner_node is not None:
            inner = resolve_scalar(inner_node, var_map)
            if inner is not None:
                geometry["innerRadius"] = inner
    return geometry


def resolve_cylinder_geometry(entry: FoamNode, var_map: dict[str, str]) -> dict:
    """Resolve a cylinder entry into {"p1", "p2", "radius"[, "innerRadius"]}.

    Accepts the point1/point2 keywords and their p1/p2 aliases; the optional
    innerRadius makes a hollow cylinder (topoSet's cylinderAnnulus, or
    snappyHexMesh's searchableCylinder with an inner shell).
    Returns {} when any required part is missing or unresolvable.
    """
    geometry: dict = {}
    p1_node = find_child_any(entry, "point1", "p1")
    p2_node = find_child_any(entry, "point2", "p2")
    r_node = find_child(entry, "radius")
    if p1_node is None or p2_node is None or r_node is None:
        return geometry
    p1 = resolve_vector(p1_node, var_map)
    p2 = resolve_vector(p2_node, var_map)
    radius = resolve_scalar(r_node, var_map)
    if p1 is None or p2 is None or radius is None:
        return geometry
    geometry["p1"] = p1
    geometry["p2"] = p2
    geometry["radius"] = radius
    inner_node = find_child(entry, "innerRadius")
    if inner_node is not None:
        inner = resolve_scalar(inner_node, var_map)
        if inner is not None:
            geometry["innerRadius"] = inner
    return geometry


def resolve_cone_geometry(
    entry: FoamNode,
    var_map: dict[str, str],
    *,
    allow_inner_radii: bool = False,
) -> dict:
    """Resolve a cone entry into {"p1", "p2", "radius1", "radius2", …}.

    ``allow_inner_radii`` reads topoSet's coneAnnulus innerRadius1/innerRadius2
    pair (added only when both resolve). Returns {} when any required part is
    missing or unresolvable.
    """
    geometry: dict = {}
    p1_node = find_child_any(entry, "point1", "p1")
    p2_node = find_child_any(entry, "point2", "p2")
    r1_node = find_child(entry, "radius1")
    r2_node = find_child(entry, "radius2")
    if p1_node is None or p2_node is None or r1_node is None or r2_node is None:
        return geometry
    p1 = resolve_vector(p1_node, var_map)
    p2 = resolve_vector(p2_node, var_map)
    r1 = resolve_scalar(r1_node, var_map)
    r2 = resolve_scalar(r2_node, var_map)
    if p1 is None or p2 is None or r1 is None or r2 is None:
        return geometry
    geometry["p1"] = p1
    geometry["p2"] = p2
    geometry["radius1"] = r1
    geometry["radius2"] = r2
    if allow_inner_radii:
        i1_node = find_child(entry, "innerRadius1")
        i2_node = find_child(entry, "innerRadius2")
        if i1_node is not None and i2_node is not None:
            i1 = resolve_scalar(i1_node, var_map)
            i2 = resolve_scalar(i2_node, var_map)
            if i1 is not None and i2 is not None:
                geometry["innerRadius1"] = i1
                geometry["innerRadius2"] = i2
    return geometry
