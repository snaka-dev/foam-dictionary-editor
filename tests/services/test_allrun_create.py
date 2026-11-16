# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""services/allrun_create: an Allrun and Allclean from a case's logs."""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from services import allrun as ar
from services import allrun_create as ac

BANNER = """\
/*---------------------------------------------------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
\\*---------------------------------------------------------------------------*/
Build  : _481094f-20260618 OPENFOAM=2606 version=2606
Arch   : "LSB;label=32;scalar=64"
"""


def write_log(
    case: Path, name: str, exec_line: str, *, time: str = "10:00:00",
    nprocs: int = 1, end: str = "End\n", date: str = "Nov 06 2026",
) -> Path:
    path = case / name
    path.write_text(
        BANNER
        + f"Exec   : {exec_line}\nDate   : {date}\nTime   : {time}\n"
        + f"Host   : machine\nCase   : /somewhere/else\nnProcs : {nprocs}\n\n"
        + "Create time\n\n" + end
    )
    return path


@pytest.fixture
def case(tmp_path: Path) -> Path:
    (tmp_path / "system").mkdir()
    (tmp_path / "constant").mkdir()
    (tmp_path / "system" / "controlDict").write_text("application interFoam;\nendTime 1;\n")
    return tmp_path


def lines(proposal: ac.Proposal) -> list[str]:
    return [ac.step_line(s, proposal.decompose_n) for s in proposal.steps]


# ── headers ──────────────────────────────────────────────────────────────────

def test_header_drops_parallel_and_case_and_rejoins_parentheses(case: Path):
    write_log(
        case, "log.foamToVTK",
        "foamToVTK -case /x/y -fields (U p) -parallel -time 0:1", nprocs=4,
    )
    h = ac.read_log_header(str(case), "log.foamToVTK")
    assert h is not None
    assert h.app == "foamToVTK"
    assert h.args == ("-fields", "(U p)", "-time", "0:1")
    assert h.nprocs == 4
    assert h.started is not None and (h.started.month, h.started.hour) == (11, 10)


def test_log_without_a_header_is_skipped(case: Path):
    (case / "log.Allrun").write_text("Running blockMesh on /x\n")
    write_log(case, "log.blockMesh", "blockMesh")
    p = ac.propose(str(case))
    assert ("log.Allrun", ac.SKIP_NO_HEADER) in p.skipped
    assert lines(p)[0] == "runApplication blockMesh"


def test_full_path_executable_gives_its_name(case: Path):
    write_log(case, "log.blockMesh", "/opt/of/bin/blockMesh")
    assert ac.read_log_header(str(case), "log.blockMesh").app == "blockMesh"


# ── order and form ───────────────────────────────────────────────────────────

def test_steps_follow_start_time_then_end_time(case: Path):
    write_log(case, "log.interFoam", "interFoam", time="10:05:00")
    write_log(case, "log.setFields", "setFields", time="10:02:00")
    sfe = write_log(case, "log.surfaceFeatureExtract", "surfaceFeatureExtract", time="10:01:00")
    snappy = write_log(case, "log.snappyHexMesh", "snappyHexMesh -overwrite", time="10:01:00")
    write_log(case, "log.blockMesh", "blockMesh", time="10:00:59")
    # Same start second: the one that finished first ran first.
    os.utime(sfe, (1_000, 1_000))
    os.utime(snappy, (2_000, 2_000))
    assert lines(ac.propose(str(case))) == [
        "runApplication blockMesh",
        "runApplication surfaceFeatureExtract",
        "runApplication snappyHexMesh -overwrite",
        "runApplication setFields",
        "runApplication interFoam",
    ]


def test_parallel_run_and_np_only_when_it_differs(case: Path):
    (case / "system" / "decomposeParDict").write_text("numberOfSubdomains 4;\n")
    write_log(case, "log.blockMesh", "blockMesh", time="10:00:00")
    write_log(case, "log.decomposePar", "decomposePar -force", time="10:00:01")
    write_log(case, "log.interFoam", "interFoam -parallel", time="10:00:02", nprocs=4)
    write_log(case, "log.foamToVTK", "foamToVTK -parallel", time="10:00:03", nprocs=2)
    assert lines(ac.propose(str(case)))[2:] == [
        "runParallel interFoam",
        "runParallel -np 2 foamToVTK",
    ]


