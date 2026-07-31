# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
import json

import pytest

from app_config.app_config_manager import AppConfigManager


@pytest.fixture(autouse=True)
def _no_wm_project_dir(monkeypatch):
    """foam_tutorials_dir falls back to $WM_PROJECT_DIR/tutorials; clear the
    variable so these tests stay hermetic on machines with a sourced
    OpenFOAM environment."""
    monkeypatch.delenv("WM_PROJECT_DIR", raising=False)


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

    def test_foam_tutorials_dir_falls_back_to_wm_project_dir(self, tmp_path, monkeypatch):
        project = tmp_path / "OpenFOAM-12"
        (project / "tutorials").mkdir(parents=True)
        monkeypatch.delenv("FOAM_TUTORIALS", raising=False)
        monkeypatch.setenv("WM_PROJECT_DIR", str(project))
        assert AppConfigManager.foam_tutorials_dir() == str(project / "tutorials")


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


class TestSettingsWereReset:
    """The flag that stops a shut-down from writing a deleted config file back."""

    def test_false_on_a_fresh_manager(self, manager):
        assert manager.settings_were_reset is False

    def test_set_by_deleting_the_config_file(self, manager):
        manager.delete_config_file()
        assert manager.settings_were_reset is True

    def test_set_even_when_there_was_no_file_to_delete(self, config_path, manager):
        assert not config_path.exists()
        manager.delete_config_file()
        assert manager.settings_were_reset is True

    def test_an_in_memory_reset_alone_does_not_set_it(self, manager):
        manager.reset()
        assert manager.settings_were_reset is False

    def test_does_not_survive_into_the_next_run(self, config_path, manager):
        manager.delete_config_file()
        manager.save()
        assert AppConfigManager(config_path=str(config_path)).settings_were_reset is False


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


class TestFeatureFlags:
    def test_get_feature_defaults_to_true_when_absent(self, manager):
        assert manager.get_feature("terminal") is True
        assert manager.get_feature("blockmesh") is True

    def test_get_feature_respects_custom_default(self, manager):
        assert manager.get_feature("nonexistent", default=False) is False

    def test_get_feature_returns_false_when_set_false(self, config_path):
        data = {"features": {"terminal": False, "blockmesh": False}}
        config_path.write_text(json.dumps(data), encoding="utf-8")
        mgr = AppConfigManager(config_path=str(config_path))
        assert mgr.get_feature("terminal") is False
        assert mgr.get_feature("blockmesh") is False

    def test_get_feature_returns_true_when_set_true(self, config_path):
        data = {"features": {"terminal": True, "blockmesh": True}}
        config_path.write_text(json.dumps(data), encoding="utf-8")
        mgr = AppConfigManager(config_path=str(config_path))
        assert mgr.get_feature("terminal") is True
        assert mgr.get_feature("blockmesh") is True

    def test_get_feature_mixed_values(self, config_path):
        data = {"features": {"terminal": False, "blockmesh": True}}
        config_path.write_text(json.dumps(data), encoding="utf-8")
        mgr = AppConfigManager(config_path=str(config_path))
        assert mgr.get_feature("terminal") is False
        assert mgr.get_feature("blockmesh") is True

    def test_features_saved_to_json(self, config_path):
        mgr = AppConfigManager(config_path=str(config_path))
        mgr._features = {"terminal": False, "blockmesh": True}
        mgr.save()
        content = json.loads(config_path.read_text(encoding="utf-8"))
        assert content["features"] == {"terminal": False, "blockmesh": True}

    def test_features_not_written_when_empty(self, manager, config_path):
        manager.save()
        content = json.loads(config_path.read_text(encoding="utf-8"))
        assert "features" not in content

    def test_features_persist_across_reload(self, config_path):
        mgr1 = AppConfigManager(config_path=str(config_path))
        mgr1._features = {"terminal": False, "blockmesh": False}
        mgr1.save()
        mgr2 = AppConfigManager(config_path=str(config_path))
        assert mgr2.get_feature("terminal") is False
        assert mgr2.get_feature("blockmesh") is False

    def test_reset_clears_features(self, config_path):
        mgr = AppConfigManager(config_path=str(config_path))
        mgr._features = {"terminal": False}
        mgr.reset()
        assert mgr.get_feature("terminal") is True

    def test_broken_json_clears_features(self, config_path):
        config_path.write_text("{ broken", encoding="utf-8")
        mgr = AppConfigManager(config_path=str(config_path))
        assert mgr.get_feature("terminal") is True

    def test_set_feature(self, config_path):
        mgr = AppConfigManager(config_path=str(config_path))
        mgr.set_feature("syntax_highlighting", False)
        assert mgr.get_feature("syntax_highlighting") is False

    def test_set_features_replaces_whole_mapping(self, config_path):
        mgr = AppConfigManager(config_path=str(config_path))
        mgr.set_feature("terminal", False)
        mgr.set_features({"blockmesh": False})
        assert mgr.get_feature("blockmesh") is False
        assert mgr.get_feature("terminal") is True  # dropped by the replace

    def test_set_features_persists_after_save_reload(self, config_path):
        mgr1 = AppConfigManager(config_path=str(config_path))
        mgr1.set_features({"terminal": False, "blockmesh": True})
        mgr1.save()
        mgr2 = AppConfigManager(config_path=str(config_path))
        assert mgr2.get_feature("terminal") is False
        assert mgr2.get_feature("blockmesh") is True

    def test_set_features_copies_the_mapping(self, config_path):
        mgr = AppConfigManager(config_path=str(config_path))
        features = {"terminal": False}
        mgr.set_features(features)
        features["terminal"] = True
        assert mgr.get_feature("terminal") is False

    def test_set_feature_persists_after_save_reload(self, config_path):
        mgr1 = AppConfigManager(config_path=str(config_path))
        mgr1.set_feature("syntax_highlighting", False)
        mgr1.save()
        mgr2 = AppConfigManager(config_path=str(config_path))
        assert mgr2.get_feature("syntax_highlighting") is False


