# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""
Regression tests for save_file()/save_all_files() refreshing the File List
panel (ui/mixins/_file_ops.py).

QFileSystemWatcher.directoryChanged only fires on directory-entry add/remove,
not on in-place content rewrites, so the app's own writes (which rewrite an
existing file in place) are invisible to the case-dir watcher. save_file()
and save_all_files() must call _reload_file_list() themselves so disk-derived
indicators (e.g. the constant/polyMesh mesh indicator and its staleness
flag) update immediately, without requiring "Reload Case".

MainWindow is instantiated directly here (the first behavior-level test to
do so, as opposed to test_main_window_split.py's structural-only checks).
The shared `main_window` fixture (tests/conftest.py) disables the terminal
and blockmesh features for the duration of each test to keep instantiation
light and independent of VTK/QtWebEngine availability -- neither feature is
touched by the code path under test.
"""
from __future__ import annotations

import os
import time


def _mesh_indicator_text(win) -> str | None:
    for i in range(win.file_list_panel._list.count()):
        text = win.file_list_panel._list.item(i).text()
        if "constant/polyMesh" in text:
            return text
    return None


def _make_case_with_fresh_mesh(tmp_path):
    """A case with blockMeshDict and an already-generated, not-yet-stale mesh."""
    (tmp_path / "system").mkdir()
    (tmp_path / "constant").mkdir()
    dict_path = tmp_path / "system" / "blockMeshDict"
    dict_path.write_text("dummy v1", encoding="utf-8")

    poly_mesh = tmp_path / "constant" / "polyMesh"
    poly_mesh.mkdir()
    owner_path = poly_mesh / "owner"
    owner_path.write_text(
        'FoamFile\n{\n    note        "nPoints:1  nCells:1  nFaces:1  nInternalFaces:0";\n}\n',
        encoding="utf-8",
    )

    now = time.time()
    os.utime(dict_path, (now - 100, now - 100))
    os.utime(owner_path, (now, now))  # mesh newer than dict -> starts fresh

    return str(dict_path)


class TestSaveTriggersFileListRefresh:
    def test_edit_without_save_does_not_flip_stale(self, main_window, tmp_path):
        """Editing in memory only must not change the on-disk-derived indicator."""
        win = main_window
        dict_path = _make_case_with_fresh_mesh(tmp_path)
        win._load_case_dir(str(tmp_path))

        assert "stale" not in _mesh_indicator_text(win)

        win.load_selected_file(dict_path)
        win.editor_panel.set_text("dummy v2 edited")
        win._on_user_text_changed()

        assert "stale" not in _mesh_indicator_text(win)

    def test_save_file_flips_indicator_to_stale_without_reload_case(self, main_window, tmp_path):
        """save_file() must refresh the file list so disk-derived indicators
        update immediately, without the user needing to Reload Case."""
        win = main_window
        dict_path = _make_case_with_fresh_mesh(tmp_path)
        win._load_case_dir(str(tmp_path))

        win.load_selected_file(dict_path)
        win.editor_panel.set_text("dummy v2 edited")
        win._on_user_text_changed()
        time.sleep(0.05)  # ensure a distinct, later mtime than the owner file

        win.save_file()

        text = _mesh_indicator_text(win)
        assert text is not None
        assert "stale" in text

    def test_save_all_files_also_refreshes_file_list(self, main_window, tmp_path):
        """save_all_files() must likewise refresh the file list after writing."""
        win = main_window
        dict_path = _make_case_with_fresh_mesh(tmp_path)
        win._load_case_dir(str(tmp_path))

        win.load_selected_file(dict_path)
        win.editor_panel.set_text("dummy v2 edited")
        win._on_user_text_changed()
        time.sleep(0.05)

        win.save_all_files()

        text = _mesh_indicator_text(win)
        assert text is not None
        assert "stale" in text
