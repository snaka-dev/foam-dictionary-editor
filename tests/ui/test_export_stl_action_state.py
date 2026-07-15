# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for the STL ▾ menu's 'Export Shapes as STL…' action enabled-state."""
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

_SNAPPY_DEMO_DICT = (
    "FoamFile { version 2.0; format ascii; class dictionary; object snappyHexMeshDict; }\n"
    "geometry { motorBike { type box; min (0 0 0); max (1 1 1); } }\n"
)

_HEADER_ONLY_TOPO = (
    "FoamFile { version 2.0; format ascii; class dictionary; object topoSetDict; }\n"
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])
    return app


def test_export_action_disabled_by_default(qapp):
    panel = BlockMeshPanel()
    assert not panel._export_stl_act.isEnabled()


def test_export_action_enabled_after_loading_topo_set(qapp):
    panel = BlockMeshPanel()
    root = OpenFoamParser(_TOPO_SET_DICT.read_text()).parse()
    panel.update_topo_set(str(_TOPO_SET_DICT), root)
    assert panel._export_stl_act.isEnabled()


def test_export_action_enabled_after_loading_snappy(qapp):
    panel = BlockMeshPanel()
    root = OpenFoamParser(_SNAPPY_DEMO_DICT).parse()
    panel.update_snappy_hex_mesh("snappyHexMeshDict", root)
    assert panel._export_stl_act.isEnabled()


def test_export_action_disabled_after_clear(qapp):
    panel = BlockMeshPanel()
    root = OpenFoamParser(_TOPO_SET_DICT.read_text()).parse()
    panel.update_topo_set(str(_TOPO_SET_DICT), root)
    assert panel._export_stl_act.isEnabled()

    panel.clear()
    assert not panel._export_stl_act.isEnabled()


def test_export_action_disabled_when_reloaded_empty(qapp):
    panel = BlockMeshPanel()
    root = OpenFoamParser(_TOPO_SET_DICT.read_text()).parse()
    panel.update_topo_set(str(_TOPO_SET_DICT), root)
    assert panel._export_stl_act.isEnabled()

    empty_root = OpenFoamParser(_HEADER_ONLY_TOPO).parse()
    panel.update_topo_set("empty", empty_root)
    assert not panel._export_stl_act.isEnabled()
