# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Qt-free: what is running under a process, read from ``/proc``.

Used to tell whether the Terminal tab's shell is busy -- a solver, Allrun or
a hand-typed command still in progress -- before FoDE does something that
ends that shell (closing the window, switching terminal mode). Linux only by
construction: where there is no ``/proc``, nothing is reported, which is the
safe failure, since the caller then behaves exactly as it did before this
check existed.
"""
from __future__ import annotations

import dataclasses
import os

# Helpers that only ever run beside the real work -- the `tee log.<tool>`
# half of every Tools-menu command -- so they are never what a warning names.
_PLUMBING = frozenset({"tee"})

# Programs that only watch: the ``tail -F`` following a background run (see
# services/background_run.py), or one typed by hand. Ending one loses
# nothing, so they never count as running -- closing FoDE does not ask about
# them -- and the Terminal tab stops them before sending a new command,
# since the shell would otherwise not read it until they ended.
FOLLOWERS = frozenset({"tail"})


@dataclasses.dataclass(frozen=True)
class ProcessInfo:
    pid: int
    name: str
    pgrp: int


def _read_stat(path: str) -> tuple[str, int, int] | None:
    """``(comm, ppid, pgrp)`` from one ``/proc/<pid>/stat``, or None if unreadable.

    ``comm`` sits in parentheses and may itself contain spaces or ``)``, so
    the fields after it are found from the *last* ``)``.
    """
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return None
    open_at = text.find("(")
    close_at = text.rfind(")")
    if open_at < 0 or close_at < open_at:
        return None
    fields = text[close_at + 1:].split()  # state ppid pgrp ...
    if len(fields) < 3:
        return None
    try:
        return text[open_at + 1:close_at], int(fields[1]), int(fields[2])
    except ValueError:
        return None


def child_processes(pid: int, proc_root: str = "/proc") -> list[ProcessInfo]:
    """The direct children of *pid*, sorted by pid; [] if none or no ``/proc``."""
    try:
        entries = os.listdir(proc_root)
    except OSError:
        return []
    children = []
    for entry in entries:
        if not entry.isdigit():
            continue
        stat = _read_stat(os.path.join(proc_root, entry, "stat"))
        if stat is not None and stat[1] == pid:
            children.append(ProcessInfo(int(entry), stat[0], stat[2]))
    return sorted(children, key=lambda p: p.pid)


def _user_jobs(
    shell_pid: int, children: list[ProcessInfo], job_control: bool, proc_root: str
) -> list[ProcessInfo]:
    """*children* less the shell's own helpers (see running_command_names)."""
    if not job_control:
        return children
    shell = _read_stat(os.path.join(proc_root, str(shell_pid), "stat"))
    shell_pgrp = shell[2] if shell is not None else shell_pid
    return [c for c in children if c.pgrp != shell_pgrp]


def follower_pids(
    shell_pid: int | None, *, job_control: bool = False, proc_root: str = "/proc"
) -> list[int]:
    """Pids of the ``FOLLOWERS`` *shell_pid* is running, to stop before a command."""
    if not shell_pid:
        return []
    children = _user_jobs(shell_pid, child_processes(shell_pid, proc_root), job_control, proc_root)
    return [c.pid for c in children if c.name in FOLLOWERS]


def running_command_names(
    shell_pid: int | None, *, job_control: bool = False, proc_root: str = "/proc"
) -> list[str]:
    """Names of what *shell_pid* is running, for a warning; [] when idle.

    Direct children only: they are what the user started (``simpleFoam``,
    ``mpirun``, ``Allrun``), whereas their own children are implementation
    detail. Plumbing such as ``tee`` is left out of the names -- but a shell
    running nothing *except* plumbing is still busy, so it is reported then
    rather than dropped. ``FOLLOWERS`` are left out altogether.

    ``job_control`` is for an interactive shell (the xterm terminal's bash on
    a PTY). That shell also forks helpers of its own -- a prompt's command
    substitutions, its rc file's -- which would read as "running" for an
    instant. Job control tells them apart: every job the user starts,
    foreground or ``&``, gets a process group of its own, while the shell's
    helpers stay in the shell's group. A non-interactive shell (the Simple
    terminal's ``bash --norc``) has no prompt, no rc file and no job control,
    so every child it has is the user's.
    """
    if not shell_pid:
        return []
    children = child_processes(shell_pid, proc_root)
    children = [c for c in _user_jobs(shell_pid, children, job_control, proc_root)
                if c.name not in FOLLOWERS]
    names = [c.name for c in children if c.name not in _PLUMBING]
    if not names:
        names = [c.name for c in children]
    return list(dict.fromkeys(names))


