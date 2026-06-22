# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from PySide6.QtCore import Qt
from foam.parser import OpenFoamParser
from model.tree_model import FoamTreeModel


def test_tree_model_basic(control_dict_text):
    root = OpenFoamParser(control_dict_text).parse()
    model = FoamTreeModel(root)

    assert model.columnCount() == 3
    assert model.rowCount() > 0

    index0 = model.index(0, 0)
    assert index0.isValid()


def test_tree_model_edit_scalar(control_dict_text):
    root = OpenFoamParser(control_dict_text).parse()
    model = FoamTreeModel(root)

    target_row = None
    for row, child in enumerate(root.children):
        if child.name == "deltaT":
            target_row = row
            break

    assert target_row is not None

    value_index = model.index(target_row, 2)
    assert model.data(value_index, Qt.DisplayRole) == "0.005"

    ok = model.setData(value_index, "0.01", Qt.EditRole)
    assert ok is True
    assert root.children[target_row].value == 0.01
    assert root.children[target_row].modified is True


def test_tree_model_header_data(control_dict_text):
    """headerData returns Key, Type, and Value column headers"""
    root = OpenFoamParser(control_dict_text).parse()
    model = FoamTreeModel(root)

    assert model.headerData(0, Qt.Horizontal, Qt.DisplayRole) == "Key"
    assert model.headerData(1, Qt.Horizontal, Qt.DisplayRole) == "Type"
    assert model.headerData(2, Qt.Horizontal, Qt.DisplayRole) == "Value"
    # vertical header returns None
    assert model.headerData(0, Qt.Vertical, Qt.DisplayRole) is None


def test_tree_model_column_count(control_dict_text):
    """columnCount always returns 3"""
    root = OpenFoamParser(control_dict_text).parse()
    model = FoamTreeModel(root)

    assert model.columnCount() == 3
    index0 = model.index(0, 0)
    assert model.columnCount(index0) == 3


def test_tree_model_key_column(control_dict_text):
    """Column 0 (Key) returns the node name"""
    root = OpenFoamParser(control_dict_text).parse()
    model = FoamTreeModel(root)

    target_row = None
    for row, child in enumerate(root.children):
        if child.name == "application":
            target_row = row
            break
    assert target_row is not None

    key_index = model.index(target_row, 0)
    assert model.data(key_index, Qt.DisplayRole) == "application"


def test_tree_model_type_column(control_dict_text):
    """Column 1 (Type) returns the node_type string"""
    root = OpenFoamParser(control_dict_text).parse()
    model = FoamTreeModel(root)

    target_row = None
    for row, child in enumerate(root.children):
        if child.name == "application":
            target_row = row
            break
    assert target_row is not None

    type_index = model.index(target_row, 1)
    assert model.data(type_index, Qt.DisplayRole) == "word"


def test_tree_model_value_column_word(control_dict_text):
    """Column 2 (Value) returns the value of a word node"""
    root = OpenFoamParser(control_dict_text).parse()
    model = FoamTreeModel(root)

    target_row = None
    for row, child in enumerate(root.children):
        if child.name == "application":
            target_row = row
            break
    assert target_row is not None

    value_index = model.index(target_row, 2)
    assert model.data(value_index, Qt.DisplayRole) == "interFoam"


def test_tree_model_value_column_int(control_dict_text):
    """Column 2 (Value) returns an int node value as a string"""
    root = OpenFoamParser(control_dict_text).parse()
    model = FoamTreeModel(root)

    target_row = None
    for row, child in enumerate(root.children):
        if child.name == "writeInterval":
            target_row = row
            break
    assert target_row is not None

    value_index = model.index(target_row, 2)
    assert model.data(value_index, Qt.DisplayRole) == "20"


def test_tree_model_value_column_scalar(control_dict_text):
    """Column 2 (Value) returns a scalar node value as a string"""
    root = OpenFoamParser(control_dict_text).parse()
    model = FoamTreeModel(root)

    target_row = None
    for row, child in enumerate(root.children):
        if child.name == "deltaT":
            target_row = row
            break
    assert target_row is not None

    value_index = model.index(target_row, 2)
    display = model.data(value_index, Qt.DisplayRole)
    assert "0.005" in display


