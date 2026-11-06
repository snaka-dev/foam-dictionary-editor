# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""services/process_tree.py: what the Terminal tab's shell is still running."""
from __future__ import annotations

import subprocess
import sys
import time

import pytest

from services.process_tree import ProcessInfo, child_processes, running_command_names


def _proc(tmp_path, pid, comm, ppid, pgrp=None):
    d = tmp_path / str(pid)
    d.mkdir()
    pgrp = pid if pgrp is None else pgrp
    (d / "stat").write_text(f"{pid} ({comm}) S {ppid} {pgrp} {pgrp} 0 -1 4194304 0\n")


@pytest.fixture
def fake_proc(tmp_path):
    _proc(tmp_path, 100, "bash", 1)
    _proc(tmp_path, 120, "tee", 100)
    _proc(tmp_path, 110, "simpleFoam", 100)
    _proc(tmp_path, 130, "a (weird) name", 100)
    _proc(tmp_path, 200, "mpirun", 110)  # a grandchild: not reported
    (tmp_path / "self").mkdir()  # non-numeric entries are skipped
    (tmp_path / "300").mkdir()  # no stat file (process gone mid-scan)
    return str(tmp_path)


def test_direct_children_sorted_by_pid(fake_proc):
    assert child_processes(100, fake_proc) == [
        ProcessInfo(110, "simpleFoam", 110),
        ProcessInfo(120, "tee", 120),
        ProcessInfo(130, "a (weird) name", 130),
    ]


def test_names_leave_out_plumbing(fake_proc):
    assert running_command_names(100, proc_root=fake_proc) == ["simpleFoam", "a (weird) name"]


def test_plumbing_alone_still_counts_as_busy(tmp_path):
    _proc(tmp_path, 100, "bash", 1)
    _proc(tmp_path, 101, "tee", 100)
    assert running_command_names(100, proc_root=str(tmp_path)) == ["tee"]


def test_idle_or_unknown_shell(fake_proc):
    assert running_command_names(110, proc_root=fake_proc) == ["mpirun"]
    assert running_command_names(200, proc_root=fake_proc) == []
    assert running_command_names(None, proc_root=fake_proc) == []
    assert running_command_names(0, proc_root=fake_proc) == []


def test_job_control_ignores_the_shells_own_helpers(tmp_path):
    """An interactive shell's prompt/rc helpers share its process group; jobs do not."""
    _proc(tmp_path, 100, "bash", 1)              # session + group leader
    _proc(tmp_path, 101, "bash", 100, pgrp=100)  # a prompt's $(...) subshell
    assert running_command_names(100, job_control=True, proc_root=str(tmp_path)) == []
    # ...whereas without job control every child counts.
    assert running_command_names(100, proc_root=str(tmp_path)) == ["bash"]
    _proc(tmp_path, 102, "simpleFoam", 100, pgrp=102)  # a job: its own group
    assert running_command_names(100, job_control=True, proc_root=str(tmp_path)) == [
        "simpleFoam"
    ]


def test_no_proc_reports_nothing(tmp_path):
    assert child_processes(1, str(tmp_path / "missing")) == []


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="reads /proc")
def test_a_real_child_is_found():
    # `sleep` is not the last command, so bash forks it rather than exec'ing.
    shell = subprocess.Popen(["bash", "-c", "sleep 30; true"])
    try:
        deadline = time.monotonic() + 5
        names: list[str] = []
        while time.monotonic() < deadline and not names:
            names = running_command_names(shell.pid)
            time.sleep(0.05)
        assert names == ["sleep"]
    finally:
        shell.kill()
        shell.wait()
