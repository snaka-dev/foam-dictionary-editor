# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for services/log_advice.py (View Log Summary's advice).

``tests/fixtures/logs/v2606/`` holds logs the installed OpenFOAM v2606 really
wrote, each for one deliberate break of a tutorial copy (mostly icoFoam
cavity; ``ras.log`` is simpleFoam pitzDaily, ``np.log`` a ``mpirun -np 2``
of a 4-way decomposition). The case path is replaced by ``{CASE}`` and the
host/date lines are dropped. The Foundation logs below are composed from the
Foundation-12 source (``dictionary.C``, ``IOerror.C``, ``fvPatchFieldNew.C``,
``RASModel.C``, ``argList.C``, …): no Foundation binaries were available to
run, so its wording is checked against the code that prints it.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from services import log_advice as la

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "logs" / "v2606"

CONTROL = """\
FoamFile { version 2.0; format ascii; class dictionary; object controlDict; }
application     icoFoam;
startFrom       startTime;
startTime       0;
endTime         0.5
deltaT          0.005;
writeControl    timeStep;
"""


@pytest.fixture
def case(tmp_path: Path) -> Path:
    """A case holding the files the fixture logs refer to."""
    for rel in ("0/U", "0/p", "system/fvSchemes", "system/fvSolution", "system/decomposeParDict",
                "constant/transportProperties", "constant/turbulenceProperties"):
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("// placeholder\n")
    (tmp_path / "system" / "controlDict").write_text(CONTROL)
    return tmp_path


def run(name: str, case: Path) -> list[la.Advice]:
    text = (FIXTURES / f"{name}.log").read_text().replace("{CASE}", str(case))
    return la.advise(text, str(case))


def rel(advice: la.Advice, case: Path) -> str:
    return os.path.relpath(advice.path, case) if advice.path else ""


@pytest.mark.parametrize("name, code, args, path, line", [
    ("missingpatch", la.MISSING_PATCH_ENTRY, {"patch": "movingWall", "field": "U"}, "0/U", 25),
    ("unknownbc", la.UNKNOWN_NAME, {"what": "patchField", "name": "noSlp", "suggestion": "noSlip"},
     "0/U", 31),
    ("scheme", la.UNKNOWN_NAME, {"what": "discretisation", "name": "lineer", "suggestion": "linear"},
     "system/fvSchemes", 31),
    ("linsolver", la.UNKNOWN_NAME, {"what": "symmetric matrix solver", "name": "PCGG", "suggestion": "PCG"},
     "system/fvSolution", 21),
    ("ras", la.UNKNOWN_NAME, {"what": "RAS model", "name": "kEpsilonn", "suggestion": "kEpsilon"},
     "constant/turbulenceProperties", 23),
    ("constraint", la.CONSTRAINT_MISMATCH,
     {"patch_type": "empty", "field_type": "zeroGradient", "field": "p"}, "0/p", 35),
    ("wallempty", la.CONSTRAINT_MISMATCH,
     {"patch_type": "wall", "field_type": "empty", "field": "p"}, "0/p", 35),
    ("keyword", la.MISSING_ENTRY, {"key": "deltaT", "dict": "system/controlDict", "present": "yes"},
     "system/controlDict", 6),
    ("nonu", la.MISSING_ENTRY, {"key": "nu", "dict": "constant/transportProperties", "present": ""},
     "constant/transportProperties", 17),
    ("noschemeentry", la.MISSING_ENTRY,
     {"key": "div(phi,U)", "dict": "system/fvSchemes/divSchemes", "present": ""}, "system/fvSchemes", 30),
    ("nosolverentry", la.MISSING_ENTRY, {"key": "p", "dict": "system/fvSolution/solvers", "present": ""},
     "system/fvSolution", 21),
    ("pref", la.NO_REFERENCE_CELL, {"field": "p"}, "system/fvSolution", 44),
    ("nomesh", la.NO_MESH, {}, "", 0),
    ("nozero", la.MISSING_FILE, {"path": "0/p", "orig": ""}, "", 0),
    ("foundnames", la.MISSING_FILE, {"path": "constant/transportProperties", "orig": ""}, "", 0),
    ("decomp", la.DECOMPOSITION_DIVISIONS, {"count": "4", "n": "2 1 1", "product": "2"},
     "system/decomposeParDict", 4),
    ("decomp3", la.DECOMPOSITION_DIVISIONS, {"count": "4", "n": "2 1 1", "product": "2"},
     "system/decomposeParDict", 2),
    ("np", la.PROCESSOR_COUNT, {"want": "4", "got": "2"}, "", 0),
    ("brace", la.SYNTAX_ERROR, {"message": "Unexpected EOF while reading dictionary entry"},
     "system/fvSchemes", 51),
    ("brace2", la.SYNTAX_ERROR, {"message": "Found { but expected }"}, "system/fvSolution", 43),
])
def test_real_v2606_logs(case: Path, name, code, args, path, line):
    advice = run(name, case)
    assert [a.code for a in advice] == [code]
    assert advice[0].args == args
    assert rel(advice[0], case) == path
    assert advice[0].line == line


