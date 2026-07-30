# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Text -> typed-value validation for editing a FoamNode's value in place.

Backs ``model/tree_model.py``'s ``FoamTreeModel.setData`` (see DEVELOPER.md):
given the string a user typed into the tree view's Value column, decide
whether it re-parses as the target node's ``node_type`` and, if so, what the
converted Python value (and possibly promoted ``node_type``) should be. Pure
Python, no Qt dependency, so it can be unit-tested without a QApplication.
"""
from __future__ import annotations

from foam.nodes import BOOL_WORDS, STRING_TYPES, FoamNode, NodeType
from foam.utils import (
    BLOCK_SHAPE_WORDS,
    classify_simple_value,
    is_int,
    is_number,
    parse_box_pair,
    split_block_entry_tokens,
    strip_block_name_prefix,
)


def parse_parenthesized_numbers(
    text: str, force_int: bool = False
) -> list[int] | list[float] | None:
    """Parse a parenthesized, whitespace-separated number list, e.g. ``"(1 2 3)"``.

    Returns ``None`` when *text* is not parenthesized, or when any element
    fails to parse as the requested numeric kind (int when *force_int* is
    True, else float). An empty ``"()"`` parses to an empty list.
    """
    text = text.strip()
    if not (text.startswith("(") and text.endswith(")")):
        return None

    body = text[1:-1].strip()
    if not body:
        return []

    parts = body.split()

    if force_int:
        if not all(is_int(x) for x in parts):
            return None
        return [int(x) for x in parts]

    if not all(is_number(x) for x in parts):
        return None

    return [float(x) for x in parts]


def parse_text_for_node_type(
    node_type: NodeType, text: str
) -> tuple[NodeType, object] | tuple[None, None]:
    """Re-parse *text* as *node_type*, returning ``(new_node_type, value)``.

    Returns ``(None, None)`` when *text* does not re-parse as *node_type*.
    An ``"int"`` node whose text parses as a float instead promotes to
    ``"scalar"`` -- the returned node_type then differs from the input; this
    is the contract ``set_node_value`` relies on to change ``node.node_type``
    on promotion.
    """
    if node_type == "int":
        try:
            return "int", int(text)
        except ValueError:
            if is_number(text):
                return "scalar", float(text)
            return None, None

    if node_type == "scalar":
        try:
            return "scalar", float(text)
        except ValueError:
            return None, None

    if node_type == "vector":
        nums = parse_parenthesized_numbers(text)
        if nums is None or len(nums) != 3:
            return None, None
        return "vector", nums

    if node_type == "box_pair":
        parsed_box = parse_box_pair(text)
        if parsed_box is None:
            return None, None
        return "box_pair", parsed_box

    if node_type == "int_list":
        nums = parse_parenthesized_numbers(text, force_int=True)
        if nums is None:
            return None, None
        return "int_list", nums

    if node_type == "scalar_list":
        nums = parse_parenthesized_numbers(text)
        if nums is None:
            return None, None
        return "scalar_list", nums

    if node_type == "raw_list":
        if text.startswith("(") and text.endswith(")"):
            return "raw_list", text[1:-1].strip()
        return "raw_list", text

    if node_type == "bool":
        if text.lower() not in BOOL_WORDS:
            return None, None
        return "bool", text.lower()

    if node_type == "block_entry":
        return _parse_block_entry_text(text)

    if node_type in STRING_TYPES:
        return node_type, text

    return None, None


def _parse_block_entry_text(text: str) -> tuple[NodeType, object] | tuple[None, None]:
    """Validate a block_entry edit: shape word, balanced parens, 8-vertex first group.

    An optional ``name <blockName>`` prefix is allowed before the shape word.
    $var/${var} pass through untouched -- a macro may stand in for the whole
    entry, its tail, or the vertex group itself, in which case the vertex
    count cannot be checked and isn't; a bare macro tail (no cells/grading
    groups) is accepted; zero cells/grading groups is accepted. Otherwise
    only the shape word and the vertex-count of the first group are checked,
    matching what foam/block_mesh_extractor.py's _parse_hex_blocks consumes.

    A comment marker is rejected: the value is written back on one line, so
    a ``//`` would comment out the rest of the block.
    """
    if text.count("(") != text.count(")"):
        return None, None

    if "//" in text or "/*" in text:
        return None, None

    _, tokens = strip_block_name_prefix(split_block_entry_tokens(text))
    if not tokens or tokens[0] not in BLOCK_SHAPE_WORDS:
        return None, None

    if tokens[0] == "hex":
        if len(tokens) < 2:
            return None, None
        group = tokens[1]
        if group.startswith("$"):
            pass  # a macro stands in for the vertex list; nothing to count
        elif not (group.startswith("(") and group.endswith(")")):
            return None, None
        elif len(group[1:-1].split()) != 8:
            return None, None

    return "block_entry", " ".join(text.split())


def set_node_value(node: FoamNode, value: object) -> bool:
    """Validate and apply a user-supplied *value* to *node*, in place.

    Mutates ``node.value``/``node.node_type``/``node.modified`` on success.
    Returns True when the value was accepted and applied, False when it was
    rejected (node left completely unchanged) -- the return value is what
    ``FoamTreeModel.setData`` uses to decide whether to emit ``dataChanged``
    or the ``edit_rejected`` signal, and it drives the undo
    about_to_change/rejection path, so it must not change for any input.

    ``field_value``/``directive_entry``/``unknown_raw_entry`` nodes always
    accept free text (there's no node_type to validate against); every other
    node_type is validated/converted via ``parse_text_for_node_type``.
    """
    text = str(value).strip()

    if node.node_type == "field_value":
        value_type, parsed = classify_simple_value(text)
        node.value["value_type"] = value_type
        node.value["value"] = parsed
        node.value["raw_value"] = text
        node.modified = True
        return True

    if node.node_type in {"directive_entry", "unknown_raw_entry"}:
        node.value = text
        node.modified = True
        return True

    new_type, parsed_value = parse_text_for_node_type(node.node_type, text)
    if new_type is None:
        return False

    node.node_type = new_type
    node.value = parsed_value
    node.modified = True
    return True
