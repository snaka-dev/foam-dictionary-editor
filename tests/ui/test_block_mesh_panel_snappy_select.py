# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for per-shape snappyHexMesh visibility toggles in BlockMeshPanel."""
from __future__ import annotations

import sys

import pytest
from PySide6.QtWidgets import QApplication

from foam.parser import OpenFoamParser
from ui.panels import block_mesh_panel
from ui.panels.block_mesh_panel import BlockMeshPanel

pytestmark = pytest.mark.skipif(
    not block_mesh_panel._PYVISTA_OK, reason="pyvista/pyvistaqt not installed"
)

_HEADER = "FoamFile { version 2.0; format ascii; class dictionary; object snappyHexMeshDict; }\n"

# Four renderable shapes (box/sphere/cylinder/cone), one non-geometric
# triSurfaceMesh reference (no case_dir passed, so the file can't be
# resolved), and two locationsInMesh keep-points.
_SNAPPY_DEMO_DICT = _HEADER + """
geometry
{
    motorBike { type box; min (0 0 0); max (1 1 1); }
    igloo { type sphere; centre (3 3 0); radius 3.5; }
    pipe { type cylinder; point1 (0 0 -1); point2 (0 0 1); radius 0.1; }
    spike { type cone; point1 (0 0 0); point2 (0 0 2); radius1 1; radius2 0; }
    geom.stl { type triSurfaceMesh; name geom; }
}

castellatedMeshControls
{
    refinementSurfaces
    {
        igloo { level (1 1); }
    }
    refinementRegions
    {
        pipe { mode inside; levels ((1e15 4)); }
    }
    locationsInMesh
    (
        (( 0.005 0.005  0.005) heater)
        (( 0.05  0.005  0.005) rightSolid)
    );
}
"""

_HEADER_ONLY = (
    "FoamFile { version 2.0; format ascii; class dictionary; object snappyHexMeshDict; }\n"
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])
    return app


def _panel_with_demo(qapp) -> BlockMeshPanel:
    panel = BlockMeshPanel()
    root = OpenFoamParser(_SNAPPY_DEMO_DICT).parse()
    panel.update_snappy_hex_mesh("/fake/system/snappyHexMeshDict", root)
    return panel


def test_menu_populated_per_shape(qapp):
    panel = _panel_with_demo(qapp)
    assert len(panel._snappy.shape_actions) == 4
    assert len(panel._snappy.visible_shapes()) == 4
    # Menu entries are labelled "<name>  ·  <geo_type>  <level/mode>".
    texts = [a.text() for a in panel._snappy.shape_actions]
    assert any(t.startswith("igloo") and "sphere" in t for t in texts)
    assert any(t.startswith("pipe") and "inside" in t for t in texts)


def test_unchecking_one_hides_only_that_shape(qapp):
    panel = _panel_with_demo(qapp)
    # Hide the "pipe" cylinder.
    pipe_idx = next(
        i for i, s in enumerate(panel._snappy.shapes) if s.name == "pipe"
    )
    panel._snappy.shape_actions[pipe_idx].setChecked(False)

    visible = panel._snappy.visible_shapes()
    assert len(visible) == 3
    assert all(s.name != "pipe" for s in visible)


def test_master_toggle_hides_all(qapp):
    panel = _panel_with_demo(qapp)
    panel._snappy.master.setChecked(False)
    assert panel._snappy.visible_shapes() == []
    assert panel._snappy.visible_locations() == []
    # Per-shape actions are disabled while the master is off.
    assert all(not a.isEnabled() for a in panel._snappy.shape_actions)
    panel._snappy.master.setChecked(True)
    assert len(panel._snappy.visible_shapes()) == 4
    assert len(panel._snappy.visible_locations()) == 2
    assert all(a.isEnabled() for a in panel._snappy.shape_actions)


def test_action_colour_legend_present(qapp):
    panel = _panel_with_demo(qapp)
    labels = [a.text() for a in panel._snappy.legend_actions]
    assert labels == ["surface", "region", "geometry"]
    # Legend rows are informational (disabled) and each carries a colour swatch.
    assert all(not a.isEnabled() for a in panel._snappy.legend_actions)
    assert all(not a.icon().isNull() for a in panel._snappy.legend_actions)


def test_per_shape_rows_have_colour_swatches(qapp):
    panel = _panel_with_demo(qapp)
    assert panel._snappy.shape_actions
    assert all(not a.icon().isNull() for a in panel._snappy.shape_actions)


def test_non_geometric_source_listed_disabled(qapp):
    panel = _panel_with_demo(qapp)
    # The demo's geom.stl reference resolves no file: shown greyed-out.
    assert len(panel._snappy.info_actions) == 1
    act = panel._snappy.info_actions[0]
    assert "geom" in act.text()
    assert "(no geometry)" in act.text()
    assert not act.isEnabled()
    # It is not one of the renderable shapes.
    assert all(s.name != "geom" for s in panel._snappy.shapes)


def test_location_actions_populated_and_toggle(qapp):
    panel = _panel_with_demo(qapp)
    assert len(panel._snappy.location_actions) == 2
    texts = [a.text() for a in panel._snappy.location_actions]
    assert texts == ["📍 heater", "📍 rightSolid"]

    panel._snappy.location_actions[0].setChecked(False)
    visible = panel._snappy.visible_locations()
    assert len(visible) == 1
    assert visible[0][1] == "rightSolid"


def test_reload_empty_clears_actions(qapp):
    panel = _panel_with_demo(qapp)
    assert panel._snappy.shape_actions     # populated
    assert panel._snappy.info_actions      # populated
    assert panel._snappy.location_actions  # populated
    empty_root = OpenFoamParser(_HEADER_ONLY).parse()
    panel.update_snappy_hex_mesh("empty", empty_root)
    assert panel._snappy.shape_actions == []
    assert panel._snappy.info_actions == []
    assert panel._snappy.location_actions == []
    assert panel._snappy.visible_shapes() == []
    assert panel._snappy.visible_locations() == []
