# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""The tree view's right-click menu (ui/mixins/_tree_crud_ops.py).

Built through _build_tree_context_menu, without the blocking QMenu.exec()
(see ui/menu_builder.py): which rows each kind of node gets, which are
enabled, and that each row calls the operation it names.
"""
from __future__ import annotations

import pytest

_BLOCK_MESH_DICT = """\
scale   1;

vertices
(
    (0 0 0)
);

blocks
(
    hex (0 1 2 3 4 5 6 7) (10 10 10) simpleGrading (1 1 1)
);

boundary
(
    inlet
    {
        type patch;
        faces ((0 1 2 3));
    }
);

#include "settings"
"""


@pytest.fixture
def win(main_window, tmp_path):
    (tmp_path / "system").mkdir()
    path = tmp_path / "system" / "blockMeshDict"
    path.write_text(_BLOCK_MESH_DICT, encoding="utf-8")
    main_window._load_case_dir(str(tmp_path))
    main_window.load_selected_file(str(path))
    return main_window


def _node(win, *names):
    node = win.state.current_root
    for name in names:
        node = (
            node.children[name]
            if isinstance(name, int)
            else next(c for c in node.children if c.name == name)
        )
    return node


def _menu(win, node):
    model = win.state.current_model
    index = win.proxy_model.mapFromSource(model.index_of_node(node))
    menu, actions = win._build_tree_context_menu(index)
    rows = {a.text(): a for a in menu.actions() if not a.isSeparator()}
    return rows, actions


def _enabled(rows):
    return {t for t, a in rows.items() if a.isEnabled()}


def test_plain_entry_gets_sibling_operations(win):
    rows, _ = _menu(win, _node(win, "scale"))
    assert {"Add Entry After", "Duplicate", "Comment Out", "Delete"} <= _enabled(rows)
    assert "Add Child Entry" not in _enabled(rows)
    assert "Restore from Comment" not in _enabled(rows)
    assert "Open Included File" not in rows
    assert "Rename Boundary…" not in rows


def test_block_entry_allows_crud_but_not_comment_out(win):
    rows, _ = _menu(win, _node(win, "blocks", 0))
    enabled = _enabled(rows)
    assert {"Add Entry After", "Duplicate", "Delete"} <= enabled
    assert "Comment Out" not in enabled


def test_boundary_entry_offers_rename(win):
    rows, actions = _menu(win, _node(win, "boundary", "inlet"))
    assert "Rename Boundary…" in rows


def test_directive_offers_open_included_file(win):
    directive = next(
        c for c in win.state.current_root.children if c.node_type == "directive_entry"
    )
    rows, _ = _menu(win, directive)
    # Present, but disabled: system/settings does not exist.
    assert "Open Included File" in rows
    assert not rows["Open Included File"].isEnabled()


def test_read_only_file_disables_every_mutation(win):
    win.state.read_only_files = {win.state.current_file}
    # The model takes its read-only flag when the tree is loaded, as it is for
    # an out-of-case include, which is read-only from the moment it opens.
    win._load_tree(win.state.current_root)
    rows, _ = _menu(win, _node(win, "scale"))
    assert _enabled(rows) == {"Copy Value\tCtrl+C"}


def test_rows_call_their_operation(win, monkeypatch):
    node = _node(win, "scale")
    called = []
    for name in (
        "_tree_add_entry_after",
        "_tree_duplicate",
        "_tree_comment_out",
        "_tree_delete",
    ):
        monkeypatch.setattr(win, name, lambda n, name=name: called.append((name, n)))
    monkeypatch.setattr(win, "_tree_copy_value", lambda: called.append(("copy", None)))
    rows, actions = _menu(win, node)
    for label in ("Add Entry After", "Duplicate", "Comment Out", "Delete", "Copy Value\tCtrl+C"):
        actions[rows[label]]()
    assert called == [
        ("_tree_add_entry_after", node),
        ("_tree_duplicate", node),
        ("_tree_comment_out", node),
        ("_tree_delete", node),
        ("copy", None),
    ]
