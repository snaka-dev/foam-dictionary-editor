# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for services/allrun.py (the Allrun as steps, marked from their logs).

The log names and the skip rule are those of OpenFOAM's RunFunctions in both
forks (``runApplication``/``runParallel``: ``log.<app>[.<suffix>]``, skipped
while the log exists unless ``-o``/``-a``). Three real v2606 Allruns
(damBreak, extrudeMesh/polyline, IO/systemCall) were run during development
and the logs they wrote matched these names exactly.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from services import allrun as ar

HEAD = '#!/bin/sh\ncd "${0%/*}" || exit\n. ${WM_PROJECT_DIR:?}/bin/tools/RunFunctions\n'


@pytest.fixture
def case(tmp_path: Path) -> Path:
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "controlDict").write_text("application interFoam;\n")
    return tmp_path


def allrun(case: Path, body: str, name: str = "Allrun") -> None:
    (case / name).write_text(HEAD + body)


def runs(plan: ar.AllrunPlan) -> list[tuple[str, str, str]]:
    return [(s.kind, s.app, s.log) for s in plan.runs]


def log(case: Path, name: str, text: str = "Starting\nEnd\n") -> Path:
    p = case / name
    p.write_text(text)
    return p


def test_no_allrun(case: Path):
    assert ar.read_allrun(str(case)) is None


def test_the_tutorial_shape(case: Path):
    allrun(case, "restore0Dir\nrunApplication blockMesh\nrunApplication setFields\n"
                 "runApplication $(getApplication)\n")
    plan = ar.read_allrun(str(case))
    assert plan is not None and plan.linear
    assert [s.text for s in plan.steps] == [
        "restore0Dir", "runApplication blockMesh", "runApplication setFields",
        "runApplication $(getApplication)",
    ]
    assert runs(plan) == [
        (ar.RUN, "blockMesh", "log.blockMesh"),
        (ar.RUN, "setFields", "log.setFields"),
        (ar.RUN, "interFoam", "log.interFoam"),
    ]


class TestOptions:
    @pytest.mark.parametrize("line, app, logname, always", [
        ("runApplication -s arc extrudeMesh", "extrudeMesh", "log.extrudeMesh.arc", False),
        ("runApplication -suffix .1 topoSet -dict system/topoSetDict.1", "topoSet", "log.topoSet.1", False),
        ("runApplication -o checkMesh", "checkMesh", "log.checkMesh", True),
        ("runApplication -a $(getApplication)", "interFoam", "log.interFoam", True),
        ("runApplication -p myLog. blockMesh", "blockMesh", "myLog.blockMesh", False),
        ("runApplication -d logs blockMesh", "blockMesh", "logs/log.blockMesh", False),
        ("runParallel -np 4 -s 2 snappyHexMesh -overwrite", "snappyHexMesh", "log.snappyHexMesh.2", False),
        ("runApplication -decomposeParDict system/d6 decomposePar", "decomposePar", "log.decomposePar",
         False),
        ("runApplication $FOAM_APPBIN/../bin/foo", "", "", False),
    ])
    def test_call(self, case: Path, line: str, app: str, logname: str, always: bool):
        allrun(case, line + "\n")
        step = ar.read_allrun(str(case)).steps[0]
        assert (step.app, step.log, step.always_reruns) == (app, logname, always)

    def test_parallel_kind(self, case: Path):
        allrun(case, "runParallel $(getApplication)\n")
        assert ar.read_allrun(str(case)).steps[0].kind == ar.PARALLEL

    def test_variables(self, case: Path):
        allrun(case, 'app=$(getApplication)\nrunApplication $app\nsolver=simpleFoam\n'
                     'runApplication ${solver}\ndecompDict="-decomposeParDict system/d6"\n'
                     "runParallel $decompDict $app\n")
        assert [s.app for s in ar.read_allrun(str(case)).runs] == ["interFoam", "simpleFoam", "interFoam"]

    def test_environment_prefix(self, case: Path):
        allrun(case, "USE_ARC=true runApplication -s arc extrudeMesh\n")
        assert runs(ar.read_allrun(str(case))) == [(ar.RUN, "extrudeMesh", "log.extrudeMesh.arc")]

    def test_split_assignment_is_not_a_row(self, case: Path):
        allrun(case, "latestTime=$(foamListTimes -latestTime)\nrunApplication blockMesh\n")
        assert [s.text for s in ar.read_allrun(str(case)).steps] == ["runApplication blockMesh"]


