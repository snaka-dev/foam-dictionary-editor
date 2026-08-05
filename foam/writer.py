# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from collections.abc import Iterable

from foam.nodes import FoamNode
from foam.utils import format_embedded_value, format_leaf_value


def write_node(node: FoamNode, indent: int = 0) -> str:
    text = _write_node(node, indent)
    if text and not text.endswith("\n"):
        text += "\n"
    return text


def write_root(root: FoamNode) -> str:
    result = _join(_part(child, 0) for child in root.children)
    # The source's own trailing newline lives in trailing_trivia, so a file
    # that ended without one keeps ending without one. Nothing is appended
    # here -- write_root must not invent whitespace the user never typed.
    result += "".join(root.trailing_trivia)
    return result


def _continues_previous_line(node: FoamNode) -> bool:
    """True when *node* directly abutted the previous entry in the source.

    Nothing at all stood between them -- not even a space -- which is why the
    node has no ``leading_trivia``. The stray ``;`` that some dictionaries
    close with (``divSchemes { … };``) is the case that matters: it is its own
    entry, and breaking the line before it would move it off the ``}``.

    A node added in the tree carries no trivia either. The two are told apart
    by ``source_line``, which only a parsed node has.
    """
    return node.source_line > 0 and not node.leading_trivia


def _own_indent(node: FoamNode, indent: int) -> str:
    """The indentation that belongs before *node*'s own first line.

    Nothing, when ``leading_trivia`` already ends in whitespace: that trivia is
    the source's own indentation and ``_with_leading_trivia`` reproduces it
    verbatim, so adding ``_indent`` on top would indent the line twice. Nothing
    either when the node continues the previous line, where any indent is wrong.

    Otherwise the generated indent -- which is the case for nodes added in the
    tree, and for entries the source wrote flush against the left margin.
    """
    if _continues_previous_line(node):
        return ""
    leading = node.leading_trivia
    if leading and leading[-1] and leading[-1][-1] in " \t":
        return ""
    return _indent(indent)


def _part(node: FoamNode, indent: int) -> tuple[str, bool]:
    """Render *node* as a part for ``_join``.

    The flag says the part separates itself from whatever precedes it. That is
    true when the node carries ``leading_trivia`` -- the original inter-entry
    whitespace already spaces it correctly, whether that means a blank line or
    the single space in ``x1 14; x2 6;`` -- and equally true when a parsed node
    carries none, because the source put it flush against its predecessor.
    """
    return _write_node(node, indent), (
        bool(node.leading_trivia) or _continues_previous_line(node)
    )


def _join(parts: Iterable[tuple[str, bool]]) -> str:
    """Concatenate rendered parts, breaking the line only where needed.

    Every ``_write_*`` helper renders a node up to its last *content*
    character; the newline that ends that line belongs to whatever comes next
    (a sibling's ``leading_trivia``, or the enclosing block's closing brace).
    Preserving that ownership is what makes an unmodified tree round-trip
    byte-identically -- see DEVELOPER.md's "Trivia ownership" section.

    The inserted break is the fallback for parts that carry no trivia: nodes
    added in the tree, and the writer's own synthetic braces and headers.
    """
    out: list[str] = []
    for text, self_separating in parts:
        if not text:
            continue
        if out and not self_separating and not out[-1].endswith("\n"):
            out.append("\n")
        out.append(text)
    return "".join(out)


def _write_node(node: FoamNode, indent: int = 0) -> str:
    if not node.modified and node.raw_text and not _has_modified_descendant(node):
        return _with_leading_trivia(node, node.raw_text)

    if node.node_type in {"dictionary", "region_entry", "boundary_entry", "named_dict_entry"}:
        return _with_leading_trivia(node, _write_dictionary(node, indent))

    if node.node_type in {
        "region_block", "boundary_block", "action_list", "named_dict_list", "block_list",
    }:
        return _with_leading_trivia(node, _write_region_block(node, indent))

    if node.node_type == "action_entry":
        return _with_leading_trivia(node, _write_action_entry(node, indent))

    if node.node_type == "field_value_block":
        return _with_leading_trivia(node, _write_field_value_block(node, indent))

    if node.node_type in {"directive_entry", "unknown_raw_entry"}:
        return _write_inline_entry(node, indent)

    if node.node_type == "macro_entry":
        return _write_inline_entry(node, indent, _macro_suffix(node))

    if node.node_type == "block_entry":
        return _write_block_entry(node, indent)

    return _with_leading_trivia(node, _write_simple_entry(node, indent))


