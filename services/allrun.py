# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""A case's ``Allrun`` as a list of steps, each marked from its log.

Behind Tools > Allrun Steps…. ``read_allrun(case_dir)`` reads the script into
:class:`Step` rows: every ``runApplication``/``runParallel`` line is a step,
every other command (``restore0Dir``, ``cp``, ``foamDictionary`` …) a row
without a state. ``step_state`` marks a step from its log by OpenFOAM's own
rule -- ``runApplication`` writes ``log.<app>`` (``log.<app>.<suffix>`` with
``-s``) and *skips a step whose log exists* unless ``-o``/``-a`` is given --
so the view cannot disagree with what the script will do. ``step_command``
and ``run_from_command`` build the line FoDE sends to the terminal: the same
``runApplication`` call with OpenFOAM's ``RunFunctions`` sourced, plus ``-o``
where a log exists, so a re-run really runs.

Measured over the tutorial trees: 72% of v2606's Allruns and 84% of
Foundation 12's are straight lists of these calls. A script with loops or
conditionals still lists the steps it holds (``branches`` is set, and steps
inside a block are ``conditional``); "run from here" is then withheld, since
the lines between steps no longer run in a straight line. Codes, never
sentences -- the UI words them (``ui/allrun_text.py``).
"""
from __future__ import annotations

import os
import re
import shlex
from collections.abc import Callable
from dataclasses import dataclass, field

from services.solver_run import read_solver_info

RUN = "run"
PARALLEL = "parallel"
OTHER = "other"

NOT_RUN = "not_run"
DONE = "done"
FAILED = "failed"
INCOMPLETE = "incomplete"   # a log without "End" or an error: stopped (or, unwatched, running)
RUNNING = "running"         # INCOMPLETE, and a process is still writing the log

# Notes about the script as a whole.
NOTE_BRANCHES = "branches"               # loops/conditionals: steps listed, run-from-here off
NOTE_UNRESOLVED_APP = "unresolved_app"   # a step's application could not be told
NOTE_SUBDIRECTORY = "subdirectory"       # work done in another directory is not followed

# Top-level scripts, in the order one is shown by default. Allrun-parallel is
# the tutorials' parallel twin of Allrun (61 of v2606's cases, 57 beside an
# Allrun); neither is followed into from the other.
SCRIPT_NAMES = ("Allrun", "Allrun-parallel")
# Scripts an Allrun calls that are followed into: ./Allrun.pre, ./Allmesh, …
_FOLLOWED_RE = re.compile(r"^\./(All[\w.-]*)$")
_MAX_DEPTH = 3
# Shell plumbing, not work: not listed as rows.
_PLUMBING = frozenset({
    "printf", "echo", "[", "[[", "test", "!", "continue", "break", "shift", "usage",
    "wait", "trap", "export", "unset", "local", "readonly", "eval", "getopts",
})

_CONTROL_WORDS = frozenset({
    "if", "then", "else", "elif", "fi", "for", "while", "until", "do", "done",
    "case", "esac", "function", "select",
})
_OPENERS = frozenset({"if", "for", "while", "until", "case", "select"})
_CLOSERS = frozenset({"fi", "done", "esac"})
_FUNC_RE = re.compile(r"^\s*[A-Za-z_]\w*\s*\(\s*\)")
_ASSIGN_RE = re.compile(r"^([A-Za-z_]\w*)=(.*)$")
# What the RunFunctions do with their leading options. The value-taking ones
# differ by fork only in which exist; both log to <prefix|log.><app><suffix>.
_FLAG_OPTS = frozenset({"-a", "-append", "-o", "-overwrite"})
_VALUE_OPTS = frozenset({
    "-s", "-suffix", "-d", "-directory", "-p", "-prefix", "-n", "-np", "-decomposeParDict",
})

ReadText = Callable[[str], "str | None"]


@dataclass(frozen=True)
class Step:
    """One command of the script, in order."""

    kind: str           # RUN | PARALLEL | OTHER
    text: str           # the command as written (continuations joined)
    script: str         # the script it came from, case-relative ("Allrun", "Allrun.pre")
    line: int           # 1-based line in that script
    app: str = ""       # the application a RUN/PARALLEL step runs, '' if unknown
    log: str = ""       # its log file, case-relative, '' if unknown
    always_reruns: bool = False   # -o / -a: never skipped by the script
    conditional: bool = False     # inside an if/for/… block
    # The call's own words, for rebuilding the command with -o.
    words: tuple[str, ...] = ()


@dataclass(frozen=True)
class AllrunPlan:
    script: str                    # the top-level script, case-relative
    steps: tuple[Step, ...] = ()
    notes: frozenset[str] = frozenset()

    @property
    def runs(self) -> tuple[Step, ...]:
        return tuple(s for s in self.steps if s.kind != OTHER)

    @property
    def linear(self) -> bool:
        return NOTE_BRANCHES not in self.notes


# ── reading the script ───────────────────────────────────────────────────────

def _read(path: str, read_text: ReadText | None) -> str | None:
    if read_text is not None:
        text = read_text(path)
        if text is not None:
            return text
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return None


def _logical_lines(text: str) -> list[tuple[int, str]]:
    """(first line number, line) with backslash continuations joined."""
    out: list[tuple[int, str]] = []
    buf = ""
    start = 0
    for number, raw in enumerate(text.splitlines(), 1):
        if not buf:
            start = number
        if raw.rstrip().endswith("\\"):
            buf += raw.rstrip()[:-1] + " "
            continue
        buf += raw
        out.append((start, buf))
        buf = ""
    if buf:
        out.append((start, buf))
    return out


def _commands(line: str) -> list[str]:
    """A logical line split at top-level ``;``, ``&&`` and ``||``, comments dropped."""
    parts: list[str] = []
    current = []
    quote = ""
    depth = 0
    i = 0
    while i < len(line):
        c = line[i]
        if quote:
            current.append(c)
            if c == quote:
                quote = ""
        elif c in "'\"":
            quote = c
            current.append(c)
        elif c == "#" and (i == 0 or line[i - 1].isspace()) and depth == 0:
            break
        elif c == "$" and line[i + 1:i + 2] == "(":
            depth += 1
            current.append("$(")
            i += 1
        elif c == ")" and depth:
            depth -= 1
            current.append(c)
        elif depth == 0 and (c == ";" or line[i:i + 2] in ("&&", "||")):
            parts.append("".join(current))
            current = []
            if c != ";":
                i += 1
        else:
            current.append(c)
        i += 1
    parts.append("".join(current))
    return [p.strip() for p in parts if p.strip()]


def _words(command: str) -> list[str] | None:
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        return None


@dataclass
class _Ctx:
    case_dir: str
    read_text: ReadText | None
    application: str | None
    variables: dict[str, str] = field(default_factory=dict)
    notes: set[str] = field(default_factory=set)
    steps: list[Step] = field(default_factory=list)
    # Commands run somewhere else -- inside a `( cd sub && … )` subshell
    # (``subshell``, whole lines skipped) or after `cd sub` (``away``, lines
    # still read so the `cd ..` back is seen). Their steps belong to another
    # case and their logs are not this case's, so they are not listed.
    subshell: int = 0
    away: int = 0


def _resolve_app(word: str, ctx: _Ctx) -> str:
    """The application a step's executable word names, '' when unknown."""
    if word in ("$(getApplication)", "`getApplication`"):
        return ctx.application or ""
    m = re.fullmatch(r"\$\{?(\w+)\}?", word)
    if m:
        return ctx.variables.get(m.group(1), "")
    if "$" in word or "`" in word:
        return ""
    return os.path.basename(word)


