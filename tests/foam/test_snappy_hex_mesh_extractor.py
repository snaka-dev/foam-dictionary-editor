# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for snappy_hex_mesh_extractor: geometry extraction, refinementSurfaces/
Regions cross-referencing, locationInMesh(s), and $var / #eval resolution."""
from __future__ import annotations

from pathlib import Path

from foam.parser import OpenFoamParser
from foam.snappy_hex_mesh_extractor import extract_snappy_hex_mesh_data

HEADER = """\
FoamFile { version 2.0; format ascii; class dictionary; object snappyHexMeshDict; }
"""


def _parse(text: str):
    return OpenFoamParser(HEADER + text).parse()


def _shape_by_name(data, name):
    return next(s for s in data.shapes if s.name == name)


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
    assert shape.geo_type == "box"
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
    assert [s.name for s in data.non_geometric] == ["twoFridgeFreezers"]


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
    assert seal.geo_type == "collection_box"
    for shape, origin in ((seal, [2.0, 2.0, 0.0]), (herring, [3.5, 3.0, 0.0])):
        assert shape.geometry["origin"] == origin
        assert shape.geometry["i"] == [1.0, 0.0, 0.0]
        assert shape.geometry["j"] == [0.0, 1.0, 0.0]
        assert shape.geometry["k"] == [0.0, 0.0, 2.1]
    assert not any(s.name == "twoFridgeFreezers" for s in data.non_geometric)


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
    assert not any(s.name.startswith("coll.") for s in data.shapes)
    assert [s.name for s in data.non_geometric if s.name == "coll"] == ["coll"]


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
    assert not any(s.name.startswith("coll.") for s in data.shapes)
    assert [s.name for s in data.non_geometric if s.name == "coll"] == ["coll"]


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
    assert shape.geo_type == "triSurfaceMesh"
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
    assert [s.name for s in data.non_geometric] == ["geom"]


def test_triSurfaceMesh_no_case_dir_is_non_geometric():
    root = _parse("""
        geometry
        {
            geom.stl { type triSurfaceMesh; name geom; }
        }
    """)
    data = extract_snappy_hex_mesh_data(root)
    assert data.shapes == []
    assert [s.name for s in data.non_geometric] == ["geom"]


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