def test_suffix_becomes_s_and_fode_part_logs_are_earlier_runs(case: Path):
    write_log(case, "log.topoSet.1", "topoSet -dict system/topoSetDict.1", time="10:00:01")
    write_log(case, "log.topoSet", "topoSet", time="10:00:00")
    write_log(case, "log.interFoam.part1", "interFoam", time="10:00:02")
    write_log(case, "log.interFoam", "interFoam", time="10:00:03")
    p = ac.propose(str(case))
    assert lines(p) == [
        "runApplication topoSet",
        "runApplication -s 1 topoSet -dict system/topoSetDict.1",
        "runApplication interFoam",
    ]
    assert ("log.interFoam.part1", ac.SKIP_EARLIER_RUN) in p.skipped


def test_a_part_log_alone_keeps_its_step_without_the_suffix(case: Path):
    write_log(case, "log.interFoam.part1", "interFoam", time="10:00:00")
    write_log(case, "log.interFoam.part2", "interFoam", time="10:00:05")
    p = ac.propose(str(case))
    runs = [s for s in p.steps if s.app == "interFoam"]
    assert [s.log for s in runs] == ["log.interFoam.part2"]
    assert lines(p)[-1] == "runApplication interFoam"


def test_failed_and_read_only_steps_are_unticked(case: Path):
    write_log(case, "log.blockMesh", "blockMesh", time="10:00:00")
    write_log(case, "log.checkMesh", "checkMesh", time="10:00:01")
    write_log(case, "log.setFields", "setFields", time="10:00:02",
              end="--> FOAM FATAL IO ERROR:\nbad\n")
    write_log(case, "log.interFoam", "interFoam", time="10:00:03", end="Time = 0.1\n")
    by_app = {s.app: s for s in ac.propose(str(case)).steps}
    assert by_app["checkMesh"].marks == (ac.MARK_READ_ONLY,) and not by_app["checkMesh"].checked
    assert by_app["setFields"].marks == (ac.MARK_FAILED,) and not by_app["setFields"].checked
    assert by_app["interFoam"].marks == (ac.MARK_INCOMPLETE,) and by_app["interFoam"].checked


def test_reconstruct_before_a_later_parallel_run_moves_after_it(case: Path):
    # mixerVesselAMI as a user ran it: reconstructed, decomposed again, ran on.
    write_log(case, "log.decomposePar", "decomposePar -force", time="10:00:00")
    write_log(case, "log.reconstructPar", "reconstructPar -newTimes", time="10:30:00")
    write_log(case, "log.interFoam", "interFoam -parallel", time="10:50:00", nprocs=6)
    p = ac.propose(str(case))
    assert [s.app for s in p.steps] == ["decomposePar", "interFoam", "reconstructPar"]
    assert ac.MARK_MOVED in p.steps[2].marks


# ── suggestions from dictionaries ────────────────────────────────────────────

def test_missing_mesh_and_solver_steps_are_suggested(case: Path):
    (case / "system" / "blockMeshDict").write_text("vertices ();\n")
    write_log(case, "log.setFields", "setFields")
    p = ac.propose(str(case))
    assert lines(p) == [
        "runApplication blockMesh",
        "runApplication setFields",
        "runApplication interFoam",
    ]
    assert p.steps[0].source == ac.SOURCE_DICT and p.steps[0].origin == "system/blockMeshDict"
    assert p.steps[0].marks == (ac.MARK_NO_LOG,)
    assert ac.NOTE_LIMITS in p.notes


def test_parallel_run_without_a_decompose_log_gets_decomposepar(case: Path):
    write_log(case, "log.blockMesh", "blockMesh", time="10:00:00")
    write_log(case, "log.interFoam", "interFoam -parallel", time="10:00:01", nprocs=2)
    assert lines(ac.propose(str(case))) == [
        "runApplication blockMesh",
        "runApplication decomposePar -force",
        "runParallel -np 2 interFoam",
    ]


def test_no_logs_gives_a_skeleton_from_the_dictionaries(case: Path):
    for name in ("blockMeshDict", "snappyHexMeshDict", "surfaceFeatureExtractDict",
                 "topoSetDict", "setFieldsDict"):
        (case / "system" / name).write_text("\n")
    p = ac.propose(str(case))
    assert ac.NOTE_FROM_DICTIONARIES in p.notes
    assert lines(p) == [
        "runApplication blockMesh",
        "runApplication surfaceFeatureExtract",
        "runApplication snappyHexMesh -overwrite",
        "runApplication topoSet",
        "runApplication setFields",
        "runApplication interFoam",
    ]
    assert ac.MARK_GUESSED in p.steps[3].marks
    text = ac.render_allrun(p.steps, p)
    assert "Suggested from the case's dictionaries" in text
    assert "# suggested: no log found" not in text


