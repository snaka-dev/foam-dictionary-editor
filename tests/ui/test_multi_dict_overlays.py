# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Several files feeding one overlay -- the `topoSetDict-slices` / `topoSetDict-background` case.

Recognising a non-default name is only half of it. Before this, every overlay except
sampling rebuilt from whichever file was last handed to it, so loading a second
topoSetDict erased the first -- the two would take turns rather than both being drawn.
"""
from __future__ import annotations

import pytest

from foam.parser import OpenFoamParser
from ui.panels import block_mesh_panel
from ui.panels.block_mesh_panel import BlockMeshPanel

pytestmark = pytest.mark.skipif(
    not block_mesh_panel._PYVISTA_OK, reason="pyvista/pyvistaqt not installed"
)

HEADER = "FoamFile { version 2.0; format ascii; class dictionary; object topoSetDict; }\n"

SLICES = HEADER + """
actions ( { name c0; type cellSet; action new; source boxToCell;
            box (0 0 0) (1 1 1); } );
"""
BACKGROUND = HEADER + """
actions ( { name n0; type cellSet; action new; source sphereToCell;
            origin (5 5 5); radius 2; } );
"""
EMPTY = HEADER


@pytest.fixture
def panel(qapp, destroy_widget):  # noqa: ARG001 (qapp required by PySide6)
    p = BlockMeshPanel()
    yield p
    p.shutdown()
    destroy_widget(p)


def _load(panel, name, text):
    panel.update_topo_set(f"/case/system/{name}", OpenFoamParser(text).parse())


def _labels(panel):
    return [a.text() for a in panel._topo.shape_actions]


class TestTwoTopoSetDicts:
    def test_both_files_are_drawn_at_once(self, panel):
        _load(panel, "topoSetDict-slices", SLICES)
        _load(panel, "topoSetDict-background", BACKGROUND)
        labels = _labels(panel)
        assert len(labels) == 2
        assert any("c0" in t for t in labels), labels
        assert any("n0" in t for t in labels), labels

    def test_each_row_says_which_file_it_came_from(self, panel):
        _load(panel, "topoSetDict-slices", SLICES)
        _load(panel, "topoSetDict-background", BACKGROUND)
        labels = _labels(panel)
        assert any("[topoSetDict-slices]" in t for t in labels), labels
        assert any("[topoSetDict-background]" in t for t in labels), labels

    def test_a_single_file_carries_no_attribution(self, panel):
        # Nothing to disambiguate, so the suffix would be noise on every row.
        _load(panel, "topoSetDict-slices", SLICES)
        assert all("[" not in t for t in _labels(panel))

    def test_emptying_one_file_leaves_the_other(self, panel):
        _load(panel, "topoSetDict-slices", SLICES)
        _load(panel, "topoSetDict-background", BACKGROUND)
        _load(panel, "topoSetDict-slices", EMPTY)
        labels = _labels(panel)
        assert len(labels) == 1
        assert "n0" in labels[0], labels

    def test_reloading_the_same_file_replaces_rather_than_duplicates(self, panel):
        _load(panel, "topoSetDict-slices", SLICES)
        _load(panel, "topoSetDict-slices", SLICES)
        assert len(_labels(panel)) == 1

    def test_two_files_sharing_a_basename_do_not_overwrite_each_other(self, panel):
        # Keyed by full path, so an extra directory holding a second topoSetDict works.
        panel.update_topo_set("/case/system/topoSetDict", OpenFoamParser(SLICES).parse())
        panel.update_topo_set("/case/other/topoSetDict", OpenFoamParser(BACKGROUND).parse())
        assert len(_labels(panel)) == 2

    def test_clear_drops_every_file(self, panel):
        _load(panel, "topoSetDict-slices", SLICES)
        _load(panel, "topoSetDict-background", BACKGROUND)
        panel.clear()
        assert _labels(panel) == []

    def test_hiding_a_shape_survives_an_edit_to_the_other_file(self, panel):
        # The union is rebuilt on every edit; a toggle must not be reset by a change to
        # a file it has nothing to do with. Mirrors the sampling overlay's guarantee.
        _load(panel, "topoSetDict-slices", SLICES)
        _load(panel, "topoSetDict-background", BACKGROUND)
        slices_act = next(a for a in panel._topo.shape_actions if "[topoSetDict-slices]" in a.text())
        slices_act.setChecked(False)
        _load(panel, "topoSetDict-background", BACKGROUND)
        still = next(a for a in panel._topo.shape_actions if "[topoSetDict-slices]" in a.text())
        assert still.isChecked() is False


class TestForgetFile:
    """Dropping one file's contribution -- what a changed "show as" override needs.

    Re-dispatching alone cannot clean up after an override change: the overlay a file
    used to feed is not the one being written now, and clearing the override to
    "automatic" dispatches nothing at all.
    """

    def test_forgetting_a_file_removes_only_its_rows(self, panel):
        _load(panel, "topoSetDict-slices", SLICES)
        _load(panel, "topoSetDict-background", BACKGROUND)
        panel.forget_file("/case/system/topoSetDict-slices")
        labels = _labels(panel)
        assert len(labels) == 1
        assert "n0" in labels[0], labels

    def test_forgetting_the_last_file_empties_the_overlay(self, panel):
        _load(panel, "topoSetDict-slices", SLICES)
        panel.forget_file("/case/system/topoSetDict-slices")
        assert _labels(panel) == []

    def test_forgetting_an_unknown_path_changes_nothing(self, panel):
        _load(panel, "topoSetDict-slices", SLICES)
        panel.forget_file("/case/system/never-loaded")
        assert len(_labels(panel)) == 1

    def test_switching_a_file_between_overlays_leaves_nothing_behind(self, panel):
        # What an override change does: the file was drawn as topoSet, now as setFields.
        set_fields = (
            "FoamFile { version 2.0; format ascii; class dictionary; object setFieldsDict; }\n"
            "regions ( boxToCell { box (0 0 0) (1 1 1);"
            " fieldValues ( volScalarFieldValue alpha.water 1 ); } );\n"
        )
        path = "/case/system/ambiguous"
        _load(panel, "ambiguous", SLICES)
        assert len(_labels(panel)) == 1
        panel.forget_file(path)
        panel.update_set_fields(path, OpenFoamParser(set_fields).parse())
        assert _labels(panel) == []
        assert len(panel._set_fields.shape_actions) == 1
