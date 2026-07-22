# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from pathlib import Path

from app_config.json_io import load_json, save_json


class AppConfigManager:
    MIN_WIDTH, MIN_HEIGHT = 400, 300

    def __init__(self, config_path: str | None = None):
        if config_path is None:
            config_path = str(Path(__file__).parent.parent / "app_config.json")
        self._config_path = Path(config_path)
        self._window_size: list[int] | None = None
        self._default_case_dir: str | None = None
        self._case_library_dirs: list[str] = []
        self._user_links: list[dict] = []
        self._features: dict[str, bool] = {}
        self._language: str = "en"
        self._openfoam_dir: str | None = None
        self._load()

    def _load(self) -> None:
        data = load_json(self._config_path)
        if data is None:
            if self._config_path.exists():
                print("Warning: Failed to load config file: invalid JSON")
            self._window_size = None
            self._default_case_dir = None
            self._case_library_dirs = []
            self._user_links = []
            self._features = {}
            self._openfoam_dir = None
            return
        self._window_size = data.get("window_size", None)
        self._default_case_dir = data.get("default_case_dir", None)
        self._case_library_dirs = data.get("case_library_dirs", [])
        self._user_links = data.get("user_links", [])
        self._features = data.get("features", {})
        self._language = data.get("language", "en")
        self._openfoam_dir = data.get("openfoam_dir", None)

    def save(self) -> None:
        try:
            data: dict[str, object] = {
                "window_size": self._window_size,
                "default_case_dir": self._default_case_dir,
                "case_library_dirs": self._case_library_dirs,
                "user_links": self._user_links,
            }
            if self._features:
                data["features"] = self._features
            if self._language != "en":
                data["language"] = self._language
            if self._openfoam_dir:
                data["openfoam_dir"] = self._openfoam_dir
            save_json(self._config_path, data)
        except OSError as e:
            print(f"Warning: Failed to save config file: {e}")

    def reset(self) -> None:
        self._window_size = None
        self._default_case_dir = None
        self._case_library_dirs = []
        self._user_links = []
        self._features = {}
        self._language = "en"
        self._openfoam_dir = None

    def delete_config_file(self) -> None:
        try:
            if self._config_path.exists():
                self._config_path.unlink()
        except OSError as e:
            print(f"Warning: Failed to delete config file: {e}")
        self.reset()

    # ── window size ───────────────────────────────────────────────────────────

    def get_window_size(self) -> list[int] | None:
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

    def get_default_case_dir(self) -> str | None:
        return self._default_case_dir

    def get_default_case_dir_or_default(self, default: str) -> str:
        return self._default_case_dir if self._default_case_dir is not None else default

    def set_default_case_dir(self, path: str | None) -> None:
        self._default_case_dir = path

    # ── case library ──────────────────────────────────────────────────────────

    @staticmethod
    def foam_tutorials_dir() -> str | None:
        """Return the tutorials dir of the sourced OpenFOAM environment, if any.

        Resolved via $FOAM_TUTORIALS with a $WM_PROJECT_DIR/tutorials fallback.
        """
        # Local import: app_config is a lower layer than services; import lazily
        # so the app_config package never depends on services at import time.
        from services.foam_env import foam_env_dirs

        tutorials = foam_env_dirs().tutorials_dir
        return str(tutorials) if tutorials is not None else None

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

    def set_feature(self, name: str, value: bool) -> None:
        self._features[name] = value

    def set_features(self, features: dict[str, bool]) -> None:
        """Replace the whole feature-flag mapping.

        Used by the --variant presets at startup; like any other setting the
        mapping is persisted on the next save().
        """
        self._features = dict(features)

    # ── language ──────────────────────────────────────────────────────────────

    def get_language(self) -> str:
        return self._language

    def set_language(self, lang: str) -> None:
        self._language = lang

    def get_openfoam_dir(self) -> str | None:
        """Return the user-chosen OpenFOAM installation directory, if any."""
        return self._openfoam_dir

    def set_openfoam_dir(self, path: str | None) -> None:
        """Set the OpenFOAM installation directory. Does not auto-save."""
        self._openfoam_dir = path
