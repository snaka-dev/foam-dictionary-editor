# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""services/domain_bounds.py, and the starting values drawn from it."""
from __future__ import annotations

import pytest

from services.domain_bounds import DomainBounds, domain_bounds
from services.function_templates import parse_template, suggest_values
from tests.services.test_function_templates import (
    FOUNDATION_FORCES,
    OPENCFD_PROBES,
    OPENCFD_SURFACES,
)

_BLOCK = """\
FoamFile { object blockMeshDict; }
scale 0.1;
#include "geometry"
vertices ((0 0 0) ($L 0 0) ($L 1 0) (0 1 0) (0 0 0.1) ($L 0 0.1) ($L 1 0.1) (0 1 0.1));
blocks ( hex (0 1 2 3 4 5 6 7) (20 20 1) simpleGrading (1 1 1) );
"""


def _case(tmp_path, *, snappy=False):
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "blockMeshDict").write_text(_BLOCK)
    (tmp_path / "system" / "geometry").write_text("L 2;\n")
    if snappy:
        (tmp_path / "system" / "snappyHexMeshDict").write_text("geometry {}\n")
    return str(tmp_path)


class TestBounds:
    def test_scaled_with_includes_resolved(self, tmp_path):
        b = domain_bounds(_case(tmp_path))
        assert b.lo == (0.0, 0.0, 0.0)
        assert b.hi == pytest.approx((0.2, 0.1, 0.01))
        assert b.centre == pytest.approx((0.1, 0.05, 0.005))
        assert not b.background

    def test_a_snappy_background_box_says_so(self, tmp_path):
        assert domain_bounds(_case(tmp_path, snappy=True)).background

    def test_the_editors_text_wins(self, tmp_path):
        case = _case(tmp_path)

        def read(path):
            if path.name == "geometry":
                return "L 4;\n"  # unsaved in FoDE
            return None

        assert domain_bounds(case, read_text=read).hi[0] == pytest.approx(0.4)

    def test_no_blockmesh_no_guess(self, tmp_path):
        assert domain_bounds(str(tmp_path)) is None
        (tmp_path / "system").mkdir()
        (tmp_path / "system" / "blockMeshDict").write_text("vertices ();\n")
        assert domain_bounds(str(tmp_path)) is None


_BOX = DomainBounds((0.0, 0.0, 0.0), (0.4, 0.2, 0.02))


class TestSuggestions:
    def test_a_probe_goes_to_the_centre(self):
        assert suggest_values(parse_template(OPENCFD_PROBES), _BOX) == {
            "probeLocations": ("0.2 0.1 0.01", "centre")
        }

    def test_a_line_spans_the_longest_direction_inside_the_walls(self):
        text = "start (0 1e-06 0);\nend (1 1e-06 0);\nfields (U p);\n"
        out = suggest_values(parse_template(text), _BOX)
        assert out["start"] == ("0.0004 0.1 0.01", "line")
        assert out["end"] == ("0.3996 0.1 0.01", "line")

    def test_a_plane_crosses_the_thinnest_direction(self):
        text = "point <point>;\nnormal <normal>;\nfields (<fieldNames>);\n"
        out = suggest_values(parse_template(text), _BOX)
        assert out == {"point": ("0.2 0.1 0.01", "plane"), "normal": ("0 0 1", "plane")}

    def test_cutting_plane_rows_move_to_the_centre_keeping_their_normals(self):
        from services.function_templates import SURFACES_SEPARATOR

        value, reason = suggest_values(parse_template(OPENCFD_SURFACES), _BOX)["surfaces"]
        planes, others = value.split(SURFACES_SEPARATOR)
        assert planes.strip().split("\n") == [
            "xNormal  0.2 0.1 0.01  1 0 0",
            "zNormal  0.2 0.1 0.01  0 0 1",
        ]
        assert "CAD" in others and reason == "planes"

    def test_physics_is_left_alone(self):
        # A centre of rotation is a choice about the body, not the domain.
        assert suggest_values(parse_template(FOUNDATION_FORCES), _BOX) == {}

    def test_nothing_without_a_domain(self):
        assert suggest_values(parse_template(OPENCFD_PROBES), None) == {}
