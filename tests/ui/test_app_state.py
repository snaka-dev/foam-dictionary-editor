# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from ui.app_state import AppState, DiffState


class TestDiffState:
    def test_default_diff_is_diff_state(self):
        state = AppState()
        assert isinstance(state.diff, DiffState)

    def test_default_case_dir_is_none(self):
        assert AppState().diff.case_dir is None

    def test_default_parsed_roots_is_empty(self):
        assert AppState().diff.parsed_roots == {}

    def test_independent_instances_do_not_share_parsed_roots(self):
        a = AppState()
        b = AppState()
        a.diff.parsed_roots["foo"] = object()
        assert b.diff.parsed_roots == {}

    def test_fields_are_mutable(self):
        state = AppState()
        state.diff.case_dir = "/some/case"
        state.diff.parsed_roots["key"] = "root"
        assert state.diff.case_dir == "/some/case"
        assert state.diff.parsed_roots == {"key": "root"}
