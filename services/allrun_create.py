# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Write an ``Allrun`` (and ``Allclean``) for a case that has none.

Behind Tools > Create Allrun from Logs…. The steps come from the case's own
``log.*`` files first: OpenFOAM writes the same header at the top of every log
in both forks (``argList.C``) -- ``Exec`` with the command line, ``Date`` and
``Time`` when it started, ``nProcs`` -- so the logs say what ran, with which
options, serial or parallel, and in what order. Where a step the case clearly
needs left no log (a ``blockMeshDict`` but no ``log.blockMesh``) it is
*suggested* from the dictionary and marked as such; with no logs at all the
whole list is such a suggestion.

What is written follows the tutorials' form (``cd "${0%/*}"``, ``RunFunctions``,
``runApplication``/``runParallel``) and calls only helpers the installed fork
has: ``restore0Dir`` and ``cleanCase0`` are OpenCFD's alone, so a Foundation
or unknown installation gets the plain commands they stand for.

The Allclean is where a careless script loses data: ``cleanCase`` deletes
``constant/polyMesh`` in both forks, so when no step of the Allrun makes the
mesh the Allclean keeps it and removes the run's output by hand instead.

Codes, never sentences -- the UI words them (``ui/allrun_create_text.py``).
See DEVELOPER.md's "Create Allrun from Logs".
"""
from __future__ import annotations

import os
import re
import shlex
from dataclasses import dataclass, replace
from datetime import datetime

from services import allrun as ar
from services.solver_run import read_solver_info

# Where a row came from.
SOURCE_LOG = "log"           # a log.* file's header
SOURCE_DICT = "dict"         # suggested from a dictionary the case holds
SOURCE_ADDED = "added"       # a helper FoDE adds (restore 0/ from 0.orig/)
SOURCE_USER = "user"         # a command the user typed in

# Why a row is marked, or unticked.
MARK_FAILED = "failed"               # its log holds an error: unticked
MARK_INCOMPLETE = "incomplete"       # its log has neither End nor an error
MARK_READ_ONLY = "read_only"         # checkMesh & co. change nothing: unticked
MARK_NO_LOG = "no_log"               # suggested: the case needs it, no log says so
MARK_GUESSED = "guessed"             # suggested, and its position is a guess
MARK_MOVED = "moved"                 # moved from where its log's time put it
MARK_RESTORE = "restore"             # the added restore-0/ row
MARK_PARALLEL_ONLY = "parallel_only"  # added for Allrun-parallel: decomposePar, reconstructPar
MARK_USER = "user"                   # typed in by the user

# Logs left out, and why.
SKIP_NO_HEADER = "no_header"         # not an OpenFOAM application's log
SKIP_EARLIER_RUN = "earlier_run"     # FoDE's log.<app>.partN: an earlier run of a listed step

# Notes about the proposal as a whole.
NOTE_FROM_DICTIONARIES = "from_dictionaries"   # no logs: every step is a suggestion
NOTE_LIMITS = "limits"                         # commands without logs are not included
NOTE_RESTORES_ZERO = "restores_zero"           # 0/ is restored from 0.orig/: edit 0.orig/
NOTE_NO_ZERO_ORIG = "no_zero_orig"             # a step rewrites 0/ and there is no 0.orig/
NOTE_ORIG_FILES = "orig_files"                 # Foundation's cleanCase deletes a *.orig file's twin

# The scripts a parallel split writes, beside the serial Allrun.
SCRIPT_ALLRUN = "Allrun"
SCRIPT_PRE = "Allrun.pre"
SCRIPT_PARALLEL = "Allrun-parallel"

FORK_OPENCFD = "opencfd"
FORK_FOUNDATION = "foundation"

# Applications that create a mesh from nothing; without one ticked, the
# Allclean must not delete constant/polyMesh.
_MESH_MAKERS = frozenset({
    "blockMesh", "extrudeMesh", "extrude2DMesh", "foamyHexMesh", "foamyQuadMesh",
    "cartesianMesh", "cartesian2DMesh", "tetMesh", "pMesh",
})
# Applications that only change the mesh (or the surfaces it is built from):
# 0/ is restored after them, the way the tutorials do, so their patches do
# not end up in the initial fields twice.
_MESH_TOOLS = _MESH_MAKERS | frozenset({
    "surfaceFeatureExtract", "surfaceFeatures", "snappyHexMesh", "topoSet",
    "setsToZones", "createBaffles", "mergeOrSplitBaffles", "createPatch",
    "refineMesh", "refineHexMesh", "refineWallLayer", "transformPoints",
    "surfaceTransformPoints", "mirrorMesh", "mergeMeshes", "stitchMesh",
    "subsetMesh", "collapseEdges", "polyDualMesh", "renumberMesh", "checkMesh",
    "splitMeshRegions", "extrudeToRegionMesh", "moveDynamicMesh", "autoPatch",
    "surfaceCheck", "surfaceMeshTriangulate", "surfaceConvert",
})
# Change nothing a later step reads: listed, unticked.
_READ_ONLY = frozenset({"checkMesh", "foamListTimes", "surfaceCheck", "foamInfo"})
# Rewrite 0/ in place: without 0.orig/ a second run starts from the first's output.
_WRITE_FIELDS = frozenset({
    "setFields", "snappyHexMesh", "mapFields", "applyBoundaryLayer", "createPatch",
    "changeDictionary", "createBaffles",
})
_RECONSTRUCT = frozenset({"reconstructPar", "reconstructParMesh"})
# Steps that belong to a parallel run only: Allrun-parallel, never the serial Allrun.
_PARALLEL_ONLY = _RECONSTRUCT | frozenset({"decomposePar"})
# Options OpenFOAM prints in Exec that the script must not repeat.
_DROP_FLAGS = frozenset({"-parallel"})
_DROP_VALUED = frozenset({"-case"})

_PART_RE = re.compile(r"^part\d+$")
_HEADER_BYTES = 8 * 1024
_MONTHS = {m: i for i, m in enumerate(
    ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), 1
)}


@dataclass(frozen=True)
class LogHeader:
    """What a log's header says about the run that wrote it."""

    log: str                     # case-relative name, "log.topoSet.1"
    app: str
    args: tuple[str, ...]        # without -parallel and -case
    nprocs: int
    started: datetime | None


