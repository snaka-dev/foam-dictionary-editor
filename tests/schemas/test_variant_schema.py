# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""A suffixed variant answers from its base dictionary's schema (foam/variants.py)."""
from __future__ import annotations

from pathlib import Path

from foam.variants import clear_variant_cache
from schemas import schema_for_file_key


def _dict(obj: str) -> str:
    return (
        "FoamFile\n{\n    version 2.0;\n    format ascii;\n    class dictionary;\n"
        f"    object {obj};\n}}\nendTime 1;\n"
    )


def test_variant_uses_the_base_schema(tmp_path: Path):
    clear_variant_cache()
    base = tmp_path / "controlDict"
    base.write_text(_dict("controlDict"))
    variant = tmp_path / "controlDict.orig"
    variant.write_text(_dict("controlDict"))
    assert schema_for_file_key(str(base), "endTime") is not None
    assert schema_for_file_key(str(variant), "endTime") is schema_for_file_key(str(base), "endTime")


def test_a_header_that_disagrees_gets_nothing(tmp_path: Path):
    clear_variant_cache()
    other = tmp_path / "controlDict.liquid"
    other.write_text(_dict("setFieldsDict"))
    assert schema_for_file_key(str(other), "endTime") is None


def test_an_included_fragment_gets_nothing(tmp_path: Path):
    clear_variant_cache()
    frag = tmp_path / "controlDict.settings"
    frag.write_text(_dict("controlDict.settings"))
    (tmp_path / "controlDict").write_text(_dict("controlDict") + '#include "controlDict.settings"\n')
    assert schema_for_file_key(str(frag), "endTime") is None
