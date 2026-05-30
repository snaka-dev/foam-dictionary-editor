# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations
from foam.nodes import FoamNode

_RECURSE_TYPES = frozenset({
    "dictionary",
    "boundary_block", "boundary_entry",
    "region_block", "region_entry",
    "field_value_block",
})


DiffEntry = tuple[str, "FoamNode | None"]


def diff_trees_reverse(b: FoamNode, a: FoamNode) -> dict[FoamNode, DiffEntry]:
    """Like diff_trees but annotates nodes in *b* relative to *a*.

    Used to colour the reference-case pane: nodes in *b* absent from *a* are
    ``"only_here"`` (shown green); nodes with differing values are ``"changed"``.
    """
    return diff_trees(b, a)


def diff_trees(a: FoamNode, b: FoamNode) -> dict[FoamNode, DiffEntry]:
    """Compare tree *a* against reference tree *b*.

    Returns a mapping from nodes in *a* to a ``(status, ref_node)`` pair:
    - ``("changed",   ref_node)`` – key present in both trees but value or type differs;
      *ref_node* is the matching node from *b*.
    - ``("only_here", None)``     – key present in *a* but absent in *b*.

    Only named dictionary entries are annotated; positional list items
    (vertices, blocks, …) and anonymous nodes are skipped.
    """
    result: dict[FoamNode, DiffEntry] = {}
    _diff_node(a, b, result)
    return result


def _diff_node(a: FoamNode, b: FoamNode, result: dict[FoamNode, DiffEntry]) -> None:
    if a.node_type == "field_value_block" and b.node_type == "field_value_block":
        _diff_field_value_block(a, b, result)
        return

    b_map = _by_name(b.children)
    for a_child in a.children:
        if not a_child.name:
            continue
        b_child = b_map.get(a_child.name)
        if b_child is None:
            result[a_child] = ("only_here", None)
        elif a_child.node_type in _RECURSE_TYPES and b_child.node_type in _RECURSE_TYPES:
            _diff_node(a_child, b_child, result)
        else:
            if not _equal(a_child, b_child):
                result[a_child] = ("changed", b_child)


def _diff_field_value_block(
    a: FoamNode, b: FoamNode, result: dict[FoamNode, DiffEntry]
) -> None:
    a_items = a.value if isinstance(a.value, list) else []
    b_items = b.value if isinstance(b.value, list) else []

    b_map: dict[str, FoamNode] = {}
    for c in b_items:
        if isinstance(c, FoamNode) and isinstance(c.value, dict):
            fname = c.value.get("field_name", "")
            if fname and fname not in b_map:
                b_map[fname] = c

    for a_child in a_items:
        if not isinstance(a_child, FoamNode) or not isinstance(a_child.value, dict):
            continue
        fname = a_child.value.get("field_name", "")
        b_child = b_map.get(fname)
        if b_child is None:
            result[a_child] = ("only_here", None)
        elif a_child.value != b_child.value:
            result[a_child] = ("changed", b_child)


def _by_name(children: list[FoamNode]) -> dict[str, FoamNode]:
    seen: dict[str, FoamNode] = {}
    for c in children:
        if c.name and c.name not in seen:
            seen[c.name] = c
    return seen


def _equal(a: FoamNode, b: FoamNode) -> bool:
    return a.node_type == b.node_type and a.value == b.value