def _parse_call(words: list[str], ctx: _Ctx) -> tuple[str, str, bool] | None:
    """(app, log, always_reruns) for a runApplication/runParallel call."""
    i = 1
    suffix = ""
    prefix = "log."
    directory = ""
    always = False
    while i < len(words):
        w = words[i]
        if w in _FLAG_OPTS:
            always = True
        elif w in _VALUE_OPTS and i + 1 < len(words):
            value = words[i + 1]
            if w in ("-s", "-suffix"):
                suffix = "." + value.lstrip(".")
            elif w in ("-p", "-prefix"):
                prefix = value
            elif w in ("-d", "-directory"):
                directory = value.rstrip("/") + "/"
            i += 1
        elif w.startswith("-decompose-dict="):
            pass
        elif w.startswith("$") and i + 1 < len(words) and not w.startswith("$(") and (
            ctx.variables.get(w.strip("${}"), "-").startswith("-")
        ):
            pass  # `$decompDict` holding "-decomposeParDict …": an option, not the app
        else:
            app = _resolve_app(w, ctx)
            log = f"{directory}{prefix}{app}{suffix}" if app else ""
            return app, log, always
        i += 1
    return None


def _walk(script: str, ctx: _Ctx, depth: int) -> None:
    text = _read(os.path.join(ctx.case_dir, script), ctx.read_text)
    if text is None:
        return
    nesting = 0
    in_function = False
    for number, line in _logical_lines(text):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # A subshell opened on this line runs elsewhere until it closes.
        opens = stripped.startswith("(")
        if opens:
            ctx.notes.add(NOTE_SUBDIRECTORY)
            ctx.subshell += 1
        if ctx.subshell and not opens and stripped.startswith(")"):
            ctx.subshell -= 1
            continue
        if ctx.subshell:
            if opens and _balanced(stripped):
                ctx.subshell -= 1
            elif not opens and stripped.endswith(")") and stripped.count(")") > stripped.count("("):
                ctx.subshell -= 1
            continue
        if _FUNC_RE.match(stripped):
            ctx.notes.add(NOTE_BRANCHES)
            in_function = True
        for command in _commands(stripped):
            words = _words(command)
            if not words:
                continue
            first = words[0]
            if first in ("{", "}"):
                if first == "}":
                    in_function = False
                continue
            if first in _CONTROL_WORDS:
                ctx.notes.add(NOTE_BRANCHES)
                if first in _OPENERS:
                    nesting += 1
                elif first in _CLOSERS:
                    nesting = max(0, nesting - 1)
                # `if [ … ]; then runApplication x` -- the command after the keyword
                words = [w for w in words[1:]]
                if first in ("then", "do", "else") and words:
                    first = words[0]
                else:
                    continue
            if first == "cd":
                target = words[1] if len(words) > 1 else ""
                if target.startswith("${0") or target in ("", "."):
                    continue  # the script's own directory
                ctx.notes.add(NOTE_SUBDIRECTORY)
                # `cd ..`/`cd -` comes back; anything else leaves.
                ctx.away = max(0, ctx.away - 1) if target in ("..", "-") else ctx.away + 1
                break  # the rest of this line runs there too
            if ctx.away:
                break
            if first in (".", "source", "set", "exit", "return", "echo", "true", ":"):
                continue
            # `USE_ARC=true runApplication …`: an environment prefix before a
            # command. A value with an open `$(` or `(` was split by shlex and
            # is the whole assignment instead (`t=$(foamListTimes -latestTime)`).
            while (
                len(words) > 1 and _ASSIGN_RE.match(words[0])
                and words[0].count("(") <= words[0].count(")")
            ):
                words = words[1:]
                first = words[0]
            assign = _ASSIGN_RE.match(first)
            if assign:
                # A variable, not work. Only a literal or $(getApplication)
                # is remembered; anything else makes the name unknown.
                name, value = assign.groups()
                if len(words) == 1 and value in ("$(getApplication)", "`getApplication`"):
                    ctx.variables[name] = ctx.application or ""
                elif len(words) == 1 and "$" not in value and "`" not in value and "(" not in value:
                    ctx.variables[name] = value
                else:
                    ctx.variables.pop(name, None)
                continue
            conditional = nesting > 0 or in_function
            if first in _PLUMBING or first.endswith(")") or first.endswith("()"):
                continue  # plumbing, a case label, or a function definition
            followed = _FOLLOWED_RE.match(first)
            if followed and followed.group(1) != script and followed.group(1) not in SCRIPT_NAMES \
                    and depth < _MAX_DEPTH and os.path.isfile(
                os.path.join(ctx.case_dir, followed.group(1))
            ):
                _walk(followed.group(1), ctx, depth + 1)
                continue
            if first in ("runApplication", "runParallel"):
                parsed = _parse_call(words, ctx)
                if parsed is None:
                    continue
                app, log, always = parsed
                if not app:
                    ctx.notes.add(NOTE_UNRESOLVED_APP)
                ctx.steps.append(Step(
                    RUN if first == "runApplication" else PARALLEL, command, script, number,
                    app, log, always, conditional, tuple(words),
                ))
                continue
            ctx.steps.append(Step(OTHER, command, script, number, conditional=conditional,
                                  words=tuple(words)))


