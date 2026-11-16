# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""services/allrun.py over every tutorial Allrun (skipped when not installed).

Every script must read without an exception, and the counts pin what was
measured on 2026-11-14 so a parser change that loses steps is noticed: the
v2606 tree holds 494 Allruns (359 linear, 2001 steps, 5 with an application
that cannot be told), Foundation 12 holds 213 (178 linear, 893 steps, 8).
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from services.allrun import read_allrun

TREES = {
    "v2606": (Path("/usr/lib/openfoam/openfoam2606"), 494, 359, 2001, 5),
    "foundation-12": (
        Path(__file__).resolve().parents[3] / "openfoam-sources" / "OpenFOAM-12", 213, 178, 893, 8,
    ),
}


@pytest.mark.parametrize("name", sorted(TREES))
def test_every_tutorial_allrun_reads(name: str):
    root, scripts, linear, steps, unresolved = TREES[name]
    if not (root / "tutorials").is_dir():
        pytest.skip(f"{root} is not installed")
    n = n_linear = n_steps = n_unresolved = 0
    for r, _dirs, files in os.walk(root / "tutorials"):
        if "Allrun" not in files:
            continue
        plan = read_allrun(r)
        assert plan is not None
        n += 1
        n_linear += plan.linear
        n_steps += len(plan.runs)
        n_unresolved += sum(1 for s in plan.runs if not s.app)
    assert (n, n_linear, n_steps, n_unresolved) == (scripts, linear, steps, unresolved)


def test_dam_break():
    root = Path("/usr/lib/openfoam/openfoam2606/tutorials/multiphase/interFoam/laminar/damBreak/damBreak")
    if not root.is_dir():
        pytest.skip("v2606 tutorials not installed")
    plan = read_allrun(str(root))
    assert [s.text for s in plan.steps][0] == "restore0Dir"
    assert [(s.app, s.log) for s in plan.runs] == [
        ("blockMesh", "log.blockMesh"), ("setFields", "log.setFields"), ("interFoam", "log.interFoam"),
    ]
