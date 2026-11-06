# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""What the user is told when the settings file cannot be read, written or deleted.

These used to be four `print()` calls -- the entire error-reporting mechanism for
settings. FoDE is a GUI: started from a desktop entry, stdout goes nowhere, so a config
that would not parse reset every setting the user had with no explanation at all.
"""
from __future__ import annotations

import json

import pytest

from app_config.app_config_manager import AppConfigManager


def _manager(path):
    return AppConfigManager(config_path=str(path))


class TestAnUnreadableConfig:
    @pytest.fixture
    def broken(self, tmp_path):
        p = tmp_path / "app_config.json"
        p.write_text('{"window_size": [1600, 900], "default_case_dir": "/work/case",', encoding="utf-8")
        return p

    def test_the_user_is_told_rather_than_silently_reset(self, broken):
        warnings = _manager(broken).take_warnings()
        assert len(warnings) == 1
        assert "could not be read" in warnings[0]

    def test_the_damaged_file_is_kept_not_overwritten(self, broken):
        original = broken.read_text(encoding="utf-8")
        cfg = _manager(broken)
        # closeEvent always saves; before this, that wrote defaults straight over the
        # file and the only copy of the user's settings was gone.
        cfg.set_window_size(1200, 800)
        cfg.save()
        spare = broken.with_suffix(broken.suffix + ".bad")
        assert spare.exists(), "the unreadable file was not preserved"
        assert spare.read_text(encoding="utf-8") == original

    def test_the_warning_says_where_the_old_file_went(self, broken):
        warning = _manager(broken).take_warnings()[0]
        assert ".bad" in warning

    def test_defaults_are_in_use_afterwards(self, broken):
        assert _manager(broken).get_window_size() is None

    def test_saving_after_the_rescue_writes_a_readable_file(self, broken):
        cfg = _manager(broken)
        cfg.set_window_size(1024, 768)
        cfg.save()
        assert json.loads(broken.read_text(encoding="utf-8"))["window_size"] == [1024, 768]


class TestAHealthyConfig:
    def test_it_warns_about_nothing(self, tmp_path):
        p = tmp_path / "app_config.json"
        p.write_text(json.dumps({"window_size": [1000, 700]}), encoding="utf-8")
        cfg = _manager(p)
        assert cfg.take_warnings() == []
        assert cfg.get_window_size() == [1000, 700]

    def test_an_absent_file_is_not_a_failure(self, tmp_path):
        assert _manager(tmp_path / "nothing.json").take_warnings() == []

    def test_nothing_is_moved_aside(self, tmp_path):
        p = tmp_path / "app_config.json"
        p.write_text(json.dumps({"window_size": [1000, 700]}), encoding="utf-8")
        _manager(p)
        assert not p.with_suffix(".json.bad").exists()


class TestWarningsAreDrained:
    def test_taking_them_twice_does_not_repeat_them(self, tmp_path):
        p = tmp_path / "app_config.json"
        p.write_text("{not json", encoding="utf-8")
        cfg = _manager(p)
        assert cfg.take_warnings() != []
        assert cfg.take_warnings() == []


class TestDeleteReportsWhetherItWorked:
    def test_it_returns_true_when_the_file_goes(self, tmp_path):
        p = tmp_path / "app_config.json"
        p.write_text("{}", encoding="utf-8")
        assert _manager(p).delete_config_file() is True
        assert not p.exists()

    def test_it_returns_true_when_there_was_nothing_to_delete(self, tmp_path):
        assert _manager(tmp_path / "absent.json").delete_config_file() is True

    def test_a_failure_returns_false_and_warns(self, tmp_path, monkeypatch):
        p = tmp_path / "app_config.json"
        p.write_text("{}", encoding="utf-8")
        cfg = _manager(p)
        monkeypatch.setattr(
            type(p), "unlink", lambda self, *a, **k: (_ for _ in ()).throw(OSError("read-only"))
        )
        assert cfg.delete_config_file() is False
        assert any("could not be deleted" in w for w in cfg.take_warnings())


class TestSaveFailureIsRecorded:
    def test_an_unwritable_path_warns_instead_of_printing(self, tmp_path, monkeypatch):
        cfg = _manager(tmp_path / "app_config.json")
        import app_config.app_config_manager as acm

        monkeypatch.setattr(
            acm, "save_json", lambda *a, **k: (_ for _ in ()).throw(OSError("disk full"))
        )
        cfg.save()
        assert any("could not be saved" in w for w in cfg.take_warnings())