@dataclass(frozen=True)
class Proposed:
    """One row of the checklist: a line of the Allrun to be."""

    kind: str                    # allrun.RUN | PARALLEL | OTHER
    app: str = ""
    args: tuple[str, ...] = ()
    suffix: str = ""             # runApplication -s
    nprocs: int = 0              # PARALLEL: the run's process count
    text: str = ""               # OTHER: the command itself
    source: str = SOURCE_LOG
    log: str = ""                # SOURCE_LOG: the log it came from
    origin: str = ""             # SOURCE_DICT: the dictionary that suggests it
    marks: tuple[str, ...] = ()
    checked: bool = True


@dataclass(frozen=True)
class Proposal:
    steps: tuple[Proposed, ...]
    skipped: tuple[tuple[str, str], ...] = ()   # (log name, SKIP_*)
    notes: frozenset[str] = frozenset()
    orig_twins: tuple[str, ...] = ()            # files Foundation's cleanCase deletes
    fork: str | None = None
    decompose_n: int | None = None              # numberOfSubdomains, if readable
    has_zero_orig: bool = False
    solver: str = ""                            # controlDict's application


# ── log headers ──────────────────────────────────────────────────────────────

def _words(exec_line: str) -> list[str]:
    """Exec's words. OpenFOAM joins argv with spaces and no quoting, so a
    parenthesised value (``-fields (U p)``) is rejoined until it balances."""
    out: list[str] = []
    depth = 0
    for token in exec_line.split():
        if depth > 0:
            out[-1] += " " + token
        else:
            out.append(token)
        depth += token.count("(") - token.count(")")
        depth = max(depth, 0)
    return out


