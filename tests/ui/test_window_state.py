# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Cover ui/window_state.py and the screenshot spec that is its main input.

The capture tool itself needs a real X display, so what is testable here is the
state layer underneath it: serialisation, the defaults merge, key-path
addressing, and reading a live window back. Plus the spec file, which is
hand-written and so the thing most likely to drift.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from foam.parser import OpenFoamParser
from model.tree_model import FoamTreeModel
from ui.window_state import (
    SPLITTERS,
    BlockMeshViewState,
    WindowState,
    apply_window_state,
    capture_window_state,
    index_for_key_path,
    key_path_for_index,
    load_saved_state,
)

SPEC_PATH = Path(__file__).resolve().parents[2] / "tools" / "screenshot_specs.json"

TOPO_SET_TEXT = """\
actions
(
    {
        name    c0;
        type    cellSet;
        action  new;
        source  boxToCell;
    }

    {
        name    c1;
        type    cellSet;
        action  add;
        source  sphereToCell;
    }
);
"""


class TestSerialisation:
    def test_round_trip_preserves_every_set_field(self):
        state = WindowState(
            geometry="Z2VvbQ==",
            window_size=(1200, 800),
            splitters={"main": "c3Bs"},
            splitter_sizes={"right": [460, 260]},
            upper_tab="BlockMesh",
            lower_tab="Editor",
            side_by_side=True,
            block_mesh_visible=True,
            terminal_mode="simple",
            case_dir="/cases/motorBike",
            preload_files=["system/blockMeshDict"],
            current_file="system/snappyHexMeshDict",
            tree_selection=["actions", 0, "name"],
            tree_expand=[["castellatedMeshControls"]],
            editor_zoom=2,
            block_mesh=BlockMeshViewState(
                toggles={"boundary_faces": False},
                overlays={"topo_set": True},
                label_font_size=14,
                camera=((1.0, 2.0, 3.0), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
            ),
        )
        assert WindowState.from_dict(state.to_dict()) == state

    def test_unset_fields_are_left_out_of_the_dict(self):
        assert WindowState(upper_tab="Tree").to_dict() == {"upper_tab": "Tree"}

    def test_unknown_field_is_rejected(self):
        # A silently ignored typo is how a spec drifts from what it claims.
        with pytest.raises(ValueError, match="upper_tabb"):
            WindowState.from_dict({"upper_tabb": "Tree"})

    def test_unknown_block_mesh_field_is_rejected(self):
        with pytest.raises(ValueError, match="labelsize"):
            WindowState.from_dict({"block_mesh": {"labelsize": 12}})

    def test_camera_must_be_three_triples(self):
        with pytest.raises(ValueError, match="three"):
            WindowState.from_dict({"block_mesh": {"camera": [[1, 2, 3], [0, 0, 0]]}})

    def test_camera_accepts_ints_and_returns_floats(self):
        state = WindowState.from_dict(
            {"block_mesh": {"camera": [[1, 2, 3], [0, 0, 0], [0, 0, 1]]}}
        )
        assert state.block_mesh is not None
        assert state.block_mesh.camera == ((1.0, 2.0, 3.0), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0))


class TestLenientParsing:
    """The saved-session half: a bad blob costs a layout, never the launch.

    Every one of these raises under the strict path the screenshot specs use;
    the point of each test is that the lenient path does not.
    """

    def test_unknown_field_is_dropped_not_rejected(self):
        # The blob a *newer* version wrote: it names a field this one has never
        # heard of, and everything else in it must still apply.
        state = load_saved_state({"upper_tab": "Tree", "future_field": 1})
        assert state == WindowState(upper_tab="Tree")

    def test_unknown_block_mesh_field_is_dropped(self):
        state = load_saved_state({"block_mesh": {"label_font_size": 12, "whatever": True}})
        assert state is not None and state.block_mesh is not None
        assert state.block_mesh.label_font_size == 12

    def test_malformed_camera_is_dropped_and_the_rest_survives(self):
        state = load_saved_state(
            {"upper_tab": "Tree", "block_mesh": {"label_font_size": 9, "camera": [[1, 2, 3]]}}
        )
        assert state is not None and state.block_mesh is not None
        assert state.block_mesh.camera is None
        assert state.block_mesh.label_font_size == 9
        assert state.upper_tab == "Tree"

    def test_malformed_window_size_is_dropped(self):
        state = load_saved_state({"window_size": "1200x800", "upper_tab": "Tree"})
        assert state is not None
        assert state.window_size is None
        assert state.upper_tab == "Tree"

    def test_malformed_splitter_sizes_are_dropped(self):
        state = load_saved_state({"splitter_sizes": {"main": ["wide", "narrow"]}})
        assert state is not None and state.splitter_sizes == {}

    @pytest.mark.parametrize("blob", [None, [], "", 7, "not json at all"])
    def test_unusable_blob_gives_none(self, blob):
        assert load_saved_state(blob) is None

    def test_strict_is_still_the_default(self):
        with pytest.raises(ValueError, match="future_field"):
            WindowState.from_dict({"upper_tab": "Tree", "future_field": 1})


