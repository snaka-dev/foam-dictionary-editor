# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from dataclasses import dataclass

FOUNDATION_V13 = "Foundation v13"
OPENCFD_V2312  = "OpenCFD v2312"
OPENCFD_V2512  = "OpenCFD v2512"
OPENCFD_SERIES = "OpenCFD v2312/v2512 series"


@dataclass(frozen=True)
class ChoiceItem:
    value: str
    description: str
    supported_in: tuple[str, ...] = ()
    note: str = ""


@dataclass(frozen=True)
class KeySchema:
    key: str
    label: str
    description: str
    supported_in: tuple[str, ...] = ()
    note: str = ""
    choices: tuple[ChoiceItem, ...] = ()


def _versions_text(items: tuple[str, ...]) -> str:
    return ", ".join(items)

