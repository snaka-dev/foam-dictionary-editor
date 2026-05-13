# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from .constants import (
    APP_CONFIG_FILE,
    JSON_ENSURE_ASCII,
    JSON_INDENT,
    SCHEMA_CONFIG_FILE,
)
from .defaults import (
    DEFAULT_CASE_DIRECTORY,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
)
from .app_config_manager import AppConfigManager

__all__ = [
    "APP_CONFIG_FILE",
    "SCHEMA_CONFIG_FILE",
    "JSON_INDENT",
    "JSON_ENSURE_ASCII",
    "DEFAULT_WINDOW_WIDTH",
    "DEFAULT_WINDOW_HEIGHT",
    "DEFAULT_CASE_DIRECTORY",
    "AppConfigManager",
    "get_app_config",
]

_app_config: AppConfigManager | None = None


def get_app_config() -> AppConfigManager:
    global _app_config
    if _app_config is None:
        _app_config = AppConfigManager()
    return _app_config