def _started(date: str, time: str) -> datetime | None:
    # "Nov 06 2026" / "10:59:14", the same in both forks (clock::date/clockTime).
    m = re.fullmatch(r"([A-Z][a-z]{2})\s+(\d{1,2})\s+(\d{4})", date.strip())
    t = re.fullmatch(r"(\d{1,2}):(\d{2}):(\d{2})", time.strip())
    if not m or not t or m.group(1) not in _MONTHS:
        return None
    try:
        return datetime(
            int(m.group(3)), _MONTHS[m.group(1)], int(m.group(2)),
            int(t.group(1)), int(t.group(2)), int(t.group(3)),
        )
    except ValueError:
        return None


def read_log_header(case_dir: str, name: str) -> LogHeader | None:
    """The header of ``case_dir/name``; None for a log without one."""
    try:
        with open(os.path.join(case_dir, name), "rb") as f:
            head = f.read(_HEADER_BYTES).decode("utf-8", "replace")
    except OSError:
        return None
    fields: dict[str, str] = {}
    for line in head.splitlines():
        m = re.match(r"^(Exec|Date|Time|nProcs)\s*:\s?(.*)$", line)
        if m and m.group(1) not in fields:
            fields[m.group(1)] = m.group(2).strip()
    words = _words(fields.get("Exec", ""))
    if not words:
        return None
    args: list[str] = []
    rest = words[1:]
    i = 0
    while i < len(rest):
        word = rest[i]
        if word in _DROP_FLAGS:
            pass
        elif word in _DROP_VALUED:
            i += 1
        else:
            args.append(word)
        i += 1
    try:
        nprocs = int(fields.get("nProcs", "1"))
    except ValueError:
        nprocs = 1
    return LogHeader(
        log=name,
        app=os.path.basename(words[0]),
        args=tuple(args),
        nprocs=nprocs,
        started=_started(fields.get("Date", ""), fields.get("Time", "")),
    )


def _log_suffix(name: str, app: str) -> str:
    prefix = f"log.{app}"
    if name == prefix:
        return ""
    if name.startswith(prefix + "."):
        return name[len(prefix) + 1:]
    return ""


def _log_names(case_dir: str) -> list[str]:
    try:
        names = os.listdir(case_dir)
    except OSError:
        return []
    return sorted(
        n for n in names
        if n.startswith("log.") and os.path.isfile(os.path.join(case_dir, n))
    )


# ── the case's dictionaries ──────────────────────────────────────────────────

def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _exists(case_dir: str, *rel: str) -> str:
    """The first of *rel* present in the case, case-relative; '' if none."""
    for r in rel:
        if os.path.isfile(os.path.join(case_dir, r)):
            return r
    return ""


def decompose_subdomains(case_dir: str) -> int | None:
    text = _read(os.path.join(case_dir, "system", "decomposeParDict"))
    m = re.search(r"^\s*numberOfSubdomains\s+(\d+)\s*;", text, re.M)
    return int(m.group(1)) if m else None


def _has_processor_dirs(case_dir: str) -> bool:
    try:
        return any(
            n.startswith("processor") and os.path.isdir(os.path.join(case_dir, n))
            for n in os.listdir(case_dir)
        )
    except OSError:
        return False


def _application(case_dir: str) -> str:
    text = _read(os.path.join(case_dir, "system", "controlDict"))
    return (read_solver_info(text).application or "") if text else ""


# Where a suggested step goes among the others, by the order the tutorials use.
_RANK = {
    "blockMesh": 0, "surfaceFeatureExtract": 1, "surfaceFeatures": 1,
    "snappyHexMesh": 2, "topoSet": 3, "setFields": 4, "decomposePar": 5,
}
_SOLVER_RANK = 6
_RECONSTRUCT_RANK = 7


