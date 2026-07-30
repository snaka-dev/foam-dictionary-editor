# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""topoSet log grammar: group Created/Read set/Applying source/size lines by set."""
from __future__ import annotations

import re

from services.log_summary._types import PhaseSummary

_TOPOSET_CREATED_RE = re.compile(r"^Created (\S+) (\S+)\s*$")
_TOPOSET_READSET_RE = re.compile(r"^Read set (\S+) (\S+) size:(\d+)\s*$")
_TOPOSET_SOURCE_RE = re.compile(r"^\s*Applying source (\S+)\s*$")
_TOPOSET_SIZE_RE = re.compile(r"^\s*(\S+) (\S+) now size (\d+)\s*$")


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
