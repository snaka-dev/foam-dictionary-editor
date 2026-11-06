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


def running_command_names(
    shell_pid: int | None, *, job_control: bool = False, proc_root: str = "/proc"
) -> list[str]:
    """Names of what *shell_pid* is running, for a warning; [] when idle.

    Direct children only: they are what the user started (``simpleFoam``,
    ``mpirun``, ``Allrun``), whereas their own children are implementation
    detail. Plumbing such as ``tee`` is left out of the names -- but a shell
    running nothing *except* plumbing is still busy, so it is reported then
    rather than dropped.

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
    if job_control:
        shell = _read_stat(os.path.join(proc_root, str(shell_pid), "stat"))
        shell_pgrp = shell[2] if shell is not None else shell_pid
        children = [c for c in children if c.pgrp != shell_pgrp]
    names = [c.name for c in children if c.name not in _PLUMBING]
    if not names:
        names = [c.name for c in children]
    return list(dict.fromkeys(names))
