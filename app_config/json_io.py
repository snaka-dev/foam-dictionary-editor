# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import json
import os
import secrets
import stat
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


def atomic_write_text(path: Path, text: str, *, new_mode: int = 0o666) -> None:
    """Write text to path atomically, creating the parent directory if needed.

    Writes to a randomly named sibling temp file and then ``os.replace``s it
    over the target, so a failed write can never truncate an existing file.

    The temp file is created exclusively (``O_CREAT | O_EXCL``, and
    ``O_NOFOLLOW`` where the platform has it), under a name nobody can
    predict. A fixed name such as ``<name>.tmp`` let a case ship a symlink
    there, and the write then went through it to whatever file it named.
    ``os.replace`` swaps the directory entry, so a symlink at the final name
    is replaced, never written through.

    Permissions: an existing regular file keeps its mode, read with
    ``lstat`` so a symlink at the final name says nothing about it. A new
    file gets *new_mode* less the process umask, which the kernel applies at
    creation -- the per-user config passes ``0o600``; a case's config keeps
    the umask default so a group-shared case stays shared.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    keep_mode: int | None = None
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        pass
    else:
        if stat.S_ISREG(st.st_mode):
            keep_mode = stat.S_IMODE(st.st_mode)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    for _ in range(_TEMP_ATTEMPTS):
        tmp = path.with_name(f"{path.name}.{secrets.token_hex(8)}.tmp")
        try:
            fd = os.open(tmp, flags, new_mode)
            break
        except FileExistsError:
            continue
    else:
        raise FileExistsError(f"no free temporary name beside {path}")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            if keep_mode is not None and hasattr(os, "fchmod"):
                os.fchmod(f.fileno(), keep_mode)
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# Random 64-bit names: a clash is already unlikely, so a handful of tries is plenty.
_TEMP_ATTEMPTS = 16


def save_json(path: Path, data: dict, *, new_mode: int = 0o666) -> None:
    """Write data as indented JSON atomically (see atomic_write_text)."""
    atomic_write_text(
        path,
        json.dumps(data, indent=JSON_INDENT, ensure_ascii=JSON_ENSURE_ASCII),
        new_mode=new_mode,
    )
