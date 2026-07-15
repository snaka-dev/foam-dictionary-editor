# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
import pytest

from app_config.json_io import load_json, save_json


@pytest.fixture
def path(tmp_path):
    return tmp_path / "sub" / "data.json"


class TestLoadJson:
    def test_missing_file_returns_none(self, path):
        assert load_json(path) is None

    def test_corrupt_json_returns_none(self, path):
        path.parent.mkdir(parents=True)
        path.write_text("{ not json", encoding="utf-8")
        assert load_json(path) is None

    def test_valid_json_returns_dict(self, path):
        path.parent.mkdir(parents=True)
        path.write_text('{"a": 1}', encoding="utf-8")
        assert load_json(path) == {"a": 1}


class TestSaveJson:
    def test_creates_parent_directory(self, path):
        save_json(path, {"a": 1})
        assert path.exists()

    def test_round_trips(self, path):
        save_json(path, {"a": 1, "b": [1, 2, 3]})
        assert load_json(path) == {"a": 1, "b": [1, 2, 3]}

    def test_overwrites_existing_file(self, path):
        save_json(path, {"a": 1})
        save_json(path, {"a": 2})
        assert load_json(path) == {"a": 2}