def _dictionary_steps(case_dir: str, solver: str) -> list[Proposed]:
    """The steps the case's dictionaries suggest, in the tutorials' order."""
    out: list[Proposed] = []

    def add(app: str, origin: str, *args: str, marks: tuple[str, ...] = ()) -> None:
        out.append(Proposed(
            kind=ar.RUN, app=app, args=args, source=SOURCE_DICT, origin=origin,
            marks=(MARK_NO_LOG, *marks),
        ))

    block = _exists(case_dir, "system/blockMeshDict", "constant/polyMesh/blockMeshDict")
    if block:
        add("blockMesh", block)
    snappy = _exists(case_dir, "system/snappyHexMeshDict")
    if snappy:
        features = _exists(case_dir, "system/surfaceFeatureExtractDict")
        if features:
            add("surfaceFeatureExtract", features)
        else:
            features = _exists(case_dir, "system/surfaceFeaturesDict")
            if features:
                add("surfaceFeatures", features)
        add("snappyHexMesh", snappy, "-overwrite")
    topo = _exists(case_dir, "system/topoSetDict")
    if topo:
        # Before or after snappyHexMesh, cellZones for the solver or sets
        # for setFields: the dictionary alone cannot say.
        add("topoSet", topo, marks=(MARK_GUESSED,))
    fields = _exists(case_dir, "system/setFieldsDict")
    if fields:
        add("setFields", fields)
    # A meshing-only tutorial (flange) names its mesher as the application:
    # it is already a step above, and not a solver to run after it.
    if solver and solver not in _MESH_TOOLS and all(s.app != solver for s in out):
        n = decompose_subdomains(case_dir)
        parallel = (
            n is not None and n > 1 and _has_processor_dirs(case_dir)
        )
        if parallel:
            add("decomposePar", "system/decomposeParDict", "-force")
            out.append(Proposed(
                kind=ar.PARALLEL, app=solver, nprocs=n or 0, source=SOURCE_DICT,
                origin="system/controlDict", marks=(MARK_NO_LOG,),
            ))
            # Most parallel tutorials end with it (41 of v2606's 61
            # Allrun-parallel scripts): the results in time directories.
            add("reconstructPar", "system/decomposeParDict")
        else:
            add(solver, "system/controlDict")
    return out


# ── putting the list together ────────────────────────────────────────────────

def _from_logs(case_dir: str) -> tuple[list[tuple[LogHeader, Proposed]], list[tuple[str, str]]]:
    headers: list[LogHeader] = []
    skipped: list[tuple[str, str]] = []
    for name in _log_names(case_dir):
        header = read_log_header(case_dir, name)
        if header is None:
            skipped.append((name, SKIP_NO_HEADER))
        else:
            headers.append(header)
    # FoDE's Run Solver keeps an earlier log as log.<app>.partN: the same
    # step run before, not a step of its own -- unless it is all that is left.
    _Key = tuple[str, tuple[str, ...], bool]
    commands: dict[_Key, LogHeader] = {}
    for h in headers:
        if not _PART_RE.match(_log_suffix(h.log, h.app)):
            commands.setdefault((h.app, h.args, h.nprocs > 1), h)
    kept: list[LogHeader] = []
    parts: dict[_Key, LogHeader] = {}
    for h in headers:
        key = (h.app, h.args, h.nprocs > 1)
        if _PART_RE.match(_log_suffix(h.log, h.app)):
            if key in commands:
                skipped.append((h.log, SKIP_EARLIER_RUN))
                continue
            latest = parts.get(key)
            if latest is not None:
                # Keep the newest of several part logs.
                if (h.started or datetime.min) >= (latest.started or datetime.min):
                    skipped.append((latest.log, SKIP_EARLIER_RUN))
                    parts[key] = h
                else:
                    skipped.append((h.log, SKIP_EARLIER_RUN))
                continue
            parts[key] = h
        else:
            kept.append(h)
    kept.extend(parts.values())

    def mtime(h: LogHeader) -> float:
        try:
            return os.path.getmtime(os.path.join(case_dir, h.log))
        except OSError:
            return 0.0

    # Start time first; a tie (the header has whole seconds) by when it ended.
    kept.sort(key=lambda h: (h.started or datetime.min, mtime(h), h.log))
    rows: list[tuple[LogHeader, Proposed]] = []
    for h in kept:
        suffix = _log_suffix(h.log, h.app)
        if _PART_RE.match(suffix):
            suffix = ""
        probe = ar.Step(kind=ar.RUN, text="", script="", line=0, app=h.app, log=h.log)
        state = ar.step_state(case_dir, probe)
        marks: list[str] = []
        checked = True
        if state == ar.FAILED:
            marks.append(MARK_FAILED)
            checked = False
        elif state == ar.INCOMPLETE:
            marks.append(MARK_INCOMPLETE)
        if h.app in _READ_ONLY:
            marks.append(MARK_READ_ONLY)
            checked = False
        rows.append((h, Proposed(
            kind=ar.PARALLEL if h.nprocs > 1 else ar.RUN,
            app=h.app, args=h.args, suffix=suffix,
            nprocs=h.nprocs if h.nprocs > 1 else 0,
            source=SOURCE_LOG, log=h.log, marks=tuple(marks), checked=checked,
        )))
    return rows, skipped