def _balanced(text: str) -> bool:
    return text.count("(") <= text.count(")")


def available_scripts(case_dir: str) -> tuple[str, ...]:
    """The top-level scripts the case has, of ``SCRIPT_NAMES``, in that order."""
    return tuple(n for n in SCRIPT_NAMES if os.path.isfile(os.path.join(case_dir, n)))


def read_allrun(
    case_dir: str, read_text: ReadText | None = None, script: str | None = None
) -> AllrunPlan | None:
    """The case's Allrun (or *script*, when it has one) as steps; None when the
    case has none of ``SCRIPT_NAMES``.

    ``read_text(abs_path)`` serves an unsaved editor buffer (None: the disk),
    for the script and for ``system/controlDict``, whose ``application``
    stands in for ``$(getApplication)``.
    """
    names = available_scripts(case_dir)
    if not names:
        return None
    name = script if script in names else names[0]
    control = _read(os.path.join(case_dir, "system", "controlDict"), read_text)
    application = read_solver_info(control).application if control else None
    ctx = _Ctx(case_dir, read_text, application)
    _walk(name, ctx, 0)
    return AllrunPlan(name, tuple(ctx.steps), frozenset(ctx.notes))


# ── state from the log ───────────────────────────────────────────────────────

# Read from the end only: a solver log can be large, and "End" or the error
# that stopped it is in its last lines.
_TAIL_BYTES = 16 * 1024
_FATAL_RE = re.compile(r"FOAM FATAL (?:IO )?ERROR|Foam::sigFpe::sigHandler|Foam::sigSegv")
_END_RE = re.compile(r"^(?:\[\d+\]\s*)?End\s*$", re.M)


