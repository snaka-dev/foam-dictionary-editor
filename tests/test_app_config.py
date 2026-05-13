# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
import json
import pytest
from pathlib import Path
from app_config.app_config_manager import AppConfigManager


@pytest.fixture
def config_path(tmp_path):
    return tmp_path / "app_config.json"


@pytest.fixture
def manager(config_path):
    return AppConfigManager(config_path=str(config_path))


class TestInit:
    def test_no_config_file_window_size_is_none(self, manager):
        assert manager.get_window_size() is None

    def test_no_config_file_default_case_dir_is_none(self, manager):
        assert manager.get_default_case_dir() is None

    def test_load_existing_config_window_size(self, config_path):
        data = {"window_size": [1200, 800], "default_case_dir": None}
        config_path.write_text(json.dumps(data), encoding="utf-8")
        mgr = AppConfigManager(config_path=str(config_path))
        assert mgr.get_window_size() == [1200, 800]

    def test_load_existing_config_default_case_dir(self, config_path, tmp_path):
        case_dir = str(tmp_path / "myCase")
        data = {"window_size": None, "default_case_dir": case_dir}
        config_path.write_text(json.dumps(data), encoding="utf-8")
        mgr = AppConfigManager(config_path=str(config_path))
        assert mgr.get_default_case_dir() == case_dir

    def test_load_broken_json_does_not_raise(self, config_path):
        config_path.write_text("{ broken json", encoding="utf-8")
        mgr = AppConfigManager(config_path=str(config_path))
        assert mgr.get_window_size() is None
        assert mgr.get_default_case_dir() is None

    def test_load_partial_config_missing_window_size(self, config_path, tmp_path):
        data = {"default_case_dir": str(tmp_path)}
        config_path.write_text(json.dumps(data), encoding="utf-8")
        mgr = AppConfigManager(config_path=str(config_path))
        assert mgr.get_window_size() is None

    def test_load_partial_config_missing_default_case_dir(self, config_path):
        data = {"window_size": [800, 600]}
        config_path.write_text(json.dumps(data), encoding="utf-8")
        mgr = AppConfigManager(config_path=str(config_path))
        assert mgr.get_default_case_dir() is None


class TestWindowSize:
    def test_set_window_size(self, manager):
        manager.set_window_size(1280, 720)
        assert manager.get_window_size() == [1280, 720]

    def test_set_window_size_overwrite(self, manager):
        manager.set_window_size(800, 600)
        manager.set_window_size(1920, 1080)
        assert manager.get_window_size() == [1920, 1080]

    def test_set_window_size_zero_raises(self, manager):
        with pytest.raises((ValueError, AssertionError)):
            manager.set_window_size(0, 600)

    def test_set_window_size_negative_raises(self, manager):
        with pytest.raises((ValueError, AssertionError)):
            manager.set_window_size(800, -100)

    def test_get_window_size_returns_list_or_tuple(self, manager):
        manager.set_window_size(1024, 768)
        result = manager.get_window_size()
        assert isinstance(result, (list, tuple))
        assert len(result) == 2

    def test_window_size_width_and_height(self, manager):
        manager.set_window_size(1366, 768)
        w, h = manager.get_window_size()
        assert w == 1366
        assert h == 768


class TestDefaultCaseDir:
    def test_set_default_case_dir(self, manager, tmp_path):
        case_dir = str(tmp_path / "case1")
        (tmp_path / "case1").mkdir()
        manager.set_default_case_dir(case_dir)
        assert manager.get_default_case_dir() == case_dir

    def test_set_default_case_dir_overwrite(self, manager, tmp_path):
        d1 = tmp_path / "case1"
        d2 = tmp_path / "case2"
        d1.mkdir()
        d2.mkdir()
        manager.set_default_case_dir(str(d1))
        manager.set_default_case_dir(str(d2))
        assert manager.get_default_case_dir() == str(d2)

    def test_set_default_case_dir_nonexistent_does_not_raise(self, manager, tmp_path):
        path = str(tmp_path / "nonexistent_dir")
        manager.set_default_case_dir(path)
        assert manager.get_default_case_dir() == path

    def test_set_default_case_dir_none(self, manager, tmp_path):
        manager.set_default_case_dir(str(tmp_path))
        manager.set_default_case_dir(None)
        assert manager.get_default_case_dir() is None


