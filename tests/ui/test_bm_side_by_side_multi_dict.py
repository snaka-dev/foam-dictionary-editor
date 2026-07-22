# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Regression tests for the BlockMesh side-by-side corner button
(ui/mixins/_panel_ops.py's _update_bm_side_by_side_btn()).

It used to enable the button only when the current file was exactly
blockMeshDict, even though BlockMeshPanel already overlays
topoSetDict/snappyHexMeshDict geometry onto the same 3-D view (see
foam/topo_set_extractor.py and foam/snappy_hex_mesh_extractor.py). It must
enable for all three dict types and stay disabled otherwise.

Uses a real MainWindow with the BlockMesh feature enabled (terminal
disabled to sidestep the xterm/VTK OpenGL conflict), unlike the shared
`main_window` fixture in tests/conftest.py which disables blockmesh for
lighter, VTK-independent instantiation.
"""
from __future__ import annotations

import sys

import pytest
from PySide6.QtWidgets import QApplication

from ui.panels import block_mesh_panel

pytestmark = pytest.mark.skipif(
    not block_mesh_panel._PYVISTA_OK, reason="pyvista/pyvistaqt not installed"
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])
    return app


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


_BLOCK_MESH_DICT_TEXT = """FoamFile { version 2.0; format ascii; class dictionary; object blockMeshDict; }
scale 1;
vertices ( (0 0 0) (1 0 0) (1 1 0) (0 1 0) (0 0 1) (1 0 1) (1 1 1) (0 1 1) );
blocks ( hex (0 1 2 3 4 5 6 7) (1 1 1) simpleGrading (1 1 1) );
edges ( );
boundary ( );
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

_SNAPPY_HEX_MESH_DICT_TEXT = """FoamFile { version 2.0; format ascii; class dictionary; object snappyHexMeshDict; }
geometry
{
    motorBike { type box; min (0 0 0); max (1 1 1); }
}
castellatedMeshControls
{
    locationInMesh (0.5 0.5 0.5);
}
"""

_CONTROL_DICT_TEXT = """FoamFile { version 2.0; format ascii; class dictionary; object controlDict; }
application interFoam;
"""

_FV_SCHEMES_TEXT = """FoamFile { version 2.0; format ascii; class dictionary; object fvSchemes; }
ddtSchemes { default Euler; }
"""


def _make_case_file(tmp_path, name: str, text: str) -> str:
    system_dir = tmp_path / "system"
    system_dir.mkdir(exist_ok=True)
    path = system_dir / name
    path.write_text(text, encoding="utf-8")
    return str(path)


@pytest.mark.parametrize(
    "filename, text",
    [
        ("blockMeshDict", _BLOCK_MESH_DICT_TEXT),
        ("topoSetDict", _TOPO_SET_DICT_TEXT),
        ("snappyHexMeshDict", _SNAPPY_HEX_MESH_DICT_TEXT),
        # controlDict feeds the sampling overlay, so it is 3-D viewable too.
        ("controlDict", _CONTROL_DICT_TEXT),
    ],
)
def test_side_by_side_button_enabled_for_3d_viewable_dicts(
    main_window_bm, tmp_path, filename, text
):
    win = main_window_bm
    path = _make_case_file(tmp_path, filename, text)
    win._load_case_dir(str(tmp_path))

    win.load_selected_file(path)

    assert win._bm_side_by_side_btn is not None
    assert win._bm_side_by_side_btn.isEnabled()


def test_side_by_side_button_disabled_for_unrelated_dict(main_window_bm, tmp_path):
    win = main_window_bm
    path = _make_case_file(tmp_path, "fvSchemes", _FV_SCHEMES_TEXT)
    win._load_case_dir(str(tmp_path))

    win.load_selected_file(path)

    assert win._bm_side_by_side_btn is not None
    assert not win._bm_side_by_side_btn.isEnabled()


def test_side_by_side_splitter_panes_cannot_fold(main_window_bm):
    """Dragging the handle past a pane's minimum must not snap it to zero
    width, and the BlockMesh panel keeps a small usable minimum."""
    win = main_window_bm
    assert not win._tree_bm_splitter.childrenCollapsible()
    assert win.block_mesh_panel.minimumWidth() == 150
