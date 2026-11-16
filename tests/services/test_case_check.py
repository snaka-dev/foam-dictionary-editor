# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for services/case_check.py (Tools > Check Case…).

Each check has a case that triggers it -- modelled on a broken cavity whose
real icoFoam/decomposePar error was captured -- and the cases that must *not*
trigger it, which matter more: a false alarm is worse than silence. The
whole-tutorial-tree guard is tests/services/test_case_check_corpus.py.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from services import case_check as cc

HEADER = "FoamFile {{ version 2.0; format ascii; class {cls}; object {obj}; }}\n"

CONTROL = """\
application     icoFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         0.5;
deltaT          0.005;
writeControl    timeStep;
writeInterval   20;
"""

BOUNDARY = """\
3
(
    movingWall
    {
        type            wall;
        inGroups        1(wall);
        nFaces          20;
        startFace       760;
    }
    fixedWalls
    {
        type            wall;
        inGroups        List<word> 1(wall);
        nFaces          60;
        startFace       780;
    }
    frontAndBack
    {
        type            empty;
        inGroups        1(empty);
        nFaces          800;
        startFace       840;
    }
)
"""

U_BF = """\
    movingWall   { type fixedValue; value uniform (1 0 0); }
    fixedWalls   { type noSlip; }
    frontAndBack { type empty; }
"""

P_BF = """\
    movingWall   { type zeroGradient; }
    fixedWalls   { type zeroGradient; }
    frontAndBack { type empty; }
"""


WALLS_P = "    movingWall   { type zeroGradient; }\n    fixedWalls   { type zeroGradient; }\n"
MOVING_WALL_P = "    movingWall   { type zeroGradient; }\n"
FRONT_AND_BACK = "    frontAndBack { type empty; }\n"
SET_CONSTRAINT_TYPES = '    #includeEtc "caseDicts/setConstraintTypes"\n'


def patch_type(name: str) -> str:
    """A boundary-file patch's type and group lines, as BOUNDARY spells them."""
    return f"type            {name};\n        inGroups        1({name});"


def field(name: str, cls: str, bf: str, internal: str = "uniform 0", extra: str = "") -> str:
    return (
        HEADER.format(cls=cls, obj=name)
        + extra
        + f"dimensions [0 0 0 0 0 0 0];\ninternalField {internal};\n"
        + "boundaryField\n{\n" + bf + "}\n"
    )


def header(cls: str, obj: str) -> str:
    return HEADER.format(cls=cls, obj=obj)


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


@pytest.fixture
def cavity(tmp_path: Path) -> Path:
    """A meshed, correct icoFoam cavity."""
    case = tmp_path / "cavity"
    write(case / "system" / "controlDict", header("dictionary", "controlDict") + CONTROL)
    write(case / "constant" / "polyMesh" / "boundary", header("polyBoundaryMesh", "boundary") + BOUNDARY)
    write(case / "constant" / "transportProperties", "nu 0.01;\n")
    write(case / "0" / "U", field("U", "volVectorField", U_BF, "uniform (0 0 0)"))
    write(case / "0" / "p", field("p", "volScalarField", P_BF))
    return case


def codes(result: cc.CaseCheck) -> list[str]:
    return [f.code for f in result.findings]


