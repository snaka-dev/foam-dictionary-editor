# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Cover what happens to app_config.json after **Reset All Settings**.

Deleting the file is only half a reset: the application keeps running, and
``MainWindow.closeEvent`` used to capture the session layout and window size on
the way out — recreating the file and, to the user, restoring exactly the
settings they had just asked to be rid of. These tests pin the close down to
writing nothing once the config file has been deleted, and to writing as before
when it has not.
"""
from __future__ import annotations

import json

from PySide6.QtGui import QCloseEvent

# ``temp_config`` and ``config_path`` come from tests/conftest.py, which points
# every test at a throwaway config file — these tests close a window, which
# saves, and that must not land in the repository's own app_config.json.


class TestCloseAfterReset:
    def test_the_close_does_not_recreate_the_deleted_file(
        self, main_window, temp_config, config_path
    ):
        temp_config.set_window_size(1024, 768)
        temp_config.save()
        assert config_path.exists()

        temp_config.delete_config_file()
        main_window.closeEvent(QCloseEvent())

        assert not config_path.exists()

    def test_the_close_stores_no_session(self, main_window, temp_config):
        temp_config.delete_config_file()
        main_window.closeEvent(QCloseEvent())

        assert temp_config.get_session_state() is None

    def test_the_close_does_not_recapture_the_window_size(self, main_window, temp_config):
        temp_config.delete_config_file()
        main_window.closeEvent(QCloseEvent())

        assert temp_config.get_window_size() is None

    def test_an_explicit_save_afterwards_is_still_honoured(
        self, main_window, temp_config, config_path
    ):
        """Only the implicit end-of-run capture is suppressed, not the user's own
        choices — picking a theme after the reset still persists."""
        temp_config.delete_config_file()
        temp_config.set_theme("dark")
        temp_config.save()
        main_window.closeEvent(QCloseEvent())

        data = json.loads(config_path.read_text(encoding="utf-8"))
        assert data["theme"] == "dark"
        assert data.get("window_size") is None
        assert "sessions" not in data


class TestCloseWithoutReset:
    """The ordinary path must be untouched by the guard above."""

    def test_the_close_writes_the_config_file(self, main_window, temp_config, config_path):
        main_window.closeEvent(QCloseEvent())
        assert config_path.exists()

    def test_the_close_captures_the_window_size(self, main_window, temp_config):
        main_window.resize(900, 700)
        main_window.closeEvent(QCloseEvent())
        assert temp_config.get_window_size() is not None

    def test_the_close_captures_the_session(self, main_window, temp_config):
        main_window.closeEvent(QCloseEvent())
        assert temp_config.get_session_state() is not None
