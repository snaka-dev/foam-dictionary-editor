# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Extract renderable geometry from a topoSetDict FoamNode tree."""
from __future__ import annotations

import dataclasses
import re

from foam.nodes import FoamNode
from foam.utils import parse_box_pair
from foam.var_resolver import build_var_map, eval_foam_expr, substitute_vars

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
_GEOMETRIC_SOURCES = (
    _BOX_SOURCES | _SPHERE_SOURCES | _CYLINDER_SOURCES
    | _CONE_SOURCES | _ROTATED_BOX_SOURCES
)

# Matches any topoSet source name of the form "<x>To<Set>" (e.g. cellToFace,
# zoneToCell). Used to recognise non-geometric sources so they can still be listed.
_SOURCE_NAME_RE = re.compile(r"^\w+To(Cell|Face|Point|Set|Zone)\w*$")

# Keys that are structural in topoSetDict (not variable definitions).
_TOPO_STRUCTURAL = frozenset({"actions"})

# Matches #eval{...} fragments inside a substituted string.
_INLINE_EVAL_RE = re.compile(r'#eval\s*\{([^}]+)\}')


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


def _find_child(entry: FoamNode, key: str) -> FoamNode | None:
    for child in entry.children:
        if child.name == key:
            return child
    return None


def _find_child_any(entry: FoamNode, *keys: str) -> FoamNode | None:
    """Return the first child matching any of the given key aliases."""
    for key in keys:
        node = _find_child(entry, key)
        if node is not None:
            return node
    return None


def _expand_evals(text: str) -> str:
    """Evaluate any #eval{...} fragments in an already-var-substituted string."""
    def _repl(m: re.Match) -> str:
        result = eval_foam_expr(m.group(1))
        return result if result is not None else m.group(0)
    return _INLINE_EVAL_RE.sub(_repl, text)


def _resolve_scalar(node: FoamNode, var_map: dict[str, str]) -> float | None:
    """Return a float from a scalar/int/macro/word node, resolving $vars."""
    if node.node_type in ("scalar", "int"):
        return float(node.value)
    if node.node_type == "macro":
        ref = str(node.value).lstrip("$").strip("{}")
        val = var_map.get(ref)
        if val is not None:
            return float(val)
    if node.node_type in ("word", "compound"):
        text = _expand_evals(substitute_vars(str(node.value), var_map))
        result = eval_foam_expr(text)
        if result is not None:
            return float(result)
    return None


def _resolve_vector(node: FoamNode, var_map: dict[str, str]) -> list[float] | None:
    """Return [x, y, z] from a vector/raw_list node, resolving $vars."""
    if node.node_type == "vector":
        return node.value
    if node.node_type == "raw_list":
        text = _expand_evals(substitute_vars(str(node.value), var_map))
        parts = text.split()
        if len(parts) == 3:
            try:
                return [float(p) for p in parts]
            except ValueError:
                pass
    return None


