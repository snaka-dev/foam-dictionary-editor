# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from pathlib import Path

from app_config.json_io import load_json, save_json

_CONFIG_FILENAME = ".foam-editor-files.json"

# (relative path, recursive)
DirEntry = tuple[str, bool]


class CaseFilesConfig:
    """Manages per-case extra file/directory list stored in .foam-editor-files.json."""

    def __init__(self, case_dir: str):
        self._path = Path(case_dir) / _CONFIG_FILENAME
        self._extra_files: list[str] = []
        self._extra_dirs: list[DirEntry] = []
        self._load()

    def _load(self) -> None:
        data = load_json(self._path)
        if data is None:
            self._extra_files = []
            self._extra_dirs = []
            return
        self._extra_files = [str(f) for f in data.get("extra_files", [])]
        self._extra_dirs = []
        for d in data.get("extra_dirs", []):
            if isinstance(d, dict):
                self._extra_dirs.append(
                    (str(d.get("path", "")), bool(d.get("recursive", False)))
                )
            else:
                # Backward compat: old format stored plain strings (non-recursive).
                self._extra_dirs.append((str(d), False))

    def save(self) -> None:
        data: dict = {"extra_files": self._extra_files}
        if self._extra_dirs:
            data["extra_dirs"] = [
                {"path": p, "recursive": r} for p, r in self._extra_dirs
            ]
        save_json(self._path, data)

    def get_extra_files(self) -> list[str]:
        return list(self._extra_files)

    def add_file(self, rel_path: str) -> None:
        if rel_path not in self._extra_files:
            self._extra_files.append(rel_path)

    def remove_file(self, rel_path: str) -> None:
        if rel_path in self._extra_files:
            self._extra_files.remove(rel_path)

    def get_extra_dirs(self) -> list[DirEntry]:
        return list(self._extra_dirs)

    def add_dir(self, rel_path: str, recursive: bool = False) -> None:
        for i, (p, _) in enumerate(self._extra_dirs):
            if p == rel_path:
                self._extra_dirs[i] = (rel_path, recursive)
                return
        self._extra_dirs.append((rel_path, recursive))

    def remove_dir(self, rel_path: str) -> None:
        self._extra_dirs = [(p, r) for p, r in self._extra_dirs if p != rel_path]

    def reset(self) -> None:
        self._extra_files = []
        self._extra_dirs = []

    def delete_config_file(self) -> None:
        try:
            if self._path.exists():
                self._path.unlink()
        except OSError:
            pass
        self.reset()

    @property
    def config_filename(self) -> str:
        return _CONFIG_FILENAME

    @property
    def exists(self) -> bool:
        return self._path.exists()
