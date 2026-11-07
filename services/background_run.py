# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Qt-free: runs that keep going after FoDE closes, and how to stop one.

A run started in the Terminal tab dies with FoDE: closing the window ends the
tab's shell, the shell's end hangs up its jobs, and a solver whose output
goes through ``| tee`` dies of a broken pipe the moment ``tee`` does --
``nohup`` in front of the solver protects only the solver. So a background
run is started detached from the terminal altogether::

    setsid -f sh -c 'echo "$$ simpleFoam log.simpleFoam" > .fode-background-run;
                     "$@" > log.simpleFoam 2>&1 < /dev/null;
                     : > .fode-background-run' sh mpirun -np 4 simpleFoam -parallel

- ``setsid -f`` forks into a new session with no controlling terminal, so no
  hangup reaches it, and its parent exits at once, so the run is not even
  the terminal shell's child (which is also why closing FoDE no longer warns
  about it);
- the output goes straight to the log, with no pipe left to break;
- ``< /dev/null``: ``mpirun`` forwards its input to the solver, and a
  detached job reading a terminal would be stopped;
- the small ``sh`` around the run writes its own pid to a hidden file in the
  case (``$$`` -- ``$!`` would name ``setsid``, which has already exited),
  stays alive for as long as the run does, and empties the file at the end
  (an empty or absent file means no run; nothing is ever deleted).
  The command travels as ``"$@"`` so no quoting of it is needed. The
  recorded pid is this ``sh``, not the solver: ``setsid`` made it the
  leader of a process group holding the whole run, so ending the run by
  hand is ``kill -- -<pid>`` -- a plain ``kill <pid>`` ends only the
  wrapper and leaves the solver running.

The terminal then follows the log with ``tail -F --pid``, which ends with
the run; Ctrl+C there stops only the ``tail``.

Stopping one is OpenFOAM's own way: ``stopAt writeNow;`` in controlDict,
which a running solver re-reads (``runTimeModifiable``, on by default), so it
writes the current time step and exits cleanly -- a killed one would lose
that step. The original ``stopAt`` is recorded beside the pid file and put
back once the run has gone; otherwise the next run would stop at its first
step.
"""
from __future__ import annotations

import dataclasses
import json
import os
import re
import shlex
import shutil
import sys
import time

from services.case_loader import detect_time_dirs

PID_FILE = ".fode-background-run"
STOP_FILE = ".fode-stopAt-restore"

# controlDict values under which a solver stops at once: left behind by a
# stop, they would end the next run before it began.
STOPPING_VALUES = frozenset({"writeNow", "noWriteNow", "nextWrite"})

_STOP_AT_RE = re.compile(r"^(\s*stopAt\s+)([A-Za-z]+)(\s*;)", re.MULTILINE)
_MODIFIABLE_RE = re.compile(r"^\s*runTimeModifiable\s+(\w+)\s*;", re.MULTILINE)
_OFF_WORDS = frozenset({"false", "no", "off", "none", "n", "f"})


def background_supported() -> bool:
    """Linux with util-linux's ``setsid`` (``-f`` needs it, not the BSD one)."""
    return sys.platform.startswith("linux") and shutil.which("setsid") is not None


def background_command(tokens: list[str], log_name: str, label: str, prefix: str = "") -> str:
    """The detached run of *tokens* writing *log_name*, then a ``tail`` of it.

    *label* names the run in the pid file (``simpleFoam``, ``Allrun``) for
    the messages that refer to it. *prefix* is a shell prefix run first in
    the foreground (keeping the previous log, cleaning the case). The log is
    emptied before the run starts, so the ``tail`` never shows the previous
    run's output as this one's.
    """
    log = shlex.quote(log_name)
    note = shlex.quote(f"{label} {log_name}")
    script = (
        f'echo "$$" {note} > {PID_FILE}; '
        f'"$@" > {log} 2>&1 < /dev/null; '
        f": > {PID_FILE}"
    )
    wait = (
        f"for i in $(seq 50); do [ -s {PID_FILE} ] && break; sleep 0.1; done; "
        f'if [ -s {PID_FILE} ]; then tail -n +1 -F --pid="$(cut -d" " -f1 {PID_FILE})" {log}; '
        f"else cat {log}; fi"
    )
    return (
        f"{prefix}: > {log} && : > {PID_FILE} && setsid -f sh -c {shlex.quote(script)} sh "
        f"{shlex.join(tokens)} && {wait}"
    )


@dataclasses.dataclass(frozen=True)
class BackgroundRun:
    pid: int
    label: str
    log_name: str