class TestLenientApply:
    """Paths that have since moved are skipped and named, not raised over."""

    def test_missing_case_dir_skips_the_files_and_notes_it(self, main_window, tmp_path):
        gone = str(tmp_path / "no-such-case")
        notes = apply_window_state(
            main_window,
            WindowState(case_dir=gone, current_file="system/controlDict", upper_tab="Tree"),
            strict=False,
        )
        assert any("case directory is gone" in note for note in notes)
        assert main_window.state.current_case_dir is None
        # The layout half still applied.
        assert main_window.upper_tabs.tabText(main_window.upper_tabs.currentIndex()) == "Tree"

    def test_missing_file_is_skipped_but_the_case_still_loads(self, main_window, tmp_path):
        case = tmp_path / "case"
        (case / "system").mkdir(parents=True)
        notes = apply_window_state(
            main_window,
            WindowState(case_dir=str(case), current_file="system/controlDict"),
            strict=False,
        )
        assert any("file is gone" in note for note in notes)
        assert main_window.state.current_case_dir == str(case)

    def test_large_non_dictionary_file_is_not_reopened(self, main_window, tmp_path):
        # load_selected_file asks "Open anyway?" in a modal for these, warning
        # that the window will freeze. A restore must neither ask at startup
        # nor answer on the user's behalf. A log.* run log is the real case.
        case = tmp_path / "case"
        case.mkdir()
        (case / "log.simpleFoam").write_text("Time = 1\n" * 40000, encoding="utf-8")
        notes = apply_window_state(
            main_window,
            WindowState(case_dir=str(case), current_file="log.simpleFoam"),
            strict=False,
        )
        assert any("large file not reopened" in note for note in notes)
        assert main_window.state.current_file is None

    def test_unknown_tab_label_is_skipped(self, main_window):
        # What a session saved in another language looks like: tabs are
        # addressed by their displayed text, which tr() translates.
        notes = apply_window_state(main_window, WindowState(lower_tab="エディタ"), strict=False)
        assert any("エディタ" in note for note in notes)

    def test_unknown_splitter_is_skipped(self, main_window):
        notes = apply_window_state(
            main_window, WindowState(splitter_sizes={"nope": [1, 2]}), strict=False
        )
        assert any("'nope'" in note for note in notes)

    def test_missing_tree_row_is_skipped(self, main_window, tmp_path, control_dict_text):
        case = tmp_path / "case"
        (case / "system").mkdir(parents=True)
        (case / "system" / "controlDict").write_text(control_dict_text, encoding="utf-8")
        notes = apply_window_state(
            main_window,
            WindowState(
                case_dir=str(case),
                current_file="system/controlDict",
                tree_selection=["deletedSinceLastRun"],
            ),
            strict=False,
        )
        assert any("tree row is gone" in note for note in notes)

    def test_a_clean_state_produces_no_notes(self, main_window, tmp_path, control_dict_text):
        case = tmp_path / "case"
        (case / "system").mkdir(parents=True)
        (case / "system" / "controlDict").write_text(control_dict_text, encoding="utf-8")
        notes = apply_window_state(
            main_window,
            WindowState(
                case_dir=str(case),
                current_file="system/controlDict",
                tree_selection=["startTime"],
                upper_tab="Tree",
                lower_tab="Editor",
            ),
            strict=False,
        )
        assert notes == []
        assert main_window.state.current_file == str(case / "system" / "controlDict")

    def test_strict_still_raises_for_a_spec(self, main_window):
        with pytest.raises(ValueError, match="no tab labelled"):
            apply_window_state(main_window, WindowState(lower_tab="Nope"))


class TestMergedWith:
    def test_unset_field_keeps_the_default(self):
        defaults = WindowState(window_size=(1200, 800), lower_tab="Editor")
        merged = defaults.merged_with(WindowState(upper_tab="BlockMesh"))
        assert merged.window_size == (1200, 800)
        assert merged.lower_tab == "Editor"
        assert merged.upper_tab == "BlockMesh"

    def test_set_field_overrides_the_default(self):
        defaults = WindowState(upper_tab="Tree")
        assert defaults.merged_with(WindowState(upper_tab="Boundary")).upper_tab == "Boundary"

    def test_false_overrides_a_true_default(self):
        # side_by_side is the case that matters: False is a value, not "unset".
        defaults = WindowState(side_by_side=True)
        assert defaults.merged_with(WindowState(side_by_side=False)).side_by_side is False

    def test_block_mesh_merges_one_level_deep(self):
        defaults = WindowState(
            block_mesh=BlockMeshViewState(toggles={"grid": False}, label_font_size=10)
        )
        over = WindowState(block_mesh=BlockMeshViewState(toggles={"axes": False}))
        merged = defaults.merged_with(over).block_mesh
        assert merged is not None
        assert merged.toggles == {"grid": False, "axes": False}
        assert merged.label_font_size == 10


