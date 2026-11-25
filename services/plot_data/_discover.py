# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Find the plottable files of a case and load them as tables.

A *source* is one logical data set, whatever number of files holds it:

- ``series``: a time series a function object appends to, e.g.
  ``postProcessing/forces/0/force.dat``. A restarted run starts a new
  ``<startTime>/`` directory (and OpenCFD a ``force_<time>.dat`` beside an
  existing file); all of them are segments of one source, stitched in
  start-time order.
- ``profile``: a sampled set (``.xy``/``.csv``/``.raw``), one file per
  written time. One time is plotted at once.
- ``residuals``: a solver log, ``log.<solver>``.

``Source.key`` is the case-relative path with the time directories taken
out (``postProcessing/forces/force.dat``), so the same data set in another
case has the same key -- what the Plot Results window's "same in all cases"
matches on.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from services.plot_data._reader import Table, read_log_residuals, read_table, stitch

SourceKind = Literal["series", "profile", "residuals"]

POST_PROCESSING = "postProcessing"
PROFILE_SUFFIXES = (".xy", ".csv", ".raw")
# Output no table reader can use: geometry, images, ParaView series files.
_SKIP_SUFFIXES = {
    ".vtp", ".vtk", ".vtu", ".vtm", ".series", ".stl", ".obj", ".foam",
    ".png", ".jpg", ".jpeg", ".ensight", ".case", ".geo", ".x3d", ".nas",
    ".ply", ".h5", ".hdf5", ".bin",
}
# A directory tree this deep below postProcessing/ is not a function object.
_MAX_DEPTH = 4
# Files bigger than this are listed but not sniffed for a table shape.
_SNIFF_BYTES = 4096
_RESIDUAL_MARK = b"Initial residual"


@dataclass(frozen=True)
class Source:
    case_dir: str
    key: str
    kind: SourceKind
    # series: segments in start-time order. profile: one file per time.
    # residuals: the log.
    paths: tuple[str, ...]
    # profile only: the time each path belongs to, ascending.
    times: tuple[str, ...] = ()

    @property
    def title(self) -> str:
        """The key without the ``postProcessing/`` prefix, for display."""
        prefix = POST_PROCESSING + "/"
        return self.key[len(prefix):] if self.key.startswith(prefix) else self.key


def _time_value(name: str) -> float | None:
    try:
        return float(name)
    except ValueError:
        return None


def _restart_base(name: str, time_name: str) -> str:
    """``force_0.5.dat`` in time dir ``0.5`` is a second segment of ``force.dat``.

    OpenCFD's ``writeFile::newFileAtTime`` appends ``_<time>`` before the
    extension when the file already exists (Foundation 7's ``logFiles`` does
    the same).
    """
    suffix = "_" + time_name
    if name.endswith(suffix) and len(name) > len(suffix):
        return name[: -len(suffix)]
    ext = Path(name).suffix
    stem = name[: -len(ext)] if ext else name
    if ext and stem.endswith(suffix) and len(stem) > len(suffix):
        return stem[: -len(suffix)] + ext
    return name


