# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Extract renderable sampling geometry for the BlockMesh 3-D viewer.

Sources: ``probes``-type function objects (probe point markers), ``sets``-type
sample lines, and ``surfaces``-type sample planes. Definitions are read either
from a ``functions {}`` block (``controlDict``) or from a standalone
function-object dict (``system/sample``, ``system/probes``, ``system/surfaces``,
``system/singleGraph`` — including the .org ``singleGraph`` style whose
``start``/``end`` sit at the file's top level with no ``type`` entry).

Nested member lists come in two syntaxes, both walkable structural nodes the
parser produces. The dictionary form (``sets { lineA { … } }``) parses into
child dictionaries; the parenthesised list form (``sets ( lineA { … } );`` —
the classic sampleDict style) parses into a ``named_dict_list`` node with
``named_dict_entry`` children (see ``parser._OPTIONAL_NAMED_BLOCK_PARAMS``).
A ``sets``/``surfaces`` entry with no resolvable member list is listed as
non-geometric instead of silently dropped.

Shape classes follow the shared ``label``/``kind`` field scheme (see
``topo_set_extractor.TopoShape``).
"""
from __future__ import annotations

import dataclasses

from foam.nodes import FoamNode
from foam.shapes import SourceShape
from foam.tree_utils import (
    child_vector,
    find_child,
    find_child_any,
    resolve_plane_geometry,
    resolve_point_list,
)
from foam.var_resolver import build_var_map

# Function-object types whose probeLocations are drawn as point markers.
_PROBE_TYPES = frozenset({"probes", "patchProbes", "boundaryProbes"})

# Surface member types drawn as an (infinite) plane disc.
_PLANE_SURFACE_TYPES = frozenset({"plane", "cuttingPlane"})


@dataclasses.dataclass
class SamplingShape(SourceShape):
    """A sampling shape. Adds no fields of its own.

    Inherits label/kind/geometry/source_file from SourceShape (see foam/shapes.py):
    label = entry name, or "entry.member" for nested set/surface members; kind = e.g.
    "probes", "lineUniform", "plane", "patch"; geometry = {"points": …} |
    {"start": …, "end": …} | {"planePoint": …, "planeNormal": …}.
    """


@dataclasses.dataclass
class SamplingData:
    shapes: list[SamplingShape]
    # Recognised sampling entries with no drawable geometry (patch surfaces,
    # unparsed list-form sets/surfaces, …). Listed in the UI but not drawn.
    non_geometric: list[SamplingShape] = dataclasses.field(default_factory=list)


def _entry_type(entry: FoamNode) -> str:
    type_node = find_child(entry, "type")
    return str(type_node.value) if type_node is not None else ""


def _entry_label(entry: FoamNode) -> str:
    """Entry display name; a file-level root has none unless one was given."""
    return "" if entry.name == "root" else entry.name


# Keys a file-level dictionary of a sampling template defines for its members
# to refer to; never sampling entries themselves.
_VECTOR_NODE_TYPES = frozenset({"vector", "raw_list"})
_MAX_REFERENCE_DEPTH = 8


def _merge(base: list[FoamNode], own: list[FoamNode]) -> list[FoamNode]:
    """*own* entries over *base*, merging same-named dictionaries recursively.

    OpenFOAM's default ``inputMode merge``: ``yNormal { $cuttingPlane;
    pointAndNormalDict { normalVector $y; } }`` keeps the base's basePoint.
    """
    merged = list(base)
    for node in own:
        for i, existing in enumerate(merged):
            if existing.name and existing.name == node.name:
                if existing.node_type == node.node_type == "dictionary":
                    node = dataclasses.replace(
                        node, children=_merge(existing.children, node.children)
                    )
                merged[i] = node
                break
        else:
            merged.append(node)
    return merged


def _resolve_references(node: FoamNode, scope: dict[str, FoamNode], depth: int = 0) -> FoamNode:
    """A copy of *node* with the file's own ``$`` references filled in.

    FoDE's variable map holds scalars only, but sampling templates refer to
    whole vectors and dictionaries: OpenCFD's ``graph.cfg`` builds the line
    as ``line { $setConfig; start $start; end $end; }``, and its surfaces
    as ``xNormal { $cuttingPlane; }``. A ``$name;`` line splices the named
    top-level dictionary in (merged under the entry's own settings), and a
    ``key $name;`` value naming a top-level vector or list takes its value.
    Anything else is left as it is.
    """
    if depth > _MAX_REFERENCE_DEPTH or not node.children:
        return node
    spliced: list[FoamNode] = []
    own: list[FoamNode] = []
    for child in node.children:
        if child.node_type == "macro_entry":
            target = scope.get(str(child.value).lstrip("$"))
            if target is not None and target.node_type == "dictionary":
                spliced = _merge(spliced, list(target.children))
                continue
        if child.node_type == "macro":
            target = scope.get(str(child.value).lstrip("$"))
            if target is not None and target.node_type in _VECTOR_NODE_TYPES:
                child = dataclasses.replace(target, name=child.name)
        own.append(child)
    children = _merge(spliced, own)
    children = [_resolve_references(c, scope, depth + 1) for c in children]
    return dataclasses.replace(node, children=children)


def _resolve_line(entry: FoamNode, var_map: dict[str, str]) -> dict:
    """Return {"start", "end"} when the entry carries a resolvable line."""
    start = child_vector(entry, var_map, "start")
    end = child_vector(entry, var_map, "end")
    if start is None or end is None:
        return {}
    return {"start": start, "end": end}


def _find_member_dict(entry: FoamNode, key: str) -> FoamNode | None:
    """Return the node whose children are ``key``'s members, or None.

    Both member-list syntaxes are structural nodes the parser produces: the
    dictionary form ``key { … }`` (a ``dictionary`` child) and the classic
    parenthesised list form ``key ( name { … } … );`` (a ``named_dict_list``
    child, see ``parser._OPTIONAL_NAMED_BLOCK_PARAMS``).
    """
    child = find_child(entry, key)
    if child is not None and child.node_type in ("dictionary", "named_dict_list"):
        return child
    return None


def _member_label(entry: FoamNode, member: FoamNode) -> str:
    prefix = _entry_label(entry)
    return f"{prefix}.{member.name}" if prefix else member.name


def _extract_set_members(
    entry: FoamNode,
    var_map: dict[str, str],
    shapes: list[SamplingShape],
    non_geometric: list[SamplingShape],
    label: str = "",
) -> None:
    """Walk a sets-type entry's nested member list (either syntax)."""
    sets_node = _find_member_dict(entry, "sets")
    if sets_node is None:
        # Missing or unrecoverable: recognised but not drawable.
        non_geometric.append(SamplingShape(label=label, kind="sets", geometry={}))
        return
    for member in sets_node.children:
        if member.node_type not in ("dictionary", "named_dict_entry") or not member.name:
            continue
        label = _member_label(entry, member)
        kind = _entry_type(member) or "line"
        geometry = _resolve_line(member, var_map)
        if not geometry:
            points_node = find_child(member, "points")
            points = (
                resolve_point_list(points_node, var_map)
                if points_node is not None else None
            )
            if points:
                geometry = {"points": points}
        if geometry:
            shapes.append(SamplingShape(label=label, kind=kind, geometry=geometry))
        else:
            non_geometric.append(
                SamplingShape(label=label, kind=kind, geometry={})
            )


def _extract_surface_members(
    entry: FoamNode,
    var_map: dict[str, str],
    shapes: list[SamplingShape],
    non_geometric: list[SamplingShape],
    label: str = "",
) -> None:
    """Walk a surfaces-type entry's nested member list (either syntax)."""
    surfaces_node = _find_member_dict(entry, "surfaces")
    if surfaces_node is None:
        non_geometric.append(SamplingShape(label=label, kind="surfaces", geometry={}))
        return
    for member in surfaces_node.children:
        if member.node_type not in ("dictionary", "named_dict_entry") or not member.name:
            continue
        label = _member_label(entry, member)
        kind = _entry_type(member)
        # No type: the plane's settings may come from a .cfg FoDE could not
        # read; a point and normal still make it drawable as a plane.
        geometry = (
            resolve_plane_geometry(
                member, var_map, allow_aliases=True, nested_dict="pointAndNormalDict"
            )
            if kind in _PLANE_SURFACE_TYPES or not kind else {}
        )
        if geometry and not kind:
            kind = "cuttingPlane"
        if geometry:
            shapes.append(SamplingShape(label=label, kind=kind, geometry=geometry))
        else:
            non_geometric.append(
                SamplingShape(label=label, kind=kind or "surface", geometry={})
            )


def _extract_candidate(
    entry: FoamNode,
    var_map: dict[str, str],
    shapes: list[SamplingShape],
    non_geometric: list[SamplingShape],
    file_label: str = "",
) -> None:
    """One function-object entry's shapes.

    *file_label* names what the file defines at its top level (the root
    has no name of its own); a named entry keeps its own name, and its
    members are named after themselves -- each menu row already says which
    file it came from.
    """
    label = _entry_label(entry) or file_label
    entry_type = _entry_type(entry)
    if not entry_type:
        # A template whose type is in the .cfg it includes, which FoDE may not
        # have been able to read: what it holds says what it is. Foundation
        # spells the probe locations `points`.
        if find_child_any(entry, "probeLocations", "points") is not None:
            entry_type = "probes"
        elif _find_member_dict(entry, "sets") is not None:
            entry_type = "sets"
        elif _find_member_dict(entry, "surfaces") is not None:
            entry_type = "surfaces"
    if entry_type in _PROBE_TYPES:
        points_node = find_child_any(entry, "probeLocations", "points")
        points = (
            resolve_point_list(points_node, var_map)
            if points_node is not None else None
        )
        if points:
            shapes.append(
                SamplingShape(label=label, kind=entry_type, geometry={"points": points})
            )
        else:
            non_geometric.append(SamplingShape(label=label, kind=entry_type, geometry={}))
    elif entry_type == "sets":
        _extract_set_members(entry, var_map, shapes, non_geometric, label)
    elif entry_type == "surfaces":
        _extract_surface_members(entry, var_map, shapes, non_geometric, label)
    elif not entry_type:
        # singleGraph-style: bare start/end with no `type` (file top level);
        # Foundation's cutPlaneSurface: a bare point and normal.
        geometry = _resolve_line(entry, var_map)
        if geometry:
            shapes.append(SamplingShape(label=label, kind="line", geometry=geometry))
            return
        geometry = resolve_plane_geometry(entry, var_map)
        if geometry and find_child(entry, "sets") is None and find_child(entry, "surfaces") is None:
            shapes.append(SamplingShape(label=label, kind="cutPlane", geometry=geometry))
    # Any other function-object type (forces, fieldAverage, …) is unrelated to
    # sampling and intentionally ignored rather than listed as non-geometric.


def extract_sampling_data(root: FoamNode, name: str = "") -> SamplingData:
    """Collect sampling shapes from a controlDict or standalone sampling dict.

    *name* labels what the file defines at its top level -- a standalone
    ``system/probes`` is one unnamed function object, and the file name is
    the name OpenFOAM gives it too (``#includeFunc probes``).
    """
    scope = {c.name: c for c in root.children if c.name}
    root = _resolve_references(root, scope)
    var_map = build_var_map(root)
    shapes: list[SamplingShape] = []
    non_geometric: list[SamplingShape] = []

    functions_node = find_child(root, "functions")
    if functions_node is not None and functions_node.node_type == "dictionary":
        candidates = [
            child for child in functions_node.children
            if child.node_type == "dictionary" and child.name
        ]
    else:
        # Standalone file: the root itself may be the function-object dict
        # (system/sample, singleGraph) or hold several named ones.
        candidates = [root] + [
            child for child in root.children
            if child.node_type == "dictionary" and child.name
            and child.name != "FoamFile"
        ]

    for entry in candidates:
        _extract_candidate(entry, var_map, shapes, non_geometric, name if entry is root else "")

    return SamplingData(shapes=shapes, non_geometric=non_geometric)