# Programs that can sit in a case directory without writing its results: an
# idle shell, a pager or editor on a log, a plot of one, a viewer. Anything
# else found working there is assumed to be writing -- a reconstructPar in
# another terminal, a solver started by hand -- since that is the case a
# deletion must not race.
_HARMLESS_IN_CASE = frozenset(
    {
        "bash", "sh", "dash", "zsh", "fish", "ksh", "tcsh", "csh",
        "less", "more", "most", "tail", "head", "cat", "watch", "top", "htop",
        "vi", "vim", "nvim", "view", "emacs", "nano", "gedit",
        "gnuplot", "gnuplot_qt", "paraview", "pvpython", "pvserver",
        "code", "xdg-open",
    }
)


def _inside(path: str, directory: str) -> bool:
    return path == directory or path.startswith(directory.rstrip(os.sep) + os.sep)


def _case_arg(cmdline: list[str], cwd: str | None) -> str | None:
    """The directory an OpenFOAM ``-case <dir>`` argument names, resolved."""
    for i, arg in enumerate(cmdline[:-1]):
        if arg == "-case":
            target = cmdline[i + 1]
            if cwd is not None and not os.path.isabs(target):
                target = os.path.join(cwd, target)
            return os.path.realpath(target)
    return None


def processes_in_directory(
    directory: str, *, exclude_tree_of: int | None = None, proc_root: str = "/proc"
) -> list[ProcessInfo]:
    """Processes working in *directory*: running there, or given it as ``-case``.

    Read from each process's ``cwd`` link and command line, so only the
    current user's processes are seen -- another user's links are not
    readable, which is fine: they could not write this user's case either.
    Programs in ``_HARMLESS_IN_CASE`` are left out, and so is the whole
    process tree under ``exclude_tree_of`` (FoDE itself: its own terminal is
    checked separately, and its helper processes inherit its directory).
    [] where there is no ``/proc``.
    """
    try:
        entries = [e for e in os.listdir(proc_root) if e.isdigit()]
    except OSError:
        return []
    target = os.path.realpath(directory)
    stats: dict[int, tuple[str, int, int]] = {}
    for entry in entries:
        stat = _read_stat(os.path.join(proc_root, entry, "stat"))
        if stat is not None:
            stats[int(entry)] = stat

    def ours(pid: int) -> bool:
        seen = set()
        while pid > 1 and pid not in seen:
            if pid == exclude_tree_of:
                return True
            seen.add(pid)
            stat = stats.get(pid)
            if stat is None:
                return False
            pid = stat[1]
        return False

    found = []
    for pid, (name, _ppid, pgrp) in sorted(stats.items()):
        if name in _HARMLESS_IN_CASE:
            continue
        base = os.path.join(proc_root, str(pid))
        try:
            cwd: str | None = os.path.realpath(os.readlink(os.path.join(base, "cwd")))
        except OSError:
            cwd = None
        try:
            with open(os.path.join(base, "cmdline"), "rb") as f:
                cmdline = [a.decode("utf-8", "replace") for a in f.read().split(b"\0") if a]
        except OSError:
            cmdline = []
        case = _case_arg(cmdline, cwd)
        here = (cwd is not None and _inside(cwd, target)) or (
            case is not None and _inside(case, target)
        )
        if here and not (exclude_tree_of is not None and ours(pid)):
            found.append(ProcessInfo(pid, name, pgrp))
    return found
