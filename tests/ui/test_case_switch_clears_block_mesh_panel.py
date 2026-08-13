# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Regression test for _load_case_dir() (ui/mixins/_file_ops.py).

It used to reset BlockMeshPanel state by poking `_topo_shapes`/`_snappy_shapes`
directly to `[]` instead of calling the panel's own `clear()`. That skipped
rebuilding the topoSet ▾/snappyHexMesh ▾ menus (stale per-shape checkboxes from
the previous case lingered), skipped resetting non_geometric/location-point
lists, skipped re-rendering the 3-D view (old overlays stayed drawn), and
skipped updating the STL ▾ "Export Shapes as STL…" action's enabled state.
Opening a new case must fully clear all of it.
"""
from __future__ import annotations

import pytest

from ui.panels import block_mesh_panel

pytestmark = pytest.mark.skipif(
    not block_mesh_panel._PYVISTA_OK, reason="pyvista/pyvistaqt not installed"
)


@pytest.fixture
def main_window_bm(qapp):
    """A real MainWindow instance with the BlockMesh 3-D panel enabled."""
    from app_config import get_app_config

    cfg = get_app_config()
    original = {name: cfg.get_feature(name) for name in ("terminal", "blockmesh")}
    cfg.set_feature("terminal", False)
    cfg.set_feature("blockmesh", True)

    from ui.main_window import MainWindow

    win = MainWindow()
    yield win

    win._file_list_refresh_timer.stop()
    if win._case_dir_watcher.directories():
        win._case_dir_watcher.removePaths(win._case_dir_watcher.directories())
    win._stop_foam_monitor()
    if win.terminal_panel is not None:
        win.terminal_panel.cleanup()
    if win.block_mesh_panel is not None:
        win.block_mesh_panel.shutdown()

    for name, value in original.items():
        cfg.set_feature(name, value)


_SNAPPY_HEX_MESH_DICT_TEXT = """\
FoamFile { version 2.0; format ascii; class dictionary; object snappyHexMeshDict; }
geometry
{
    motorBike { type box; min (0 0 0); max (1 1 1); }
    igloo { type sphere; centre (3 3 0); radius 3.5; }
}
castellatedMeshControls
{
    locationInMesh (0.5 0.5 0.5);
}
"""

_TOPO_SET_DICT_TEXT = """FoamFile { version 2.0; format ascii; class dictionary; object topoSetDict; }
actions
(
    {
        name box1;
        type cellSet;
        action new;
        source boxToCell;
        box (0 0 0) (1 1 1);
    }
);
"""

_CONTROL_DICT_TEXT = """FoamFile { version 2.0; format ascii; class dictionary; object controlDict; }
application interFoam;
"""


def _make_case_file(case_dir, name: str, text: str) -> str:
    system_dir = case_dir / "system"
    system_dir.mkdir(exist_ok=True)
    path = system_dir / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_switching_case_clears_snappy_and_topo_state(main_window_bm, tmp_path):
    win = main_window_bm
    panel = win.block_mesh_panel

    case_a = tmp_path / "case_a"
    case_a.mkdir()
    snappy_path = _make_case_file(case_a, "snappyHexMeshDict", _SNAPPY_HEX_MESH_DICT_TEXT)
    topo_path = _make_case_file(case_a, "topoSetDict", _TOPO_SET_DICT_TEXT)
    win._load_case_dir(str(case_a))
    win.load_selected_file(snappy_path)
    win.load_selected_file(topo_path)

    assert panel._snappy.shapes
    assert panel._topo.shapes
    assert panel._snappy.shape_actions
    assert panel._topo.shape_actions
    assert panel._snappy.locations
    assert panel._export_stl_act.isEnabled()

    case_b = tmp_path / "case_b"
    case_b.mkdir()
    _make_case_file(case_b, "controlDict", _CONTROL_DICT_TEXT)
    win._load_case_dir(str(case_b))

    assert panel._snappy.shapes == []
    assert panel._topo.shapes == []
    assert panel._snappy.non_geometric == []
    assert panel._topo.non_geometric == []
    assert panel._snappy.locations == []
    # The menus themselves must be rebuilt too, not just the backing lists,
    # otherwise stale per-shape checkboxes from case_a would still be shown.
    assert panel._snappy.shape_actions == []
    assert panel._topo.shape_actions == []
    assert not panel._export_stl_act.isEnabled()


_ASCII_STL = (
    "solid box\n"
    "facet normal 0 0 1\n outer loop\n"
    "  vertex 0 0 0\n  vertex 1 0 0\n  vertex 0 1 0\n"
    " endloop\nendfacet\n"
    "endsolid box\n"
)


def test_switching_case_clears_loaded_stl_overlays(main_window_bm, tmp_path, monkeypatch):
    """Surfaces loaded via STL ▾ > Load STL / OBJ… belong to the case they were
    loaded for; they used to survive clear() and stay drawn over the next case."""
    win = main_window_bm
    panel = win.block_mesh_panel

    case_a = tmp_path / "case_a"
    case_a.mkdir()
    _make_case_file(case_a, "controlDict", _CONTROL_DICT_TEXT)
    win._load_case_dir(str(case_a))

    stl = tmp_path / "surface.stl"
    stl.write_text(_ASCII_STL)
    monkeypatch.setattr(
        block_mesh_panel.QFileDialog,
        "getOpenFileNames",
        staticmethod(lambda *a, **k: ([str(stl)], "")),
    )
    panel._load_stl()
    assert len(panel._surfaces) == 1
    assert panel._clear_stl_act.isEnabled()

    case_b = tmp_path / "case_b"
    case_b.mkdir()
    _make_case_file(case_b, "controlDict", _CONTROL_DICT_TEXT)
    win._load_case_dir(str(case_b))

    assert panel._surfaces == []
    assert not panel._clear_stl_act.isEnabled()
