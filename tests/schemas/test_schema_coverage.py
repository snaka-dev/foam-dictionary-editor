# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Coverage and consistency tests for the schema tables.

`schemas/fv_schemes.py` once spelled its keys ``"<key>.<parent>"`` while the
registry looked them up as ``"<parent>.<key>"``, so every entry in the module was
unreachable — 0% of the nodes in a real fvSchemes resolved. The unit tests of
the day passed anyway, because they asserted the internal table shape
(`schema_for_file_key(path, "default.ddtSchemes")`) rather than the call the UI
actually makes.

These tests close that gap: they walk real dictionaries exactly as
`DetailPanel` does and require a minimum share of nodes to resolve.
"""
from __future__ import annotations

import pathlib

import pytest

from foam.nodes import FoamNode
from foam.parser import OpenFoamParser
from schemas._base import FOUNDATION_SERIES
from schemas.registry import SchemaRegistry

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "schemas"

# Floors, not targets: they exist to catch a module going dark, so they sit
# below current coverage and should only ever be raised.
COVERAGE_FLOOR = {
    "fvSchemes": 0.90,
    "fvSolution": 0.85,
    "controlDict": 0.85,
    "blockMeshDict": 0.75,
    "snappyHexMeshDict": 0.75,
    "turbulenceProperties": 0.70,
    # The viscosity models, generated like turbulenceProperties and opening at
    # the same floor. Both fixtures currently resolve at 100%, so there is room
    # to raise these — deliberately, not by accident.
    "transportProperties": 0.70,
    "physicalProperties": 0.70,
}


@pytest.fixture
def registry(monkeypatch, tmp_path):
    """A registry using the built-in default modules, not the user's config."""
    monkeypatch.setattr("schemas.config_store.CONFIG_FILE", tmp_path / "absent.json")
    return SchemaRegistry()


def _walk(
    node: FoamNode,
    parent: str | None = None,
    grandparent: str | None = None,
):
    """Yield (node, parent_key, grandparent_key) the way DetailPanel sees them.

    `DetailPanel` reads `node.parent.name` and `node.parent.parent.name`; the
    FoamFile header is skipped because it carries no dictionary semantics.
    """
    for child in node.children or []:
        if child.name == "FoamFile":
            continue
        yield child, parent, grandparent
        yield from _walk(child, child.name, parent)


def _coverage(registry: SchemaRegistry, name: str) -> tuple[int, int, list[str]]:
    path = FIXTURES / name
    root = OpenFoamParser(path.read_text()).parse()
    hits = total = 0
    missed: list[str] = []
    for child, parent, grandparent in _walk(root):
        if not child.name:
            continue
        total += 1
        if registry.schema_for_file_key(str(path), child.name, parent, grandparent):
            hits += 1
        else:
            missed.append(f"{parent or '<root>'}/{child.name}")
    return hits, total, missed


@pytest.mark.parametrize("name", sorted(COVERAGE_FLOOR))
def test_fixture_coverage_meets_floor(registry, name):
    hits, total, missed = _coverage(registry, name)
    assert total > 0, f"{name} fixture parsed to nothing"
    ratio = hits / total
    assert ratio >= COVERAGE_FLOOR[name], (
        f"{name}: only {hits}/{total} ({ratio:.1%}) of nodes resolve to a schema, "
        f"below the {COVERAGE_FLOOR[name]:.0%} floor. Unresolved: {missed[:20]}"
    )


def test_fvschemes_default_resolves_through_its_category(registry):
    """The exact shape that was broken: `ddtSchemes { default Euler; }`."""
    path = str(FIXTURES / "fvSchemes")
    for category in ("ddtSchemes", "gradSchemes", "divSchemes", "laplacianSchemes"):
        schema = registry.schema_for_file_key(path, "default", category)
        assert schema is not None, f"{category}/default does not resolve"
        assert schema.choices, f"{category}/default offers no values to choose from"


def test_wildcard_answers_for_per_term_entries(registry):
    """Per-field div terms are named after the case and cannot be enumerated."""
    path = str(FIXTURES / "fvSchemes")
    assert registry.schema_for_file_key(path, "div(phi,U)", "divSchemes") is not None
    assert registry.schema_for_file_key(path, "div(phi,epsilon)", "divSchemes") is not None


# ── table consistency ─────────────────────────────────────────────────────────

def _all_tables(registry: SchemaRegistry) -> dict[str, dict]:
    return registry._file_key_schemas


def test_dotted_key_suffix_matches_schema_key(registry):
    """A qualified key's suffix must be the key it describes.

    This is the invariant the dead fv_schemes module violated: it declared
    ``"default.ddtSchemes"`` with ``key="default.ddtSchemes"``, when the table
    key means ``"<parent>.<key>"`` and so should have been ``"ddtSchemes.default"``
    with ``key="default"``.
    """
    wrong = []
    for file_name, table in _all_tables(registry).items():
        for table_key, schema in table.items():
            if "." not in table_key:
                if schema.key != table_key:
                    wrong.append(f"{file_name}: {table_key!r} has key={schema.key!r}")
                continue
            _, suffix = table_key.split(".", 1)
            if suffix != schema.key:
                wrong.append(f"{file_name}: {table_key!r} has key={schema.key!r}, expected {suffix!r}")
    assert not wrong, "schema keys inconsistent with their table keys:\n" + "\n".join(wrong)


