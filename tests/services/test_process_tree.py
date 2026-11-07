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


# ── processes_in_directory: is anything working in a case? ───────────────────

from services.process_tree import processes_in_directory  # noqa: E402


def _proc_in(root, pid, comm, ppid, cwd=None, cmdline=()):
    _proc(root, pid, comm, ppid)
    d = root / str(pid)
    if cwd is not None:
        (d / "cwd").symlink_to(cwd)
    (d / "cmdline").write_bytes(b"\0".join(a.encode() for a in cmdline) + b"\0")


def test_processes_running_in_the_case_or_naming_it(tmp_path):
    case = tmp_path / "case"
    (case / "system").mkdir(parents=True)
    other = tmp_path / "elsewhere"
    other.mkdir()
    proc = tmp_path / "proc"
    proc.mkdir()
    _proc_in(proc, 10, "reconstructPar", 1, case)
    _proc_in(proc, 11, "simpleFoam", 1, case / "system")  # a subdirectory counts
    _proc_in(proc, 12, "mpirun", 1, other, ["mpirun", "-np", "2", "x", "-case", str(case)])
    _proc_in(proc, 13, "icoFoam", 1, tmp_path, ["icoFoam", "-case", "case"])  # relative
    _proc_in(proc, 14, "bash", 1, case)  # an idle shell
    _proc_in(proc, 15, "less", 1, case)  # a pager on a log
    _proc_in(proc, 16, "simpleFoam", 1, other)
    _proc_in(proc, 17, "gone", 1)  # cwd unreadable
    found = processes_in_directory(str(case), proc_root=str(proc))
    assert [(p.pid, p.name) for p in found] == [
        (10, "reconstructPar"), (11, "simpleFoam"), (12, "mpirun"), (13, "icoFoam")
    ]


def test_a_sibling_directory_with_a_common_prefix_is_not_inside(tmp_path):
    (tmp_path / "case").mkdir()
    (tmp_path / "case2").mkdir()
    proc = tmp_path / "proc"
    proc.mkdir()
    _proc_in(proc, 10, "simpleFoam", 1, tmp_path / "case2")
    assert processes_in_directory(str(tmp_path / "case"), proc_root=str(proc)) == []


def test_fodes_own_process_tree_is_left_out(tmp_path):
    case = tmp_path / "case"
    case.mkdir()
    proc = tmp_path / "proc"
    proc.mkdir()
    _proc_in(proc, 50, "python3", 1, case)  # FoDE, started from the case
    _proc_in(proc, 51, "QtWebEngineProc", 50, case)  # its helper, same cwd
    _proc_in(proc, 60, "reconstructPar", 1, case)  # another terminal's job
    found = processes_in_directory(str(case), exclude_tree_of=50, proc_root=str(proc))
    assert [p.pid for p in found] == [60]


def test_a_real_process_in_the_directory_is_found(tmp_path):
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], cwd=tmp_path)
    try:
        for _ in range(50):
            found = processes_in_directory(str(tmp_path))
            if found:
                break
            time.sleep(0.05)
        assert child.pid in [p.pid for p in found]
        # …and not when it belongs to the tree being excluded (FoDE's own).
        import os

        mine = processes_in_directory(str(tmp_path), exclude_tree_of=os.getpid())
        assert child.pid not in [p.pid for p in mine]
    finally:
        child.kill()
        child.wait()


def test_no_proc_means_nothing_found(tmp_path):
    assert processes_in_directory(str(tmp_path), proc_root=str(tmp_path / "missing")) == []


# ── followers: a tail is never "running", and is stopped before a command ────

from services.process_tree import follower_pids  # noqa: E402


def test_a_tail_never_counts_as_running(tmp_path):
    _proc(tmp_path, 100, "bash", 1)
    _proc(tmp_path, 101, "tail", 100)
    assert running_command_names(100, proc_root=str(tmp_path)) == []
    assert follower_pids(100, proc_root=str(tmp_path)) == [101]


def test_a_tail_beside_a_real_job(tmp_path):
    _proc(tmp_path, 100, "bash", 1)
    _proc(tmp_path, 101, "tail", 100)
    _proc(tmp_path, 102, "simpleFoam", 100)
    assert running_command_names(100, proc_root=str(tmp_path)) == ["simpleFoam"]
    assert follower_pids(100, proc_root=str(tmp_path)) == [101]
    assert follower_pids(None, proc_root=str(tmp_path)) == []