def test_tree_model_value_column_dictionary(control_dict_text):
    """Column 2 (Value) returns an entry count summary for dictionary nodes"""
    root = OpenFoamParser(control_dict_text).parse()
    model = FoamTreeModel(root)

    target_row = None
    for row, child in enumerate(root.children):
        if child.name == "FoamFile":
            target_row = row
            break
    assert target_row is not None

    value_index = model.index(target_row, 2)
    display = model.data(value_index, Qt.DisplayRole)
    assert "entries" in display


def test_tree_model_nested_row_count(control_dict_text):
    """rowCount returns the number of children for a nested dictionary node"""
    root = OpenFoamParser(control_dict_text).parse()
    model = FoamTreeModel(root)

    foam_file_row = None
    for row, child in enumerate(root.children):
        if child.name == "FoamFile":
            foam_file_row = row
            break
    assert foam_file_row is not None

    foam_file_index = model.index(foam_file_row, 0)
    assert model.rowCount(foam_file_index) > 0


def test_tree_model_parent_index(control_dict_text):
    """parent() returns the correct parent index for a nested node"""
    root = OpenFoamParser(control_dict_text).parse()
    model = FoamTreeModel(root)

    foam_file_row = None
    for row, child in enumerate(root.children):
        if child.name == "FoamFile":
            foam_file_row = row
            break
    assert foam_file_row is not None

    foam_file_index = model.index(foam_file_row, 0)
    child_index = model.index(0, 0, foam_file_index)
    assert child_index.isValid()

    parent_index = model.parent(child_index)
    assert parent_index.isValid()
    assert parent_index.row() == foam_file_row


def test_tree_model_flags_editable_value(control_dict_text):
    """ItemIsEditable flag is set for editable Value cells (column 2)"""
    root = OpenFoamParser(control_dict_text).parse()
    model = FoamTreeModel(root)

    target_row = None
    for row, child in enumerate(root.children):
        if child.name == "deltaT":
            target_row = row
            break
    assert target_row is not None

    value_index = model.index(target_row, 2)
    flags = model.flags(value_index)
    assert flags & Qt.ItemIsEditable


def test_tree_model_flags_editable_key(control_dict_text):
    """ItemIsEditable flag is set for Key cells (column 0) of regular nodes"""
    root = OpenFoamParser(control_dict_text).parse()
    model = FoamTreeModel(root)

    target_row = None
    for row, child in enumerate(root.children):
        if child.name == "application":
            target_row = row
            break
    assert target_row is not None

    key_index = model.index(target_row, 0)
    flags = model.flags(key_index)
    assert flags & Qt.ItemIsEditable


def test_tree_model_flags_not_editable_type_column(control_dict_text):
    """ItemIsEditable flag is not set for Type cells (column 1)"""
    root = OpenFoamParser(control_dict_text).parse()
    model = FoamTreeModel(root)

    type_index = model.index(0, 1)
    flags = model.flags(type_index)
    assert not (flags & Qt.ItemIsEditable)


def test_tree_model_setdata_invalid_role(control_dict_text):
    """setData returns False when called with a role other than EditRole"""
    root = OpenFoamParser(control_dict_text).parse()
    model = FoamTreeModel(root)

    index = model.index(0, 2)
    result = model.setData(index, "somevalue", Qt.DisplayRole)
    assert result is False


def test_tree_model_setdata_key_column(control_dict_text):
    """Node name in column 0 (Key) can be changed via setData"""
    root = OpenFoamParser(control_dict_text).parse()
    model = FoamTreeModel(root)

    target_row = None
    for row, child in enumerate(root.children):
        if child.name == "application":
            target_row = row
            break
    assert target_row is not None

    key_index = model.index(target_row, 0)
    ok = model.setData(key_index, "myApplication", Qt.EditRole)
    assert ok is True
    assert root.children[target_row].name == "myApplication"
    assert root.children[target_row].modified is True


