# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Condense OpenFOAM run logs (blockMesh/snappyHexMesh/topoSet stdout, tee'd to
``log.*`` files, and solver logs written by Allrun's ``runApplication``) into a
short, structured report. Solver logs are recognised by shape ("Time = ..."
steps plus "Solving for ..." residual lines) rather than by executable name.

This is unrelated to ``foam/``'s dictionary-tree extractors: it parses solver/
utility *log text*, not ``FoamNode`` trees.

Split into a package: ``_types.py`` holds the dataclasses and generic header/
warning/error parsing; one module per grammar (``_block_mesh``,
``_snappy_hex_mesh``, ``_topo_set``, ``_solver``, ``_generic``); this file
holds only utility dispatch (``parse_log``) and rendering (``format_summary``).
"""
from __future__ import annotations

from services.log_summary._block_mesh import _parse_block_mesh
from services.log_summary._generic import _parse_generic
from services.log_summary._snappy_hex_mesh import _parse_snappy_hex_mesh
from services.log_summary._solver import _looks_like_solver, _parse_solver
from services.log_summary._topo_set import _parse_topo_set
from services.log_summary._types import (
    _HEADER_FIELDS,
    LogSummary,
    LogWarning,
    PhaseSummary,
    _collect_warnings_and_errors,
    _parse_header,
)

__all__ = [
    "LogSummary",
    "LogWarning",
    "PhaseSummary",
    "parse_log",
    "format_summary",
]


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
    elif _looks_like_solver(body):
        phases, solver_finished_ok, total_time = _parse_solver(body)
        finished_ok = solver_finished_ok and not errors
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
