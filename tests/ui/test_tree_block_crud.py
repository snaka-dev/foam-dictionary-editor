# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Add/Duplicate/Delete on blockMeshDict block rows (ui/mixins/_tree_crud_ops.py).

`blocks ( … )` shows one row per block, and those rows are positional and
anonymous -- their "block N" key comes from the row index. CRUD is enabled on
them anyway, because deleting a block is what a user reaches for once the
blocks are individually visible. Comment Out is not: a commented-out block
inside the parentheses reparses as trivia, so the row would vanish.
"""
from __future__ import annotations

from PySide6.QtWidgets import QApplication, QMessageBox

from foam.parser import OpenFoamParser
from foam.writer import write_root
from ui.mixins._tree_crud_ops import _delete_label, _new_sibling_for

_BLOCK_MESH_DICT = """\
scale   1;

vertices
(
    (0 0 0)
    (1 0 0)
);

blocks
(
    hex (0 1 2 3 4 5 6 7) (10 10 10) simpleGrading (1 1 1)
    hex (1 8 9 2 5 10 11 6) (20 10 10) simpleGrading (1 1 1)
    hex (8 12 13 9 10 14 15 11) (30 10 10) simpleGrading (2 1 1)
);
"""


def _blocks_of(text):
    root = OpenFoamParser(text).parse()
    blocks = next(c for c in root.children if c.name == "blocks")
    assert blocks.node_type == "block_list"
    return root, blocks


class TestNewSibling:
    def test_block_list_parent_gets_a_block_entry(self):
        _, blocks = _blocks_of(_BLOCK_MESH_DICT)
        new_node = _new_sibling_for(blocks)

        assert new_node.node_type == "block_entry"
        assert new_node.modified is True
        assert new_node.name == ""

    def test_default_block_is_valid_syntax(self):
        """The inserted text has to parse back as a block, not a placeholder."""
        _, blocks = _blocks_of(_BLOCK_MESH_DICT)
        text = f"blocks\n(\n    {_new_sibling_for(blocks).value}\n);\n"

        _, reparsed = _blocks_of(text)
        assert len(reparsed.children) == 1
        assert reparsed.children[0].node_type == "block_entry"

    def test_dictionary_parent_still_gets_a_word_entry(self):
        root, _ = _blocks_of(_BLOCK_MESH_DICT)
        new_node = _new_sibling_for(root)

        assert (new_node.node_type, new_node.name, new_node.value) == (
            "word", "newKey", "newValue",
        )


class TestDeleteLabel:
    def test_block_entry_is_named_by_position(self):
        """A block has no name, so the dialog must not ask "Delete ''?"."""
        _, blocks = _blocks_of(_BLOCK_MESH_DICT)

        assert _delete_label(blocks.children[1]) == "block 1"

    def test_named_node_keeps_its_name(self):
        root, _ = _blocks_of(_BLOCK_MESH_DICT)
        scale = next(c for c in root.children if c.name == "scale")

        assert _delete_label(scale) == "scale"


class TestWriteAfterBlockCrud:
    """The tree mutation is only useful if the file it produces is right."""

    def test_deleting_a_block_leaves_the_others_untouched(self):
        root, blocks = _blocks_of(_BLOCK_MESH_DICT)
        removed = blocks.children.pop(1)
        blocks.modified = True

        out = write_root(root)

        assert removed.raw_text not in out
        assert out.count("hex ") == 2
        assert "hex (0 1 2 3 4 5 6 7) (10 10 10) simpleGrading (1 1 1)" in out
        assert "hex (8 12 13 9 10 14 15 11) (30 10 10) simpleGrading (2 1 1)" in out
        # the list still closes on its own line
        assert "\n);\n" in out

    def test_added_block_lands_on_its_own_indented_line(self):
        root, blocks = _blocks_of(_BLOCK_MESH_DICT)
        new_node = _new_sibling_for(blocks)
        new_node.parent = blocks
        blocks.children.insert(3, new_node)

        out = write_root(root)

        assert f"    {new_node.value}\n);" in out
        assert out.count("hex ") == 4

    def test_block_crud_through_the_window_is_undoable(
        self, main_window, tmp_path, monkeypatch,
    ):
        """End to end: delete a block, the editor text follows, Ctrl+Z brings it back."""
        win = main_window
        (tmp_path / "system").mkdir()
        path = tmp_path / "system" / "blockMeshDict"
        path.write_text(_BLOCK_MESH_DICT, encoding="utf-8")
        win._load_case_dir(str(tmp_path))
        win.load_selected_file(str(path))

        blocks = next(c for c in win.state.current_root.children if c.name == "blocks")
        assert len(blocks.children) == 3

        monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
        win._tree_delete(blocks.children[1])
        QApplication.processEvents()

        blocks = next(c for c in win.state.current_root.children if c.name == "blocks")
        assert len(blocks.children) == 2
        assert "hex (1 8 9 2 5 10 11 6)" not in win.editor_panel.get_text()

        win._tree_undo()

        blocks = next(c for c in win.state.current_root.children if c.name == "blocks")
        assert len(blocks.children) == 3
        assert "hex (1 8 9 2 5 10 11 6)" in win.editor_panel.get_text()

    def test_deleting_a_block_renumbers_the_rest_by_position(self):
        """The tree key is the row index, so the file order is the numbering."""
        root, blocks = _blocks_of(_BLOCK_MESH_DICT)
        blocks.children.pop(0)
        blocks.modified = True

        _, reparsed = _blocks_of(write_root(root))
        assert [c.value.split(")")[0] + ")" for c in reparsed.children] == [
            "hex (1 8 9 2 5 10 11 6)",
            "hex (8 12 13 9 10 14 15 11)",
        ]
