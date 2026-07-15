# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import json
from pathlib import Path

from app_config.constants import JSON_ENSURE_ASCII, JSON_INDENT


def load_json(path: Path) -> dict | None:
    """Return the parsed JSON object at path, or None if missing/corrupt."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def save_json(path: Path, data: dict) -> None:
    """Write data as indented JSON, creating the parent directory if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=JSON_INDENT, ensure_ascii=JSON_ENSURE_ASCII),
        encoding="utf-8",
    )
