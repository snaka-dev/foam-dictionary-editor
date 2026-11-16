# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Suffixed variants against the real tutorials (skipped when not installed).

Spot checks of the cases that shaped the rule in foam/variants.py, from the
local v2606 tree: what must be listed, and what must stay out.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from services.case_loader import list_case_files

TUTORIALS = Path("/usr/lib/openfoam/openfoam2606/tutorials")

pytestmark = pytest.mark.skipif(not TUTORIALS.is_dir(), reason="OpenFOAM v2606 tutorials not installed")


def _listed(case: str) -> set[str]:
    root = TUTORIALS / case
    return {os.path.relpath(p, root) for p in list_case_files(str(root))}


def test_mixer_vessel():
    listed = _listed("mesh/foamyHexMesh/mixerVessel")
    # Variants run with -dict or copied into place by Allrun.
    for name in ("controlDict.flow", "controlDict.mesh", "collapseDict.collapseFaces",
                 "collapseDict.indirectPatchFaces"):
        assert os.path.join("system", name) in listed
    # #include fragments of foamyHexMeshDict, whose headers name themselves:
    # the include scan shows them as included rows, not as variants of meshDict.
    for name in ("meshDict.geometry", "meshDict.conformationSurfaces", "meshDict.cellShapeControl"):
        assert os.path.join("system", name) not in listed


def test_a_case_with_a_series_of_decompositions():
    hits = [
        p for p in TUTORIALS.rglob("decomposeParDict.*")
        if p.parent.name == "system" and (p.parent / "controlDict").is_file()
    ]
    assert hits, "expected decomposeParDict.N variants in the v2606 tutorials"
    case = hits[0].parent.parent
    assert os.path.join("system", hits[0].name) in _listed(str(case.relative_to(TUTORIALS)))
