# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for foam/include_expand: splicing #include'd entries for the viewer."""
from __future__ import annotations

from pathlib import Path

import pytest

from foam.block_mesh_extractor import extract_block_mesh_data
from foam.include_expand import clear_expand_cache, expand_includes
from foam.parser import OpenFoamParser

HEADER = "FoamFile { version 2.0; format ascii; class dictionary; object d; }\n"


@pytest.fixture(autouse=True)
def _clear_cache():
    """The parse memo is process-wide; a tmp_path reused across tests must not hit it."""
    clear_expand_cache()
    yield
    clear_expand_cache()


def _case(tmp_path: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    return tmp_path


def _expand(tmp_path: Path, main: str, **kwargs):
    root = OpenFoamParser((tmp_path / main).read_text()).parse()
    return root, expand_includes(
        root, source_file=tmp_path / main, case_dir=tmp_path, **kwargs
    )


# ── the basic splice ──────────────────────────────────────────────────────────

def test_top_level_entries_are_spliced_in(tmp_path):
    _case(tmp_path, {
        "system/settings": "a 1;\nb 2;\n",
        "system/d": HEADER + '#include "settings"\nc 3;\n',
    })
    _, result = _expand(tmp_path, "system/d")

    assert result.expanded
    assert result.unresolved == ()
    assert result.sources == frozenset({str(tmp_path / "system/settings")})
    names = [c.name for c in result.root.children]
    assert names == ["FoamFile", "a", "b", "c"]


def test_document_order_is_preserved(tmp_path):
    """OpenFOAM inserts textually, so a later definition shadows an earlier one."""
    _case(tmp_path, {
        "system/settings": "a 2;\n",
        "system/d": HEADER + "a 1;\n#include \"settings\"\na 3;\n",
    })
    _, result = _expand(tmp_path, "system/d")
    assert [c.value for c in result.root.children if c.name == "a"] == [1, 2, 3]


def test_foam_file_header_of_the_include_is_dropped(tmp_path):
    _case(tmp_path, {
        "system/settings": HEADER + "a 1;\n",
        "system/d": HEADER + '#include "settings"\n',
    })
    _, result = _expand(tmp_path, "system/d")
    assert [c.name for c in result.root.children] == ["FoamFile", "a"]


def test_original_tree_is_not_mutated(tmp_path):
    _case(tmp_path, {
        "system/settings": "a 1;\n",
        "system/d": HEADER + '#include "settings"\n',
    })
    root, result = _expand(tmp_path, "system/d")

    assert result.root is not root
    assert [c.name for c in root.children] == ["FoamFile", ""]
    assert root.children[1].node_type == "directive_entry"


def test_no_includes_returns_the_same_object(tmp_path):
    """The common case must allocate nothing."""
    _case(tmp_path, {"system/d": HEADER + "a 1;\n"})
    root, result = _expand(tmp_path, "system/d")

    assert result.root is root
    assert not result.expanded
    assert result.sources == frozenset()


# ── depth: nested positions and transitive includes ───────────────────────────

def test_include_inside_a_dictionary_is_expanded(tmp_path):
    _case(tmp_path, {
        "system/inner": "type wall;\n",
        "system/d": HEADER + 'boundary\n{\n    #include "inner"\n    nFaces 4;\n}\n',
    })
    _, result = _expand(tmp_path, "system/d")

    boundary = next(c for c in result.root.children if c.name == "boundary")
    assert [c.name for c in boundary.children] == ["type", "nFaces"]


def test_include_is_transitive(tmp_path):
    _case(tmp_path, {
        "system/deep": "b 2;\n",
        "system/settings": 'a 1;\n#include "deep"\n',
        "system/d": HEADER + '#include "settings"\n',
    })
    _, result = _expand(tmp_path, "system/d")

    assert [c.name for c in result.root.children] == ["FoamFile", "a", "b"]
    assert result.sources == {
        str(tmp_path / "system/settings"), str(tmp_path / "system/deep")
    }


def test_depth_cap_stops_expansion(tmp_path):
    _case(tmp_path, {
        "system/deep": "b 2;\n",
        "system/settings": 'a 1;\n#include "deep"\n',
        "system/d": HEADER + '#include "settings"\n',
    })
    _, result = _expand(tmp_path, "system/d", max_depth=1)

    assert [c.name for c in result.root.children] == ["FoamFile", "a", ""]
    assert result.sources == {str(tmp_path / "system/settings")}


# ── failures are non-events ───────────────────────────────────────────────────

def test_missing_include_is_left_in_place_and_reported(tmp_path):
    _case(tmp_path, {"system/d": HEADER + '#include "absent"\na 1;\n'})
    _, result = _expand(tmp_path, "system/d")

    assert not result.expanded
    assert result.unresolved == ('#include "absent"',)
    assert result.root.children[1].node_type == "directive_entry"


def test_missing_optional_include_is_not_reported(tmp_path):
    """A #sinclude whose target is absent is legal OpenFOAM, not a problem."""
    _case(tmp_path, {"system/d": HEADER + '#sinclude "absent"\n'})
    _, result = _expand(tmp_path, "system/d")

    assert result.unresolved == ()


def test_cycle_is_broken(tmp_path):
    _case(tmp_path, {
        "system/b": 'x 1;\n#include "d"\n',
        "system/d": HEADER + '#include "b"\n',
    })
    _, result = _expand(tmp_path, "system/d")

    assert [c.name for c in result.root.children] == ["FoamFile", "x", ""]
    assert result.unresolved == ('#include "d"',)


def test_self_include_is_broken(tmp_path):
    _case(tmp_path, {"system/d": HEADER + '#include "d"\n'})
    _, result = _expand(tmp_path, "system/d")

    assert not result.expanded
    assert result.unresolved == ('#include "d"',)


def test_include_func_is_not_expanded(tmp_path):
    """Its target is already listed and rendered standalone; splicing duplicates."""
    _case(tmp_path, {
        "system/mag": "type sets;\n",
        "system/d": HEADER + "functions { #includeFunc mag }\n",
    })
    _, result = _expand(tmp_path, "system/d")

    assert not result.expanded
    assert result.unresolved == ()


# ── unsaved buffers ───────────────────────────────────────────────────────────

def test_read_text_wins_over_disk(tmp_path):
    _case(tmp_path, {
        "system/settings": "a 1;\n",
        "system/d": HEADER + '#include "settings"\n',
    })
    settings = tmp_path / "system/settings"

    def read_text(path: Path) -> str | None:
        return "a 99;\n" if path == settings else None

    _, result = _expand(tmp_path, "system/d", read_text=read_text)
    assert next(c for c in result.root.children if c.name == "a").value == 99


def test_read_text_returning_none_falls_back_to_disk(tmp_path):
    _case(tmp_path, {
        "system/settings": "a 1;\n",
        "system/d": HEADER + '#include "settings"\n',
    })
    _, result = _expand(tmp_path, "system/d", read_text=lambda _p: None)
    assert next(c for c in result.root.children if c.name == "a").value == 1


# ── end to end, mirroring the real case ───────────────────────────────────────

def test_block_mesh_geometry_defined_entirely_in_an_include(tmp_path):
    """The shape that motivated this: every dimension lives in one shared file."""
    _case(tmp_path, {
        "system/settings-region": (
            "scale 0.001;\n"
            "x0 0; y0 0; z0 0;\n"
            "xLead 0.7; yMargin 0.5; yLead 2.5;\n"
            "xMax #eval{$xLead + 5.3};\n"
            "yMax #eval{$yLead + $yMargin};\n"
            "zMax $xMax;\n"
            "CS 0.175;\n"
            "nX #eval{round($xMax/$CS)};\n"
        ),
        "system/blockMeshDict": HEADER + """#include "settings-region"
vertices
(
    ($x0 $y0 $z0) ($xMax $y0 $z0) ($xMax $yMax $z0) ($x0 $yMax $z0)
    ($x0 $y0 $zMax) ($xMax $y0 $zMax) ($xMax $yMax $zMax) ($x0 $yMax $zMax)
);
blocks ( hex (0 1 2 3 4 5 6 7) ($nX $nX $nX) simpleGrading (1 1 1) );
""",
    })
    root, result = _expand(tmp_path, "system/blockMeshDict")

    # Without the expansion there is nothing to draw at all.
    assert extract_block_mesh_data(root).vertices == []

    data = extract_block_mesh_data(result.root)
    assert data.scale == 0.001
    assert len(data.vertices) == 8
    assert len(data.hex_blocks) == 1
    # 6 x 3 x 6 mm, in metres after the include's own `scale` is applied.
    assert [max(v[i] for v in data.vertices) for i in range(3)] == [0.006, 0.003, 0.006]


def test_two_dicts_share_one_settings_file(tmp_path):
    """Both report the same source, which is what drives the dependent refresh."""
    _case(tmp_path, {
        "system/settings": "a 1;\n",
        "system/blockMeshDict": HEADER + '#include "settings"\n',
        "system/topoSetDict": HEADER + '#include "settings"\n',
    })
    _, bm = _expand(tmp_path, "system/blockMeshDict")
    _, ts = _expand(tmp_path, "system/topoSetDict")

    assert bm.sources == ts.sources == frozenset({str(tmp_path / "system/settings")})