class TestCaseLibraryDirs:
    def test_initial_empty_user_dirs_when_no_env(self, config_path, monkeypatch):
        monkeypatch.delenv("FOAM_TUTORIALS", raising=False)
        mgr = AppConfigManager(config_path=str(config_path))
        assert mgr.get_user_library_dirs() == []
        assert mgr.get_case_library_dirs() == []

    def test_foam_tutorials_always_included_when_env_set(self, config_path, tmp_path, monkeypatch):
        foam_dir = tmp_path / "tutorials"
        foam_dir.mkdir()
        monkeypatch.setenv("FOAM_TUTORIALS", str(foam_dir))
        mgr = AppConfigManager(config_path=str(config_path))
        assert str(foam_dir) in mgr.get_case_library_dirs()

    def test_foam_tutorials_included_even_when_saved_config_exists(self, config_path, tmp_path, monkeypatch):
        foam_dir = tmp_path / "tutorials"
        foam_dir.mkdir()
        monkeypatch.setenv("FOAM_TUTORIALS", str(foam_dir))
        data = {"case_library_dirs": []}
        config_path.write_text(json.dumps(data), encoding="utf-8")
        mgr = AppConfigManager(config_path=str(config_path))
        assert str(foam_dir) in mgr.get_case_library_dirs()

    def test_foam_tutorials_not_in_user_dirs(self, config_path, tmp_path, monkeypatch):
        foam_dir = tmp_path / "tutorials"
        foam_dir.mkdir()
        monkeypatch.setenv("FOAM_TUTORIALS", str(foam_dir))
        mgr = AppConfigManager(config_path=str(config_path))
        assert str(foam_dir) not in mgr.get_user_library_dirs()

    def test_foam_tutorials_not_duplicated_when_also_user_added(self, config_path, tmp_path, monkeypatch):
        foam_dir = tmp_path / "tutorials"
        foam_dir.mkdir()
        monkeypatch.setenv("FOAM_TUTORIALS", str(foam_dir))
        mgr = AppConfigManager(config_path=str(config_path))
        mgr.add_case_library_dir(str(foam_dir))
        assert mgr.get_case_library_dirs().count(str(foam_dir)) == 1

    def test_no_foam_tutorials_when_dir_missing(self, config_path, monkeypatch):
        monkeypatch.setenv("FOAM_TUTORIALS", "/nonexistent/path")
        mgr = AppConfigManager(config_path=str(config_path))
        assert "/nonexistent/path" not in mgr.get_case_library_dirs()

    def test_foam_tutorials_at_front_of_list(self, config_path, tmp_path, monkeypatch):
        foam_dir = tmp_path / "tutorials"
        foam_dir.mkdir()
        monkeypatch.setenv("FOAM_TUTORIALS", str(foam_dir))
        mgr = AppConfigManager(config_path=str(config_path))
        mgr.add_case_library_dir(str(tmp_path / "user_lib"))
        dirs = mgr.get_case_library_dirs()
        assert dirs[0] == str(foam_dir)

    def test_add_case_library_dir(self, manager, tmp_path, monkeypatch):
        monkeypatch.delenv("FOAM_TUTORIALS", raising=False)
        d = str(tmp_path / "lib")
        manager.add_case_library_dir(d)
        assert d in manager.get_case_library_dirs()

    def test_add_case_library_dir_ignores_duplicates(self, manager, tmp_path, monkeypatch):
        monkeypatch.delenv("FOAM_TUTORIALS", raising=False)
        d = str(tmp_path / "lib")
        manager.add_case_library_dir(d)
        manager.add_case_library_dir(d)
        assert manager.get_case_library_dirs().count(d) == 1

    def test_remove_case_library_dir(self, manager, tmp_path, monkeypatch):
        monkeypatch.delenv("FOAM_TUTORIALS", raising=False)
        d = str(tmp_path / "lib")
        manager.add_case_library_dir(d)
        manager.remove_case_library_dir(d)
        assert d not in manager.get_case_library_dirs()

    def test_remove_nonexistent_does_not_raise(self, manager):
        manager.remove_case_library_dir("/nonexistent/path")

    def test_get_case_library_dirs_returns_copy(self, manager, tmp_path, monkeypatch):
        monkeypatch.delenv("FOAM_TUTORIALS", raising=False)
        d = str(tmp_path / "lib")
        manager.add_case_library_dir(d)
        result = manager.get_case_library_dirs()
        result.append("/injected")
        assert "/injected" not in manager.get_case_library_dirs()

    def test_foam_tutorials_dir_static_method_returns_path_when_valid(self, tmp_path, monkeypatch):
        foam_dir = tmp_path / "tutorials"
        foam_dir.mkdir()
        monkeypatch.setenv("FOAM_TUTORIALS", str(foam_dir))
        assert AppConfigManager.foam_tutorials_dir() == str(foam_dir)

    def test_foam_tutorials_dir_static_method_returns_none_when_unset(self, monkeypatch):
        monkeypatch.delenv("FOAM_TUTORIALS", raising=False)
        assert AppConfigManager.foam_tutorials_dir() is None

    def test_foam_tutorials_dir_static_method_returns_none_when_dir_missing(self, monkeypatch):
        monkeypatch.setenv("FOAM_TUTORIALS", "/nonexistent/path")
        assert AppConfigManager.foam_tutorials_dir() is None