class TestLines:
    def test_continuations_semicolons_and_comments(self, case: Path):
        allrun(case, "runApplication \\\n    blockMesh   # the mesh\n"
                     "runApplication topoSet; runApplication setFields\n")
        assert [s.app for s in ar.read_allrun(str(case)).runs] == ["blockMesh", "topoSet", "setFields"]

    def test_plumbing_is_not_listed(self, case: Path):
        allrun(case, 'echo "start"\nprintf "x"\n[ -d 0 ] || cp -r 0.orig 0\nrunApplication blockMesh\n')
        steps = [s.text for s in ar.read_allrun(str(case)).steps]
        assert steps == ["cp -r 0.orig 0", "runApplication blockMesh"]

    def test_branches_mark_conditional_steps(self, case: Path):
        allrun(case, "runApplication blockMesh\nif notTest; then\n    runApplication setFields\nfi\n"
                     "for d in a b; do\n    runApplication -s $d topoSet\ndone\n")
        plan = ar.read_allrun(str(case))
        assert not plan.linear and ar.NOTE_BRANCHES in plan.notes
        assert [(s.app, s.conditional) for s in plan.runs] == [
            ("blockMesh", False), ("setFields", True), ("topoSet", True),
        ]

    def test_other_directories_are_not_followed(self, case: Path):
        allrun(case, "runApplication blockMesh\n(cd sub && runApplication setFields)\n"
                     "cd other\nrunApplication icoFoam\ncd ..\nrunApplication topoSet\n")
        plan = ar.read_allrun(str(case))
        assert [s.app for s in plan.runs] == ["blockMesh", "topoSet"]
        assert ar.NOTE_SUBDIRECTORY in plan.notes

    def test_multi_line_subshell(self, case: Path):
        allrun(case, "(\n    cd sub || exit\n    runApplication setFields\n)\nrunApplication blockMesh\n")
        assert [s.app for s in ar.read_allrun(str(case)).runs] == ["blockMesh"]

    def test_allrun_pre_is_followed(self, case: Path):
        allrun(case, "runApplication blockMesh\nrunApplication topoSet\n", name="Allrun.pre")
        allrun(case, "./Allrun.pre\nrunApplication $(getApplication)\n")
        plan = ar.read_allrun(str(case))
        assert [(s.app, s.script) for s in plan.runs] == [
            ("blockMesh", "Allrun.pre"), ("topoSet", "Allrun.pre"), ("interFoam", "Allrun"),
        ]

    def test_allrun_calling_itself_is_not_followed(self, case: Path):
        allrun(case, "./Allrun\nrunApplication blockMesh\n")
        assert [s.app for s in ar.read_allrun(str(case)).runs] == ["blockMesh"]

    def test_unsaved_buffer_counts(self, case: Path):
        allrun(case, "runApplication blockMesh\n")
        path = str(case / "Allrun")
        plan = ar.read_allrun(str(case), read_text=lambda p: HEAD + "runApplication snappyHexMesh\n"
                              if p == path else None)
        assert [s.app for s in plan.runs] == ["snappyHexMesh"]


