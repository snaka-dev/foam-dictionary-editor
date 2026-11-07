# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""services/background_run.py: runs that outlive FoDE, and stopping one."""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time

import pytest

from services.background_run import (
    PID_FILE,
    STOP_FILE,
    BackgroundRun,
    StopReport,
    active_run,
    background_command,
    background_supported,
    finish_stop,
    last_written_time,
    pending_restore,
    read_stop_at,
    request_stop,
    run_time_modifiable,
    stop_requested_at,
    with_stop_at,
)

_CONTROL = (
    "FoamFile { object controlDict; }\n"
    "application     icoFoam;\n"
    "stopAt          endTime; // run to the end\n"
    "endTime         0.5;\n"
)

def restore_stop_at(case_dir):
    """The ``stopAt`` finish_stop put back, or None (no report, or not restored)."""
    report = finish_stop(case_dir)
    return None if report is None else report.restored


needs_setsid = pytest.mark.skipif(not background_supported(), reason="needs Linux setsid")


def _case(tmp_path, control=_CONTROL):
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "controlDict").write_text(control)
    return tmp_path


def _control(case):
    return (case / "system" / "controlDict").read_text()


class TestCommand:
    def test_shape(self):
        cmd = background_command(
            ["mpirun", "-np", "4", "simpleFoam", "-parallel"], "log.simpleFoam", "simpleFoam",
            "mv log.simpleFoam log.simpleFoam.part1 && ",
        )
        assert cmd.startswith("mv log.simpleFoam log.simpleFoam.part1 && : > log.simpleFoam && ")
        assert "setsid -f sh -c" in cmd
        assert "sh mpirun -np 4 simpleFoam -parallel &&" in cmd
        # No pipe for a hangup to break; no terminal for mpirun to read.
        assert "| tee" not in cmd and "< /dev/null" in cmd
        assert 'tail -n +1 -F --pid=' in cmd

    def test_arguments_need_no_quoting_of_their_own(self):
        cmd = background_command(["solver", "-dict", "it's here"], "log.solver", "solver")
        assert "sh solver -dict 'it'\"'\"'s here'" in cmd

    def test_build_command_background_mode(self):
        import dataclasses

        from services.tool_options import SOLVER_SPEC, build_command

        spec = dataclasses.replace(SOLVER_SPEC, name="icoFoam")
        cmd = build_command(spec, {}, "", "", 2, background=True)
        assert "setsid -f" in cmd and "sh mpirun -np 2 icoFoam -parallel" in cmd
        assert build_command(spec, {}).endswith("icoFoam 2>&1 | tee log.icoFoam")


