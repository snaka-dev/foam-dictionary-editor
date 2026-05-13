# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import importlib
import logging
from pathlib import Path

from schemas._base import ChoiceItem, KeySchema, _versions_text
from schemas.config_store import load_schema_config, save_schema_config

logger = logging.getLogger(__name__)


class SchemaRegistry:
    """Manage schema configuration and runtime schema lookup tables."""

    def __init__(self) -> None:
        self._config: dict = {}
        self._file_key_schemas: dict[str, dict[str, KeySchema]] = {}
        self.reload()

    def get_config(self) -> dict:
        """Return a shallow copy of the current schema config."""
        return {
            "schema_modules": list(self._config.get("schema_modules", [])),
        }

    def get_schema_modules(self) -> list[str]:
        """Return the configured schema module list."""
        return list(self._config.get("schema_modules", []))

    def set_schema_modules(self, modules: list[str]) -> None:
        """Replace schema modules in memory."""
        self._config["schema_modules"] = list(modules)

    def save(self) -> None:
        """Save the current config to disk."""
        save_schema_config(self._config)

    def reload(self) -> None:
        """Reload the config from disk and rebuild runtime schemas."""
        raw = load_schema_config()
        self._config = {"schema_modules": raw.get("schema_modules", [])}
        self._file_key_schemas = self._build_file_key_schemas(self._config)

    def apply_and_reload(self) -> None:
        """Rebuild runtime schemas from the current in-memory config."""
        self._file_key_schemas = self._build_file_key_schemas(self._config)

    def schema_for_file_key(
        self,
        file_path: str | None,
        key_name: str | None,
    ) -> KeySchema | None:
        """Return the schema for a file/key pair."""
        if not file_path or not key_name:
            return None
        file_name = Path(file_path).name
        per_file = self._file_key_schemas.get(file_name, {})
        return per_file.get(key_name)

    def choices_for_file_key(
        self,
        file_path: str | None,
        key_name: str | None,
    ) -> list[str]:
        """Return choice values for a file/key pair."""
        schema = self.schema_for_file_key(file_path, key_name)
        if schema is None:
            return []
        return [item.value for item in schema.choices]

    def choice_for_value(
        self,
        file_path: str | None,
        key_name: str | None,
        value: str | None,
    ) -> ChoiceItem | None:
        """Return the matching choice item for a file/key/value triple."""
        schema = self.schema_for_file_key(file_path, key_name)
        if schema is None or value is None:
            return None
        for item in schema.choices:
            if item.value == value:
                return item
        return None

    def choice_description_for_value(
        self,
        file_path: str | None,
        key_name: str | None,
        value: str | None,
    ) -> str:
        """Return the choice description for a file/key/value triple."""
        item = self.choice_for_value(file_path, key_name, value)
        return item.description if item else ""

    def choice_supported_in_for_value(
        self,
        file_path: str | None,
        key_name: str | None,
        value: str | None,
    ) -> str:
        """Return supported version text for a file/key/value triple."""
        item = self.choice_for_value(file_path, key_name, value)
        if item is None or not item.supported_in:
            return ""
        return _versions_text(item.supported_in)

    def choice_note_for_value(
        self,
        file_path: str | None,
        key_name: str | None,
        value: str | None,
    ) -> str:
        """Return the choice note for a file/key/value triple."""
        item = self.choice_for_value(file_path, key_name, value)
        return item.note if item else ""

    def schema_supported_in_text(
        self,
        file_path: str | None,
        key_name: str | None,
    ) -> str:
        """Return supported version text for a file/key pair."""
        schema = self.schema_for_file_key(file_path, key_name)
        if schema is None or not schema.supported_in:
            return ""
        return _versions_text(schema.supported_in)

    def schema_note_text(
        self,
        file_path: str | None,
        key_name: str | None,
    ) -> str:
        """Return the schema note for a file/key pair."""
        schema = self.schema_for_file_key(file_path, key_name)
        return schema.note if schema else ""

    @staticmethod
    def _build_file_key_schemas(
        config: dict,
    ) -> dict[str, dict[str, KeySchema]]:
        """Build runtime schema lookup tables from the config."""
        result: dict[str, dict[str, KeySchema]] = {}

        for module_name in config.get("schema_modules", []):
            try:
                module = importlib.import_module(module_name)
            except ImportError as e:
                logger.warning("Could not import %s: %s", module_name, e)
                continue

            target_file = getattr(module, "TARGET_FILE", None)
            schemas = getattr(module, "SCHEMAS", None)
            if target_file and isinstance(schemas, dict):
                result[target_file] = schemas

        return result
