# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for sampling_extractor: probes, sample lines, and sample planes."""
from __future__ import annotations

import pytest

from foam.parser import OpenFoamParser
from foam.sampling_extractor import extract_sampling_data


def _parse(text: str):
    return OpenFoamParser(text).parse()


CONTROL_HEADER = """\
FoamFile { version 2.0; format ascii; class dictionary; object controlDict; }
application icoFoam;
endTime 1;
"""


def _functions(*entries: str) -> str:
    return CONTROL_HEADER + "functions\n{\n" + "\n".join(entries) + "\n}\n"


def test_empty_control_dict():
    data = extract_sampling_data(_parse(CONTROL_HEADER))
    assert data.shapes == []
    assert data.non_geometric == []


def test_probes_in_functions_block():
    src = _functions("""\
    myProbes
    {
        type probes;
        libs (sampling);
        fields (p U);
        probeLocations
        (
            (0.1 0.2 0.3)
            (0.4 0.5 0.6)
        );
    }
""")
    data = extract_sampling_data(_parse(src))
    assert len(data.shapes) == 1
    s = data.shapes[0]
    assert s.label == "myProbes"
    assert s.kind == "probes"
    assert s.geometry == {"points": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]}


def test_sets_dict_form_lines():
    src = _functions("""\
    graphs
    {
        type sets;
        libs (sampling);
        fields (U);
        sets
        {
            lineA
            {
                type lineUniform;
                axis distance;
                start (0 0 0);
                end   (1 0 0);
                nPoints 100;
            }
            cloudA
            {
                type cloud;
                axis xyz;
                points ( (0.1 0.1 0.1) );
            }
            noGeo
            {
                type midPoint;
                axis distance;
            }
        }
    }
""")
    data = extract_sampling_data(_parse(src))
    kinds = {s.label: s.kind for s in data.shapes}
    assert kinds == {"graphs.lineA": "lineUniform", "graphs.cloudA": "cloud"}
    line = next(s for s in data.shapes if s.label == "graphs.lineA")
    assert line.geometry == {"start": [0.0, 0.0, 0.0], "end": [1.0, 0.0, 0.0]}
    cloud = next(s for s in data.shapes if s.label == "graphs.cloudA")
    assert cloud.geometry == {"points": [[0.1, 0.1, 0.1]]}
    assert [s.label for s in data.non_geometric] == ["graphs.noGeo"]


def test_sets_list_form_recovered_from_raw_entry():
    # The parenthesised list form (classic sampleDict style) is stored raw by
    # the tolerant parser; the extractor re-parses the block's inner text.
    src = _functions("""\
    graphs
    {
        type sets;
        sets
        (
            lineA { type lineUniform; start (0 0 0); end (1 0 0); nPoints 10; }
            lineB { type face; axis x; start (0 1 0); end (1 1 0); }
        );
    }
""")
    data = extract_sampling_data(_parse(src))
    assert [s.label for s in data.shapes] == ["graphs.lineA", "graphs.lineB"]
    assert data.shapes[1].geometry == {"start": [0.0, 1.0, 0.0], "end": [1.0, 1.0, 0.0]}
    assert data.non_geometric == []


def test_sets_list_form_at_file_root():
    # Standalone sampleDict layout: `type sets;` and the member list at root.
    src = """\
FoamFile { version 2.0; format ascii; class dictionary; object sampleDict; }
interpolationScheme cellPointFace;
setFormat raw;
type sets;
sets
(
    y0.1 { type face; axis x; start (-1 0.218 0); end (1 0.218 0); }
    y0.2 { type face; axis x; start (-1 0.436 0); end (1 0.436 0); }
);
fields ( T U );
"""
    data = extract_sampling_data(_parse(src))
    assert [s.label for s in data.shapes] == ["y0.1", "y0.2"]
    assert all(s.kind == "face" for s in data.shapes)


def test_surfaces_list_form_recovered_from_raw_entry():
    src = _functions("""\
    surf
    {
        type surfaces;
        surfaces
        (
            cut { type cuttingPlane; point (0 0 0.5); normal (0 1 0); }
        );
    }
""")
    data = extract_sampling_data(_parse(src))
    assert [s.label for s in data.shapes] == ["surf.cut"]
    assert data.shapes[0].geometry["planeNormal"] == [0.0, 1.0, 0.0]


