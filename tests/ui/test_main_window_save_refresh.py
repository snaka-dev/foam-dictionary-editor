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


def _push_owner_mtime_into_past(tmp_path) -> None:
    """Stamp constant/polyMesh/owner's mtime safely into the past.

    The staleness check (services/case_loader.py) is a plain
    dict.mtime > owner.mtime comparison, read from disk at refresh time.
    A subsequent blockMeshDict write picks up whatever mtime the OS clock
    reports at that instant -- not something the test can dictate -- so the
    only deterministic way to guarantee "later" is to move the *reference*
    file's mtime comfortably backward, by more than any plausible
    filesystem mtime granularity/rounding (previously done by sleeping
    briefly before saving and hoping the wall clock had advanced far enough).
    """
    owner_path = tmp_path / "constant" / "polyMesh" / "owner"
    reference = os.stat(owner_path).st_mtime
    stamp = reference - 10
    os.utime(owner_path, (stamp, stamp))


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
        _push_owner_mtime_into_past(tmp_path)  # dict's imminent write must land later

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
        _push_owner_mtime_into_past(tmp_path)

        win.save_all_files()

        text = _mesh_indicator_text(win)
        assert text is not None
        assert "stale" in text


class TestVanishedCaseDirectory:
    """A reload must not blank the file list when the case dir is gone.

    ``list_case_files`` returns ``[]`` for a directory that is not there --
    every branch of it is guarded by ``is_file()``/``is_dir()``/``glob`` -- so
    a reload against a stale ``current_case_dir`` used to empty the file list
    with no error, no exception and no warning, making the case look as though
    it had lost every file it had. The case directory can go away without the
    app doing it: something renames or deletes it outside FoDE, and
    ``QFileSystemWatcher`` then fires ``directoryChanged`` (reporting a renamed
    directory by its *old* path, while silently following the inode), which the
    400 ms debounce turns into exactly this reload.
    """

    def test_reload_leaves_the_file_list_alone(self, main_window, tmp_path, monkeypatch):
        win = main_window
        case_dir = tmp_path / "case"
        (case_dir / "system").mkdir(parents=True)
        (case_dir / "system" / "controlDict").write_text("dummy v2;\n", encoding="utf-8")
        win._load_case_dir(str(case_dir))
        before = win.file_list_panel.file_paths()
        assert before, "fixture should have listed at least one file"

        os.rename(case_dir, tmp_path / "renamed_elsewhere")
        win._reload_file_list()

        assert win.file_list_panel.file_paths() == before

    def test_reload_warns_rather_than_failing_silently(self, main_window, tmp_path):
        win = main_window
        case_dir = tmp_path / "case"
        (case_dir / "system").mkdir(parents=True)
        win._load_case_dir(str(case_dir))

        os.rename(case_dir, tmp_path / "gone")
        win._reload_file_list()

        assert "no longer on disk" in win.statusBar().currentMessage()

    def test_buffers_survive_so_unsaved_work_is_recoverable(self, main_window, tmp_path):
        win = main_window
        case_dir = tmp_path / "case"
        (case_dir / "system").mkdir(parents=True)
        dict_path = case_dir / "system" / "controlDict"
        dict_path.write_text("dummy v2;\n", encoding="utf-8")
        win._load_case_dir(str(case_dir))
        win.load_selected_file(str(dict_path))
        win.editor_panel.set_text("edited but never saved")
        win._on_user_text_changed()

        os.rename(case_dir, tmp_path / "gone")
        win._reload_file_list()

        assert win.state.file_dirty.get(str(dict_path)) is True
        assert "edited but never saved" in win.editor_panel.editor.toPlainText()