class TestStates:
    @pytest.fixture
    def plan(self, case: Path) -> ar.AllrunPlan:
        allrun(case, "runApplication blockMesh\nrunApplication setFields\nrunApplication $(getApplication)\n")
        return ar.read_allrun(str(case))

    def test_each_state(self, case: Path, plan: ar.AllrunPlan):
        log(case, "log.blockMesh")
        log(case, "log.setFields", "--> FOAM FATAL IO ERROR: (openfoam-2606)\nUnknown\n")
        log(case, "log.interFoam", "Time = 0.1\nCourant Number mean: 0 max: 0\n")
        assert [ar.step_state(str(case), s) for s in plan.runs] == [ar.DONE, ar.FAILED, ar.INCOMPLETE]
        (case / "log.interFoam").unlink()
        assert ar.step_state(str(case), plan.runs[2]) == ar.NOT_RUN

    def test_a_log_still_being_written_is_running(self, case: Path, plan: ar.AllrunPlan):
        log(case, "log.blockMesh")
        log(case, "log.setFields")
        log(case, "log.interFoam", "Time = 0.1\n")
        states = ar.step_states(str(case), plan, writing={"log.interFoam"})
        assert [s.state for s in states] == [ar.DONE, ar.DONE, ar.RUNNING]
        assert all(s.watched for s in states)
        # Nothing writing it: stopped, and the window may say so.
        stopped = ar.step_states(str(case), plan, writing=set())[2]
        assert stopped.state == ar.INCOMPLETE and stopped.watched
        # Writers unseen (no /proc): it may still be running.
        assert not ar.step_states(str(case), plan)[2].watched
        # A finished log stays done while its writer closes it.
        log(case, "log.interFoam")
        assert ar.step_states(str(case), plan, writing={"log.interFoam"})[2].state == ar.DONE

    def test_parallel_end_and_long_logs(self, case: Path, plan: ar.AllrunPlan):
        log(case, "log.blockMesh", "x\n" * 200_000 + "[0] End\n")
        assert ar.step_state(str(case), plan.runs[0]) == ar.DONE

    def test_floating_point_crash_is_failed(self, case: Path, plan: ar.AllrunPlan):
        log(case, "log.interFoam", "#1  Foam::sigFpe::sigHandler(int)\n")
        assert ar.step_state(str(case), plan.runs[2]) == ar.FAILED

    def test_done_after_a_failure_is_suspect(self, case: Path, plan: ar.AllrunPlan):
        # An Allrun carries on past a failure: interFoam "done" on fields
        # a broken setFields never wrote.
        log(case, "log.blockMesh")
        log(case, "log.setFields", "--> FOAM FATAL ERROR:\n")
        log(case, "log.interFoam")
        statuses = [s for s in ar.step_states(str(case), plan) if s.state]
        assert [s.suspect for s in statuses] == ["", "", ar.SUSPECT_AFTER_FAILURE]

    def test_done_older_than_an_earlier_rerun_is_suspect(self, case: Path, plan: ar.AllrunPlan):
        for name in ("log.blockMesh", "log.setFields", "log.interFoam"):
            log(case, name)
        now = time.time()
        os.utime(case / "log.blockMesh", (now - 100, now - 100))
        os.utime(case / "log.interFoam", (now - 50, now - 50))
        os.utime(case / "log.setFields", (now, now))   # re-run after interFoam
        statuses = [s for s in ar.step_states(str(case), plan) if s.state]
        assert [s.suspect for s in statuses] == ["", "", ar.SUSPECT_OUTDATED]

    def test_all_done_in_order_is_clean(self, case: Path, plan: ar.AllrunPlan):
        now = time.time()
        for i, name in enumerate(("log.blockMesh", "log.setFields", "log.interFoam")):
            p = log(case, name)
            os.utime(p, (now + i * 10, now + i * 10))
        assert all(not s.suspect for s in ar.step_states(str(case), plan))


class TestCommands:
    def test_not_run_step_is_sent_as_written(self, case: Path):
        allrun(case, "runApplication -s 1 topoSet -dict system/topoSetDict.1\n")
        step = ar.read_allrun(str(case)).steps[0]
        assert ar.step_command(str(case), step) == (
            ar.RUN_FUNCTIONS + " && runApplication -s 1 topoSet -dict system/topoSetDict.1"
        )

    def test_existing_log_gets_overwrite(self, case: Path):
        allrun(case, "runApplication checkMesh -writeFields '(nonOrthoAngle)'\n")
        log(case, "log.checkMesh")
        step = ar.read_allrun(str(case)).steps[0]
        assert ar.step_command(str(case), step) == (
            ar.RUN_FUNCTIONS + " && runApplication -o checkMesh -writeFields '(nonOrthoAngle)'"
        )

    def test_get_application_stays_unquoted(self, case: Path):
        allrun(case, "runApplication $(getApplication)\n")
        log(case, "log.interFoam")
        step = ar.read_allrun(str(case)).steps[0]
        assert ar.step_command(str(case), step).endswith("runApplication -o $(getApplication)")

    def test_run_from_here(self, case: Path):
        allrun(case, "runApplication blockMesh\nrestore0Dir\nrunApplication setFields\n"
                     "runApplication $(getApplication)\n")
        log(case, "log.setFields")
        plan = ar.read_allrun(str(case))
        assert ar.run_from_command(str(case), plan, 1) == " && ".join([
            ar.RUN_FUNCTIONS, "restore0Dir", "runApplication -o setFields",
            "runApplication $(getApplication)",
        ])

    def test_run_from_here_is_withheld_with_branches(self, case: Path):
        allrun(case, "runApplication blockMesh\nif true; then\n    runApplication setFields\nfi\n")
        plan = ar.read_allrun(str(case))
        assert ar.run_from_command(str(case), plan, 0) is None