def test_keyword_deleted_outright(case: Path):
    # keyword.log comes from a controlDict with deltaT deleted; this case's
    # controlDict still has it (after a line missing its ';'), so "present".
    # With it really gone, the advice says it is missing.
    (case / "system" / "controlDict").write_text(CONTROL.replace("deltaT          0.005;\n", ""))
    advice = run("keyword", case)
    assert advice[0].args["present"] == ""
    assert advice[0].line == 17  # OpenFOAM's own "at line 17 to 44"


def test_missing_zero_dir_suggests_restore(case: Path):
    (case / "0").rename(case / "0.orig")
    assert run("nozero", case)[0].args == {"path": "0/p", "orig": "0.orig"}


def test_floating_point_after_courant_growth(case: Path):
    advice = run("fpe", case)
    assert [a.code for a in advice] == [la.FLOATING_POINT]
    assert advice[0].args == {"courant": "6677.83", "time": "1"}
    # Opens controlDict at deltaT.
    assert rel(advice[0], case) == "system/controlDict"
    assert advice[0].line == 6


def test_floating_point_without_a_high_courant_number(case: Path):
    text = (
        "Time = 3\nCourant Number mean: 0.1 max: 0.4\n"
        "#1  Foam::sigFpe::sigHandler(int) in libOpenFOAM.so\n"
    )
    advice = la.advise(text, str(case))
    assert advice[0].args == {"courant": "", "time": "3"}
    assert advice[0].path == ""


def test_successful_log_has_no_advice(case: Path):
    text = "Time = 0.5\nCourant Number mean: 0.2 max: 0.8\nExecutionTime = 0.1 s\n\nEnd\n"
    assert la.advise(text, str(case)) == []


def test_unrecognised_error_gets_no_advice(case: Path):
    text = "--> FOAM FATAL ERROR: (openfoam-2606)\nSomething nobody has seen before\n\nFOAM exiting\n"
    assert la.advise(text, str(case)) == []


def test_file_outside_the_case_is_not_offered(case: Path):
    text = (
        "--> FOAM FATAL IO ERROR: (openfoam-2606)\nCannot find patchField entry for inlet\n\n"
        "file: elsewhere/0/U/boundaryField at line 3.\n\nFOAM exiting\n"
    )
    advice = la.advise(text, str(case))
    assert advice[0].code == la.MISSING_PATCH_ENTRY
    assert advice[0].path == "" and advice[0].line == 0


def test_parallel_ranks_are_stripped_and_deduplicated(case: Path):
    block = (
        "[{r}] --> FOAM FATAL IO ERROR: (openfoam-2606)\n[{r}] Cannot find patchField entry for inlet\n"
        "[{r}] \n[{r}] file: 0/U/boundaryField at line 3.\n[{r}] \nFOAM parallel run exiting\n"
    )
    advice = la.advise(block.format(r=0) + block.format(r=1), str(case))
    assert [a.code for a in advice] == [la.MISSING_PATCH_ENTRY]
    assert rel(advice[0], case) == "0/U"