def _resolve_box_pair(node: FoamNode, var_map: dict[str, str]) -> list[list[float]] | None:
    """Return [[x,y,z],[x,y,z]] from a box_pair/raw_list node, resolving $vars."""
    if node.node_type == "box_pair":
        return node.value
    if node.node_type == "raw_list":
        # raw_list strips the outer parens; prepend '(' to restore the expected format.
        text = _expand_evals(substitute_vars(str(node.value), var_map))
        return parse_box_pair("(" + text + ")")
    return None


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

        source_node = _find_child(entry, "source")
        source = str(source_node.value) if source_node else ""
        label_node = _find_child(entry, "name")
        label = str(label_node.value) if label_node else ""
        action_node = _find_child(entry, "action")
        action = str(action_node.value) if action_node else "new"

        geometry: dict = {}
        if source in _BOX_SOURCES:
            node = _find_child(entry, "box")
            if node is not None:
                val = _resolve_box_pair(node, var_map)
                if val is not None:
                    geometry["box"] = val
        elif source in _ROTATED_BOX_SOURCES:
            o_node = _find_child(entry, "origin")
            i_node = _find_child(entry, "i")
            j_node = _find_child(entry, "j")
            k_node = _find_child(entry, "k")
            if (
                o_node is not None and i_node is not None
                and j_node is not None and k_node is not None
            ):
                origin = _resolve_vector(o_node, var_map)
                i = _resolve_vector(i_node, var_map)
                j = _resolve_vector(j_node, var_map)
                k = _resolve_vector(k_node, var_map)
                if (
                    origin is not None and i is not None
                    and j is not None and k is not None
                ):
                    geometry["origin"] = origin
                    geometry["i"] = i
                    geometry["j"] = j
                    geometry["k"] = k
        elif source in _SPHERE_SOURCES:
            c_node = _find_child(entry, "centre")
            r_node = _find_child(entry, "radius")
            if c_node is not None and r_node is not None:
                centre = _resolve_vector(c_node, var_map)
                radius = _resolve_scalar(r_node, var_map)
                if centre is not None and radius is not None:
                    geometry["centre"] = centre
                    geometry["radius"] = radius
        elif source in _CYLINDER_SOURCES:
            p1_node = _find_child_any(entry, "point1", "p1")
            p2_node = _find_child_any(entry, "point2", "p2")
            r_node = _find_child(entry, "radius")
            if p1_node is not None and p2_node is not None and r_node is not None:
                p1 = _resolve_vector(p1_node, var_map)
                p2 = _resolve_vector(p2_node, var_map)
                radius = _resolve_scalar(r_node, var_map)
                if p1 is not None and p2 is not None and radius is not None:
                    geometry["p1"] = p1
                    geometry["p2"] = p2
                    geometry["radius"] = radius
                    inner_node = _find_child(entry, "innerRadius")
                    if inner_node is not None:
                        inner = _resolve_scalar(inner_node, var_map)
                        if inner is not None:
                            geometry["innerRadius"] = inner
        elif source in _CONE_SOURCES:
            p1_node = _find_child_any(entry, "point1", "p1")
            p2_node = _find_child_any(entry, "point2", "p2")
            r1_node = _find_child(entry, "radius1")
            r2_node = _find_child(entry, "radius2")
            if (
                p1_node is not None and p2_node is not None
                and r1_node is not None and r2_node is not None
            ):
                p1 = _resolve_vector(p1_node, var_map)
                p2 = _resolve_vector(p2_node, var_map)
                r1 = _resolve_scalar(r1_node, var_map)
                r2 = _resolve_scalar(r2_node, var_map)
                if p1 is not None and p2 is not None and r1 is not None and r2 is not None:
                    geometry["p1"] = p1
                    geometry["p2"] = p2
                    geometry["radius1"] = r1
                    geometry["radius2"] = r2
                    i1_node = _find_child(entry, "innerRadius1")
                    i2_node = _find_child(entry, "innerRadius2")
                    if i1_node is not None and i2_node is not None:
                        i1 = _resolve_scalar(i1_node, var_map)
                        i2 = _resolve_scalar(i2_node, var_map)
                        if i1 is not None and i2 is not None:
                            geometry["innerRadius1"] = i1
                            geometry["innerRadius2"] = i2

        if geometry:
            shapes.append(
                TopoShape(label=label, source=source, action=action, geometry=geometry)
            )
        elif (
            source
            and source not in _GEOMETRIC_SOURCES
            and _SOURCE_NAME_RE.match(source)
        ):
            # A recognisable topoSet source that carries no drawable geometry
            # (set/field/surface reference). Geometric sources that merely fail
            # to resolve are left out so they are not mislabelled here.
            non_geometric.append(
                TopoShape(label=label, source=source, action=action, geometry={})
            )

    return TopoSetData(shapes=shapes, non_geometric=non_geometric)