def test_skeleton_runs_in_parallel_only_with_processor_dirs(case: Path):
    (case / "system" / "decomposeParDict").write_text("numberOfSubdomains 4;\n")
    assert lines(ac.propose(str(case))) == ["runApplication interFoam"]
    (case / "processor0").mkdir()
    assert lines(ac.propose(str(case))) == [
        "runApplication decomposePar -force",
        "runParallel interFoam",
        "runApplication reconstructPar",
    ]


def test_foundation_surface_features(case: Path):
    (case / "system" / "snappyHexMeshDict").write_text("\n")
    (case / "system" / "surfaceFeaturesDict").write_text("\n")
    assert lines(ac.propose(str(case)))[:2] == [
        "runApplication surfaceFeatures", "runApplication snappyHexMesh -overwrite",
    ]


def test_a_mesher_named_as_the_application_is_not_a_second_step(case: Path):
    # v2606's mesh/snappyHexMesh/flange: a meshing-only tutorial whose
    # controlDict says `application snappyHexMesh`.
    (case / "system" / "controlDict").write_text("application snappyHexMesh;\n")
    for name in ("blockMeshDict", "snappyHexMeshDict", "surfaceFeatureExtractDict"):
        (case / "system" / name).write_text("\n")
    assert lines(ac.propose(str(case))) == [
        "runApplication blockMesh",
        "runApplication surfaceFeatureExtract",
        "runApplication snappyHexMesh -overwrite",
    ]
    (case / "system" / "controlDict").write_text("application blockMesh;\n")
    (case / "system" / "snappyHexMeshDict").unlink()
    (case / "system" / "surfaceFeatureExtractDict").unlink()
    assert lines(ac.propose(str(case))) == ["runApplication blockMesh"]


# ── 0.orig ───────────────────────────────────────────────────────────────────

def _zero_orig_case(case: Path) -> None:
    (case / "0.orig").mkdir()
    write_log(case, "log.blockMesh", "blockMesh", time="10:00:00")
    write_log(case, "log.snappyHexMesh", "snappyHexMesh -overwrite", time="10:00:01")
    write_log(case, "log.setFields", "setFields", time="10:00:02")


def test_restore_goes_after_meshing_in_the_forks_own_words(case: Path):
    _zero_orig_case(case)
    p = ac.propose(str(case), ac.FORK_OPENCFD)
    assert lines(p)[2:4] == ["restore0Dir", "runApplication setFields"]
    assert ac.NOTE_RESTORES_ZERO in p.notes
    p = ac.propose(str(case), ac.FORK_FOUNDATION)
    assert lines(p)[2] == "rm -rf 0 && cp -r 0.orig 0"
    assert lines(ac.propose(str(case), None))[2] == "rm -rf 0 && cp -r 0.orig 0"


def test_no_zero_orig_note_needs_a_zero_dir_and_a_field_writer(case: Path):
    write_log(case, "log.setFields", "setFields")
    assert ac.NOTE_NO_ZERO_ORIG not in ac.propose(str(case)).notes
    (case / "0").mkdir()
    assert ac.NOTE_NO_ZERO_ORIG in ac.propose(str(case)).notes


def test_foundation_lists_files_its_cleancase_deletes(case: Path):
    (case / "system" / "controlDict.orig").write_text("\n")
    write_log(case, "log.blockMesh", "blockMesh")
    assert ac.propose(str(case), ac.FORK_OPENCFD).orig_twins == ()
    p = ac.propose(str(case), ac.FORK_FOUNDATION)
    assert p.orig_twins == ("system/controlDict",)
    assert ac.NOTE_ORIG_FILES in p.notes


# ── the scripts ──────────────────────────────────────────────────────────────

def test_allclean_forms(case: Path):
    _zero_orig_case(case)
    p = ac.propose(str(case), ac.FORK_OPENCFD)
    assert "\ncleanCase0\n" in ac.render_allclean(p.steps, p)
    p = ac.propose(str(case), ac.FORK_FOUNDATION)
    assert "\ncleanCase\nrm -rf 0\n" in ac.render_allclean(p.steps, p)


def test_allclean_keeps_a_mesh_the_allrun_cannot_rebuild(case: Path):
    _zero_orig_case(case)
    p = ac.propose(str(case), ac.FORK_OPENCFD)
    steps = [s if s.app != "blockMesh" else ac.Proposed(**{**s.__dict__, "checked": False})
             for s in p.steps]
    assert not ac.makes_mesh(steps)
    text = ac.render_allclean(steps, p)
    assert "cleanCase" not in text.replace("# cleanCase would", "")
    assert "foamListTimes -rm" in text and "rm -rf 0" in text
    assert "runApplication blockMesh" not in ac.render_allrun(steps, p)


