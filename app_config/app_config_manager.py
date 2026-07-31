# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from pathlib import Path

from app_config.defaults import DEFAULT_RESTORE_SESSION, DEFAULT_THEME
from app_config.foam_env import foam_env_dirs
from app_config.json_io import load_json, save_json

# Feature flags that change which panels and tabs a window has, and so which
# saved layouts can be applied to each other. A layout captured with a terminal
# in it means nothing to a --variant that has no terminal, so each combination
# keeps its own. Flags that do not move anything (syntax_highlighting) are not
# here: they would only fragment the stored layouts for no benefit.
_LAYOUT_FEATURES = ("terminal", "blockmesh")


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
        self._theme: str = DEFAULT_THEME
        self._restore_session: bool = DEFAULT_RESTORE_SESSION
        self._sessions: dict[str, dict] = {}
        self._settings_were_reset = False
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
            self._theme = DEFAULT_THEME
            self._restore_session = DEFAULT_RESTORE_SESSION
            self._sessions = {}
            return
        self._window_size = data.get("window_size", None)
        self._default_case_dir = data.get("default_case_dir", None)
        self._case_library_dirs = data.get("case_library_dirs", [])
        self._user_links = data.get("user_links", [])
        self._features = data.get("features", {})
        self._language = data.get("language", "en")
        self._openfoam_dir = data.get("openfoam_dir", None)
        self._theme = data.get("theme", DEFAULT_THEME)
        self._restore_session = bool(data.get("restore_session", DEFAULT_RESTORE_SESSION))
        sessions = data.get("sessions")
        # Kept as raw dicts: this layer has no business knowing what a window
        # state looks like, and ui/window_state.py is where a bad one is
        # forgiven (see load_saved_state).
        self._sessions = sessions if isinstance(sessions, dict) else {}

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
            if self._theme != DEFAULT_THEME:
                data["theme"] = self._theme
            if self._restore_session != DEFAULT_RESTORE_SESSION:
                data["restore_session"] = self._restore_session
            if self._sessions:
                data["sessions"] = self._sessions
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
        self._theme = DEFAULT_THEME
        self._restore_session = DEFAULT_RESTORE_SESSION
        self._sessions = {}

    def delete_config_file(self) -> None:
        try:
            if self._config_path.exists():
                self._config_path.unlink()
        except OSError as e:
            print(f"Warning: Failed to delete config file: {e}")
        self.reset()
        self._settings_were_reset = True

    @property
    def settings_were_reset(self) -> bool:
        """Whether **Reset All Settings** deleted the config file during this run.

        The flag exists because deleting the file is not by itself a reset: the
        application goes on running, and anything that captures state at shut-down
        would write the file straight back. ``MainWindow.closeEvent`` checks this
        and persists nothing, so the reset survives to the restart the dialog asks
        for. An explicit ``save()`` afterwards — the user picking a theme, say — is
        deliberately still honoured; only the implicit end-of-run capture is not.
        """
        return self._settings_were_reset

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

    # ── appearance ────────────────────────────────────────────────────────────

    def get_theme(self) -> str:
        """Return the theme mode: "system", "light", or "dark"."""
        return self._theme

    def set_theme(self, mode: str) -> None:
        """Set the theme mode. Does not auto-save."""
        self._theme = mode

    # ── session restore ───────────────────────────────────────────────────────

    def get_restore_session(self) -> bool:
        """Whether the last session's layout is reapplied at startup."""
        return self._restore_session

    def set_restore_session(self, enabled: bool) -> None:
        """Turn session restore on or off. Does not auto-save.

        A behaviour switch and nothing more: the stored layouts are left where
        they are, so switching off and back on returns to the layout that was
        stored when it was last on. Throwing one away is ``clear_sessions``'s
        job — deleting data is what an item that says so should do, not a side
        effect of a checkbox that says something else.
        """
        self._restore_session = enabled

    def has_stored_sessions(self) -> bool:
        """Whether any feature set has a layout stored."""
        return bool(self._sessions)

    def clear_sessions(self) -> None:
        """Forget every feature set's stored layout. Does not auto-save.

        Every one of them, not just this run's: which layout a window would
        restore depends on the ``--variant`` it was launched with, which is
        nowhere on screen, and an action whose reach depends on invisible state
        is worse than one that is broad and predictable. It is also the answer
        for someone clearing the case paths a layout records.
        """
        self._sessions = {}

    def session_key(self) -> str:
        """Return the key this run's layout is stored under.

        Derived from the layout-affecting feature flags rather than from the
        ``--variant`` name, because the name is not persisted anywhere and a
        plain ``python3 main.py`` run has none — it inherits whatever features
        were last saved. The flags are what actually decide which panels exist,
        which is the thing a layout has to agree with.
        """
        enabled = [name for name in _LAYOUT_FEATURES if self.get_feature(name)]
        return "+".join(enabled) or "minimal"

    def get_session_state(self) -> dict | None:
        """Return the raw saved window state for this run's feature set, if any."""
        state = self._sessions.get(self.session_key())
        return state if isinstance(state, dict) else None

    def set_session_state(self, state: dict | None) -> None:
        """Store the window state for this run's feature set. Does not auto-save.

        Other feature sets' layouts are left alone: switching to ``--variant
        no-terminal`` for one run must not cost the standard variant its layout.
        """
        if state is None:
            self._sessions.pop(self.session_key(), None)
        else:
            self._sessions[self.session_key()] = state

    def clear_session_geometry(self) -> None:
        """Drop the saved size and position from every stored layout.

        What makes **Reset Window Size** stick: without this the reset would be
        undone by the next restore, and the window would come back the size the
        user just asked it not to be.
        """
        for state in self._sessions.values():
            if isinstance(state, dict):
                state.pop("geometry", None)
                state.pop("window_size", None)
