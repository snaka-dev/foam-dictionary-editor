# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Has a file changed on disk since FoDE read or wrote it?

The case-directory watcher sees entries added and removed, never a file
rewritten in place, so when another program (``foamDictionary -set``, ``sed``,
another editor, a script in the terminal) rewrites a file FoDE holds a buffer
of, nothing notices -- and a later save would silently overwrite the change.
FoDE records a :class:`DiskStamp` whenever it reads a file into a buffer or
writes one out, and asks :func:`changed_since` before writing again.

A stamp is the file's ``(st_mtime_ns, st_size)`` plus a digest of the text
FoDE read or wrote. The stat pair is the cheap test; only when it differs is
the file read and its text compared, so a ``touch`` or a rewrite with the same
content is not reported as a change.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass

from foam.utils import read_foam_file

UNCHANGED = ""
CHANGED = "changed"
DELETED = "deleted"


@dataclass(frozen=True)
class DiskStamp:
    mtime_ns: int
    size: int
    digest: str


def _digest(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", "surrogatepass")).hexdigest()


def take_stamp(path: str, text: str) -> DiskStamp | None:
    """The stamp of *path* as it is now, holding *text*; None if it cannot be stat'ed."""
    try:
        st = os.stat(path)
    except OSError:
        return None
    return DiskStamp(st.st_mtime_ns, st.st_size, _digest(text))


def changed_since(path: str, stamp: DiskStamp) -> str:
    """``UNCHANGED``, ``CHANGED`` or ``DELETED`` relative to *stamp*.

    An unreadable file that still exists counts as unchanged: the write that
    follows will report its own error, and a question FoDE cannot back up
    would only be noise.
    """
    try:
        st = os.stat(path)
    except FileNotFoundError:
        return DELETED
    except OSError:
        return UNCHANGED
    if (st.st_mtime_ns, st.st_size) == (stamp.mtime_ns, stamp.size):
        return UNCHANGED
    try:
        text = read_foam_file(path)
    except OSError:
        return UNCHANGED
    return CHANGED if _digest(text) != stamp.digest else UNCHANGED
