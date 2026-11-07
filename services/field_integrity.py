# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Qt-free: is one OpenFOAM output file whole? Read from its two ends.

Behind the soundness check that Tools > Delete processor* Directories runs on
the case-root copy of everything it is about to delete. A ``reconstructPar``
killed part-way -- one of several run side by side, say -- leaves the field
it was writing cut off. Its size proves nothing (a reconstructed file is
never the sum of its processor parts), but OpenFOAM writes every file the
same way, start to finish::

    FoamFile { … object U; class volVectorField; … }
    dimensions …;
    internalField nonuniform List<vector> 894950 ( …data, ASCII or binary… );
    boundaryField { … }
    // ************************************************************************* //

so three cheap reads tell a whole file from a broken one, without parsing
the data:

- the closing ``// *** //`` line, written last -- a file cut off anywhere,
  ``boundaryField`` included, lacks it;
- the ``FoamFile`` header, whose ``object`` names the file;
- the ``internalField`` count, which must match the mesh -- ``nCells`` for a
  vol field, ``nInternalFaces`` for a surface field, ``nPoints`` for a point
  field. This catches a different failure: a file that is complete but
  stale, left by a run on another mesh (``reconstructPar -newTimes`` skips a
  time that already exists at the root, so nothing overwrites it).

The count sits in plain text even in binary format, right after the header.

A compressed ``.gz`` file's start is cheap to read -- gzip decompresses only
as far as asked -- but its closing line is not: reaching it means
decompressing the whole file. :func:`inspect_file` therefore reads a ``.gz``
only as far as its head unless asked for ``full``; a small one is read whole
anyway, its head being the whole file.
"""
from __future__ import annotations

import dataclasses
import gzip
import os
import re
import zlib
from collections.abc import Callable

_HEAD_BYTES = 16384
_TAIL_BYTES = 4096
_CHUNK = 1 << 20

# The divider IOobject::writeEndDivider writes, in both forks: "// ", a run
# of asterisks, " //". Matched loosely on spacing so a hand-trimmed file is
# not called broken, and only at the very end (trailing whitespace allowed).
_END_RE = re.compile(rb"//\s*\*{10,}\s*//\s*\Z")
_HEADER_RE = re.compile(rb"\bFoamFile\s*\{(.*?)\}", re.DOTALL)
_ENTRY_RE = {
    key: re.compile(rb"\b" + key.encode() + rb"\s+\"?([^;\s\"]+)\"?\s*;")
    for key in ("class", "object")
}
_COUNT_RE = re.compile(rb"\binternalField\s+nonuniform\s+List<\w+>\s*(\d+)")
_MESH_NOTE_RE = {
    key: re.compile(rb"\b" + key.encode() + rb":\s*(\d+)")
    for key in ("nPoints", "nCells", "nFaces", "nInternalFaces")
}


@dataclasses.dataclass(frozen=True)
class MeshSizes:
    n_points: int
    n_cells: int
    n_internal_faces: int

    def expected_count(self, field_class: str) -> int | None:
        """How many internalField values a field of *field_class* holds.

        None for anything not a plain geometric field -- ``volScalarField::
        Internal``, an ``areaScalarField``, a cloud's ``IOField`` -- whose size
        does not come from this mesh's three numbers.
        """
        if "::" in field_class:
            return None
        if field_class.startswith("vol"):
            return self.n_cells
        if field_class.startswith("surface"):
            return self.n_internal_faces
        if field_class.startswith("point"):
            return self.n_points
        return None


def read_mesh_sizes(owner_path: str) -> MeshSizes | None:
    """The sizes in ``owner``'s header note, or None if absent or unreadable."""
    try:
        head = _read_head(owner_path, 4000)[0]
    except (OSError, EOFError, zlib.error):
        return None
    found = {}
    for key, rx in _MESH_NOTE_RE.items():
        m = rx.search(head)
        if m is None and key != "nFaces":
            return None
        if m is not None:
            found[key] = int(m.group(1))
    return MeshSizes(found["nPoints"], found["nCells"], found["nInternalFaces"])


