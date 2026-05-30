# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for ui/comparison_tree_panel.py."""
from __future__ import annotations

import pytest
from PySide6.QtCore import Qt

from foam.nodes import FoamNode
from model.tree_model import FoamTreeModel
from ui.comparison_tree_panel import ComparisonTreePanel


def _make_root(children: list[FoamNode]) -> FoamNode:
    root = FoamNode(name="root", node_type="dictionary")
    for c in children:
        c.parent = root
        root.children.append(c)
    return root


def _leaf(name, node_type, value) -> FoamNode:
    return FoamNode(name=name, node_type=node_type, value=value)


def _dict_node(name, children) -> FoamNode:
    n = FoamNode(name=name, node_type="dictionary")
    for c in children:
        c.parent = n
        n.children.append(c)
    return n


@pytest.fixture
def panel(qapp):
    p = ComparisonTreePanel()
    yield p
    p.deleteLater()


# ── initial state ─────────────────────────────────────────────────────────────

def test_initial_header_text(panel):
    assert panel._header_label.text() == "Reference case"


def test_initial_model_is_none(panel):
    assert panel._model is None


def test_type_column_hidden_after_load(panel):
    """Column 1 (Type) must be hidden after load() — the meaningful check point."""
    root = _make_root([_leaf("k", "scalar", 1.0)])
    panel.load(root, {}, "ref")
    assert panel._tree.isColumnHidden(FoamTreeModel.COL_TYPE)


# ── load ──────────────────────────────────────────────────────────────────────

def test_load_sets_header_label(panel):
    root = _make_root([_leaf("k", "scalar", 1.0)])
    panel.load(root, {}, "myCaseB")
    assert "myCaseB" in panel._header_label.text()


def test_load_sets_model(panel):
    root = _make_root([_leaf("k", "scalar", 1.0)])
    panel.load(root, {}, "ref")
    assert panel._model is not None


def test_load_populates_tree(panel):
    root = _make_root([_leaf("k", "scalar", 1.0)])
    panel.load(root, {}, "ref")
    assert panel._proxy.rowCount() == 1


def test_load_reapplies_type_column_hidden(panel):
    root = _make_root([_leaf("k", "scalar", 1.0)])
    panel.load(root, {}, "ref")
    assert panel._tree.isColumnHidden(FoamTreeModel.COL_TYPE)


def test_load_collapses_foam_file(panel):
    foam_file = _dict_node("FoamFile", [_leaf("version", "scalar", 2.0)])
    other = _leaf("nu", "scalar", 1e-6)
    root = _make_root([foam_file, other])
    panel.load(root, {}, "ref")
    # FoamFile should be collapsed (not expanded) in the proxy
    proxy_idx = panel._proxy.index(0, 0)  # FoamFile is first child
    assert not panel._tree.isExpanded(proxy_idx)


# ── clear ─────────────────────────────────────────────────────────────────────

def test_clear_resets_header(panel):
    root = _make_root([_leaf("k", "scalar", 1.0)])
    panel.load(root, {}, "ref")
    panel.clear()
    assert panel._header_label.text() == "Reference case"


def test_clear_resets_model(panel):
    root = _make_root([_leaf("k", "scalar", 1.0)])
    panel.load(root, {}, "ref")
    panel.clear()
    assert panel._model is None


def test_clear_empties_proxy(panel):
    root = _make_root([_leaf("k", "scalar", 1.0)])
    panel.load(root, {}, "ref")
    panel.clear()
    assert panel._proxy.rowCount() == 0


# ── set_type_column_visible ───────────────────────────────────────────────────

def test_set_type_column_visible_true(panel):
    panel.set_type_column_visible(True)
    assert not panel._tree.isColumnHidden(FoamTreeModel.COL_TYPE)


def test_set_type_column_visible_false(panel):
    root = _make_root([_leaf("k", "scalar", 1.0)])
    panel.load(root, {}, "ref")
    panel.set_type_column_visible(True)
    panel.set_type_column_visible(False)
    assert panel._tree.isColumnHidden(FoamTreeModel.COL_TYPE)


def test_set_type_column_visible_persists_across_load(panel):
    panel.set_type_column_visible(True)
    root = _make_root([_leaf("k", "scalar", 1.0)])
    panel.load(root, {}, "ref")
    # load() must re-apply the stored visibility
    assert not panel._tree.isColumnHidden(FoamTreeModel.COL_TYPE)


# ── use_value_requested signal ────────────────────────────────────────────────

def test_use_value_requested_signal_defined(panel):
    assert hasattr(panel, "use_value_requested")


def test_use_value_requested_can_connect(panel):
    received: list = []
    panel.use_value_requested.connect(received.append)
    node = _leaf("k", "scalar", 1.0)
    panel.use_value_requested.emit(node)
    assert received == [node]