class TestKeyPaths:
    @pytest.fixture
    def model(self, qapp):
        root = OpenFoamParser(TOPO_SET_TEXT).parse()
        return FoamTreeModel(root)

    def test_named_path_resolves(self, model):
        index = index_for_key_path(model, ["actions"])
        assert model.data(index) == "actions"

    def test_int_element_addresses_an_anonymous_row(self, model):
        # The entries of `actions ( … )` have no key of their own.
        index = index_for_key_path(model, ["actions", 1, "name"])
        assert index.isValid()
        assert model.data(index.siblingAtColumn(FoamTreeModel.COL_VALUE)) == "c1"

    def test_missing_key_gives_an_invalid_index(self, model):
        assert not index_for_key_path(model, ["actions", 0, "nope"]).isValid()

    def test_out_of_range_row_gives_an_invalid_index(self, model):
        assert not index_for_key_path(model, ["actions", 9]).isValid()

    def test_key_path_round_trips(self, model):
        path = ["actions", 1, "action"]
        index = index_for_key_path(model, path)
        assert key_path_for_index(index) == path


class TestCaptureLiveWindow:
    def test_captures_tabs_and_splitters(self, main_window):
        state = capture_window_state(main_window)
        assert state.upper_tab == "Tree"
        assert state.lower_tab == "Editor"
        # The fixture disables the terminal and BlockMesh features, so those
        # two are absent rather than merely unset.
        assert state.terminal_mode is None
        assert state.block_mesh is None
        assert set(state.splitters) == set(SPLITTERS)

    def test_capture_round_trips_through_json(self, main_window):
        state = capture_window_state(main_window)
        assert WindowState.from_dict(json.loads(json.dumps(state.to_dict()))) == state

    def test_captures_the_editor_zoom(self, main_window):
        main_window.editor_panel.editor.set_zoom_steps(3)
        try:
            assert capture_window_state(main_window).editor_zoom == 3
        finally:
            main_window.editor_panel.editor.reset_zoom()

    def test_applying_a_state_restores_the_editor_zoom(self, main_window):
        editor = main_window.editor_panel.editor
        try:
            apply_window_state(main_window, WindowState(editor_zoom=4))
            assert editor.zoom_steps() == 4
        finally:
            editor.reset_zoom()

    def test_a_state_that_says_nothing_about_zoom_leaves_it_alone(self, main_window):
        editor = main_window.editor_panel.editor
        editor.set_zoom_steps(2)
        try:
            apply_window_state(main_window, WindowState(upper_tab="Tree"))
            assert editor.zoom_steps() == 2
        finally:
            editor.reset_zoom()


class TestScreenshotSpec:
    @pytest.fixture
    def spec(self):
        return json.loads(SPEC_PATH.read_text(encoding="utf-8"))

    def test_defaults_are_a_valid_state(self, spec):
        WindowState.from_dict(spec["defaults"])

    def test_every_shot_state_is_valid(self, spec):
        for name, entry in spec["shots"].items():
            defaults = WindowState.from_dict(spec["defaults"])
            merged = defaults.merged_with(WindowState.from_dict(entry["state"]))
            assert merged.case_dir, f"{name}: no case_dir"
            assert merged.current_file, f"{name}: no current_file"

    def test_every_shot_names_at_least_one_output(self, spec):
        for name, entry in spec["shots"].items():
            assert entry.get("outputs"), f"{name}: no outputs"

    def test_no_two_shots_write_the_same_file(self, spec):
        written = [
            filename
            for entry in spec["shots"].values()
            for filename in entry["outputs"].values()
        ]
        assert len(written) == len(set(written))

    def test_compare_shots_name_cases_outside_a_home_directory(self, spec):
        # The diff bar prints the reference case's full path into the image, so
        # a compare shot run from $HOME would publish the capturing user's name.
        # See DEVELOPER.md's "Screenshot capture".
        for name, entry in spec["shots"].items():
            reference = entry.get("compare_with")
            if not reference:
                continue
            for path in (reference, entry["state"]["case_dir"]):
                assert "{repo}" not in path and "{cases}" not in path, (
                    f"{name}: both cases must be outside $HOME, so neither can be "
                    f"a placeholder that resolves under it ({path})"
                )
                assert not path.startswith(str(Path.home())), f"{name}: {path}"

    def test_case_dir_placeholders_are_known(self, spec):
        for name, entry in spec["shots"].items():
            case_dir = entry["state"].get("case_dir", "")
            for placeholder in ("{repo}", "{cases}"):
                case_dir = case_dir.replace(placeholder, "")
            assert "{" not in case_dir, f"{name}: unknown placeholder in case_dir"