def _move_reconstructs(steps: list[Proposed]) -> list[Proposed]:
    """A reconstructPar run before a later parallel run goes after the last one:
    in a fresh run there is nothing to reconstruct until the solver has run."""
    last_parallel = max((i for i, s in enumerate(steps) if s.kind == ar.PARALLEL), default=-1)
    early = [i for i, s in enumerate(steps) if s.app in _RECONSTRUCT and i < last_parallel]
    if not early:
        return steps
    moved = [replace(steps[i], marks=(*steps[i].marks, MARK_MOVED)) for i in early]
    rest = [s for i, s in enumerate(steps) if i not in early]
    at = max(i for i, s in enumerate(rest) if s.kind == ar.PARALLEL) + 1
    return rest[:at] + moved + rest[at:]


def _order(step: Proposed, solver: str) -> float | None:
    """Where *step* sits in the tutorials' order; None if it has no place."""
    if step.app in _RANK:
        return _RANK[step.app]
    if step.app and step.app == solver:
        return _SOLVER_RANK
    if step.app in _RECONSTRUCT:
        return _RECONSTRUCT_RANK
    if step.app in _MESH_TOOLS:
        return _RANK["topoSet"] + 0.5   # createBaffles & co.: after meshing, before fields
    return None


def _merge(steps: list[Proposed], suggested: list[Proposed], solver: str) -> list[Proposed]:
    """Add each suggested step no log covers, after the last step that ranks before it."""
    have = {s.app for s in steps}
    out = list(steps)
    for s in suggested:
        if s.app in have or s.app == "decomposePar":
            continue
        if s.app in _RECONSTRUCT and not any(x.kind == ar.PARALLEL for x in out):
            continue   # nothing ran in parallel: nothing to reconstruct
        if s.app == solver and s.kind == ar.PARALLEL and not any(
            x.kind == ar.PARALLEL for x in out
        ):
            s = replace(s, kind=ar.RUN, nprocs=0)
        rank = _order(s, solver)
        at = 0
        for i, x in enumerate(out):
            r = _order(x, solver)
            if rank is not None and r is not None and r < rank:
                at = i + 1
        out.insert(at, s)
        have.add(s.app)
    # A parallel run needs the case decomposed first.
    first_parallel = next((i for i, x in enumerate(out) if x.kind == ar.PARALLEL), None)
    if first_parallel is not None and "decomposePar" not in have:
        out.insert(first_parallel, Proposed(
            kind=ar.RUN, app="decomposePar", args=("-force",), source=SOURCE_DICT,
            origin="system/decomposeParDict", marks=(MARK_NO_LOG,),
        ))
    return out


def restore_row(fork: str | None) -> Proposed:
    text = "restore0Dir" if fork == FORK_OPENCFD else "rm -rf 0 && cp -r 0.orig 0"
    return Proposed(kind=ar.OTHER, text=text, source=SOURCE_ADDED, marks=(MARK_RESTORE,))


def _insert_restore(steps: list[Proposed], fork: str | None) -> list[Proposed]:
    """Restore 0/ before the first step that is not a mesh tool -- after meshing,
    as the tutorials do, so meshing does not write its patches into 0/."""
    at = next((i for i, s in enumerate(steps) if s.app not in _MESH_TOOLS), len(steps))
    return [*steps[:at], restore_row(fork), *steps[at:]]