def edit(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    assert old in text
    path.write_text(text.replace(old, new))


def test_correct_case_has_no_findings(cavity: Path):
    result = cc.check_case(str(cavity))
    assert result.findings == ()
    assert result.skipped == ()


def test_no_control_dict(cavity: Path):
    (cavity / "system" / "controlDict").unlink()
    assert codes(cc.check_case(str(cavity))) == [cc.NO_CONTROL_DICT]


# ── 0/ ───────────────────────────────────────────────────────────────────────

class TestStartDir:
    def test_zero_dir_kept_in_orig(self, cavity: Path):
        (cavity / "0").rename(cavity / "0.orig")
        result = cc.check_case(str(cavity))
        assert codes(result) == [cc.NO_START_DIR]
        assert result.findings[0].path == "0.orig"

    def test_no_time_dir_and_no_orig_is_not_reported(self, cavity: Path):
        # chemFoam and mesh-only demos have neither; not a mistake.
        for f in (cavity / "0").iterdir():
            f.unlink()
        (cavity / "0").rmdir()
        assert codes(cc.check_case(str(cavity))) == []

    def test_latest_time_checks_the_latest_dir(self, cavity: Path):
        edit(cavity / "system" / "controlDict", "startFrom       startTime", "startFrom latestTime")
        edit(cavity / "system" / "controlDict", "endTime         0.5", "endTime 1")
        write(cavity / "0.5" / "p", field("p", "volScalarField", "    movingWall { type zeroGradient; }\n"))
        result = cc.check_case(str(cavity))
        assert codes(result) == [cc.MISSING_PATCH_ENTRY]
        assert result.findings[0].path == os.path.join("0.5", "p")


# ── boundary coverage ────────────────────────────────────────────────────────

class TestBoundaryCoverage:
    def test_misspelt_patch(self, cavity: Path):
        edit(cavity / "0" / "U", "movingWall", "movingwall")
        result = cc.check_case(str(cavity))
        assert codes(result) == [cc.MISSING_PATCH_ENTRY, cc.UNMATCHED_PATCH_ENTRY]
        missing, stray = result.findings
        assert missing.args == {"field": "U", "patches": "movingWall"}
        assert missing.path == os.path.join("0", "U")
        assert missing.line > 0
        assert stray.args["entries"] == "movingwall"

    def test_unmatched_entry_alone_is_not_reported(self, cavity: Path):
        # OpenFOAM ignores an entry for a patch that does not exist.
        stray = "frontAndBack { type empty; }\n    inlet { type zeroGradient; }"
        edit(cavity / "0" / "p", "frontAndBack { type empty; }", stray)
        assert codes(cc.check_case(str(cavity))) == []

    def test_regex_key_covers(self, cavity: Path):
        edit(cavity / "0" / "p", WALLS_P,
             '    ".*Wall.*" { type zeroGradient; }\n')
        assert codes(cc.check_case(str(cavity))) == []

    def test_group_key_covers(self, cavity: Path):
        edit(cavity / "0" / "p", WALLS_P,
             "    wall { type zeroGradient; }\n")
        assert codes(cc.check_case(str(cavity))) == []

    def test_empty_patch_needs_no_entry(self, cavity: Path):
        # Both forks fill an empty patch in when its entry is absent.
        edit(cavity / "0" / "p", FRONT_AND_BACK, "")
        assert codes(cc.check_case(str(cavity))) == []

    def test_set_constraint_types_resolved(self, cavity: Path, tmp_path: Path):
        etc = tmp_path / "etc"
        write(etc / "caseDicts" / "setConstraintTypes", "empty { type empty; }\ncyclic { type cyclic; }\n")
        edit(cavity / "constant" / "polyMesh" / "boundary", patch_type("empty"),
             patch_type("symmetryPlane"))
        write(etc / "caseDicts" / "setConstraintTypes", "symmetryPlane { type symmetryPlane; }\n")
        for name in ("U", "p"):
            edit(cavity / "0" / name, FRONT_AND_BACK, SET_CONSTRAINT_TYPES)
        assert codes(cc.check_case(str(cavity), etc_dirs=[str(etc)])) == []

    def test_set_constraint_types_without_installation(self, cavity: Path):
        edit(cavity / "constant" / "polyMesh" / "boundary", patch_type("empty"),
             patch_type("symmetryPlane"))
        for name in ("U", "p"):
            edit(cavity / "0" / name, FRONT_AND_BACK, SET_CONSTRAINT_TYPES)
        assert codes(cc.check_case(str(cavity), etc_dirs=[])) == []

    def test_include_in_boundary_field_is_followed(self, cavity: Path):
        write(cavity / "0" / "include" / "walls", "movingWall { type zeroGradient; }\n")
        edit(cavity / "0" / "p", MOVING_WALL_P, '    #include "include/walls"\n')
        assert codes(cc.check_case(str(cavity))) == []
        edit(cavity / "0" / "include" / "walls", "movingWall", "fixedWalls")
        assert codes(cc.check_case(str(cavity))) == [cc.MISSING_PATCH_ENTRY]

    def test_unresolvable_include_skips_the_field(self, cavity: Path):
        edit(cavity / "0" / "p", MOVING_WALL_P, '    #include "nowhere"\n')
        result = cc.check_case(str(cavity))
        assert codes(result) == []
        assert [s.code for s in result.skipped] == [cc.SKIP_FIELD_UNREADABLE]

    def test_macro_splice_skips_the_field(self, cavity: Path):
        edit(cavity / "0" / "p", MOVING_WALL_P, "    $:walls;\n")
        result = cc.check_case(str(cavity))
        assert codes(result) == []
        assert [s.code for s in result.skipped] == [cc.SKIP_FIELD_UNREADABLE]

    def test_bad_regex_skips_the_field(self, cavity: Path):
        edit(cavity / "0" / "p", MOVING_WALL_P, '    "(movingWall" { type zeroGradient; }\n')
        assert codes(cc.check_case(str(cavity))) == []

    def test_large_nonuniform_internal_field(self, cavity: Path):
        values = "\n".join("(0 0 0)" for _ in range(20000))
        internal = f"nonuniform List<vector> 20000\n(\n{values}\n)"
        write(cavity / "0" / "U", field("U", "volVectorField", U_BF, internal))
        assert codes(cc.check_case(str(cavity))) == []
        edit(cavity / "0" / "U", "fixedWalls   { type noSlip; }", "")
        assert codes(cc.check_case(str(cavity))) == [cc.MISSING_PATCH_ENTRY]

    def test_non_field_files_are_ignored(self, cavity: Path):
        write(cavity / "0" / "notes", "boundaryField { }\n")
        write(cavity / "0" / "p.orig", field("p", "volScalarField", ""))
        assert codes(cc.check_case(str(cavity))) == []

    def test_binary_field_is_not_read(self, cavity: Path):
        text = field("p", "volScalarField", "").replace("format ascii", "format binary")
        write(cavity / "0" / "p", text)
        assert codes(cc.check_case(str(cavity))) == []

    def test_optionally_read_motion_field(self, cavity: Path):
        write(cavity / "0" / "cellDisplacement", field("cellDisplacement", "volVectorField", ""))
        assert codes(cc.check_case(str(cavity))) == []

    def test_unsaved_buffer_counts(self, cavity: Path):
        path = str(cavity / "0" / "U")
        broken = (cavity / "0" / "U").read_text().replace("movingWall", "lid")
        result = cc.check_case(str(cavity), read_text=lambda p: broken if p == path else None)
        assert cc.MISSING_PATCH_ENTRY in codes(result)


class TestConstraintTypes:
    def test_empty_patch_given_another_type(self, cavity: Path):
        edit(cavity / "0" / "p", "frontAndBack { type empty; }", "frontAndBack { type zeroGradient; }")
        result = cc.check_case(str(cavity))
        assert codes(result) == [cc.CONSTRAINT_MISMATCH]
        assert result.findings[0].args == {
            "field": "p", "patch": "frontAndBack", "patch_type": "empty", "field_type": "zeroGradient",
        }

    def test_empty_field_on_a_wall_patch(self, cavity: Path):
        edit(cavity / "constant" / "polyMesh" / "boundary", patch_type("empty"),
             patch_type("wall"))
        result = cc.check_case(str(cavity))
        assert codes(result) == [cc.CONSTRAINT_MISMATCH, cc.CONSTRAINT_MISMATCH]

    def test_patch_type_override_is_accepted(self, cavity: Path):
        override = "frontAndBack { type zeroGradient; patchType empty; }"
        edit(cavity / "0" / "p", "frontAndBack { type empty; }", override)
        assert codes(cc.check_case(str(cavity))) == []

    def test_unknown_field_type_is_not_judged(self, cavity: Path):
        edit(cavity / "0" / "p", "frontAndBack { type empty; }", "frontAndBack { type myCustomBC; }")
        assert codes(cc.check_case(str(cavity))) == []

    def test_point_fields_are_not_judged(self, cavity: Path):
        # pointPatchField::New substitutes the constraint type silently.
        write(cavity / "0" / "pointDisplacement", field(
            "pointDisplacement", "pointVectorField",
            "    movingWall { type fixedValue; value uniform (0 0 0); }\n"
            "    fixedWalls { type fixedValue; value uniform (0 0 0); }\n"
            "    frontAndBack { type fixedValue; value uniform (0 0 0); }\n",
        ))
        assert codes(cc.check_case(str(cavity))) == []


# ── before meshing ───────────────────────────────────────────────────────────

FIXED_WALLS_BM = "    fixedWalls { type wall; faces ((0 4 7 3) (2 6 5 1) (1 5 4 0)); }\n"

BLOCK_MESH = """\
vertices ((0 0 0) (1 0 0) (1 1 0) (0 1 0) (0 0 0.1) (1 0 0.1) (1 1 0.1) (0 1 0.1));
blocks (hex (0 1 2 3 4 5 6 7) (20 20 1) simpleGrading (1 1 1));
boundary
(
    movingWall { type wall; faces ((3 7 6 2)); }
    fixedWalls { type wall; faces ((0 4 7 3) (2 6 5 1) (1 5 4 0)); }
    frontAndBack { type empty; faces ((0 3 2 1) (4 5 6 7)); }
);
"""


@pytest.fixture
def unmeshed(cavity: Path) -> Path:
    for f in (cavity / "constant" / "polyMesh").iterdir():
        f.unlink()
    (cavity / "constant" / "polyMesh").rmdir()
    write(cavity / "system" / "blockMeshDict", header("dictionary", "blockMeshDict") + BLOCK_MESH)
    return cavity


class TestBeforeMeshing:
    def test_patches_come_from_block_mesh_dict(self, unmeshed: Path):
        assert codes(cc.check_case(str(unmeshed))) == []
        edit(unmeshed / "0" / "U", "movingWall", "lid")
        assert cc.MISSING_PATCH_ENTRY in codes(cc.check_case(str(unmeshed)))

    def test_wall_patches_are_in_the_wall_group(self, unmeshed: Path):
        edit(unmeshed / "0" / "p", WALLS_P,
             "    wall { type zeroGradient; }\n")
        assert codes(cc.check_case(str(unmeshed))) == []

    def test_default_faces_patch(self, unmeshed: Path):
        # fixedWalls' faces left out -> blockMesh's defaultFaces, type empty
        # unless defaultPatch says otherwise.
        edit(unmeshed / "system" / "blockMeshDict", FIXED_WALLS_BM, "")
        for name in ("U", "p"):
            edit(unmeshed / "0" / name, "fixedWalls", "defaultFaces")
        result = cc.check_case(str(unmeshed))
        assert codes(result) == [cc.CONSTRAINT_MISMATCH, cc.CONSTRAINT_MISMATCH]
        default = "defaultPatch { name defaultFaces; type wall; }\nboundary"
        edit(unmeshed / "system" / "blockMeshDict", "boundary", default)
        assert codes(cc.check_case(str(unmeshed))) == []

    def test_declared_default_faces_keeps_its_type(self, unmeshed: Path):
        # TJunction: `defaultFaces { type wall; faces (); }` takes the leftovers.
        edit(unmeshed / "system" / "blockMeshDict", FIXED_WALLS_BM,
             "    defaultFaces { type wall; faces (); }\n")
        for name in ("U", "p"):
            edit(unmeshed / "0" / name, "fixedWalls", "defaultFaces")
        assert codes(cc.check_case(str(unmeshed))) == []

    @pytest.mark.parametrize("marker", [
        ("system/snappyHexMeshDict", "castellatedMesh true;\n"),
        ("system/createPatchDict", "patches ();\n"),
        ("Allrun", "#!/bin/sh\nrunApplication blockMesh\nrunApplication extrudeMesh\n"),
    ])
    def test_reshaped_mesh_is_not_inferred(self, unmeshed: Path, marker):
        write(unmeshed / marker[0], marker[1])
        edit(unmeshed / "0" / "U", "movingWall", "lid")
        result = cc.check_case(str(unmeshed))
        assert codes(result) == []
        assert [s.code for s in result.skipped] == [cc.SKIP_NO_MESH]

    def test_commented_utility_in_allrun_does_not_count(self, unmeshed: Path):
        write(unmeshed / "Allrun", "#!/bin/sh\nrunApplication blockMesh\n# runApplication snappyHexMesh\n")
        assert codes(cc.check_case(str(unmeshed))) == []

    def test_merge_patch_pairs_is_not_inferred(self, unmeshed: Path):
        merge = "mergePatchPairs ((movingWall fixedWalls));\nboundary"
        edit(unmeshed / "system" / "blockMeshDict", "boundary", merge)
        edit(unmeshed / "0" / "U", "movingWall", "lid")
        assert codes(cc.check_case(str(unmeshed))) == []

    def test_empty_merge_patch_pairs_is_fine(self, unmeshed: Path):
        edit(unmeshed / "system" / "blockMeshDict", "boundary", "mergePatchPairs\n(\n);\nboundary")
        edit(unmeshed / "0" / "U", "movingWall", "lid")
        assert cc.MISSING_PATCH_ENTRY in codes(cc.check_case(str(unmeshed)))


def test_multi_region_before_splitting(cavity: Path):
    write(cavity / "constant" / "regionProperties", "regions (fluid (air) solid (wall));\n")
    write(cavity / "0" / "air" / "U", field("U", "volVectorField", ""))
    result = cc.check_case(str(cavity))
    assert codes(result) == []
    assert [s.code for s in result.skipped] == [cc.SKIP_REGIONS_PREMESH]


def test_multi_region_meshed(cavity: Path):
    write(cavity / "constant" / "regionProperties", "regions (fluid (air));\n")
    write(cavity / "constant" / "air" / "polyMesh" / "boundary",
          header("polyBoundaryMesh", "boundary")
          + "1\n(\n    outer { type wall; nFaces 1; startFace 0; }\n)\n")
    write(cavity / "0" / "air" / "T", field("T", "volScalarField", "    inner { type zeroGradient; }\n"))
    result = cc.check_case(str(cavity))
    assert codes(result) == [cc.MISSING_PATCH_ENTRY, cc.UNMATCHED_PATCH_ENTRY]
    assert result.findings[0].path == os.path.join("0", "air", "T")


# ── controlDict ──────────────────────────────────────────────────────────────

class TestControlDict:
    def control(self, case: Path, old: str, new: str) -> list[str]:
        edit(case / "system" / "controlDict", old, new)
        return codes(cc.check_case(str(case)))

    def test_write_interval_in_steps(self, cavity: Path):
        assert self.control(cavity, "writeInterval   20", "writeInterval 150") == [cc.NOTHING_WRITTEN]

    def test_write_interval_equal_to_run_writes(self, cavity: Path):
        # 0.5 / 0.005 = 100 steps: the end time itself is written.
        assert self.control(cavity, "writeInterval   20", "writeInterval 100") == []

    def test_write_interval_in_run_time(self, cavity: Path):
        edit(cavity / "system" / "controlDict", "writeControl    timeStep", "writeControl runTime")
        assert self.control(cavity, "writeInterval   20", "writeInterval 1") == [cc.NOTHING_WRITTEN]

    def test_huge_interval_is_deliberate(self, cavity: Path):
        assert self.control(cavity, "writeInterval   20", "writeInterval 100000") == []

    def test_write_interval_from_macro(self, cavity: Path):
        edit(cavity / "system" / "controlDict", "application", "steps 150;\napplication")
        assert self.control(cavity, "writeInterval   20", "writeInterval $steps") == [cc.NOTHING_WRITTEN]

    def test_adjustable_time_step_skips_the_step_count(self, cavity: Path):
        edit(cavity / "system" / "controlDict", "application", "adjustTimeStep yes;\napplication")
        assert self.control(cavity, "writeInterval   20", "writeInterval 150") == []

    def test_delta_t_longer_than_run(self, cavity: Path):
        assert self.control(cavity, "deltaT          0.005", "deltaT 0.7") == [cc.DELTA_T_EXCEEDS_RUN]

    def test_delta_t_equal_to_run_is_one_step(self, cavity: Path):
        edit(cavity / "system" / "controlDict", "writeInterval   20", "writeInterval 1")
        assert self.control(cavity, "deltaT          0.005", "deltaT 0.5") == []

    def test_already_at_end_time(self, cavity: Path):
        edit(cavity / "system" / "controlDict", "startFrom       startTime", "startFrom latestTime")
        write(cavity / "0.5" / "p", (cavity / "0" / "p").read_text())
        write(cavity / "0.5" / "U", (cavity / "0" / "U").read_text())
        assert codes(cc.check_case(str(cavity))) == [cc.ALREADY_AT_END]

    def test_end_time_zero_from_zero_is_a_demo(self, cavity: Path):
        assert self.control(cavity, "endTime         0.5", "endTime 0") == []

    @pytest.mark.parametrize("value", ["writeNow", "noWriteNow"])
    def test_stop_at_left(self, cavity: Path, value: str):
        assert self.control(cavity, "stopAt          endTime", f"stopAt {value}") == [cc.STOP_AT_LEFT]

    def test_stop_at_next_write_still_runs(self, cavity: Path):
        assert self.control(cavity, "stopAt          endTime", "stopAt nextWrite") == []


# ── decomposeParDict ─────────────────────────────────────────────────────────

class TestDecomposition:
    @pytest.mark.parametrize("coeffs", [
        "simpleCoeffs { n (2 1 1); }", "coeffs { n (2 1 1); }", "n (2 1 1);",
    ])
    def test_product_mismatch(self, cavity: Path, coeffs: str):
        write(cavity / "system" / "decomposeParDict", f"numberOfSubdomains 4;\nmethod simple;\n{coeffs}\n")
        result = cc.check_case(str(cavity))
        assert codes(result) == [cc.DECOMPOSITION_PRODUCT]
        assert result.findings[0].args["product"] == "2"

    def test_foundation_decomposer_keyword(self, cavity: Path):
        write(cavity / "system" / "decomposeParDict",
              "numberOfSubdomains 4;\ndecomposer hierarchical;\n"
              "hierarchicalCoeffs { n (2 1 1); order xyz; }\n")
        assert codes(cc.check_case(str(cavity))) == [cc.DECOMPOSITION_PRODUCT]

    def test_matching_product(self, cavity: Path):
        write(cavity / "system" / "decomposeParDict",
              "numberOfSubdomains 4;\nmethod simple;\ncoeffs { n (2 2 1); }\n")
        assert codes(cc.check_case(str(cavity))) == []

    def test_inactive_method_coeffs_are_ignored(self, cavity: Path):
        write(cavity / "system" / "decomposeParDict",
              "numberOfSubdomains 4;\nmethod scotch;\nsimpleCoeffs { n (2 1 1); }\n")
        assert codes(cc.check_case(str(cavity))) == []

    def test_processor_dirs_disagree(self, cavity: Path):
        write(cavity / "system" / "decomposeParDict", "numberOfSubdomains 4;\nmethod scotch;\n")
        (cavity / "processor0").mkdir()
        (cavity / "processor1").mkdir()
        result = cc.check_case(str(cavity))
        assert codes(result) == [cc.PROCESSOR_COUNT]
        assert result.findings[0].args == {"count": "4", "pieces": "2"}


# ── dictionaries ─────────────────────────────────────────────────────────────

def installation(tmp_path: Path, version: str) -> str:
    root = tmp_path / f"OpenFOAM-{version}"
    write(root / "etc" / "bashrc", f"export WM_PROJECT_VERSION={version}\n")
    return str(root)


class TestDictionaries:
    def test_installation_info(self, tmp_path: Path):
        assert cc.installation_info(installation(tmp_path, "v2606")) == cc.Installation("opencfd", 2606)
        assert cc.installation_info(installation(tmp_path, "12")) == cc.Installation("foundation", 12)
        assert cc.installation_info(installation(tmp_path, "dev")).version == float("inf")
        assert cc.installation_info(None) is None
        assert cc.installation_info(str(tmp_path / "nowhere")) is None

    def test_foundation_name_on_opencfd(self, cavity: Path, tmp_path: Path):
        (cavity / "constant" / "transportProperties").rename(cavity / "constant" / "physicalProperties")
        result = cc.check_case(str(cavity), installation=installation(tmp_path, "v2606"))
        assert codes(result) == [cc.OTHER_FORK_DICTIONARY]
        assert result.findings[0].args == {
            "have": "physicalProperties", "want": "transportProperties", "solver": "icoFoam",
        }

    def test_foundation_name_on_foundation_10(self, cavity: Path, tmp_path: Path):
        (cavity / "constant" / "transportProperties").rename(cavity / "constant" / "physicalProperties")
        assert codes(cc.check_case(str(cavity), installation=installation(tmp_path, "10"))) == []

    def test_foundation_name_before_it_existed(self, cavity: Path, tmp_path: Path):
        (cavity / "constant" / "transportProperties").rename(cavity / "constant" / "physicalProperties")
        result = cc.check_case(str(cavity), installation=installation(tmp_path, "9"))
        assert codes(result) == [cc.OTHER_FORK_DICTIONARY]

    def test_old_name_is_read_by_every_fork(self, cavity: Path, tmp_path: Path):
        # Foundation falls back to transportProperties (physicalProperties.C).
        assert codes(cc.check_case(str(cavity), installation=installation(tmp_path, "12"))) == []

    def test_missing_under_both_names(self, cavity: Path, tmp_path: Path):
        (cavity / "constant" / "transportProperties").unlink()
        write(cavity / "constant" / "g", "value (0 0 -9.81);\n")
        assert codes(cc.check_case(str(cavity))) == [cc.MISSING_DICTIONARY]
        result = cc.check_case(str(cavity), installation=installation(tmp_path, "12"))
        assert result.findings[0].args["name"] == "physicalProperties"

    def test_turbulence_for_simple_foam(self, cavity: Path, tmp_path: Path):
        edit(cavity / "system" / "controlDict", "icoFoam", "simpleFoam")
        result = cc.check_case(str(cavity), installation=installation(tmp_path, "v2606"))
        assert [f.args["name"] for f in result.findings] == ["turbulenceProperties"]
        write(cavity / "constant" / "momentumTransport", "simulationType laminar;\n")
        result = cc.check_case(str(cavity), installation=installation(tmp_path, "v2606"))
        assert codes(result) == [cc.OTHER_FORK_DICTIONARY]

    def test_foam_run_module(self, cavity: Path, tmp_path: Path):
        module = "application foamRun;\nsolver incompressibleFluid;"
        edit(cavity / "system" / "controlDict", "application     icoFoam;", module)
        result = cc.check_case(str(cavity), installation=installation(tmp_path, "12"))
        assert [f.args["name"] for f in result.findings] == ["momentumTransport"]

    def test_unlisted_solver_is_not_judged(self, cavity: Path):
        edit(cavity / "system" / "controlDict", "icoFoam", "rhoCentralFoam")
        (cavity / "constant" / "transportProperties").unlink()
        write(cavity / "constant" / "thermophysicalProperties", "x 1;\n")
        assert codes(cc.check_case(str(cavity))) == []

    def test_generated_from_a_template(self, cavity: Path):
        constant = cavity / "constant"
        (constant / "transportProperties").rename(constant / "transportProperties.template")
        assert codes(cc.check_case(str(cavity))) == []

    def test_meshing_demo_without_dictionaries(self, cavity: Path):
        (cavity / "constant" / "transportProperties").unlink()
        assert codes(cc.check_case(str(cavity))) == []


def test_read_boundary_patches_groups():
    patches = cc.read_boundary_patches(header("polyBoundaryMesh", "boundary") + BOUNDARY)
    assert patches is not None
    assert [(p.name, p.type) for p in patches] == [
        ("movingWall", "wall"), ("fixedWalls", "wall"), ("frontAndBack", "empty"),
    ]
    assert patches[1].groups == frozenset({"wall"})


def test_every_code_is_declared():
    assert {
        cc.NO_CONTROL_DICT, cc.NO_START_DIR, cc.MISSING_PATCH_ENTRY, cc.UNMATCHED_PATCH_ENTRY,
        cc.CONSTRAINT_MISMATCH, cc.NOTHING_WRITTEN, cc.DELTA_T_EXCEEDS_RUN, cc.ALREADY_AT_END,
        cc.STOP_AT_LEFT, cc.DECOMPOSITION_PRODUCT, cc.PROCESSOR_COUNT, cc.MISSING_DICTIONARY,
        cc.OTHER_FORK_DICTIONARY,
    } == cc.FINDING_CODES
