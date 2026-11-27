# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Single source of truth for the application version.

Bump ``__version__`` on each release (alongside the matching ``vX.Y.Z`` git
tag). ``get_version()`` always reports that number, and in a git checkout adds a
short suffix (commits past the release + commit hash, ``*`` if the tree is
dirty) so bug reports can pinpoint the build.

The number never comes from the tag. A clone whose git client was set not to
fetch tags still had ``v1.15.1`` as its newest, and showed
``1.15.1 (dev+117, …)`` for 1.21.1 code. The commit count is shown only when the
tag ``git describe`` found is this version's own, since a count from another tag
is just as wrong; otherwise the hash alone identifies the build.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

__version__ = "1.22.0"

_REPO_DIR = Path(__file__).resolve().parent


def _git_describe() -> str | None:
    """Return ``git describe --tags --long --always --dirty=*`` output, or None.

    ``--long`` keeps the hash even on the tagged commit itself ("v1.21.1-0-g…"),
    so a tag that turns out not to be this version's still leaves a hash to show.
    """
    if not (_REPO_DIR / ".git").exists():
        return None
    try:
        out = subprocess.run(
            ["git", "describe", "--tags", "--long", "--always", "--dirty=*"],
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

    # "v1.21.1-3-ge75192d", "*"-suffixed when dirty.
    m = re.match(
        r"v?(?P<tag>.+?)-(?P<n>\d+)-g(?P<sha>[0-9a-f]+)(?P<dirty>\*?)$",
        described,
    )
    if m and m["tag"] == __version__:
        if m["n"] == "0":
            return f"{__version__} (dirty)" if m["dirty"] else __version__
        return f"{__version__} (dev+{m['n']}, g{m['sha']}{m['dirty']})"
    if m:
        # Another version's tag (tags not fetched, or a stale one): its number
        # and commit count are both wrong for this code, so keep only the hash.
        return f"{__version__} (g{m['sha']}{m['dirty']})"

    # No tags reachable: "--always" gives a bare hash, "*"-suffixed when dirty.
    return f"{__version__} (g{described})"
