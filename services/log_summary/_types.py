# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Shared dataclasses and generic (utility-agnostic) log parsing helpers.

Header-field extraction and FOAM Warning/FATAL ERROR collection apply to
every utility's log, regardless of which grammar module (``_block_mesh``,
``_snappy_hex_mesh``, ``_topo_set``, ``_solver``, ``_generic``) parses the
rest of the body.
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
