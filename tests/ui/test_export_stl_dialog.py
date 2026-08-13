# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for ExportStlDialog (Export Shapes as STL)."""
from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

from foam.parser import OpenFoamParser
from foam.set_fields_extractor import extract_set_fields_data
from foam.snappy_hex_mesh_extractor import extract_snappy_hex_mesh_data
from foam.topo_set_extractor import extract_topo_set_data
from ui.panels import block_mesh_panel

pytestmark = pytest.mark.skipif(
    not block_mesh_panel._PYVISTA_OK, reason="pyvista/pyvistaqt not installed"
)


@pytest.fixture(autouse=True)
def _no_blocking_message_box(monkeypatch):
    """_export() ends with a summary QMessageBox.information(); it must not
    block waiting for a click in a headless test run."""
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))

from ui.dialogs.export_stl_dialog import ExportStlDialog, _safe_filename  # noqa: E402
from ui.widgets._checkable_list import checked_indices  # noqa: E402

_TOPO_SET_DICT = (
    Path(__file__).resolve().parents[2]
    / "tutorials" / "topoSetShapes" / "system" / "topoSetDict"
)

_SNAPPY_HEADER = "FoamFile { version 2.0; format ascii; class dictionary; object snappyHexMeshDict; }\n"

_SNAPPY_DEMO_DICT = _SNAPPY_HEADER + """
geometry
{
    motorBike { type box; min (0 0 0); max (1 1 1); }
    igloo { type sphere; centre (3 3 0); radius 3.5; }
    pipe { type cylinder; point1 (0 0 -1); point2 (0 0 1); radius 0.1; }
    spike { type cone; point1 (0 0 0); point2 (0 0 2); radius1 1; radius2 0; }
}
"""

_SNAPPY_DEGENERATE_DICT = _SNAPPY_HEADER + """
geometry
{
    flat { type cylinder; point1 (0 0 0); point2 (0 0 0); radius 1; }
}
"""

_SET_FIELDS_DICT = """FoamFile { version 2.0; format ascii; class dictionary; object setFieldsDict; }
regions
(
    boxToCell
    {
        box (0 0 -1) (0.1461 0.292 1);
        fieldValues ( volScalarFieldValue alpha.water 1 );
    }
);
"""


def _topo_shapes():
    root = OpenFoamParser(_TOPO_SET_DICT.read_text()).parse()
    shapes = extract_topo_set_data(root).shapes
    # Mirror BlockMeshPanel._exportable_topo_shapes(): point markers and
    # planeToFaceZone discs are never offered for export.
    return [s for s in shapes if not ({"points", "planePoint"} & s.geometry.keys())]


def _snappy_shapes(text=_SNAPPY_DEMO_DICT):
    root = OpenFoamParser(text).parse()
    return extract_snappy_hex_mesh_data(root, case_dir=None).shapes


def _set_fields_shapes():
    root = OpenFoamParser(_SET_FIELDS_DICT).parse()
    return extract_set_fields_data(root).shapes


def test_row_count_matches_geometric_shapes(qapp):
    topo = _topo_shapes()
    snappy = _snappy_shapes()
    dlg = ExportStlDialog(topo, set(), snappy, set(), None)
    assert dlg._list.count() == len(topo) + len(snappy)


def test_set_fields_shapes_form_third_group(qapp):
    set_fields = _set_fields_shapes()
    assert set_fields  # the demo dict has one boxToCell region
    dlg = ExportStlDialog(
        [], set(), [], set(), None,
        set_fields_shapes=set_fields,
        set_fields_visible={id(set_fields[0])},
    )
    assert dlg._list.count() == 1
    item = dlg._list.item(0)
    assert item.text().startswith("[setFields]")
    assert "boxToCell" in item.text()
    assert item.checkState() == Qt.Checked


def test_default_checked_state_matches_visible_sets(qapp):
    topo = _topo_shapes()
    snappy = _snappy_shapes()
    visible_topo = {id(topo[0])}
    visible_snappy = {id(snappy[1])}
    dlg = ExportStlDialog(topo, visible_topo, snappy, visible_snappy, None)

    checked = [dlg._list.item(i).checkState() == Qt.Checked for i in range(dlg._list.count())]
    # Only entry 0 (first topo shape) and entry len(topo)+1 (second snappy shape) start checked.
    expected = [False] * (len(topo) + len(snappy))
    expected[0] = True
    expected[len(topo) + 1] = True
    assert checked == expected


def test_select_all_and_deselect_all(qapp):
    topo = _topo_shapes()
    snappy = _snappy_shapes()
    dlg = ExportStlDialog(topo, set(), snappy, set(), None)

    dlg._select_all()
    assert checked_indices(dlg._list) == list(range(dlg._list.count()))

    dlg._deselect_all()
    assert checked_indices(dlg._list) == []


def test_export_writes_one_stl_per_checked_shape(qapp, tmp_path):
    import pyvista as pv

    topo = _topo_shapes()
    snappy = _snappy_shapes()
    dlg = ExportStlDialog(topo, set(), snappy, set(), None)
    dlg._select_all()
    dlg._folder_edit.setText(str(tmp_path))

    dlg._export()

    files = sorted(tmp_path.glob("*.stl"))
    assert len(files) == len(topo) + len(snappy)
    for f in files:
        mesh = pv.read(str(f))
        assert mesh.n_points > 0


def test_export_handles_name_collisions(qapp, tmp_path):
    # Duplicate a shape so two entries share the same label and would collide
    # on filename if not de-duplicated.
    topo = _topo_shapes()
    shapes = topo + [topo[0]]
    dlg = ExportStlDialog(shapes, set(), [], set(), None)
    dlg._select_all()
    dlg._folder_edit.setText(str(tmp_path))

    dlg._export()

    files = sorted(tmp_path.glob("*.stl"))
    assert len(files) == len(shapes)
    names = {f.name for f in files}
    assert len(names) == len(shapes)  # all unique despite the collision


def test_export_skips_degenerate_geometry_without_raising(qapp, tmp_path):
    snappy = _snappy_shapes(_SNAPPY_DEGENERATE_DICT)
    assert len(snappy) == 1
    dlg = ExportStlDialog([], set(), snappy, set(), None)
    dlg._select_all()
    dlg._folder_edit.setText(str(tmp_path))

    dlg._export()  # should not raise

    assert list(tmp_path.glob("*.stl")) == []


def test_safe_filename_sanitizes_and_falls_back():
    assert _safe_filename("inlet box") == "inlet_box"
    assert _safe_filename("") == "shape"
    assert _safe_filename("a/b\\c") == "a_b_c"