def _pid_alive_in(pid: int, case_dir: str, proc_root: str) -> bool:
    """Whether *pid* is running with its working directory in *case_dir*.

    The directory guards against a reused pid: a stale file from a run that
    ended in a crash must not make an unrelated process look like it.
    """
    try:
        cwd = os.path.realpath(os.readlink(os.path.join(proc_root, str(pid), "cwd")))
    except OSError:
        return False
    case = os.path.realpath(case_dir)
    return cwd == case or cwd.startswith(case.rstrip(os.sep) + os.sep)


def _group_alive_in(pgid: int, case_dir: str, proc_root: str) -> bool:
    """Whether any process of group *pgid* is still working in *case_dir*.

    The recorded pid is the run's wrapper, the leader of its process group.
    A plain ``kill <pid>`` ends only that wrapper and leaves the solver
    running as an orphan in the same group -- which must still count as the
    run, or FoDE would let a second one start beside it.
    """
    try:
        entries = os.listdir(proc_root)
    except OSError:
        return False
    for entry in entries:
        if not entry.isdigit():
            continue
        try:
            with open(os.path.join(proc_root, entry, "stat"), encoding="utf-8", errors="replace") as f:
                fields = f.read().rsplit(")", 1)[1].split()
        except (OSError, IndexError):
            continue
        if len(fields) > 2 and fields[2] == str(pgid) and _pid_alive_in(int(entry), case_dir, proc_root):
            return True
    return False


def active_run(case_dir: str, *, proc_root: str = "/proc") -> BackgroundRun | None:
    """The background run going in *case_dir*, or None.

    Alive while its wrapper is, or -- the wrapper killed on its own -- while
    any process of its group still works in the case. A pid file with
    neither (a crash, a reboot) is stale: it is treated as no run, and
    removed.
    """
    path = os.path.join(case_dir, PID_FILE)
    try:
        with open(path, encoding="utf-8") as f:
            fields = f.read().split()
    except OSError:
        return None
    try:
        pid = int(fields[0])
    except (IndexError, ValueError):
        pid = -1
    if pid > 0 and (
        _pid_alive_in(pid, case_dir, proc_root) or _group_alive_in(pid, case_dir, proc_root)
    ):
        label = fields[1] if len(fields) > 1 else "?"
        log = fields[2] if len(fields) > 2 else ""
        return BackgroundRun(pid, label, log)
    try:
        os.remove(path)
    except OSError:
        pass
    return None


def read_stop_at(control_dict_text: str) -> str | None:
    m = _STOP_AT_RE.search(control_dict_text)
    return m.group(2) if m else None


def run_time_modifiable(control_dict_text: str) -> bool:
    """False only when controlDict turns re-reading off; on is the default."""
    m = _MODIFIABLE_RE.search(control_dict_text)
    return not (m and m.group(1).lower() in _OFF_WORDS)


def with_stop_at(control_dict_text: str, value: str | None) -> str:
    """*control_dict_text* with ``stopAt`` set to *value*, or removed for None.

    Only the value token changes, so the rest of the file -- comments,
    spacing -- is untouched. A missing entry is added at the end.
    """
    if _STOP_AT_RE.search(control_dict_text):
        if value is None:
            return _STOP_AT_RE.sub("", control_dict_text, count=1)
        return _STOP_AT_RE.sub(lambda m: f"{m.group(1)}{value}{m.group(3)}", control_dict_text, count=1)
    if value is None:
        return control_dict_text
    sep = "" if control_dict_text.endswith("\n") or not control_dict_text else "\n"
    return f"{control_dict_text}{sep}\nstopAt          {value};\n"


def request_stop(case_dir: str, run: BackgroundRun | None = None) -> str | None:
    """Set ``stopAt writeNow`` on disk, recording the value it replaces.

    Returns the error text, or None on success. The record also keeps which
    run was asked and when, for the report :func:`finish_stop` gives once it
    has gone. A stop already requested keeps its first record, so pressing
    Stop twice cannot record writeNow as the value to restore.
    """
    path = os.path.join(case_dir, "system", "controlDict")
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        record = os.path.join(case_dir, STOP_FILE)
        if not os.path.exists(record):
            with open(record, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "stopAt": read_stop_at(text),
                        "requested": time.time(),
                        "label": run.label if run else "",
                        "log": run.log_name if run else "",
                    },
                    f,
                )
        _write_in_place(path, with_stop_at(text, "writeNow"))
    except OSError as e:
        return str(e)
    return None