def test_sets_missing_member_list_is_non_geometric():
    src = _functions("""\
    graphs
    {
        type sets;
        fields (U);
    }
""")
    data = extract_sampling_data(_parse(src))
    assert data.shapes == []
    assert len(data.non_geometric) == 1
    assert data.non_geometric[0].kind == "sets"


def test_surfaces_plane_and_cutting_plane_and_patch():
    src = _functions("""\
    surf
    {
        type surfaces;
        libs (sampling);
        surfaces
        {
            planeXY
            {
                type plane;
                planeType pointAndNormal;
                pointAndNormalDict
                {
                    point  (0.1 0.1 0.005);
                    normal (0 0 1);
                }
            }
            cutter
            {
                type cuttingPlane;
                point  (0 0 0.5);
                normal (0 1 0);
                interpolate true;
            }
            wallSurf
            {
                type patch;
                patches (walls);
            }
        }
    }
""")
    data = extract_sampling_data(_parse(src))
    labels = {s.label: s for s in data.shapes}
    assert set(labels) == {"surf.planeXY", "surf.cutter"}
    assert labels["surf.planeXY"].geometry == {
        "planePoint": [0.1, 0.1, 0.005], "planeNormal": [0.0, 0.0, 1.0],
    }
    assert labels["surf.cutter"].kind == "cuttingPlane"
    assert labels["surf.cutter"].geometry["planeNormal"] == [0.0, 1.0, 0.0]
    assert [s.label for s in data.non_geometric] == ["surf.wallSurf"]
    assert data.non_geometric[0].kind == "patch"


def test_unrelated_function_objects_ignored():
    src = _functions("""\
    forces1
    {
        type forces;
        patches (hull);
    }
""")
    data = extract_sampling_data(_parse(src))
    assert data.shapes == []
    assert data.non_geometric == []


def test_standalone_single_graph_root_level_line():
    src = """\
FoamFile { version 2.0; format ascii; class dictionary; object singleGraph; }
start (0 0 0);
end   (0 2 0);
fields (U p);
"""
    data = extract_sampling_data(_parse(src))
    assert len(data.shapes) == 1
    s = data.shapes[0]
    assert s.label == ""
    assert s.kind == "line"
    assert s.geometry == {"start": [0.0, 0.0, 0.0], "end": [0.0, 2.0, 0.0]}


def test_standalone_sample_file_root_type_sets():
    src = """\
FoamFile { version 2.0; format ascii; class dictionary; object sample; }
type sets;
interpolationScheme cellPoint;
setFormat raw;
fields (U);
sets
{
    centerline
    {
        type lineCell;
        axis x;
        start (0 0.05 0.005);
        end   (2 0.05 0.005);
    }
}
"""
    data = extract_sampling_data(_parse(src))
    assert [s.label for s in data.shapes] == ["centerline"]
    assert data.shapes[0].kind == "lineCell"


def test_standalone_probes_file_root_level():
    src = """\
FoamFile { version 2.0; format ascii; class dictionary; object probes; }
type probes;
fields (p);
probeLocations ( (1 2 3) );
"""
    data = extract_sampling_data(_parse(src))
    assert len(data.shapes) == 1
    assert data.shapes[0].label == ""
    assert data.shapes[0].geometry == {"points": [[1.0, 2.0, 3.0]]}


def test_variable_substitution_in_line():
    src = """\
FoamFile { version 2.0; format ascii; class dictionary; object singleGraph; }
x0 0.5;
start ($x0 0 0);
end   ($x0 1 0);
fields (U);
"""
    data = extract_sampling_data(_parse(src))
    assert len(data.shapes) == 1
    geo = data.shapes[0].geometry
    assert geo["start"] == pytest.approx([0.5, 0.0, 0.0])
    assert geo["end"] == pytest.approx([0.5, 1.0, 0.0])


def test_probes_without_locations_is_non_geometric():
    src = _functions("""\
    badProbes
    {
        type probes;
        fields (p);
    }
""")
    data = extract_sampling_data(_parse(src))
    assert data.shapes == []
    assert [s.kind for s in data.non_geometric] == ["probes"]
