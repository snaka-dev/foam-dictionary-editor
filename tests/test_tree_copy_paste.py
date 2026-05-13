# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""
Tests for the copy-paste workflow on the tree view Value column.

The UI layer (context menu, keyboard shortcuts, clipboard) is not covered here.
These tests verify the model-level operations that back the feature:
  - reading the display value that "Copy Value" would put on the clipboard
  - writing a pasted string back via setData (same path as "Paste Value")
  - round-trip: paste the copied value back to the same node
  - cross-node paste: copy from one node, paste to another of the same type
  - guard: setData rejects pasting to non-editable nodes (dictionary entries)
  - guard: setData rejects badly-formatted values
"""
from __future__ import annotations

import pytest
from PySide6.QtCore import Qt

from foam.parser import OpenFoamParser
from model.tree_model import FoamTreeModel


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_model(text: str) -> tuple[FoamTreeModel, object]:
    root = OpenFoamParser(text).parse()
    return FoamTreeModel(root), root


def _find_row(root, name: str) -> int:
    for i, child in enumerate(root.children):
        if child.name == name:
            return i
    raise KeyError(name)


# ── copy: display value is copyable text ─────────────────────────────────────

class TestCopyValue:
    def test_copy_word_value(self, control_dict_text):
        """Display value for a word node matches the text that Copy Value would place on the clipboard"""
        model, root = _make_model(control_dict_text)
        row = _find_row(root, "application")
        val = model.data(model.index(row, FoamTreeModel.COL_VALUE), Qt.DisplayRole)
        assert val == "interFoam"

    def test_copy_scalar_value(self, control_dict_text):
        """Display value for a scalar node is a numeric string"""
        model, root = _make_model(control_dict_text)
        row = _find_row(root, "deltaT")
        val = model.data(model.index(row, FoamTreeModel.COL_VALUE), Qt.DisplayRole)
        assert "0.005" in val

    def test_copy_int_value(self, control_dict_text):
        """Display value for an int node is an integer string"""
        model, root = _make_model(control_dict_text)
        row = _find_row(root, "writeInterval")
        val = model.data(model.index(row, FoamTreeModel.COL_VALUE), Qt.DisplayRole)
        assert val == "20"

    def test_copy_dictionary_value_shows_entry_count(self, control_dict_text):
        """Display value for a dictionary node returns an entry-count summary (copyable but not editable)"""
        model, root = _make_model(control_dict_text)
        row = _find_row(root, "FoamFile")
        val = model.data(model.index(row, FoamTreeModel.COL_VALUE), Qt.DisplayRole)
        assert "entries" in val

    def test_copy_vector_value(self):
        """Display value for a vector node is a parenthesized (x y z) string"""
        text = "U ( 1.0 0.0 0.0 );"
        model, root = _make_model(text)
        row = _find_row(root, "U")
        val = model.data(model.index(row, FoamTreeModel.COL_VALUE), Qt.DisplayRole)
        # format_scalar omits the decimal part when zero, so (1.0 0.0 0.0) is displayed as (1 0 0)
        assert val.startswith("(") and val.endswith(")")
        assert "1" in val


# ── paste: setData accepts valid values ───────────────────────────────────────

class TestPasteValue:
    def test_paste_word_value(self, control_dict_text):
        """A string can be written to a word node via setData (equivalent to Paste Value)"""
        model, root = _make_model(control_dict_text)
        row = _find_row(root, "application")
        idx = model.index(row, FoamTreeModel.COL_VALUE)
        ok = model.setData(idx, "simpleFoam", Qt.EditRole)
        assert ok is True
        assert root.children[row].value == "simpleFoam"
        assert root.children[row].modified is True

    def test_paste_scalar_value(self, control_dict_text):
        """A numeric string can be written to a scalar node via setData"""
        model, root = _make_model(control_dict_text)
        row = _find_row(root, "deltaT")
        idx = model.index(row, FoamTreeModel.COL_VALUE)
        ok = model.setData(idx, "0.001", Qt.EditRole)
        assert ok is True
        assert abs(root.children[row].value - 0.001) < 1e-9

    def test_paste_int_value(self, control_dict_text):
        """An integer string can be written to an int node via setData"""
        model, root = _make_model(control_dict_text)
        row = _find_row(root, "writeInterval")
        idx = model.index(row, FoamTreeModel.COL_VALUE)
        ok = model.setData(idx, "50", Qt.EditRole)
        assert ok is True
        assert root.children[row].value == 50

    def test_paste_vector_value(self):
        """A (x y z) string can be written to a vector node via setData"""
        text = "U ( 1.0 0.0 0.0 );"
        model, root = _make_model(text)
        row = _find_row(root, "U")
        idx = model.index(row, FoamTreeModel.COL_VALUE)
        ok = model.setData(idx, "( 2.0 3.0 4.0 )", Qt.EditRole)
        assert ok is True
        assert root.children[row].value == pytest.approx([2.0, 3.0, 4.0])


# ── round-trip: copy then paste back ─────────────────────────────────────────

class TestRoundTrip:
    def test_roundtrip_word_value(self, control_dict_text):
        """Pasting a copied value back to the same word node preserves the value"""
        model, root = _make_model(control_dict_text)
        row = _find_row(root, "application")
        idx = model.index(row, FoamTreeModel.COL_VALUE)

        copied = model.data(idx, Qt.DisplayRole)
        ok = model.setData(idx, copied, Qt.EditRole)

        assert ok is True
        assert root.children[row].value == "interFoam"

    def test_roundtrip_scalar_value(self, control_dict_text):
        """Pasting a copied value back to the same scalar node preserves the value"""
        model, root = _make_model(control_dict_text)
        row = _find_row(root, "deltaT")
        idx = model.index(row, FoamTreeModel.COL_VALUE)

        copied = model.data(idx, Qt.DisplayRole)
        ok = model.setData(idx, copied, Qt.EditRole)

        assert ok is True
        assert abs(root.children[row].value - 0.005) < 1e-9

    def test_roundtrip_int_value(self, control_dict_text):
        """Pasting a copied value back to the same int node preserves the value"""
        model, root = _make_model(control_dict_text)
        row = _find_row(root, "writeInterval")
        idx = model.index(row, FoamTreeModel.COL_VALUE)

        copied = model.data(idx, Qt.DisplayRole)
        ok = model.setData(idx, copied, Qt.EditRole)

        assert ok is True
        assert root.children[row].value == 20


# ── cross-node paste ──────────────────────────────────────────────────────────

class TestCrossNodePaste:
    def test_paste_word_to_another_word_node(self, control_dict_text):
        """A word value can be pasted from one node to another word node"""
        model, root = _make_model(control_dict_text)
        src_row = _find_row(root, "application")
        dst_row = _find_row(root, "startFrom")

        copied = model.data(model.index(src_row, FoamTreeModel.COL_VALUE), Qt.DisplayRole)
        ok = model.setData(model.index(dst_row, FoamTreeModel.COL_VALUE), copied, Qt.EditRole)

        assert ok is True
        assert root.children[dst_row].value == "interFoam"

    def test_paste_int_to_another_int_node(self, control_dict_text):
        """An int value can be pasted from one node to another int node"""
        model, root = _make_model(control_dict_text)
        src_row = _find_row(root, "writeInterval")
        dst_row = _find_row(root, "writePrecision")

        copied = model.data(model.index(src_row, FoamTreeModel.COL_VALUE), Qt.DisplayRole)
        ok = model.setData(model.index(dst_row, FoamTreeModel.COL_VALUE), copied, Qt.EditRole)

        assert ok is True
        assert root.children[dst_row].value == 20


# ── guard: paste to non-editable node ────────────────────────────────────────

class TestPasteGuards:
    def test_paste_to_dictionary_node_is_rejected(self, control_dict_text):
        """setData returns False for the Value column of a dictionary node"""
        model, root = _make_model(control_dict_text)
        row = _find_row(root, "FoamFile")
        idx = model.index(row, FoamTreeModel.COL_VALUE)

        ok = model.setData(idx, "anything", Qt.EditRole)
        assert ok is False

    def test_paste_invalid_scalar_rejected(self, control_dict_text):
        """setData returns False when a non-numeric string is pasted to a scalar node"""
        model, root = _make_model(control_dict_text)
        row = _find_row(root, "deltaT")
        idx = model.index(row, FoamTreeModel.COL_VALUE)

        ok = model.setData(idx, "notanumber", Qt.EditRole)
        assert ok is False

    def test_paste_float_to_int_promotes_to_scalar(self, control_dict_text):
        """Pasting a float into an int node promotes the node type to scalar."""
        model, root = _make_model(control_dict_text)
        row = _find_row(root, "writeInterval")
        idx = model.index(row, FoamTreeModel.COL_VALUE)

        ok = model.setData(idx, "3.14", Qt.EditRole)
        assert ok is True
        assert root.children[row].node_type == "scalar"

    def test_paste_non_numeric_to_int_rejected(self, control_dict_text):
        """setData returns False when a non-numeric string is pasted to an int node."""
        model, root = _make_model(control_dict_text)
        row = _find_row(root, "writeInterval")
        idx = model.index(row, FoamTreeModel.COL_VALUE)

        ok = model.setData(idx, "notanumber", Qt.EditRole)
        assert ok is False

    def test_paste_invalid_vector_rejected(self):
        """setData returns False when a vector with fewer than 3 elements is pasted"""
        text = "U ( 1.0 0.0 0.0 );"
        model, root = _make_model(text)
        row = _find_row(root, "U")
        idx = model.index(row, FoamTreeModel.COL_VALUE)

        ok = model.setData(idx, "( 1.0 0.0 )", Qt.EditRole)
        assert ok is False

    def test_editable_flag_absent_for_dictionary_value(self, control_dict_text):
        """ItemIsEditable flag is absent for a dictionary node Value column (Paste Value can be disabled)"""
        model, root = _make_model(control_dict_text)
        row = _find_row(root, "FoamFile")
        idx = model.index(row, FoamTreeModel.COL_VALUE)

        assert not (model.flags(idx) & Qt.ItemIsEditable)

    def test_editable_flag_present_for_word_value(self, control_dict_text):
        """ItemIsEditable flag is present for a word node Value column (Paste Value can be enabled)"""
        model, root = _make_model(control_dict_text)
        row = _find_row(root, "application")
        idx = model.index(row, FoamTreeModel.COL_VALUE)

        assert model.flags(idx) & Qt.ItemIsEditable