class TestSave:
    def test_save_creates_file(self, manager, config_path):
        manager.set_window_size(800, 600)
        manager.save()
        assert config_path.exists()

    def test_save_content_is_valid_json(self, manager, config_path):
        manager.set_window_size(800, 600)
        manager.save()
        content = json.loads(config_path.read_text(encoding="utf-8"))
        assert isinstance(content, dict)

    def test_save_window_size_persisted(self, manager, config_path):
        manager.set_window_size(1440, 900)
        manager.save()
        content = json.loads(config_path.read_text(encoding="utf-8"))
        assert content["window_size"] == [1440, 900]

    def test_save_default_case_dir_persisted(self, manager, config_path, tmp_path):
        case_dir = str(tmp_path / "myCase")
        manager.set_default_case_dir(case_dir)
        manager.save()
        content = json.loads(config_path.read_text(encoding="utf-8"))
        assert content["default_case_dir"] == case_dir

    def test_save_case_library_dirs_persisted(self, manager, config_path, tmp_path):
        d = str(tmp_path / "lib")
        manager.add_case_library_dir(d)
        manager.save()
        content = json.loads(config_path.read_text(encoding="utf-8"))
        assert d in content["case_library_dirs"]

    def test_save_and_reload_window_size(self, config_path):
        mgr1 = AppConfigManager(config_path=str(config_path))
        mgr1.set_window_size(1600, 900)
        mgr1.save()
        mgr2 = AppConfigManager(config_path=str(config_path))
        assert mgr2.get_window_size() == [1600, 900]

    def test_save_and_reload_default_case_dir(self, config_path, tmp_path):
        mgr1 = AppConfigManager(config_path=str(config_path))
        case_dir = str(tmp_path / "case_A")
        mgr1.set_default_case_dir(case_dir)
        mgr1.save()
        mgr2 = AppConfigManager(config_path=str(config_path))
        assert mgr2.get_default_case_dir() == case_dir

    def test_save_and_reload_case_library_dirs(self, config_path, tmp_path, monkeypatch):
        monkeypatch.delenv("FOAM_TUTORIALS", raising=False)
        mgr1 = AppConfigManager(config_path=str(config_path))
        d = str(tmp_path / "lib")
        mgr1.add_case_library_dir(d)
        mgr1.save()
        mgr2 = AppConfigManager(config_path=str(config_path))
        assert mgr2.get_case_library_dirs() == [d]

    def test_save_empty_config(self, manager, config_path):
        manager.save()
        content = json.loads(config_path.read_text(encoding="utf-8"))
        assert isinstance(content, dict)

    def test_save_overwrites_existing_file(self, config_path):
        old_data = {"window_size": [800, 600], "default_case_dir": "/old/path"}
        config_path.write_text(json.dumps(old_data), encoding="utf-8")
        mgr = AppConfigManager(config_path=str(config_path))
        mgr.set_window_size(1920, 1080)
        mgr.save()
        content = json.loads(config_path.read_text(encoding="utf-8"))
        assert content["window_size"] == [1920, 1080]

    def test_save_creates_parent_directory(self, tmp_path):
        nested_path = tmp_path / "subdir" / "app_config.json"
        mgr = AppConfigManager(config_path=str(nested_path))
        mgr.set_window_size(800, 600)
        mgr.save()
        assert nested_path.exists()


