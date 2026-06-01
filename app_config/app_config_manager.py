# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from app_config.constants import JSON_INDENT


class AppConfigManager:
    MIN_WIDTH, MIN_HEIGHT = 400, 300

    def __init__(self, config_path: str | None = None):
        if config_path is None:
            config_path = str(Path(__file__).parent.parent / "app_config.json")
        self._config_path = Path(config_path)
        self._window_size: Optional[list[int]] = None
        self._default_case_dir: Optional[str] = None
        self._case_library_dirs: list[str] = []
        self._user_links: list[dict] = []
        self._features: dict[str, bool] = {}
        self._language: str = "en"
        self._load()

    def _load(self) -> None:
        if not self._config_path.exists():
            return
        try:
            data = json.loads(self._config_path.read_text(encoding="utf-8"))
            self._window_size = data.get("window_size", None)
            self._default_case_dir = data.get("default_case_dir", None)
            self._case_library_dirs = data.get("case_library_dirs", [])
            self._user_links = data.get("user_links", [])
            self._features = data.get("features", {})
            self._language = data.get("language", "en")
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load config file: {e}")
            self._window_size = None
            self._default_case_dir = None
            self._case_library_dirs = []
            self._user_links = []
            self._features = {}

    def save(self) -> None:
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "window_size": self._window_size,
                "default_case_dir": self._default_case_dir,
                "case_library_dirs": self._case_library_dirs,
                "user_links": self._user_links,
            }
            if self._features:
                data["features"] = self._features
            if self._language != "en":
                data["language"] = self._language
            self._config_path.write_text(
                json.dumps(data, indent=JSON_INDENT, ensure_ascii=False),
                encoding="utf-8",
            )
        except IOError as e:
            print(f"Warning: Failed to save config file: {e}")

    def reset(self) -> None:
        self._window_size = None
        self._default_case_dir = None
        self._case_library_dirs = []
        self._user_links = []
        self._features = {}
        self._language = "en"

    def delete_config_file(self) -> None:
        try:
            if self._config_path.exists():
                self._config_path.unlink()
        except OSError as e:
            print(f"Warning: Failed to delete config file: {e}")
        self.reset()

    # ── window size ───────────────────────────────────────────────────────────

    def get_window_size(self) -> Optional[list[int]]:
        return self._window_size

    def get_window_size_or_default(self, default_w: int, default_h: int) -> tuple[int, int]:
        if self._window_size is not None:
            return (self._window_size[0], self._window_size[1])
        return (default_w, default_h)

    def set_window_size(self, width: int, height: int) -> None:
        if width < self.MIN_WIDTH or height < self.MIN_HEIGHT:
            raise ValueError(
                f"Window size must be at least ({self.MIN_WIDTH}, {self.MIN_HEIGHT}): "
                f"({width}, {height})"
            )
        self._window_size = [width, height]

    # ── default case directory ────────────────────────────────────────────────

    def get_default_case_dir(self) -> Optional[str]:
        return self._default_case_dir

    def get_default_case_dir_or_default(self, default: str) -> str:
        return self._default_case_dir if self._default_case_dir is not None else default

    def set_default_case_dir(self, path: Optional[str]) -> None:
        self._default_case_dir = path

    # ── case library ──────────────────────────────────────────────────────────

    @staticmethod
    def foam_tutorials_dir() -> str | None:
        """Return $FOAM_TUTORIALS if the env var is set and the directory exists."""
        foam = os.environ.get("FOAM_TUTORIALS", "")
        return foam if (foam and Path(foam).is_dir()) else None

    def get_case_library_dirs(self) -> list[str]:
        """Return all library dirs: $FOAM_TUTORIALS (auto, if valid) then user-added."""
        result: list[str] = []
        foam = self.foam_tutorials_dir()
        if foam and foam not in self._case_library_dirs:
            result.append(foam)
        result.extend(self._case_library_dirs)
        return result

    def get_user_library_dirs(self) -> list[str]:
        """Return only user-added library dirs (persisted to config)."""
        return list(self._case_library_dirs)

    def add_case_library_dir(self, path: str) -> None:
        if path not in self._case_library_dirs:
            self._case_library_dirs.append(path)

    def remove_case_library_dir(self, path: str) -> None:
        if path in self._case_library_dirs:
            self._case_library_dirs.remove(path)

    # ── user links ────────────────────────────────────────────────────────────

    def get_user_links(self) -> list[dict]:
        """Return user-defined links as [{label, url}, ...]."""
        return list(self._user_links)

    def set_user_links(self, links: list[dict]) -> None:
        self._user_links = list(links)

    # ── feature flags ─────────────────────────────────────────────────────────

    def get_feature(self, name: str, default: bool = True) -> bool:
        """Return the value of a feature flag; defaults to True when absent."""
        return bool(self._features.get(name, default))

    # ── language ──────────────────────────────────────────────────────────────

    def get_language(self) -> str:
        return self._language

    def set_language(self, lang: str) -> None:
        self._language = lang
