# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Suffixed variants of a known dictionary: ``decomposeParDict.4``, ``controlDict.orig``.

Tutorials keep alternatives of a dictionary beside it under a suffix -- one
``decomposeParDict.N`` per processor count, ``refineMeshDict.tier6`` run with
``-dict``, ``fvSchemes.template`` a script copies into place. OpenFOAM reads
such a file only when a command names it or a script copies it over the real
one, but it is a complete dictionary of the same kind, so FoDE lists it (dimmed)
and gives it the base dictionary's schema.

The name alone is not enough to tell. A plain prefix match takes
``gravitationalProperties`` for a variant of ``g`` and ``sampleDict`` for one
of ``sample``, so a separator must follow the base name (``.``, ``-``, ``_`` or
a digit). Even then a copy-pasted header can claim to be something else
(``setAlphaFieldDict.liquid`` declares ``object setFieldsDict``), so the file's
own ``FoamFile`` header must agree: its ``object`` is the base name or the
file's own name. A file with no header is an ``#include`` fragment, not a
variant -- and so is one whose header names itself but which a sibling
``#include``s: foamyHexMesh's ``meshDict.geometry`` is spliced into
``foamyHexMeshDict``, and the file list already shows it as an included row.
Measured over the thirteen local tutorial trees in DEVELOPER.md's "Suffixed
variants".

Qt-free and services-free: the caller passes the base names it knows
(``services/case_loader`` its listed dictionaries, ``schemas/registry`` the
files it has schemas for).
"""
from __future__ import annotations

import os
import re
from collections.abc import Iterable

_SEPARATOR_RE = re.compile(r"[._-]|\d")
_HEADER_RE = re.compile(r"\bFoamFile\s*\{(?P<body>[^{}]*)\}", re.S)
_OBJECT_RE = re.compile(r"(?<![\w.])object\s+\"?(?P<name>[^\s;\"]+)\"?\s*;")
# A header sits at the top; nothing past this is read.
_HEAD_BYTES = 4096

# path -> (mtime_ns, size, header object or None)
_object_cache: dict[str, tuple[int, int, str | None]] = {}
# directory -> (its files' (name, mtime_ns, size), names they #include). Keyed
# on the files themselves, not the directory's mtime, which an in-place edit
# does not move. Siblings are read only for a file whose header names itself.
_include_cache: dict[str, tuple[frozenset[tuple[str, int, int]], frozenset[str]]] = {}
_INCLUDE_RE = re.compile(r"^\s*#(?:s?include|includeIfPresent)\s+\"([^\"]+)\"", re.M)
# An included fragment is small; a sibling is not read past this.
_SIBLING_BYTES = 256 * 1024


def clear_variant_cache() -> None:
    """Drop the header memo (on a case switch, and in tests)."""
    _object_cache.clear()
    _include_cache.clear()


def suffixed_base(name: str, bases: Iterable[str]) -> str | None:
    """The longest of *bases* that *name* extends past a separator, or None."""
    best: str | None = None
    for base in bases:
        if (
            name != base
            and name.startswith(base)
            and _SEPARATOR_RE.match(name, len(base))
            and (best is None or len(base) > len(best))
        ):
            best = base
    return best


def header_object(path: str) -> str | None:
    """The ``object`` entry of *path*'s ``FoamFile`` header, or None."""
    try:
        st = os.stat(path)
    except OSError:
        return None
    cached = _object_cache.get(path)
    if cached is not None and cached[:2] == (st.st_mtime_ns, st.st_size):
        return cached[2]
    found: str | None = None
    try:
        with open(path, "rb") as f:
            head = f.read(_HEAD_BYTES).decode("utf-8", "replace")
    except OSError:
        head = ""
    header = _HEADER_RE.search(head)
    if header is not None:
        obj = _OBJECT_RE.search(header.group("body"))
        if obj is not None:
            found = obj.group("name")
    _object_cache[path] = (st.st_mtime_ns, st.st_size, found)
    return found


def variant_base(path: str, bases: Iterable[str]) -> str | None:
    """The dictionary *path* is a suffixed variant of, or None.

    Both tests must pass: the name extends a base past a separator, and the
    file's header ``object`` is that base or the file's own name.
    """
    name = os.path.basename(path)
    base = suffixed_base(name, bases)
    if base is None:
        return None
    obj = header_object(path)
    if obj == base:
        return base
    if obj == name and name not in _included_by_siblings(os.path.dirname(path)):
        return base
    return None


def _included_by_siblings(directory: str) -> frozenset[str]:
    """Base names the files in *directory* pull in with ``#include``."""
    try:
        entries = list(os.scandir(directory))
    except OSError:
        return frozenset()
    files = []
    for entry in entries:
        try:
            if entry.is_file():
                st = entry.stat()
                files.append((entry.name, st.st_mtime_ns, st.st_size))
        except OSError:
            continue
    key = frozenset(files)
    cached = _include_cache.get(directory)
    if cached is not None and cached[0] == key:
        return cached[1]
    names: set[str] = set()
    for name, _mtime, _size in files:
        try:
            with open(os.path.join(directory, name), "rb") as f:
                text = f.read(_SIBLING_BYTES).decode("utf-8", "replace")
        except OSError:
            continue
        names.update(os.path.basename(m) for m in _INCLUDE_RE.findall(text))
    found = frozenset(names)
    _include_cache[directory] = (key, found)
    return found