def test_allrun_quotes_and_marks(case: Path):
    write_log(case, "log.blockMesh", "blockMesh", time="10:00:00")
    write_log(case, "log.foamToVTK", "foamToVTK -fields (U p)", time="10:00:01")
    p = ac.propose(str(case))
    text = ac.render_allrun(p.steps, p)
    assert text.startswith("#!/bin/sh\ncd \"${0%/*}\" || exit")
    assert "runApplication foamToVTK -fields '(U p)'\n" in text
    assert "runApplication interFoam    # suggested: no log found\n" in text


@pytest.mark.skipif(shutil.which("sh") is None, reason="needs sh")
def test_scripts_are_valid_shell(case: Path):
    _zero_orig_case(case)
    write_log(case, "log.foamToVTK", "foamToVTK -fields (U p)", time="10:00:09")
    p = ac.propose(str(case), ac.FORK_OPENCFD)
    for text in (ac.render_allrun(p.steps, p), ac.render_allclean(p.steps, p)):
        subprocess.run(["sh", "-n"], input=text, text=True, check=True)


def test_write_script_is_executable_and_never_replaces(case: Path):
    path = case / "Allrun"
    ac.write_script(str(path), "#!/bin/sh\n")
    assert os.access(path, os.X_OK)
    with pytest.raises(FileExistsError):
        ac.write_script(str(path), "#!/bin/sh\necho other\n")
    assert path.read_text() == "#!/bin/sh\n"


def test_written_allrun_reads_back_as_the_same_steps(case: Path):
    """The step view reads what was written as the same commands and logs."""
    _zero_orig_case(case)
    write_log(case, "log.topoSet.1", "topoSet -dict system/topoSetDict.1", time="10:00:03")
    p = ac.propose(str(case), ac.FORK_OPENCFD)
    ac.write_script(str(case / "Allrun"), ac.render_allrun(p.steps, p))
    plan = ar.read_allrun(str(case))
    assert plan is not None
    expected = [
        f"log.{s.app}" + (f".{s.suffix}" if s.suffix else "")
        for s in p.steps if s.kind != ar.OTHER
    ]
    assert [s.log for s in plan.runs] == expected
    assert "log.topoSet.1" in expected


# ── reconstructPar, the parallel split, typed commands ───────────────────────

def body(script: str) -> list[str]:
    """The script's command lines: no header, comments or blank lines."""
    out = []
    for line in script.splitlines():
        line = line.split("    #")[0].strip()
        if line and not line.startswith(("#", "cd ", ". ")):
            out.append(line)
    return out


def test_no_reconstruct_suggested_after_a_serial_run(case: Path):
    # processor dirs left from some earlier run, but the logs ran it serially.
    (case / "system" / "decomposeParDict").write_text("numberOfSubdomains 4;\n")
    (case / "processor0").mkdir()
    write_log(case, "log.interFoam", "interFoam")
    assert lines(ac.propose(str(case))) == ["runApplication interFoam"]


def test_reconstruct_suggested_after_a_parallel_run_without_one(case: Path):
    (case / "system" / "decomposeParDict").write_text("numberOfSubdomains 4;\n")
    (case / "processor0").mkdir()
    write_log(case, "log.decomposePar", "decomposePar", time="10:00:00")
    write_log(case, "log.interFoam", "interFoam -parallel", time="10:00:01", nprocs=4)
    assert lines(ac.propose(str(case))) == [
        "runApplication decomposePar", "runParallel interFoam", "runApplication reconstructPar",
    ]


def _with_parallel_rows(p: ac.Proposal) -> list[ac.Proposed]:
    """The rows the dialog shows once "Also create Allrun-parallel" is ticked."""
    steps = list(p.steps)
    at = next(i for i, s in enumerate(steps) if s.app == p.solver)
    for row in ac.parallel_rows(p):
        if row.app == "decomposePar":
            steps.insert(at, row)
            at += 1
        else:
            steps.insert(at + 1, row)
    return steps


