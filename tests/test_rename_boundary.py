# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for the rename-boundary scanner (find_rename_targets)."""
from __future__ import annotations

import pytest

from foam.parser import OpenFoamParser
from ui.rename_boundary_dialog import find_rename_targets


def _parse(text: str):
    return OpenFoamParser(text).parse()


_BLOCKMESH = """
FoamFile { version 2.0; format ascii; class dictionary; object blockMeshDict; }
scale 1;
vertices ( (0 0 0) (1 0 0) (1 1 0) (0 1 0) (0 0 1) (1 0 1) (1 1 1) (0 1 1) );
blocks ( hex (0 1 2 3 4 5 6 7) (10 10 10) simpleGrading (1 1 1) );
boundary
(
    inlet  { type patch; faces ( (0 4 7 3) ); }
    outlet { type patch; faces ( (1 2 6 5) ); }
    walls  { type wall;  faces ( (0 1 5 4) (3 7 6 2) ); }
);
"""

_FIELD_U = """
FoamFile { version 2.0; format ascii; class volVectorField; object U; }
dimensions [0 1 -1 0 0 0 0];
internalField uniform (0 0 0);
boundaryField
{
    inlet  { type fixedValue; value uniform (1 0 0); }
    outlet { type zeroGradient; }
    walls  { type noSlip; }
}
"""

_FIELD_P = """
FoamFile { version 2.0; format ascii; class volScalarField; object p; }
dimensions [0 2 -2 0 0 0 0];
internalField uniform 0;
boundaryField
{
    inlet  { type zeroGradient; }
    outlet { type fixedValue; value uniform 0; }
    walls  { type zeroGradient; }
}
"""

_ROOTS = {
    "/case/system/blockMeshDict": _parse(_BLOCKMESH),
    "/case/0/U":                  _parse(_FIELD_U),
    "/case/0/p":                  _parse(_FIELD_P),
}


def test_finds_boundary_entry_in_blockmesh():
    targets = find_rename_targets("inlet", _ROOTS)
    assert "/case/system/blockMeshDict" in targets
    nodes = targets["/case/system/blockMeshDict"]
    assert len(nodes) == 1
    assert nodes[0].node_type == "boundary_entry"
    assert nodes[0].name == "inlet"


def test_finds_boundaryfiled_dict_in_field_files():
    targets = find_rename_targets("inlet", _ROOTS)
    assert "/case/0/U" in targets
    assert "/case/0/p" in targets
    u_nodes = targets["/case/0/U"]
    assert len(u_nodes) == 1
    assert u_nodes[0].node_type == "dictionary"
    assert u_nodes[0].name == "inlet"


def test_all_three_files_found_for_inlet():
    targets = find_rename_targets("inlet", _ROOTS)
    assert set(targets.keys()) == {
        "/case/system/blockMeshDict",
        "/case/0/U",
        "/case/0/p",
    }


def test_no_false_positives_for_unrelated_name():
    targets = find_rename_targets("nonexistent", _ROOTS)
    assert targets == {}


def test_only_matching_patch_returned():
    targets = find_rename_targets("outlet", _ROOTS)
    for path, nodes in targets.items():
        assert all(n.name == "outlet" for n in nodes)


def test_empty_roots_returns_empty():
    assert find_rename_targets("inlet", {}) == {}


def test_does_not_match_non_boundary_dict():
    """A dictionary named 'inlet' that is NOT inside boundaryField is ignored."""
    text = """
FoamFile { version 2.0; format ascii; }
inlet { type someType; }
"""
    root = _parse(text)
    targets = find_rename_targets("inlet", {"/case/system/fvSolution": root})
    assert targets == {}
