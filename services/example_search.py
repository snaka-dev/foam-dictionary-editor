# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Search example usages of OpenFOAM keywords in a local installation.

Scans tutorial cases (``tutorials/``) and the curated templates under
``etc/caseDicts/`` of an OpenFOAM installation so users can find real usage
examples of a keyword or setting without resorting to ``find``/``grep``.

Pure Python, no Qt: the UI layer (``ui/dialogs/find_examples_dialog.py``) runs
:func:`search_examples` in a background thread using the same ``progress``/
``cancelled`` callback convention as ``app_config/keyword_generator.py``.
"""
from __future__ import annotations

import glob
import os
from collections.abc import Callable, Collection, Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app_config.foam_env import foam_env_dirs

Source = Literal["tutorials", "caseDicts"]
SOURCE_TUTORIALS: Source = "tutorials"
SOURCE_CASEDICTS: Source = "caseDicts"

_MAX_FILE_SIZE = 2 * 1024 * 1024  # skip binary meshes and other large payloads
_MAX_LINE_NUMBERS = 50
_SNIPPET_LIMIT = 120
_PROGRESS_EVERY = 200

_INSTALL_GLOBS = (
    "/usr/lib/openfoam/openfoam*",
    "/opt/openfoam*",
    "~/OpenFOAM/OpenFOAM-*",
)


@dataclass(frozen=True)
class FoamInstallation:
    """A discovered OpenFOAM installation offering searchable example sources."""

    root: Path
    label: str
    tutorials_dir: Path | None
    casedicts_dir: Path | None


@dataclass(frozen=True)
class SearchHit:
    """One file matching a query, with enough context for display."""

    file: Path
    source: Source
    case_root: Path | None  # tutorials only: the case directory containing the hit
    rel_label: str  # path relative to the searched source root, for display
    line_numbers: tuple[int, ...]  # 1-based, capped at _MAX_LINE_NUMBERS
    snippet: str  # first matched line, stripped and truncated


def _snippet(line: str, limit: int = _SNIPPET_LIMIT) -> str:
    text = line.strip()
    if len(text) > limit:
        return text[: limit - 1] + "…"
    return text


def installation_from_dir(root: Path, label: str | None = None) -> FoamInstallation | None:
    """Build a :class:`FoamInstallation` from an install root or a bare tutorials dir.

    Returns ``None`` when the directory offers neither ``tutorials/`` nor
    ``etc/caseDicts/``.
    """
    root = root.expanduser()
    if not root.is_dir():
        return None
    tutorials: Path | None = None
    if (root / "tutorials").is_dir():
        tutorials = root / "tutorials"
    elif root.name == "tutorials":
        tutorials = root
    casedicts: Path | None = None
    if (root / "etc" / "caseDicts").is_dir():
        casedicts = root / "etc" / "caseDicts"
    if tutorials is None and casedicts is None:
        return None
    return FoamInstallation(
        root=root,
        label=label or root.name or str(root),
        tutorials_dir=tutorials,
        casedicts_dir=casedicts,
    )


def _installation_from_env(env: Mapping[str, str]) -> FoamInstallation | None:
    """Build an installation from FOAM_TUTORIALS/FOAM_ETC/WM_PROJECT_DIR if set."""
    dirs = foam_env_dirs(env)
    project = dirs.project_dir
    tutorials_dir = dirs.tutorials_dir
    casedicts = dirs.etc_dir / "caseDicts" if dirs.etc_dir is not None else None
    casedicts_dir = casedicts if casedicts is not None and casedicts.is_dir() else None
    if tutorials_dir is None and casedicts_dir is None:
        return None
    if project is not None:
        root = project
        label = f"{project.name} (environment)"
    elif tutorials_dir is not None:
        root = tutorials_dir
        label = "(environment)"
    else:
        assert casedicts_dir is not None
        root = casedicts_dir.parent.parent
        label = "(environment)"
    return FoamInstallation(
        root=root, label=label, tutorials_dir=tutorials_dir, casedicts_dir=casedicts_dir
    )


def discover_installations(
    env: Mapping[str, str] | None = None,
    extra_roots: Iterable[str] = (),
) -> list[FoamInstallation]:
    """Discover OpenFOAM installations to search.

    Order: ``extra_roots`` (user overrides) first, then an entry derived from
    the environment (``FOAM_TUTORIALS``/``FOAM_ETC``/``WM_PROJECT_DIR``), then
    well-known install locations (newest version first). De-duplicated by
    resolved root; unreadable directories are silently skipped.
    """
    if env is None:
        env = os.environ
    result: list[FoamInstallation] = []
    seen: set[Path] = set()

    def _add(installation: FoamInstallation | None) -> None:
        if installation is None:
            return
        try:
            key = installation.root.resolve()
        except OSError:
            return
        if key in seen:
            return
        seen.add(key)
        result.append(installation)

    for root_str in extra_roots:
        if root_str:
            _add(installation_from_dir(Path(root_str)))
    _add(_installation_from_env(env))
    for pattern in _INSTALL_GLOBS:
        expanded = os.path.expanduser(pattern)
        for match in sorted(glob.glob(expanded), reverse=True):
            _add(installation_from_dir(Path(match)))
    return result


def case_root_for(path: Path, stop: Path) -> Path | None:
    """Return the nearest ancestor case directory (containing ``system/controlDict``).

    Walks up from ``path`` and gives up above ``stop`` (the tutorials root).
    """
    try:
        path.relative_to(stop)
    except ValueError:
        return None
    current = path if path.is_dir() else path.parent
    while True:
        if (current / "system" / "controlDict").is_file():
            return current
        if current == stop or current.parent == current:
            return None
        current = current.parent


def _iter_files(root: Path, file_name: str | None) -> Iterator[Path]:
    """Yield candidate files under root, skipping oversized ones."""
    pattern = file_name if file_name else "*"
    for path in sorted(root.rglob(pattern)):
        try:
            if not path.is_file() or path.stat().st_size > _MAX_FILE_SIZE:
                continue
        except OSError:
            continue
        yield path


def _match_file(path: Path, needle: str) -> tuple[tuple[int, ...], str] | None:
    """Return (matched line numbers, snippet) or None if the file has no match."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if "\x00" in text:  # binary file (e.g. binary-format mesh data)
        return None
    line_numbers: list[int] = []
    snippet = ""
    for number, line in enumerate(text.splitlines(), start=1):
        if needle in line.lower():
            if not line_numbers:
                snippet = _snippet(line)
            line_numbers.append(number)
            if len(line_numbers) >= _MAX_LINE_NUMBERS:
                break
    if not line_numbers:
        return None
    return tuple(line_numbers), snippet