def test_split_of_a_serial_case_like_cavity(case: Path):
    # The tutorial cavity: a decomposeParDict it never uses, no logs, no processor dirs.
    (case / "system" / "controlDict").write_text("application icoFoam;\n")
    (case / "system" / "blockMeshDict").write_text("\n")
    (case / "system" / "decomposeParDict").write_text("numberOfSubdomains 9;\n")
    p = ac.propose(str(case), ac.FORK_OPENCFD)
    assert ac.can_split(p) and not ac.ran_in_parallel(p)
    split = ac.render_split(_with_parallel_rows(p), p)
    assert split is not None and split.pre is not None
    assert body(split.pre) == ["runApplication blockMesh"]
    assert body(split.allrun) == ["./Allrun.pre", "runApplication icoFoam"]
    assert body(split.parallel) == [
        "./Allrun.pre", "runApplication decomposePar", "runParallel icoFoam",
        "runApplication reconstructPar",
    ]
    for text in (split.pre, split.allrun, split.parallel):
        subprocess.run(["sh", "-n"], input=text, text=True, check=True)
        assert text.count("Suggested from the case's dictionaries") == 1


def test_split_of_a_parallel_run_from_logs(case: Path):
    (case / "0.orig").mkdir()
    (case / "system" / "decomposeParDict").write_text("numberOfSubdomains 4;\n")
    write_log(case, "log.blockMesh", "blockMesh", time="10:00:00")
    write_log(case, "log.setFields", "setFields", time="10:00:01")
    write_log(case, "log.decomposePar", "decomposePar", time="10:00:02")
    write_log(case, "log.interFoam", "interFoam -parallel", time="10:00:03", nprocs=4)
    write_log(case, "log.reconstructPar", "reconstructPar", time="10:00:04")
    p = ac.propose(str(case), ac.FORK_OPENCFD)
    assert ac.ran_in_parallel(p) and not ac.parallel_rows(p)
    split = ac.render_split(p.steps, p)
    assert split is not None and split.pre is not None
    assert body(split.pre) == ["runApplication blockMesh", "restore0Dir", "runApplication setFields"]
    # The serial twin: the solver alone, no decomposePar or reconstructPar.
    assert body(split.allrun) == ["./Allrun.pre", "runApplication interFoam"]
    assert body(split.parallel) == [
        "./Allrun.pre", "runApplication decomposePar", "runParallel interFoam",
        "runApplication reconstructPar",
    ]


def test_split_needs_a_ticked_solver(case: Path):
    (case / "system" / "blockMeshDict").write_text("\n")
    (case / "system" / "decomposeParDict").write_text("numberOfSubdomains 2;\n")
    p = ac.propose(str(case))
    steps = [replace(s, checked=s.app != "interFoam") for s in p.steps]
    assert ac.render_split(steps, p) is None


def test_split_with_nothing_before_the_solver_has_no_pre(case: Path):
    (case / "system" / "decomposeParDict").write_text("numberOfSubdomains 2;\n")
    p = ac.propose(str(case))
    split = ac.render_split(_with_parallel_rows(p), p)
    assert split is not None and split.pre is None
    assert body(split.allrun) == ["runApplication interFoam"]
    assert body(split.parallel)[0] == "runApplication decomposePar"


def test_no_split_offered_without_subdomains(case: Path):
    (case / "system" / "blockMeshDict").write_text("\n")
    assert not ac.can_split(ac.propose(str(case)))
    (case / "system" / "decomposeParDict").write_text("numberOfSubdomains 1;\n")
    assert not ac.can_split(ac.propose(str(case)))


@pytest.mark.parametrize(("typed", "line"), [
    ("decomposePar -force", "runApplication decomposePar -force"),
    ("interFoam", "runApplication interFoam"),        # the case's solver
    ("runParallel interFoam", "runParallel interFoam"),
    ("runApplication -s 1 topoSet", "runApplication -s 1 topoSet"),   # own options: as typed
    ("cp -r 0.orig 0", "cp -r 0.orig 0"),
    ("foamDictionary -entry x system/controlDict", "foamDictionary -entry x system/controlDict"),
])
def test_typed_commands(typed: str, line: str, monkeypatch):
    monkeypatch.delenv("FOAM_APPBIN", raising=False)
    monkeypatch.delenv("FOAM_USER_APPBIN", raising=False)
    row = ac.user_row(typed, "interFoam")
    assert row is not None and ac.MARK_USER in row.marks
    assert ac.step_line(row) == line


def test_typed_application_found_in_the_installation(tmp_path: Path, monkeypatch):
    (tmp_path / "myTool").write_text("")
    monkeypatch.setenv("FOAM_APPBIN", str(tmp_path))
    row = ac.user_row("myTool -dict system/x")
    assert row is not None and row.kind == ar.RUN and row.app == "myTool"


def test_blank_typed_command_is_nothing():
    assert ac.user_row("   ") is None
