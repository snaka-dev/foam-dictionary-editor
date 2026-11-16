# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Plain-language advice for the errors in an OpenFOAM log.

``advise(log_text, case_dir)`` finds the FATAL ERRORs (and a floating-point
exception's stack trace) in a log and matches each against a table of the
errors beginners meet most. It returns :class:`Advice` *codes* with the
values they mention, never sentences -- ``ui/log_advice_text.py`` words them,
where the i18n scans can see it -- plus the file and line to open when
OpenFOAM names one.

Every pattern was taken from a log the installed OpenFOAM (v2606) actually
wrote for a deliberately broken tutorial copy, and checked against the
Foundation-12 source for that fork's wording, which differs in places
("keyword X is undefined in dictionary" vs "Entry 'X' not found in
dictionary"; "file: … from line A to line B" vs "file: … at line A to B";
"Unknown discretisation scheme" vs "type"). See DEVELOPER.md's "Log advice".
An error no pattern matches gets no advice -- its text is in the summary
anyway -- so a wrong guess is never offered in place of the real message.
"""
from __future__ import annotations

import difflib
import os
import re
from dataclasses import dataclass, field

# ── codes ───────────────────────────────────────────────────────────────────
MISSING_PATCH_ENTRY = "missing_patch_entry"
UNKNOWN_NAME = "unknown_name"
CONSTRAINT_MISMATCH = "constraint_mismatch"
MISSING_ENTRY = "missing_entry"
NO_REFERENCE_CELL = "no_reference_cell"
MISSING_FILE = "missing_file"
NO_MESH = "no_mesh"
DECOMPOSITION_DIVISIONS = "decomposition_divisions"
PROCESSOR_COUNT = "processor_count"
SYNTAX_ERROR = "syntax_error"
MAX_ITERATIONS = "max_iterations"
FLOATING_POINT = "floating_point"

ADVICE_CODES = frozenset({
    MISSING_PATCH_ENTRY, UNKNOWN_NAME, CONSTRAINT_MISMATCH, MISSING_ENTRY,
    NO_REFERENCE_CELL, MISSING_FILE, NO_MESH, DECOMPOSITION_DIVISIONS,
    PROCESSOR_COUNT, SYNTAX_ERROR, MAX_ITERATIONS, FLOATING_POINT,
})


@dataclass(frozen=True)
class Advice:
    code: str
    # Values the sentence mentions (patch, key, suggestion, …), all strings.
    args: dict[str, str] = field(default_factory=dict, hash=False)
    # Absolute path of the file to open, '' when there is none to open.
    path: str = ""
    # 1-based line in ``path``; 0 when unknown.
    line: int = 0
    # The error's own first line, to show what the advice is about.
    excerpt: str = ""


# ── finding the errors ───────────────────────────────────────────────────────

_RANK_PREFIX_RE = re.compile(r"^\[\d+\] ?", re.M)
_FATAL_RE = re.compile(r"^-->\s*FOAM FATAL (?:IO )?ERROR", re.M)
_BLOCK_END_RE = re.compile(r"^(?:FOAM (?:exiting|aborting)|FOAM parallel run (?:exiting|aborting))", re.M)
# OpenCFD: "file: 0/U/boundaryField at line 25 to 36." / "at line 31."
# Foundation: "file: /abs/0/U/boundaryField from line 25 to line 36."
_FILE_RE = re.compile(
    r"^file:\s*(?P<path>.+?)(?:\s+(?:at|from) line (?P<start>\d+)(?:\s+to(?: line)?\s+\d+)?)?\.?\s*$",
    re.M,
)
_SIGFPE_RE = re.compile(r"Foam::sigFpe::sigHandler")
_COURANT_RE = re.compile(r"^Courant Number mean:\s*\S+\s+max:\s*(\S+)", re.M)
_TIME_RE = re.compile(r"^Time = (\S+?)s?\s*$", re.M)
# A list of valid names after an "Unknown … type X": either "N\n(\nname\n…)"
# or inline "N(name name …)".
_VALID_LIST_RE = re.compile(
    r"Valid [^\n]*?(?:types|schemes)[^\n]*?:?\s*\n?\s*\d*\s*\((?P<names>[^()]*)\)", re.S
)


@dataclass
class _Block:
    message: str  # the lines between the FATAL header and "file:"/"From", joined
    text: str     # the whole block
    file_path: str = ""
    line: int = 0


def _blocks(text: str) -> list[_Block]:
    found = []
    for m in _FATAL_RE.finditer(text):
        end = _BLOCK_END_RE.search(text, m.end())
        nxt = _FATAL_RE.search(text, m.end())
        stop = min(e for e in (
            end.start() if end else len(text), nxt.start() if nxt else len(text),
        ))
        body = text[m.end():stop]
        lines = body.splitlines()[1:]  # the rest of the header line is "(openfoam-2606)"
        message: list[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("file:", "From ", "Valid ")) or re.match(r"^\d+\s*\(?$", stripped):
                break
            if stripped:
                message.append(stripped)
        block = _Block(" ".join(message), body)
        fm = _FILE_RE.search(body)
        if fm:
            block.file_path = fm.group("path").strip()
            block.line = int(fm.group("start")) if fm.group("start") else 0
        found.append(block)
    return found


def _resolve(path: str, case_dir: str) -> str:
    """The file a ``file:`` reference names, without its dictionary scope.

    OpenFOAM appends the dictionary path to the file name
    (``0/U/boundaryField/inlet``), so components are dropped from the end
    until an existing file remains. '' when none does.
    """
    path = path.strip().strip('"')
    if not path:
        return ""
    candidate = path if os.path.isabs(path) else os.path.join(case_dir, path)
    candidate = os.path.normpath(candidate)
    while candidate and candidate != os.path.dirname(candidate):
        if os.path.isfile(candidate):
            return candidate
        candidate = os.path.dirname(candidate)
    return ""


def _valid_names(text: str) -> list[str]:
    m = _VALID_LIST_RE.search(text)
    if not m:
        return []
    return re.findall(r"[A-Za-z_][\w:.<>,-]*", m.group("names"))


def _suggest(name: str, valid: list[str]) -> str:
    """The valid name closest to a misspelt one, or ''."""
    if not valid or name in valid:
        return ""
    lowered = {v.lower(): v for v in valid}
    if name.lower() in lowered:
        return lowered[name.lower()]
    close = difflib.get_close_matches(name, valid, n=1, cutoff=0.75)
    return close[0] if close else ""


def _key_line(path: str, key: str) -> int:
    """The line of the first entry spelled *key* in *path*, or 0."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for number, line in enumerate(f, 1):
                if re.match(rf"\s*{re.escape(key)}(?:\s|$)", line):
                    return number
    except OSError:
        pass
    return 0


# ── the table ────────────────────────────────────────────────────────────────

_MISSING_PATCH_RE = re.compile(r"Cannot find patchField entry for (?:cyclic )?(?P<patch>\S+)")
_UNKNOWN_RE = re.compile(r"Unknown (?P<what>[A-Za-z][\w ]*?) (?:type|scheme) (?P<name>\S+)")
_INCONSISTENT_RE = re.compile(
    r"inconsistent patch and patchField types for\s+"
    r"patch type (?P<patch_type>\S+) and patchField type (?P<field_type>\S+)"
)
_NOT_CONSTRAINT_RE = re.compile(
    r"patch type '(?P<patch_type>[^']+)' not constraint type '(?P<field_type>[^']+)'"
    r"(?:\s+for patch (?P<patch>\S+) of field (?P<field>\S+))?"
)
# OpenCFD / Foundation.
_MISSING_ENTRY_RES = (
    re.compile(r"Entry '(?P<key>[^']+)' not found in dictionary \"(?P<dict>[^\"]+)\""),
    re.compile(r"keyword (?P<key>\S+) is undefined in dictionary \"?(?P<dict>[^\"\s]+)\"?"),
)
_REFERENCE_RE = re.compile(r"Unable to set reference cell for field (?P<field>\S+)")
_NO_MESH_RE = re.compile(r"Cannot find file \"points\" in directory \"polyMesh\"")
_MISSING_FILE_RE = re.compile(r"cannot find file \"(?P<path>[^\"]+)\"")
_DIVISIONS_RE = re.compile(
    r"Wrong number of (?:domain|processor) divisions.*?Number of domains\s*:\s*(?P<count>\d+)"
    r".*?Wanted decomposition\s*:\s*\((?P<n>[^)]*)\)",
    re.S,
)
_PROCESSORS_RES = (
    re.compile(
        r"specifies (?P<want>\d+) processors but job was started with (?P<got>\d+) (?:ranks|processors)"
    ),
    re.compile(
        r"number of processor directories = (?P<want>\d+) "
        r"is not equal to the number of processors = (?P<got>\d+)"
    ),
)
_SYNTAX_RE = re.compile(
    r"Unexpected EOF|Found \S+ but expected|ill defined primitiveEntry|Unexpected close|"
    r"Unexpected end|Premature end|attempt to read beyond EOF|Expected a .* while reading"
)
_MAX_ITER_RE = re.compile(r"Maximum number of iterations exceeded")


def _advise_block(block: _Block, case_dir: str) -> Advice | None:
    msg = block.message
    path = _resolve(block.file_path, case_dir) if block.file_path else ""
    excerpt = msg[:200]

    def advice(code: str, args: dict[str, str], p: str = path, line: int = block.line) -> Advice:
        return Advice(code, args, p, line if p else 0, excerpt)

    m = _MISSING_PATCH_RE.search(msg)
    if m:
        return advice(MISSING_PATCH_ENTRY, {"patch": m.group("patch"), "field": _field_of(path)})
    m = _INCONSISTENT_RE.search(msg)
    if m:
        return advice(CONSTRAINT_MISMATCH, {
            "patch_type": m.group("patch_type"), "field_type": m.group("field_type"),
            "field": _field_of(path),
        })
    m = _NOT_CONSTRAINT_RE.search(msg)
    if m:
        return advice(CONSTRAINT_MISMATCH, {
            "patch_type": m.group("patch_type"), "field_type": m.group("field_type"),
            "field": m.group("field") or _field_of(path),
        })
    m = _UNKNOWN_RE.search(msg)
    if m:
        name = m.group("name")
        return advice(UNKNOWN_NAME, {
            "what": m.group("what"), "name": name,
            "suggestion": _suggest(name, _valid_names(block.text)),
        })
    for pattern in _MISSING_ENTRY_RES:
        m = pattern.search(msg)
        if m:
            key = m.group("key")
            target = path or _resolve(m.group("dict"), case_dir)
            # Present in the file yet not found: the entry before it has
            # swallowed it -- a missing ';' -- or a brace is out of place.
            present = bool(target) and _key_line(target, key) > 0
            line = _key_line(target, key) if present else block.line
            return advice(MISSING_ENTRY, {
                "key": key, "dict": _short_dict(m.group("dict"), case_dir),
                "present": "yes" if present else "",
            }, target, line)
    m = _REFERENCE_RE.search(msg)
    if m:
        return advice(NO_REFERENCE_CELL, {"field": m.group("field")})
    if _NO_MESH_RE.search(msg):
        return advice(NO_MESH, {})
    m = _MISSING_FILE_RE.search(msg)
    if m:
        missing = m.group("path")
        rel = os.path.relpath(missing, case_dir) if os.path.isabs(missing) else missing
        first = rel.split(os.sep, 1)[0]
        orig = ""
        if _is_time(first) and os.path.isdir(os.path.join(case_dir, first + ".orig")):
            orig = first + ".orig"
        return advice(MISSING_FILE, {"path": rel, "orig": orig}, "", 0)
    m = _DIVISIONS_RE.search(block.text)
    if m:
        n = m.group("n").split()
        product = 1
        for v in n:
            product *= int(v) if v.isdigit() else 1
        return advice(DECOMPOSITION_DIVISIONS, {
            "count": m.group("count"), "n": " ".join(n), "product": str(product),
        })
    for pattern in _PROCESSORS_RES:
        m = pattern.search(msg)
        if m:
            return advice(PROCESSOR_COUNT, {"want": m.group("want"), "got": m.group("got")})
    if _SYNTAX_RE.search(msg):
        return advice(SYNTAX_ERROR, {"message": excerpt})
    if _MAX_ITER_RE.search(msg):
        return advice(MAX_ITERATIONS, {})
    return None


def _field_of(path: str) -> str:
    return os.path.basename(path) if path else ""


def _short_dict(name: str, case_dir: str) -> str:
    if os.path.isabs(name):
        try:
            return os.path.relpath(name, case_dir)
        except ValueError:
            return name
    return name


def _is_time(name: str) -> bool:
    try:
        float(name)
    except ValueError:
        return False
    return True


def _floating_point(text: str, case_dir: str) -> Advice:
    """Advice for a crash by floating-point exception (a diverged solution)."""
    head = text[:_SIGFPE_RE.search(text).start()]  # type: ignore[union-attr]
    courants = _COURANT_RE.findall(head)
    times = _TIME_RE.findall(head)
    courant = courants[-1] if courants else ""
    try:
        high = float(courant) > 1.0
    except ValueError:
        high = False
    control = os.path.join(case_dir, "system", "controlDict")
    line = _key_line(control, "deltaT") if high else 0
    return Advice(
        FLOATING_POINT,
        {"courant": courant if high else "", "time": times[-1] if times else ""},
        control if line else "",
        line,
        "Foam::sigFpe::sigHandler",
    )


def advise(log_text: str, case_dir: str) -> list[Advice]:
    """Advice for each recognised error in *log_text*, in the order they occur.

    *case_dir* is where the log's relative ``file:`` references point (the
    case the log was written in); a referenced file that does not exist
    there is simply not offered for opening.
    """
    text = _RANK_PREFIX_RE.sub("", log_text)
    result: list[Advice] = []
    seen: set[tuple[str, str]] = set()
    for block in _blocks(text):
        found = _advise_block(block, case_dir)
        if found is None:
            continue
        # A parallel run repeats the same error once per rank.
        key = (found.code, repr(sorted(found.args.items())))
        if key not in seen:
            seen.add(key)
            result.append(found)
    if _SIGFPE_RE.search(text):
        result.append(_floating_point(text, case_dir))
    return result
