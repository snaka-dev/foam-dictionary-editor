# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for foam/include_resolver.py.

Covers both halves of include support's pure layer: turning a directive's
source text into an IncludeRef, and resolving that reference against a case
plus a set of OpenFOAM ``etc`` roots. Everything here builds its own tiny case
on tmp_path -- no OpenFOAM installation is required to run these.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from foam.include_resolver import (
    clear_post_processing_cache,
    include_candidates,
    parse_include_directive,
    resolve_include,
)


@pytest.fixture(autouse=True)
def _clear_caches():
    clear_post_processing_cache()
    yield
    clear_post_processing_cache()


def _case(tmp_path: Path) -> Path:
    """Build a minimal case skeleton and return its root."""
    for sub in ("system", "constant", "0"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    return tmp_path


def _write(path: Path, text: str = "// stub\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


# ── parsing ───────────────────────────────────────────────────────────────────


class TestParseIncludeDirective:
    def test_include_quoted_path_parsed(self):
        ref = parse_include_directive('#include "initialConditions"')
        assert ref is not None
        assert ref.kind == "include"
        assert ref.target == "initialConditions"
        assert ref.optional is False

    def test_sinclude_marked_optional(self):
        ref = parse_include_directive('#sinclude   "sampling"')
        assert ref is not None
        assert ref.kind == "sinclude"
        assert ref.optional is True

    def test_include_if_present_marked_optional(self):
        ref = parse_include_directive('#includeIfPresent "sampling"')
        assert ref is not None
        assert ref.optional is True

    def test_include_etc_not_read_as_include(self):
        # `\b` must not let the shorter `#include` alternative win.
        ref = parse_include_directive('#includeEtc "caseDicts/setConstraintTypes"')
        assert ref is not None
        assert ref.kind == "includeEtc"
        assert ref.target == "caseDicts/setConstraintTypes"

    def test_trailing_semicolon_stripped(self):
        ref = parse_include_directive('#include "meshQualityDict";')
        assert ref is not None
        assert ref.target == "meshQualityDict"

    def test_trailing_line_comment_stripped(self):
        ref = parse_include_directive('#include "foo"  // why')
        assert ref is not None
        assert ref.target == "foo"

    def test_unquoted_argument_accepted(self):
        ref = parse_include_directive("#includeFunc solverInfo")
        assert ref is not None
        assert ref.target == "solverInfo"

    def test_include_func_strips_parentheses(self):
        ref = parse_include_directive("#includeFunc mag(U)")
        assert ref is not None
        assert ref.target == "mag"      # the file to find
        assert ref.arg == "mag(U)"      # what the user wrote, kept for display

    def test_cpp_header_suffix_rejected(self):
        # Pulled in by a #codeStream body, not a dictionary.
        for name in ("createTime.H", "argList.H", "fvCFD.H", "foo.cpp"):
            assert parse_include_directive(f'#include "{name}"') is None

    def test_angle_bracket_cpp_header_rejected(self):
        assert parse_include_directive("#include <fvCFD.H>") is None

    def test_constant_token_not_mistaken_for_cpp_header(self):
        # `<constant>/…` starts with `<` but is a path token, not `<header>`.
        ref = parse_include_directive('#include "<constant>/caseSettings"')
        assert ref is not None
        assert ref.target == "<constant>/caseSettings"

    def test_non_include_directive_returns_none(self):
        for text in ("#eval{1+2}", "#remove x", "#codeStream", "#calc \"1\"", "#inputMode merge;"):
            assert parse_include_directive(text) is None

    def test_empty_argument_returns_none(self):
        assert parse_include_directive("#include") is None
        assert parse_include_directive('#include ""') is None

    def test_plain_text_returns_none(self):
        assert parse_include_directive("startTime 0;") is None


# ── token and variable expansion ──────────────────────────────────────────────


class TestTokenExpansion:
    def test_case_token_expanded(self, tmp_path):
        case = _case(tmp_path)
        target = _write(case / "0" / "include" / "bafflePatches")
        ref = parse_include_directive('#include "<case>/0/include/bafflePatches"')
        got = resolve_include(ref, source_file=case / "system" / "x", case_dir=case)
        assert got.path == target

    def test_constant_token_expanded(self, tmp_path):
        case = _case(tmp_path)
        target = _write(case / "constant" / "caseSettings")
        ref = parse_include_directive('#include "<constant>/caseSettings"')
        got = resolve_include(ref, source_file=case / "0" / "k", case_dir=case)
        assert got.path == target

    def test_system_token_expanded(self, tmp_path):
        case = _case(tmp_path)
        target = _write(case / "system" / "decomposeConstraints")
        ref = parse_include_directive('#include "<system>/decomposeConstraints"')
        got = resolve_include(ref, source_file=case / "0" / "k", case_dir=case)
        assert got.path == target

    def test_etc_token_expands_per_root(self, tmp_path):
        case = _case(tmp_path)
        etc_a = tmp_path / "etc_a"
        etc_b = tmp_path / "etc_b"
        target = _write(etc_b / "shared")
        (etc_a).mkdir(exist_ok=True)
        ref = parse_include_directive('#include "<etc>/shared"')
        got = resolve_include(
            ref, source_file=case / "system" / "x", case_dir=case, etc_dirs=[etc_a, etc_b]
        )
        assert got.path == target

    def test_env_var_expanded(self, tmp_path, monkeypatch):
        case = _case(tmp_path)
        target = _write(case / "constant" / "fromEnv")
        monkeypatch.setenv("FODE_TEST_CASE", str(case))
        ref = parse_include_directive('#include "$FODE_TEST_CASE/constant/fromEnv"')
        got = resolve_include(ref, source_file=case / "system" / "x", case_dir=case)
        assert got.path == target

    def test_unset_env_var_simply_misses(self, tmp_path):
        case = _case(tmp_path)
        ref = parse_include_directive('#include "$FODE_NOT_SET/x"')
        got = resolve_include(ref, source_file=case / "system" / "x", case_dir=case)
        assert got.path is None
        assert got.status == "missing"


# ── plain #include resolution ─────────────────────────────────────────────────


class TestResolveInclude:
    def test_relative_to_including_file_dir_first(self, tmp_path):
        case = _case(tmp_path)
        beside = _write(case / "0" / "include" / "initialConditions")
        _write(case / "include" / "initialConditions")  # also at the case root
        ref = parse_include_directive('#include "include/initialConditions"')
        got = resolve_include(ref, source_file=case / "0" / "U", case_dir=case)
        assert got.path == beside

    def test_falls_back_to_case_dir(self, tmp_path):
        case = _case(tmp_path)
        at_root = _write(case / "shared" / "settings")
        ref = parse_include_directive('#include "shared/settings"')
        got = resolve_include(ref, source_file=case / "system" / "controlDict", case_dir=case)
        assert got.path == at_root

    def test_sibling_of_including_file(self, tmp_path):
        case = _case(tmp_path)
        target = _write(case / "system" / "meshQualityDict")
        ref = parse_include_directive('#include "meshQualityDict"')
        got = resolve_include(ref, source_file=case / "system" / "snappyHexMeshDict", case_dir=case)
        assert got.path == target

    def test_absolute_target_used_as_is(self, tmp_path):
        case = _case(tmp_path)
        target = _write(tmp_path / "elsewhere" / "shared")
        ref = parse_include_directive(f'#include "{target}"')
        got = resolve_include(ref, source_file=case / "system" / "x", case_dir=case)
        assert got.path == target

    def test_gz_sibling_resolved(self, tmp_path):
        case = _case(tmp_path)
        target = _write(case / "constant" / "big.gz")
        ref = parse_include_directive('#include "big"')
        got = resolve_include(ref, source_file=case / "constant" / "x", case_dir=case)
        assert got.path == target


# ── #includeEtc ───────────────────────────────────────────────────────────────


class TestResolveIncludeEtc:
    def test_include_etc_searches_roots_in_order(self, tmp_path):
        case = _case(tmp_path)
        etc_a = tmp_path / "etc_a"
        etc_b = tmp_path / "etc_b"
        first = _write(etc_a / "caseDicts" / "setConstraintTypes")
        _write(etc_b / "caseDicts" / "setConstraintTypes")
        ref = parse_include_directive('#includeEtc "caseDicts/setConstraintTypes"')
        got = resolve_include(
            ref, source_file=case / "0" / "U", case_dir=case, etc_dirs=[etc_a, etc_b]
        )
        assert got.path == first

    def test_include_etc_ignores_case_dir(self, tmp_path):
        # A same-named file in the case must not satisfy #includeEtc.
        case = _case(tmp_path)
        _write(case / "caseDicts" / "setConstraintTypes")
        etc = tmp_path / "etc"
        etc.mkdir()
        ref = parse_include_directive('#includeEtc "caseDicts/setConstraintTypes"')
        got = resolve_include(ref, source_file=case / "0" / "U", case_dir=case, etc_dirs=[etc])
        assert got.path is None


# ── #includeFunc ──────────────────────────────────────────────────────────────


class TestResolveIncludeFunc:
    def test_include_func_prefers_case_system(self, tmp_path):
        case = _case(tmp_path)
        local = _write(case / "system" / "solverInfo")
        etc = tmp_path / "etc"
        _write(etc / "caseDicts" / "postProcessing" / "numerical" / "solverInfo")
        ref = parse_include_directive("#includeFunc solverInfo")
        got = resolve_include(
            ref, source_file=case / "system" / "controlDict", case_dir=case, etc_dirs=[etc]
        )
        assert got.path == local

    def test_include_func_found_under_post_processing(self, tmp_path):
        case = _case(tmp_path)
        etc = tmp_path / "etc"
        target = _write(etc / "caseDicts" / "postProcessing" / "numerical" / "solverInfo")
        ref = parse_include_directive("#includeFunc solverInfo")
        got = resolve_include(
            ref, source_file=case / "system" / "controlDict", case_dir=case, etc_dirs=[etc]
        )
        assert got.path == target

    def test_include_func_with_arguments_resolves_base_name(self, tmp_path):
        case = _case(tmp_path)
        etc = tmp_path / "etc"
        target = _write(etc / "caseDicts" / "postProcessing" / "fields" / "mag")
        ref = parse_include_directive("#includeFunc mag(U)")
        got = resolve_include(
            ref, source_file=case / "system" / "controlDict", case_dir=case, etc_dirs=[etc]
        )
        assert got.path == target


# ── status reporting ──────────────────────────────────────────────────────────


class TestIncludeStatus:
    def test_resolved_status(self, tmp_path):
        case = _case(tmp_path)
        _write(case / "system" / "extra")
        ref = parse_include_directive('#include "extra"')
        got = resolve_include(ref, source_file=case / "system" / "x", case_dir=case)
        assert got.status == "resolved"
        assert got.resolved is True

    def test_missing_required_status(self, tmp_path):
        case = _case(tmp_path)
        ref = parse_include_directive('#include "nope"')
        got = resolve_include(ref, source_file=case / "system" / "x", case_dir=case)
        assert got.status == "missing"
        assert got.resolved is False

    def test_missing_optional_status(self, tmp_path):
        case = _case(tmp_path)
        ref = parse_include_directive('#sinclude "nope"')
        got = resolve_include(ref, source_file=case / "system" / "x", case_dir=case)
        assert got.status == "missing_optional"

    def test_no_installation_status(self, tmp_path):
        case = _case(tmp_path)
        ref = parse_include_directive('#includeEtc "caseDicts/setConstraintTypes"')
        got = resolve_include(ref, source_file=case / "0" / "U", case_dir=case, etc_dirs=[])
        assert got.status == "no_installation"

    def test_optional_etc_include_reports_optional_not_installation(self, tmp_path):
        # Optionality wins: the user asked for "if present".
        case = _case(tmp_path)
        ref = parse_include_directive('#sinclude "<etc>/nope"')
        got = resolve_include(ref, source_file=case / "0" / "U", case_dir=case, etc_dirs=[])
        assert got.status == "missing_optional"


class TestIncludeCandidates:
    def test_candidates_are_public_and_ordered(self, tmp_path):
        case = _case(tmp_path)
        ref = parse_include_directive('#include "settings"')
        candidates = include_candidates(
            ref, source_file=case / "system" / "controlDict", case_dir=case
        )
        assert candidates == [case / "system" / "settings", case / "settings"]
