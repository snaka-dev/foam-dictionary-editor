# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from schemas._base import KeySchema
from schemas.config_store import delete_schema_config
from schemas.registry import SchemaRegistry

__all__ = [
    "delete_schema_config",
    "apply_schema_modules",
    "get_schema_modules",
    "save_current_config",
    "schema_for_file_key",
    "choices_for_file_key",
    "choice_description_for_value",
    "choice_note_for_value",
    "choice_supported_in_for_value",
    "schema_supported_in_text",
    "schema_note_text",
]

_registry = SchemaRegistry()


def save_current_config() -> None:
    _registry.save()


def apply_schema_modules(modules: list[str]) -> None:
    _registry.set_schema_modules(modules)
    _registry.apply_and_reload()


def get_schema_modules() -> list[str]:
    return _registry.get_schema_modules()


def schema_for_file_key(
    file_path: str | None,
    key_name: str | None,
    parent_key: str | None = None,
    grandparent_key: str | None = None,
) -> KeySchema | None:
    return _registry.schema_for_file_key(file_path, key_name, parent_key, grandparent_key)


def choices_for_file_key(
    file_path: str | None,
    key_name: str | None,
    parent_key: str | None = None,
    grandparent_key: str | None = None,
) -> list[str]:
    return _registry.choices_for_file_key(file_path, key_name, parent_key, grandparent_key)


def choice_description_for_value(
    file_path: str | None,
    key_name: str | None,
    value: str | None,
    parent_key: str | None = None,
    grandparent_key: str | None = None,
) -> str:
    return _registry.choice_description_for_value(file_path, key_name, value, parent_key, grandparent_key)


def choice_supported_in_for_value(
    file_path: str | None,
    key_name: str | None,
    value: str | None,
    parent_key: str | None = None,
    grandparent_key: str | None = None,
) -> str:
    return _registry.choice_supported_in_for_value(file_path, key_name, value, parent_key, grandparent_key)


def choice_note_for_value(
    file_path: str | None,
    key_name: str | None,
    value: str | None,
    parent_key: str | None = None,
    grandparent_key: str | None = None,
) -> str:
    return _registry.choice_note_for_value(file_path, key_name, value, parent_key, grandparent_key)


def schema_supported_in_text(
    file_path: str | None,
    key_name: str | None,
    parent_key: str | None = None,
    grandparent_key: str | None = None,
) -> str:
    return _registry.schema_supported_in_text(file_path, key_name, parent_key, grandparent_key)


def schema_note_text(
    file_path: str | None,
    key_name: str | None,
    parent_key: str | None = None,
    grandparent_key: str | None = None,
) -> str:
    return _registry.schema_note_text(file_path, key_name, parent_key, grandparent_key)
