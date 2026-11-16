# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for foam/variants.py (suffixed variants of a known dictionary)."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from foam.variants import clear_variant_cache, header_object, suffixed_base, variant_base

BASES = ("g", "sample", "controlDict", "decomposeParDict", "meshDict", "topoSetDict")


def header(obj: str) -> str:
    return (
        "FoamFile\n{\n    version 2.0;\n    format ascii;\n    class dictionary;\n"
        f"    object {obj};\n}}\n"
    )


@pytest.fixture(autouse=True)
def _fresh():
    clear_variant_cache()
    yield
    clear_variant_cache()


@pytest.mark.parametrize("name, base", [
    ("decomposeParDict.4", "decomposeParDict"),
    ("decomposeParDict-2x3x2", "decomposeParDict"),
    ("decomposeParDict_0.003", "decomposeParDict"),
    ("topoSetDict2", "topoSetDict"),
    ("controlDict.orig", "controlDict"),
    # No separator after the base: a different dictionary, not a variant.
    ("gravitationalProperties", None),
    ("sampleDict", None),
    ("controlDict", None),
    ("fvSchemes", None),
])
def test_suffixed_base(name, base):
    assert suffixed_base(name, BASES) == base


def test_longest_base_wins():
    assert suffixed_base("meshDict.geometry", ("mesh", "meshDict")) == "meshDict"


def test_header_object_one_line_and_none(tmp_path: Path):
    f = tmp_path / "a"
    f.write_text("FoamFile { version 2.0; format ascii; class dictionary; object controlDict; }\n")
    assert header_object(str(f)) == "controlDict"
    g = tmp_path / "b"
    g.write_text("// a fragment\nx 1;\n")
    assert header_object(str(g)) is None
    assert header_object(str(tmp_path / "missing")) is None


def test_header_object_memo_follows_the_file(tmp_path: Path):
    f = tmp_path / "decomposeParDict.4"
    f.write_text(header("decomposeParDict"))
    assert header_object(str(f)) == "decomposeParDict"
    f.write_text(header("somethingElseEntirely"))
    st = f.stat()
    os.utime(f, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))
    assert header_object(str(f)) == "somethingElseEntirely"


class TestVariantBase:
    def test_header_names_the_base(self, tmp_path: Path):
        f = tmp_path / "decomposeParDict.4"
        f.write_text(header("decomposeParDict") + "numberOfSubdomains 4;\n")
        assert variant_base(str(f), BASES) == "decomposeParDict"

    def test_header_names_itself(self, tmp_path: Path):
        f = tmp_path / "topoSetDict.2"
        f.write_text(header("topoSetDict.2"))
        assert variant_base(str(f), BASES) == "topoSetDict"

    def test_header_claims_another_dictionary(self, tmp_path: Path):
        # setAlphaFieldDict.liquid declares `object setFieldsDict;` in the tutorials.
        f = tmp_path / "controlDict.liquid"
        f.write_text(header("setFieldsDict"))
        assert variant_base(str(f), BASES) is None

    def test_no_header_is_a_fragment(self, tmp_path: Path):
        f = tmp_path / "controlDict.settings"
        f.write_text("endTime 1;\n")
        assert variant_base(str(f), BASES) is None

    def test_self_named_fragment_included_by_a_sibling(self, tmp_path: Path):
        # foamyHexMesh: meshDict.geometry has a full header naming itself, and
        # foamyHexMeshDict splices it in with #include.
        frag = tmp_path / "meshDict.geometry"
        frag.write_text(header("meshDict.geometry"))
        assert variant_base(str(frag), BASES) == "meshDict"
        clear_variant_cache()
        includer = header("foamyHexMeshDict") + '#include "meshDict.geometry"\n'
        (tmp_path / "foamyHexMeshDict").write_text(includer)
        assert variant_base(str(frag), BASES) is None

    def test_sibling_include_added_in_place_is_noticed(self, tmp_path: Path):
        frag = tmp_path / "meshDict.geometry"
        frag.write_text(header("meshDict.geometry"))
        includer = tmp_path / "foamyHexMeshDict"
        includer.write_text(header("foamyHexMeshDict"))
        assert variant_base(str(frag), BASES) == "meshDict"
        includer.write_text(header("foamyHexMeshDict") + '#include "meshDict.geometry"\n')
        st = includer.stat()
        os.utime(includer, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))
        assert variant_base(str(frag), BASES) is None

    def test_base_named_header_wins_over_an_include(self, tmp_path: Path):
        # A real variant stays one even if something includes it.
        f = tmp_path / "controlDict.orig"
        f.write_text(header("controlDict"))
        (tmp_path / "other").write_text('#include "controlDict.orig"\n')
        assert variant_base(str(f), BASES) == "controlDict"
