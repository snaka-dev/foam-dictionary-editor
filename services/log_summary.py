# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Condense OpenFOAM run logs (blockMesh/snappyHexMesh/topoSet stdout, tee'd to
``log.*`` files) into a short, structured report.

This is unrelated to ``foam/``'s dictionary-tree extractors: it parses solver/
utility *log text*, not ``FoamNode`` trees.
"""
from __future__ import annotations

import dataclasses
import re

_HEADER_FIELD_RE = re.compile(r"^([A-Za-z][\w ]*?)\s*:\s*(.*)$")
_HEADER_FIELDS = ("Exec", "Version", "Build", "Date", "Case", "nProcs")
_HEADER_END_RE = re.compile(r"^//\s*\*")

_WARNING_START_RE = re.compile(r"^-->\s*FOAM Warning\s*:\s*(.*)$")
_FATAL_START_RE = re.compile(r"^-{3,}\s*$|^\s*$")
_FATAL_HEADER_RE = re.compile(r"FOAM FATAL ERROR", re.IGNORECASE)
_NUMERIC_RE = re.compile(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")

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

_TOPOSET_CREATED_RE = re.compile(r"^Created (\S+) (\S+)\s*$")
_TOPOSET_READSET_RE = re.compile(r"^Read set (\S+) (\S+) size:(\d+)\s*$")
_TOPOSET_SOURCE_RE = re.compile(r"^\s*Applying source (\S+)\s*$")
_TOPOSET_SIZE_RE = re.compile(r"^\s*(\S+) (\S+) now size (\d+)\s*$")


@dataclasses.dataclass
class LogWarning:
    message: str
    count: int


@dataclasses.dataclass
class PhaseSummary:
    name: str
    lines: list[str]


@dataclasses.dataclass
class LogSummary:
    utility: str
    header: dict[str, str]
    phases: list[PhaseSummary]
    warnings: list[LogWarning]
    errors: list[str]
    finished_ok: bool
    total_time: str | None = None


def _parse_header(lines: list[str]) -> tuple[dict[str, str], int]:
    """Return the header field map and the index of the first line after it."""
    header: dict[str, str] = {}
    end = len(lines)
    for i, line in enumerate(lines):
        if _HEADER_END_RE.match(line):
            end = i + 1
            break
        match = _HEADER_FIELD_RE.match(line)
        if match and match.group(1) in _HEADER_FIELDS:
            header[match.group(1)] = match.group(2).strip()
    return header, end


def _collect_warnings_and_errors(lines: list[str]) -> tuple[list[LogWarning], list[str]]:
    counts: dict[str, int] = {}
    order: list[str] = []
    errors: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        warn_match = _WARNING_START_RE.match(line)
        if warn_match:
            body = [warn_match.group(1)] if warn_match.group(1) else []
            i += 1
            while i < n and lines[i][:1] in (" ", "\t"):
                body.append(lines[i].strip())
                i += 1
            message = _NUMERIC_RE.sub("#", " ".join(body).strip())
            if message not in counts:
                order.append(message)
            counts[message] = counts.get(message, 0) + 1
            continue
        if _FATAL_HEADER_RE.search(line):
            body = [line]
            i += 1
            while i < n and lines[i].strip():
                body.append(lines[i])
                i += 1
            errors.append("\n".join(body))
            continue
        i += 1
    warnings = [LogWarning(message=m, count=counts[m]) for m in order]
    return warnings, errors


def _parse_block_mesh(lines: list[str]) -> list[PhaseSummary]:
    start = next((i for i, line in enumerate(lines) if line.strip() == "Mesh Information"), None)
    if start is None:
        return []
    mesh_lines: list[str] = []
    for line in lines[start:]:
        stripped = line.strip()
        if mesh_lines and not stripped:
            break
        if stripped and set(stripped) == {"-"}:
            continue
        mesh_lines.append(stripped)
    return [PhaseSummary(name="Mesh", lines=mesh_lines)]


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


def _parse_topo_set(lines: list[str]) -> list[PhaseSummary]:
    entries: list[str] = []
    set_type: str | None = None
    set_name: str | None = None
    sources: list[str] = []
    final_size: int | None = None

    def flush() -> None:
        if set_name is None:
            return
        source_part = ", ".join(sources) if sources else "no sources"
        size_part = f"{final_size} entries" if final_size is not None else "unknown size"
        entries.append(f"{set_type} {set_name}: {source_part} → {size_part}")

    for line in lines:
        created = _TOPOSET_CREATED_RE.match(line.strip())
        read_set = _TOPOSET_READSET_RE.match(line.strip())
        if created:
            flush()
            set_type, set_name = created.groups()
            final_size = None
            sources = []
            continue
        if read_set:
            # "Read set" re-checkpoints the current set before the next source is
            # applied; only start a new group if it names a different set (e.g. one
            # created by an earlier, unrelated topoSet run).
            read_type, read_name, size_str = read_set.groups()
            if (read_type, read_name) != (set_type, set_name):
                flush()
                set_type, set_name = read_type, read_name
                sources = []
            final_size = int(size_str)
            continue
        source_match = _TOPOSET_SOURCE_RE.match(line)
        if source_match:
            sources.append(source_match.group(1))
            continue
        size_match = _TOPOSET_SIZE_RE.match(line)
        if size_match and size_match.group(2) == set_name:
            final_size = int(size_match.group(3))
    flush()

    if not entries:
        return []
    return [PhaseSummary(name="Sets", lines=entries)]


def _parse_generic(lines: list[str]) -> list[PhaseSummary]:
    tail = [line for line in lines[-20:] if line.strip()]
    return [PhaseSummary(name="Tail", lines=tail)]


def parse_log(text: str) -> LogSummary:
    lines = text.splitlines()
    header, header_end = _parse_header(lines)
    exec_line = header.get("Exec", "")
    utility = exec_line.split()[0] if exec_line.split() else "unknown"
    body = lines[header_end:]

    warnings, errors = _collect_warnings_and_errors(body)
    finished_ok = not errors
    total_time: str | None = None

    if utility == "blockMesh":
        phases = _parse_block_mesh(body)
    elif utility == "snappyHexMesh":
        phases, snappy_finished_ok, total_time = _parse_snappy_hex_mesh(body)
        finished_ok = snappy_finished_ok and not errors
    elif utility == "topoSet":
        phases = _parse_topo_set(body)
    else:
        phases = _parse_generic(body)

    return LogSummary(
        utility=utility,
        header=header,
        phases=phases,
        warnings=warnings,
        errors=errors,
        finished_ok=finished_ok,
        total_time=total_time,
    )


def format_summary(summary: LogSummary) -> str:
    out: list[str] = []
    out.append(f"Utility: {summary.utility}")
    for key in _HEADER_FIELDS:
        if key in summary.header and key != "Exec":
            out.append(f"{key}: {summary.header[key]}")
    out.append("")

    for phase in summary.phases:
        out.append(f"== {phase.name} ==")
        for line in phase.lines:
            out.append(f"  {line}")
        out.append("")

    if summary.warnings:
        out.append("== Warnings ==")
        for warning in summary.warnings:
            suffix = f" (x{warning.count})" if warning.count > 1 else ""
            out.append(f"  {warning.message}{suffix}")
        out.append("")

    if summary.errors:
        out.append("== Errors ==")
        for error in summary.errors:
            out.append(error)
            out.append("")

    status = "OK" if summary.finished_ok else "FAILED"
    out.append(f"Result: {status}")
    if summary.total_time:
        out.append(f"Total time: {summary.total_time}")

    return "\n".join(out).rstrip() + "\n"
