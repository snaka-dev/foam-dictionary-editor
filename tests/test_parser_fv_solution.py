# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from foam.parser import OpenFoamParser


def find_child(node, name):
    for child in node.children:
        if child.name == name:
            return child
    raise AssertionError(f"child not found: {name}")


def test_parse_fv_solution_macro_and_regex_key(fv_solution_text):
    root = OpenFoamParser(fv_solution_text).parse()

    solvers = find_child(root, "solvers")
    p = find_child(solvers, "p")
    p_final = find_child(solvers, "pFinal")
    regex_block = find_child(solvers, '"(U|k|omega)"')

    solver = find_child(p, "solver")
    assert solver.node_type == "word"
    assert solver.value == "GAMG"

    tolerance = find_child(p, "tolerance")
    assert tolerance.node_type == "scalar"
    assert tolerance.value == 1e-06

    macro_entry = p_final.children[0]
    assert macro_entry.node_type == "macro_entry"
    assert macro_entry.value == "$p"

    rel_tol = find_child(p_final, "relTol")
    assert rel_tol.node_type == "int"
    assert rel_tol.value == 0

    assert regex_block.node_type == "dictionary"
    smoother = find_child(regex_block, "smoother")
    assert smoother.value == "symGaussSeidel"

def test_parse_fv_solution_pimple_block(fv_solution_text):
    """PIMPLE block settings are parsed correctly"""
    root = OpenFoamParser(fv_solution_text).parse()
    pimple = find_child(root, "PIMPLE")
    assert pimple.node_type == "dictionary"

    n_correctors = find_child(pimple, "nCorrectors")
    assert n_correctors.node_type == "int"
    assert n_correctors.value == 2

    momentum_predictor = find_child(pimple, "momentumPredictor")
    assert momentum_predictor.value == "yes"


def test_parse_fv_solution_solver_tolerance(fv_solution_text):
    """Solver tolerance is parsed as a scalar"""
    root = OpenFoamParser(fv_solution_text).parse()
    solvers = find_child(root, "solvers")
    p = find_child(solvers, "p")
    tolerance = find_child(p, "tolerance")
    assert tolerance.node_type == "scalar"
    assert tolerance.value == 1e-06


def test_parse_fv_solution_solver_smoother(fv_solution_text):
    """GaussSeidel smoother is parsed as a word"""
    root = OpenFoamParser(fv_solution_text).parse()
    solvers = find_child(root, "solvers")
    p = find_child(solvers, "p")
    smoother = find_child(p, "smoother")
    assert smoother.node_type == "word"
    assert smoother.value == "GaussSeidel"


def test_parse_fv_solution_roundtrip(fv_solution_text):
    """Key entries are preserved after fvSolution parse and write"""
    from foam.writer import write_root
    root = OpenFoamParser(fv_solution_text).parse()
    out = write_root(root)
    assert "solvers" in out
    assert "PIMPLE" in out
    assert "GAMG" in out
    assert "nCorrectors" in out
