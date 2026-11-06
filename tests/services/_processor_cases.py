# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Shared builders for decomposed-case tests (not a test module).

Used by tests/services/test_solver_run.py and tests/ui/test_tools_busy_terminal.py.
The layout mirrors what decomposePar + a parallel run + reconstructPar leave
on disk; it was checked against a real OpenFOAM v2606 cavity run.
"""
from __future__ import annotations


def _owner(mesh_dir, n_cells):
    mesh_dir.mkdir(parents=True, exist_ok=True)
    (mesh_dir / "owner").write_text(
        f'FoamFile\n{{\n    note "nPoints:10 nCells:{n_cells} nFaces:20 nInternalFaces:5";\n}}\n'
    )
    (mesh_dir / "points").write_text("()")


def _reconstructed_case(root, times=("0", "0.5", "1"), fields=("U", "p"), n_proc=2):
    """A case whose processor* data all exists at the root -- safe to delete."""
    _owner(root / "constant" / "polyMesh", 8 * n_proc)
    for n in range(n_proc):
        proc = root / f"processor{n}"
        _owner(proc / "constant" / "polyMesh", 8)
        (proc / "constant" / "polyMesh" / "cellProcAddressing").write_text("x")
        for t in times:
            (proc / t).mkdir(parents=True)
            for f in fields:
                (proc / t / f).write_text("x" * 100)
            if t != "0":
                (proc / t / "uniform").mkdir()
                (proc / t / "uniform" / "time").write_text("x")
    for t in times:
        (root / t).mkdir(parents=True)
        for f in fields:
            (root / t / f).write_text("x")
        if t != "0":
            (root / t / "uniform").mkdir()
            (root / t / "uniform" / "time").write_text("x")
    return root
