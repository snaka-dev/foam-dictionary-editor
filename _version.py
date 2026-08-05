# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Single source of truth for the application version.

Bump ``__version__`` on each release (alongside the matching ``vX.Y.Z`` git
tag). ``get_version()`` returns that number for installed copies, and enriches
it with a short dev suffix (commits-past-tag + commit hash, ``*`` if the tree is
dirty) when running from a git checkout so bug reports can pinpoint the build.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

__version__ = "1.12.0"

_REPO_DIR = Path(__file__).resolve().parent


def _git_describe() -> str | None:
    """Return ``git describe --tags --dirty`` output, or None if unavailable."""
    if not (_REPO_DIR / ".git").exists():
        return None
    try:
        out = subprocess.run(
            ["git", "describe", "--tags", "--always", "--dirty=*"],
            cwd=_REPO_DIR,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    described = out.stdout.strip()
    return described or None


def get_version() -> str:
    """Return a human-readable version string for display (About dialog, CLI)."""
    described = _git_describe()
    if described is None:
        return __version__

    # "v1.7.0-3-g e75192d" (optionally "*"-suffixed when dirty) → ahead of tag.
    m = re.match(
        r"v?(?P<tag>.+?)-(?P<n>\d+)-g(?P<sha>[0-9a-f]+)(?P<dirty>\*?)$",
        described,
    )
    if m:
        return f"{m['tag']} (dev+{m['n']}, g{m['sha']}{m['dirty']})"

    # Exact tag, optionally dirty: "v1.7.0" / "v1.7.0*".
    m = re.match(r"v?(?P<tag>.+?)(?P<dirty>\*?)$", described)
    if m and m["tag"] and not re.fullmatch(r"[0-9a-f]{7,}", m["tag"]):
        dirty = " (dirty)" if m["dirty"] else ""
        return f"{m['tag']}{dirty}"

    # No tags reachable — bare commit hash from "--always".
    return f"{__version__} (g{described})"
