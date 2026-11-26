# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Unit tests for _version.get_version().

The number always comes from ``__version__``; ``git describe`` only adds the
suffix, and its commit count only when the tag it found is this version's own.
"""
import pytest

import _version
from _version import get_version


@pytest.fixture(autouse=True)
def _pin_version(monkeypatch):
    monkeypatch.setattr(_version, "__version__", "1.7.0")


def _describe(monkeypatch, text):
    monkeypatch.setattr(_version, "_git_describe", lambda: text)


def test_no_git_returns_base_version(monkeypatch):
    _describe(monkeypatch, None)
    assert get_version() == "1.7.0"


def test_on_the_release_commit(monkeypatch):
    _describe(monkeypatch, "v1.7.0-0-ge75192d")
    assert get_version() == "1.7.0"


def test_on_the_release_commit_dirty(monkeypatch):
    _describe(monkeypatch, "v1.7.0-0-ge75192d*")
    assert get_version() == "1.7.0 (dirty)"


def test_ahead_of_tag(monkeypatch):
    _describe(monkeypatch, "v1.7.0-12-ge75192d")
    assert get_version() == "1.7.0 (dev+12, ge75192d)"


def test_ahead_of_tag_dirty(monkeypatch):
    _describe(monkeypatch, "v1.7.0-12-ge75192d*")
    assert get_version() == "1.7.0 (dev+12, ge75192d*)"


def test_an_older_tag_shows_neither_its_number_nor_its_count(monkeypatch):
    # A clone that never fetched the newer tags (its git client set not to
    # fetch them) showed "1.5.1 (dev+117, ...)" for 1.7.0 code.
    _describe(monkeypatch, "v1.5.1-117-g1673a08")
    assert get_version() == "1.7.0 (g1673a08)"


def test_an_older_tag_dirty(monkeypatch):
    _describe(monkeypatch, "v1.5.1-117-g1673a08*")
    assert get_version() == "1.7.0 (g1673a08*)"


def test_another_tag_on_this_very_commit(monkeypatch):
    _describe(monkeypatch, "v1.6.9-0-ge75192d")
    assert get_version() == "1.7.0 (ge75192d)"


def test_hyphenated_tag_is_parsed_whole(monkeypatch):
    monkeypatch.setattr(_version, "__version__", "1.8.0-rc1")
    _describe(monkeypatch, "v1.8.0-rc1-2-ge75192d")
    assert get_version() == "1.8.0-rc1 (dev+2, ge75192d)"


def test_bare_hash_no_tags(monkeypatch):
    # "git describe --always" with no reachable tag yields a bare short hash.
    _describe(monkeypatch, "e75192d")
    assert get_version() == "1.7.0 (ge75192d)"


def test_bare_hash_dirty_no_tags(monkeypatch):
    _describe(monkeypatch, "e75192d*")
    assert get_version() == "1.7.0 (ge75192d*)"


def test_real_checkout_reports_this_version():
    # Whatever tags this clone has, the number shown is __version__'s.
    assert _version.get_version().startswith(_version.__version__)