def _looks_tabular(path: Path) -> bool:
    """Cheap sniff: a line of the first 4 KB starts with a number."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(_SNIFF_BYTES)
    except OSError:
        return False
    if head[:2] == b"\x1f\x8b":
        return True
    if b"\x00" in head:
        return False
    for line in head.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return bool(re.match(r"^[-+]?(\d|\.\d)", line))
    return False


def _function_dirs(root: Path):
    """Yield directories that hold time directories, up to _MAX_DEPTH deep."""
    stack = [(root, 0)]
    while stack:
        d, depth = stack.pop()
        try:
            entries = sorted(os.scandir(d), key=lambda e: e.name)
        except OSError:
            continue
        subdirs = [e for e in entries if e.is_dir() and not e.name.startswith(".")]
        if any(_time_value(e.name) is not None for e in subdirs):
            yield Path(d), [e for e in subdirs if _time_value(e.name) is not None]
        if depth < _MAX_DEPTH:
            stack += [
                (Path(e.path), depth + 1) for e in reversed(subdirs)
                if _time_value(e.name) is None
            ]


def find_sources(case_dir: str | os.PathLike[str]) -> list[Source]:
    """Every plottable data set of *case_dir*, function objects first."""
    case = Path(case_dir)
    out: list[Source] = []
    pp = case / POST_PROCESSING
    if pp.is_dir():
        for fo_dir, time_dirs in _function_dirs(pp):
            out += _sources_in(case, fo_dir, time_dirs)
    out.sort(key=lambda s: s.key)
    out += _log_sources(case)
    return out


def _sources_in(case: Path, fo_dir: Path, time_dirs: list[os.DirEntry]) -> list[Source]:
    time_dirs = sorted(time_dirs, key=lambda e: _time_value(e.name) or 0.0)
    # base file name -> [(time value, time name, path)]
    found: dict[str, list[tuple[float, str, str]]] = {}
    for td in time_dirs:
        tval = _time_value(td.name) or 0.0
        try:
            files = [e for e in os.scandir(td.path) if e.is_file()]
        except OSError:
            continue
        for f in sorted(files, key=lambda e: e.name):
            name = f.name
            if name.startswith(".") or Path(name).suffix.lower() in _SKIP_SUFFIXES:
                continue
            base = name if name.endswith(PROFILE_SUFFIXES) else _restart_base(name, td.name)
            # A restart duplicate sorts after the file it continues.
            order = tval + (1e-12 if base != name else 0.0)
            found.setdefault(base, []).append((order, td.name, f.path))
    rel_dir = fo_dir.relative_to(case).as_posix()
    sources = []
    for base, entries in sorted(found.items()):
        entries.sort()
        kind: SourceKind = "profile" if base.endswith(PROFILE_SUFFIXES) else "series"
        if not _looks_tabular(Path(entries[-1][2])):
            continue
        sources.append(Source(
            case_dir=str(case),
            key=f"{rel_dir}/{base}",
            kind=kind,
            paths=tuple(e[2] for e in entries),
            times=tuple(e[1] for e in entries) if kind == "profile" else (),
        ))
    return sources


def _log_sources(case: Path) -> list[Source]:
    out: list[Source] = []
    try:
        names = sorted(e.name for e in os.scandir(case) if e.is_file())
    except OSError:
        return out
    for name in names:
        if not name.startswith("log."):
            continue
        path = case / name
        if not _has_residuals(path):
            continue
        out.append(Source(case_dir=str(case), key=name, kind="residuals", paths=(str(path),)))
    return out


def _has_residuals(path: Path) -> bool:
    """Whether a log records a time loop's residuals near its start.

    Judged by content, not name: ``log.fluentMeshToFoam`` is no solver,
    and ``log.foamRun`` or a user's own solver is one. snappyHexMesh's
    smoothing solves report residuals too but have no ``Time =`` steps,
    which :func:`read_log_residuals` needs, so the steps are checked too.
    """
    try:
        with open(path, "rb") as fh:
            head = fh.read(256 * 1024)
    except OSError:
        return False
    return _RESIDUAL_MARK in head and re.search(rb"(?m)^Time = ", head) is not None


# ── loading, with a cache ──────────────────────────────────────────────────

_cache: dict[str, tuple[tuple[int, int], Table]] = {}


def _stamp(path: str) -> tuple[int, int]:
    st = os.stat(path)
    return st.st_mtime_ns, st.st_size


def _cached(path: str, reader) -> Table:
    stamp = _stamp(path)
    hit = _cache.get(path)
    if hit is not None and hit[0] == stamp:
        return hit[1]
    table = reader(path)
    _cache[path] = (stamp, table)
    return table


def clear_cache() -> None:
    _cache.clear()


def load_source(source: Source, time: str | None = None) -> Table:
    """The table of *source*; for a profile, at *time* (default: the latest)."""
    if source.kind == "residuals":
        return _cached(source.paths[0], read_log_residuals)
    if source.kind == "profile":
        return _cached(profile_path(source, time), read_table)
    return stitch([_cached(p, read_table) for p in source.paths])


def profile_path(source: Source, time: str | None) -> str:
    """The file of *source* written at *time*, or the latest one."""
    if time is not None and time in source.times:
        return source.paths[source.times.index(time)]
    return source.paths[-1]


def source_for_key(case_dir: str, key: str, sources: list[Source] | None = None) -> Source | None:
    for s in sources if sources is not None else find_sources(case_dir):
        if s.key == key:
            return s
    return None