@dataclasses.dataclass(frozen=True)
class FileState:
    """What the two ends of one file say.

    ``readable`` False: it could not be opened, or (compressed) its stream is
    broken -- which for a ``.gz`` is how being cut off shows. ``ended`` is
    None when the end was not read: a large ``.gz`` without ``full``.
    """

    readable: bool
    ended: bool | None = None
    object_name: str | None = None
    field_class: str | None = None
    count: int | None = None

    @property
    def header_ok(self) -> bool:
        return self.object_name is not None

    def names(self, path: str) -> bool:
        """Whether the header's ``object`` is this file's own name."""
        name = os.path.basename(path)
        if name.endswith(".gz"):
            name = name[:-3]
        return self.object_name == name


def is_compressed(path: str) -> bool:
    return path.endswith(".gz")


def _read_head(path: str, size: int) -> tuple[bytes, bool]:
    """The first *size* bytes (decompressed for ``.gz``), and whether that was all.

    A ``.gz`` cut off inside those bytes raises EOFError; one whose CRC is
    wrong raises a BadGzipFile (an OSError) when its end is reached.
    """
    if is_compressed(path):
        with gzip.open(path, "rb") as f:
            head = f.read(size)
            whole = len(head) < size
    else:
        with open(path, "rb") as f:
            head = f.read(size)
            whole = len(head) < size
    return head, whole


def _read_tail(path: str) -> bytes:
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        f.seek(max(0, f.tell() - _TAIL_BYTES))
        return f.read()


def _gz_tail(
    path: str, progress: Callable[[int], None] | None, cancelled: Callable[[], bool] | None
) -> bytes | None:
    """Decompress *path* whole and return its last bytes; None if cancelled.

    ``progress`` gets compressed bytes consumed since its last call, so a
    caller can show progress over many files. Raises like :func:`_read_head`
    on a broken stream.
    """
    tail = b""
    with open(path, "rb") as raw, gzip.GzipFile(fileobj=raw) as f:
        seen = 0
        while True:
            if cancelled is not None and cancelled():
                return None
            chunk = f.read(_CHUNK)
            if not chunk:
                break
            tail = (tail + chunk)[-_TAIL_BYTES:]
            if progress is not None:
                pos = raw.tell()
                progress(pos - seen)
                seen = pos
    return tail


def has_end_divider(data: bytes) -> bool:
    return _END_RE.search(data[-_TAIL_BYTES:]) is not None


def _parse_head(head: bytes) -> tuple[str | None, str | None, int | None]:
    m = _HEADER_RE.search(head)
    if m is None:
        return None, None, None
    block = m.group(1)
    values = {}
    for key, rx in _ENTRY_RE.items():
        e = rx.search(block)
        values[key] = e.group(1).decode("latin-1") if e else None
    count_m = _COUNT_RE.search(head, m.end())
    count = int(count_m.group(1)) if count_m else None
    return values["object"], values["class"], count


class Cancelled(Exception):
    """Raised by :func:`inspect_file` when ``cancelled()`` turned true."""


def inspect_file(
    path: str,
    *,
    full: bool = False,
    progress: Callable[[int], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> FileState:
    """Read *path*'s head and tail -- see the module docstring.

    ``full`` decompresses a ``.gz`` to its end; without it a ``.gz`` larger
    than the head is reported with ``ended`` None. ``progress``/``cancelled``
    matter only for that full read.
    """
    try:
        head, whole = _read_head(path, _HEAD_BYTES)
    except (OSError, EOFError, zlib.error):
        return FileState(readable=False)
    obj, cls, count = _parse_head(head)
    try:
        if whole:
            tail: bytes | None = head
        elif not is_compressed(path):
            tail = _read_tail(path)
        elif full:
            tail = _gz_tail(path, progress, cancelled)
            if tail is None:
                raise Cancelled
        else:
            tail = None
    except (OSError, EOFError, zlib.error):
        return FileState(False, None, obj, cls, count)
    ended = None if tail is None else has_end_divider(tail)
    return FileState(True, ended, obj, cls, count)