class TestOpenfoamDir:
    def test_default_is_none(self, manager):
        assert manager.get_openfoam_dir() is None

    def test_set_get(self, manager):
        manager.set_openfoam_dir("/usr/lib/openfoam/openfoam2606")
        assert manager.get_openfoam_dir() == "/usr/lib/openfoam/openfoam2606"

    def test_persists_across_reload(self, config_path):
        mgr1 = AppConfigManager(config_path=str(config_path))
        mgr1.set_openfoam_dir("/opt/openfoam12")
        mgr1.save()
        mgr2 = AppConfigManager(config_path=str(config_path))
        assert mgr2.get_openfoam_dir() == "/opt/openfoam12"

    def test_unset_not_written_to_json(self, config_path, manager):
        manager.save()
        data = json.loads(config_path.read_text(encoding="utf-8"))
        assert "openfoam_dir" not in data

    def test_reset_clears(self, manager):
        manager.set_openfoam_dir("/opt/openfoam12")
        manager.reset()
        assert manager.get_openfoam_dir() is None

    def test_broken_json_clears(self, config_path):
        config_path.write_text("{ broken", encoding="utf-8")
        mgr = AppConfigManager(config_path=str(config_path))
        assert mgr.get_openfoam_dir() is None


class TestSessionRestore:
    def test_enabled_by_default(self, manager):
        assert manager.get_restore_session() is True

    def test_disabling_persists_and_is_written_to_json(self, config_path):
        mgr1 = AppConfigManager(config_path=str(config_path))
        mgr1.set_restore_session(False)
        mgr1.save()
        assert "restore_session" in json.loads(config_path.read_text(encoding="utf-8"))
        assert AppConfigManager(config_path=str(config_path)).get_restore_session() is False

    def test_enabled_is_not_written_to_json(self, config_path, manager):
        manager.save()
        assert "restore_session" not in json.loads(config_path.read_text(encoding="utf-8"))

    def test_state_round_trips(self, config_path):
        mgr1 = AppConfigManager(config_path=str(config_path))
        mgr1.set_session_state({"upper_tab": "Tree"})
        mgr1.save()
        mgr2 = AppConfigManager(config_path=str(config_path))
        assert mgr2.get_session_state() == {"upper_tab": "Tree"}

    def test_disabling_keeps_the_stored_state(self, manager):
        """The setting decides whether a layout is applied, not whether it exists.
        Discarding one is Forget Saved Session's job (see TestClearSessions)."""
        manager.set_session_state({"upper_tab": "Tree"})
        manager.set_restore_session(False)
        assert manager.get_session_state() == {"upper_tab": "Tree"}

    def test_off_then_on_returns_the_same_state(self, manager):
        manager.set_session_state({"upper_tab": "Tree"})
        manager.set_restore_session(False)
        manager.set_restore_session(True)
        assert manager.get_session_state() == {"upper_tab": "Tree"}

    def test_a_non_dict_state_reads_back_as_none(self, config_path):
        config_path.write_text(json.dumps({"sessions": {"terminal+blockmesh": "nope"}}),
                               encoding="utf-8")
        mgr = AppConfigManager(config_path=str(config_path))
        assert mgr.get_session_state() is None

    def test_a_non_dict_sessions_key_reads_back_as_none(self, config_path):
        config_path.write_text(json.dumps({"sessions": ["nope"]}), encoding="utf-8")
        assert AppConfigManager(config_path=str(config_path)).get_session_state() is None

    def test_reset_clears(self, manager):
        manager.set_session_state({"upper_tab": "Tree"})
        manager.reset()
        assert manager.get_session_state() is None
        assert manager.get_restore_session() is True


