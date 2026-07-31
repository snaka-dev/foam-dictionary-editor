# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Persist the window's layout between runs, so FoDE reopens where it was left.

The state model is entirely ``ui/window_state.py``'s; this module is only the
two ends of the wire. ``save_session`` is called from ``MainWindow.closeEvent``
and ``restore_session`` from ``main.py`` once the window is on screen. What
travels is a ``WindowState``: geometry, splitter sizes, the active tabs, the
terminal's mode, the case directory and the files open in it, the selected tree
row, and the 3-D panel's toggles and camera.

Three things are worth knowing before changing this.

**A restore may never be the reason the application fails to open.** The blob
comes off disk and describes a window that existed some other day, under some
other version. Everything here goes through the lenient half of
``ui/window_state.py`` — ``load_saved_state`` and ``apply_window_state(...,
strict=False)`` — so a case that has been renamed, a file that has been deleted
or a field written by a newer version costs the user that one part of the
layout and nothing else. What was skipped is reported in the status bar, not in
a dialog: nobody wants to dismiss a modal before they can start work.

**Layouts are stored per feature set**, keyed by ``AppConfigManager.session_key``.
A window captured with a terminal in it describes tabs and splitters that a
``--variant no-terminal`` run does not have, so each variant keeps its own and
they never overwrite each other.

**The camera has to be applied twice.** Every ``BlockMeshRenderer.render`` ends
in ``reset_camera()``, and the renders triggered by loading the case land after
this function returns — so the pinned camera is re-applied on a timer once the
scene has settled, which is the same dance ``tools/capture_screenshots.py``
does after its settle delay.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QEventLoop, QTimer

from app_config import get_app_config
from i18n import tr
from ui.window_state import (
    apply_block_mesh_view,
    apply_window_state,
    capture_window_state,
    load_saved_state,
)

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication

    from ui.main_window import MainWindow

# How long to spin the event loop at ``apply_window_state``'s settle points.
# Shorter than the screenshot tool's 600 ms because this one is in front of a
# person waiting for the window: it is only reached when the restore actually
# switches the terminal's mode or side-by-side, and those complete well inside
# it. Getting it wrong costs a mis-sized pane, not a broken window.
_SETTLE_MS = 250

# When to re-apply the 3-D camera. Must outlast the deferred VTK
# re-initialisation (300 ms after a terminal-mode switch) and the render that
# follows the case load, both of which end in reset_camera().
_CAMERA_MS = 1200

_STATUS_MS = 8000


def save_session(window: MainWindow) -> None:
    """Store *window*'s layout for the next run. Does not write to disk.

    Follows ``AppConfigManager``'s house rule that setters do not auto-save;
    ``MainWindow.closeEvent`` already calls ``cfg.save()`` right after this.
    Must run *before* the panels are torn down — a shut-down BlockMesh panel has
    no camera left to read.
    """
    cfg = get_app_config()
    if not cfg.get_restore_session():
        return
    try:
        cfg.set_session_state(capture_window_state(window).to_dict())
    except Exception as e:
        # Never worth blocking a close over. The previous session stays stored.
        print(f"Warning: Failed to capture the window layout: {e}")


def restore_session(app: QApplication, window: MainWindow) -> bool:
    """Reapply the stored layout to a freshly shown *window*.

    Returns whether a state was found and applied, so the caller can tell a
    restored launch from a default one — ``main.py`` uses it for nothing yet,
    but the alternative is a bool-less function whose one interesting fact is
    unobservable.
    """
    cfg = get_app_config()
    if not cfg.get_restore_session():
        return False
    state = load_saved_state(cfg.get_session_state())
    if state is None:
        return False

    notes = apply_window_state(
        window, state, settle=lambda: _settle(app, _SETTLE_MS), strict=False
    )

    if state.block_mesh is not None and state.block_mesh.camera is not None:
        QTimer.singleShot(_CAMERA_MS, lambda: apply_block_mesh_view(window, state))

    if notes:
        window.statusBar().showMessage(
            tr("Session restored, except: {details}").format(details="; ".join(notes)),
            _STATUS_MS,
        )
    return True


def _settle(app: QApplication, milliseconds: int) -> None:
    """Run the event loop for a fixed time so deferred work completes."""
    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    loop.exec()
    app.processEvents()
