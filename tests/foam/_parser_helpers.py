# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Shared helpers for the `test_parser_*.py` grammar tests.

`find_child` was copy-pasted, identically, into four of them (once under the name
`child_by_name`). A module rather than a conftest fixture: the helper is called 65 times
across about 30 tests, so a fixture would add a parameter to every one of those signatures
to remove fifteen lines of duplication. pytest puts a test file's own directory on
`sys.path` (the default `prepend` import mode, with no `__init__.py` in the way), which is
what makes the flat import below resolve.
"""


def find_child(node, name):
    """The direct child of *node* called *name*, or an assertion failure naming it."""
    for child in node.children:
        if child.name == name:
            return child
    raise AssertionError(f"child not found: {name}")
