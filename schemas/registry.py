# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import importlib
import logging
from pathlib import Path

from schemas._base import ChoiceItem, KeySchema, _versions_text
from schemas.builtin import get_default_schema_config
from schemas.config_store import load_schema_config, save_schema_config

logger = logging.getLogger(__name__)


def _supported_in_text(obj: KeySchema | ChoiceItem | None) -> str:
    """Format a resolved schema/choice item's `supported_in` versions, or ""."""
    if obj is None or not obj.supported_in:
        return ""
    return _versions_text(obj.supported_in)


class SchemaRegistry:
    """Manage schema configuration and runtime schema lookup tables."""

    def __init__(self) -> None:
        self._config: dict = {}
        self._file_key_schemas: dict[str, dict[str, KeySchema]] = {}
        self._file_namespaces: dict[str, frozenset[str]] = {}
        self._file_owned_keys: dict[str, frozenset[str]] = {}
        self._file_open_namespaces: dict[str, frozenset[str]] = {}
        self.reload()

    def get_config(self) -> dict:
        """Return a shallow copy of the current schema config."""
        return {
            "schema_modules": list(self._config.get("schema_modules", [])),
            "disabled_modules": list(self._config.get("disabled_modules", [])),
        }

    def get_schema_modules(self) -> list[str]:
        """Return the configured schema module list."""
        return list(self._config.get("schema_modules", []))

    def set_schema_modules(self, modules: list[str]) -> None:
        """Replace schema modules in memory.

        Anything known but absent from *modules* is recorded as deliberately
        disabled, which is what stops `_effective_config` reinstating it on the
        next load.
        """
        known = (
            set(get_default_schema_config().get("schema_modules", []))
            | set(self._config.get("schema_modules", []))
            | set(self._config.get("disabled_modules", []))
        )
        self._config["schema_modules"] = list(modules)
        self._config["disabled_modules"] = sorted(known - set(modules))

    def save(self) -> None:
        """Save the current config to disk."""
        save_schema_config(self._config)

    def reload(self) -> None:
        """Reload the config from disk and rebuild runtime schemas."""
        self._config = self._effective_config(load_schema_config())
        self._rebuild_tables()

    @staticmethod
    def _effective_config(raw: dict) -> dict:
        """Union the saved module list with the built-in defaults.

        A saved list used to be authoritative, which meant a schema module
        added to `schemas/builtin.py` in a later release never reached anyone
        who had opened Manage Schema Modules even once — their config pinned
        the old list forever. Defaults are therefore merged in on every load,
        and only modules the user explicitly removed (recorded in
        ``disabled_modules``) stay out.

        A config written before ``disabled_modules`` existed has no record of
        intent, so a module removed back then comes back once. That is the
        conservative direction: a schema too many is visible and one click to
        remove, a schema missing is invisible.
        """
        defaults = get_default_schema_config().get("schema_modules", [])
        disabled = list(raw.get("disabled_modules", []))

        merged = list(defaults)
        for module_name in raw.get("schema_modules", []):
            if module_name not in merged:
                merged.append(module_name)

        return {
            "schema_modules": [m for m in merged if m not in disabled],
            "disabled_modules": disabled,
        }

    def apply_and_reload(self) -> None:
        """Rebuild runtime schemas from the current in-memory config."""
        self._rebuild_tables()

    def _rebuild_tables(self) -> None:
        """Rebuild the lookup table and the qualified-key index derived from it."""
        self._file_key_schemas = self._build_file_key_schemas(self._config)
        self._file_open_namespaces = self._build_open_namespaces(self._config)
        self._file_namespaces, self._file_owned_keys = self._build_qualified_index(
            self._file_key_schemas
        )

    def schema_for_file_key(
        self,
        file_path: str | None,
        key_name: str | None,
        parent_key: str | None = None,
        grandparent_key: str | None = None,
    ) -> KeySchema | None:
        """Return the schema for a file/key pair.

        Lookup order (first match wins):
        1. ``"<parent_key>.<key_name>"``      — direct parent context
        2. ``"<grandparent_key>.<key_name>"`` — grandparent context, used for
           blocks whose immediate parent is a user-defined name (e.g. a named
           geometry or refinement-region entry)
        3. ``"<parent_key>.*"`` — wildcard, for dictionaries whose children are
           named by the user and so cannot be enumerated (``divSchemes``,
           ``relaxationFactors``, ``residualControl``). Direct parent only, so a
           wildcard never answers for a key one level deeper than it describes.
        4. plain ``key_name``                 — flat fallback, unless the
           surrounding dictionary is a closed namespace (see below)

        A dotted prefix is a *closed namespace*: once a module qualifies any key
        under ``kOmegaSSTCoeffs``, a key it does not qualify there is not that
        dictionary's key, and the flat fallback must not answer for it. Without
        this, ``kOmegaSSTCoeffs { C1 1.44; }`` resolves through the plain ``C1``
        that exists for the flat ``RAS { C1 …; }`` spelling and reports kEpsilon's
        coefficient inside a kOmegaSST dictionary. The guard applies only to keys
        that *are* qualified somewhere in the same file, so a key belonging to no
        namespace still falls back from any context.

        Some dictionaries are namespaces yet still legitimately hold arbitrary
        keys — ``RAS`` has structural entries of its own (``model``,
        ``turbulence``) while OpenFOAM's ``optionalSubDict`` idiom also allows a
        model's coefficients to be written straight into it. Structure alone
        cannot distinguish that from ``kOmegaSSTCoeffs``, so a module lists such
        prefixes in ``OPEN_NAMESPACES`` and they keep the flat fallback.

        Existing schema modules that use only flat keys are unaffected.
        """
        if not file_path or not key_name:
            return None
        file_name = Path(file_path).name
        per_file = self._file_key_schemas.get(file_name, {})
        if parent_key:
            schema = per_file.get(f"{parent_key}.{key_name}")
            if schema is not None:
                return schema
        if grandparent_key:
            schema = per_file.get(f"{grandparent_key}.{key_name}")
            if schema is not None:
                return schema
        # Wildcard entries answer for children whose names cannot be enumerated:
        # `divSchemes { div(phi,U) … }`, `relaxationFactors { equations { U 0.7; } }`.
        # Tried after both exact forms (a named key always beats a catch-all) but
        # before the flat fallback, since parent context beats a global key.
        #
        # Deliberately the *direct* parent only. A grandparent wildcard would
        # reach a level too far: `functions.*` describes one function object, and
        # matching it from the grandparent would make it answer for every key
        # *inside* that object too.
        if parent_key:
            schema = per_file.get(f"{parent_key}.*")
            if schema is not None:
                return schema
        if key_name in self._file_owned_keys.get(file_name, frozenset()):
            namespaces = self._file_namespaces.get(file_name, frozenset())
            open_ns = self._file_open_namespaces.get(file_name, frozenset())
            closed = (
                context for context in (parent_key, grandparent_key)
                if context and context in namespaces and context not in open_ns
            )
            if any(closed):
                return None
        return per_file.get(key_name)

    def choices_for_file_key(
        self,
        file_path: str | None,
        key_name: str | None,
        parent_key: str | None = None,
        grandparent_key: str | None = None,
    ) -> list[str]:
        """Return choice values for a file/key pair."""
        schema = self.schema_for_file_key(file_path, key_name, parent_key, grandparent_key)
        if schema is None:
            return []
        return [item.value for item in schema.choices]

    def choice_for_value(
        self,
        file_path: str | None,
        key_name: str | None,
        value: str | None,
        parent_key: str | None = None,
        grandparent_key: str | None = None,
    ) -> ChoiceItem | None:
        """Return the matching choice item for a file/key/value triple."""
        schema = self.schema_for_file_key(file_path, key_name, parent_key, grandparent_key)
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
        parent_key: str | None = None,
        grandparent_key: str | None = None,
    ) -> str:
        """Return the choice description for a file/key/value triple."""
        item = self.choice_for_value(file_path, key_name, value, parent_key, grandparent_key)
        return item.description if item else ""

    def choice_supported_in_for_value(
        self,
        file_path: str | None,
        key_name: str | None,
        value: str | None,
        parent_key: str | None = None,
        grandparent_key: str | None = None,
    ) -> str:
        """Return supported version text for a file/key/value triple."""
        item = self.choice_for_value(file_path, key_name, value, parent_key, grandparent_key)
        return _supported_in_text(item)

    def choice_note_for_value(
        self,
        file_path: str | None,
        key_name: str | None,
        value: str | None,
        parent_key: str | None = None,
        grandparent_key: str | None = None,
    ) -> str:
        """Return the choice note for a file/key/value triple."""
        item = self.choice_for_value(file_path, key_name, value, parent_key, grandparent_key)
        return item.note if item else ""

    def schema_supported_in_text(
        self,
        file_path: str | None,
        key_name: str | None,
        parent_key: str | None = None,
        grandparent_key: str | None = None,
    ) -> str:
        """Return supported version text for a file/key pair."""
        schema = self.schema_for_file_key(file_path, key_name, parent_key, grandparent_key)
        return _supported_in_text(schema)

    def schema_note_text(
        self,
        file_path: str | None,
        key_name: str | None,
        parent_key: str | None = None,
        grandparent_key: str | None = None,
    ) -> str:
        """Return the schema note for a file/key pair."""
        schema = self.schema_for_file_key(file_path, key_name, parent_key, grandparent_key)
        return schema.note if schema else ""

    @staticmethod
    def _build_file_key_schemas(
        config: dict,
    ) -> dict[str, dict[str, KeySchema]]:
        """Build runtime schema lookup tables from the config.

        A module names its target as either ``TARGET_FILES`` (a tuple, for a
        dictionary the two forks spell differently — ``turbulenceProperties``
        and ``momentumTransport`` are the same file renamed in OpenFOAM 8) or
        the original single ``TARGET_FILE``.

        Tables are *merged* per file rather than replaced, so several modules
        can contribute to one dictionary — which is what lets a hand-written
        structural module sit alongside a generated coefficient module without
        either having to know about the other. Later modules win on a collision.
        """
        result: dict[str, dict[str, KeySchema]] = {}

        for module_name in config.get("schema_modules", []):
            try:
                module = importlib.import_module(module_name)
            except ImportError as e:
                logger.warning("Could not import %s: %s", module_name, e)
                continue

            target_files = getattr(module, "TARGET_FILES", None)
            if target_files is None:
                single = getattr(module, "TARGET_FILE", None)
                target_files = (single,) if single else ()
            schemas = getattr(module, "SCHEMAS", None)
            if not isinstance(schemas, dict):
                continue

            for target_file in target_files:
                if not target_file:
                    continue
                # setdefault + update never mutates the module's own SCHEMAS.
                table = result.setdefault(target_file, {})
                clashes = table.keys() & schemas.keys()
                if clashes:
                    logger.debug(
                        "%s overrides %d key(s) for %s: %s",
                        module_name, len(clashes), target_file, sorted(clashes),
                    )
                table.update(schemas)

        return result

    @staticmethod
    def _build_open_namespaces(config: dict) -> dict[str, frozenset[str]]:
        """Collect each file's `OPEN_NAMESPACES` declarations.

        A prefix listed here is a namespace that still permits the flat
        fallback — see `schema_for_file_key`.
        """
        result: dict[str, set[str]] = {}

        for module_name in config.get("schema_modules", []):
            try:
                module = importlib.import_module(module_name)
            except ImportError:
                continue  # already reported by _build_file_key_schemas

            open_ns = getattr(module, "OPEN_NAMESPACES", ())
            if not open_ns:
                continue
            target_files = getattr(module, "TARGET_FILES", None)
            if target_files is None:
                single = getattr(module, "TARGET_FILE", None)
                target_files = (single,) if single else ()
            for target_file in target_files:
                if target_file:
                    result.setdefault(target_file, set()).update(open_ns)

        return {name: frozenset(values) for name, values in result.items()}

    @staticmethod
    def _build_qualified_index(
        file_key_schemas: dict[str, dict[str, KeySchema]],
    ) -> tuple[dict[str, frozenset[str]], dict[str, frozenset[str]]]:
        """Index the dotted keys of each file's table.

        Returns the namespaces (the dotted prefixes a file declares) and the
        owned keys (the suffixes qualified under at least one of them), which
        together decide when `schema_for_file_key` withholds the flat fallback.

        A ``"<prefix>.*"`` wildcard registers its prefix as a namespace but
        contributes no owned key: ``*`` is not a key name, and letting it in
        would arm the closed-namespace guard against every key in the file.
        """
        namespaces: dict[str, frozenset[str]] = {}
        owned_keys: dict[str, frozenset[str]] = {}

        for file_name, schemas in file_key_schemas.items():
            split = [key.split(".", 1) for key in schemas if "." in key]
            namespaces[file_name] = frozenset(prefix for prefix, _ in split)
            owned_keys[file_name] = frozenset(
                suffix for _, suffix in split if suffix != "*"
            )

        return namespaces, owned_keys
