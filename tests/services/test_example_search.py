# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for example_search: finding example usages in an OpenFOAM installation."""
from __future__ import annotations

from pathlib import Path

import pytest

from services.example_search import (
    SOURCE_CASEDICTS,
    SOURCE_TUTORIALS,
    FoamInstallation,
    case_root_for,
    discover_installations,
    installation_from_dir,
    search_examples,
)

_CONTROL_DICT = """\
application     simpleFoam;
startFrom       startTime;

functions
{
    #includeFunc mag
}
"""

_FV_SCHEMES = """\
ddtSchemes
{
    default         steadyState;
}
"""

_MAG_TEMPLATE = """\
type            mag;
libs            (fieldFunctionObjects);
field           U;
"""


@pytest.fixture
def fake_install(tmp_path: Path) -> Path:
    """A minimal OpenFOAM installation: one tutorial case + caseDicts templates."""
    root = tmp_path / "openfoam9999"
    case = root / "tutorials" / "incompressible" / "simpleFoam" / "pitzDaily"
    (case / "system").mkdir(parents=True)
    (case / "0").mkdir()
    (case / "system" / "controlDict").write_text(_CONTROL_DICT)
    (case / "system" / "fvSchemes").write_text(_FV_SCHEMES)
    (case / "0" / "U").write_text("internalField   uniform (0 0 0);\n")
    fields = root / "etc" / "caseDicts" / "postProcessing" / "fields"
    fields.mkdir(parents=True)
    (fields / "mag").write_text(_MAG_TEMPLATE)
    annotated = root / "etc" / "caseDicts" / "annotated"
    annotated.mkdir()
    (annotated / "fvSolution").write_text("solvers\n{\n}\n")
    return root


@pytest.fixture
def installation(fake_install: Path) -> FoamInstallation:
    inst = installation_from_dir(fake_install)
    assert inst is not None
    return inst


class TestInstallationFromDir:
    def test_install_root(self, fake_install: Path) -> None:
        inst = installation_from_dir(fake_install)
        assert inst is not None
        assert inst.label == "openfoam9999"
        assert inst.tutorials_dir == fake_install / "tutorials"
        assert inst.casedicts_dir == fake_install / "etc" / "caseDicts"

    def test_bare_tutorials_dir(self, fake_install: Path) -> None:
        inst = installation_from_dir(fake_install / "tutorials")
        assert inst is not None
        assert inst.tutorials_dir == fake_install / "tutorials"
        assert inst.casedicts_dir is None

    def test_non_install_dir(self, tmp_path: Path) -> None:
        (tmp_path / "empty").mkdir()
        assert installation_from_dir(tmp_path / "empty") is None

    def test_missing_dir(self, tmp_path: Path) -> None:
        assert installation_from_dir(tmp_path / "nope") is None

    def test_custom_label(self, fake_install: Path) -> None:
        inst = installation_from_dir(fake_install, label="custom")
        assert inst is not None
        assert inst.label == "custom"


class TestDiscoverInstallations:
    def test_env_project_dir(self, fake_install: Path) -> None:
        found = discover_installations(env={"WM_PROJECT_DIR": str(fake_install)})
        assert [i.root for i in found[:1]] == [fake_install]
        assert found[0].label == "openfoam9999 (environment)"
        assert found[0].tutorials_dir == fake_install / "tutorials"
        assert found[0].casedicts_dir == fake_install / "etc" / "caseDicts"

    def test_env_foam_tutorials_only(self, fake_install: Path) -> None:
        found = discover_installations(
            env={"FOAM_TUTORIALS": str(fake_install / "tutorials")}
        )
        assert found[0].tutorials_dir == fake_install / "tutorials"
        assert found[0].casedicts_dir is None
        assert found[0].label == "(environment)"

    def test_extra_roots_first(self, fake_install: Path) -> None:
        found = discover_installations(env={}, extra_roots=[str(fake_install)])
        assert found[0].root == fake_install

    def test_dedupe_extra_root_and_env(self, fake_install: Path) -> None:
        found = discover_installations(
            env={"WM_PROJECT_DIR": str(fake_install)},
            extra_roots=[str(fake_install)],
        )
        assert sum(1 for i in found if i.root == fake_install) == 1
        # extra_roots entry wins (added first)
        assert found[0].label == "openfoam9999"

    def test_empty_extra_root_ignored(self, fake_install: Path) -> None:
        found = discover_installations(env={}, extra_roots=[""])
        assert all(i.root != Path("") for i in found)