@needs_setsid
class TestRealRun:
    def test_runs_follows_and_leaves_no_run_behind(self, tmp_path):
        cmd = background_command(["sh", "-c", "echo one; sleep 0.5; echo two"], "log.x", "x")
        out = subprocess.run(
            ["bash", "-c", cmd], cwd=tmp_path, capture_output=True, text=True, timeout=30
        )
        assert out.returncode == 0
        assert (tmp_path / "log.x").read_text() == "one\ntwo\n"
        assert "one" in out.stdout and "two" in out.stdout  # the tail showed it
        assert active_run(str(tmp_path)) is None

    def test_survives_its_terminal(self, tmp_path):
        """Killing the shell that started it -- closing FoDE -- leaves it running."""
        cmd = background_command(["sh", "-c", "sleep 2; echo done"], "log.x", "x")
        term = subprocess.Popen(
            ["bash", "-c", cmd], cwd=tmp_path, start_new_session=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        run = None
        for _ in range(100):
            run = active_run(str(tmp_path))
            if run is not None:
                break
            time.sleep(0.05)
        assert run is not None and (run.label, run.log_name) == ("x", "log.x")
        os.killpg(term.pid, signal.SIGHUP)
        os.killpg(term.pid, signal.SIGKILL)
        term.wait()
        assert active_run(str(tmp_path)) == run  # still going
        for _ in range(100):
            if active_run(str(tmp_path)) is None:
                break
            time.sleep(0.05)
        assert (tmp_path / "log.x").read_text() == "done\n"


@needs_setsid
class TestKillingByHand:
    """What the user guide's "Without FoDE" commands do to a real detached run."""

    def _start(self, tmp_path):
        cmd = background_command(["sleep", "60"], "log.x", "x")
        term = subprocess.Popen(
            ["bash", "-c", cmd], cwd=tmp_path, start_new_session=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        for _ in range(100):
            run = active_run(str(tmp_path))
            if run is not None:
                return term, run
            time.sleep(0.05)
        raise AssertionError("the run never started")

    @staticmethod
    def _sleepers(pgid):
        out = subprocess.run(["pgrep", "-g", str(pgid), "sleep"], capture_output=True, text=True)
        return out.stdout.split()

    def test_kill_the_group_ends_the_whole_run(self, tmp_path):
        term, run = self._start(tmp_path)
        try:
            os.killpg(run.pid, signal.SIGTERM)  # kill -- -<pid>
            for _ in range(100):
                if active_run(str(tmp_path)) is None and not self._sleepers(run.pid):
                    break
                time.sleep(0.05)
            assert active_run(str(tmp_path)) is None
            assert self._sleepers(run.pid) == []
        finally:
            term.kill()
            term.wait()

    def test_killing_only_the_wrapper_leaves_the_run_counted(self, tmp_path):
        term, run = self._start(tmp_path)
        try:
            os.kill(run.pid, signal.SIGTERM)  # kill <pid>: the wrapper alone
            time.sleep(0.3)
            assert self._sleepers(run.pid)  # the "solver" is still running…
            assert active_run(str(tmp_path)) == run  # …and FoDE still sees the run
        finally:
            try:
                os.killpg(run.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            term.kill()
            term.wait()


class TestActiveRun:
    def test_no_file_no_run(self, tmp_path):
        assert active_run(str(tmp_path)) is None

    def test_a_stale_file_is_no_run_and_is_cleared(self, tmp_path):
        (tmp_path / PID_FILE).write_text("999999999 icoFoam log.icoFoam\n")
        assert active_run(str(tmp_path)) is None
        assert not (tmp_path / PID_FILE).exists()

    def test_an_empty_file_is_no_run(self, tmp_path):
        (tmp_path / PID_FILE).write_text("")
        assert active_run(str(tmp_path)) is None

    def test_a_reused_pid_elsewhere_is_no_run(self, tmp_path):
        # This test process is alive, but not working in tmp_path.
        (tmp_path / PID_FILE).write_text(f"{os.getpid()} icoFoam log.icoFoam\n")
        assert active_run(str(tmp_path)) is None

    @pytest.mark.skipif(not sys.platform.startswith("linux"), reason="reads /proc")
    def test_a_live_process_in_the_case(self, tmp_path):
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], cwd=tmp_path)
        try:
            (tmp_path / PID_FILE).write_text(f"{child.pid} icoFoam log.icoFoam\n")
            assert active_run(str(tmp_path)) == BackgroundRun(child.pid, "icoFoam", "log.icoFoam")
        finally:
            child.kill()
            child.wait()


class TestStopAt:
    def test_read(self):
        assert read_stop_at(_CONTROL) == "endTime"
        assert read_stop_at("endTime 1;") is None

    def test_set_changes_only_the_value(self):
        text = with_stop_at(_CONTROL, "writeNow")
        assert "stopAt          writeNow; // run to the end\n" in text
        assert text.replace("writeNow", "endTime") == _CONTROL

    def test_set_adds_a_missing_entry_and_none_removes_it(self):
        text = with_stop_at("endTime 1;\n", "writeNow")
        assert read_stop_at(text) == "writeNow"
        assert read_stop_at(with_stop_at(text, None)) is None

    @pytest.mark.parametrize(
        "line, expected",
        [("", True), ("runTimeModifiable true;", True), ("runTimeModifiable yes;", True),
         ("runTimeModifiable false;", False), ("runTimeModifiable off;", False)],
    )
    def test_run_time_modifiable(self, line, expected):
        assert run_time_modifiable(_CONTROL + line + "\n") is expected


class TestStopAndRestore:
    def test_stop_then_restore(self, tmp_path):
        case = _case(tmp_path)
        assert request_stop(str(case)) is None
        assert read_stop_at(_control(case)) == "writeNow"
        assert pending_restore(str(case))
        assert restore_stop_at(str(case)) == "endTime"
        assert _control(case) == _CONTROL  # byte for byte
        assert not pending_restore(str(case))

    def test_stopping_twice_keeps_the_first_record(self, tmp_path):
        case = _case(tmp_path)
        request_stop(str(case))
        request_stop(str(case))
        assert json.loads((case / STOP_FILE).read_text())["stopAt"] == "endTime"
        assert restore_stop_at(str(case)) == "endTime"

    def test_an_absent_entry_is_removed_again(self, tmp_path):
        case = _case(tmp_path, "application icoFoam;\n")
        request_stop(str(case))
        assert restore_stop_at(str(case)) == "(removed)"
        assert read_stop_at(_control(case)) is None

    def test_a_value_changed_meanwhile_wins(self, tmp_path):
        case = _case(tmp_path)
        request_stop(str(case))
        (case / "system" / "controlDict").write_text(with_stop_at(_CONTROL, "nextWrite"))
        assert restore_stop_at(str(case)) is None
        assert read_stop_at(_control(case)) == "nextWrite"
        assert not pending_restore(str(case))

    @pytest.mark.skipif(not sys.platform.startswith("linux"), reason="reads /proc")
    def test_nothing_is_restored_while_the_run_goes_on(self, tmp_path):
        case = _case(tmp_path)
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], cwd=case)
        try:
            (case / PID_FILE).write_text(f"{child.pid} icoFoam log.icoFoam\n")
            request_stop(str(case))
            assert restore_stop_at(str(case)) is None
            assert read_stop_at(_control(case)) == "writeNow"
        finally:
            child.kill()
            child.wait()
        assert restore_stop_at(str(case)) == "endTime"

    def test_the_file_keeps_its_inode(self, tmp_path):
        # A solver watching controlDict with inotify must see a modification.
        case = _case(tmp_path)
        before = os.stat(case / "system" / "controlDict").st_ino
        request_stop(str(case))
        assert os.stat(case / "system" / "controlDict").st_ino == before

    def test_no_control_dict_reports_the_error(self, tmp_path):
        assert request_stop(str(tmp_path)) is not None


