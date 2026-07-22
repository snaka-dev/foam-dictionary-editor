# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for the optional named-dict-list syntax (`sets ( name { … } … );`).

The classic sampleDict style: `sets`/`surfaces` MAY hold a parenthesised list
of named dictionaries, but the same keys also legitimately hold plain word
lists (topoSet's `sets (setA setB);`). A lookahead decides which parse runs.
"""
from __future__ import annotations

from foam.parser import OpenFoamParser
from foam.writer import write_root


def _parse(text: str):
    return OpenFoamParser(text).parse()


_SAMPLE_SETS = """\
sets
(
    y0.1
    {
        type            face;
        axis            x;
        start           (-1 0.218 0);
        end             (1 0.218 0);
    }
    y0.2
    {
        type            face;
        axis            x;
        start           (-1 0.436 0);
        end             (1 0.436 0);
    }
);
"""


def test_sets_named_list_parses_to_named_dict_list():
    root = _parse(_SAMPLE_SETS)
    sets = root.children[0]
    assert sets.node_type == "named_dict_list"
    assert sets.name == "sets"
    assert [c.name for c in sets.children] == ["y0.1", "y0.2"]
    assert all(c.node_type == "named_dict_entry" for c in sets.children)
    start = next(g for g in sets.children[0].children if g.name == "start")
    assert start.node_type == "vector"


def test_surfaces_named_list_parses_to_named_dict_list():
    text = "surfaces\n(\n    cut\n    {\n        type cuttingPlane;\n    }\n);\n"
    root = _parse(text)
    surfaces = root.children[0]
    assert surfaces.node_type == "named_dict_list"
    assert [c.name for c in surfaces.children] == ["cut"]


def test_plain_word_sets_list_stays_raw_list():
    # topoSet source style: `sets (setA setB);` must not become a named block.
    root = _parse("sets (setA setB);\n")
    node = root.children[0]
    assert node.node_type == "raw_list"
    assert node.name == "sets"


def test_plain_string_surfaces_list_stays_raw_list():
    root = _parse('surfaces ("wing.stl");\n')
    node = root.children[0]
    assert node.node_type == "raw_list"


def test_empty_sets_list_stays_plain():
    root = _parse("sets ();\n")
    node = root.children[0]
    assert node.name == "sets"
    assert node.node_type != "named_dict_list"


def test_named_list_nested_inside_function_object_dict():
    text = (
        "functions\n{\n    graphs\n    {\n        type sets;\n"
        "        sets\n        (\n            lineA\n            {\n"
        "                type lineUniform;\n                start (0 0 0);\n"
        "                end (1 0 0);\n            }\n        );\n    }\n}\n"
    )
    root = _parse(text)
    graphs = root.children[0].children[0]
    sets = next(c for c in graphs.children if c.name == "sets")
    assert sets.node_type == "named_dict_list"
    assert [c.name for c in sets.children] == ["lineA"]


def test_named_list_unmodified_roundtrip():
    root = _parse(_SAMPLE_SETS)
    assert write_root(root) == _SAMPLE_SETS


def test_named_list_modified_entry_keeps_sibling_names():
    # Regression: an unmodified sibling's raw_text must include its name.
    root = _parse(_SAMPLE_SETS)
    sets = root.children[0]
    sets.children[0].modified = True
    out = write_root(root)
    assert "y0.1" in out
    assert "y0.2" in out
    reparsed = _parse(out).children[0]
    assert reparsed.node_type == "named_dict_list"
    assert [c.name for c in reparsed.children] == ["y0.1", "y0.2"]
