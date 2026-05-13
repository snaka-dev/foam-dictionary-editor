# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import json
from pathlib import Path

from app_config.constants import JSON_INDENT

_CONFIG_FILENAME = ".foam-editor-files.json"


class CaseFilesConfig:
    """Manages per-case extra file/directory list stored in .foam-editor-files.json."""

    def __init__(self, case_dir: str):
        self._path = Path(case_dir) / _CONFIG_FILENAME
        self._extra_files: list[str] = []
        self._extra_dirs: list[str] = []
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._extra_files = [str(f) for f in data.get("extra_files", [])]
            self._extra_dirs = [str(d) for d in data.get("extra_dirs", [])]
        except (json.JSONDecodeError, IOError):
            self._extra_files = []
            self._extra_dirs = []

    def save(self) -> None:
        data: dict = {"extra_files": self._extra_files}
        if self._extra_dirs:
            data["extra_dirs"] = self._extra_dirs
        self._path.write_text(
            json.dumps(data, indent=JSON_INDENT, ensure_ascii=False),
            encoding="utf-8",
        )

    def get_extra_files(self) -> list[str]:
        return list(self._extra_files)

    def add_file(self, rel_path: str) -> None:
        if rel_path not in self._extra_files:
            self._extra_files.append(rel_path)

    def remove_file(self, rel_path: str) -> None:
        if rel_path in self._extra_files:
            self._extra_files.remove(rel_path)

    def get_extra_dirs(self) -> list[str]:
        return list(self._extra_dirs)

    def add_dir(self, rel_path: str) -> None:
        if rel_path not in self._extra_dirs:
            self._extra_dirs.append(rel_path)

    def remove_dir(self, rel_path: str) -> None:
        if rel_path in self._extra_dirs:
            self._extra_dirs.remove(rel_path)

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