def test_provenance_targets_exist(registry):
    """A rename or warning must point at a key that is actually documented."""
    dangling = []
    for file_name, table in _all_tables(registry).items():
        known = {k.split(".", 1)[1] if "." in k else k for k in table}
        for table_key, schema in table.items():
            if schema.status == "valid":
                continue
            assert schema.use_instead, f"{file_name}: {table_key} is {schema.status} but names no replacement"
            if schema.use_instead not in known:
                dangling.append(f"{file_name}: {table_key} -> {schema.use_instead}")
    assert not dangling, "provenance points at undocumented keys:\n" + "\n".join(dangling)


def test_renamed_from_is_documented_as_its_own_entry(registry):
    """An old name listed on a current key should itself be findable."""
    for file_name, table in _all_tables(registry).items():
        known = {k.split(".", 1)[1] if "." in k else k for k in table}
        for schema in table.values():
            for old in schema.renamed_from:
                assert old in known, (
                    f"{file_name}: {schema.key} claims former name {old!r}, which has no entry"
                )


# ── the ineffective category ──────────────────────────────────────────────────

def test_min_flatness_is_flagged_in_a_real_tutorial(registry):
    """motorBike ships `minFlatness`, which no OpenFOAM reader consumes."""
    path = str(FIXTURES / "snappyHexMeshDict")
    schema = registry.schema_for_file_key(path, "minFlatness", "meshQualityControls")
    assert schema is not None, "minFlatness is in the fixture but has no schema"
    assert schema.status == "ineffective"
    assert schema.use_instead == "minFaceFlatness"


def test_min_face_flatness_is_the_documented_key(registry):
    path = str(FIXTURES / "snappyHexMeshDict")
    schema = registry.schema_for_file_key(path, "minFaceFlatness", "meshQualityControls")
    assert schema is not None
    assert schema.status == "valid"


def test_renamed_key_carries_its_successor_and_version(registry):
    path = str(FIXTURES / "snappyHexMeshDict")
    schema = registry.schema_for_file_key(path, "minMedianAxisAngle", "addLayersControls")
    assert schema is not None
    assert schema.status == "renamed"
    assert schema.use_instead == "minMedialAxisAngle"
    assert schema.deprecated_since


# ── version tagging ───────────────────────────────────────────────────────────

# Keys verified present in every Foundation release from v7 to dev and in
# OpenCFD v2106-v2606, by scanning the source trees. Tagging one of these with a
# single release tells the user it is unavailable to them, which is how the
# hand-written modules once claimed 61 shared finiteVolume/lduMatrix keys were
# Foundation-only.
_LONG_STANDING = [
    ("snappyHexMeshDict", "castellatedMesh", None),
    ("snappyHexMeshDict", "snap", None),
    ("snappyHexMeshDict", "addLayers", None),
    ("snappyHexMeshDict", "mergeTolerance", None),
    ("snappyHexMeshDict", "nSurfaceLayers", "layers"),
    ("snappyHexMeshDict", "maxNonOrtho", "meshQualityControls"),
    ("fvSchemes", "default", "ddtSchemes"),
    ("fvSolution", "solver", "solvers"),
    ("controlDict", "writeControl", None),
    ("blockMeshDict", "scale", None),
]


@pytest.mark.parametrize(("file_name", "key", "parent"), _LONG_STANDING)
def test_long_standing_keys_are_not_tagged_to_one_release(registry, file_name, key, parent):
    path = str(FIXTURES / file_name) if (FIXTURES / file_name).exists() else f"/case/{file_name}"
    schema = registry.schema_for_file_key(path, key, parent)
    assert schema is not None, f"{file_name}: {key} has no schema"
    tags = schema.supported_in
    text = ", ".join(tags)

    foundation = [t for t in tags if t.startswith("Foundation")]
    opencfd = [t for t in tags if t.startswith("OpenCFD")]
    assert foundation, f"{file_name}: {key} claims no Foundation support ({text})"
    assert opencfd, f"{file_name}: {key} claims no OpenCFD support ({text})"

    # The bug this guards was not a *missing* fork but a too-narrow one:
    # `("Foundation v13", "OpenCFD v2106-v2606")` names both forks and still
    # tells a Foundation v11 user the key is unavailable. These keys span the
    # whole range, so they must carry the collective label.
    assert FOUNDATION_SERIES in foundation, (
        f"{file_name}: {key} is tagged {text!r}, naming specific Foundation "
        f"release(s); it has existed since v7, so it should use FOUNDATION_SERIES"
    )


def test_switch_choices_are_not_fork_specific(registry):
    """yes/no/on/off are Switch spellings, accepted by both forks alike."""
    path = str(FIXTURES / "snappyHexMeshDict")
    for value in ("true", "false", "yes", "no", "on", "off"):
        text = registry.choice_supported_in_for_value(path, "castellatedMesh", value)
        assert "Foundation" in text and "OpenCFD" in text, (
            f"switch value {value!r} is tagged {text!r}"
        )


def test_no_invalid_merge_type_value(registry):
    """`merge` was never a valid mergeType; the enum is topology/points."""
    values = registry.choices_for_file_key(str(FIXTURES / "blockMeshDict"), "mergeType")
    assert "merge" not in values
    assert {"topology", "points"} <= set(values)
