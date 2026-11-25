# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Plot Results' read-only data-file window: what it shows of a large file."""
from __future__ import annotations

import gzip

from ui.dialogs.data_file_viewer import DataFileViewer, read_for_view


def _rows(n: int) -> str:
    return "# Time p\n" + "".join(f"{i} {i * 0.5}\n" for i in range(n))


def test_a_small_file_is_shown_whole(tmp_path):
    path = tmp_path / "p"
    path.write_text(_rows(50))
    text, size, cut = read_for_view(str(path))
    assert text == _rows(50) and size == len(_rows(50)) and not cut


def test_a_large_file_shows_its_head_and_tail(tmp_path):
    path = tmp_path / "p"
    path.write_text(_rows(10000))
    text, size, cut = read_for_view(str(path), full_limit=10_000, head_lines=3, tail_bytes=100)
    assert cut and size == len(_rows(10000))
    lines = text.splitlines()
    assert lines[:3] == ["# Time p", "0 0.0", "1 0.5"]
    assert "MB not shown" in text
    # The tail is whole lines and ends with the last row.
    assert lines[-1] == "9999 4999.5"
    tail = text.split("not shown …\n\n", 1)[1]
    assert 100 <= len(tail) < 120 and tail.splitlines()[0].count(" ") == 1


def test_a_gzipped_file_is_read_through(tmp_path):
    path = tmp_path / "p.dat.gz"
    with gzip.open(path, "wt") as fh:
        fh.write(_rows(5))
    assert read_for_view(str(path))[0] == _rows(5)


def test_the_window_says_when_it_shows_part(tmp_path, monkeypatch, destroy_widget):
    path = tmp_path / "p"
    path.write_text(_rows(10000))
    monkeypatch.setattr("ui.dialogs.data_file_viewer.FULL_LIMIT", 10_000)
    viewer = DataFileViewer(str(path))
    try:
        assert viewer.text.isReadOnly()
        assert not viewer.note.isHidden() and "too large" in viewer.note.text()
        path.write_text(_rows(5))
        viewer.reload()
        assert viewer.note.isHidden() and viewer.text.toPlainText() == _rows(5)
        path.unlink()
        viewer.reload()
        assert "Cannot read" in viewer.note.text()
    finally:
        destroy_widget(viewer)
