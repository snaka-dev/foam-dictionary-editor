# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
import pytest
from PySide6.QtCore import Qt
from foam.parser import OpenFoamParser
from foam.writer import write_root
from model.tree_model import FoamTreeModel


# ── bool parsing ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("token", ["true", "false", "on", "off", "yes", "no"])
def test_parser_bool_tokens(token):
    text = f"key {token};\n"
    root = OpenFoamParser(text).parse()
    node = root.children[0]
    assert node.node_type == "bool"
    assert node.value == token


def test_parser_bool_not_classified_as_word():
    root = OpenFoamParser("writeCompression off;\n").parse()
    node = root.children[0]
    assert node.node_type == "bool"
    assert node.value == "off"


def test_parser_non_bool_word_unchanged():
    root = OpenFoamParser("solver GAMG;\n").parse()
    node = root.children[0]
    assert node.node_type == "word"


def test_parser_bool_roundtrip_unmodified(control_dict_text):
    root = OpenFoamParser(control_dict_text).parse()
    out = write_root(root)
    assert "runTimeModifiable true;" in out
    assert "writeCompression off;" in out


def test_parser_bool_roundtrip_modified():
    root = OpenFoamParser("writeCompression off;\n").parse()
    node = root.children[0]
    node.value = "on"
    node.modified = True
    out = write_root(root)
    assert "writeCompression on;" in out


# ── bool tree model editing ───────────────────────────────────────────────────

def test_tree_model_bool_is_editable(control_dict_text):
    root = OpenFoamParser(control_dict_text).parse()
    model = FoamTreeModel(root)
    row = next(i for i, c in enumerate(root.children) if c.name == "writeCompression")
    idx = model.index(row, FoamTreeModel.COL_VALUE)
    assert model.flags(idx) & Qt.ItemIsEditable


def test_tree_model_bool_setdata_valid(control_dict_text):
    root = OpenFoamParser(control_dict_text).parse()
    model = FoamTreeModel(root)
    row = next(i for i, c in enumerate(root.children) if c.name == "writeCompression")
    idx = model.index(row, FoamTreeModel.COL_VALUE)
    assert model.setData(idx, "on", Qt.EditRole) is True
    assert root.children[row].value == "on"
    assert root.children[row].node_type == "bool"
    assert root.children[row].modified is True


def test_tree_model_bool_setdata_case_insensitive(control_dict_text):
    root = OpenFoamParser(control_dict_text).parse()
    model = FoamTreeModel(root)
    row = next(i for i, c in enumerate(root.children) if c.name == "writeCompression")
    idx = model.index(row, FoamTreeModel.COL_VALUE)
    assert model.setData(idx, "ON", Qt.EditRole) is True
    assert root.children[row].value == "on"


def test_tree_model_bool_setdata_invalid(control_dict_text):
    root = OpenFoamParser(control_dict_text).parse()
    model = FoamTreeModel(root)
    row = next(i for i, c in enumerate(root.children) if c.name == "writeCompression")
    idx = model.index(row, FoamTreeModel.COL_VALUE)
    assert model.setData(idx, "maybe", Qt.EditRole) is False


def test_tree_model_bool_edit_rejected_signal(control_dict_text):
    root = OpenFoamParser(control_dict_text).parse()
    model = FoamTreeModel(root)
    row = next(i for i, c in enumerate(root.children) if c.name == "writeCompression")
    idx = model.index(row, FoamTreeModel.COL_VALUE)
    rejected_messages = []
    model.edit_rejected.connect(rejected_messages.append)
    model.setData(idx, "maybe", Qt.EditRole)
    assert len(rejected_messages) == 1
    assert "bool" in rejected_messages[0]


def test_tree_model_bool_display(control_dict_text):
    root = OpenFoamParser(control_dict_text).parse()
    model = FoamTreeModel(root)
    row = next(i for i, c in enumerate(root.children) if c.name == "writeCompression")
    idx = model.index(row, FoamTreeModel.COL_VALUE)
    assert model.data(idx, Qt.DisplayRole) == "off"


# ── edit_rejected signal for other types ─────────────────────────────────────

