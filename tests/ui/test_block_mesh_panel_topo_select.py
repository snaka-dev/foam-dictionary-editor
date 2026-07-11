# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for per-shape topoSet visibility toggles in BlockMeshPanel."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

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


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])
    return app


def _panel_with_demo(qapp) -> BlockMeshPanel:
    panel = BlockMeshPanel()
    root = OpenFoamParser(_TOPO_SET_DICT.read_text()).parse()
    panel.update_topo_set(str(_TOPO_SET_DICT), root)
    return panel


def test_menu_populated_per_shape(qapp):
    panel = _panel_with_demo(qapp)
    assert len(panel._topo_shape_actions) == 9
    assert len(panel._visible_topo_shapes()) == 9
    # Menu entries are labelled "<name>  ·  <source>".
    texts = [a.text() for a in panel._topo_shape_actions]
    assert any(t.startswith("spike") and "coneToCell" in t for t in texts)


def test_unchecking_one_hides_only_that_shape(qapp):
    panel = _panel_with_demo(qapp)
    # Hide the "spike" cone.
    spike_idx = next(
        i for i, s in enumerate(panel._topo_shapes) if s.label == "spike"
    )
    panel._topo_shape_actions[spike_idx].setChecked(False)

    visible = panel._visible_topo_shapes()
    assert len(visible) == 8
    assert all(s.label != "spike" for s in visible)


def test_master_toggle_hides_all(qapp):
    panel = _panel_with_demo(qapp)
    panel._show_topo.setChecked(False)
    assert panel._visible_topo_shapes() == []
    # Per-shape actions are disabled while the master is off.
    assert all(not a.isEnabled() for a in panel._topo_shape_actions)
    panel._show_topo.setChecked(True)
    assert len(panel._visible_topo_shapes()) == 9
    assert all(a.isEnabled() for a in panel._topo_shape_actions)


def test_action_colour_legend_present(qapp):
    panel = _panel_with_demo(qapp)
    labels = [a.text() for a in panel._topo_legend_actions]
    assert labels == ["new", "add", "subtract", "subset", "invert"]
    # Legend rows are informational (disabled) and each carries a colour swatch.
    assert all(not a.isEnabled() for a in panel._topo_legend_actions)
    assert all(not a.icon().isNull() for a in panel._topo_legend_actions)


def test_per_shape_rows_have_colour_swatches(qapp):
    panel = _panel_with_demo(qapp)
    assert panel._topo_shape_actions
    assert all(not a.icon().isNull() for a in panel._topo_shape_actions)


def test_non_geometric_source_listed_disabled(qapp):
    panel = _panel_with_demo(qapp)
    # The demo's cellToFace action carries no geometry: shown greyed-out.
    assert len(panel._topo_info_actions) == 1
    act = panel._topo_info_actions[0]
    assert "cellToFace" in act.text()
    assert "(no geometry)" in act.text()
    assert not act.isEnabled()
    # It is not one of the renderable shapes.
    assert all(s.source != "cellToFace" for s in panel._topo_shapes)


def test_reload_empty_clears_actions(qapp):
    panel = _panel_with_demo(qapp)
    assert panel._topo_shape_actions  # populated
    assert panel._topo_info_actions   # populated
    empty_root = OpenFoamParser(_HEADER_ONLY).parse()
    panel.update_topo_set("empty", empty_root)
    assert panel._topo_shape_actions == []
    assert panel._topo_info_actions == []
    assert panel._visible_topo_shapes() == []
