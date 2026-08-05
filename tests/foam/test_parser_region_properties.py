# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for `regions ( … )`, a key two unrelated dictionaries both claim.

setFieldsDict writes `regions ( boxToCell { … } );` — named dictionaries, which
is what the 3-D overlay reads. constant/regionProperties writes
`regions ( fluid (bottomAir topAir) solid (heater leftSolid rightSolid) );` — a
list of name/word-list pairs that has nothing to do with setFields.

The key used to take the named-dict path unconditionally, so regionProperties
parsed as two nameless unknown_raw_entry nodes: the one file naming a
multi-region case's regions was the one file about it that could not be edited
through the tree. It is gated by the same lookahead `sets`/`surfaces` use now,
so the named-dict parse runs only when the content is actually named dicts.
"""
from __future__ import annotations

from pathlib import Path

from foam.parser import OpenFoamParser
from foam.writer import write_root

ROOT = Path(__file__).resolve().parents[2]

_REGION_PROPERTIES = """\
regions
(
    fluid       (bottomAir topAir)
    solid       (heater leftSolid rightSolid)
);
"""

_SET_FIELDS_REGIONS = """\
regions
(
    boxToCell
    {
        box (0 0 -1) (0.1461 0.292 1);
        fieldValues
        (
            volScalarFieldValue alpha.water 1
        );
    }
);
"""


def _parse(text: str):
    return OpenFoamParser(text).parse()


def _entry(root, name: str):
    return next(c for c in root.children if c.name == name)


class TestRegionProperties:
    def test_parses_as_a_single_entry(self):
        # The bug: two nameless unknown_raw_entry nodes, one holding the bare
        # word `regions` and one holding the whole parenthesised body.
        root = _parse(_REGION_PROPERTIES)
        assert [c.node_type for c in root.children] == ["raw_list"]
        assert root.children[0].name == "regions"

    def test_keeps_the_pairs_in_its_value(self):
        node = _entry(_parse(_REGION_PROPERTIES), "regions")
        assert "fluid (bottomAir topAir)" in node.value
        assert "solid (heater leftSolid rightSolid)" in node.value

    def test_produces_no_parse_errors(self):
        parser = OpenFoamParser(_REGION_PROPERTIES)
        parser.parse()
        assert parser.errors == []

    def test_round_trips_byte_for_byte(self):
        assert write_root(_parse(_REGION_PROPERTIES)) == _REGION_PROPERTIES

    def test_the_bundled_tutorial_file_parses_and_round_trips(self):
        path = ROOT / "tutorials" / "snappyMultiRegionHeater" / "constant" / "regionProperties"
        text = path.read_text(encoding="utf-8")
        parser = OpenFoamParser(text)
        root = parser.parse()
        assert parser.errors == []
        assert not any(c.node_type == "unknown_raw_entry" for c in root.children)
        assert _entry(root, "regions").node_type == "raw_list"
        assert write_root(root) == text


class TestSetFieldsRegionsStillWins:
    """The gate must not cost setFieldsDict its structured parse."""

    def test_named_dicts_still_parse_as_a_region_block(self):
        node = _entry(_parse(_SET_FIELDS_REGIONS), "regions")
        assert node.node_type == "region_block"
        assert [c.node_type for c in node.children] == ["region_entry"]
        assert node.children[0].name == "boxToCell"

    def test_round_trips_byte_for_byte(self):
        assert write_root(_parse(_SET_FIELDS_REGIONS)) == _SET_FIELDS_REGIONS

    def test_the_bundled_tutorial_file_still_gives_a_region_block(self):
        path = ROOT / "tutorials" / "damBreak" / "system" / "setFieldsDict"
        text = path.read_text(encoding="utf-8")
        root = OpenFoamParser(text).parse()
        assert _entry(root, "regions").node_type == "region_block"
        assert write_root(root) == text


class TestOtherRegionsShapes:
    def test_a_plain_word_list_is_a_raw_list(self):
        # Also broken before the gate: `regions` committed to the named-dict
        # path on the strength of the key alone, whatever followed it.
        node = _entry(_parse("regions ( a b c );\n"), "regions")
        assert node.node_type == "raw_list"
        assert node.value == "a b c"

    def test_an_empty_list_does_not_raise(self):
        parser = OpenFoamParser("regions ( );\n")
        root = parser.parse()
        assert parser.errors == []
        assert _entry(root, "regions").node_type != "unknown_raw_entry"

    def test_regions_matches_an_identically_shaped_entry_under_another_key(self):
        # The rule the fix restores: `regions` is only special when its content
        # is, so anything else parses exactly as any other key would.
        theirs = _entry(_parse(_REGION_PROPERTIES.replace("regions", "zones", 1)), "zones")
        ours = _entry(_parse(_REGION_PROPERTIES), "regions")
        assert ours.node_type == theirs.node_type
        assert ours.value == theirs.value
