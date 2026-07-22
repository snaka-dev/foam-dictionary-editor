# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Extract renderable geometry from a snappyHexMeshDict FoamNode tree.

Reads the ``geometry {}`` block (searchable-surface primitives and STL/OBJ
references) and cross-references it with ``castellatedMeshControls``'s
``refinementSurfaces`` / ``refinementRegions`` to classify each shape, plus
the ``locationInMesh`` / ``locationsInMesh`` keep-point(s).
"""
from __future__ import annotations

import dataclasses
import re
from pathlib import Path

from foam.nodes import FoamNode
from foam.tree_utils import (
    expand_evals,
    find_child,
    resolve_box_geometry,
    resolve_cone_geometry,
    resolve_cylinder_geometry,
    resolve_sphere_geometry,
    resolve_vector,
)
from foam.utils import resolve_optionally_gzipped
from foam.var_resolver import build_var_map, substitute_vars

_TRISURFACE_EXTENSIONS = (".stl", ".stlb", ".obj")
_TRISURFACE_GZ_EXTENSIONS = tuple(ext + ".gz" for ext in _TRISURFACE_EXTENSIONS)

# Matches a "((x y z) name)" pair inside locationsInMesh's raw source text.
_LOCATION_PAIR_RE = re.compile(
    r'\(\s*\(\s*([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s*\)\s+(\S+?)\s*\)'
)

# Characters that indicate a refinementSurfaces/Regions key is a regex pattern
# (e.g. "iglo.*") rather than a literal geometry name.
_REGEX_META = frozenset(".*+?[]^$|\\")


@dataclasses.dataclass
class SnappyShape:
    # `label`/`kind`: shared field names across all extractor shape classes.
    label: str                             # resolved cross-reference name
    kind: str                              # e.g. "box", "sphere", "triSurfaceMesh"
    category: str                          # "surface" | "region" | "geometry"
    geometry: dict                         # same key convention as TopoShape.geometry
    level: tuple[float, float] | None = None      # from refinementSurfaces
    mode: str | None = None                       # from refinementRegions


@dataclasses.dataclass
class SnappyHexMeshData:
    shapes: list[SnappyShape]
    # geometry entries with no drawable geometry (unresolved STL, "collection", ...)
    non_geometric: list[SnappyShape] = dataclasses.field(default_factory=list)
    location_points: list[tuple[list[float], str]] = dataclasses.field(default_factory=list)


def _cross(a: list[float], b: list[float]) -> list[float]:
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]


def _normalize(v: list[float]) -> list[float] | None:
    norm = sum(c * c for c in v) ** 0.5
    if norm == 0.0:
        return None
    return [c / norm for c in v]


def _mat_vec(cols: tuple[list[float], list[float], list[float]], v: list[float]) -> list[float]:
    """Multiply a 3x3 matrix (given as its 3 column vectors) by a vector."""
    return [
        cols[0][i] * v[0] + cols[1][i] * v[1] + cols[2][i] * v[2]
        for i in range(3)
    ]


def _add(a: list[float], b: list[float]) -> list[float]:
    return [a[i] + b[i] for i in range(3)]


def _unquote(text: str) -> str:
    text = text.strip()
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        return text[1:-1]
    return text


def _resolve_name(entry: FoamNode) -> str:
    """Return the geometry entry's cross-referenceable name.

    A ``name`` child overrides the entry's own key, e.g.
    ``geom.stl { type triSurfaceMesh; name geom; }`` is referred to as
    "geom" by refinementSurfaces, not "geom.stl".
    """
    name_node = find_child(entry, "name")
    if name_node is not None and name_node.value:
        return _unquote(str(name_node.value))
    return _unquote(entry.name)


def _resolve_stl_path(entry: FoamNode, entry_key: str, case_dir: str | None) -> str | None:
    if case_dir is None:
        return None
    file_node = find_child(entry, "file")
    if file_node is not None and file_node.value:
        filename = _unquote(str(file_node.value))
    elif entry_key.lower().endswith(_TRISURFACE_EXTENSIONS + _TRISURFACE_GZ_EXTENSIONS):
        filename = entry_key
    else:
        return None
    path = Path(case_dir) / "constant" / "triSurface" / filename
    resolved = resolve_optionally_gzipped(path)
    return str(resolved) if resolved is not None else None


def _extract_geometry_entry(
    entry: FoamNode, var_map: dict[str, str], case_dir: str | None
) -> tuple[str, dict]:
    """Return (geo_type, geometry) for one named entry under 'geometry {}'."""
    type_node = find_child(entry, "type")
    geo_type = str(type_node.value) if type_node is not None else ""
    geometry: dict = {}

    if geo_type == "box":
        geometry = resolve_box_geometry(entry, var_map)
    elif geo_type == "sphere":
        geometry = resolve_sphere_geometry(entry, var_map, allow_vector_radius=True)
    elif geo_type == "cylinder":
        geometry = resolve_cylinder_geometry(entry, var_map)
    elif geo_type == "cone":
        geometry = resolve_cone_geometry(entry, var_map)
    elif geo_type in ("triSurfaceMesh", "distributedTriSurfaceMesh"):
        stl_path = _resolve_stl_path(entry, _unquote(entry.name), case_dir)
        if stl_path is not None:
            geometry["stl_path"] = stl_path

    return geo_type, geometry


def _collection_rotation(transform: FoamNode, var_map: dict[str, str]):
    """Return the 3 column vectors of a rotation matrix from a `transform` block.

    Supports `rotation none;` (identity) and an `e1`/`e3` axis pair (the other
    two forms snappyHexMesh's coordinateSystem/transform accepts). Anything
    else — a different rotation specification, or a missing one — is
    unsupported here and returns None.
    """
    rotation_node = find_child(transform, "rotation")
    if rotation_node is not None and str(rotation_node.value) == "none":
        return ([1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0])
    e1_node = find_child(transform, "e1")
    e3_node = find_child(transform, "e3")
    if e1_node is None or e3_node is None:
        return None
    e1 = resolve_vector(e1_node, var_map)
    e3 = resolve_vector(e3_node, var_map)
    if e1 is None or e3 is None:
        return None
    e1n = _normalize(e1)
    if e1n is None:
        return None
    e2 = _normalize(_cross(e3, e1n))
    if e2 is None:
        return None
    e3n = _cross(e1n, e2)
    return (e1n, e2, e3n)


def _extract_collection_members(
    entry: FoamNode, shapes: dict[str, SnappyShape], var_map: dict[str, str]
) -> list[SnappyShape]:
    """Resolve a `type collection` (searchableSurfaceCollection) entry's members.

    Only members referencing an already-extracted `box`-type base surface are
    handled — each becomes an oriented box (`origin`/`i`/`j`/`k`, the same
    convention `_make_shape_mesh` already renders for topoSet's rotated box).
    Members with a non-box base, or an unsupported/missing transform, are
    silently skipped; the caller falls back to listing the whole collection as
    non-geometric if nothing could be resolved.
    """
    members: list[SnappyShape] = []
    for sub in entry.children:
        if sub.node_type != "dictionary" or not sub.name:
            continue
        surface_node = find_child(sub, "surface")
        if surface_node is None:
            continue
        base = shapes.get(_unquote(str(surface_node.value)))
        if base is None or "box" not in base.geometry:
            continue

        scale_node = find_child(sub, "scale")
        scale = resolve_vector(scale_node, var_map) if scale_node is not None else [1.0, 1.0, 1.0]
        if scale is None:
            continue

        transform_node = find_child(sub, "transform")
        if transform_node is None or transform_node.node_type != "dictionary":
            continue
        origin_node = find_child(transform_node, "origin")
        if origin_node is None:
            continue
        origin = resolve_vector(origin_node, var_map)
        if origin is None:
            continue
        rotation = _collection_rotation(transform_node, var_map)
        if rotation is None:
            continue

        mn, mx = base.geometry["box"]
        size = [(mx[i] - mn[i]) * scale[i] for i in range(3)]
        corner_local = [mn[i] * scale[i] for i in range(3)]
        origin_world = _add(_mat_vec(rotation, corner_local), origin)
        i_vec = _mat_vec(rotation, [size[0], 0.0, 0.0])
        j_vec = _mat_vec(rotation, [0.0, size[1], 0.0])
        k_vec = _mat_vec(rotation, [0.0, 0.0, size[2]])

        members.append(SnappyShape(
            label=f"{_unquote(entry.name)}.{_unquote(sub.name)}",
            kind="collection_box",
            category="geometry",
            geometry={"origin": origin_world, "i": i_vec, "j": j_vec, "k": k_vec},
        ))
    return members


def _match_name(key: str, names: list[str]) -> str | None:
    """Match a refinementSurfaces/Regions key against known geometry names.

    Tries an exact match first, then treats the key as a regex — snappyHexMesh
    allows quoted patterns like "iglo.*" to match geometry names (e.g. "igloo").
    """
    key = _unquote(key)
    if key in names:
        return key
    if any(c in key for c in _REGEX_META):
        try:
            pattern = re.compile(key)
        except re.error:
            return None
        for name in names:
            if pattern.fullmatch(name):
                return name
    return None


def extract_snappy_hex_mesh_data(
    root: FoamNode, case_dir: str | None = None
) -> SnappyHexMeshData:
    """Walk geometry / castellatedMeshControls and collect renderable shapes.

    ``case_dir`` (the directory containing ``system/`` and ``constant/``) is
    used only to resolve triSurfaceMesh file references under
    ``constant/triSurface/``; pass ``None`` to skip STL/OBJ resolution.
    """
    var_map = build_var_map(root)

    shapes: dict[str, SnappyShape] = {}
    non_geometric: list[SnappyShape] = []

    geometry_node = find_child(root, "geometry")
    collection_entries: list[FoamNode] = []
    if geometry_node is not None:
        for entry in geometry_node.children:
            if entry.node_type != "dictionary" or not entry.name:
                continue
            type_node = find_child(entry, "type")
            if type_node is not None and str(type_node.value) == "collection":
                # Deferred: members reference other geometry entries, so they can
                # only be resolved once every primitive above has been collected.
                collection_entries.append(entry)
                continue
            geo_type, geometry = _extract_geometry_entry(entry, var_map, case_dir)
            if not geo_type:
                continue
            name = _resolve_name(entry)
            shape = SnappyShape(label=name, kind=geo_type, category="geometry", geometry=geometry)
            if geometry:
                shapes[name] = shape
            else:
                non_geometric.append(shape)

        for entry in collection_entries:
            members = _extract_collection_members(entry, shapes, var_map)
            if members:
                for member in members:
                    shapes[member.label] = member
            else:
                non_geometric.append(
                    SnappyShape(
                        label=_resolve_name(entry), kind="collection",
                        category="geometry", geometry={},
                    )
                )

    known_names = list(shapes.keys())
    location_points: list[tuple[list[float], str]] = []

    cmc_node = find_child(root, "castellatedMeshControls")
    if cmc_node is not None:
        rs_node = find_child(cmc_node, "refinementSurfaces")
        if rs_node is not None:
            for entry in rs_node.children:
                if entry.node_type != "dictionary" or not entry.name:
                    continue
                matched = _match_name(entry.name, known_names)
                if matched is None:
                    continue
                level_node = find_child(entry, "level")
                if (
                    level_node is not None
                    and isinstance(level_node.value, list)
                    and len(level_node.value) == 2
                ):
                    shapes[matched].level = (float(level_node.value[0]), float(level_node.value[1]))
                shapes[matched].category = "surface"

        rr_node = find_child(cmc_node, "refinementRegions")
        if rr_node is not None:
            for entry in rr_node.children:
                if entry.node_type != "dictionary" or not entry.name:
                    continue
                matched = _match_name(entry.name, known_names)
                if matched is None:
                    continue
                mode_node = find_child(entry, "mode")
                if mode_node is not None:
                    shapes[matched].mode = str(mode_node.value)
                if shapes[matched].category != "surface":
                    shapes[matched].category = "region"

        loc_node = find_child(cmc_node, "locationInMesh")
        if loc_node is not None:
            point = resolve_vector(loc_node, var_map)
            if point is not None:
                location_points.append((point, "locationInMesh"))

        locs_node = find_child(cmc_node, "locationsInMesh")
        if locs_node is not None:
            text = expand_evals(substitute_vars(str(locs_node.value), var_map))
            for m in _LOCATION_PAIR_RE.finditer(text):
                try:
                    pt = [float(m.group(1)), float(m.group(2)), float(m.group(3))]
                except ValueError:
                    continue
                location_points.append((pt, m.group(4)))

    return SnappyHexMeshData(
        shapes=list(shapes.values()),
        non_geometric=non_geometric,
        location_points=location_points,
    )
