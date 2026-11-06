# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for snappy_hex_mesh_extractor: geometry extraction, refinementSurfaces/
Regions cross-referencing, locationInMesh(s), and $var / #eval resolution."""
from __future__ import annotations

import gzip

import pytest

from foam.parser import OpenFoamParser
from foam.snappy_hex_mesh_extractor import extract_snappy_hex_mesh_data

HEADER = """\
FoamFile { version 2.0; format ascii; class dictionary; object snappyHexMeshDict; }
"""


def _parse(text: str):
    return OpenFoamParser(HEADER + text).parse()


def _shape_by_name(data, name):
    return next(s for s in data.shapes if s.label == name)


# ── geometry primitives ───────────────────────────────────────────────────────

def test_empty_dict():
    root = _parse("")
    data = extract_snappy_hex_mesh_data(root)
    assert data.shapes == []
    assert data.non_geometric == []
    assert data.location_points == []


def test_box_geometry():
    root = _parse("""
        geometry
        {
            box1 { type box; min (0 0 0); max (1 1 1); }
        }
    """)
    data = extract_snappy_hex_mesh_data(root)
    shape = _shape_by_name(data, "box1")
    assert shape.kind == "box"
    assert shape.geometry["box"] == [[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]
    assert shape.category == "geometry"


def test_sphere_scalar_radius():
    root = _parse("""
        geometry
        {
            ball { type sphere; centre (1 2 3); radius 0.5; }
        }
    """)
    data = extract_snappy_hex_mesh_data(root)
    shape = _shape_by_name(data, "ball")
    assert shape.geometry["centre"] == [1.0, 2.0, 3.0]
    assert shape.geometry["radius"] == 0.5


def test_sphere_vector_radius_ellipsoid():
    root = _parse("""
        geometry
        {
            igloo { type sphere; origin (3 3 0); radius (3.5 3.5 4); }
        }
    """)
    data = extract_snappy_hex_mesh_data(root)
    shape = _shape_by_name(data, "igloo")
    assert shape.geometry["centre"] == [3.0, 3.0, 0.0]
    assert shape.geometry["radius"] == [3.5, 3.5, 4.0]


def test_cylinder_geometry():
    root = _parse("""
        geometry
        {
            cyl1 { type cylinder; point1 (0 0 -1); point2 (0 0 1); radius 0.1; }
        }
    """)
    data = extract_snappy_hex_mesh_data(root)
    shape = _shape_by_name(data, "cyl1")
    assert shape.geometry["p1"] == [0.0, 0.0, -1.0]
    assert shape.geometry["p2"] == [0.0, 0.0, 1.0]
    assert shape.geometry["radius"] == 0.1


def test_cone_geometry():
    root = _parse("""
        geometry
        {
            cone1 { type cone; point1 (0 0 0); point2 (0 0 2); radius1 1; radius2 0; }
        }
    """)
    data = extract_snappy_hex_mesh_data(root)
    shape = _shape_by_name(data, "cone1")
    assert shape.geometry["radius1"] == 1.0
    assert shape.geometry["radius2"] == 0.0


def test_collection_type_is_non_geometric():
    root = _parse("""
        geometry
        {
            twoFridgeFreezers { type collection; mergeSubRegions true; }
        }
    """)
    data = extract_snappy_hex_mesh_data(root)
    assert data.shapes == []
    assert [s.label for s in data.non_geometric] == ["twoFridgeFreezers"]


# ── collection (searchableSurfaceCollection) box members ─────────────────────

def test_collection_box_members_rotation_none_and_identity_axes():
    """Real igloo tutorial case: `seal` uses `rotation none`, `herring` uses
    e1/e3 axes that happen to also be the identity frame — both should place
    the same 1x1x1 box (scaled to 1x1x2.1) at their own `transform.origin`."""
    root = _parse("""
        geometry
        {
            box1 { type box; min (0 0 0); max (1 1 1); }
            twoFridgeFreezers
            {
                type collection;
                mergeSubRegions true;
                seal
                {
                    surface box1;
                    scale (1.0 1.0 2.1);
                    transform { origin (2 2 0); rotation none; }
                }
                herring
                {
                    surface box1;
                    scale (1.0 1.0 2.1);
                    transform { origin (3.5 3 0); e1 (1 0 0); e3 (0 0 1); }
                }
            }
        }
    """)
    data = extract_snappy_hex_mesh_data(root)
    seal = _shape_by_name(data, "twoFridgeFreezers.seal")
    herring = _shape_by_name(data, "twoFridgeFreezers.herring")
    assert seal.kind == "collection_box"
    for shape, origin in ((seal, [2.0, 2.0, 0.0]), (herring, [3.5, 3.0, 0.0])):
        assert shape.geometry["origin"] == origin
        assert shape.geometry["i"] == [1.0, 0.0, 0.0]
        assert shape.geometry["j"] == [0.0, 1.0, 0.0]
        assert shape.geometry["k"] == [0.0, 0.0, 2.1]
    assert not any(s.label == "twoFridgeFreezers" for s in data.non_geometric)


def test_collection_box_member_with_actual_rotation():
    """e1=(0,1,0), e3=(0,0,1) rotates the box's local X extent onto world Y."""
    root = _parse("""
        geometry
        {
            box1 { type box; min (0 0 0); max (2 1 1); }
            coll
            {
                type collection;
                rotated
                {
                    surface box1;
                    transform { origin (0 0 0); e1 (0 1 0); e3 (0 0 1); }
                }
            }
        }
    """)
    data = extract_snappy_hex_mesh_data(root)
    shape = _shape_by_name(data, "coll.rotated")
    # Local size (2, 1, 1) rotated so local-X -> world-Y, local-Y -> world -X.
    assert shape.geometry["origin"] == [0.0, 0.0, 0.0]
    assert shape.geometry["i"] == [0.0, 2.0, 0.0]
    assert shape.geometry["j"] == [-1.0, 0.0, 0.0]
    assert shape.geometry["k"] == [0.0, 0.0, 1.0]


def test_collection_member_with_non_box_base_is_skipped():
    root = _parse("""
        geometry
        {
            ball { type sphere; centre (0 0 0); radius 1; }
            coll
            {
                type collection;
                inst { surface ball; transform { origin (0 0 0); rotation none; } }
            }
        }
    """)
    data = extract_snappy_hex_mesh_data(root)
    assert not any(s.label.startswith("coll.") for s in data.shapes)
    assert [s.label for s in data.non_geometric if s.label == "coll"] == ["coll"]


def test_collection_member_missing_transform_is_skipped():
    root = _parse("""
        geometry
        {
            box1 { type box; min (0 0 0); max (1 1 1); }
            coll
            {
                type collection;
                inst { surface box1; }
            }
        }
    """)
    data = extract_snappy_hex_mesh_data(root)
    assert not any(s.label.startswith("coll.") for s in data.shapes)
    assert [s.label for s in data.non_geometric if s.label == "coll"] == ["coll"]


# ── name resolution (entry key vs. `name` override) ───────────────────────────

def test_name_override_for_triSurfaceMesh(tmp_path):
    case_dir = tmp_path
    tri_dir = case_dir / "constant" / "triSurface"
    tri_dir.mkdir(parents=True)
    (tri_dir / "geom.stl").write_text("solid geom\nendsolid geom\n")

    root = _parse("""
        geometry
        {
            geom.stl { type triSurfaceMesh; name geom; }
        }
        castellatedMeshControls
        {
            refinementSurfaces { geom { level (1 1); } }
        }
    """)
    data = extract_snappy_hex_mesh_data(root, case_dir=str(case_dir))
    shape = _shape_by_name(data, "geom")
    assert shape.kind == "triSurfaceMesh"
    assert shape.geometry["stl_path"] == str(tri_dir / "geom.stl")
    assert shape.category == "surface"
    assert shape.level == (1.0, 1.0)


def test_triSurfaceMesh_missing_file_is_non_geometric(tmp_path):
    root = _parse("""
        geometry
        {
            geom.stl { type triSurfaceMesh; name geom; }
        }
    """)
    data = extract_snappy_hex_mesh_data(root, case_dir=str(tmp_path))
    assert data.shapes == []
    assert [s.label for s in data.non_geometric] == ["geom"]


def test_triSurfaceMesh_no_case_dir_is_non_geometric():
    root = _parse("""
        geometry
        {
            geom.stl { type triSurfaceMesh; name geom; }
        }
    """)
    data = extract_snappy_hex_mesh_data(root)
    assert data.shapes == []
    assert [s.label for s in data.non_geometric] == ["geom"]


def test_distributedTriSurfaceMesh_explicit_file(tmp_path):
    case_dir = tmp_path
    tri_dir = case_dir / "constant" / "triSurface"
    tri_dir.mkdir(parents=True)
    (tri_dir / "box.obj").write_text("# obj\n")

    root = _parse("""
        geometry
        {
            box { type distributedTriSurfaceMesh; file "box.obj"; }
        }
    """)
    data = extract_snappy_hex_mesh_data(root, case_dir=str(case_dir))
    shape = _shape_by_name(data, "box")
    assert shape.geometry["stl_path"] == str(tri_dir / "box.obj")


# ── gzip-compressed triSurface files ──────────────────────────────────────────

def test_triSurfaceMesh_resolves_gz_sibling(tmp_path):
    case_dir = tmp_path
    tri_dir = case_dir / "constant" / "triSurface"
    tri_dir.mkdir(parents=True)
    (tri_dir / "motorBike.obj.gz").write_bytes(gzip.compress(b"# obj\n"))

    root = _parse("""
        geometry
        {
            motorBike.obj { type triSurfaceMesh; name motorBike; }
        }
    """)
    data = extract_snappy_hex_mesh_data(root, case_dir=str(case_dir))
    shape = _shape_by_name(data, "motorBike")
    assert shape.geometry["stl_path"] == str(tri_dir / "motorBike.obj.gz")


def test_triSurfaceMesh_gz_entry_key_resolves(tmp_path):
    case_dir = tmp_path
    tri_dir = case_dir / "constant" / "triSurface"
    tri_dir.mkdir(parents=True)
    (tri_dir / "motorBike.obj.gz").write_bytes(gzip.compress(b"# obj\n"))

    root = _parse("""
        geometry
        {
            motorBike.obj.gz { type triSurfaceMesh; name motorBike; }
        }
    """)
    data = extract_snappy_hex_mesh_data(root, case_dir=str(case_dir))
    shape = _shape_by_name(data, "motorBike")
    assert shape.geometry["stl_path"] == str(tri_dir / "motorBike.obj.gz")


def test_triSurfaceMesh_gz_reference_uncompressed_fallback(tmp_path):
    case_dir = tmp_path
    tri_dir = case_dir / "constant" / "triSurface"
    tri_dir.mkdir(parents=True)
    (tri_dir / "motorBike.obj").write_text("# obj\n")

    root = _parse("""
        geometry
        {
            motorBike.obj.gz { type triSurfaceMesh; name motorBike; }
        }
    """)
    data = extract_snappy_hex_mesh_data(root, case_dir=str(case_dir))
    shape = _shape_by_name(data, "motorBike")
    assert shape.geometry["stl_path"] == str(tri_dir / "motorBike.obj")


# ── refinementSurfaces / refinementRegions cross-referencing ─────────────────

def test_refinement_surfaces_exact_name_match():
    root = _parse("""
        geometry
        {
            motorBike { type box; min (0 0 0); max (1 1 1); }
        }
        castellatedMeshControls
        {
            refinementSurfaces { motorBike { level (5 6); } }
        }
    """)
    data = extract_snappy_hex_mesh_data(root)
    shape = _shape_by_name(data, "motorBike")
    assert shape.category == "surface"
    assert shape.level == (5.0, 6.0)


def test_refinement_surfaces_regex_key_match():
    root = _parse("""
        geometry
        {
            igloo { type sphere; centre (3 3 0); radius 3.5; }
        }
        castellatedMeshControls
        {
            refinementSurfaces { "iglo.*" { level (1 1); } }
        }
    """)
    data = extract_snappy_hex_mesh_data(root)
    shape = _shape_by_name(data, "igloo")
    assert shape.category == "surface"
    assert shape.level == (1.0, 1.0)


def test_refinement_regions_mode():
    root = _parse("""
        geometry
        {
            sphere1 { type sphere; centre (0 0 0); radius 1; }
        }
        castellatedMeshControls
        {
            refinementRegions { sphere1 { mode inside; levels ((1e15 4)); } }
        }
    """)
    data = extract_snappy_hex_mesh_data(root)
    shape = _shape_by_name(data, "sphere1")
    assert shape.category == "region"
    assert shape.mode == "inside"


def test_surface_and_region_keeps_surface_category():
    root = _parse("""
        geometry
        {
            dirRefineBox1 { type box; min (-10 -10 -10); max (10 10 0.5); }
        }
        castellatedMeshControls
        {
            refinementSurfaces { dirRefineBox1 { level (1 1); } }
            refinementRegions { dirRefineBox1 { mode inside; levels ((10000 0)); } }
        }
    """)
    data = extract_snappy_hex_mesh_data(root)
    shape = _shape_by_name(data, "dirRefineBox1")
    assert shape.category == "surface"
    assert shape.level == (1.0, 1.0)
    assert shape.mode == "inside"


# ── locationInMesh / locationsInMesh ──────────────────────────────────────────

def test_location_in_mesh_singular():
    root = _parse("""
        castellatedMeshControls
        {
            locationInMesh (3.12 0.2833 0.4322);
        }
    """)
    data = extract_snappy_hex_mesh_data(root)
    assert data.location_points == [([3.12, 0.2833, 0.4322], "locationInMesh")]


def test_locations_in_mesh_plural():
    root = _parse("""
        castellatedMeshControls
        {
            locationsInMesh
            (
                (( 0.005 0.005  0.005) heater)
                (( 0.05  0.005  0.005) rightSolid)
                ((-0.05  0.015  0.005) topAir)
            );
        }
    """)
    data = extract_snappy_hex_mesh_data(root)
    assert data.location_points == [
        ([0.005, 0.005, 0.005], "heater"),
        ([0.05, 0.005, 0.005], "rightSolid"),
        ([-0.05, 0.015, 0.005], "topAir"),
    ]


# ── $var / #eval{} resolution ─────────────────────────────────────────────────

def test_box_with_variables_resolved():
    root = _parse("""
        xMin -1;
        xMax 1;
        geometry
        {
            box1 { type box; min ($xMin $xMin $xMin); max ($xMax $xMax $xMax); }
        }
    """)
    data = extract_snappy_hex_mesh_data(root)
    shape = _shape_by_name(data, "box1")
    assert shape.geometry["box"] == [[-1.0, -1.0, -1.0], [1.0, 1.0, 1.0]]


# ── both forks' spellings of the same geometry types ──────────────────────────
#
# The two forks' tutorials do not overlap at all: OpenCFD's use the short form
# exclusively (37 `box`, 6 `sphere`, 4 `cylinder`), Foundation's the long one
# exclusively (12 `searchableBox`, 3 `searchableSphere`, 1 `searchableCylinder`).
# The long form is canonical in *both* -- each fork's searchableBox.H declares
# `TypeName("searchableBox")` -- so a dict written either way is valid. Handling
# only the short form meant no Foundation case drew any geometry: every entry was
# filed as non-geometric, which reads as an empty dictionary rather than a bug.

class TestSearchableTypeSpellings:
    @pytest.mark.parametrize(("long_name", "short_name", "body"), [
        ("searchableBox", "box", "min (0 0 0); max (1 2 3);"),
        ("searchableSphere", "sphere", "centre (1 2 3); radius 0.5;"),
        ("searchableCylinder", "cylinder", "point1 (0 0 0); point2 (0 0 1); radius 0.5;"),
    ])
    def test_long_and_short_spellings_resolve_the_same_geometry(self, long_name, short_name, body):
        long_data = extract_snappy_hex_mesh_data(
            _parse(f"geometry {{ g {{ type {long_name}; {body} }} }}")
        )
        short_data = extract_snappy_hex_mesh_data(
            _parse(f"geometry {{ g {{ type {short_name}; {body} }} }}")
        )
        assert len(long_data.shapes) == 1, f"{long_name} produced no shape"
        assert long_data.shapes[0].geometry == short_data.shapes[0].geometry

    def test_the_kind_shown_is_the_spelling_the_dict_used(self):
        # kind reaches the user verbatim in the overlay menu row, so a dict saying
        # searchableBox must not read "box" there.
        data = extract_snappy_hex_mesh_data(
            _parse("geometry { g { type searchableBox; min (0 0 0); max (1 1 1); } }")
        )
        assert data.shapes[0].kind == "searchableBox"

    def test_a_searchable_type_is_not_filed_as_non_geometric(self):
        data = extract_snappy_hex_mesh_data(
            _parse("geometry { g { type searchableSphere; centre (0 0 0); radius 1; } }")
        )
        assert [s.label for s in data.non_geometric] == []


class TestKeepPointSpellings:
    def test_inside_point_is_read_as_a_keep_point(self):
        # Foundation's spelling of locationInMesh, and the only one its tutorials use.
        data = extract_snappy_hex_mesh_data(
            _parse("castellatedMeshControls { insidePoint (1 2 3); }")
        )
        assert data.location_points == [([1.0, 2.0, 3.0], "insidePoint")]

    def test_location_in_mesh_still_works(self):
        data = extract_snappy_hex_mesh_data(
            _parse("castellatedMeshControls { locationInMesh (1 2 3); }")
        )
        assert data.location_points == [([1.0, 2.0, 3.0], "locationInMesh")]

    def test_a_per_surface_inside_point_is_not_a_keep_point(self):
        # OpenCFD spells a refinementSurfaces entry's cellZone selector `insidePoint`
        # too, and that is a different thing. Reading the keep-point at the
        # castellatedMeshControls level only is what keeps the two apart.
        data = extract_snappy_hex_mesh_data(_parse("""
            geometry { g { type box; min (0 0 0); max (1 1 1); } }
            castellatedMeshControls
            {
                refinementSurfaces
                {
                    g { level (1 1); cellZoneInside insidePoint; insidePoint (9 9 9); }
                }
            }
        """))
        assert data.location_points == []


# ── closedTriSurfaceMesh ──────────────────────────────────────────────────────
#
# `class closedTriSurfaceMesh : public triSurfaceMesh` in both forks, so it reads exactly
# the same entries and differs only in promising the surface is closed. Naming only the
# other two types meant every one of its uses -- 4 across the two tutorial trees, in both
# the `file "x.obj"` and the entry-name-is-the-filename spellings -- was filed as having
# no geometry and never drawn.

class TestClosedTriSurfaceMesh:
    @pytest.fixture
    def case_dir(self, tmp_path):
        tri_dir = tmp_path / "constant" / "triSurface"
        tri_dir.mkdir(parents=True)
        (tri_dir / "pipe.obj").write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")
        return tmp_path

    def test_the_explicit_file_form_resolves(self, case_dir):
        # Foundation's spelling: `file "pipe.obj";`
        root = _parse('geometry { pipe { type closedTriSurfaceMesh; file "pipe.obj"; } }')
        data = extract_snappy_hex_mesh_data(root, case_dir=str(case_dir))
        shape = _shape_by_name(data, "pipe")
        assert shape.geometry["stl_path"] == str(case_dir / "constant" / "triSurface" / "pipe.obj")
        assert data.non_geometric == []

    def test_the_entry_name_form_resolves(self, case_dir):
        # OpenCFD's spelling: the entry key is the filename, `name` renames the shape.
        root = _parse("geometry { pipe.obj { type closedTriSurfaceMesh; name pipe; } }")
        data = extract_snappy_hex_mesh_data(root, case_dir=str(case_dir))
        shape = _shape_by_name(data, "pipe")
        assert shape.geometry["stl_path"] == str(case_dir / "constant" / "triSurface" / "pipe.obj")

    def test_the_kind_shown_is_the_type_the_dict_used(self, case_dir):
        root = _parse('geometry { pipe { type closedTriSurfaceMesh; file "pipe.obj"; } }')
        data = extract_snappy_hex_mesh_data(root, case_dir=str(case_dir))
        assert _shape_by_name(data, "pipe").kind == "closedTriSurfaceMesh"

    def test_a_missing_file_is_still_non_geometric(self, case_dir):
        # Same failure mode as triSurfaceMesh: recognised, but nothing to draw.
        root = _parse('geometry { gone { type closedTriSurfaceMesh; file "gone.obj"; } }')
        data = extract_snappy_hex_mesh_data(root, case_dir=str(case_dir))
        assert data.shapes == []
        assert [s.label for s in data.non_geometric] == ["gone"]

    def test_it_is_classified_like_any_other_surface(self, case_dir):
        root = _parse("""
            geometry { pipe { type closedTriSurfaceMesh; file "pipe.obj"; } }
            castellatedMeshControls { refinementSurfaces { pipe { level (2 3); } } }
        """)
        data = extract_snappy_hex_mesh_data(root, case_dir=str(case_dir))
        shape = _shape_by_name(data, "pipe")
        assert shape.category == "surface"
        assert shape.level == (2.0, 3.0)


class TestInsidePointsPlural:
    """Foundation's list form of the keep-point.

    Rare: it appears zero times in Foundation's own tutorials and once in OpenCFD's, and
    that one is the *other* `insidePoints` -- a per-surface cellZone selector inside a
    refinementSurfaces entry, which must not be drawn as a keep-point. Handled because
    Foundation's reader does accept it at this level, so a hand-written multi-region case
    can legitimately use it; scoped to castellatedMeshControls so the per-surface one
    cannot be picked up by mistake.
    """

    def test_a_list_of_points_becomes_several_keep_points(self):
        data = extract_snappy_hex_mesh_data(_parse("""
            castellatedMeshControls { insidePoints ( (1 2 3) (4 5 6) ); }
        """))
        assert data.location_points == [
            ([1.0, 2.0, 3.0], "insidePoints"),
            ([4.0, 5.0, 6.0], "insidePoints"),
        ]

    def test_it_wins_over_the_singular_forms(self):
        # Foundation's reader takes the first of insidePoints / insidePoint /
        # locationInMesh that is present; reading all three would invent keep-points the
        # mesher never uses.
        data = extract_snappy_hex_mesh_data(_parse("""
            castellatedMeshControls
            {
                insidePoints ( (1 1 1) );
                insidePoint (9 9 9);
                locationInMesh (7 7 7);
            }
        """))
        assert data.location_points == [([1.0, 1.0, 1.0], "insidePoints")]

    def test_an_empty_list_falls_through_to_the_singular(self):
        data = extract_snappy_hex_mesh_data(_parse("""
            castellatedMeshControls { insidePoints ( ); insidePoint (9 9 9); }
        """))
        assert data.location_points == [([9.0, 9.0, 9.0], "insidePoint")]

    def test_a_per_surface_insidePoints_is_not_a_keep_point(self):
        # OpenCFD's tutorials/mesh/snappyHexMesh/insidePoints, reduced: the plural sits
        # inside a refinementSurfaces entry beside `cellZoneInside insidePoint;` and means
        # something else entirely.
        data = extract_snappy_hex_mesh_data(_parse("""
            geometry { box { type box; min (0 0 0); max (1 1 1); } }
            castellatedMeshControls
            {
                refinementSurfaces
                {
                    box
                    {
                        level (1 1);
                        cellZone boxCz;
                        cellZoneInside insidePoint;
                        insidePoints ( (2.01 0.75 1.13) (2.01 1.25 1.1) );
                    }
                }
            }
        """))
        assert data.location_points == []

    def test_variables_in_the_list_resolve(self):
        data = extract_snappy_hex_mesh_data(_parse("""
            x 5;
            castellatedMeshControls { insidePoints ( ($x 0 0) ); }
        """))
        assert data.location_points == [([5.0, 0.0, 0.0], "insidePoints")]