def search_examples(
    installation: FoamInstallation,
    query: str,
    *,
    sources: Collection[Source] = (SOURCE_TUTORIALS, SOURCE_CASEDICTS),
    file_name: str | None = None,
    max_hits: int = 200,
    progress: Callable[[str], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> list[SearchHit]:
    """Search example files for a case-insensitive substring, line by line.

    Returns at most ``max_hits`` file-level hits; stops early when
    ``cancelled()`` reports True. Raises ``ValueError`` on a blank query.
    """
    needle = query.strip().lower()
    if not needle:
        raise ValueError("query must not be empty")
    roots: list[tuple[Source, Path]] = []
    if SOURCE_TUTORIALS in sources and installation.tutorials_dir is not None:
        roots.append((SOURCE_TUTORIALS, installation.tutorials_dir))
    if SOURCE_CASEDICTS in sources and installation.casedicts_dir is not None:
        roots.append((SOURCE_CASEDICTS, installation.casedicts_dir))

    hits: list[SearchHit] = []
    scanned = 0
    for source, root in roots:
        for path in _iter_files(root, file_name):
            if cancelled is not None and cancelled():
                return hits
            scanned += 1
            if progress is not None and scanned % _PROGRESS_EVERY == 0:
                progress(f"Searching {source}… ({scanned} files scanned)")
            matched = _match_file(path, needle)
            if matched is None:
                continue
            line_numbers, snippet = matched
            case_root = case_root_for(path, root) if source == SOURCE_TUTORIALS else None
            hits.append(
                SearchHit(
                    file=path,
                    source=source,
                    case_root=case_root,
                    rel_label=str(path.relative_to(root)),
                    line_numbers=line_numbers,
                    snippet=snippet,
                )
            )
            if len(hits) >= max_hits:
                return hits
    return hits
