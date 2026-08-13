# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for the STL ▾ menu's loaded-surface handling.

Covers the multi-file 'Load STL / OBJ…' selection and the per-file rows it
feeds: individual show/hide, individual unload, and re-loading a path in place.
"""
from __future__ import annotations

import pytest

from ui.panels import block_mesh_panel
from ui.panels.block_mesh_panel import BlockMeshPanel

pytestmark = pytest.mark.skipif(
    not block_mesh_panel._PYVISTA_OK, reason="pyvista/pyvistaqt not installed"
)

_ASCII_STL = (
    "solid box\n"
    "facet normal 0 0 1\n outer loop\n"
    "  vertex 0 0 0\n  vertex 1 0 0\n  vertex 0 1 0\n"
    " endloop\nendfacet\n"
    "endsolid box\n"
)


def _write_stl(tmp_path, name: str, text: str = _ASCII_STL) -> str:
    path = tmp_path / name
    path.write_text(text)
    return str(path)


def _select(monkeypatch, paths: list[str]) -> None:
    """Make the Load STL / OBJ dialog return *paths* without showing it."""
    monkeypatch.setattr(
        block_mesh_panel.QFileDialog,
        "getOpenFileNames",
        staticmethod(lambda *a, **k: (paths, "")),
    )


def _capture_warnings(monkeypatch) -> list[str]:
    """Collect the text of every QMessageBox.warning raised by the panel."""
    seen: list[str] = []
    monkeypatch.setattr(
        block_mesh_panel.QMessageBox,
        "warning",
        staticmethod(lambda _parent, _title, text, *a, **k: seen.append(text)),
    )
    return seen


def test_loads_every_selected_file(qapp, tmp_path, monkeypatch):
    _select(monkeypatch, [
        _write_stl(tmp_path, "a.stl"),
        _write_stl(tmp_path, "b.stl"),
    ])
    panel = BlockMeshPanel()
    panel._load_stl()
    assert len(panel._surfaces) == 2
    assert panel._clear_stl_act.isEnabled()


def test_unreadable_file_does_not_discard_the_others(qapp, tmp_path, monkeypatch):
    _select(monkeypatch, [
        _write_stl(tmp_path, "good.stl"),
        str(tmp_path / "missing.stl"),
    ])
    warnings = _capture_warnings(monkeypatch)
    panel = BlockMeshPanel()
    panel._load_stl()
    assert len(panel._surfaces) == 1
    assert panel._clear_stl_act.isEnabled()
    assert len(warnings) == 1
    assert "missing.stl" in warnings[0]


def test_cancelled_dialog_loads_nothing(qapp, monkeypatch):
    _select(monkeypatch, [])
    warnings = _capture_warnings(monkeypatch)
    panel = BlockMeshPanel()
    panel._load_stl()
    assert panel._surfaces == []
    assert not panel._clear_stl_act.isEnabled()
    assert warnings == []


# ── per-file rows ─────────────────────────────────────────────────────────────


def test_each_file_gets_its_own_row_and_colour(qapp, tmp_path, monkeypatch):
    _select(monkeypatch, [
        _write_stl(tmp_path, "a.stl"),
        _write_stl(tmp_path, "b.obj"),
    ])
    panel = BlockMeshPanel()
    panel._load_stl()

    assert [s.label for s in panel._surfaces] == ["a.stl", "b.obj"]
    assert [s.kind for s in panel._surfaces] == ["stl", "obj"]
    # One menu row per file, and each carries a distinct colour. The first is
    # the old uniform grey, so a single loaded file looks exactly as before.
    assert len(panel._loaded_surfaces.shape_actions) == 2
    assert panel._surfaces[0].color == "lightgray"
    assert panel._surfaces[0].color != panel._surfaces[1].color
    assert panel._unload_stl_menu.isEnabled()
    assert [a.text() for a in panel._unload_stl_menu.actions()] == ["a.stl", "b.obj"]


def test_unchecking_a_row_hides_only_that_surface(qapp, tmp_path, monkeypatch):
    _select(monkeypatch, [
        _write_stl(tmp_path, "a.stl"),
        _write_stl(tmp_path, "b.stl"),
    ])
    panel = BlockMeshPanel()
    panel._load_stl()

    panel._loaded_surfaces.shape_actions[0].setChecked(False)
    visible = panel._loaded_surfaces.visible_shapes()
    assert [s.label for s in visible] == ["b.stl"]
    # Hidden, not unloaded: the file keeps its row and stays in the list.
    assert len(panel._surfaces) == 2
    assert panel._clear_stl_act.isEnabled()

    panel._loaded_surfaces.master.setChecked(False)
    assert panel._loaded_surfaces.visible_shapes() == []


def test_unloading_one_surface_leaves_the_others_alone(qapp, tmp_path, monkeypatch):
    a = _write_stl(tmp_path, "a.stl")
    b = _write_stl(tmp_path, "b.stl")
    _select(monkeypatch, [a, b])
    panel = BlockMeshPanel()
    panel._load_stl()
    panel._loaded_surfaces.shape_actions[1].setChecked(False)

    panel._unload_surface(a)

    assert [s.label for s in panel._surfaces] == ["b.stl"]
    assert len(panel._loaded_surfaces.shape_actions) == 1
    # b.stl was hidden before the unload and must stay hidden after it.
    assert not panel._loaded_surfaces.shape_actions[0].isChecked()
    assert panel._loaded_surfaces.visible_shapes() == []

    panel._unload_surface(b)
    assert panel._surfaces == []
    assert panel._loaded_surfaces.shape_actions == []
    assert not panel._unload_stl_menu.isEnabled()
    assert not panel._clear_stl_act.isEnabled()


def test_reloading_a_loaded_path_refreshes_it_in_place(qapp, tmp_path, monkeypatch):
    a = _write_stl(tmp_path, "a.stl")
    b = _write_stl(tmp_path, "b.stl")
    _select(monkeypatch, [a, b])
    panel = BlockMeshPanel()
    panel._load_stl()
    panel._loaded_surfaces.shape_actions[0].setChecked(False)
    color = panel._surfaces[0].color

    _select(monkeypatch, [a])
    panel._load_stl()

    # Same file, so it is re-read into the existing entry rather than added as
    # a second row; its colour and its hidden state both survive.
    assert [s.label for s in panel._surfaces] == ["a.stl", "b.stl"]
    assert panel._surfaces[0].color == color
    assert not panel._loaded_surfaces.shape_actions[0].isChecked()


# ── rendering with no blockMeshDict loaded ────────────────────────────────────


class _SpyRenderer:
    """Stands in for BlockMeshRenderer, recording the surfaces each render got.

    Avoids creating a real QtInteractor, which needs a display; _render() only
    requires that the panel has some renderer attached.
    """

    def __init__(self) -> None:
        self.calls: list = []

    def render(self, _data, _settings, surfaces, *_args, **_kw) -> None:
        self.calls.append(surfaces)


def test_surface_alone_is_drawn_and_unloading_it_clears_the_scene(
    qapp, tmp_path, monkeypatch
):
    """A surface loaded with no blockMeshDict open used to draw nothing."""
    path = _write_stl(tmp_path, "a.stl")
    _select(monkeypatch, [path])
    panel = BlockMeshPanel()
    spy = _SpyRenderer()
    panel._renderer = spy

    panel._load_stl()
    assert len(spy.calls) == 1
    assert [s.label for s in spy.calls[0]] == ["a.stl"]

    # Unloading the last one must still render, to clear the stale actors.
    panel._unload_surface(path)
    assert len(spy.calls) == 2
    assert spy.calls[1] == []

    # Now the scene really is empty, so further renders are skipped.
    panel._render()
    assert len(spy.calls) == 2