def _orig_twins(case_dir: str) -> list[str]:
    """Files Foundation's cleanCase deletes: the twin of every ``*.orig`` file."""
    out: list[str] = []
    for root, dirs, files in os.walk(case_dir):
        dirs[:] = [d for d in dirs if not d.startswith(".") and not d.startswith("processor")]
        for f in files:
            if f.endswith(".orig"):
                twin = os.path.join(root, f[:-5])
                for t in (twin, twin + ".gz"):
                    if os.path.isfile(t):
                        out.append(os.path.relpath(t, case_dir))
    return sorted(out)


def propose(case_dir: str, fork: str | None = None) -> Proposal:
    """The steps for a new Allrun, from the logs first, then the dictionaries."""
    solver = _application(case_dir)
    rows, skipped = _from_logs(case_dir)
    suggested = _dictionary_steps(case_dir, solver)
    notes: set[str] = set()
    if rows:
        steps = _move_reconstructs([p for _, p in rows])
        steps = _merge(steps, suggested, solver)
        notes.add(NOTE_LIMITS)
    else:
        steps = suggested
        notes.add(NOTE_FROM_DICTIONARIES)
    has_zero_orig = os.path.isdir(os.path.join(case_dir, "0.orig"))
    if has_zero_orig:
        steps = _insert_restore(steps, fork)
        notes.add(NOTE_RESTORES_ZERO)
    elif os.path.isdir(os.path.join(case_dir, "0")) and any(s.app in _WRITE_FIELDS for s in steps):
        notes.add(NOTE_NO_ZERO_ORIG)
    twins: list[str] = []
    if fork == FORK_FOUNDATION:
        twins = _orig_twins(case_dir)
        if twins:
            notes.add(NOTE_ORIG_FILES)
    return Proposal(
        steps=tuple(steps), skipped=tuple(skipped), notes=frozenset(notes),
        orig_twins=tuple(twins), fork=fork, decompose_n=decompose_subdomains(case_dir),
        has_zero_orig=has_zero_orig, solver=solver,
    )


# ── writing the scripts ──────────────────────────────────────────────────────

_RUN_HEADER = """\
#!/bin/sh
cd "${0%/*}" || exit                                # Run from this directory
. ${WM_PROJECT_DIR:?}/bin/tools/RunFunctions        # Tutorial run functions
#------------------------------------------------------------------------------
"""
_CLEAN_HEADER = """\
#!/bin/sh
cd "${0%/*}" || exit                                # Run from this directory
. ${WM_PROJECT_DIR:?}/bin/tools/CleanFunctions      # Tutorial clean functions
#------------------------------------------------------------------------------
"""
_FOOTER = "\n#------------------------------------------------------------------------------\n"


def _quote(word: str) -> str:
    return word if word.startswith("$") else shlex.quote(word)


def step_line(step: Proposed, decompose_n: int | None = None) -> str:
    """The Allrun line for *step*."""
    if step.kind == ar.OTHER:
        return step.text
    words = ["runParallel" if step.kind == ar.PARALLEL else "runApplication"]
    if step.suffix:
        words += ["-s", step.suffix]
    if step.kind == ar.PARALLEL and step.nprocs and step.nprocs != decompose_n:
        # runParallel takes the count from system/decomposeParDict otherwise.
        words += ["-np", str(step.nprocs)]
    words.append(step.app)
    return " ".join([*words[:-1], _quote(words[-1]), *(_quote(a) for a in step.args)])


def makes_mesh(steps: list[Proposed] | tuple[Proposed, ...]) -> bool:
    return any(s.checked and s.app in _MESH_MAKERS for s in steps)


def _all_suggested(ticked: list[Proposed]) -> bool:
    return bool(ticked) and not any(s.source == SOURCE_LOG for s in ticked)


