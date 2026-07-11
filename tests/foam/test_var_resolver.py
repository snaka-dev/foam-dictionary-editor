# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for foam/var_resolver: build_var_map, substitute_vars, eval_foam_expr."""
from __future__ import annotations

import pytest

from foam.parser import OpenFoamParser
from foam.var_resolver import build_var_map, eval_foam_expr, substitute_vars


def _root(body: str):
    header = "FoamFile { version 2.0; format ascii; class dictionary; object d; }\n"
    return OpenFoamParser(header + body).parse()


# ── eval_foam_expr ────────────────────────────────────────────────────────────

def test_eval_simple_addition():
    assert eval_foam_expr("1 + 2") == "3.0"


def test_eval_float_division():
    result = eval_foam_expr("1.0 / 4")
    assert pytest.approx(float(result)) == 0.25


def test_eval_negative():
    assert pytest.approx(float(eval_foam_expr("-0.01"))) == -0.01


def test_eval_unresolved_var_returns_none():
    assert eval_foam_expr("$x + 1") is None


def test_eval_empty_returns_none():
    assert eval_foam_expr("") is None


# ── substitute_vars ───────────────────────────────────────────────────────────

def test_substitute_simple():
    assert substitute_vars("$x", {"x": "1.0"}) == "1.0"


def test_substitute_braced():
    assert substitute_vars("${x}", {"x": "2.0"}) == "2.0"


def test_substitute_longest_first():
    result = substitute_vars("$xMin $x", {"x": "1", "xMin": "-0.5"})
    assert result == "-0.5 1"


def test_substitute_no_partial_match():
    result = substitute_vars("$xMin", {"x": "1"})
    assert result == "$xMin"


def test_substitute_empty_map():
    assert substitute_vars("$x", {}) == "$x"


# ── build_var_map ─────────────────────────────────────────────────────────────

def test_scalar_int_collected():
    root = _root("a 1.5;\nb 3;\n")
    vm = build_var_map(root)
    assert vm["a"] == "1.5"
    assert vm["b"] == "3"


def test_macro_reference_resolved():
    root = _root("x 0.1;\ny $x;\n")
    vm = build_var_map(root)
    assert vm["y"] == "0.1"


def test_eval_expression_resolved():
    root = _root("r 0.1;\nrHalf #eval{ $r / 2 };\n")
    vm = build_var_map(root)
    assert pytest.approx(float(vm["rHalf"])) == 0.05


def test_chained_resolution():
    root = _root("a 1.0;\nb #eval{ $a * 2 };\nc $b;\n")
    vm = build_var_map(root)
    assert pytest.approx(float(vm["b"])) == 2.0
    assert pytest.approx(float(vm["c"])) == 2.0


def test_negated_macro_word():
    root = _root("xMax 0.01;\nxMin -$xMax;\n")
    vm = build_var_map(root)
    assert pytest.approx(float(vm["xMin"])) == -0.01


def test_unresolvable_absent():
    root = _root("y $undeclared;\n")
    vm = build_var_map(root)
    assert "y" not in vm


def test_skip_keys_excluded():
    root = _root("vertices ( (0 0 0) );\na 1.0;\n")
    vm = build_var_map(root, skip_keys=frozenset({"vertices"}))
    assert "a" in vm
    assert "vertices" not in vm


def test_dictionary_nodes_not_collected():
    root = _root("subDict { x 1; }\na 2.0;\n")
    vm = build_var_map(root)
    assert "a" in vm
    assert "subDict" not in vm