def step_state(case_dir: str, step: Step) -> str:
    """``NOT_RUN``, ``DONE``, ``FAILED`` or ``INCOMPLETE`` for a RUN/PARALLEL step."""
    if not step.log:
        return NOT_RUN
    path = os.path.join(case_dir, step.log)
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            if size > _TAIL_BYTES:
                f.seek(size - _TAIL_BYTES)
            tail = f.read().decode("utf-8", "replace")
    except OSError:
        return NOT_RUN
    if _FATAL_RE.search(tail):
        return FAILED
    if _END_RE.search(tail):
        return DONE
    return INCOMPLETE


# ── commands to send ─────────────────────────────────────────────────────────

RUN_FUNCTIONS = '. "${WM_PROJECT_DIR:?}/bin/tools/RunFunctions"'


def _with_overwrite(step: Step) -> str:
    """The step's call with ``-o`` added, so an existing log does not skip it."""
    if step.always_reruns or not step.words:
        return step.text
    words = list(step.words)
    return " ".join(shlex.quote(w) if not w.startswith("$") else w for w in [words[0], "-o", *words[1:]])


def step_command(case_dir: str, step: Step) -> str:
    """The line that runs *step* now, as the script would but never skipped."""
    exists = bool(step.log) and os.path.exists(os.path.join(case_dir, step.log))
    call = _with_overwrite(step) if exists else step.text
    return f"{RUN_FUNCTIONS} && {call}"


def run_from_command(case_dir: str, plan: AllrunPlan, index: int) -> str | None:
    """Every command from ``plan.steps[index]`` to the end, stopping at a failure.

    None for a script with branches: its lines no longer run in a straight
    line, so replaying them in order could run what the script would not.
    A step whose log exists gets ``-o`` -- an earlier failure invalidates
    what follows it, which ``runApplication`` would otherwise skip.
    """
    if not plan.linear or not 0 <= index < len(plan.steps):
        return None
    parts = [RUN_FUNCTIONS]
    for step in plan.steps[index:]:
        if step.kind == OTHER:
            parts.append(step.text)
        else:
            exists = bool(step.log) and os.path.exists(os.path.join(case_dir, step.log))
            parts.append(_with_overwrite(step) if exists else step.text)
    return " && ".join(parts)


# ── a step's standing among the others ───────────────────────────────────────

# Why a DONE step's results may not be what the script now produces.
SUSPECT_AFTER_FAILURE = "after_failure"   # an earlier step failed or did not finish
SUSPECT_OUTDATED = "outdated"             # an earlier step was re-run after it


@dataclass(frozen=True)
class StepStatus:
    state: str          # NOT_RUN / DONE / FAILED / INCOMPLETE / RUNNING; '' for an OTHER row
    suspect: str = ""   # SUSPECT_* for a DONE step that ran on stale input
    # Whether the logs' writers could be seen at all: if so, INCOMPLETE means
    # stopped; if not (no /proc), it may still be running.
    watched: bool = False


def step_states(
    case_dir: str, plan: AllrunPlan, writing: set[str] | None = None
) -> list[StepStatus]:
    """The status of every row of *plan*, in order.

    A DONE step is *suspect* when it cannot be trusted to reflect the steps
    before it: an earlier step failed, is incomplete or never ran (an Allrun
    carries on past a failure -- damBreak's interFoam reports done on fields
    a broken setFields never wrote), or an earlier step's log is newer than
    its own (that step was re-run afterwards). Conditional steps are left
    out of both tests, since the script may never run them.

    *writing* names the case's files some process has open for writing
    (``process_tree.files_written_in``); an INCOMPLETE step whose log is
    among them is RUNNING. None: the writers cannot be seen.
    """
    out: list[StepStatus] = []
    broken = False
    newest_before = 0.0
    for step in plan.steps:
        if step.kind == OTHER:
            out.append(StepStatus(""))
            continue
        state = step_state(case_dir, step)
        if state == INCOMPLETE and writing is not None and step.log in writing:
            state = RUNNING
        try:
            mtime = os.path.getmtime(os.path.join(case_dir, step.log)) if step.log else 0.0
        except OSError:
            mtime = 0.0
        suspect = ""
        if state == DONE:
            if broken:
                suspect = SUSPECT_AFTER_FAILURE
            elif newest_before > mtime + 1.0:
                suspect = SUSPECT_OUTDATED
        out.append(StepStatus(state, suspect, watched=writing is not None))
        if not step.conditional:
            if state != DONE:
                broken = True
            newest_before = max(newest_before, mtime)
    return out
