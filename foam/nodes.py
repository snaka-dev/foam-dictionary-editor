# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations
from dataclasses import dataclass, field

# Node types where the key column is not editable.
NON_KEY_EDITABLE = frozenset({"field_value", "macro_entry", "directive_entry", "unknown_raw_entry"})

# Node types whose value is a plain string (word/macro/compound/string).
STRING_TYPES = frozenset({"compound", "macro", "string", "word"})


@dataclass
class FoamNode:
    name: str
    node_type: str
    value: object = None
    children: list[FoamNode] = field(default_factory=list)
    parent: FoamNode | None = field(default=None, repr=False)

    modified: bool = False

    leading_trivia: list[str] = field(default_factory=list)
    inline_comment: str = ""
    raw_text: str = ""

    def add_child(self, child: FoamNode) -> None:
        child.parent = self
        self.children.append(child)
