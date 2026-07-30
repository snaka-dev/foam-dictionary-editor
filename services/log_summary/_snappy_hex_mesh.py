# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""snappyHexMesh log grammar: castellation / snapping / layer-addition phases."""
from __future__ import annotations

import re

from services.log_summary._types import PhaseSummary

_CELLS_FACES_POINTS_RE = re.compile(
    r"cells:(\d+)\s+faces:(\d+)\s+points:(\d+)(?:\s+unbalance:([\d.eE+-]+))?"
)
_REFINEMENT_ITERATION_RE = re.compile(r"^(.+?) refinement iteration (\d+)\s*$")
_WROTE_MESH_RE = re.compile(r"^Wrote mesh in = .* s\.\s*$")
_MORPH_ITERATION_RE = re.compile(r"^Morph iteration (\d+)\s*$")
_LAYER_TABLE_HEADER_RE = re.compile(r"^patch\s+faces\s+layers")
_LAYER_MESH_RE = re.compile(r"^(Layer mesh|Mesh with layers)\s*:\s*(.*)$")
_CELLS_PER_LEVEL_HEADER_RE = re.compile(r"^Cells per refinement level:\s*$")
_FINISHED_TIME_RE = re.compile(r"^Finished meshing in = (.*)\.\s*$")
_FINISHED_OK_RE = re.compile(r"^Finished meshing without any errors\s*$")


def _final_cells_faces_points(lines: list[str]) -> str | None:
    result = None
    for line in lines:
        match = _CELLS_FACES_POINTS_RE.search(line)
        if match:
            cells, faces, points, _unbalance = match.groups()
            result = f"cells: {cells}, faces: {faces}, points: {points}"
    return result


def _iteration_counts(lines: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for line in lines:
        match = _REFINEMENT_ITERATION_RE.match(line.strip())
        if match:
            category = match.group(1)
            counts[category] = counts.get(category, 0) + 1
    return counts


def _last_layer_table(lines: list[str]) -> list[str]:
    last_table: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        if _LAYER_TABLE_HEADER_RE.match(lines[i].strip()):
            header = [lines[i].strip()]
            i += 1
            while i < n and lines[i].strip() and not lines[i].strip().startswith("-----"):
                header.append(lines[i].strip())
                i += 1
            while i < n and (lines[i].strip().startswith("-----") or not lines[i].strip()):
                i += 1
            rows: list[str] = []
            while i < n and lines[i].strip():
                rows.append(lines[i].strip())
                i += 1
            last_table = header + rows
            continue
        i += 1
    return last_table


def _parse_snappy_hex_mesh(lines: list[str]) -> tuple[list[PhaseSummary], bool, str | None]:
    phase_boundaries = [i for i, line in enumerate(lines) if _WROTE_MESH_RE.match(line.strip())]
    phases: list[PhaseSummary] = []

    castellation_end = phase_boundaries[0] if phase_boundaries else len(lines)
    castellation_lines = lines[:castellation_end]
    counts = _iteration_counts(castellation_lines)
    stats = _final_cells_faces_points(castellation_lines)
    castellation_summary = []
    if stats:
        castellation_summary.append(f"Final mesh: {stats}")
    for category, count in counts.items():
        castellation_summary.append(f"{category} refinement: {count} iteration(s)")
    if castellation_summary:
        phases.append(PhaseSummary(name="Castellation", lines=castellation_summary))

    if len(phase_boundaries) >= 2:
        snap_lines = lines[phase_boundaries[0]:phase_boundaries[1]]
        morph_count = sum(1 for line in snap_lines if _MORPH_ITERATION_RE.match(line.strip()))
        snap_stats = _final_cells_faces_points(snap_lines)
        snap_summary = []
        if snap_stats:
            snap_summary.append(f"Final mesh: {snap_stats}")
        snap_summary.append(f"Snapping relaxation: {morph_count} iteration(s)")
        phases.append(PhaseSummary(name="Snapping", lines=snap_summary))

    if len(phase_boundaries) >= 3:
        layer_lines = lines[phase_boundaries[1]:phase_boundaries[2]]
        table_rows = _last_layer_table(layer_lines)
        layer_summary = list(table_rows)
        for line in layer_lines:
            match = _LAYER_MESH_RE.match(line.strip())
            if match:
                layer_summary.append(f"{match.group(1)}: {match.group(2).strip()}")
        if layer_summary:
            phases.append(PhaseSummary(name="Layer addition", lines=layer_summary))

    tail = lines[phase_boundaries[-1]:] if phase_boundaries else lines
    finished_ok = any(_FINISHED_OK_RE.match(line.strip()) for line in tail)
    total_time = None
    for line in tail:
        match = _FINISHED_TIME_RE.match(line.strip())
        if match:
            total_time = match.group(1).strip()
    return phases, finished_ok, total_time
