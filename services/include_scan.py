# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Find the files a case's dictionaries pull in with ``#include``.

The disk-touching half of include support: ``foam/include_resolver.py`` is pure
text->path logic, this module supplies it with an OpenFOAM ``etc`` search path
and runs it over a case.

The scan is a **regular-expression line scan, not a parse**. It runs on every
file-list refresh, and refresh is driven by a 400 ms-debounced
``QFileSystemWatcher``, so it is built to be near-free: it never walks
directories (it only reads the paths ``services/case_loader.list_case_files``
already returned), it rejects most files with a substring test before any
regex, and it memoises per file on ``(mtime, size)``.

Resolution is **one level deep and not transitive** -- an included file is not
itself scanned. See DEVELOPER.md's "Include resolution" section.
"""
from __future__ import annotations

import dataclasses
import re
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path

from app_config import get_app_config
from app_config.foam_env import foam_env_dirs
from foam.include_resolver import (
    IncludeRef,
    ResolvedInclude,
    parse_include_directive,
    resolve_include,
)
from foam.utils import is_log_filename, is_script_path, read_foam_file
from services.example_search import discover_installations

# Same directive set as foam/include_resolver's own regex; every match is handed
# to parse_include_directive, so the C++-header rejection applies here too.
_DIRECTIVE_RE = re.compile(
    r"^[ \t]*#(?:s?include|includeIfPresent|includeEtc|includeFunc)\b.*$", re.M
)

# Cheap substring gate: a file without either of these cannot hold a match, and
# rejecting it costs one C-speed scan instead of a regex pass.
_SUBSTRING_GATE = ("#include", "#sinclude")

# A dictionary this large is a mesh or data file, not something to scan.
_MAX_SCAN_BYTES = 512 * 1024

# path -> (mtime, size, refs). Bounded by clear_scan_cache() on a case switch.
_scan_cache: dict[str, tuple[float, int, tuple[tuple[IncludeRef, int, str], ...]]] = {}

# path -> realpath. `Path.resolve()` walks every component for symlinks, which
# dominated the refresh cost before this was memoised; a re-pointed symlink is
# picked up on the next case switch, when clear_scan_cache() drops both caches.
_realpath_cache: dict[str, str] = {}


@dataclasses.dataclass(frozen=True)
class IncludeHit:
    """One include directive found in a case file, and what it resolved to."""

    ref: IncludeRef
    source_file: Path
    line: int  # 1-based, for reporting
    resolved: ResolvedInclude
    # The directive exactly as written, which is also what the parser stores as
    # a `directive_entry`'s value -- so this is the key the tree can look up.
    text: str


@lru_cache(maxsize=1)
def foam_etc_dirs() -> tuple[Path, ...]:
    """Return the OpenFOAM ``etc`` directories to search, most specific first.

    Mirrors where OpenFOAM itself looks, then falls back to the app's own
    installation discovery. Returns an empty tuple when no installation can be
    found at all -- ``#includeEtc``/``#includeFunc`` then resolve to the
    ``no_installation`` status rather than a bare "not found".
    """
    roots: list[Path] = []

    def _add(path: Path | None) -> None:
        if path is None:
            return
        expanded = path.expanduser()
        if expanded.is_dir() and expanded not in roots:
            roots.append(expanded)

    env_dirs = foam_env_dirs()
    # OpenFOAM's own first search location: a per-user override of etc files.
    if env_dirs.version:
        _add(Path.home() / ".OpenFOAM" / env_dirs.version)
    # The installation the user picked in the shared InstallationSelector.
    user_dir = get_app_config().get_openfoam_dir()
    if user_dir:
        _add(Path(user_dir) / "etc")
    _add(env_dirs.etc_dir)
    for installation in discover_installations():
        _add(installation.root / "etc")
    return tuple(roots)


def clear_foam_etc_cache() -> None:
    """Drop the cached etc search path (after an installation setting change)."""
    foam_etc_dirs.cache_clear()


def clear_scan_cache() -> None:
    """Drop the per-file scan and realpath memos (on a case switch, and in tests)."""
    _scan_cache.clear()
    _realpath_cache.clear()


def scan_includes(
    case_dir: str,
    paths: Sequence[str],
    *,
    etc_dirs: Sequence[Path] | None = None,
) -> list[IncludeHit]:
    """Return every resolvable include directive found in ``paths``.

    ``paths`` are the case's already-listed files; nothing else is read and no
    directory is walked, which is what keeps this cheap enough to run on every
    file-list refresh.
    """
    if etc_dirs is None:
        etc_dirs = foam_etc_dirs()
    case_path = Path(case_dir)

    # The same reference recurs across a case (`setConstraintTypes` appears in
    # every field file), and resolving one probes the disk. Only the directory
    # of the including file affects the outcome, so memoise on that.
    seen: dict[tuple[IncludeRef, Path], ResolvedInclude] = {}

    hits: list[IncludeHit] = []
    for path_str in paths:
        source = Path(path_str)
        for ref, line, text in _refs_in_file(path_str):
            key = (ref, source.parent)
            resolved = seen.get(key)
            if resolved is None:
                resolved = resolve_include(
                    ref, source_file=source, case_dir=case_path, etc_dirs=etc_dirs
                )
                seen[key] = resolved
            # Re-stamp the including file: a cache hit carries the first one.
            hits.append(
                IncludeHit(
                    ref=ref,
                    source_file=source,
                    line=line,
                    resolved=dataclasses.replace(resolved, source_file=source),
                    text=text,
                )
            )
    return hits


def _refs_in_file(path_str: str) -> tuple[tuple[IncludeRef, int, str], ...]:
    """Return ((ref, 1-based line, raw text), ...), memoised on mtime+size."""
    try:
        stat = Path(path_str).stat()
    except OSError:
        return ()
    if stat.st_size > _MAX_SCAN_BYTES:
        return ()

    cached = _scan_cache.get(path_str)
    if cached is not None and cached[0] == stat.st_mtime and cached[1] == stat.st_size:
        return cached[2]

    refs = _parse_file_refs(path_str)
    _scan_cache[path_str] = (stat.st_mtime, stat.st_size, refs)
    return refs


def _parse_file_refs(path_str: str) -> tuple[tuple[IncludeRef, int, str], ...]:
    """Read a file and pull out its include references. No caching."""
    name = Path(path_str).name
    # Run logs hold solver output, scripts hold shell `#!`/comments -- neither
    # is a dictionary, and both can be large.
    if is_log_filename(name) or is_script_path(path_str):
        return ()
    try:
        text = read_foam_file(path_str)
    except OSError:
        return ()
    if not any(token in text for token in _SUBSTRING_GATE):
        return ()

    refs: list[tuple[IncludeRef, int, str]] = []
    for match in _DIRECTIVE_RE.finditer(text):
        raw = match.group(0).strip()
        ref = parse_include_directive(raw)
        if ref is not None:
            refs.append((ref, text.count("\n", 0, match.start()) + 1, raw))
    return tuple(refs)


def included_files(
    case_dir: str,
    paths: Sequence[str],
    *,
    etc_dirs: Sequence[Path] | None = None,
) -> tuple[list[str], dict[str, str], set[str]]:
    """Return the file-list view of a scan.

    ``(new_paths, origin_labels, read_only_paths)``:

    * ``new_paths`` -- resolved include targets **not already in** ``paths``,
      in a stable order. A ``.gz`` resolution is excluded, because
      ``foam.utils.read_foam_file`` cannot decompress it.
    * ``origin_labels`` -- path -> a human label naming the including file(s).
    * ``read_only_paths`` -- the subset that lies outside ``case_dir``.
    """
    case_path = Path(case_dir)
    known = {_dedupe_key(p) for p in paths}

    new_paths: list[str] = []
    origins: dict[str, list[str]] = {}
    read_only: set[str] = set()

    for hit in scan_includes(case_dir, paths, etc_dirs=etc_dirs):
        target = hit.resolved.path
        if target is None or target.suffix == ".gz":
            continue
        key = _dedupe_key(str(target))
        if key in known:
            continue
        listed = str(target)
        if listed not in origins:
            new_paths.append(listed)
            origins[listed] = []
            if not _is_inside(target, case_path):
                read_only.add(listed)
        label = _origin_label(hit.source_file, case_path)
        if label not in origins[listed]:
            origins[listed].append(label)

    return new_paths, {path: _join_origins(names) for path, names in origins.items()}, read_only


def _dedupe_key(path_str: str) -> str:
    """Key that recognises two spellings of the same file (symlinks, ``..``)."""
    cached = _realpath_cache.get(path_str)
    if cached is not None:
        return cached
    try:
        key = str(Path(path_str).resolve())
    except OSError:
        key = str(Path(path_str))
    _realpath_cache[path_str] = key
    return key


def _is_inside(path: Path, case_dir: Path) -> bool:
    try:
        path.relative_to(case_dir)
    except ValueError:
        return False
    return True


def _origin_label(source: Path, case_dir: Path) -> str:
    try:
        return str(source.relative_to(case_dir))
    except ValueError:
        return source.name


def _join_origins(names: list[str]) -> str:
    """Name the first two including files, counting any others."""
    if len(names) <= 2:
        return ", ".join(names)
    return f"{', '.join(names[:2])} +{len(names) - 2} more"


def resolve_directive_text(
    text: str,
    source_file: str,
    case_dir: str,
) -> ResolvedInclude | None:
    """Resolve one directive on demand, for a tree row. None if not an include."""
    ref = parse_include_directive(text)
    if ref is None:
        return None
    return resolve_include(
        ref,
        source_file=Path(source_file),
        case_dir=Path(case_dir),
        etc_dirs=foam_etc_dirs(),
    )


def copy_destination_for(src: Path, case_dir: Path, ref: IncludeRef | None) -> Path:
    """Return where "Copy into case" should put an out-of-case include.

    ``#includeFunc`` and ``#includeEtc`` land in ``system/`` -- for the former
    that is exactly where OpenFOAM looks first, so the copy overrides the
    installation's version with no edit to the directive. A plain ``#include``
    whose target is a relative path keeps that path, so it too re-resolves to
    the local copy unchanged.
    """
    if ref is not None and ref.kind not in {"includeEtc", "includeFunc"}:
        target = Path(ref.target)
        if not target.is_absolute() and not str(target).startswith("<") and ".." not in target.parts:
            return case_dir / target
    return case_dir / "system" / src.name
