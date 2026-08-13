# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for per-shape topoSet visibility toggles in BlockMeshPanel."""
from __future__ import annotations

from pathlib import Path

import pytest

from foam.parser import OpenFoamParser
from ui.panels import block_mesh_panel
from ui.panels.block_mesh_panel import BlockMeshPanel

pytestmark = pytest.mark.skipif(
    not block_mesh_panel._PYVISTA_OK, reason="pyvista/pyvistaqt not installed"
)

_TOPO_SET_DICT = (
    Path(__file__).resolve().parents[2]
    / "tutorials" / "topoSetShapes" / "system" / "topoSetDict"
)

_HEADER_ONLY = (
    "FoamFile { version 2.0; format ascii; class dictionary; object topoSetDict; }\n"
)


def _panel_with_demo(qapp) -> BlockMeshPanel:
    panel = BlockMeshPanel()
    root = OpenFoamParser(_TOPO_SET_DICT.read_text()).parse()
    panel.update_topo_set(str(_TOPO_SET_DICT), root)
    return panel


def test_menu_populated_per_shape(qapp):
    panel = _panel_with_demo(qapp)
    assert len(panel._topo.shape_actions) == 14
    assert len(panel._topo.visible_shapes()) == 14
    # Menu entries are labelled "<name>  ·  <source>".
    texts = [a.text() for a in panel._topo.shape_actions]
    assert any(t.startswith("spike") and "coneToCell" in t for t in texts)


def test_unchecking_one_hides_only_that_shape(qapp):
    panel = _panel_with_demo(qapp)
    # Hide the "spike" cone.
    spike_idx = next(
        i for i, s in enumerate(panel._topo.shapes) if s.label == "spike"
    )
    panel._topo.shape_actions[spike_idx].setChecked(False)

    visible = panel._topo.visible_shapes()
    assert len(visible) == 13
    assert all(s.label != "spike" for s in visible)


def test_master_toggle_hides_all(qapp):
    panel = _panel_with_demo(qapp)
    panel._topo.master.setChecked(False)
    assert panel._topo.visible_shapes() == []
    # Per-shape actions are disabled while the master is off.
    assert all(not a.isEnabled() for a in panel._topo.shape_actions)
    panel._topo.master.setChecked(True)
    assert len(panel._topo.visible_shapes()) == 14
    assert all(a.isEnabled() for a in panel._topo.shape_actions)


def test_action_colour_legend_present(qapp):
    panel = _panel_with_demo(qapp)
    labels = [a.text() for a in panel._topo.legend_actions]
    assert labels == ["new", "add", "subtract", "subset", "invert"]
    # Legend rows are informational (disabled) and each carries a colour swatch.
    assert all(not a.isEnabled() for a in panel._topo.legend_actions)
    assert all(not a.icon().isNull() for a in panel._topo.legend_actions)


def test_per_shape_rows_have_colour_swatches(qapp):
    panel = _panel_with_demo(qapp)
    assert panel._topo.shape_actions
    assert all(not a.icon().isNull() for a in panel._topo.shape_actions)


def test_non_geometric_source_listed_disabled(qapp):
    panel = _panel_with_demo(qapp)
    # The demo's cellToFace action carries no geometry: shown greyed-out
    # inside the "Non-geometric sources (N)" submenu.
    assert len(panel._topo.info_actions) == 1
    act = panel._topo.info_actions[0]
    assert "cellToFace" in act.text()
    assert "(no geometry)" in act.text()
    assert not act.isEnabled()
    assert panel._topo.info_menu is not None
    assert panel._topo.info_menu.title() == "Non-geometric sources (1)"
    assert act in panel._topo.info_menu.actions()
    # It is not one of the renderable shapes.
    assert all(s.kind != "cellToFace" for s in panel._topo.shapes)


def test_show_all_hide_all(qapp):
    panel = _panel_with_demo(qapp)
    n = len(panel._topo.shape_actions)
    panel._topo.hide_all.trigger()
    assert panel._topo.visible_shapes() == []
    assert all(not a.isChecked() for a in panel._topo.shape_actions)
    panel._topo.show_all.trigger()
    assert len(panel._topo.visible_shapes()) == n
    assert all(a.isChecked() for a in panel._topo.shape_actions)


def test_show_hide_all_disabled_with_master_off(qapp):
    panel = _panel_with_demo(qapp)
    panel._topo.master.setChecked(False)
    assert not panel._topo.show_all.isEnabled()
    assert not panel._topo.hide_all.isEnabled()
    panel._topo.master.setChecked(True)
    assert panel._topo.show_all.isEnabled()
    assert panel._topo.hide_all.isEnabled()


def test_point_and_plane_shapes_excluded_from_stl_export(qapp):
    panel = _panel_with_demo(qapp)
    exportable = panel._exportable_topo_shapes()
    assert exportable  # solids remain
    assert all("points" not in s.geometry for s in exportable)
    assert all("planePoint" not in s.geometry for s in exportable)
    # The demo dict does contain point and plane shapes to exclude.
    assert len(exportable) < len(panel._topo.shapes)


def test_reload_empty_clears_actions(qapp):
    panel = _panel_with_demo(qapp)
    assert panel._topo.shape_actions  # populated
    assert panel._topo.info_actions   # populated
    assert panel._topo.info_menu is not None
    empty_root = OpenFoamParser(_HEADER_ONLY).parse()
    panel.update_topo_set("empty", empty_root)
    assert panel._topo.shape_actions == []
    assert panel._topo.info_actions == []
    assert panel._topo.info_menu is None
    assert panel._topo.visible_shapes() == []
