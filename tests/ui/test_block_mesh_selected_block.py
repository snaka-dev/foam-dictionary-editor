# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Selecting a `block N` tree row highlights that block in the 3-D viewer.

The row index needs no translation: the tree key and the viewer's centroid
labels are both numbered off the parsed order of `blocks ( … )`. These tests
cover the state plumbing (tree selection → panel → RenderSettings) and the
renderer's bounds guard; drawing the actor itself needs a real X display, so it
is verified by hand, as with everything else in this panel.
"""
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

_BLOCK_MESH_DICT = """\
scale   1;

vertices
(
    (0 0 0)
    (1 0 0)
    (1 1 0)
    (0 1 0)
    (0 0 1)
    (1 0 1)
    (1 1 1)
    (0 1 1)
);

blocks
(
    hex (0 1 2 3 4 5 6 7) (10 10 10) simpleGrading (1 1 1)
    hex (0 1 2 3 4 5 6 7) (20 10 10) simpleGrading (1 1 1)
);

boundary
(
);
"""


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])
    return app


@pytest.fixture
def panel(qapp):
    p = BlockMeshPanel()
    p.update_block_mesh("system/blockMeshDict", OpenFoamParser(_BLOCK_MESH_DICT).parse())
    yield p
    p.shutdown()


class TestPanelState:
    def test_no_block_is_highlighted_initially(self, panel):
        assert panel._make_settings().selected_block is None

    def test_set_selected_block_reaches_render_settings(self, panel):
        panel.set_selected_block(1)
        assert panel._make_settings().selected_block == 1

    def test_selection_clears(self, panel):
        panel.set_selected_block(1)
        panel.set_selected_block(None)
        assert panel._make_settings().selected_block is None

    def test_loading_another_mesh_drops_the_highlight(self, panel):
        """The index would point into a different file's blocks."""
        panel.set_selected_block(1)
        panel.update_block_mesh(
            "system/blockMeshDict", OpenFoamParser(_BLOCK_MESH_DICT).parse()
        )
        assert panel._make_settings().selected_block is None


class TestTreeSelectionWiring:
    def test_selecting_a_block_row_highlights_that_block(
        self, main_window, tmp_path, monkeypatch,
    ):
        win = main_window
        (tmp_path / "system").mkdir()
        path = tmp_path / "system" / "blockMeshDict"
        path.write_text(_BLOCK_MESH_DICT, encoding="utf-8")
        win._load_case_dir(str(tmp_path))
        win.load_selected_file(str(path))

        calls: list[int | None] = []
        # The window under test runs with the blockmesh feature off, so stand a
        # recorder in for the panel: what matters here is the index handed over.
        monkeypatch.setattr(
            win, "block_mesh_panel",
            type("P", (), {"set_selected_block": lambda _self, i: calls.append(i)})(),
            raising=False,
        )

        root = win.state.current_root
        blocks = next(c for c in root.children if c.name == "blocks")
        win._highlight_selected_block(blocks.children[1], 1)
        assert calls[-1] == 1

        # anything else clears it
        win._highlight_selected_block(blocks, 0)
        assert calls[-1] is None


class TestRendererGuard:
    """An index the current mesh cannot honour must not raise."""

    def _settings(self, index):
        from ui.panels.block_mesh_renderer import RenderSettings

        return RenderSettings(
            show_vertices=False, show_labels=False, show_edges=False,
            show_block_labels=False, color_blocks=False, solid_blocks=False,
            show_boundary=False, show_axes=False, show_grid=False,
            show_bounds=False, label_font_size=10,
            selected_vertex=None, selected_block=index,
        )

    @pytest.mark.parametrize("index", [None, -1, 5])
    def test_out_of_range_index_draws_nothing(self, index):
        import numpy as np

        from foam.block_mesh_extractor import extract_block_mesh_data
        from ui.panels.block_mesh_renderer import BlockMeshRenderer

        data = extract_block_mesh_data(OpenFoamParser(_BLOCK_MESH_DICT).parse())
        renderer = BlockMeshRenderer(plotter=None)
        pts = np.array(data.vertices, dtype=float)

        # A None plotter would blow up on the first add_mesh, so reaching the
        # end without one proves nothing was drawn.
        renderer._render_selected_block(pts, data, self._settings(index))
