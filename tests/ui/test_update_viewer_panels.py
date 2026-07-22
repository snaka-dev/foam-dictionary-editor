# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for MainWindow._update_viewer_panels (ui/mixins/_model_ops.py).

The file-name → 3-D viewer dispatch used to be copy-pasted into the load,
save, and tree-edit paths, and the "Apply Text to Tree" copy was missing the
snappyHexMeshDict case, so applying edited snappy text never refreshed the
3-D overlay. The dispatch is now a single helper shared by all paths; these
tests pin the mapping and the previously missing apply path.
"""
from __future__ import annotations

import pytest


class _RecordingBlockMeshPanel:
    """Stands in for BlockMeshPanel; records which update entry point ran."""

    def __init__(self):
        self.calls: list[tuple[str, str]] = []

    def update_block_mesh(self, path, root):
        self.calls.append(("block_mesh", path))

    def update_topo_set(self, path, root):
        self.calls.append(("topo_set", path))

    def update_snappy_hex_mesh(self, path, root):
        self.calls.append(("snappy_hex_mesh", path))

    def update_set_fields(self, path, root):
        self.calls.append(("set_fields", path))

    def update_sampling(self, path, root):
        self.calls.append(("sampling", path))

    def clear(self):
        self.calls.append(("clear", ""))

    def shutdown(self):
        pass


_SNAPPY_TEXT = """FoamFile { version 2.0; format ascii; class dictionary; object snappyHexMeshDict; }
geometry
{
    refBox { type box; min (0 0 0); max (1 1 1); }
}
castellatedMeshControls
{
    locationInMesh (0.5 0.5 0.5);
}
"""

_TOPO_TEXT = """FoamFile { version 2.0; format ascii; class dictionary; object topoSetDict; }
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

_BLOCK_MESH_TEXT = """FoamFile { version 2.0; format ascii; class dictionary; object blockMeshDict; }
scale 1;
vertices ( (0 0 0) (1 0 0) (1 1 0) (0 1 0) (0 0 1) (1 0 1) (1 1 1) (0 1 1) );
blocks ( hex (0 1 2 3 4 5 6 7) (1 1 1) simpleGrading (1 1 1) );
edges ( );
boundary ( );
"""

_SET_FIELDS_TEXT = """FoamFile { version 2.0; format ascii; class dictionary; object setFieldsDict; }
defaultFieldValues ( volScalarFieldValue alpha.water 0 );
regions
(
    boxToCell
    {
        box (0 0 -1) (0.1461 0.292 1);
        fieldValues ( volScalarFieldValue alpha.water 1 );
    }
);
"""

_CONTROL_TEXT = """FoamFile { version 2.0; format ascii; class dictionary; object controlDict; }
application interFoam;
functions
{
    myProbes { type probes; fields (p); probeLocations ( (0.1 0.2 0.3) ); }
}
"""

_SAMPLE_TEXT = """FoamFile { version 2.0; format ascii; class dictionary; object sample; }
type sets;
fields (U);
sets
{
    lineA { type lineUniform; axis distance; start (0 0 0); end (1 0 0); nPoints 10; }
}
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
    "filename, text, expected",
    [
        ("blockMeshDict", _BLOCK_MESH_TEXT, "block_mesh"),
        ("topoSetDict", _TOPO_TEXT, "topo_set"),
        ("snappyHexMeshDict", _SNAPPY_TEXT, "snappy_hex_mesh"),
        ("setFieldsDict", _SET_FIELDS_TEXT, "set_fields"),
        ("controlDict", _CONTROL_TEXT, "sampling"),
        ("sample", _SAMPLE_TEXT, "sampling"),
    ],
)
def test_load_dispatches_to_matching_viewer(main_window, tmp_path, filename, text, expected):
    win = main_window
    panel = _RecordingBlockMeshPanel()
    win.block_mesh_panel = panel
    path = _make_case_file(tmp_path, filename, text)
    win._load_case_dir(str(tmp_path))

    win.load_selected_file(path)

    assert (expected, path) in panel.calls


def test_load_unrelated_dict_does_not_dispatch(main_window, tmp_path):
    win = main_window
    panel = _RecordingBlockMeshPanel()
    win.block_mesh_panel = panel
    path = _make_case_file(tmp_path, "fvSchemes", _FV_SCHEMES_TEXT)
    win._load_case_dir(str(tmp_path))

    win.load_selected_file(path)

    assert [c for c in panel.calls if c[0] != "clear"] == []


def test_apply_text_to_tree_refreshes_snappy_overlay(main_window, tmp_path):
    """Regression: the apply path used to skip snappyHexMeshDict entirely."""
    win = main_window
    panel = _RecordingBlockMeshPanel()
    win.block_mesh_panel = panel
    path = _make_case_file(tmp_path, "snappyHexMeshDict", _SNAPPY_TEXT)
    win._load_case_dir(str(tmp_path))
    win.load_selected_file(path)
    panel.calls.clear()

    win.editor_panel.set_text(_SNAPPY_TEXT.replace("(1 1 1)", "(2 2 2)"))
    win.apply_text_to_tree()

    assert ("snappy_hex_mesh", path) in panel.calls
