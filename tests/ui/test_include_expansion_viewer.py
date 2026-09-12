# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""MainWindow wiring for `#include` expansion into the 3-D viewer.

The `main_window` fixture disables the blockmesh feature (VTK is not available
under the offscreen platform), so these tests install a recording stand-in for
`block_mesh_panel`. That is the right seam anyway: what is under test is which
tree MainWindow hands the panel and when, not what VTK does with it.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from foam import include_expand
from foam.block_mesh_extractor import extract_block_mesh_data
from services import include_scan

_HEADER = """FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      blockMeshDict;
}
"""

_VERTICES = """vertices
(
    ($x0 $y0 $z0) ($xMax $y0 $z0) ($xMax $yMax $z0) ($x0 $yMax $z0)
    ($x0 $y0 $zMax) ($xMax $y0 $zMax) ($xMax $yMax $zMax) ($x0 $yMax $zMax)
);
blocks ( hex (0 1 2 3 4 5 6 7) (1 1 1) simpleGrading (1 1 1) );
"""

_SETTINGS = """scale 0.001;
x0 0; y0 0; z0 0;
xMax 6;
yMax 3;
zMax $xMax;
"""


class _RecordingPanel:
    """Stands in for BlockMeshPanel, recording the roots it is handed."""

    def __init__(self) -> None:
        self.block_mesh_calls: list[tuple[str, object]] = []
        self.topo_set_calls: list[tuple[str, object]] = []

    def update_block_mesh(self, path, root):
        self.block_mesh_calls.append((path, root))

    def update_topo_set(self, path, root):
        self.topo_set_calls.append((path, root))

    def update_snappy_hex_mesh(self, path, root): ...
    def update_set_fields(self, path, root): ...
    def update_sampling(self, path, root): ...
    def clear(self): ...
    def set_case_dir(self, directory): ...
    def shutdown(self): ...


@pytest.fixture(autouse=True)
def _clear_caches():
    include_scan.clear_scan_cache()
    include_scan.clear_foam_etc_cache()
    include_expand.clear_expand_cache()
    yield
    include_scan.clear_scan_cache()
    include_scan.clear_foam_etc_cache()
    include_expand.clear_expand_cache()


@pytest.fixture
def panel(main_window):
    recording = _RecordingPanel()
    main_window.block_mesh_panel = recording
    return recording


def _case(tmp_path: Path) -> Path:
    case = tmp_path / "case"
    (case / "system").mkdir(parents=True)
    (case / "constant").mkdir()
    (case / "system" / "settings-region").write_text(_SETTINGS)
    (case / "system" / "blockMeshDict").write_text(
        _HEADER + '#include "settings-region"\n' + _VERTICES
    )
    (case / "system" / "controlDict").write_text(_HEADER)
    return case


def test_viewer_receives_the_expanded_tree(main_window, panel, tmp_path):
    case = _case(tmp_path)
    main_window._load_case_dir(str(case))
    main_window.load_selected_file(str(case / "system" / "blockMeshDict"))

    assert panel.block_mesh_calls, "the panel was never updated"
    _path, root = panel.block_mesh_calls[-1]
    data = extract_block_mesh_data(root)
    assert len(data.vertices) == 8
    assert data.scale == 0.001
    assert [max(v[i] for v in data.vertices) for i in range(3)] == pytest.approx([0.006, 0.003, 0.006])


def test_tree_and_editor_keep_the_unexpanded_root(main_window, panel, tmp_path):
    """The merged tree must never reach anything that writes."""
    case = _case(tmp_path)
    main_window._load_case_dir(str(case))
    bm = str(case / "system" / "blockMeshDict")
    main_window.load_selected_file(bm)

    tree_root = main_window.state.current_root
    assert extract_block_mesh_data(tree_root).vertices == []
    assert any(c.node_type == "directive_entry" for c in tree_root.children)
    # The tree's root is also what was cached and what the panel did NOT get.
    assert main_window.state.parsed_roots[bm] is tree_root
    assert panel.block_mesh_calls[-1][1] is not tree_root


def test_sources_are_tracked_for_the_dependent_refresh(main_window, panel, tmp_path):
    case = _case(tmp_path)
    main_window._load_case_dir(str(case))
    bm = str(case / "system" / "blockMeshDict")
    main_window.load_selected_file(bm)

    assert main_window.state.viewer_include_sources[bm] == frozenset(
        {str(case / "system" / "settings-region")}
    )


def test_editing_the_included_file_refreshes_the_viewer(main_window, panel, tmp_path):
    """The whole point: change a dimension in one place and the view follows."""
    case = _case(tmp_path)
    main_window._load_case_dir(str(case))
    bm = str(case / "system" / "blockMeshDict")
    settings = str(case / "system" / "settings-region")

    main_window.load_selected_file(bm)
    before = len(panel.block_mesh_calls)
    assert extract_block_mesh_data(panel.block_mesh_calls[-1][1]).vertices[2][1] == pytest.approx(0.003)

    main_window.load_selected_file(settings)
    main_window.editor_panel.set_text(_SETTINGS.replace("yMax 3;", "yMax 9;"))
    main_window.apply_text_to_tree()

    assert len(panel.block_mesh_calls) > before, "blockMeshDict was not re-rendered"
    data = extract_block_mesh_data(panel.block_mesh_calls[-1][1])
    assert data.vertices[2][1] == pytest.approx(0.009)


def test_unsaved_edits_to_the_included_file_are_used(main_window, panel, tmp_path):
    """No save required -- the buffer is served ahead of the file on disk."""
    case = _case(tmp_path)
    main_window._load_case_dir(str(case))
    settings = str(case / "system" / "settings-region")

    main_window.load_selected_file(settings)
    main_window.editor_panel.set_text(_SETTINGS.replace("yMax 3;", "yMax 9;"))
    main_window.apply_text_to_tree()
    # Still dirty: nothing has been written to disk.
    assert main_window.state.file_dirty.get(settings)
    assert "yMax 3;" in Path(settings).read_text()

    main_window.load_selected_file(str(case / "system" / "blockMeshDict"))
    data = extract_block_mesh_data(panel.block_mesh_calls[-1][1])
    assert data.vertices[2][1] == pytest.approx(0.009)


def test_a_dict_without_includes_tracks_nothing(main_window, panel, tmp_path):
    case = _case(tmp_path)
    bm = case / "system" / "blockMeshDict"
    bm.write_text(_HEADER + _SETTINGS + _VERTICES)
    main_window._load_case_dir(str(case))
    main_window.load_selected_file(str(bm))

    assert str(bm) not in main_window.state.viewer_include_sources
    # ...and the panel still gets a fully resolved mesh, from the file alone.
    assert len(extract_block_mesh_data(panel.block_mesh_calls[-1][1]).vertices) == 8


def test_case_switch_drops_the_tracking(main_window, panel, tmp_path):
    case = _case(tmp_path)
    main_window._load_case_dir(str(case))
    main_window.load_selected_file(str(case / "system" / "blockMeshDict"))
    assert main_window.state.viewer_include_sources

    other = _case(tmp_path / "other")
    main_window._load_case_dir(str(other))
    assert main_window.state.viewer_include_sources == {}