class TestClearSessions:
    """What Settings > Forget Saved Session calls."""

    def test_has_stored_sessions_is_false_when_nothing_is_stored(self, manager):
        assert manager.has_stored_sessions() is False

    def test_has_stored_sessions_is_true_once_one_is(self, manager):
        manager.set_session_state({"upper_tab": "Tree"})
        assert manager.has_stored_sessions() is True

    def test_clears_every_feature_sets_layout(self, manager):
        manager.set_features({"terminal": True, "blockmesh": True})
        manager.set_session_state({"upper_tab": "Tree"})
        manager.set_features({"terminal": False, "blockmesh": False})
        manager.set_session_state({"upper_tab": "Editor"})

        manager.clear_sessions()

        assert manager.has_stored_sessions() is False
        assert manager.get_session_state() is None
        manager.set_features({"terminal": True, "blockmesh": True})
        assert manager.get_session_state() is None

    def test_leaves_the_setting_itself_alone(self, manager):
        manager.set_session_state({"upper_tab": "Tree"})
        manager.clear_sessions()
        assert manager.get_restore_session() is True

    def test_the_cleared_state_does_not_come_back_from_disk(self, config_path, manager):
        manager.set_session_state({"upper_tab": "Tree"})
        manager.save()
        manager.clear_sessions()
        manager.save()
        assert "sessions" not in json.loads(config_path.read_text(encoding="utf-8"))
        assert AppConfigManager(config_path=str(config_path)).get_session_state() is None


class TestSessionKey:
    """Layouts are partitioned by the feature flags that decide which panels exist."""

    def test_reflects_the_layout_features(self, manager):
        manager.set_features({"terminal": True, "blockmesh": True})
        assert manager.session_key() == "terminal+blockmesh"
        manager.set_features({"terminal": False, "blockmesh": True})
        assert manager.session_key() == "blockmesh"
        manager.set_features({"terminal": False, "blockmesh": False})
        assert manager.session_key() == "minimal"

    def test_non_layout_features_do_not_split_the_key(self, manager):
        manager.set_features({"terminal": True, "blockmesh": True})
        before = manager.session_key()
        manager.set_feature("syntax_highlighting", False)
        assert manager.session_key() == before

    def test_variants_do_not_overwrite_each_other(self, manager):
        manager.set_features({"terminal": True, "blockmesh": True})
        manager.set_session_state({"upper_tab": "Tree"})
        manager.set_features({"terminal": False, "blockmesh": False})
        assert manager.get_session_state() is None
        manager.set_session_state({"upper_tab": "Boundary"})
        manager.set_features({"terminal": True, "blockmesh": True})
        assert manager.get_session_state() == {"upper_tab": "Tree"}


class TestClearSessionGeometry:
    """What makes Reset Window Size outlive the next restore."""

    def test_drops_size_and_position_but_keeps_the_rest(self, manager):
        manager.set_session_state(
            {"geometry": "blob", "window_size": [900, 700], "upper_tab": "Tree"}
        )
        manager.clear_session_geometry()
        assert manager.get_session_state() == {"upper_tab": "Tree"}

    def test_clears_every_variants_geometry(self, manager):
        manager.set_features({"terminal": True, "blockmesh": True})
        manager.set_session_state({"window_size": [900, 700]})
        manager.set_features({"terminal": False, "blockmesh": False})
        manager.set_session_state({"window_size": [800, 600]})
        manager.clear_session_geometry()
        assert manager.get_session_state() == {}
        manager.set_features({"terminal": True, "blockmesh": True})
        assert manager.get_session_state() == {}
