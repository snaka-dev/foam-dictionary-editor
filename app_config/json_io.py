# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import json
import os
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


def atomic_write_text(path: Path, text: str) -> None:
    """Write text to path atomically, creating the parent directory if needed.

    Writes to a sibling ``<name>.tmp`` file and then ``os.replace``s it over
    the target, so a failed write can never truncate an existing file. A plain
    named temp file (not ``tempfile.mkstemp``) is used deliberately: mkstemp
    creates 0600 files, which would silently tighten the permissions of
    umask-default config files. Concurrent writers are not a concern here.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def save_json(path: Path, data: dict) -> None:
    """Write data as indented JSON atomically (see atomic_write_text)."""
    atomic_write_text(
        path,
        json.dumps(data, indent=JSON_INDENT, ensure_ascii=JSON_ENSURE_ASCII),
    )
