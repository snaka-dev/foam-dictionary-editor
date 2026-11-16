# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""The false-alarm guard for services/case_check.py.

Every tutorial of the local v2606 and Foundation-12 trees is checked as the
solver would see it once Allrun's ``restore0Dir`` has run (0.orig/ shown as
0/ through a symlinked view; the tree itself is never touched), and must
produce no finding beyond the reviewed ones below. A false alarm is worse
than silence for a beginner, so a new entry here needs a reason a reviewer
can verify. Skipped when the trees are not installed.

Measured 2026-11-14 over all thirteen local trees (OpenCFD v2212-v2606,
Foundation 7-12 and dev); a run of the real blockMesh on the 199 v2606
tutorials whose mesh is blockMeshDict alone found nothing further either.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from services.case_check import DECOMPOSITION_PRODUCT, STOP_AT_LEFT, check_case

TREES = {
    "v2606": Path("/usr/lib/openfoam/openfoam2606"),
    "foundation-12": Path(__file__).resolve().parents[3] / "openfoam-sources" / "OpenFOAM-12",
}

# (tree, case relative to tutorials/, code) -> why the finding is right.
REVIEWED = {
    ("v2606", "IO/fileHandler", STOP_AT_LEFT):
        "deliberate: a file-handler test; each of its many solver runs is "
        "meant to write one time and stop",
    ("v2606", "mesh/snappyHexMesh/rotated_block", STOP_AT_LEFT):
        "deliberate: application is snappyHexMesh and the Allrun only meshes",
    ("v2606", "preProcessing/createZeroDirectory/motorBike", STOP_AT_LEFT):
        "deliberate: a createZeroDirectory demo; the solver run that ends "
        "its Allrun only has to start, write and stop",
    ("v2606", "preProcessing/createZeroDirectory/snappyMultiRegionHeater", STOP_AT_LEFT):
        "deliberate: as motorBike",
    ("v2606", "multiphase/interIsoFoam/standingWave", DECOMPOSITION_PRODUCT):
        "a real latent bug: decomposePar on it stops with 'Wrong number of "
        "domain divisions' (numberOfSubdomains 1, n (2 1 2)); the tutorial "
        "never decomposes",
}


def _cases(tree: Path) -> list[Path]:
    found = []
    for root, _dirs, files in os.walk(tree / "tutorials"):
        if "controlDict" in files and root.endswith(os.sep + "system"):
            case = Path(root).parent
            # setups.orig/common holds fragments merged into each setup by
            # its Allrun; it is not a case of its own.
            if "setups.orig" not in case.parts:
                found.append(case)
    return sorted(found)


def _restored_view(case: Path, view: Path) -> Path:
    view.mkdir()
    names = os.listdir(case)
    for name in names:
        (view / name).symlink_to(case / name)
    if "0" not in names and "0.orig" in names:
        (view / "0").symlink_to(case / "0.orig")
    return view


@pytest.mark.parametrize("tree_name", sorted(TREES))
def test_unbroken_tutorials_have_no_findings(tree_name: str, tmp_path: Path):
    tree = TREES[tree_name]
    if not (tree / "tutorials").is_dir():
        pytest.skip(f"{tree} is not installed")
    unexpected = []
    seen = set()
    for i, case in enumerate(_cases(tree)):
        rel = case.relative_to(tree / "tutorials").as_posix()
        result = check_case(
            str(_restored_view(case, tmp_path / str(i))),
            etc_dirs=[str(tree / "etc")],
            installation=str(tree),
        )
        for finding in result.findings:
            key = (tree_name, rel, finding.code)
            if key in REVIEWED:
                seen.add(key)
            else:
                unexpected.append(f"{rel}: {finding.code} {finding.path}:{finding.line} {finding.args}")
    assert unexpected == []
    stale = [k for k in REVIEWED if k[0] == tree_name and k not in seen]
    assert stale == [], "reviewed findings that no longer occur -- drop them"
