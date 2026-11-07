# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""services/post_process.py: running function objects on existing results."""
from __future__ import annotations

import pytest

from services.post_process import (
    ALL_FUNCTIONS,
    invocation,
    is_valid_function,
    needs_solver,
    post_process_command,
    post_process_tool,
)
from services.tool_options import POST_PROCESS_SPEC, build_command


def test_the_tool_comes_from_the_installation(tmp_path):
    for name in ("postProcess", "foamPostProcess"):
        (tmp_path / name / "applications" / "utilities" / "postProcessing" / name).mkdir(parents=True)
    assert post_process_tool(str(tmp_path / "postProcess")) == "postProcess"
    assert post_process_tool(str(tmp_path / "foamPostProcess")) == "foamPostProcess"
    assert post_process_tool(None) == "postProcess"


@pytest.mark.parametrize(
    "func, ok",
    [("probes", True), ("mag(U)", True), ("residuals(p, U)", True), ("", False),
     ("a;rm -rf x", False), ("$(x)", False), ("2x", False)],
)
def test_function_names(func, ok):
    assert is_valid_function(func) is ok


class TestNeedsSolver:
    def test_by_template_name(self, tmp_path):
        assert needs_solver(str(tmp_path), "yPlus")
        assert needs_solver(str(tmp_path), "forcesIncompressible")  # prefix
        assert not needs_solver(str(tmp_path), "probes")
        assert not needs_solver(str(tmp_path), "mag(U)")
        # No -func: plain postProcess would load no fields at all.
        assert needs_solver(str(tmp_path), ALL_FUNCTIONS)

    def test_by_the_files_own_type(self, tmp_path):
        (tmp_path / "system").mkdir()
        (tmp_path / "system" / "liftOnWing").write_text("type forceCoeffs;\npatches (wing);\n")
        assert needs_solver(str(tmp_path), "liftOnWing")

    def test_by_the_template_the_file_includes(self, tmp_path):
        (tmp_path / "system").mkdir()
        (tmp_path / "system" / "drag").write_text(
            '#includeEtc "caseDicts/postProcessing/forces/forcesIncompressible.cfg"\n'
            "patches (wing);\n"
        )
        assert needs_solver(str(tmp_path), "drag")


class TestInvocation:
    def test_plain(self):
        assert invocation("postProcess", False, "simpleFoam", None) == ["postProcess"]
        assert invocation("foamPostProcess", False, "foamRun", "fluid") == ["foamPostProcess"]

    def test_through_the_solver_opencfd_and_foundation_up_to_10(self):
        assert invocation("postProcess", True, "simpleFoam", None) == ["simpleFoam", "-postProcess"]
        assert invocation("postProcess", True, None, None) is None

    def test_through_the_solver_foundation_11_and_later(self):
        assert invocation("foamPostProcess", True, "foamRun", "incompressibleFluid") == [
            "foamPostProcess", "-solver", "incompressibleFluid"
        ]
        assert invocation("foamPostProcess", True, "foamRun", None) is None


def test_build_command_lead_and_log():
    import dataclasses

    spec = dataclasses.replace(POST_PROCESS_SPEC, name="simpleFoam")
    cmd = build_command(
        spec, {"-latestTime": True}, lead=("-postProcess", "-func", "yPlus"),
        log_name="log.postProcess",
    )
    # Never log.simpleFoam: that is the solver's own log.
    assert cmd == "simpleFoam -postProcess -func yPlus -latestTime 2>&1 | tee log.postProcess"
    assert build_command(spec, {}, lead=("-func", "mag(U)")).startswith(
        "simpleFoam -func 'mag(U)'"
    )


def test_post_process_command(tmp_path):
    opencfd, foundation = tmp_path / "v2606", tmp_path / "OpenFOAM-12"
    for inst, tool in ((opencfd, "postProcess"), (foundation, "foamPostProcess")):
        (inst / "applications" / "utilities" / "postProcessing" / tool).mkdir(parents=True)
    assert post_process_tool(str(opencfd)) == "postProcess"
    assert post_process_tool(str(foundation)) == "foamPostProcess"
    case = tmp_path / "case"
    (case / "0").mkdir(parents=True)
    assert post_process_command(str(opencfd), str(case)) == ""  # no results yet
    (case / "0.5").mkdir()
    assert post_process_command(str(foundation), str(case)) == (
        "foamPostProcess -func {name} -latestTime"
    )
    for n in range(4):  # a later time only in the processors
        (case / f"processor{n}" / "1").mkdir(parents=True)
    assert post_process_command(str(opencfd), str(case)) == (
        "mpirun -np 4 postProcess -func {name} -latestTime -parallel"
    )
