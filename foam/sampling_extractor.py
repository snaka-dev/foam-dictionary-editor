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
    find_child,
    resolve_plane_geometry,
    resolve_point_list,
    resolve_vector,
)
from foam.var_resolver import build_var_map

# Function-object types whose probeLocations are drawn as point markers.
_PROBE_TYPES = frozenset({"probes", "patchProbes", "boundaryProbes"})

# Surface member types drawn as an (infinite) plane disc.
_PLANE_SURFACE_TYPES = frozenset({"plane", "cuttingPlane"})


@dataclasses.dataclass
class SamplingShape(SourceShape):
    # Inherits label/kind/geometry from SourceShape (see foam/shapes.py):
    # label = entry name, or "entry.member" for nested set/surface members;
    # kind = e.g. "probes", "lineUniform", "plane", "patch"; geometry =
    # {"points": …} | {"start": …, "end": …} | {"planePoint": …, "planeNormal": …}.
    source_file: str = ""  # basename of the defining file; filled by the UI layer


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
    """Entry display name; a file-level root has no meaningful name."""
    return "" if entry.name == "root" else entry.name


def _resolve_line(entry: FoamNode, var_map: dict[str, str]) -> dict:
    """Return {"start", "end"} when the entry carries a resolvable line."""
    start_node = find_child(entry, "start")
    end_node = find_child(entry, "end")
    if start_node is None or end_node is None:
        return {}
    start = resolve_vector(start_node, var_map)
    end = resolve_vector(end_node, var_map)
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
) -> None:
    """Walk a sets-type entry's nested member list (either syntax)."""
    sets_node = _find_member_dict(entry, "sets")
    if sets_node is None:
        # Missing or unrecoverable: recognised but not drawable.
        non_geometric.append(
            SamplingShape(label=_entry_label(entry), kind="sets", geometry={})
        )
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
) -> None:
    """Walk a surfaces-type entry's nested member list (either syntax)."""
    surfaces_node = _find_member_dict(entry, "surfaces")
    if surfaces_node is None:
        non_geometric.append(
            SamplingShape(label=_entry_label(entry), kind="surfaces", geometry={})
        )
        return
    for member in surfaces_node.children:
        if member.node_type not in ("dictionary", "named_dict_entry") or not member.name:
            continue
        label = _member_label(entry, member)
        kind = _entry_type(member)
        geometry = (
            resolve_plane_geometry(
                member, var_map, allow_aliases=True, nested_dict="pointAndNormalDict"
            )
            if kind in _PLANE_SURFACE_TYPES else {}
        )
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
) -> None:
    entry_type = _entry_type(entry)
    if entry_type in _PROBE_TYPES:
        points_node = find_child(entry, "probeLocations")
        points = (
            resolve_point_list(points_node, var_map)
            if points_node is not None else None
        )
        if points:
            shapes.append(
                SamplingShape(
                    label=_entry_label(entry), kind=entry_type, geometry={"points": points}
                )
            )
        else:
            non_geometric.append(
                SamplingShape(label=_entry_label(entry), kind=entry_type, geometry={})
            )
    elif entry_type == "sets":
        _extract_set_members(entry, var_map, shapes, non_geometric)
    elif entry_type == "surfaces":
        _extract_surface_members(entry, var_map, shapes, non_geometric)
    elif not entry_type:
        # singleGraph-style: bare start/end with no `type` (file top level).
        geometry = _resolve_line(entry, var_map)
        if geometry:
            shapes.append(
                SamplingShape(label=_entry_label(entry), kind="line", geometry=geometry)
            )
    # Any other function-object type (forces, fieldAverage, …) is unrelated to
    # sampling and intentionally ignored rather than listed as non-geometric.


def extract_sampling_data(root: FoamNode) -> SamplingData:
    """Collect sampling shapes from a controlDict or standalone sampling dict."""
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
        _extract_candidate(entry, var_map, shapes, non_geometric)

    return SamplingData(shapes=shapes, non_geometric=non_geometric)