class TestReset:
    def test_reset_clears_window_size(self, manager):
        manager.set_window_size(1280, 720)
        manager.reset()
        assert manager.get_window_size() is None

    def test_reset_clears_default_case_dir(self, manager, tmp_path):
        manager.set_default_case_dir(str(tmp_path))
        manager.reset()
        assert manager.get_default_case_dir() is None

    def test_reset_clears_case_library_dirs(self, manager, tmp_path):
        manager.add_case_library_dir(str(tmp_path))
        manager.reset()
        assert manager.get_user_library_dirs() == []

    def test_reset_and_save_writes_empty_config(self, config_path):
        mgr = AppConfigManager(config_path=str(config_path))
        mgr.set_window_size(1280, 720)
        mgr.save()
        mgr.reset()
        mgr.save()
        content = json.loads(config_path.read_text(encoding="utf-8"))
        assert content.get("window_size") is None
        assert content.get("default_case_dir") is None
        assert content.get("case_library_dirs") == []

    def test_reset_does_not_delete_config_file(self, config_path):
        mgr = AppConfigManager(config_path=str(config_path))
        mgr.set_window_size(800, 600)
        mgr.save()
        mgr.reset()
        assert config_path.exists()

    def test_reset_and_reload_returns_defaults(self, config_path):
        mgr1 = AppConfigManager(config_path=str(config_path))
        mgr1.set_window_size(1024, 768)
        mgr1.save()
        mgr1.reset()
        mgr1.save()
        mgr2 = AppConfigManager(config_path=str(config_path))
        assert mgr2.get_window_size() is None
        assert mgr2.get_default_case_dir() is None


class TestWindowSizeFallback:
    def test_get_window_size_or_default_returns_config_value(self, manager):
        manager.set_window_size(1280, 720)
        w, h = manager.get_window_size_or_default(800, 600)
        assert (w, h) == (1280, 720)

    def test_get_window_size_or_default_returns_default_when_none(self, manager):
        w, h = manager.get_window_size_or_default(800, 600)
        assert (w, h) == (800, 600)

    def test_get_window_size_or_default_after_reset(self, manager):
        manager.set_window_size(1920, 1080)
        manager.reset()
        w, h = manager.get_window_size_or_default(1024, 768)
        assert (w, h) == (1024, 768)

    def test_config_window_size_takes_priority_over_default(self, config_path):
        data = {"window_size": [1366, 768], "default_case_dir": None}
        config_path.write_text(json.dumps(data), encoding="utf-8")
        mgr = AppConfigManager(config_path=str(config_path))
        w, h = mgr.get_window_size_or_default(800, 600)
        assert (w, h) == (1366, 768)


