# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""MainWindow._prime_viewer: the 3-D view shows a case's shapes without opening files.

The `main_window` fixture runs without VTK, so a recording stand-in takes
the panel's place: what is under test is which files reach the view, when,
and that drawing them touches nothing else.
"""
from __future__ import annotations

import os

import pytest

from foam import include_expand
from services import include_scan

_TOPO = (
    "FoamFile { object topoSetDict; }\n"
    "actions ( { name c; type cellSet; action new; source boxToCell; box (0 0 0) (1 1 1); } );\n"
)
_BLOCK = (
    "FoamFile { object blockMeshDict; }\n"
    "vertices ((0 0 0) (1 0 0) (1 1 0) (0 1 0) (0 0 1) (1 0 1) (1 1 1) (0 1 1));\n"
    "blocks ( hex (0 1 2 3 4 5 6 7) (1 1 1) simpleGrading (1 1 1) );\n"
)
_SAMPLING = "sampleSets { type sets; sets { g1 { type face; start (0 0 0); end (1 0 0); } } }\n"
_CONTROL = "FoamFile { object controlDict; }\napplication icoFoam;\n"


class _Panel:
    """Records which file reached which overlay, and what was withdrawn."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.forgotten: list[str] = []

    def update_block_mesh(self, path, root):
        self.calls.append(("block_mesh", os.path.basename(path)))

    def update_topo_set(self, path, root):
        self.calls.append(("topo_set", os.path.basename(path)))

    def update_snappy_hex_mesh(self, path, root):
        self.calls.append(("snappy", os.path.basename(path)))

    def update_set_fields(self, path, root):
        self.calls.append(("set_fields", os.path.basename(path)))

    def update_sampling(self, path, root, name=None):
        self.calls.append(("sampling", os.path.basename(path)))

    def forget_file(self, path):
        self.forgotten.append(os.path.basename(path))

    def clear(self): ...
    def set_case_dir(self, directory): ...
    def shutdown(self): ...


@pytest.fixture(autouse=True)
def _clear_caches():
    include_scan.clear_scan_cache()
    include_expand.clear_expand_cache()
    yield
    include_scan.clear_scan_cache()
    include_expand.clear_expand_cache()


@pytest.fixture
def panel(main_window, monkeypatch):
    recording = _Panel()
    monkeypatch.setattr(main_window, "block_mesh_panel", recording)
    return recording


def _case(tmp_path, *, include_sampling=False):
    case = tmp_path / "case"
    (case / "system").mkdir(parents=True)
    (case / "constant").mkdir()
    (case / "0").mkdir()
    (case / "system" / "blockMeshDict").write_text(_BLOCK)
    (case / "system" / "topoSetDict").write_text(_TOPO)
    (case / "system" / "sampling").write_text(_SAMPLING)
    functions = 'functions\n{\n    #sinclude "sampling"\n}\n' if include_sampling else ""
    (case / "system" / "controlDict").write_text(_CONTROL + functions)
    (case / "0" / "U").write_text("FoamFile { object U; }\ninternalField uniform (0 0 0);\n")
    return case


def test_opening_a_case_draws_its_dictionaries_without_opening_them(main_window, panel, tmp_path):
    case = _case(tmp_path)
    main_window._load_case_dir(str(case))
    assert set(panel.calls) == {
        ("block_mesh", "blockMeshDict"),
        ("topo_set", "topoSetDict"),
        ("sampling", "sampling"),
        ("sampling", "controlDict"),
    }
    # Drawing is all it did: nothing opened, nothing edited.
    assert main_window.state.file_buffers == {}
    assert not any(main_window.state.file_dirty.values())
    assert main_window.state.current_file is None


def test_an_included_file_is_not_drawn_twice(main_window, panel, tmp_path):
    # damBreak: controlDict pulls system/sampling in with #sinclude.
    case = _case(tmp_path, include_sampling=True)
    main_window._load_case_dir(str(case))
    drawn = [name for _, name in panel.calls]
    assert "controlDict" in drawn
    # Includers go first, so the included file is never drawn at all.
    assert "sampling" not in drawn and panel.forgotten == []


def test_dropping_the_include_draws_the_file_on_its_own(main_window, panel, tmp_path):
    case = _case(tmp_path, include_sampling=True)
    main_window._load_case_dir(str(case))
    panel.calls.clear()
    control = case / "system" / "controlDict"
    control.write_text(_CONTROL)
    os.utime(control, ns=(1, 2_000_000_000_000_000_000))
    main_window._reload_file_list()
    assert ("sampling", "sampling") in panel.calls


def test_an_unchanged_file_is_not_read_again(main_window, panel, tmp_path):
    case = _case(tmp_path)
    main_window._load_case_dir(str(case))
    panel.calls.clear()
    main_window._reload_file_list()
    assert panel.calls == []


def test_a_file_changed_on_disk_is_drawn_again(main_window, panel, tmp_path):
    case = _case(tmp_path)
    main_window._load_case_dir(str(case))
    panel.calls.clear()
    topo = case / "system" / "topoSetDict"
    topo.write_text(_TOPO + "// edited elsewhere\n")
    main_window._reload_file_list()
    assert panel.calls == [("topo_set", "topoSetDict")]


def test_a_deleted_file_takes_its_shapes_with_it(main_window, panel, tmp_path):
    case = _case(tmp_path)
    main_window._load_case_dir(str(case))
    (case / "system" / "topoSetDict").unlink()
    main_window._reload_file_list()
    assert "topoSetDict" in panel.forgotten


def test_an_open_file_is_left_to_its_own_text(main_window, panel, tmp_path):
    case = _case(tmp_path)
    main_window._load_case_dir(str(case))
    topo = str(case / "system" / "topoSetDict")
    main_window.load_selected_file(topo)
    main_window.state.file_buffers[topo] += "// unsaved\n"
    main_window.state.file_dirty[topo] = True
    (case / "system" / "topoSetDict").write_text(_TOPO + "// changed on disk\n")
    panel.calls.clear()
    main_window._reload_file_list()
    # Priming leaves an open file alone; its buffer, unsaved edit and all,
    # is what the view shows.
    assert ("topo_set", "topoSetDict") not in panel.calls


def test_large_unparseable_and_field_files_are_skipped(main_window, panel, tmp_path, monkeypatch):
    import ui.mixins._model_ops as model_ops

    case = _case(tmp_path)
    (case / "system" / "broken").write_text("sampleSets { type sets; sets { (((\n")
    monkeypatch.setattr(model_ops, "_PRIME_MAX_BYTES", len(_BLOCK) - 1)
    main_window._load_case_dir(str(case))
    names = [name for _, name in panel.calls]
    assert "blockMeshDict" not in names  # over the size limit
    assert "broken" not in names
    assert "U" not in names  # 0/ is never read for the view


def test_a_case_switch_starts_afresh(main_window, panel, tmp_path):
    main_window._load_case_dir(str(_case(tmp_path)))
    other = tmp_path / "other"
    (other / "system").mkdir(parents=True)
    (other / "system" / "controlDict").write_text(_CONTROL)
    main_window._load_case_dir(str(other))
    assert all(str(other) in p for p in main_window._viewer_primed)
