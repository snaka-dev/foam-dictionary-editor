# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for topoSetDict actions block parsing and round-trip writing."""
from __future__ import annotations

import pytest

from foam.diff import diff_trees
from foam.parser import OpenFoamParser
from foam.writer import write_root

TOPO_SET_DICT = """\
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      topoSetDict;
}

actions
(
    // Heater
    {
        name    heaterCellSet;
        type    cellSet;
        action  new;
        source  boxToCell;
        box     (-0.01001 0 -100) (0.01001 0.00999 100);
    }
    {
        name    heaterCellSet;
        type    cellSet;
        action  add;
        source  boxToCell;
        box     (-0.01001 -100 -0.01001) (0.01001 0.00999 0.01001);
    }
    {
        name    heater;
        type    cellZoneSet;
        action  new;
        source  setToCellZone;
        set     heaterCellSet;
    }
    {
        name    bottomWaterCellSet;
        type    cellSet;
        action  invert;
    }
);
"""


@pytest.fixture
def root():
    return OpenFoamParser(TOPO_SET_DICT).parse()


def test_actions_node_type(root):
    actions = root.children[1]
    assert actions.name == "actions"
    assert actions.node_type == "action_list"


def test_actions_entry_count(root):
    actions = root.children[1]
    assert len(actions.children) == 4


def test_all_entries_are_action_entry(root):
    actions = root.children[1]
    for entry in actions.children:
        assert entry.node_type == "action_entry"
        assert entry.name == ""


def test_first_entry_children(root):
    entry = root.children[1].children[0]
    by_name = {c.name: c for c in entry.children}
    assert by_name["name"].value == "heaterCellSet"
    assert by_name["type"].value == "cellSet"
    assert by_name["action"].value == "new"
    assert by_name["source"].value == "boxToCell"
    assert by_name["box"].node_type == "box_pair"
    p1, p2 = by_name["box"].value
    assert pytest.approx(p1) == [-0.01001, 0.0, -100.0]
    assert pytest.approx(p2) == [0.01001, 0.00999, 100.0]


def test_set_entry(root):
    entry = root.children[1].children[2]  # heater / setToCellZone
    by_name = {c.name: c for c in entry.children}
    assert by_name["name"].value == "heater"
    assert by_name["type"].value == "cellZoneSet"
    assert by_name["source"].value == "setToCellZone"
    assert by_name["set"].value == "heaterCellSet"


def test_sourceless_entry(root):
    entry = root.children[1].children[3]  # invert — no source
    by_name = {c.name: c for c in entry.children}
    assert by_name["action"].value == "invert"
    assert "source" not in by_name


def test_round_trip(root):
    text2 = write_root(root)
    root2 = OpenFoamParser(text2).parse()
    actions2 = root2.children[1]
    assert actions2.node_type == "action_list"
    assert len(actions2.children) == 4
    entry0 = actions2.children[0]
    by_name = {c.name: c for c in entry0.children}
    assert by_name["name"].value == "heaterCellSet"
    assert by_name["box"].node_type == "box_pair"


# ── diff tests ────────────────────────────────────────────────────────────────

TOPO_SET_DICT_MODIFIED = """\
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      topoSetDict;
}

actions
(
    {
        name    heaterCellSet;
        type    cellSet;
        action  new;
        source  boxToCell;
        box     (-0.02 0 -100) (0.02 0.01 100);
    }
    {
        name    heaterCellSet;
        type    cellSet;
        action  add;
        source  boxToCell;
        box     (-0.01001 -100 -0.01001) (0.01001 0.00999 0.01001);
    }
    {
        name    heater;
        type    cellZoneSet;
        action  new;
        source  setToCellZone;
        set     heaterCellSet;
    }
    {
        name    bottomWaterCellSet;
        type    cellSet;
        action  invert;
    }
);
"""


def test_diff_detects_changed_box():
    a = OpenFoamParser(TOPO_SET_DICT).parse()
    b = OpenFoamParser(TOPO_SET_DICT_MODIFIED).parse()
    diff = diff_trees(a, b)
    changed_nodes = {n.name for n, (status, _) in diff.items() if status == "changed"}
    assert "box" in changed_nodes


def test_diff_identical_trees(root):
    b = OpenFoamParser(write_root(root)).parse()
    diff = diff_trees(root, b)
    assert not diff
