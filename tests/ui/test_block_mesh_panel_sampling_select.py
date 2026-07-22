# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for per-shape sampling visibility toggles in BlockMeshPanel."""
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

_CONTROL_DICT = """\
FoamFile { version 2.0; format ascii; class dictionary; object controlDict; }
application icoFoam;
functions
{
    myProbes
    {
        type probes;
        fields (p U);
        probeLocations ( (0.1 0.2 0.3) );
    }
    surf
    {
        type surfaces;
        surfaces
        {
            cutter { type cuttingPlane; point (0 0 0.5); normal (0 1 0); }
            wallSurf { type patch; patches (walls); }
        }
    }
}
"""

_SAMPLE_FILE = """\
FoamFile { version 2.0; format ascii; class dictionary; object sample; }
type sets;
fields (U);
sets
{
    centerline { type lineCell; axis x; start (0 0 0); end (1 0 0); }
}
"""

_EMPTY_CONTROL_DICT = (
    "FoamFile { version 2.0; format ascii; class dictionary; object controlDict; }\n"
    "application icoFoam;\n"
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])
    return app


def _panel_with_control_dict(qapp) -> BlockMeshPanel:
    panel = BlockMeshPanel()
    root = OpenFoamParser(_CONTROL_DICT).parse()
    panel.update_sampling("/case/system/controlDict", root)
    return panel


def test_menu_populated_from_control_dict_functions(qapp):
    panel = _panel_with_control_dict(qapp)
    assert len(panel._sampling.shape_actions) == 2
    texts = [a.text() for a in panel._sampling.shape_actions]
    assert any("myProbes" in t and "probes" in t for t in texts)
    assert any("surf.cutter" in t and "cuttingPlane" in t for t in texts)
    # Rows carry the source basename so multi-file unions stay attributable.
    assert all("[controlDict]" in t for t in texts)


def test_unchecking_one_hides_only_that_shape(qapp):
    panel = _panel_with_control_dict(qapp)
    probes_idx = next(
        i for i, s in enumerate(panel._sampling.shapes) if s.kind == "probes"
    )
    panel._sampling.shape_actions[probes_idx].setChecked(False)
    visible = panel._sampling.visible_shapes()
    assert [s.kind for s in visible] == ["cuttingPlane"]


def test_master_toggle_hides_all(qapp):
    panel = _panel_with_control_dict(qapp)
    panel._sampling.master.setChecked(False)
    assert panel._sampling.visible_shapes() == []
    panel._sampling.master.setChecked(True)
    assert len(panel._sampling.visible_shapes()) == 2


def test_non_geometric_patch_surface_listed_disabled(qapp):
    panel = _panel_with_control_dict(qapp)
    assert len(panel._sampling.info_actions) == 1
    act = panel._sampling.info_actions[0]
    assert "surf.wallSurf" in act.text()
    assert "(no geometry)" in act.text()
    assert not act.isEnabled()


def test_multiple_files_merge_into_one_menu(qapp):
    panel = _panel_with_control_dict(qapp)
    sample_root = OpenFoamParser(_SAMPLE_FILE).parse()
    panel.update_sampling("/case/system/sample", sample_root)
    labels = [s.label for s in panel._sampling.shapes]
    assert "myProbes" in labels
    assert "centerline" in labels
    files = {s.source_file for s in panel._sampling.shapes}
    assert files == {"controlDict", "sample"}


def test_reloading_one_file_replaces_only_its_shapes(qapp):
    panel = _panel_with_control_dict(qapp)
    sample_root = OpenFoamParser(_SAMPLE_FILE).parse()
    panel.update_sampling("/case/system/sample", sample_root)
    assert len(panel._sampling.shapes) == 3
    # controlDict loses its functions block: its shapes go, sample's stay.
    empty_root = OpenFoamParser(_EMPTY_CONTROL_DICT).parse()
    panel.update_sampling("/case/system/controlDict", empty_root)
    assert [s.label for s in panel._sampling.shapes] == ["centerline"]


def test_hidden_shape_stays_hidden_when_another_file_is_edited(qapp):
    """Hiding a shape from system/sample must survive a later edit to
    controlDict, which rebuilds the shared union menu."""
    panel = _panel_with_control_dict(qapp)
    sample_root = OpenFoamParser(_SAMPLE_FILE).parse()
    panel.update_sampling("/case/system/sample", sample_root)

    # Hide the sample-file line.
    idx = next(
        i for i, s in enumerate(panel._sampling.shapes) if s.label == "centerline"
    )
    panel._sampling.shape_actions[idx].setChecked(False)
    assert all(s.label != "centerline" for s in panel._sampling.visible_shapes())

    # Edit controlDict (its functions block gains nothing new here).
    panel.update_sampling("/case/system/controlDict",
                          OpenFoamParser(_CONTROL_DICT).parse())

    # centerline is still present but still hidden.
    assert any(s.label == "centerline" for s in panel._sampling.shapes)
    assert all(s.label != "centerline" for s in panel._sampling.visible_shapes())


def test_clear_resets_everything(qapp):
    panel = _panel_with_control_dict(qapp)
    assert panel._sampling.shape_actions
    panel.clear()
    assert panel._sampling.shape_actions == []
    assert panel._sampling.visible_shapes() == []
    assert panel._sampling_by_file == {}
