# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations
import re
from foam.utils import format_embedded_value, format_scalar
from foam.nodes import FoamNode, STRING_TYPES


MAX_CONSECUTIVE_NEWLINES = 3


def write_node(node: FoamNode, indent: int = 0) -> str:
    return _write_node(node, indent)


def write_root(root: FoamNode) -> str:
    parts = []
    for child in root.children:
        chunk = _write_node(child, indent=0)
        if not chunk.endswith("\n"):
            chunk += "\n"
        parts.append(chunk)
    result = "".join(parts)
    result = re.sub(rf'\n{{{MAX_CONSECUTIVE_NEWLINES},}}', '\n\n', result)
    return result


def _write_node(node: FoamNode, indent: int = 0) -> str:
    if not node.modified and node.raw_text and not _has_modified_descendant(node):
        return _with_leading_trivia(node, node.raw_text)

    if node.node_type in {"dictionary", "region_entry"}:
        return _with_leading_trivia(node, _write_dictionary(node, indent))

    if node.node_type == "region_block":
        return _with_leading_trivia(node, _write_region_block(node, indent))

    if node.node_type == "field_value_block":
        return _with_leading_trivia(node, _write_field_value_block(node, indent))

    if node.node_type in {"directive_entry", "unknown_raw_entry"}:
        return _write_inline_entry(node, indent)

    if node.node_type == "macro_entry":
        return _write_inline_entry(node, indent, ";")

    return _with_leading_trivia(node, _write_simple_entry(node, indent))


def _write_dictionary(node: FoamNode, indent: int = 0) -> str:
    lines = [f"{_indent(indent)}{node.name}\n", f"{_indent(indent)}{{\n"]
    for child in node.children:
        chunk = _write_node(child, indent + 1)
        if not chunk.endswith("\n"):
            chunk += "\n"
        lines.append(chunk)
    lines.append(f"{_indent(indent)}}}\n")
    return "".join(lines)


def _write_region_block(node: FoamNode, indent: int = 0) -> str:
    lines = [f"{_indent(indent)}{node.name}\n", f"{_indent(indent)}(\n"]
    for child in node.children:
        lines.append(_write_node(child, indent + 1))
    lines.append(f"{_indent(indent)});\n")
    return "".join(lines)


def _write_field_value_block(node: FoamNode, indent: int = 0) -> str:
    lines = [f"{_indent(indent)}{node.name}\n", f"{_indent(indent)}(\n"]

    for item in (node.value or []):   # ← None guard
        if isinstance(item, FoamNode) and item.node_type == "field_value":
            lines.append(_write_field_value_item(item, indent + 1))
        else:
            lines.append(f"{_indent(indent + 1)}{_format_field_value_dict(item)}\n")

    lines.append(f"{_indent(indent)});\n")
    return "".join(lines)


def _write_field_value_item(node: FoamNode, indent: int = 0) -> str:
    return f"{_indent(indent)}{_format_field_value_dict(node.value)}\n"


def _write_inline_entry(node: FoamNode, indent: int, suffix: str = "") -> str:
    line = f"{_indent(indent)}{node.value}{suffix}"
    if node.inline_comment:
        line += node.inline_comment
    if not line.endswith("\n"):
        line += "\n"
    return _with_leading_trivia(node, line)


def _write_simple_entry(node: FoamNode, indent: int = 0) -> str:
    value_text = _format_value(node)
    line = f"{_indent(indent)}{node.name} {value_text};"
    if node.inline_comment:
        line += node.inline_comment
    line += "\n"
    return line


def _format_value(node: FoamNode) -> str:
    if node.node_type in {"vector", "scalar_list"}:
        return "(" + " ".join(format_scalar(x) for x in node.value) + ")"

    if node.node_type == "box_pair":
        p1, p2 = node.value
        return (
            "(" + " ".join(format_scalar(x) for x in p1) + ") "
            "(" + " ".join(format_scalar(x) for x in p2) + ")"
        )

    if node.node_type in {"int_list", "list"}:
        return "(" + " ".join(str(x) for x in node.value) + ")"

    if node.node_type == "raw_list":
        return "(" + str(node.value) + ")"

    if node.node_type == "field_value":
        return _format_field_value_dict(node.value)

    if node.node_type in STRING_TYPES:
        return str(node.value)

    if node.node_type == "int":
        return str(node.value)

    if node.node_type == "scalar":
        return format_scalar(node.value)

    return "" if node.value is None else str(node.value)


def _format_field_value_dict(data: dict) -> str:
    return (
        f"{data['field_type']} "
        f"{data['field_name']} "
        f"{format_embedded_value(data['value_type'], data['value'], data['raw_value'])}"
    )

def _with_leading_trivia(node: FoamNode, text: str) -> str:
    leading = "".join(node.leading_trivia) if getattr(node, "leading_trivia", None) else ""
    leading = re.sub(r'\n{2,}$', '\n', leading)
    return leading + text


def _indent(level: int) -> str:
    return "    " * level

def _has_modified_descendant(node: FoamNode) -> bool:
    for child in node.children:
        if child.modified or _has_modified_descendant(child):
            return True
    if node.node_type == "field_value_block" and isinstance(node.value, list):
        for item in node.value:
            if isinstance(item, FoamNode) and item.modified:
                return True
    return False
