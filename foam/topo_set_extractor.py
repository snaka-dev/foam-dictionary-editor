# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Extract renderable geometry from a topoSetDict FoamNode tree."""
from __future__ import annotations

import dataclasses
import re

from foam.nodes import FoamNode
from foam.tree_utils import (
    expand_evals,
    find_child,
    resolve_cone_geometry,
    resolve_cylinder_geometry,
    resolve_sphere_geometry,
    resolve_vector,
)
from foam.utils import parse_box_pair
from foam.var_resolver import build_var_map, substitute_vars

_BOX_SOURCES = frozenset({"boxToCell", "boxToFace", "boxToPoint"})
_SPHERE_SOURCES = frozenset({"sphereToCell", "sphereToFace", "sphereToPoint"})
_CYLINDER_SOURCES = frozenset(
    {"cylinderToCell", "cylinderToFace", "cylinderToPoint", "cylinderAnnulusToCell"}
)
_CONE_SOURCES = frozenset(
    {"coneToCell", "coneToFace", "coneToPoint", "coneAnnulusToCell"}
)
_ROTATED_BOX_SOURCES = frozenset(
    {"rotatedBoxToCell", "rotatedBoxToFace", "rotatedBoxToPoint"}
)
# Sources whose geometry is a set of loose points, drawn as labelled markers.
_POINT_SOURCES = frozenset(
    {"nearestToCell", "nearestToPoint", "regionToCell", "regionToFace"}
)
# Sources defined by an infinite plane (point + normal); drawn as a disc.
_PLANE_SOURCES = frozenset({"planeToFaceZone"})
_GEOMETRIC_SOURCES = (
    _BOX_SOURCES | _SPHERE_SOURCES | _CYLINDER_SOURCES
    | _CONE_SOURCES | _ROTATED_BOX_SOURCES
    | _POINT_SOURCES | _PLANE_SOURCES
)

# Matches any topoSet source name of the form "<x>To<Set>" (e.g. cellToFace,
# zoneToCell). Used to recognise non-geometric sources so they can still be listed.
_SOURCE_NAME_RE = re.compile(r"^\w+To(Cell|Face|Point|Set|Zone)\w*$")

# Keys that are structural in topoSetDict (not variable definitions).
_TOPO_STRUCTURAL = frozenset({"actions"})


@dataclasses.dataclass
class TopoShape:
    label: str    # value of the action's 'name' entry, or ""
    source: str   # e.g. "boxToCell", "sphereToCell", "cylinderToCell"
    action: str   # e.g. "new", "add", "subtract", "subset", "invert"
    geometry: dict  # parsed geometry: keys depend on source type


@dataclasses.dataclass
class TopoSetData:
    shapes: list[TopoShape]
    # Recognised sources that carry no renderable geometry (set/field/surface
    # references, e.g. cellToFace, zoneToCell). Listed in the UI but not drawn.
    non_geometric: list[TopoShape] = dataclasses.field(default_factory=list)


def _find_action_list(root: FoamNode) -> FoamNode | None:
    for child in root.children:
        if child.node_type == "action_list":
            return child
    return None


def _resolve_box_pair(node: FoamNode, var_map: dict[str, str]) -> list[list[float]] | None:
    """Return [[x,y,z],[x,y,z]] from a box_pair/raw_list node, resolving $vars."""
    if node.node_type == "box_pair":
        return node.value
    if node.node_type == "raw_list":
        # raw_list strips the outer parens; prepend '(' to restore the expected format.
        text = expand_evals(substitute_vars(str(node.value), var_map))
        return parse_box_pair("(" + text + ")")
    return None


def _scan_vectors(text: str) -> list[list[float]] | None:
    """Parse every top-level '(x y z)' group in *text* into a float triple."""
    vectors: list[list[float]] = []
    for match in re.finditer(r"\(([^()]*)\)", text):
        items = match.group(1).split()
        if len(items) != 3:
            return None
        try:
            vectors.append([float(x) for x in items])
        except ValueError:
            return None
    return vectors or None


def _resolve_point_list(node: FoamNode, var_map: dict[str, str]) -> list[list[float]] | None:
    """Return [[x,y,z], …] from a raw_list of points, resolving $vars/#eval."""
    if node.node_type != "raw_list":
        return None
    text = expand_evals(substitute_vars(str(node.value), var_map))
    return _scan_vectors(text)


def _resolve_box_pairs(node: FoamNode, var_map: dict[str, str]) -> list[list[list[float]]] | None:
    """Return [[[min],[max]], …] from a raw_list of (min) (max) vector pairs."""
    vectors = _resolve_point_list(node, var_map)
    if vectors is None or len(vectors) < 2 or len(vectors) % 2 != 0:
        return None
    return [[vectors[i], vectors[i + 1]] for i in range(0, len(vectors), 2)]


