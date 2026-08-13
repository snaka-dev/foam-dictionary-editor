# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Regression tests for _reset_diff_for_case_dir (ui/mixins/_diff_ops.py).

_load_case_dir used to leave state.diff untouched: opening a different case
kept the comparison bar, the reference-case parse cache, and the file-list
diff marks pointing at the previous case's reference. Opening a different
case must clear the comparison; reloading the same case must keep it armed
(reload_case routes the same directory through _load_case_dir).
"""
from __future__ import annotations

import pytest

_CONTROL_DICT_TEXT = """FoamFile { version 2.0; format ascii; class dictionary; object controlDict; }
application interFoam;
"""


def _make_case(tmp_path, name: str) -> str:
    case = tmp_path / name
    (case / "system").mkdir(parents=True)
    (case / "system" / "controlDict").write_text(_CONTROL_DICT_TEXT, encoding="utf-8")
    return str(case)


@pytest.fixture
def cases(tmp_path):
    return (
        _make_case(tmp_path, "case_a"),
        _make_case(tmp_path, "case_b"),
        _make_case(tmp_path, "reference"),
    )


def test_opening_different_case_clears_comparison(main_window, cases, qapp):
    win = main_window
    case_a, case_b, ref = cases
    win._load_case_dir(case_a)
    win._start_comparison_with(ref)
    qapp.processEvents()
    assert win.state.diff.case_dir == ref
    assert not win._diff_bar.isHidden()

    win._load_case_dir(case_b)
    assert win.state.diff.case_dir is None
    assert win.state.diff.parsed_roots == {}
    assert win._diff_bar.isHidden()
    assert win.comparison_panel.isHidden()


def test_reloading_same_case_keeps_comparison(main_window, cases, qapp):
    win = main_window
    case_a, _, ref = cases
    win._load_case_dir(case_a)
    win._start_comparison_with(ref)
    qapp.processEvents()

    win._load_case_dir(case_a)  # what reload_case does
    qapp.processEvents()
    assert win.state.diff.case_dir == ref
    assert not win._diff_bar.isHidden()


def test_no_comparison_active_is_a_no_op(main_window, cases):
    win = main_window
    case_a, case_b, _ = cases
    win._load_case_dir(case_a)
    assert win.state.diff.case_dir is None
    win._load_case_dir(case_b)
    assert win.state.diff.case_dir is None
    assert win._diff_bar.isHidden()
