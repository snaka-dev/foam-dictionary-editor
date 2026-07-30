# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

# The definitive list of node_type values the parser/writer/model recognise.
# This Literal is the single source of truth — mypy flags any code that
# assigns or compares against a value not listed here. See DEVELOPER.md's
# "Node types" section for what each value means and when it's produced.
NodeType = Literal[
    # Leaf value types
    "int", "scalar", "bool", "word", "string", "macro", "compound",
    "vector", "int_list", "scalar_list", "raw_list", "box_pair", "nonuniform_list",
    # Structural types
    "dictionary", "field_value_block", "field_value", "region_block", "region_entry",
    "boundary_block", "boundary_entry", "action_list", "action_entry",
    "named_dict_list", "named_dict_entry",
    "block_list", "block_entry",
    "directive_entry", "macro_entry", "unknown_raw_entry",
]

# Node types where the key column is not editable.
NON_KEY_EDITABLE = frozenset({
    "field_value", "macro_entry", "directive_entry", "unknown_raw_entry", "block_entry",
})

# Node types whose value is a plain string (word/macro/compound/string).
STRING_TYPES = frozenset({"compound", "macro", "string", "word"})

# Lowercase token strings that classify as bool node_type.
BOOL_WORDS = frozenset({"true", "false", "on", "off", "yes", "no"})


@dataclass
class FoamNode:
    name: str
    node_type: NodeType
    # Runtime type depends on node_type (str/int/float/list/dict/None).
    # Dispatch is on node_type, not on value's Python type, so a
    # discriminated union isn't modeled here.
    value: Any = None
    children: list[FoamNode] = field(default_factory=list)
    parent: FoamNode | None = field(default=None, repr=False)

    modified: bool = False

    leading_trivia: list[str] = field(default_factory=list)
    # Only ever set on the root node: the whitespace and comments left over
    # after the last entry (typically OpenFOAM's "// ****" footer banner).
    # Every other node's trailing whitespace is the *next* node's
    # leading_trivia -- see DEVELOPER.md's "Trivia ownership" section.
    trailing_trivia: list[str] = field(default_factory=list)
    inline_comment: str = ""
    raw_text: str = ""

    # 1-based line numbers in the original source (0 = unknown / not yet set).
    source_line: int = 0
    source_end_line: int = 0

    # Use object identity for hashing so FoamNode can be a dict key.
    __hash__ = object.__hash__

    def add_child(self, child: FoamNode) -> None:
        child.parent = self
        self.children.append(child)
