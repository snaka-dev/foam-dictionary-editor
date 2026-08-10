# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Cover main._apply_ui_scale — the Settings > UI Scale setting's only effect.

Qt reads QT_SCALE_FACTOR once, when the QApplication is constructed, so the
setting is an environment variable written from inside the process rather than
anything callable later. These tests are the whole of its behaviour.

Every test touches QT_SCALE_FACTOR through monkeypatch before calling in, so
the value this process was started with is put back afterwards.
"""
from __future__ import annotations

import os

import main


class TestNoScaling:
    def test_the_default_sets_nothing(self, monkeypatch):
        monkeypatch.delenv("QT_SCALE_FACTOR", raising=False)
        main._apply_ui_scale(100, forced=False)
        assert "QT_SCALE_FACTOR" not in os.environ

    def test_the_default_leaves_an_existing_value_alone(self, monkeypatch):
        # --ui-scale 100 means "no scaling of my own", not "undo the desktop's".
        monkeypatch.setenv("QT_SCALE_FACTOR", "2")
        main._apply_ui_scale(100, forced=True)
        assert os.environ["QT_SCALE_FACTOR"] == "2"


class TestFromTheConfigFile:
    def test_sets_the_scale_factor(self, monkeypatch):
        monkeypatch.delenv("QT_SCALE_FACTOR", raising=False)
        main._apply_ui_scale(150, forced=False)
        assert os.environ["QT_SCALE_FACTOR"] == "1.5"

    def test_fractional_percentages_stay_exact(self, monkeypatch):
        monkeypatch.delenv("QT_SCALE_FACTOR", raising=False)
        main._apply_ui_scale(125, forced=False)
        assert os.environ["QT_SCALE_FACTOR"] == "1.25"

    def test_yields_to_a_value_already_in_the_environment(self, monkeypatch):
        # The desktop or a wrapper script knows more about the display in front
        # of the user than a setting last touched on another machine.
        monkeypatch.setenv("QT_SCALE_FACTOR", "2")
        main._apply_ui_scale(150, forced=False)
        assert os.environ["QT_SCALE_FACTOR"] == "2"


class TestFromTheCommandLine:
    def test_overrides_the_environment(self, monkeypatch):
        monkeypatch.setenv("QT_SCALE_FACTOR", "2")
        main._apply_ui_scale(150, forced=True)
        assert os.environ["QT_SCALE_FACTOR"] == "1.5"
