# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""
Tests for _apply_comparison_value (ui/mixins/_tree_crud_ops.py) — the
comparison tree's "Use this value" action.

Covers adopting entries whose enclosing block does not exist in the current
case (missing parent dictionaries must be created on the way down), and
unnamed entries such as "#includeFunc ..." directives, which must be appended
into the target block by content — an empty-name lookup used to grab the
enclosing dictionary itself and overwrite it.
"""
from __future__ import annotations

from foam.nodes import FoamNode
from foam.parser import OpenFoamParser
from foam.writer import write_root

_REF_CONTROL_DICT = """\
application     simpleFoam;

functions
{
    #includeFunc mag

    forces1
    {
        type            forces;
        rhoInf          1.225;
    }
}
"""


def _make_case(tmp_path, text):
    (tmp_path / "system").mkdir()
    dict_path = tmp_path / "system" / "controlDict"
    dict_path.write_text(text, encoding="utf-8")
    return str(dict_path)


def _load(win, tmp_path, text):
    dict_path = _make_case(tmp_path, text)
    win._load_case_dir(str(tmp_path))
    win.load_selected_file(dict_path)


def _find(root: FoamNode, *names: str) -> FoamNode:
    node = root
    for name in names:
        node = next(c for c in node.children if c.name == name)
    return node


def _ref_root() -> FoamNode:
    return OpenFoamParser(_REF_CONTROL_DICT).parse()


def _directive(parent: FoamNode) -> FoamNode:
    return next(c for c in parent.children if c.node_type == "directive_entry")


class TestMissingParentsAreCreated:
    def test_nested_value_creates_parent_dicts(self, main_window, tmp_path, control_dict_text):
        win = main_window
        _load(win, tmp_path, control_dict_text)  # has no functions block
        ref = _ref_root()

        win._apply_comparison_value(_find(ref, "functions", "forces1", "rhoInf"))

        functions = _find(win.state.current_root, "functions")
        assert functions.node_type == "dictionary"
        forces = _find(functions, "forces1")
        assert forces.node_type == "dictionary"
        rho = _find(forces, "rhoInf")
        assert rho.value == 1.225
        text = write_root(win.state.current_root)
        assert "functions" in text
        assert "rhoInf" in text

    def test_directive_creates_parent_and_is_appended(self, main_window, tmp_path, control_dict_text):
        win = main_window
        _load(win, tmp_path, control_dict_text)
        ref = _ref_root()

        win._apply_comparison_value(_directive(_find(ref, "functions")))

        functions = _find(win.state.current_root, "functions")
        assert functions.node_type == "dictionary"
        added = _directive(functions)
        assert added.value == "#includeFunc mag"
        assert "#includeFunc mag" in write_root(win.state.current_root)


class TestDirectiveIntoExistingBlock:
    _CURRENT = """\
application     icoFoam;

functions
{
    probes1
    {
        type            probes;
    }
}
"""

    def test_existing_block_is_not_overwritten(self, main_window, tmp_path):
        win = main_window
        _load(win, tmp_path, self._CURRENT)
        ref = _ref_root()

        win._apply_comparison_value(_directive(_find(ref, "functions")))

        functions = _find(win.state.current_root, "functions")
        # The pre-existing entry survives and the directive is added beside it.
        assert functions.node_type == "dictionary"
        assert _find(functions, "probes1").node_type == "dictionary"
        assert _directive(functions).value == "#includeFunc mag"

    def test_directive_is_not_duplicated(self, main_window, tmp_path):
        win = main_window
        _load(win, tmp_path, self._CURRENT)
        ref = _ref_root()

        win._apply_comparison_value(_directive(_find(ref, "functions")))
        win._apply_comparison_value(_directive(_find(ref, "functions")))

        functions = _find(win.state.current_root, "functions")
        directives = [
            c for c in functions.children if c.node_type == "directive_entry"
        ]
        assert len(directives) == 1


class TestGuards:
    def test_named_value_still_overwrites(self, main_window, tmp_path, control_dict_text):
        win = main_window
        _load(win, tmp_path, control_dict_text)  # application interFoam;
        ref = _ref_root()

        win._apply_comparison_value(_find(ref, "application"))

        assert _find(win.state.current_root, "application").value == "simpleFoam"

    def test_non_dictionary_parent_aborts(self, main_window, tmp_path):
        win = main_window
        _load(win, tmp_path, "application icoFoam;\nfunctions yes;\n")
        ref = _ref_root()

        win._apply_comparison_value(_find(ref, "functions", "forces1", "rhoInf"))

        functions = _find(win.state.current_root, "functions")
        # Unchanged: still the scalar entry, nothing was created inside it.
        assert functions.node_type != "dictionary"
        assert functions.children == []
