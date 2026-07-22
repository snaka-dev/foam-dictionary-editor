# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for services/foam_env.py."""
from __future__ import annotations

import pytest

from services.foam_env import foam_env_dirs


@pytest.fixture
def install(tmp_path):
    """A fake OpenFOAM installation with all standard subdirectories."""
    root = tmp_path / "OpenFOAM-12"
    for sub in ("tutorials", "etc", "src", "applications"):
        (root / sub).mkdir(parents=True)
    return root


class TestAllVarsSet:
    def test_explicit_vars_win_over_fallbacks(self, tmp_path, install):
        other = tmp_path / "other"
        for sub in ("tut", "etc2", "src2", "apps2"):
            (other / sub).mkdir(parents=True)
        env = {
            "WM_PROJECT_DIR": str(install),
            "FOAM_TUTORIALS": str(other / "tut"),
            "FOAM_ETC": str(other / "etc2"),
            "FOAM_SRC": str(other / "src2"),
            "FOAM_APP": str(other / "apps2"),
            "WM_PROJECT_VERSION": "12",
        }
        dirs = foam_env_dirs(env)
        assert dirs.project_dir == install
        assert dirs.tutorials_dir == other / "tut"
        assert dirs.etc_dir == other / "etc2"
        assert dirs.src_dir == other / "src2"
        assert dirs.apps_dir == other / "apps2"
        assert dirs.version == "12"


class TestProjectDirOnly:
    def test_subdirs_fall_back_to_project_dir(self, install):
        dirs = foam_env_dirs({"WM_PROJECT_DIR": str(install)})
        assert dirs.project_dir == install
        assert dirs.tutorials_dir == install / "tutorials"
        assert dirs.etc_dir == install / "etc"
        assert dirs.src_dir == install / "src"
        assert dirs.apps_dir == install / "applications"
        assert dirs.version == "OpenFOAM-12"

    def test_missing_subdir_stays_none(self, tmp_path):
        root = tmp_path / "OpenFOAM-12"
        (root / "tutorials").mkdir(parents=True)
        dirs = foam_env_dirs({"WM_PROJECT_DIR": str(root)})
        assert dirs.tutorials_dir == root / "tutorials"
        assert dirs.etc_dir is None
        assert dirs.src_dir is None
        assert dirs.apps_dir is None

    def test_invalid_project_dir_ignored(self, tmp_path):
        dirs = foam_env_dirs({"WM_PROJECT_DIR": str(tmp_path / "missing")})
        assert dirs.project_dir is None
        assert dirs.tutorials_dir is None
        assert dirs.version is None


class TestSingleVar:
    def test_foam_etc_honoured_without_project_dir(self, tmp_path):
        etc = tmp_path / "etc"
        etc.mkdir()
        dirs = foam_env_dirs({"FOAM_ETC": str(etc)})
        assert dirs.etc_dir == etc
        assert dirs.project_dir is None
        assert dirs.src_dir is None

    def test_invalid_explicit_var_falls_back_to_project_dir(self, tmp_path, install):
        env = {
            "WM_PROJECT_DIR": str(install),
            "FOAM_TUTORIALS": str(tmp_path / "missing"),
        }
        assert foam_env_dirs(env).tutorials_dir == install / "tutorials"


class TestNothingSet:
    def test_all_none(self):
        dirs = foam_env_dirs({})
        assert dirs.project_dir is None
        assert dirs.tutorials_dir is None
        assert dirs.etc_dir is None
        assert dirs.src_dir is None
        assert dirs.apps_dir is None
        assert dirs.version is None

    def test_blank_values_treated_as_unset(self):
        dirs = foam_env_dirs({"WM_PROJECT_DIR": "  ", "FOAM_ETC": ""})
        assert dirs.project_dir is None
        assert dirs.etc_dir is None