def test_tree_model_setdata_word_value(control_dict_text):
    """Value of a word node can be changed via setData"""
    root = OpenFoamParser(control_dict_text).parse()
    model = FoamTreeModel(root)

    target_row = None
    for row, child in enumerate(root.children):
        if child.name == "application":
            target_row = row
            break
    assert target_row is not None

    value_index = model.index(target_row, 2)
    ok = model.setData(value_index, "simpleFoam", Qt.EditRole)
    assert ok is True
    assert root.children[target_row].value == "simpleFoam"
    assert root.children[target_row].modified is True


def test_tree_model_edit_int_value(control_dict_text):
    """Value of an int node can be changed via setData"""
    root = OpenFoamParser(control_dict_text).parse()
    model = FoamTreeModel(root)

    target_row = None
    for row, child in enumerate(root.children):
        if child.name == "writeInterval":
            target_row = row
            break
    assert target_row is not None

    value_index = model.index(target_row, 2)
    ok = model.setData(value_index, "100", Qt.EditRole)
    assert ok is True
    assert root.children[target_row].value == 100
    assert root.children[target_row].modified is True


def test_tree_model_edit_invalid_int_value(control_dict_text):
    """setData returns False when a non-numeric string is set on an int node"""
    root = OpenFoamParser(control_dict_text).parse()
    model = FoamTreeModel(root)

    target_row = None
    for row, child in enumerate(root.children):
        if child.name == "writeInterval":
            target_row = row
            break
    assert target_row is not None

    value_index = model.index(target_row, 2)
    ok = model.setData(value_index, "notanumber", Qt.EditRole)
    assert ok is False


def test_tree_model_int_promotes_to_scalar(control_dict_text):
    """Setting a float string on an int node promotes the node type to scalar."""
    root = OpenFoamParser(control_dict_text).parse()
    model = FoamTreeModel(root)

    target_row = None
    for row, child in enumerate(root.children):
        if child.name == "writeInterval":
            target_row = row
            break
    assert target_row is not None

    value_index = model.index(target_row, 2)
    ok = model.setData(value_index, "0.5", Qt.EditRole)
    assert ok is True
    node = root.children[target_row]
    assert node.node_type == "scalar"
    assert node.value == 0.5
    assert node.modified is True


def test_tree_model_edit_invalid_scalar_value(control_dict_text):
    """setData returns False when a non-numeric string is set on a scalar node"""
    root = OpenFoamParser(control_dict_text).parse()
    model = FoamTreeModel(root)

    target_row = None
    for row, child in enumerate(root.children):
        if child.name == "deltaT":
            target_row = row
            break
    assert target_row is not None

    value_index = model.index(target_row, 2)
    ok = model.setData(value_index, "notanumber", Qt.EditRole)
    assert ok is False


def test_tree_model_tooltip_word_node(control_dict_text):
    """ToolTipRole for a word node contains the node name and type"""
    root = OpenFoamParser(control_dict_text).parse()
    model = FoamTreeModel(root)

    target_row = None
    for row, child in enumerate(root.children):
        if child.name == "application":
            target_row = row
            break
    assert target_row is not None

    index = model.index(target_row, 0)
    tooltip = model.data(index, Qt.ToolTipRole)
    assert tooltip is not None
    assert "application" in tooltip
    assert "word" in tooltip


def test_tree_model_field_value_block_child_list():
    """rowCount returns the number of items in the value list for field_value_block"""
    text = """
defaultFieldValues
(
    volScalarFieldValue alpha.water 0
    volScalarFieldValue alpha.water 1
);
"""
    root = OpenFoamParser(text).parse()
    model = FoamTreeModel(root)

    fvb_row = None
    for row, child in enumerate(root.children):
        if child.name == "defaultFieldValues":
            fvb_row = row
            break
    assert fvb_row is not None

    fvb_index = model.index(fvb_row, 0)
    assert model.rowCount(fvb_index) == 2