class TestDefaultCaseDirFallback:
    def test_get_default_case_dir_or_default_returns_config_value(self, manager, tmp_path):
        case_dir = str(tmp_path / "myCase")
        manager.set_default_case_dir(case_dir)
        result = manager.get_default_case_dir_or_default("/default/path")
        assert result == case_dir

    def test_get_default_case_dir_or_default_returns_default_when_none(self, manager):
        result = manager.get_default_case_dir_or_default("/default/path")
        assert result == "/default/path"

    def test_get_default_case_dir_or_default_after_reset(self, manager, tmp_path):
        manager.set_default_case_dir(str(tmp_path))
        manager.reset()
        result = manager.get_default_case_dir_or_default("/fallback")
        assert result == "/fallback"


class TestCombined:
    def test_set_both_and_save_and_reload(self, config_path, tmp_path, monkeypatch):
        monkeypatch.delenv("FOAM_TUTORIALS", raising=False)
        case_dir = str(tmp_path / "caseDir")
        lib_dir = str(tmp_path / "lib")
        mgr1 = AppConfigManager(config_path=str(config_path))
        mgr1.set_window_size(1280, 720)
        mgr1.set_default_case_dir(case_dir)
        mgr1.add_case_library_dir(lib_dir)
        mgr1.save()
        mgr2 = AppConfigManager(config_path=str(config_path))
        assert mgr2.get_window_size() == [1280, 720]
        assert mgr2.get_default_case_dir() == case_dir
        assert lib_dir in mgr2.get_case_library_dirs()

    def test_partial_update_does_not_clear_other_settings(self, config_path, tmp_path):
        case_dir = str(tmp_path / "caseDir")
        mgr = AppConfigManager(config_path=str(config_path))
        mgr.set_window_size(800, 600)
        mgr.set_default_case_dir(case_dir)
        mgr.save()
        mgr.set_window_size(1920, 1080)
        mgr.save()
        mgr2 = AppConfigManager(config_path=str(config_path))
        assert mgr2.get_window_size() == [1920, 1080]
        assert mgr2.get_default_case_dir() == case_dir

    def test_reset_and_re_set(self, manager, tmp_path):
        manager.set_window_size(1280, 720)
        manager.set_default_case_dir(str(tmp_path))
        manager.reset()
        manager.set_window_size(640, 480)
        assert manager.get_window_size() == [640, 480]
        assert manager.get_default_case_dir() is None


class TestJsonStructure:
    def test_saved_json_has_window_size_key(self, manager, config_path):
        manager.set_window_size(800, 600)
        manager.save()
        content = json.loads(config_path.read_text(encoding="utf-8"))
        assert "window_size" in content

    def test_saved_json_has_default_case_dir_key(self, manager, config_path):
        manager.save()
        content = json.loads(config_path.read_text(encoding="utf-8"))
        assert "default_case_dir" in content

    def test_saved_json_has_case_library_dirs_key(self, manager, config_path):
        manager.save()
        content = json.loads(config_path.read_text(encoding="utf-8"))
        assert "case_library_dirs" in content

    def test_saved_json_window_size_is_list_of_two_ints(self, manager, config_path):
        manager.set_window_size(1024, 768)
        manager.save()
        content = json.loads(config_path.read_text(encoding="utf-8"))
        ws = content["window_size"]
        assert isinstance(ws, list)
        assert len(ws) == 2
        assert all(isinstance(v, int) for v in ws)

    def test_null_window_size_stored_as_null_in_json(self, manager, config_path):
        manager.save()
        content = json.loads(config_path.read_text(encoding="utf-8"))
        assert content["window_size"] is None

    def test_case_library_dirs_stored_as_list(self, manager, config_path, tmp_path):
        manager.add_case_library_dir(str(tmp_path / "lib"))
        manager.save()
        content = json.loads(config_path.read_text(encoding="utf-8"))
        assert isinstance(content["case_library_dirs"], list)
