# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.case_files_config import CaseFilesConfig


class TestCaseFilesConfigLoad:
    def test_no_config_file_gives_empty_list(self, tmp_path):
        """When no .foam-editor-files.json exists, extra_files is empty"""
        cfg = CaseFilesConfig(str(tmp_path))
        assert cfg.get_extra_files() == []

    def test_loads_existing_config(self, tmp_path):
        """Extra files listed in the config file are returned by get_extra_files"""
        data = {"extra_files": ["system/myDict", "constant/myProps"]}
        (tmp_path / ".foam-editor-files.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
        cfg = CaseFilesConfig(str(tmp_path))
        assert cfg.get_extra_files() == ["system/myDict", "constant/myProps"]

    def test_malformed_json_returns_empty(self, tmp_path):
        """Malformed JSON in the config file results in an empty list"""
        (tmp_path / ".foam-editor-files.json").write_text("not json", encoding="utf-8")
        cfg = CaseFilesConfig(str(tmp_path))
        assert cfg.get_extra_files() == []

    def test_missing_extra_files_key_returns_empty(self, tmp_path):
        """Config file without 'extra_files' key returns empty list"""
        (tmp_path / ".foam-editor-files.json").write_text("{}", encoding="utf-8")
        cfg = CaseFilesConfig(str(tmp_path))
        assert cfg.get_extra_files() == []


class TestCaseFilesConfigSave:
    def test_save_creates_file(self, tmp_path):
        """save() creates the config file in the case directory"""
        cfg = CaseFilesConfig(str(tmp_path))
        cfg.add_file("system/myDict")
        cfg.save()
        assert (tmp_path / ".foam-editor-files.json").exists()

    def test_save_and_reload(self, tmp_path):
        """Data saved by save() is loaded correctly by a new CaseFilesConfig instance"""
        cfg = CaseFilesConfig(str(tmp_path))
        cfg.add_file("system/dictA")
        cfg.add_file("constant/dictB")
        cfg.save()

        cfg2 = CaseFilesConfig(str(tmp_path))
        assert "system/dictA" in cfg2.get_extra_files()
        assert "constant/dictB" in cfg2.get_extra_files()


class TestCaseFilesConfigAddRemove:
    def test_add_file(self, tmp_path):
        """add_file appends a new relative path"""
        cfg = CaseFilesConfig(str(tmp_path))
        cfg.add_file("system/myDict")
        assert "system/myDict" in cfg.get_extra_files()

    def test_add_file_no_duplicate(self, tmp_path):
        """Adding the same path twice does not create duplicates"""
        cfg = CaseFilesConfig(str(tmp_path))
        cfg.add_file("system/myDict")
        cfg.add_file("system/myDict")
        assert cfg.get_extra_files().count("system/myDict") == 1

    def test_remove_file(self, tmp_path):
        """remove_file removes the specified path"""
        cfg = CaseFilesConfig(str(tmp_path))
        cfg.add_file("system/myDict")
        cfg.remove_file("system/myDict")
        assert "system/myDict" not in cfg.get_extra_files()

    def test_remove_nonexistent_file_is_silent(self, tmp_path):
        """Removing a path that was never added does not raise"""
        cfg = CaseFilesConfig(str(tmp_path))
        cfg.remove_file("system/doesNotExist")  # must not raise

    def test_get_extra_files_returns_copy(self, tmp_path):
        """Modifying the returned list does not affect the internal state"""
        cfg = CaseFilesConfig(str(tmp_path))
        cfg.add_file("system/myDict")
        result = cfg.get_extra_files()
        result.clear()
        assert cfg.get_extra_files() == ["system/myDict"]


class TestCaseFilesConfigReset:
    def test_reset_clears_extra_files(self, tmp_path):
        """reset() empties the extra files list"""
        cfg = CaseFilesConfig(str(tmp_path))
        cfg.add_file("system/myDict")
        cfg.reset()
        assert cfg.get_extra_files() == []

    def test_delete_config_file_removes_file(self, tmp_path):
        """delete_config_file() removes the JSON file from disk"""
        cfg = CaseFilesConfig(str(tmp_path))
        cfg.add_file("system/myDict")
        cfg.save()
        assert (tmp_path / ".foam-editor-files.json").exists()
        cfg.delete_config_file()
        assert not (tmp_path / ".foam-editor-files.json").exists()

    def test_delete_config_file_clears_list(self, tmp_path):
        """delete_config_file() also clears the in-memory list"""
        cfg = CaseFilesConfig(str(tmp_path))
        cfg.add_file("system/myDict")
        cfg.save()
        cfg.delete_config_file()
        assert cfg.get_extra_files() == []

    def test_delete_when_no_file_is_silent(self, tmp_path):
        """delete_config_file() does not raise when the config file does not exist"""
        cfg = CaseFilesConfig(str(tmp_path))
        cfg.delete_config_file()  # must not raise


class TestCaseFilesConfigProperties:
    def test_config_filename(self, tmp_path):
        """config_filename returns the expected file name"""
        cfg = CaseFilesConfig(str(tmp_path))
        assert cfg.config_filename == ".foam-editor-files.json"

    def test_exists_false_when_no_file(self, tmp_path):
        """exists is False when no config file has been saved"""
        cfg = CaseFilesConfig(str(tmp_path))
        assert cfg.exists is False

    def test_exists_true_after_save(self, tmp_path):
        """exists is True after save()"""
        cfg = CaseFilesConfig(str(tmp_path))
        cfg.save()
        assert cfg.exists is True
