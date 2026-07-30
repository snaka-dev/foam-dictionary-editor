# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Fallback grammar for logs not otherwise recognised: just show the tail."""
from __future__ import annotations

from services.log_summary._types import PhaseSummary


def _parse_generic(lines: list[str]) -> list[PhaseSummary]:
    tail = [line for line in lines[-20:] if line.strip()]
    return [PhaseSummary(name="Tail", lines=tail)]
