# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for drag-and-drop case opening in MainWindow."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QEvent, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QApplication

# ---------------------------------------------------------------------------
# QApplication fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])
    yield app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_window(qapp, tmp_path):
    """Stub MainWindow with just enough state for drag-drop methods."""
    from ui.main_window import MainWindow

    with patch.object(MainWindow, "_build_ui", lambda self: None):
        win = MainWindow.__new__(MainWindow)
        win.text_dirty = False
        win.current_case_dir = None
        win.current_file = None
        win.file_buffers = {}
        win.file_dirty = {}
        win._source_lines_valid = False
        win._syncing = False
        win._case_files_config = None
        win._parsed_roots = {}
        win._diff_case_dir = None
        win._diff_parsed_roots = {}
        return win


def _mime(urls: list[QUrl]) -> MagicMock:
    m = MagicMock()
    m.urls.return_value = urls
    return m


def _drag_enter(mime) -> MagicMock:
    ev = MagicMock(spec=QDragEnterEvent)
    ev.type.return_value = QEvent.DragEnter
    ev.mimeData.return_value = mime
    return ev


def _drop(mime) -> MagicMock:
    ev = MagicMock(spec=QDropEvent)
    ev.type.return_value = QEvent.Drop
    ev.mimeData.return_value = mime
    return ev


# ---------------------------------------------------------------------------
# dragEnterEvent — window-level propagation path
# ---------------------------------------------------------------------------

class TestDragEnterEvent:
    def test_accepts_directory(self, qapp, tmp_path):
        win = _make_window(qapp, tmp_path)
        ev = _drag_enter(_mime([QUrl.fromLocalFile(str(tmp_path))]))
        win.dragEnterEvent(ev)
        ev.acceptProposedAction.assert_called_once()

    def test_ignores_file(self, qapp, tmp_path):
        f = tmp_path / "U"
        f.write_text("x")
        win = _make_window(qapp, tmp_path)
        ev = _drag_enter(_mime([QUrl.fromLocalFile(str(f))]))
        win.dragEnterEvent(ev)
        ev.ignore.assert_called_once()

    def test_ignores_multiple_urls(self, qapp, tmp_path):
        d1, d2 = tmp_path / "a", tmp_path / "b"
        d1.mkdir(); d2.mkdir()
        win = _make_window(qapp, tmp_path)
        ev = _drag_enter(_mime([QUrl.fromLocalFile(str(d1)), QUrl.fromLocalFile(str(d2))]))
        win.dragEnterEvent(ev)
        ev.ignore.assert_called_once()


# ---------------------------------------------------------------------------
# dropEvent — window-level propagation path
# ---------------------------------------------------------------------------

class TestDropEvent:
    def test_loads_directory(self, qapp, tmp_path):
        win = _make_window(qapp, tmp_path)
        win._load_case_dir = MagicMock()
        win.dropEvent(_drop(_mime([QUrl.fromLocalFile(str(tmp_path))])))
        win._load_case_dir.assert_called_once_with(str(tmp_path))

    def test_ignores_file(self, qapp, tmp_path):
        f = tmp_path / "U"
        f.write_text("x")
        win = _make_window(qapp, tmp_path)
        win._load_case_dir = MagicMock()
        win.dropEvent(_drop(_mime([QUrl.fromLocalFile(str(f))])))
        win._load_case_dir.assert_not_called()

    def test_dirty_cancel_aborts_load(self, qapp, tmp_path):
        win = _make_window(qapp, tmp_path)
        win.text_dirty = True
        win._load_case_dir = MagicMock()
        with patch("PySide6.QtWidgets.QMessageBox.question", return_value=0x00400000):  # No
            win.dropEvent(_drop(_mime([QUrl.fromLocalFile(str(tmp_path))])))
        win._load_case_dir.assert_not_called()

    def test_dirty_confirm_proceeds(self, qapp, tmp_path):
        win = _make_window(qapp, tmp_path)
        win.text_dirty = True
        win._load_case_dir = MagicMock()
        with patch("PySide6.QtWidgets.QMessageBox.question", return_value=0x00004000):  # Yes
            win.dropEvent(_drop(_mime([QUrl.fromLocalFile(str(tmp_path))])))
        win._load_case_dir.assert_called_once_with(str(tmp_path))


# ---------------------------------------------------------------------------
# eventFilter — editor intercept path
# ---------------------------------------------------------------------------

class TestEventFilter:
    def test_accepts_directory_drag_enter(self, qapp, tmp_path):
        win = _make_window(qapp, tmp_path)
        ev = _drag_enter(_mime([QUrl.fromLocalFile(str(tmp_path))]))
        assert win.eventFilter(None, ev) is True
        ev.acceptProposedAction.assert_called_once()

    def test_passes_through_file_drag_enter(self, qapp, tmp_path):
        f = tmp_path / "U"
        f.write_text("x")
        win = _make_window(qapp, tmp_path)
        ev = _drag_enter(_mime([QUrl.fromLocalFile(str(f))]))
        assert win.eventFilter(None, ev) is False

    def test_loads_on_directory_drop(self, qapp, tmp_path):
        win = _make_window(qapp, tmp_path)
        win._load_case_dir = MagicMock()
        ev = _drop(_mime([QUrl.fromLocalFile(str(tmp_path))]))
        assert win.eventFilter(None, ev) is True
        win._load_case_dir.assert_called_once_with(str(tmp_path))

    def test_passes_through_file_drop(self, qapp, tmp_path):
        f = tmp_path / "U"
        f.write_text("x")
        win = _make_window(qapp, tmp_path)
        win._load_case_dir = MagicMock()
        ev = _drop(_mime([QUrl.fromLocalFile(str(f))]))
        assert win.eventFilter(None, ev) is False
        win._load_case_dir.assert_not_called()

    def test_dirty_cancel_aborts_load(self, qapp, tmp_path):
        win = _make_window(qapp, tmp_path)
        win.text_dirty = True
        win._load_case_dir = MagicMock()
        ev = _drop(_mime([QUrl.fromLocalFile(str(tmp_path))]))
        with patch("PySide6.QtWidgets.QMessageBox.question", return_value=0x00400000):  # No
            assert win.eventFilter(None, ev) is True
        win._load_case_dir.assert_not_called()

    def test_dirty_confirm_proceeds(self, qapp, tmp_path):
        win = _make_window(qapp, tmp_path)
        win.text_dirty = True
        win._load_case_dir = MagicMock()
        ev = _drop(_mime([QUrl.fromLocalFile(str(tmp_path))]))
        with patch("PySide6.QtWidgets.QMessageBox.question", return_value=0x00004000):  # Yes
            assert win.eventFilter(None, ev) is True
        win._load_case_dir.assert_called_once_with(str(tmp_path))
