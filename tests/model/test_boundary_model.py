# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import pytest
from model.boundary_model import BoundaryModel, extract_boundary
from foam.parser import OpenFoamParser


def _parse(text: str):
    return OpenFoamParser(text).parse()


def _field_root(patches: dict[str, str]):
    """Build a minimal field FoamNode with a boundaryField containing given patches."""
    entries = "\n".join(
        f"    {name}\n    {{\n        type {typ};\n    }}" for name, typ in patches.items()
    )
    src = f"FoamFile {{ version 2.0; format ascii; class volScalarField; }}\n\nboundaryField\n{{\n{entries}\n}}\n"
    return _parse(src)


@pytest.fixture()
def model():
    return BoundaryModel()


@pytest.fixture()
def case_dir(tmp_path):
    (tmp_path / "0").mkdir()
    (tmp_path / "constant").mkdir()
    return str(tmp_path)


def _path(case_dir, rel):
    from pathlib import Path
    return str(Path(case_dir) / rel)


class TestExtractBoundary:
    def test_returns_patch_nodes(self):
        root = _field_root({"inlet": "fixedValue", "outlet": "zeroGradient"})
        bd = extract_boundary(root)
        assert set(bd.keys()) == {"inlet", "outlet"}

    def test_empty_when_no_boundary_field(self):
        root = _parse("FoamFile { version 2.0; }\n")
        assert extract_boundary(root) == {}

    def test_returns_dict_nodes_only(self):
        root = _field_root({"wall": "noSlip"})
        bd = extract_boundary(root)
        for node in bd.values():
            assert node.node_type == "dictionary"


class TestBoundaryModelLoad:
    def test_stores_case_dir(self, model, case_dir):
        model.load({}, case_dir, [])
        assert model.case_dir == case_dir

    def test_stores_field_roots(self, model, case_dir):
        root = _field_root({"inlet": "fixedValue"})
        path = _path(case_dir, "0/U")
        model.load({path: root}, case_dir, ["0"])
        assert path in model.field_roots

    def test_stores_available_dirs(self, model, case_dir):
        model.load({}, case_dir, ["0", "0.orig"])
        assert model.available_dirs == ["0", "0.orig"]


class TestUpdateField:
    def test_replaces_entry(self, model, case_dir):
        path = _path(case_dir, "0/U")
        root_v1 = _field_root({"inlet": "fixedValue"})
        root_v2 = _field_root({"inlet": "fixedValue", "outlet": "zeroGradient"})
        model.load({path: root_v1}, case_dir, ["0"])
        model.update_field(path, root_v2)
        bd = extract_boundary(model.field_roots[path])
        assert "outlet" in bd

    def test_adds_new_path(self, model, case_dir):
        path = _path(case_dir, "0/p")
        model.load({}, case_dir, ["0"])
        model.update_field(path, _field_root({"wall": "zeroGradient"}))
        assert path in model.field_roots


class TestBoundariesForDir:
    def test_filters_by_dir(self, model, case_dir):
        path_0 = _path(case_dir, "0/U")
        path_const = _path(case_dir, "constant/transportProperties")
        root_0 = _field_root({"inlet": "fixedValue"})
        root_const = _field_root({"wall": "noSlip"})
        model.load({path_0: root_0, path_const: root_const}, case_dir, ["0", "constant"])

        result = model.boundaries_for_dir("0")
        assert path_0 in result
        assert path_const not in result

    def test_returns_boundary_dicts(self, model, case_dir):
        path = _path(case_dir, "0/U")
        root = _field_root({"inlet": "fixedValue", "outlet": "zeroGradient"})
        model.load({path: root}, case_dir, ["0"])
        result = model.boundaries_for_dir("0")
        assert set(result[path].keys()) == {"inlet", "outlet"}

    def test_empty_when_no_case_dir(self, model):
        assert model.boundaries_for_dir("0") == {}

    def test_empty_when_dir_has_no_files(self, model, case_dir):
        path = _path(case_dir, "0/U")
        model.load({path: _field_root({})}, case_dir, ["0"])
        assert model.boundaries_for_dir("constant") == {}


class TestIsInDir:
    def test_matches_correct_dir(self, model, case_dir):
        path = _path(case_dir, "0/U")
        model.load({}, case_dir, [])
        assert model.is_in_dir(path, "0")
        assert not model.is_in_dir(path, "constant")

    def test_false_when_no_case_dir(self, model):
        assert not model.is_in_dir("/some/path", "0")


class TestClear:
    def test_resets_all(self, model, case_dir):
        path = _path(case_dir, "0/U")
        model.load({path: _field_root({"inlet": "fixedValue"})}, case_dir, ["0"])
        model.clear()
        assert model.case_dir is None
        assert model.field_roots == {}
        assert model.available_dirs == []
        assert model.boundaries_for_dir("0") == {}