# ── Foundation wording (composed from the Foundation-12 source) ──────────────

def foundation(message: str, file_ref: str = "") -> str:
    """A FatalIOError as IOerror.C's operator<< prints it."""
    text = "\n--> FOAM FATAL IO ERROR: \n" + message + "\n\n"
    if file_ref:
        text += "file: " + file_ref + "\n\n"
    return text + "    From function Foam::something()\n    in file x.C at line 1.\n\nFOAM exiting\n"


def test_foundation_missing_patch_with_absolute_path(case: Path):
    text = foundation(
        "Cannot find patchField entry for movingWall",
        f"{case}/0/U/boundaryField from line 25 to line 36.",
    )
    advice = la.advise(text, str(case))
    assert advice[0].code == la.MISSING_PATCH_ENTRY
    assert rel(advice[0], case) == "0/U" and advice[0].line == 25


def test_foundation_keyword_undefined(case: Path):
    text = foundation(
        f"keyword deltaT is undefined in dictionary {case}/system/controlDict",
        f"{case}/system/controlDict from line 17 to line 44.",
    )
    advice = la.advise(text, str(case))
    assert advice[0].code == la.MISSING_ENTRY
    assert advice[0].args["key"] == "deltaT"
    assert advice[0].args["dict"] == "system/controlDict"


def test_foundation_unknown_patch_field(case: Path):
    text = foundation(
        "Unknown patchField type noSlp for patch fixedWalls of type wall for field U\n\n"
        "Valid patchField types are :\n\n5\n(\nfixedValue\nnoSlip\nslip\nzeroGradient\ncalculated\n)",
        f"{case}/0/U/boundaryField/fixedWalls from line 30 to line 32.",
    )
    advice = la.advise(text, str(case))
    assert advice[0].args == {"what": "patchField", "name": "noSlp", "suggestion": "noSlip"}


def test_foundation_unknown_scheme_and_model(case: Path):
    scheme = foundation(
        "Unknown discretisation scheme lineer\n\nValid schemes are :\n\n2\n(\nlinear\nupwind\n)"
    )
    assert la.advise(scheme, str(case))[0].args["suggestion"] == "linear"
    model = foundation(
        "Unknown RASModel type kEpsilonn\n\nValid RASModel types:\n\n2\n(\nkEpsilon\nkOmegaSST\n)"
    )
    advice = la.advise(model, str(case))[0]
    assert advice.args == {"what": "RASModel", "name": "kEpsilonn", "suggestion": "kEpsilon"}


@pytest.mark.parametrize("message", [
    "system/decomposeParDict specifies 4 processors but job was started with 2 processors.",
    "number of processor directories = 4 is not equal to the number of processors = 2",
])
def test_foundation_processor_counts(case: Path, message: str):
    text = "\n--> FOAM FATAL ERROR: \n" + message + "\n\nFOAM parallel run exiting\n"
    assert la.advise(text, str(case))[0].args == {"want": "4", "got": "2"}


def test_foundation_divisions(case: Path):
    text = foundation(
        "Wrong number of processor divisions in geometric:\nNumber of domains    : 4\n"
        "Wanted decomposition : (2 1 1)",
    )
    assert la.advise(text, str(case))[0].args == {"count": "4", "n": "2 1 1", "product": "2"}


def test_max_iterations(case: Path):
    text = foundation("Maximum number of iterations exceeded: 100")
    assert [a.code for a in la.advise(text, str(case))] == [la.MAX_ITERATIONS]


def test_every_code_is_declared():
    assert {
        la.MISSING_PATCH_ENTRY, la.UNKNOWN_NAME, la.CONSTRAINT_MISMATCH, la.MISSING_ENTRY,
        la.NO_REFERENCE_CELL, la.MISSING_FILE, la.NO_MESH, la.DECOMPOSITION_DIVISIONS,
        la.PROCESSOR_COUNT, la.SYNTAX_ERROR, la.MAX_ITERATIONS, la.FLOATING_POINT,
    } == la.ADVICE_CODES
