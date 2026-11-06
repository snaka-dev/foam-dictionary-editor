# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""MainWindow._current_text / _dirty_paths (ui/mixins/_model_ops.py).

The one answer to "what does this file say right now", shared by undo
snapshots, the 3-D viewer's include expansion and the Run Solver dialog.
"""
from __future__ import annotations

from foam.parser import OpenFoamParser


def test_precedence_editor_buffer_cache_disk(main_window, tmp_path):
    win = main_window
    path = tmp_path / "controlDict"
    path.write_text("application disk;\n")
    p = str(path)

    assert win._current_text(p) == "application disk;\n"
    assert win._current_text(p, fallback=False) is None

    win.state.parsed_roots[p] = OpenFoamParser("application cache;\n").parse()
    assert win._current_text(p) == "application cache;\n"

    win.state.file_buffers[p] = "application buffer;\n"
    assert win._current_text(p) == "application buffer;\n"
    assert win._current_text(p, fallback=False) == "application buffer;\n"

    # The open file is served from the editor, even over a stale buffer.
    win.state.current_file = p
    win.editor_panel.set_text("application editor;\n")
    assert win._current_text(p) == "application editor;\n"
    # A differently spelled path to the same file still matches.
    assert win._current_text(str(tmp_path) + "//controlDict") == "application editor;\n"


def test_missing_file_is_none(main_window, tmp_path):
    assert main_window._current_text(str(tmp_path / "nope")) is None


def test_dirty_paths(main_window, tmp_path):
    win = main_window
    a, b, ro, cur = (str(tmp_path / n) for n in ("a", "b", "ro", "cur"))
    win.state.file_dirty.update({a: True, b: False, ro: True})
    win.state.read_only_files = {ro}
    win.state.current_file = cur
    win.state.text_dirty = True
    assert sorted(win._dirty_paths()) == sorted([a, cur])
