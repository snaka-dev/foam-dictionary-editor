# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for per-shape setFields visibility toggles in BlockMeshPanel."""
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

_SET_FIELDS_DICT = (
    Path(__file__).resolve().parents[2]
    / "tutorials" / "damBreak" / "system" / "setFieldsDict"
)

_HEADER_ONLY = (
    "FoamFile { version 2.0; format ascii; class dictionary; object setFieldsDict; }\n"
)

_MULTI_REGION = _HEADER_ONLY + """
regions
(
    boxToCell
    {
        box (0 0 -1) (0.1461 0.292 1);
        fieldValues ( volScalarFieldValue alpha.water 1 );
    }
    sphereToCell
    {
        centre (0.3 0.3 0);
        radius 0.05;
        fieldValues ( volScalarFieldValue alpha.water 1 );
    }
    zoneToCell
    {
        zone  hotZone;
        fieldValues ( volScalarFieldValue alpha.water 1 );
    }
);
"""


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])
    return app


def _panel_with(qapp, text: str) -> BlockMeshPanel:
    panel = BlockMeshPanel()
    root = OpenFoamParser(text).parse()
    panel.update_set_fields("setFieldsDict", root)
    return panel


def test_menu_populated_from_dam_break_tutorial(qapp):
    panel = _panel_with(qapp, _SET_FIELDS_DICT.read_text())
    assert len(panel._set_fields.shape_actions) == 1
    assert len(panel._set_fields.visible_shapes()) == 1
    # Rows are labelled "<fieldValues summary>  ·  <source>".
    text = panel._set_fields.shape_actions[0].text()
    assert "alpha.water=1" in text
    assert "boxToCell" in text


def test_unchecking_one_hides_only_that_shape(qapp):
    panel = _panel_with(qapp, _MULTI_REGION)
    assert len(panel._set_fields.shape_actions) == 2
    sphere_idx = next(
        i for i, s in enumerate(panel._set_fields.shapes)
        if s.source == "sphereToCell"
    )
    panel._set_fields.shape_actions[sphere_idx].setChecked(False)
    visible = panel._set_fields.visible_shapes()
    assert len(visible) == 1
    assert visible[0].source == "boxToCell"


def test_master_toggle_hides_all(qapp):
    panel = _panel_with(qapp, _MULTI_REGION)
    panel._set_fields.master.setChecked(False)
    assert panel._set_fields.visible_shapes() == []
    assert all(not a.isEnabled() for a in panel._set_fields.shape_actions)
    panel._set_fields.master.setChecked(True)
    assert len(panel._set_fields.visible_shapes()) == 2


def test_non_geometric_source_listed_disabled(qapp):
    panel = _panel_with(qapp, _MULTI_REGION)
    assert len(panel._set_fields.info_actions) == 1
    act = panel._set_fields.info_actions[0]
    assert "zoneToCell" in act.text()
    assert "(no geometry)" in act.text()
    assert not act.isEnabled()
    assert panel._set_fields.info_menu is not None


def test_shapes_included_in_stl_export(qapp):
    panel = _panel_with(qapp, _MULTI_REGION)
    exportable = panel._exportable_set_fields_shapes()
    assert [s.source for s in exportable] == ["boxToCell", "sphereToCell"]
    assert panel._export_stl_act.isEnabled()


def test_reload_empty_clears_actions(qapp):
    panel = _panel_with(qapp, _MULTI_REGION)
    assert panel._set_fields.shape_actions
    empty_root = OpenFoamParser(_HEADER_ONLY).parse()
    panel.update_set_fields("empty", empty_root)
    assert panel._set_fields.shape_actions == []
    assert panel._set_fields.info_actions == []
    assert panel._set_fields.visible_shapes() == []
    assert not panel._export_stl_act.isEnabled()
