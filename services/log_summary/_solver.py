# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Solver-log grammar: time-loop steps, residuals, Courant number, timing."""
from __future__ import annotations

import re

from services.log_summary._types import PhaseSummary

# Solver time loops. Newer OpenFOAM.com versions append a unit ("Time = 0.005s").
_SOLVER_TIME_RE = re.compile(r"^Time = (\S+?)s?\s*$")
_SOLVER_SOLVING_RE = re.compile(
    r"Solving for ([^,]+), Initial residual = (\S+), "
    r"Final residual = (\S+), No Iterations (\d+)"
)
_SOLVER_COURANT_RE = re.compile(r"^([\w ]*Courant Number) mean: (\S+) max: (\S+)")
_SOLVER_EXEC_TIME_RE = re.compile(r"^ExecutionTime = (\S+) s\s+ClockTime = (\S+) s")
_SOLVER_CONTINUITY_RE = re.compile(
    r"^time step continuity errors :.*cumulative = (\S+)\s*$"
)
_SOLVER_CONVERGED_RE = re.compile(r"solution converged in \d+ iterations")
_SOLVER_END_RE = re.compile(r"^End\.?\s*$")


def _looks_like_solver(lines: list[str]) -> bool:
    """True for a time-loop solver log: has "Time = ..." steps and residual lines.

    The two conditions together keep utilities out: checkMesh/decomposePar print
    "Time = 0" but never "Solving for"; snappyHexMesh is dispatched by name
    before this check runs.
    """
    has_time = any(_SOLVER_TIME_RE.match(line.strip()) for line in lines)
    has_solve = any(_SOLVER_SOLVING_RE.search(line) for line in lines)
    return has_time and has_solve


def _parse_solver(lines: list[str]) -> tuple[list[PhaseSummary], bool, str | None]:
    """Summarise a solver time loop: step range, timing, last-step residuals."""
    times: list[str] = []
    # field -> "initial X, final Y (N iter)", insertion-ordered, last occurrence wins
    residuals: dict[str, str] = {}
    courant: dict[str, str] = {}
    exec_time: str | None = None
    continuity: str | None = None
    converged: str | None = None
    end_seen = False

    for raw in lines:
        line = raw.strip()
        time_match = _SOLVER_TIME_RE.match(line)
        if time_match:
            times.append(time_match.group(1))
            continue
        solve_match = _SOLVER_SOLVING_RE.search(line)
        if solve_match:
            field, initial, final, iters = solve_match.groups()
            residuals[field.strip()] = (
                f"initial {initial}, final {final} ({iters} iter)"
            )
            continue
        courant_match = _SOLVER_COURANT_RE.match(line)
        if courant_match:
            name, mean, cmax = courant_match.groups()
            courant[name.strip()] = f"mean {mean}, max {cmax}"
            continue
        exec_match = _SOLVER_EXEC_TIME_RE.match(line)
        if exec_match:
            exec_time = f"{exec_match.group(1)} s (clock {exec_match.group(2)} s)"
            continue
        continuity_match = _SOLVER_CONTINUITY_RE.match(line)
        if continuity_match:
            continuity = continuity_match.group(1)
            continue
        if _SOLVER_CONVERGED_RE.search(line):
            converged = line
            continue
        if _SOLVER_END_RE.match(line):
            end_seen = True

    run_lines: list[str] = []
    if times:
        if len(times) > 1:
            run_lines.append(f"Time steps: {len(times)} (Time = {times[0]} → {times[-1]})")
        else:
            run_lines.append(f"Time steps: 1 (Time = {times[0]})")
    if exec_time:
        run_lines.append(f"ExecutionTime: {exec_time}")
    if converged:
        run_lines.append(converged)

    residual_lines: list[str] = []
    for name, value in courant.items():
        residual_lines.append(f"{name}: {value}")
    for field, value in residuals.items():
        residual_lines.append(f"{field}: {value}")
    if continuity is not None:
        residual_lines.append(f"Cumulative continuity error: {continuity}")

    phases: list[PhaseSummary] = []
    if run_lines:
        phases.append(PhaseSummary(name="Run", lines=run_lines))
    if residual_lines:
        phases.append(PhaseSummary(name="Residuals (last step)", lines=residual_lines))
    finished_ok = end_seen or converged is not None
    return phases, finished_ok, exec_time
