# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Starting the 3-D view: re-entry through showEvent, and a failure that costs the view only.

pyvistaqt 0.13 builds QtInteractor on QOpenGLWidget. The first one added to a
window already on screen makes Qt recreate the window's native surface, which
hides and re-shows it: showEvent, and so init_plotter, ran again inside the
constructor, and the nested QtInteractor failed with SystemError. Session
restore selecting a saved BlockMesh tab hit this before the event loop ran,
and FoDE never opened. These stand-ins replay both halves without OpenGL.
"""
from __future__ import annotations

import pytest
from PySide6.QtWidgets import QLabel, QWidget

from ui.panels import block_mesh_panel
from ui.panels.block_mesh_panel import BlockMeshPanel

pytestmark = pytest.mark.skipif(
    not block_mesh_panel._PYVISTA_OK, reason="pyvista/pyvistaqt not installed"
)


class _ReenteringInteractor(QWidget):
    """Re-enters init_plotter from its constructor, as the window recreation does."""

    built: list[_ReenteringInteractor] = []

    def __init__(self, parent: BlockMeshPanel) -> None:
        super().__init__(parent)
        if len(self.built) > 3:
            raise AssertionError("init_plotter recursed without a guard")
        self.built.append(self)
        parent.init_plotter()

    def set_background(self, *_a, **_k) -> None: ...
    def add_axes(self, *_a, **_k) -> None: ...


def test_reentry_during_construction_builds_one_interactor(
    qapp, destroy_widget, monkeypatch  # noqa: ARG001
):
    _ReenteringInteractor.built = []
    monkeypatch.setattr(block_mesh_panel, "QtInteractor", _ReenteringInteractor)
    monkeypatch.setattr(block_mesh_panel, "BlockMeshRenderer", lambda plotter: object())
    panel = BlockMeshPanel()
    try:
        panel.init_plotter()
        assert len(_ReenteringInteractor.built) == 1
        assert panel._plotter is _ReenteringInteractor.built[0]
        assert not panel._plotter_starting
    finally:
        panel._plotter = None   # a stand-in owns no render window for shutdown() to close
        destroy_widget(panel)


def test_a_failing_interactor_is_reported_in_the_panel(qapp, destroy_widget, monkeypatch):  # noqa: ARG001
    calls = []

    def failing(parent):
        calls.append(parent)
        raise SystemError("returned NULL without setting an exception")

    monkeypatch.setattr(block_mesh_panel, "QtInteractor", failing)
    panel = BlockMeshPanel()
    try:
        panel.init_plotter()          # must not raise
        assert panel._plotter is None
        said = [w.text() for w in panel.findChildren(QLabel) if "could not start" in w.text()]
        assert len(said) == 1 and "SystemError" in said[0]
        assert panel.save_image_action is not None
        assert not panel.save_image_action.isEnabled()
        panel.init_plotter()          # not retried, and no second message
        assert len(calls) == 1
        assert len([w for w in panel.findChildren(QLabel) if "could not start" in w.text()]) == 1
    finally:
        destroy_widget(panel)
