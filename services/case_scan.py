# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Directory-tree scanning for the Case Browser/Cases tab (see CASE_BROWSER_PLAN.md).

Pure Python, no Qt: ``model/case_tree_model.py`` builds its rows from
:func:`list_subdirectories`, using the same ``progress``/``cancelled`` callback
convention as ``services/example_search.py``. This module deliberately carries
no user-facing prose (no ``tr()``, no ``i18n`` import) — ``tests/test_i18n.py``
only scans ``ui/``, so a translatable string here would ship untranslated with
nothing to notice.
"""
from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from services.case_loader import (
    PolyMeshInfo,
    detect_poly_mesh,
    detect_time_dirs,
    is_openfoam_case,
)


@dataclass(frozen=True)
class DirEntry:
    """One subdirectory found by :func:`list_subdirectories`."""

    path: Path
    name: str
    is_case: bool
    is_symlink: bool
    readable: bool
    has_subdirs: bool


@dataclass(frozen=True)
class CaseSummary:
    """Cheap summary of a case directory, for a detail/status display."""

    time_dirs: tuple[str, ...]
    mesh: PolyMeshInfo | None
    has_system: bool
    has_constant: bool
    has_zero: bool


def _has_subdirs(path: Path) -> bool:
    """True on the first child of *path* that is itself a directory.

    A single level of ``os.scandir`` — never recursive — so a symlink loop
    inside *path* cannot make this hang; it only ever lists one level down.
    An unreadable or vanished directory reads as having no subdirectories.
    """
    try:
        with os.scandir(path) as it:
            for child in it:
                try:
                    if child.is_dir():
                        return True
                except OSError:
                    continue
    except OSError:
        return False
    return False


def list_subdirectories(
    directory: Path,
    *,
    include_hidden: bool = False,
    progress: Callable[[str], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> list[DirEntry]:
    """Return the subdirectories of *directory*, sorted case-insensitively by name.

    Only directories are returned; hidden entries (name starting with ``.``)
    are excluded unless *include_hidden*. An ``OSError`` reading *directory*
    itself returns ``[]`` rather than raising; an unreadable *child* is still
    listed, with ``readable=False``.
    """
    try:
        with os.scandir(directory) as it:
            children = list(it)
    except OSError:
        return []

    names: list[os.DirEntry[str]] = []
    for child in children:
        if not include_hidden and child.name.startswith("."):
            continue
        try:
            if not child.is_dir():
                continue
        except OSError:
            continue
        names.append(child)
    names.sort(key=lambda e: e.name.lower())

    result: list[DirEntry] = []
    for child in names:
        if cancelled is not None and cancelled():
            break
        if progress is not None:
            progress(child.name)
        path = Path(child.path)
        readable = os.access(path, os.R_OK | os.X_OK)
        try:
            is_case = is_openfoam_case(str(path)) if readable else False
        except OSError:
            is_case = False
        result.append(
            DirEntry(
                path=path,
                name=child.name,
                is_case=is_case,
                is_symlink=child.is_symlink(),
                readable=readable,
                has_subdirs=_has_subdirs(path),
            )
        )
    return result


def case_summary(case_dir: Path) -> CaseSummary:
    """Summarise *case_dir* for a status/detail display."""
    s = str(case_dir)
    return CaseSummary(
        time_dirs=tuple(detect_time_dirs(s)),
        mesh=detect_poly_mesh(s),
        has_system=(case_dir / "system").is_dir(),
        has_constant=(case_dir / "constant").is_dir(),
        has_zero=(case_dir / "0").is_dir(),
    )


def ancestors_to(path: Path, stop: Path | None = None) -> list[Path]:
    """Return the root-first chain of directories from *stop* down to *path*.

    Both ends are included. When *stop* is ``None`` or is not an ancestor of
    *path*, the chain runs to the filesystem root instead.
    """
    chain = [path, *path.parents]
    if stop is not None and stop in chain:
        chain = chain[: chain.index(stop) + 1]
    chain.reverse()
    return chain