def resolve_source_geometry(
    source: str, entry: FoamNode, var_map: dict[str, str]
) -> dict:
    """Resolve the geometry dict for one topoSet-style source block.

    ``entry`` holds the geometry keys as children (box/centre/p1/…). Shared
    with the setFieldsDict extractor, whose ``regions`` entries use the same
    source names and geometry keywords. Returns {} when the source is not
    geometric or a required part is missing/unresolvable.
    """
    geometry: dict = {}
    if source in _BOX_SOURCES:
        node = find_child(entry, "box")
        min_node = find_child(entry, "min")
        max_node = find_child(entry, "max")
        boxes_node = find_child(entry, "boxes")
        if node is not None:
            val = _resolve_box_pair(node, var_map)
            if val is not None:
                geometry["box"] = val
        elif min_node is not None and max_node is not None:
            mn = resolve_vector(min_node, var_map)
            mx = resolve_vector(max_node, var_map)
            if mn is not None and mx is not None:
                geometry["box"] = [mn, mx]
        elif boxes_node is not None:
            pairs = _resolve_box_pairs(boxes_node, var_map)
            if pairs is not None:
                geometry["boxes"] = pairs
    elif source in _ROTATED_BOX_SOURCES:
        o_node = find_child(entry, "origin")
        i_node = find_child(entry, "i")
        j_node = find_child(entry, "j")
        k_node = find_child(entry, "k")
        if (
            o_node is not None and i_node is not None
            and j_node is not None and k_node is not None
        ):
            origin = resolve_vector(o_node, var_map)
            i = resolve_vector(i_node, var_map)
            j = resolve_vector(j_node, var_map)
            k = resolve_vector(k_node, var_map)
            if (
                origin is not None and i is not None
                and j is not None and k is not None
            ):
                geometry["origin"] = origin
                geometry["i"] = i
                geometry["j"] = j
                geometry["k"] = k
    elif source in _SPHERE_SOURCES:
        geometry = resolve_sphere_geometry(entry, var_map, allow_inner_radius=True)
    elif source in _CYLINDER_SOURCES:
        geometry = resolve_cylinder_geometry(entry, var_map)
    elif source in _CONE_SOURCES:
        geometry = resolve_cone_geometry(entry, var_map, allow_inner_radii=True)
    elif source in _POINT_SOURCES:
        points: list[list[float]] | None = None
        if source in ("nearestToCell", "nearestToPoint"):
            pts_node = find_child(entry, "points")
            if pts_node is not None:
                points = _resolve_point_list(pts_node, var_map)
        elif source == "regionToCell":
            pts_node = find_child(entry, "insidePoints")
            if pts_node is not None:
                points = _resolve_point_list(pts_node, var_map)
            else:
                single_node = find_child(entry, "insidePoint")
                if single_node is not None:
                    single = resolve_vector(single_node, var_map)
                    if single is not None:
                        points = [single]
        elif source == "regionToFace":
            near_node = find_child(entry, "nearPoint")
            if near_node is not None:
                near = resolve_vector(near_node, var_map)
                if near is not None:
                    points = [near]
        if points:
            geometry["points"] = points
    elif source in _PLANE_SOURCES:
        pt_node = find_child(entry, "point")
        n_node = find_child(entry, "normal")
        if pt_node is not None and n_node is not None:
            point = resolve_vector(pt_node, var_map)
            normal = resolve_vector(n_node, var_map)
            if point is not None and normal is not None:
                geometry["planePoint"] = point
                geometry["planeNormal"] = normal
    return geometry


def is_non_geometric_source(source: str) -> bool:
    """True for a recognisable source name that carries no drawable geometry.

    Set/field/surface references (cellToFace, zoneToCell, …) match; geometric
    sources that merely fail to resolve do not, so they are not mislabelled.
    """
    return bool(
        source
        and source not in _GEOMETRIC_SOURCES
        and _SOURCE_NAME_RE.match(source)
    )


def extract_topo_set_data(root: FoamNode) -> TopoSetData:
    """Walk action_list → action_entry nodes and collect renderable shapes."""
    var_map = build_var_map(root, skip_keys=_TOPO_STRUCTURAL)

    action_list = _find_action_list(root)
    if action_list is None:
        return TopoSetData(shapes=[])

    shapes: list[TopoShape] = []
    non_geometric: list[TopoShape] = []
    for entry in action_list.children:
        if entry.node_type != "action_entry":
            continue

        source_node = find_child(entry, "source")
        source = str(source_node.value) if source_node else ""
        label_node = find_child(entry, "name")
        label = str(label_node.value) if label_node else ""
        action_node = find_child(entry, "action")
        action = str(action_node.value) if action_node else "new"

        geometry = resolve_source_geometry(source, entry, var_map)
        if geometry:
            shapes.append(
                TopoShape(label=label, source=source, action=action, geometry=geometry)
            )
        elif is_non_geometric_source(source):
            non_geometric.append(
                TopoShape(label=label, source=source, action=action, geometry={})
            )

    return TopoSetData(shapes=shapes, non_geometric=non_geometric)
