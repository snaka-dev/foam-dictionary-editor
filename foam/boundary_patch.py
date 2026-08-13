# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Qt-free FoamNode operations for boundary patches.

Shared by ui/dialogs/boundary_edit_dialog.py, ui/dialogs/rename_boundary_dialog.py,
ui/panels/boundary_view_panel.py, and ui/mixins/_boundary_ops.py. See DEVELOPER.md's
foam/ structure list.
"""
from __future__ import annotations

from foam.nodes import FoamNode
from foam.parser import OpenFoamParser
from foam.writer import write_root

# Thresholds for deciding whether a patch value is too large/complex
# to display in the edit dialog — edit in Text Editor instead.
_COMPLEX_VALUE_CHAR_LIMIT = 500
_COMPLEX_VALUE_LINE_LIMIT = 12


def value_complexity(patch_node: FoamNode) -> str:
    """Return 'binary', 'large', or '' (not complex).

    'binary' takes priority: non-printable bytes are detected before size checks.
    """
    for child in patch_node.children:
        if child.node_type == "field_value_block":
            return "large"
        raw = child.raw_text or ""
        if any(c < "\x09" for c in raw[:_COMPLEX_VALUE_CHAR_LIMIT]):
            return "binary"
        if len(raw) > _COMPLEX_VALUE_CHAR_LIMIT or raw.count("\n") > _COMPLEX_VALUE_LINE_LIMIT:
            return "large"
    return ""


def get_patch_type(patch_node: FoamNode) -> str:
    for child in patch_node.children:
        if child.name == "type":
            return str(child.value) if child.value is not None else ""
    return ""


def patch_inner_text(patch_node: FoamNode) -> str:
    """Return the content inside the patch dict braces, preserving indentation."""
    rt = patch_node.raw_text.strip() if patch_node.raw_text else ""
    if rt:
        start = rt.find("{")
        end = rt.rfind("}")
        if start != -1 and end > start:
            return rt[start + 1 : end].strip("\n")
    # Fallback: serialise children via write_root on a temporary root
    temp = FoamNode(name="_tmp", node_type="dictionary")
    temp.children = list(patch_node.children)
    return write_root(temp).strip()


def parse_patch_content(text: str) -> list[FoamNode]:
    """Parse inner patch text and return the list of child FoamNodes."""
    wrapped = f"_patch\n{{\n{text}\n}}\n"
    root = OpenFoamParser(wrapped).parse()
    for child in root.children:
        if child.name == "_patch" and child.node_type == "dictionary":
            result = list(child.children)
            for c in result:
                c.parent = None  # caller sets parent
            return result
    return []


def find_rename_targets(name: str, roots: dict[str, FoamNode]) -> dict[str, list[FoamNode]]:
    """Return {path: [nodes]} for boundary nodes whose name matches across all roots."""
    result: dict[str, list[FoamNode]] = {}
    for path, root in roots.items():
        hits = _collect(root, name)
        if hits:
            result[path] = hits
    return result


def _collect(node: FoamNode, name: str) -> list[FoamNode]:
    hits = []
    if node.name == name and _is_boundary_node(node):
        hits.append(node)
    for child in node.children:
        hits.extend(_collect(child, name))
    return hits


def _is_boundary_node(node: FoamNode) -> bool:
    if node.node_type == "boundary_entry":
        return True
    # Patch key inside a boundaryField dictionary (field files like 0/U)
    if node.node_type == "dictionary" and node.parent is not None:
        return node.parent.name == "boundaryField"
    return False
