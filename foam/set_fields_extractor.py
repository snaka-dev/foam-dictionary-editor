# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Extract renderable region geometry from a setFieldsDict FoamNode tree.

setFieldsDict's ``regions ( boxToCell { … } … );`` list reuses topoSet's
source names and geometry keywords, but each region_entry is *named by* its
source type instead of carrying a ``source`` child, and has no topoSet
action. Geometry resolution is shared with foam/topo_set_extractor.py.
"""
from __future__ import annotations

import dataclasses

from foam.nodes import FoamNode
from foam.topo_set_extractor import is_non_geometric_source, resolve_source_geometry
from foam.tree_utils import find_child
from foam.var_resolver import build_var_map

# Keys that are structural in setFieldsDict (not variable definitions).
_SET_FIELDS_STRUCTURAL = frozenset({"regions", "defaultFieldValues"})


@dataclasses.dataclass
class SetFieldsShape:
    label: str      # summary of the entry's fieldValues, e.g. "alpha.water=1"
    source: str     # e.g. "boxToCell", "sphereToCell"
    geometry: dict  # parsed geometry: keys depend on source type


@dataclasses.dataclass
class SetFieldsData:
    shapes: list[SetFieldsShape]
    # Recognised sources that carry no renderable geometry (set/field/surface
    # references, e.g. zoneToCell, surfaceToCell). Listed in the UI but not drawn.
    non_geometric: list[SetFieldsShape] = dataclasses.field(default_factory=list)


def _field_values_label(entry: FoamNode) -> str:
    """Summarise the entry's fieldValues as "name=value, …" for UI labels."""
    fv_node = find_child(entry, "fieldValues")
    if fv_node is None or fv_node.node_type != "field_value_block":
        return ""
    parts: list[str] = []
    for item in fv_node.value or []:
        if getattr(item, "node_type", None) != "field_value":
            continue
        name = item.value.get("field_name", "")
        raw = item.value.get("raw_value", "")
        if name:
            parts.append(f"{name}={raw}" if raw else name)
    return ", ".join(parts)


def _find_region_block(root: FoamNode) -> FoamNode | None:
    for child in root.children:
        if child.node_type == "region_block":
            return child
    return None


def extract_set_fields_data(root: FoamNode) -> SetFieldsData:
    """Walk region_block → region_entry nodes and collect renderable shapes."""
    var_map = build_var_map(root, skip_keys=_SET_FIELDS_STRUCTURAL)

    region_block = _find_region_block(root)
    if region_block is None:
        return SetFieldsData(shapes=[])

    shapes: list[SetFieldsShape] = []
    non_geometric: list[SetFieldsShape] = []
    for entry in region_block.children:
        if entry.node_type != "region_entry":
            continue

        source = entry.name
        label = _field_values_label(entry)

        geometry = resolve_source_geometry(source, entry, var_map)
        if geometry:
            shapes.append(SetFieldsShape(label=label, source=source, geometry=geometry))
        elif is_non_geometric_source(source):
            non_geometric.append(
                SetFieldsShape(label=label, source=source, geometry={})
            )

    return SetFieldsData(shapes=shapes, non_geometric=non_geometric)
