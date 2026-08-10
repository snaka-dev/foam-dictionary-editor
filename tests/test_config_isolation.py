# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""The test run must not be able to write the repository's app_config.json.

A test that builds a window can save one on the way out, and a test that turns
a feature flag off to keep itself light would otherwise leave it off for the
developer whose checkout it ran in. ``tests/conftest.py``'s autouse
``temp_config`` fixture is what prevents that; these are the tests that notice
if it stops being applied.
"""
from __future__ import annotations

import os
from pathlib import Path

from app_config import get_app_config
from app_config.app_config_manager import CONFIG_PATH_ENV, AppConfigManager

REPO_CONFIG = Path(__file__).resolve().parents[1] / "app_config.json"


class TestTheSingletonIsRedirected:
    def test_it_points_at_the_throwaway_file(self, config_path):
        assert get_app_config()._config_path == config_path

    def test_it_does_not_point_at_the_repository_config(self):
        assert get_app_config()._config_path != REPO_CONFIG

    def test_saving_writes_the_throwaway_file(self, config_path):
        get_app_config().set_window_size(1024, 768)
        get_app_config().save()
        assert config_path.exists()


class TestTheEnvironmentIsRedirected:
    """The other half: code that builds its own manager, not the singleton."""

    def test_the_variable_names_the_throwaway_file(self, config_path):
        assert os.environ[CONFIG_PATH_ENV] == str(config_path)

    def test_a_manager_built_from_scratch_lands_there(self, config_path):
        assert AppConfigManager()._config_path == config_path
