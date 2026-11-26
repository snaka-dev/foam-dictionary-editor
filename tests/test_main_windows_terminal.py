# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Cover main._default_windows_to_no_terminal.

On Windows the Simple terminal's shell is cmd.exe, which runs none of the Tools
commands and used to be sent ``cd`` with Unix quoting on every case open. A
plain launch there now leaves the terminal out; an explicit --variant wins.
"""
from __future__ import annotations

import main
from app_config.app_config_manager import AppConfigManager


def _cfg(tmp_path) -> AppConfigManager:
    return AppConfigManager(config_path=str(tmp_path / "app_config.json"))


def test_windows_plain_launch_has_no_terminal(tmp_path):
    cfg = _cfg(tmp_path)
    main._default_windows_to_no_terminal(cfg, "win32")
    assert cfg.get_feature("terminal") is False


def test_windows_explicit_variant_is_respected(tmp_path):
    cfg = _cfg(tmp_path)
    cfg.set_features({"terminal": True, "blockmesh": True})
    main._default_windows_to_no_terminal(cfg, "win32")
    assert cfg.get_feature("terminal") is True


def test_other_platforms_are_unchanged(tmp_path):
    for platform in ("linux", "darwin"):
        cfg = _cfg(tmp_path)
        main._default_windows_to_no_terminal(cfg, platform)
        assert cfg.get_feature("terminal") is True
        assert not cfg.has_feature("terminal")
