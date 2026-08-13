# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from schemas._base import ChoiceItem, KeySchema
from schemas.config_store import delete_schema_config
from schemas.registry import SchemaRegistry, _supported_in_text

__all__ = [
    "KeySchema",
    "delete_schema_config",
    "apply_schema_modules",
    "get_schema_modules",
    "save_current_config",
    "schema_for_file_key",
    "choices_for_file_key",
    "choice_for_value",
    "choice_description_for_value",
    "choice_note_for_value",
    "choice_supported_in_for_value",
    "schema_supported_in_text",
    "schema_note_text",
    "supported_in_text",
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


def choice_for_value(
    file_path: str | None,
    key_name: str | None,
    value: str | None,
    parent_key: str | None = None,
    grandparent_key: str | None = None,
) -> ChoiceItem | None:
    return _registry.choice_for_value(file_path, key_name, value, parent_key, grandparent_key)


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


def supported_in_text(schema_or_choice: KeySchema | ChoiceItem | None) -> str:
    """Format a `KeySchema`/`ChoiceItem` already in hand, without a fresh lookup.

    Thin wrapper over the registry's own `_supported_in_text` formatter — the
    same text `schema_supported_in_text`/`choice_supported_in_for_value` return,
    but for a caller that has already resolved the schema/choice itself (e.g.
    `ui/panels/detail_panel.py`) and would otherwise re-run the lookup just to
    reformat its `supported_in` tuple.
    """
    return _supported_in_text(schema_or_choice)
