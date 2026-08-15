# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Shinji NAKAGAWA
"""`KeySchema.default` / `.required` -- what happens when a key is omitted.

The two are one question with two answers, so the Detail pane gives them one
row and this module guards the thing that would make that row incoherent: a
schema claiming both a default and that there is no default. See
`schemas/_base.py` for the field contract and DEVELOPER.md's "Recording what a
key *is*" for why the fact lives in a field rather than in `description` prose.

The fields exist because the viscosity models need them: `CrossPowerLaw.C:71-78`
reads `nu0`, `nuInf`, `m` and `n` as required entries with no fallback, and
before this there was no way to say so except in a sentence no code could read.
"""
from __future__ import annotations

import importlib

import pytest

from schemas._base import KeySchema
from schemas.builtin import get_default_schema_config

MODULES = get_default_schema_config()["schema_modules"]


def _all_schemas():
    """Every registered `KeySchema`, as (module, table key, schema) triples."""
    for mod_name in MODULES:
        mod = importlib.import_module(mod_name)
        for table_key, schema in getattr(mod, "SCHEMAS", {}).items():
            yield mod_name, table_key, schema


class TestFieldContract:
    def test_defaults_are_backward_compatible(self):
        # Every pre-existing entry was built without these fields, so the
        # defaults have to be the "says nothing" values or 12,501 lines of
        # generated schema would start making claims nobody measured.
        bare = KeySchema(key="k", label="K", description="d")
        assert bare.default == ""
        assert bare.required is False

    @pytest.mark.parametrize("mod_name", MODULES)
    def test_no_schema_claims_both(self, mod_name):
        # The contradiction the shared Detail-pane row cannot render: a key
        # cannot both fall back to something and require you to supply it.
        mod = importlib.import_module(mod_name)
        both = [
            key for key, schema in getattr(mod, "SCHEMAS", {}).items()
            if schema.default and schema.required
        ]
        assert not both, (
            f"{mod_name}: {both} set both `default` and `required`; they are "
            "mutually exclusive -- `required` means there is no default"
        )

    def test_empty_default_is_silence_not_a_claim(self):
        # An empty `default` must never be read as "no default exists" -- the
        # generated turbulence modules carry their defaults in `description`
        # prose and leave the field empty, so treating "" as a claim would
        # mark every one of them required.
        quiet = KeySchema(key="k", label="K", description="d")
        assert quiet.default == "" and quiet.required is False


class TestRendering:
    """`_if_omitted_text` is the whole of the pane's behaviour for these."""

    def test_default_is_rendered(self):
        from ui.panels.detail_panel import _if_omitted_text

        schema = KeySchema(key="k", label="K", description="d", default="0.09")
        assert "0.09" in _if_omitted_text(schema)

    def test_required_is_rendered(self):
        from ui.panels.detail_panel import _if_omitted_text

        schema = KeySchema(key="k", label="K", description="d", required=True)
        assert _if_omitted_text(schema) != ""

    def test_default_wins_over_required(self):
        # Belt and braces for a combination test_no_schema_claims_both forbids:
        # if one ever slips through, show the concrete value rather than a
        # claim that contradicts it.
        from ui.panels.detail_panel import _if_omitted_text

        schema = KeySchema(
            key="k", label="K", description="d", default="0.09", required=True
        )
        assert "0.09" in _if_omitted_text(schema)

    def test_neither_renders_nothing(self):
        from ui.panels.detail_panel import _if_omitted_text

        assert _if_omitted_text(KeySchema(key="k", label="K", description="d")) == ""

    def test_none_is_tolerated(self):
        from ui.panels.detail_panel import _if_omitted_text

        assert _if_omitted_text(None) == ""