def _render(
    rows: list[Proposed], proposal: Proposal, all_suggested: bool, lead: str = ""
) -> str:
    lines = [_RUN_HEADER]
    # With no logs at all every line is a suggestion: say it once.
    if all_suggested:
        lines.append(
            "# Suggested from the case's dictionaries, not from its logs:\n"
            "# check the steps and their order before running.\n"
        )
    if lead:
        lines.append("\n" + lead + "\n")
    for step in rows:
        line = step_line(step, proposal.decompose_n)
        if step.source == SOURCE_DICT and not all_suggested:
            line += "    # suggested: no log found"
        elif MARK_MOVED in step.marks:
            line += "    # moved after the parallel run"
        lines.append("\n" + line + "\n")
    return "".join(lines) + _FOOTER


def render_allrun(steps: list[Proposed] | tuple[Proposed, ...], proposal: Proposal) -> str:
    """The Allrun for the ticked *steps*, in their order."""
    ticked = [s for s in steps if s.checked]
    return _render(ticked, proposal, _all_suggested(ticked))


@dataclass(frozen=True)
class SplitScripts:
    """A serial Allrun and an Allrun-parallel sharing an Allrun.pre, as tutorials do."""

    pre: str | None          # None when no step comes before the solver
    allrun: str
    parallel: str


def solver_row(steps: list[Proposed] | tuple[Proposed, ...], solver: str) -> int | None:
    """Index in *steps* of the first ticked run of *solver*: where the scripts split."""
    if not solver:
        return None
    return next(
        (i for i, s in enumerate(steps) if s.checked and s.kind != ar.OTHER and s.app == solver),
        None,
    )


def render_split(
    steps: list[Proposed] | tuple[Proposed, ...], proposal: Proposal
) -> SplitScripts | None:
    """Allrun.pre, Allrun and Allrun-parallel for the ticked *steps*; None without
    a ticked solver step, which is where they split.

    The steps before the solver are the shared Allrun.pre. The solver and what
    follows go in both: serially in Allrun, and in Allrun-parallel after
    decomposePar and as ``runParallel``. decomposePar and reconstructPar rows
    go in Allrun-parallel only -- decomposePar first, wherever it is listed; a
    reconstructPar the user put before the solver right after it.
    """
    at = solver_row(steps, proposal.solver)
    if at is None:
        return None
    ticked = [s for s in steps if s.checked]
    split = next(i for i, s in enumerate(ticked) if s is steps[at])
    before, solver, after = ticked[:split], ticked[split], ticked[split + 1:]
    all_suggested = _all_suggested(ticked)

    pre = [s for s in before if s.app not in _PARALLEL_ONLY]
    lead = "./" + SCRIPT_PRE if pre else ""
    serial = [_serial(solver)] + [_serial(s) for s in after if s.app not in _PARALLEL_ONLY]
    decompose = [s for s in ticked if s.app == "decomposePar"]
    parallel = [
        *decompose,
        replace(solver, kind=ar.PARALLEL, nprocs=solver.nprocs or proposal.decompose_n or 0),
        *(s for s in before if s.app in _RECONSTRUCT),
        *(s for s in after if s.app != "decomposePar"),
    ]
    return SplitScripts(
        pre=_render(pre, proposal, all_suggested) if pre else None,
        allrun=_render(serial, proposal, all_suggested, lead),
        parallel=_render(parallel, proposal, all_suggested, lead),
    )


def _serial(step: Proposed) -> Proposed:
    return replace(step, kind=ar.RUN, nprocs=0) if step.kind == ar.PARALLEL else step


def parallel_rows(proposal: Proposal) -> list[Proposed]:
    """decomposePar and reconstructPar rows for a proposal that has neither."""
    have = {s.app for s in proposal.steps}
    out = []
    if "decomposePar" not in have:
        out.append(Proposed(
            kind=ar.RUN, app="decomposePar", source=SOURCE_ADDED,
            origin="system/decomposeParDict", marks=(MARK_PARALLEL_ONLY,),
        ))
    if not have & _RECONSTRUCT:
        out.append(Proposed(
            kind=ar.RUN, app="reconstructPar", source=SOURCE_ADDED,
            origin="system/decomposeParDict", marks=(MARK_PARALLEL_ONLY,),
        ))
    return out


