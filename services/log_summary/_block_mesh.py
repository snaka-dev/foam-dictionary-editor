# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""blockMesh log grammar: locate the "Mesh Information" block and pass it through."""
from __future__ import annotations

from services.log_summary._types import PhaseSummary


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
