# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from .app_config_manager import AppConfigManager
from .constants import (
    APP_CONFIG_FILE,
    JSON_ENSURE_ASCII,
    JSON_INDENT,
    SCHEMA_CONFIG_FILE,
)
from .defaults import (
    DEFAULT_CASE_DIRECTORY,
    DEFAULT_THEME,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
)

__all__ = [
    "APP_CONFIG_FILE",
    "SCHEMA_CONFIG_FILE",
    "JSON_INDENT",
    "JSON_ENSURE_ASCII",
    "DEFAULT_WINDOW_WIDTH",
    "DEFAULT_WINDOW_HEIGHT",
    "DEFAULT_CASE_DIRECTORY",
    "DEFAULT_THEME",
    "AppConfigManager",
    "get_app_config",
]

_app_config: AppConfigManager | None = None


def get_app_config(config_path: str | None = None) -> AppConfigManager:
    """Return the singleton, creating it on first call.

    *config_path* is honoured only by that first call, and exists for the
    recording harnesses: a demo take must neither open with the recording
    machine's settings nor write its own back (see DEVELOPER.md's "Demo
    recording"), so it points the singleton at a scratch file before the
    window is built. Everything in the application itself calls this with no
    argument and gets the one config in the repository root — or whatever
    ``$FODE_CONFIG`` names, which is how a test run or a scratch script keeps
    off the developer's real settings (see ``default_config_path``).
    """
    global _app_config
    if _app_config is None:
        _app_config = AppConfigManager(config_path)
    return _app_config