def can_split(proposal: Proposal) -> bool:
    """Whether an Allrun-parallel can be offered: a solver step, and more than one subdomain."""
    has_solver = any(s.app == proposal.solver and s.kind != ar.OTHER for s in proposal.steps)
    return bool(proposal.solver) and has_solver and (
        (proposal.decompose_n or 0) > 1 or any(s.kind == ar.PARALLEL for s in proposal.steps)
    )


def ran_in_parallel(proposal: Proposal) -> bool:
    """Whether the logs or processor directories show the case ran in parallel."""
    return any(s.kind == ar.PARALLEL for s in proposal.steps)


def render_allclean(steps: list[Proposed] | tuple[Proposed, ...], proposal: Proposal) -> str:
    """The Allclean that undoes what the Allrun makes.

    ``cleanCase`` deletes ``constant/polyMesh`` in both forks; when no ticked
    step makes the mesh, the Allrun could not bring it back, so it is kept.
    """
    body: list[str] = []
    if makes_mesh(steps):
        if proposal.has_zero_orig:
            body.append("cleanCase0" if proposal.fork == FORK_OPENCFD else "cleanCase\nrm -rf 0")
        else:
            body.append("cleanCase")
    else:
        body.append(
            "# No step of the Allrun makes the mesh, so constant/polyMesh is kept:\n"
            "# cleanCase would delete it.\n"
            "foamListTimes -rm\n"
            "rm -rf processor* postProcessing dynamicCode log.*"
        )
        if proposal.has_zero_orig:
            body.append("rm -rf 0")
    return _CLEAN_HEADER + "\n" + "\n".join(body) + "\n" + _FOOTER


def write_script(path: str, text: str) -> None:
    """Write *text* as an executable script; refuses to replace a file."""
    with open(path, "x", encoding="utf-8", newline="\n") as f:
        f.write(text)
    mode = os.stat(path).st_mode
    os.chmod(path, mode | 0o755)


# ── a command the user adds ──────────────────────────────────────────────────

# OpenFOAM applications FoDE knows by name without an installation to look in.
_KNOWN_APPS = (
    _MESH_TOOLS | _RECONSTRUCT | frozenset(_RANK)
    | frozenset({"decomposePar", "redistributePar", "postProcess", "foamPostProcess",
                 "mapFields", "changeDictionary", "applyBoundaryLayer", "potentialFoam",
                 "foamToVTK", "setExprFields", "createZeroDirectory"})
)


def _is_application(word: str, solver: str) -> bool:
    if word == solver or word in _KNOWN_APPS:
        return True
    # The sourced installation's own applications, when FoDE has one.
    for var in ("FOAM_APPBIN", "FOAM_USER_APPBIN"):
        directory = os.environ.get(var)
        if directory and os.path.isfile(os.path.join(directory, word)):
            return True
    return False


def user_row(text: str, solver: str = "") -> Proposed | None:
    """The row for a command the user typed; None for a blank line.

    An OpenFOAM application becomes ``runApplication <app> <args>`` (or
    ``runParallel`` when typed so), so it writes a log and Allrun Steps can
    follow it; anything else is written as typed.
    """
    text = text.strip()
    if not text:
        return None
    try:
        words = shlex.split(text)
    except ValueError:
        words = []
    kind = ar.RUN
    if words and words[0] in ("runApplication", "runParallel"):
        kind = ar.PARALLEL if words[0] == "runParallel" else ar.RUN
        words = words[1:]
        if not words or words[0].startswith("-"):
            words = []   # its own options: keep the line as typed
    elif words and not _is_application(words[0], solver):
        words = []
    if not words or not re.fullmatch(r"[A-Za-z][\w.-]*", words[0]):
        return Proposed(kind=ar.OTHER, text=text, source=SOURCE_USER, marks=(MARK_USER,))
    return Proposed(
        kind=kind, app=words[0], args=tuple(words[1:]), source=SOURCE_USER, marks=(MARK_USER,)
    )