def pending_restore(case_dir: str) -> bool:
    return os.path.exists(os.path.join(case_dir, STOP_FILE))


def stop_requested_at(case_dir: str) -> float | None:
    """When a stop still pending in *case_dir* was asked for (epoch seconds)."""
    record = _read_record(case_dir)
    value = record.get("requested") if record is not None else None
    return float(value) if isinstance(value, (int, float)) else None


@dataclasses.dataclass(frozen=True)
class StopReport:
    """How a stopped run ended, for the message FoDE shows.

    ``restored`` is the ``stopAt`` put back (``"(removed)"`` when the entry
    had been absent), or None when someone changed it from writeNow
    meanwhile -- their choice is kept. ``clean`` is whether the log ends with
    OpenFOAM's ``End`` line; None when there is no solver log to tell (an
    Allrun, whose solver logs elsewhere).
    """

    label: str
    log_name: str
    restored: str | None
    last_time: str | None
    clean: bool | None


def finish_stop(case_dir: str) -> StopReport | None:
    """Put back the ``stopAt`` a stop replaced, once its run has gone.

    None while the run is still going or when no stop is pending.
    """
    record = _read_record(case_dir)
    if record is None or active_run(case_dir) is not None:
        return None
    original = record.get("stopAt", "endTime")
    path = os.path.join(case_dir, "system", "controlDict")
    restored = None
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        if read_stop_at(text) == "writeNow":
            _write_in_place(path, with_stop_at(text, original))
            restored = original or "(removed)"
        os.remove(os.path.join(case_dir, STOP_FILE))
    except OSError:
        return None
    label = str(record.get("label") or "")
    log_name = str(record.get("log") or "")
    clean = None
    if log_name and label != "Allrun":
        clean = _log_ends_cleanly(os.path.join(case_dir, log_name))
    requested = record.get("requested")
    since = float(requested) if isinstance(requested, (int, float)) else None
    last = last_written_time(case_dir, log_name if clean is not None else "", since)
    return StopReport(label, log_name, restored, last, clean)


_TIME_LINE_RE = re.compile(r"^Time = ([-+0-9.eE]+)s?\s*$", re.MULTILINE)


def last_written_time(case_dir: str, log_name: str = "", since: float | None = None) -> str | None:
    """The time directory a run wrote last, or None.

    Not simply the newest time directory: a run restarted from an earlier
    time leaves later directories of a previous run in place. The solver's
    own log says where it stopped -- its last ``Time = t`` line (``t s`` in
    Foundation v11+), which writeNow then writes -- so that is used when
    such a directory exists, at the case root or in processor0 for a
    parallel run. Otherwise (no solver log, as for Allrun) the directory
    modified last, if that was after *since*.
    """
    roots = [case_dir]
    proc0 = os.path.join(case_dir, "processor0")
    if os.path.isdir(proc0):
        roots.append(proc0)
    if log_name:
        try:
            with open(os.path.join(case_dir, log_name), "rb") as f:
                f.seek(0, os.SEEK_END)
                f.seek(max(0, f.tell() - 65536))
                tail = f.read().decode("utf-8", "replace")
        except OSError:
            tail = ""
        found = _TIME_LINE_RE.findall(tail)
        if found:
            last = found[-1]
            for root in roots:
                for name in detect_time_dirs(root):
                    if float(name) == float(last):
                        return name
    newest: tuple[float, str] | None = None
    for root in roots:
        for name in detect_time_dirs(root):
            try:
                mtime = os.path.getmtime(os.path.join(root, name))
            except OSError:
                continue
            if since is not None and mtime < since - 1:
                continue
            if newest is None or mtime > newest[0]:
                newest = (mtime, name)
    return newest[1] if newest else None


def _log_ends_cleanly(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 4096))
            tail = f.read().decode("utf-8", "replace")
    except OSError:
        return False
    return "End" in (line.strip() for line in tail.splitlines()[-10:])


def _read_record(case_dir: str) -> dict | None:
    path = os.path.join(case_dir, STOP_FILE)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            record = json.load(f)
    except (OSError, ValueError):
        record = None
    # An unreadable record still means a stop is pending: restore endTime.
    return record if isinstance(record, dict) else {"stopAt": "endTime"}


def _write_in_place(path: str, text: str) -> None:
    """Rewrite *path* in place, keeping its inode.

    Not the usual write-then-rename: with ``fileModificationChecking
    inotify`` a running solver watches the file itself, and a rename would
    swap a new file in under the watch rather than modify the watched one.
    """
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