class TestCaseRootFor:
    def test_walks_up_to_case(self, installation: FoamInstallation) -> None:
        tutorials = installation.tutorials_dir
        assert tutorials is not None
        case = tutorials / "incompressible" / "simpleFoam" / "pitzDaily"
        assert case_root_for(case / "0" / "U", tutorials) == case
        assert case_root_for(case / "system" / "controlDict", tutorials) == case

    def test_none_outside_stop(self, installation: FoamInstallation, tmp_path: Path) -> None:
        tutorials = installation.tutorials_dir
        assert tutorials is not None
        assert case_root_for(tmp_path / "elsewhere", tutorials) is None

    def test_none_when_no_case_above(self, installation: FoamInstallation) -> None:
        tutorials = installation.tutorials_dir
        assert tutorials is not None
        assert case_root_for(tutorials / "incompressible", tutorials) is None


class TestSearchExamples:
    def test_hits_in_both_sources(self, installation: FoamInstallation) -> None:
        hits = search_examples(installation, "mag")
        sources = {h.source for h in hits}
        assert sources == {SOURCE_TUTORIALS, SOURCE_CASEDICTS}
        tut = next(h for h in hits if h.source == SOURCE_TUTORIALS)
        assert tut.file.name == "controlDict"
        assert tut.case_root is not None
        assert tut.case_root.name == "pitzDaily"
        assert tut.rel_label == "incompressible/simpleFoam/pitzDaily/system/controlDict"
        assert tut.line_numbers == (6,)
        assert tut.snippet == "#includeFunc mag"
        tmpl = next(h for h in hits if h.source == SOURCE_CASEDICTS)
        assert tmpl.file.name == "mag"
        assert tmpl.case_root is None
        assert tmpl.rel_label == "postProcessing/fields/mag"

    def test_case_insensitive(self, installation: FoamInstallation) -> None:
        hits = search_examples(installation, "SIMPLEFOAM")
        assert any(h.file.name == "controlDict" for h in hits)

    def test_file_name_filter(self, installation: FoamInstallation) -> None:
        hits = search_examples(installation, "default", file_name="fvSchemes")
        assert [h.file.name for h in hits] == ["fvSchemes"]

    def test_sources_filter(self, installation: FoamInstallation) -> None:
        hits = search_examples(installation, "mag", sources=(SOURCE_CASEDICTS,))
        assert {h.source for h in hits} == {SOURCE_CASEDICTS}

    def test_max_hits(self, installation: FoamInstallation) -> None:
        hits = search_examples(installation, "e", max_hits=2)
        assert len(hits) == 2

    def test_cancelled_stops_scan(self, installation: FoamInstallation) -> None:
        hits = search_examples(installation, "mag", cancelled=lambda: True)
        assert hits == []

    def test_blank_query_raises(self, installation: FoamInstallation) -> None:
        with pytest.raises(ValueError):
            search_examples(installation, "   ")

    def test_binary_file_skipped(self, installation: FoamInstallation) -> None:
        tutorials = installation.tutorials_dir
        assert tutorials is not None
        (tutorials / "binaryFile").write_bytes(b"mag\x00mag")
        hits = search_examples(installation, "mag", sources=(SOURCE_TUTORIALS,))
        assert all(h.file.name != "binaryFile" for h in hits)

    def test_oversize_file_skipped(self, installation: FoamInstallation) -> None:
        tutorials = installation.tutorials_dir
        assert tutorials is not None
        (tutorials / "hugeFile").write_text("mag\n" + "x" * (2 * 1024 * 1024 + 1))
        hits = search_examples(installation, "mag", sources=(SOURCE_TUTORIALS,))
        assert all(h.file.name != "hugeFile" for h in hits)

    def test_line_numbers_capped(self, installation: FoamInstallation) -> None:
        tutorials = installation.tutorials_dir
        assert tutorials is not None
        (tutorials / "manyMatches").write_text("mag\n" * 100)
        hits = search_examples(installation, "mag", sources=(SOURCE_TUTORIALS,))
        many = next(h for h in hits if h.file.name == "manyMatches")
        assert len(many.line_numbers) == 50

    def test_progress_called(self, installation: FoamInstallation) -> None:
        tutorials = installation.tutorials_dir
        assert tutorials is not None
        for i in range(250):
            (tutorials / f"file{i:03d}").write_text("nothing here\n")
        messages: list[str] = []
        search_examples(
            installation, "mag", sources=(SOURCE_TUTORIALS,), progress=messages.append
        )
        assert messages