def test_tree_model_edit_rejected_signal_scalar(control_dict_text):
    root = OpenFoamParser(control_dict_text).parse()
    model = FoamTreeModel(root)
    row = next(i for i, c in enumerate(root.children) if c.name == "deltaT")
    idx = model.index(row, FoamTreeModel.COL_VALUE)
    rejected_messages = []
    model.edit_rejected.connect(rejected_messages.append)
    model.setData(idx, "notanumber", Qt.EditRole)
    assert len(rejected_messages) == 1
    assert "scalar" in rejected_messages[0]


def test_tree_model_no_rejection_on_valid_edit(control_dict_text):
    root = OpenFoamParser(control_dict_text).parse()
    model = FoamTreeModel(root)
    row = next(i for i, c in enumerate(root.children) if c.name == "deltaT")
    idx = model.index(row, FoamTreeModel.COL_VALUE)
    rejected_messages = []
    model.edit_rejected.connect(rejected_messages.append)
    model.setData(idx, "0.01", Qt.EditRole)
    assert len(rejected_messages) == 0


# ── nonuniform_list parsing ───────────────────────────────────────────────────

def test_parser_nonuniform_list_scalar():
    text = "internalField nonuniform List<scalar> 3 ( 0.1 0.2 0.3 );\n"
    root = OpenFoamParser(text).parse()
    node = root.children[0]
    assert node.node_type == "nonuniform_list"
    assert "nonuniform" in node.value
    assert "List<scalar>" in node.value


def test_parser_nonuniform_list_vector():
    text = "internalField nonuniform List<vector> 2 ( (1 2 3) (4 5 6) );\n"
    root = OpenFoamParser(text).parse()
    node = root.children[0]
    assert node.node_type == "nonuniform_list"


def test_parser_nonuniform_list_multiline():
    text = (
        "internalField nonuniform List<scalar>\n"
        "3\n"
        "(\n"
        "0.1\n"
        "0.2\n"
        "0.3\n"
        ");\n"
    )
    root = OpenFoamParser(text).parse()
    node = root.children[0]
    assert node.node_type == "nonuniform_list"
    assert "3" in node.value


def test_parser_nonuniform_list_roundtrip():
    text = "internalField nonuniform List<scalar> 3 ( 0.1 0.2 0.3 );\n"
    root = OpenFoamParser(text).parse()
    out = write_root(root)
    assert "nonuniform List<scalar>" in out
    assert "0.1" in out


def test_tree_model_nonuniform_list_display():
    text = "internalField nonuniform List<scalar> 100 ( 0.0 );\n"
    root = OpenFoamParser(text).parse()
    model = FoamTreeModel(root)
    idx = model.index(0, FoamTreeModel.COL_VALUE)
    display = model.data(idx, Qt.DisplayRole)
    assert "nonuniform" in display
    assert "100" in display


def test_tree_model_nonuniform_list_not_editable():
    text = "internalField nonuniform List<scalar> 3 ( 0.1 0.2 0.3 );\n"
    root = OpenFoamParser(text).parse()
    model = FoamTreeModel(root)
    idx = model.index(0, FoamTreeModel.COL_VALUE)
    assert not (model.flags(idx) & Qt.ItemIsEditable)


# ── parser error collection (#7) ─────────────────────────────────────────────

def test_parser_errors_empty_for_valid_file(control_dict_text):
    parser = OpenFoamParser(control_dict_text)
    parser.parse()
    assert parser.errors == []


def test_parser_errors_collected_for_bad_entry():
    # An orphan "}" fails _parse_key (RBRACE is not a valid key token)
    # and triggers the error-collection path before falling back to unknown_raw_entry.
    text = "goodKey 1;\n} orphan_brace\ngoodKey2 2;\n"
    parser = OpenFoamParser(text)
    root = parser.parse()
    assert len(parser.errors) > 0
    assert len(root.children) >= 2


def test_parser_errors_contain_position_and_message():
    text = "key1 1;\n} orphan_brace\nkey2 2;\n"
    parser = OpenFoamParser(text)
    parser.parse()
    assert len(parser.errors) > 0
    pos, msg = parser.errors[0]
    assert isinstance(pos, int)
    assert isinstance(msg, str)
    assert len(msg) > 0


def test_parser_errors_good_entries_still_parsed():
    text = "before 42;\n} orphan\nafter 99;\n"
    parser = OpenFoamParser(text)
    root = parser.parse()
    names = [c.name for c in root.children]
    assert "before" in names
    assert "after" in names