class TestStopReport:
    def _stopped(self, tmp_path, log_tail):
        case = _case(tmp_path)
        (case / "log.icoFoam").write_text("Time = 0.1\n" + log_tail)
        (case / "0.1").mkdir()
        run = BackgroundRun(1, "icoFoam", "log.icoFoam")
        request_stop(str(case), run)
        return case

    def test_a_clean_stop(self, tmp_path):
        case = self._stopped(tmp_path, "ExecutionTime = 1 s\n\nEnd\n\n")
        assert stop_requested_at(str(case)) is not None
        assert finish_stop(str(case)) == StopReport(
            "icoFoam", "log.icoFoam", "endTime", "0.1", True
        )
        assert stop_requested_at(str(case)) is None

    def test_a_run_that_ended_without_end(self, tmp_path):
        case = self._stopped(tmp_path, "Courant Number mean: 0.1\n")
        assert finish_stop(str(case)).clean is False

    def test_allrun_has_no_solver_log_to_judge(self, tmp_path):
        case = _case(tmp_path)
        request_stop(str(case), BackgroundRun(1, "Allrun", "log.Allrun"))
        assert finish_stop(str(case)).clean is None

    def test_the_log_names_the_time_not_the_newest_directory(self, tmp_path):
        # Restarted from 0: a later directory from an earlier run is not ours.
        for d in ("0", "0.5", "2"):
            (tmp_path / d).mkdir()
        (tmp_path / "log.icoFoam").write_text("Time = 0.25\nTime = 0.5\n\nEnd\n")
        assert last_written_time(str(tmp_path), "log.icoFoam") == "0.5"

    def test_foundation_prints_seconds(self, tmp_path):
        (tmp_path / "0.005").mkdir()
        (tmp_path / "log.foamRun").write_text("Time = 0.005s\n")
        assert last_written_time(str(tmp_path), "log.foamRun") == "0.005"

    def test_a_parallel_run_writes_into_processor0(self, tmp_path):
        for d in ("0", "processor0/0", "processor0/0.75"):
            (tmp_path / d).mkdir(parents=True)
        (tmp_path / "log.icoFoam").write_text("Time = 0.75\n")
        assert last_written_time(str(tmp_path), "log.icoFoam") == "0.75"

    def test_without_a_solver_log_the_directory_changed_since_the_request(self, tmp_path):
        import time as _time

        for d in ("1", "2"):
            (tmp_path / d).mkdir()
        old = _time.time() - 3600
        os.utime(tmp_path / "2", (old, old))  # a later time, written long ago
        assert last_written_time(str(tmp_path), "", since=_time.time() - 60) == "1"
        assert last_written_time(str(tmp_path), "", since=_time.time() + 60) is None
