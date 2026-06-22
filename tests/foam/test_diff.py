# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from foam.diff import diff_trees, diff_trees_reverse
from foam.nodes import FoamNode


def _dict(name, children):
    n = FoamNode(name=name, node_type="dictionary")
    for c in children:
        c.parent = n
        n.children.append(c)
    return n


def _leaf(name, node_type, value):
    return FoamNode(name=name, node_type=node_type, value=value)


# ── basic cases ───────────────────────────────────────────────────────────────

def test_identical_trees_produce_empty_diff():
    a = _dict("root", [_leaf("k", "scalar", 1.0)])
    b = _dict("root", [_leaf("k", "scalar", 1.0)])
    assert diff_trees(a, b) == {}


def test_empty_trees_produce_empty_diff():
    a = _dict("root", [])
    b = _dict("root", [])
    assert diff_trees(a, b) == {}


def test_changed_value():
    a_k = _leaf("k", "scalar", 1.0)
    b_k = _leaf("k", "scalar", 2.0)
    a = _dict("root", [a_k])
    b = _dict("root", [b_k])
    result = diff_trees(a, b)
    assert result[a_k] == ("changed", b_k)


def test_key_only_in_a():
    a_k = _leaf("extra", "word", "yes")
    a = _dict("root", [a_k])
    b = _dict("root", [])
    result = diff_trees(a, b)
    assert result[a_k] == ("only_here", None)


def test_key_only_in_b_not_annotated():
    a = _dict("root", [])
    b = _dict("root", [_leaf("extra", "word", "yes")])
    result = diff_trees(a, b)
    assert result == {}


def test_type_change_reported_as_changed():
    a_k = _leaf("k", "scalar", 1.0)
    b_k = _leaf("k", "int", 1)
    a = _dict("root", [a_k])
    b = _dict("root", [b_k])
    result = diff_trees(a, b)
    assert result[a_k] == ("changed", b_k)


# ── nested dictionaries ───────────────────────────────────────────────────────

def test_nested_dict_unchanged():
    inner_a = _dict("sub", [_leaf("x", "scalar", 3.0)])
    inner_b = _dict("sub", [_leaf("x", "scalar", 3.0)])
    a = _dict("root", [inner_a])
    b = _dict("root", [inner_b])
    assert diff_trees(a, b) == {}


def test_nested_dict_changed_leaf():
    x_a = _leaf("x", "scalar", 3.0)
    x_b = _leaf("x", "scalar", 9.0)
    inner_a = _dict("sub", [x_a])
    inner_b = _dict("sub", [x_b])
    a = _dict("root", [inner_a])
    b = _dict("root", [inner_b])
    result = diff_trees(a, b)
    assert result[x_a] == ("changed", x_b)
    assert inner_a not in result


def test_nested_dict_missing_in_b():
    inner_a = _dict("sub", [_leaf("x", "scalar", 3.0)])
    a = _dict("root", [inner_a])
    b = _dict("root", [])
    result = diff_trees(a, b)
    assert result[inner_a] == ("only_here", None)


def test_multiple_keys_mix():
    same = _leaf("same", "scalar", 1.0)
    changed = _leaf("changed", "scalar", 1.0)
    extra = _leaf("extra", "word", "a")
    b_changed = _leaf("changed", "scalar", 2.0)
    a = _dict("root", [same, changed, extra])
    b = _dict("root", [_leaf("same", "scalar", 1.0), b_changed])
    result = diff_trees(a, b)
    assert same not in result
    assert result[changed] == ("changed", b_changed)
    assert result[extra] == ("only_here", None)


# ── anonymous nodes are skipped ───────────────────────────────────────────────

def test_anonymous_nodes_not_annotated():
    anon = FoamNode(name="", node_type="directive_entry", value="#include")
    a = _dict("root", [anon])
    b = _dict("root", [])
    result = diff_trees(a, b)
    assert anon not in result


# ── field_value_block ─────────────────────────────────────────────────────────

def _fvb(name, items):
    n = FoamNode(name=name, node_type="field_value_block", value=items)
    for c in items:
        c.parent = n
    return n


def _fv(field_name, value_type, value):
    return FoamNode(
        name="",
        node_type="field_value",
        value={"field_name": field_name, "value_type": value_type, "value": value},
    )


def test_field_value_block_unchanged():
    fv_a = _fv("p", "scalar", 0.0)
    fv_b = _fv("p", "scalar", 0.0)
    a = _dict("root", [_fvb("defaultFieldValues", [fv_a])])
    b = _dict("root", [_fvb("defaultFieldValues", [fv_b])])
    assert diff_trees(a, b) == {}


def test_field_value_block_changed():
    fv_a = _fv("p", "scalar", 0.0)
    fv_b = _fv("p", "scalar", 1.0)
    a_block = _fvb("defaultFieldValues", [fv_a])
    b_block = _fvb("defaultFieldValues", [fv_b])
    a = _dict("root", [a_block])
    b = _dict("root", [b_block])
    result = diff_trees(a, b)
    assert result[fv_a] == ("changed", fv_b)


def test_field_value_block_only_here():
    fv_a = _fv("U", "vector", [0, 0, 0])
    a_block = _fvb("defaultFieldValues", [fv_a])
    b_block = _fvb("defaultFieldValues", [])
    a = _dict("root", [a_block])
    b = _dict("root", [b_block])
    result = diff_trees(a, b)
    assert result[fv_a] == ("only_here", None)


# ── diff_trees_reverse ────────────────────────────────────────────────────────

def test_reverse_identical_trees_empty():
    a = _dict("root", [_leaf("k", "scalar", 1.0)])
    b = _dict("root", [_leaf("k", "scalar", 1.0)])
    assert diff_trees_reverse(b, a) == {}


def test_reverse_annotates_nodes_in_b():
    """Keys only in b (not in a) appear as 'only_here' on b's nodes."""
    b_k = _leaf("extra", "word", "yes")
    a = _dict("root", [])
    b = _dict("root", [b_k])
    result = diff_trees_reverse(b, a)
    assert b_k in result
    assert result[b_k] == ("only_here", None)


def test_reverse_changed_values_annotated_on_b():
    a_k = _leaf("k", "scalar", 1.0)
    b_k = _leaf("k", "scalar", 2.0)
    a = _dict("root", [a_k])
    b = _dict("root", [b_k])
    result = diff_trees_reverse(b, a)
    assert result[b_k] == ("changed", a_k)


def test_reverse_key_only_in_a_not_annotated():
    """Keys only in a do not appear in the reverse diff (b is the subject)."""
    a_k = _leaf("extra", "word", "yes")
    a = _dict("root", [a_k])
    b = _dict("root", [])
    result = diff_trees_reverse(b, a)
    assert a_k not in result
    assert result == {}


def test_reverse_is_equivalent_to_swapped_diff_trees():
    a_k = _leaf("x", "scalar", 1.0)
    b_k = _leaf("x", "scalar", 2.0)
    a = _dict("root", [a_k, _leaf("only_a", "word", "v")])
    b = _dict("root", [b_k, _leaf("only_b", "word", "v")])
    assert diff_trees_reverse(b, a) == diff_trees(b, a)
