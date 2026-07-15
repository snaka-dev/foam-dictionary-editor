# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for log_summary: condensing blockMesh/snappyHexMesh/topoSet run logs."""
from __future__ import annotations

from services.log_summary import format_summary, parse_log

_HEADER = """\
/*---------------------------------------------------------------------------*\\
| =========                 |                                                 |
\\*---------------------------------------------------------------------------*/
Build  : _bd2b6720-20260127 OPENFOAM=2512 version=2512
Exec   : {exec_line}
Date   : Jul 07 2026
Case   : /home/user/run/myCase
nProcs : 1

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
"""


def _log(exec_line: str, body: str) -> str:
    return _HEADER.format(exec_line=exec_line) + body


def test_block_mesh_summary():
    body = """\
Creating block mesh from "system/blockMeshDict"

----------------
Mesh Information
----------------
  boundingBox: (-2.03 -2 0) (8.03 8 5)
  nPoints: 4851
  nCells: 4000
  nFaces: 12800
  nInternalFaces: 11200
----------------
Patches
----------------
  patch 0 (start: 11200 size: 200) name: maxY
  patch 1 (start: 11400 size: 200) name: minX

End
"""
    summary = parse_log(_log("blockMesh", body))
    assert summary.utility == "blockMesh"
    assert summary.finished_ok is True
    assert len(summary.phases) == 1
    lines = summary.phases[0].lines
    assert "nCells: 4000" in lines
    assert "patch 0 (start: 11200 size: 200) name: maxY" in lines
    text = format_summary(summary)
    assert "nCells: 4000" in text
    assert "Result: OK" in text


def test_block_mesh_fatal_error_marks_failed():
    body = """\

FOAM FATAL ERROR
    Cannot find file "system/blockMeshDict"

    From function ...
End
"""
    summary = parse_log(_log("blockMesh", body))
    assert summary.finished_ok is False
    assert len(summary.errors) == 1
    assert "Cannot find file" in summary.errors[0]


def test_snappy_hex_mesh_phases_and_layer_table():
    body = """\
Reading refinement surfaces.
Feature refinement iteration 0
After balancing feature refinement iteration 0 : cells:100  faces:300  points:150  unbalance:0.01
Feature refinement iteration 1
After balancing feature refinement iteration 1 : cells:200  faces:600  points:300  unbalance:0.02
Wrote mesh in = 0.02 s.

Morph iteration 0
--> FOAM Warning : Displacement (-0.0002 0.0011 9e-06) at mesh point 4370 coord (3.7 -0.4 0.06) points through the surrounding patch faces
Smoothing displacement ...
Iteration 0
Iteration 10
Displacement smoothed in = 0.02 s
Wrote mesh in = 0.02 s.

patch                       faces        layers        overall thickness
                                     target   mesh     [m]       [%]
-----                       -----    -----    ----     ---       ---
ground                      538      3        1.81     0.0472    49.4

Mesh with layers : cells:250  faces:700  points:350  unbalance:0.04
Layer mesh : cells:250  faces:700  points:350  unbalance:1e-05
Wrote mesh in = 0.02 s.
Finished meshing without any errors
Finished meshing in = 2.82 s.
End
"""
    summary = parse_log(_log("snappyHexMesh -overwrite", body))
    assert summary.utility == "snappyHexMesh"
    assert summary.finished_ok is True
    assert summary.total_time == "2.82 s"

    names = [phase.name for phase in summary.phases]
    assert names == ["Castellation", "Snapping", "Layer addition"]

    castellation = summary.phases[0].lines
    assert "Final mesh: cells: 200, faces: 600, points: 300" in castellation
    assert "Feature refinement: 2 iteration(s)" in castellation

    snapping = summary.phases[1].lines
    assert any(line == "Snapping relaxation: 1 iteration(s)" for line in snapping)

    layer_lines = summary.phases[2].lines
    assert any("ground" in line and "1.81" in line for line in layer_lines)
    assert "Mesh with layers: cells:250  faces:700  points:350  unbalance:0.04" in layer_lines
    assert "Layer mesh: cells:250  faces:700  points:350  unbalance:1e-05" in layer_lines

    assert len(summary.warnings) == 1
    assert summary.warnings[0].count == 1
    assert "Displacement" in summary.warnings[0].message
    # Numeric noise inside the warning message is collapsed so repeats can merge.
    assert "0.0002" not in summary.warnings[0].message


def test_snappy_hex_mesh_duplicate_warnings_are_merged():
    body = """\
Morph iteration 0
--> FOAM Warning : Displacement (-0.0002 0.0011 9e-06) at mesh point 4370 coord (3.7 -0.4 0.06) points through the surrounding patch faces
Morph iteration 1
--> FOAM Warning : Displacement (-0.0004 0.0025 4e-06) at mesh point 4370 coord (3.73 -0.45 0.06) points through the surrounding patch faces
Wrote mesh in = 0.02 s.
End
"""
    summary = parse_log(_log("snappyHexMesh", body))
    assert len(summary.warnings) == 1
    assert summary.warnings[0].count == 2


def test_topo_set_multi_source_set_is_collapsed_to_one_line():
    body = """\
Reading topoSetDict

Time = 0
Created cellSet heaterCellSet
    Applying source boxToCell
    Adding cells with centre within boxes 1((-0.01 0 -100) (0.01 0.01 100))
    cellSet heaterCellSet now size 40
Created cellSet bottomWaterCellSet
    Applying source cellToCell
    Adding all elements of cell sets: (heaterCellSet)
    cellSet bottomWaterCellSet now size 80
Read set cellSet bottomWaterCellSet size:80
    Inverting cellSet
    cellSet bottomWaterCellSet now size 1460
Created cellZoneSet bottomWater
    Applying source setToCellZone
    Adding all cells from cell set: bottomWaterCellSet ...
    cellZoneSet bottomWater now size 1460

End
"""
    summary = parse_log(_log("topoSet", body))
    assert summary.utility == "topoSet"
    assert summary.finished_ok is True
    assert len(summary.phases) == 1
    lines = summary.phases[0].lines
    assert "cellSet heaterCellSet: boxToCell → 40 entries" in lines
    assert "cellSet bottomWaterCellSet: cellToCell → 1460 entries" in lines
    assert "cellZoneSet bottomWater: setToCellZone → 1460 entries" in lines


def test_generic_fallback_for_unrecognized_utility():
    body = "\n".join(f"line {i}" for i in range(30))
    summary = parse_log(_log("checkMesh", body))
    assert summary.utility == "checkMesh"
    assert len(summary.phases) == 1
    assert summary.phases[0].name == "Tail"
    assert len(summary.phases[0].lines) == 20
    assert summary.phases[0].lines[-1] == "line 29"


def test_format_summary_is_shorter_than_original_for_snappy_log():
    body = "\n".join(
        f"Feature refinement iteration {i}\n"
        f"After balancing feature refinement iteration {i} : cells:{100 + i}  faces:{300 + i}  points:{150 + i}  unbalance:0.01"
        for i in range(20)
    ) + "\nWrote mesh in = 0.02 s.\nEnd\n"
    text = _log("snappyHexMesh", body)
    summary = parse_log(text)
    formatted = format_summary(summary)
    assert len(formatted.splitlines()) < len(text.splitlines())
