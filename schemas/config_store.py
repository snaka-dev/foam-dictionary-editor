# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import json
from pathlib import Path

from app_config.constants import (
    JSON_ENSURE_ASCII,
    JSON_INDENT,
    SCHEMA_CONFIG_FILE,
)
from schemas.builtin import get_default_schema_config

CONFIG_FILE = Path(__file__).resolve().parent.parent / SCHEMA_CONFIG_FILE


def load_schema_config() -> dict:
    """Load schema configuration from the config file."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return get_default_schema_config()


def save_schema_config(config: dict) -> None:
    """Save schema configuration to the config file."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(
            config,
            f,
            indent=JSON_INDENT,
            ensure_ascii=JSON_ENSURE_ASCII,
        )


def reset_schema_config() -> dict:
    """Reset schema configuration to the default values."""
    config = get_default_schema_config()
    save_schema_config(config)
    return config


def delete_schema_config() -> dict:
    """Delete the config file and restore defaults."""
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()
    return reset_schema_config()
