# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Which overlay a dictionary file feeds -- ui/viewer_dicts.py.

A case can hold the same dictionary several times under non-default names
(`topoSetDict-slices`, `topoSetDict.1`), and `topoSet -dict <name>` runs each. Matching on
the file name alone meant none of them reached the 3-D view.
"""
from __future__ import annotations

import pytest

from foam.parser import OpenFoamParser
from ui import viewer_dicts as vd


def _root(text: str):
    return OpenFoamParser(text).parse()


def _header(obj: str) -> str:
    return f"FoamFile {{ version 2.0; format ascii; class dictionary; object {obj}; }}\n"


class TestDefaultNames:
    @pytest.mark.parametrize(("name", "expected"), [
        ("blockMeshDict", vd.BLOCK_MESH),
        ("topoSetDict", vd.TOPO_SET),
        ("snappyHexMeshDict", vd.SNAPPY_HEX_MESH),
        ("setFieldsDict", vd.SET_FIELDS),
        ("controlDict", vd.SAMPLING),
        ("sample", vd.SAMPLING),
    ])
    def test_a_default_name_is_recognised_without_a_tree(self, name, expected):
        # No parsed tree needed: the name alone settles it, which keeps the common case
        # independent of whether the file has been parsed yet.
        assert vd.viewer_dict_kind(f"/case/system/{name}", None) == expected

    def test_an_unrelated_name_is_not_a_viewer_dict(self):
        assert vd.viewer_dict_kind("/case/system/fvSchemes", _root(_header("fvSchemes"))) is None


class TestNonDefaultNames:
    @pytest.mark.parametrize("name", [
        "topoSetDict-slices", "topoSetDict-background", "topoSetDict.1", "topoSetDict2",
        "topoSetDict.patches", "topoSetDict.f1",
    ])
    def test_the_header_identifies_a_renamed_topo_set_dict(self, name):
        assert vd.viewer_dict_kind(f"/case/system/{name}", _root(_header("topoSetDict"))) == vd.TOPO_SET

    def test_a_header_naming_the_variant_still_resolves(self):
        # 12 tutorial files spell it this way: `object topoSetDict.1;`.
        root = _root(_header("topoSetDict.1"))
        assert vd.viewer_dict_kind("/case/system/topoSetDict.1", root) == vd.TOPO_SET

    @pytest.mark.parametrize(("obj", "expected"), [
        ("blockMeshDict", vd.BLOCK_MESH),
        ("snappyHexMeshDict", vd.SNAPPY_HEX_MESH),
        ("setFieldsDict", vd.SET_FIELDS),
    ])
    def test_the_other_dictionaries_resolve_by_header_too(self, obj, expected):
        assert vd.viewer_dict_kind(f"/case/system/{obj}-variant", _root(_header(obj))) == expected


class TestWhatMustNotBeRecognised:
    def test_an_include_fragment_is_skipped(self):
        # blockMeshDict.resolvedBlocks and friends are named like a dictionary but are a
        # bare list of hex entries #include'd into one. They carry no FoamFile header
        # precisely because they are not dictionaries, and routing one to the block-mesh
        # extractor would replace the real scene with an empty one.
        fragment = _root("hex (0 1 2 3 4 5 6 7) (1 1 1) simpleGrading (1 1 1)\n")
        assert vd.viewer_dict_kind("/case/system/blockMeshDict.resolvedBlocks", fragment) is None

    def test_a_similar_name_without_a_separator_does_not_match(self):
        root = _root(_header("topoSetDictionaryHelper"))
        assert vd.viewer_dict_kind("/case/system/whatever", root) is None

    def test_no_tree_and_no_default_name_is_not_a_guess(self):
        assert vd.viewer_dict_kind("/case/system/topoSetDict-slices", None) is None

    def test_a_renamed_sampling_dict_is_not_recognised(self):
        # Documented limitation: a standalone sample/probes file is one function-object
        # entry with no FoamFile header, so there is nothing to read. It has to be named.
        assert vd.viewer_dict_kind("/case/system/sample-extra", _root("type sets;\n")) is None