def _write_dictionary(node: FoamNode, indent: int = 0) -> str:
    return _write_block(node, indent, node.name, "{", "}")


def _write_region_block(node: FoamNode, indent: int = 0) -> str:
    return _write_block(node, indent, node.name, "(", ");")


def _write_action_entry(node: FoamNode, indent: int = 0) -> str:
    return _write_block(node, indent, None, "{", "}")


def _write_block(
    node: FoamNode, indent: int, name: str | None, opener: str, closer: str,
) -> str:
    # Only the node's *first* line takes _own_indent -- the opener and closer
    # the writer generates below it always take the generated indent.
    parts: list[tuple[str, bool]] = []
    if name is None:
        # Anonymous block (action_entry): the opener is the node's first line.
        parts.append((f"{_own_indent(node, indent)}{opener}", False))
    else:
        # A comment written between the key and the opening brace stays on the
        # key's line, which is where the source had it.
        head = f"{_own_indent(node, indent)}{name}"
        if node.inline_comment:
            head += node.inline_comment
        parts.append((head, False))
        parts.append((f"{_indent(indent)}{opener}", False))
    parts.extend(_part(child, indent + 1) for child in node.children)
    parts.append((f"{_indent(indent)}{closer}", False))
    return _join(parts)


def _write_field_value_block(node: FoamNode, indent: int = 0) -> str:
    parts: list[tuple[str, bool]] = [
        (f"{_own_indent(node, indent)}{node.name}", False), (f"{_indent(indent)}(", False),
    ]

    for item in (node.value or []):   # ← None guard
        if isinstance(item, FoamNode) and item.node_type == "field_value":
            parts.append((_write_field_value_item(item, indent + 1), False))
        else:
            parts.append((f"{_indent(indent + 1)}{_format_field_value_dict(item)}", False))

    parts.append((f"{_indent(indent)});", False))
    return _join(parts)


def _write_field_value_item(node: FoamNode, indent: int = 0) -> str:
    return f"{_indent(indent)}{_format_field_value_dict(node.value)}"


def _macro_suffix(node: FoamNode) -> str:
    """`";"` unless the source wrote a bare `$macro` with no terminator.

    OpenFOAM accepts both `$macro;` and a bare `$macro` as a complete statement
    (`maxX { $minX }`), so regenerating an edited entry must not add a `;` the
    file never had. A node with no `raw_text` was built by the app rather than
    parsed, and takes the usual terminated form.
    """
    if not node.raw_text:
        return ";"
    # raw_text ends with the inline comment, which _finalize_node collects
    # before capturing it; strip that off to see the entry's own terminator.
    core = node.raw_text
    if node.inline_comment and core.endswith(node.inline_comment):
        core = core[: len(core) - len(node.inline_comment)]
    return ";" if core.rstrip().endswith(";") else ""


def _write_inline_entry(node: FoamNode, indent: int, suffix: str = "") -> str:
    line = f"{_own_indent(node, indent)}{node.value}{suffix}"
    if node.inline_comment:
        line += node.inline_comment
    return _with_leading_trivia(node, line)


def _write_block_entry(node: FoamNode, indent: int = 0) -> str:
    line = f"{_own_indent(node, indent)}{node.value}"
    if node.inline_comment:
        line += node.inline_comment
    return _with_leading_trivia(node, line)


def _write_simple_entry(node: FoamNode, indent: int = 0) -> str:
    if node.node_type == "valueless":
        # `p;` -- no value, and so no separating space either.
        line = f"{_own_indent(node, indent)}{node.name};"
    else:
        line = f"{_own_indent(node, indent)}{node.name} {_format_value(node)};"
    if node.inline_comment:
        line += node.inline_comment
    return line


def _format_value(node: FoamNode) -> str:
    if node.node_type == "field_value":
        return _format_field_value_dict(node.value)
    return format_leaf_value(node.node_type, node.value)


def _format_field_value_dict(data: dict) -> str:
    return (
        f"{data['field_type']} "
        f"{data['field_name']} "
        f"{format_embedded_value(data['value_type'], data['value'], data['raw_value'])}"
    )

def _with_leading_trivia(node: FoamNode, text: str) -> str:
    leading = "".join(node.leading_trivia) if getattr(node, "leading_trivia", None) else ""
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
