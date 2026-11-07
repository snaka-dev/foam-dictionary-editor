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


END_LINE = "// " + "*" * 73 + " //\n"


def _field_text(obj, n=None, cls="volScalarField", *, binary=False):
    """An OpenFOAM field file as reconstructPar writes it.

    ``n`` values make the internalField nonuniform; None makes it uniform.
    ``binary`` fills the list with raw bytes, as ``writeFormat binary`` does.
    """
    head = (
        "FoamFile\n{\n    version     2.0;\n"
        f"    format      {'binary' if binary else 'ascii'};\n"
        f"    class       {cls};\n    object      {obj};\n}}\n"
        "dimensions      [0 2 -2 0 0 0 0];\n\n"
    )
    if n is None:
        internal = "internalField   uniform 0;\n\n"
    elif binary:
        internal = f"internalField   nonuniform List<scalar> \n{n}\n(" + "\x00\xff)(;}" * n + ")\n;\n\n"
    else:
        internal = f"internalField   nonuniform List<scalar> \n{n}\n(\n" + "1\n" * n + ")\n;\n\n"
    boundary = "boundaryField\n{\n    walls\n    {\n        type zeroGradient;\n    }\n}\n\n\n"
    return head + internal + boundary + END_LINE


def _write(path, text, *, gz=False):
    import gzip

    path.parent.mkdir(parents=True, exist_ok=True)
    if gz:
        with gzip.open(f"{path}.gz", "wb") as f:
            f.write(text.encode("latin-1"))
    else:
        path.write_bytes(text.encode("latin-1"))


def _sound_case(root, times=("0", "0.5", "1"), n_proc=2, cells=8, *, gz=False):
    """A reconstructed case whose files are real OpenFOAM files, all whole.

    Each processor has *cells* cells, so a root field holds cells * n_proc.
    ``gz`` writes the time directories compressed (``writeCompression on``)
    -- except the processors' ``0/``, which decomposePar compresses from an
    uncompressed root ``0/``, so there the names differ.
    """
    _owner(root / "constant" / "polyMesh", cells * n_proc)
    for n in range(n_proc):
        proc = root / f"processor{n}"
        _owner(proc / "constant" / "polyMesh", cells)
        for t in times:
            _write(proc / t / "p", _field_text("p", cells), gz=gz)
            if t != "0":
                _write(proc / t / "uniform" / "time", _field_text("time", cls="dictionary"), gz=gz)
    for t in times:
        root_gz = gz and t != "0"
        _write(root / t / "p", _field_text("p", cells * n_proc), gz=root_gz)
        if t != "0":
            _write(root / t / "uniform" / "time", _field_text("time", cls="dictionary"), gz=root_gz)
    return root
