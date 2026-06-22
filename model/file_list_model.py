# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from pathlib import Path

_PARENT_ORDER = {
    "system": 0,
    "constant": 1,
    "0": 2,
    "0.orig": 3,
}


def _group_name(path: str, case_dir: str | None = None) -> str:
    """Return the group key: 'system', 'constant', 'system/region1', etc."""
    p = Path(path)
    if case_dir:
        try:
            rel = p.relative_to(Path(case_dir))
            parts = rel.parent.parts
            if parts:
                return "/".join(parts)
        except ValueError:
            pass
    return p.parent.name or ""


def _group_sort_key(group: str) -> tuple[int, str]:
    parts = group.split("/", 1)
    order = _PARENT_ORDER.get(parts[0], 999)
    sub = parts[1] if len(parts) > 1 else ""
    return (order, sub)


class FileListModel:
    """Holds the logical data for the file list: paths, grouping, dirty/diff states."""

    def __init__(self) -> None:
        self.case_dir: str | None = None
        self._groups: list[tuple[str, list[str]]] = []
        self._extra_files: set[str] = set()
        self._extra_dir_set: set[str] = set()
        self._dirty: dict[str, bool] = {}
        self._diff_counts: dict[str, int | None] = {}

    # ── public API ────────────────────────────────────────────────────────────

    def load(
        self,
        paths: list[str],
        case_dir: str | None = None,
        extra_files: list[str] | None = None,
        extra_dirs: list[str] | None = None,
    ) -> None:
        self.case_dir = case_dir
        self._extra_dir_set = {str(Path(d)) for d in (extra_dirs or [])}
        if extra_files and case_dir:
            self._extra_files = {str(Path(ef)) for ef in extra_files}
        else:
            self._extra_files = set()
        self._dirty = {}
        self._diff_counts = {}
        self._groups = self._build_groups(paths)

    def clear(self) -> None:
        self.case_dir = None
        self._groups = []
        self._extra_files = set()
        self._extra_dir_set = set()
        self._dirty = {}
        self._diff_counts = {}

    def sorted_groups(self) -> list[tuple[str, list[str]]]:
        """Return [(group_name, [sorted_paths])] in display order."""
        return self._groups

    def mark_dirty(self, path: str, dirty: bool) -> None:
        self._dirty[path] = dirty

    def mark_diff(self, path: str, count: int | None) -> None:
        self._diff_counts[path] = count

    def clear_diff_marks(self) -> None:
        self._diff_counts.clear()

    def is_dirty(self, path: str) -> bool:
        return self._dirty.get(path, False)

    def diff_count(self, path: str) -> int | None:
        return self._diff_counts.get(path)

    def is_extra_file(self, path: str) -> bool:
        if not self.case_dir or not self._extra_files:
            return False
        try:
            rel = str(Path(path).relative_to(Path(self.case_dir)))
            return rel in self._extra_files
        except ValueError:
            return False

    def is_extra_dir(self, group: str) -> bool:
        return group in self._extra_dir_set

    @property
    def extra_dir_set(self) -> set[str]:
        return self._extra_dir_set

    @property
    def extra_file_count(self) -> int:
        return len(self._extra_files)

    @property
    def extra_dir_count(self) -> int:
        return len(self._extra_dir_set)

    # ── internals ─────────────────────────────────────────────────────────────

    def _build_groups(self, paths: list[str]) -> list[tuple[str, list[str]]]:
        sorted_paths = sorted(
            paths,
            key=lambda p: (_group_sort_key(_group_name(p, self.case_dir)), Path(p).name.lower()),
        )
        groups: list[tuple[str, list[str]]] = []
        current_group: str | None = None
        current_paths: list[str] = []
        for path in sorted_paths:
            g = _group_name(path, self.case_dir)
            if g != current_group:
                if current_group is not None:
                    groups.append((current_group, current_paths))
                current_group = g
                current_paths = []
            current_paths.append(path)
        if current_group is not None:
            groups.append((current_group, current_paths))
        return groups
