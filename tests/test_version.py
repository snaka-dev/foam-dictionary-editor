# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Unit tests for _version.get_version() — the git-describe formatting logic."""
import _version
from _version import __version__, get_version


def test_no_git_returns_base_version(monkeypatch):
    monkeypatch.setattr(_version, "_git_describe", lambda: None)
    assert get_version() == __version__


def test_exact_tag_strips_v_prefix(monkeypatch):
    monkeypatch.setattr(_version, "_git_describe", lambda: "v1.7.0")
    assert get_version() == "1.7.0"


def test_exact_tag_dirty(monkeypatch):
    monkeypatch.setattr(_version, "_git_describe", lambda: "v1.7.0*")
    assert get_version() == "1.7.0 (dirty)"


def test_ahead_of_tag(monkeypatch):
    monkeypatch.setattr(_version, "_git_describe", lambda: "v1.7.0-12-ge75192d")
    assert get_version() == "1.7.0 (dev+12, ge75192d)"


def test_ahead_of_tag_dirty(monkeypatch):
    monkeypatch.setattr(_version, "_git_describe", lambda: "v1.7.0-12-ge75192d*")
    assert get_version() == "1.7.0 (dev+12, ge75192d*)"


def test_bare_hash_no_tags(monkeypatch):
    # "git describe --always" with no reachable tag yields a bare short hash.
    monkeypatch.setattr(_version, "_git_describe", lambda: "e75192d")
    assert get_version() == f"{__version__} (ge75192d)"


def test_bare_hash_dirty_no_tags(monkeypatch):
    monkeypatch.setattr(_version, "_git_describe", lambda: "e75192d*")
    assert get_version() == f"{__version__} (ge75192d*)"