def test_tree_model_field_value_key_display():
    """Key column of a field_value node returns the field_name"""
    text = """
defaultFieldValues
(
    volScalarFieldValue alpha.water 0
);
"""
    root = OpenFoamParser(text).parse()
    model = FoamTreeModel(root)

    fvb_row = None
    for row, child in enumerate(root.children):
        if child.name == "defaultFieldValues":
            fvb_row = row
            break
    assert fvb_row is not None

    fvb_index = model.index(fvb_row, 0)
    fv_key_index = model.index(0, 0, fvb_index)
    assert model.data(fv_key_index, Qt.DisplayRole) == "alpha.water"


def test_tree_model_field_value_tooltip():
    """ToolTipRole for a field_value node contains type, field, and value"""
    text = """
defaultFieldValues
(
    volScalarFieldValue alpha.water 0
);
"""
    root = OpenFoamParser(text).parse()
    model = FoamTreeModel(root)

    fvb_row = None
    for row, child in enumerate(root.children):
        if child.name == "defaultFieldValues":
            fvb_row = row
            break
    assert fvb_row is not None

    fvb_index = model.index(fvb_row, 0)
    fv_index = model.index(0, 0, fvb_index)
    tooltip = model.data(fv_index, Qt.ToolTipRole)
    assert tooltip is not None
    assert "alpha.water" in tooltip
    assert "volScalarFieldValue" in tooltip
    assert "0" in tooltip


# ── set_diff(reverse=True) ────────────────────────────────────────────────────

def _make_diff_model():
    """Return a FoamTreeModel with one scalar leaf and one helper for building diffs."""
    from foam.nodes import FoamNode
    node = FoamNode(name="k", node_type="scalar", value=1.0)
    root = FoamNode(name="root", node_type="dictionary")
    root.children.append(node)
    node.parent = root
    model = FoamTreeModel(root)
    return model, node, root


def test_set_diff_reverse_remaps_only_here_to_only_in_ref():
    """reverse=True turns 'only_here' into 'only_in_ref' in the stored diff."""
    from foam.nodes import FoamNode
    model, node, _ = _make_diff_model()
    diff = {node: ("only_here", None)}
    model.set_diff(diff, reverse=True)
    assert model._diff[node][0] == "only_in_ref"


def test_set_diff_reverse_leaves_changed_unchanged():
    """reverse=True does not alter 'changed' entries."""
    from foam.nodes import FoamNode
    model, node, _ = _make_diff_model()
    ref_node = FoamNode(name="k", node_type="scalar", value=2.0)
    diff = {node: ("changed", ref_node)}
    model.set_diff(diff, reverse=True)
    assert model._diff[node] == ("changed", ref_node)


def test_set_diff_reverse_background_green_for_only_in_ref():
    """BackgroundRole returns the light-green colour for 'only_in_ref' nodes."""
    from PySide6.QtGui import QColor
    model, node, _ = _make_diff_model()
    diff = {node: ("only_here", None)}
    model.set_diff(diff, reverse=True)
    idx = model.index(0, 0)
    brush = model.data(idx, Qt.BackgroundRole)
    assert brush is not None
    assert brush.color() == QColor("#E8F5E9")


def test_set_diff_no_reverse_keeps_only_here():
    """Without reverse=True, 'only_here' is stored unchanged."""
    model, node, _ = _make_diff_model()
    diff = {node: ("only_here", None)}
    model.set_diff(diff)
    assert model._diff[node][0] == "only_here"


def test_set_diff_reverse_tooltip_only_in_ref():
    """ToolTipRole includes '(only in reference case)' for only_in_ref nodes."""
    model, node, _ = _make_diff_model()
    diff = {node: ("only_here", None)}
    model.set_diff(diff, reverse=True)
    idx = model.index(0, 0)
    tip = model.data(idx, Qt.ToolTipRole)
    assert "only in reference case" in tip
