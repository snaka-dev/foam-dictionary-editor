# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Where Plot Results may write (services/plot_output.py): never among a case's files."""
from __future__ import annotations

import os
import subprocess
import sys

import pytest

from services.plot_output import refusal, write_atomically


@pytest.fixture
def case(tmp_path):
    root = tmp_path / "run" / "cavity"
    for d in ("system", "constant", "0", "0.5", "0.orig", "processor0",
              "postProcessing/forces/0"):
        (root / d).mkdir(parents=True)
    (root / "postProcessing/forces/0/force.dat").write_text("# Time f\n0 1\n")
    (root / "log.icoFoam").write_text("Time = 1\n")
    (root / "Allrun").write_text("#!/bin/sh\n")
    (root / "cavity.foam").write_text("")
    (root / "plot.png").write_bytes(b"old")
    return root


@pytest.mark.parametrize("rel", [
    "system/plot.png", "constant/plot.png", "0/plot.png", "0.5/plot.png", "0.orig/x.py",
    "processor0/plot.png", "postProcessing/plot.png", "postProcessing/forces/0/force.dat",
    "postProcessing/forces/0/new.dat",
])
def test_nothing_goes_into_directories_openfoam_owns(case, rel):
    assert refusal(str(case / rel)) == "case_dir"


@pytest.mark.parametrize("name", ["log.icoFoam", "Allrun", "cavity.foam"])
def test_the_case_roots_own_files_are_not_replaced(case, name):
    assert refusal(str(case / name)) == "case_file"


def test_the_case_root_a_folder_of_ones_own_and_outside_are_fine(case, tmp_path):
    assert refusal(str(case / "plot.png")) is None       # replacing our own output
    assert refusal(str(case / "plots" / "a.png")) is None
    assert refusal(str(tmp_path / "elsewhere.png")) is None
    # A new file named like a log is not replacing anything.
    assert refusal(str(case / "log.icoFoam.png")) is None


def test_a_plotted_file_is_protected_wherever_it_is(tmp_path):
    data = tmp_path / "loose" / "probe.dat"
    data.parent.mkdir()
    data.write_text("0 1\n")
    assert refusal(str(data), frozenset({str(data)})) == "protected"
    assert refusal(str(data)) is None


def test_a_case_the_window_holds_counts_without_its_dictionaries(tmp_path):
    results = tmp_path / "copied-results"
    (results / "postProcessing" / "probes" / "0").mkdir(parents=True)
    target = str(results / "postProcessing" / "probes" / "0" / "p.csv")
    assert refusal(target) is None  # no system/ or constant/: not known as a case
    assert refusal(target, cases=(str(results),)) == "case_dir"


def test_a_symlink_is_judged_by_where_it_points(case, tmp_path):
    link = tmp_path / "innocent.dat"
    link.symlink_to(case / "postProcessing/forces/0/force.dat")
    assert refusal(str(link)) == "case_dir"


def test_an_atomic_write_replaces_whole_or_not_at_all(case, monkeypatch):
    target = case / "plot.png"
    os.chmod(target, 0o640)
    write_atomically(str(target), b"new")
    assert target.read_bytes() == b"new"
    assert target.stat().st_mode & 0o777 == 0o640

    def fail(*_a):
        raise OSError("disk full")

    monkeypatch.setattr("services.plot_output.os.replace", fail)
    with pytest.raises(OSError):
        write_atomically(str(target), b"partial")
    assert target.read_bytes() == b"new"
    assert not [p for p in os.listdir(case) if p.endswith(".tmp")]


def test_an_exported_script_will_not_save_over_a_data_file(tmp_path):
    """The script's own ``out`` argument: savefig refuses an unknown format first."""
    pytest.importorskip("matplotlib")
    data = tmp_path / "force.dat"
    data.write_text("keep me")
    code = (
        "import matplotlib; matplotlib.use('Agg');"
        "from matplotlib.figure import Figure; f = Figure(); f.add_subplot();"
        f"f.savefig({str(data)!r})"
    )
    run = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True)
    assert run.returncode != 0 and "not supported" in run.stderr
    assert data.read_text() == "keep me"
