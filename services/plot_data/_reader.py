# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Read the text tables OpenFOAM function objects write, and solver-log residuals.

Self-contained on purpose: standard library only, no project imports. The
Plot Results window's "Export Python script" copies this module's source
verbatim into the script it writes, so the script reads every file by exactly
the rules the window used -- column naming, restart stitching, vector
flattening -- rather than by a re-implementation that could drift. Keep it
importable on its own (see tests/services/test_plot_data.py, which checks).

Formats handled (surveyed from OpenCFD v2512/v2606 output and Foundation 7/dev
source, see DEVELOPER.md's "Plot Results"):

- ``writeFile`` tables (``forces``, ``probes``, ``solverInfo``/``residuals``,
  ``surfaceFieldValue``, ``fieldMinMax``, ``interfaceHeight``, ...): ``#``
  comment lines, the last one before the data naming the columns, then rows
  of whitespace-separated cells. A cell is a number, a word (a solver name,
  ``N/A``, ``true``) or a parenthesised group -- a vector, or in Foundation's
  ``forces`` a group of vectors ``((px py pz) (vx vy vz))``. Groups are
  flattened, one column per number. A header can repeat mid-file (a mesh
  topology change rewrites it); comment lines are simply skipped.
- Sampled sets, ``.xy``/``.csv``/``.raw``: Foundation 10+ writes a ``#``
  header; OpenCFD and older Foundation write none and name the fields in the
  file name instead (``line_alpha.water_p_U.xy``), which is decoded against
  the column count.
- Solver logs: the first ``Initial residual`` per field per time step.

Every function degrades instead of raising on odd input: unreadable cells
become NaN, rows of a different width are counted in ``skipped_rows``, names
that cannot be inferred become ``col N``.
"""
from __future__ import annotations

import gzip
import math
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

NAN = float("nan")

# Component suffixes OpenFOAM itself uses for a 3-vector, a symmTensor and a
# tensor. Anything else is numbered.
_COMPONENTS = {
    3: ("x", "y", "z"),
    6: ("xx", "xy", "xz", "yy", "yz", "zz"),
    9: ("xx", "xy", "xz", "yx", "yy", "yz", "zx", "zy", "zz"),
}

_TOKEN_RE = re.compile(r"[()]|[^\s()]+")
_PROBE_RE = re.compile(r"^#\s*Probe\s+(\d+)\s*\(")
_TIME_RE = re.compile(r"^Time = (\S+?)s?$")
_RESIDUAL_RE = re.compile(r"Solving for ([^,]+), Initial residual = ([^,\s]+)")


@dataclass
class Table:
    """Columns of numbers; column 0 is the x axis (time or position)."""

    names: list[str]
    columns: list[list[float]]
    # Comment lines that did not name columns: CofR, probe locations, ...
    notes: list[str] = field(default_factory=list)
    skipped_rows: int = 0
    # Where the column names came from: "header" (the file's own heading,
    # expanded), "file name" (a headerless sampled set, decoded from its
    # name), "log" (a solver log's fields) or "none" (x, col 1, ...).
    naming: str = "none"

    def column(self, name: str) -> list[float]:
        return self.columns[self.names.index(name)]

    def numeric_names(self) -> list[str]:
        """Names of the plottable columns: those holding at least one number."""
        return [
            n for n, c in zip(self.names, self.columns)
            if any(not math.isnan(v) for v in c)
        ]

    def __len__(self) -> int:
        return len(self.columns[0]) if self.columns else 0


# A file changed this recently may be in the middle of being written.
_WRITING_SECONDS = 10.0


def _read_text(path: Path) -> str:
    """The file's text; without a cut-off last line while it is being written.

    A solver appends a row at a time, and a read can land mid-row: ``1.2``
    of what will be ``1.2345`` parses as a plausible, wrong number. Such a
    row has no line ending yet, so one without is dropped -- but only for a
    file changed in the last few seconds, because a finished file whose
    last row merely lacks a newline (a hand-saved CSV) is complete.
    """
    path = Path(path)
    stat = path.stat()
    raw = path.read_bytes()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    if raw and not raw.endswith(b"\n") and time.time() - stat.st_mtime < _WRITING_SECONDS:
        raw = raw[: raw.rfind(b"\n") + 1]
    return raw.decode("utf-8", errors="replace")


def _number(token: str) -> float:
    try:
        return float(token)
    except ValueError:
        return NAN


def _cells(line: str) -> list[list[float]] | None:
    """Split a data row into top-level cells, each flattened to its numbers.

    ``(`` and ``)`` nest; a top-level group becomes one cell. Returns ``None``
    for unbalanced parentheses, so a mangled row is skipped, not misread.
    """
    cells: list[list[float]] = []
    depth = 0
    for tok in _TOKEN_RE.findall(line):
        if tok == "(":
            if depth == 0:
                cells.append([])
            depth += 1
        elif tok == ")":
            depth -= 1
            if depth < 0:
                return None
        elif depth:
            cells[-1].append(_number(tok))
        else:
            cells.append([_number(tok)])
    return cells if depth == 0 else None


def _header_tokens(line: str) -> list[str]:
    """Whitespace tokens of a ``#`` line, kept whole while parentheses are open.

    ``forces(pressure viscous)`` stays one token; ``sum(phi)`` was one anyway.
    """
    out: list[str] = []
    depth = 0
    for word in line.lstrip("#").split():
        if depth and out:
            out[-1] += " " + word
        else:
            out.append(word)
        depth += word.count("(") - word.count(")")
    return out


def _expand(name: str, width: int, groups: int) -> list[str]:
    """Column names for one cell called *name* holding *width* numbers."""
    if width == 1:
        return [name]
    m = re.fullmatch(r"([^()]+)\((.+)\)", name)
    subs = m.group(2).split() if m else []
    if m and groups > 1 and len(subs) == groups and width % groups == 0:
        each = width // groups
        return [
            n for sub in subs
            for n in _expand(f"{m.group(1)}_{sub}", each, 1)
        ]
    comps = _COMPONENTS.get(width)
    if comps:
        return [f"{name}_{c}" for c in comps]
    return [f"{name}_{i}" for i in range(width)]


def _row_groups(line: str) -> list[int]:
    """Number of parenthesised sub-groups inside each top-level cell."""
    groups: list[int] = []
    depth = 0
    for tok in _TOKEN_RE.findall(line):
        if tok == "(":
            if depth == 0:
                groups.append(0)
            elif depth == 1:
                groups[-1] += 1
            depth += 1
        elif tok == ")":
            depth -= 1
        elif depth == 0:
            groups.append(0)
    return groups


def _split_field_names(stem: str, n_values: int) -> tuple[int, list[str]] | None:
    """Decode ``<set>_<field>_<field>...`` against *n_values* value columns.

    Field names can hold ``_`` (``p_rgh``) and ``.`` (``alpha.water``), so
    every way of rejoining the ``_``-parts is tried. OpenCFD writes scalars
    before vectors, so a split is accepted when its first fields can be
    scalars and the rest vectors. Returns the best split with its penalty:
    the number of well-known scalars (``p``, ``k``, ``alpha.*``...) it would
    take for vectors. Ties go to the shortest set name, then a split that
    rejoins a known underscored name, then the fewest rejoins.
    """
    parts = stem.split("_")
    best: tuple[tuple[int, int, int, int], list[str]] | None = None
    for i in range(1, len(parts)):
        rest = parts[i:]
        for fields in _partitions(rest):
            n = len(fields)
            extra = n_values - n
            if extra < 0 or extra % 2:
                continue
            n_vec = extra // 2
            if n_vec > n:
                continue
            names: list[str] = []
            for k, f in enumerate(fields):
                names += [f] if k < n - n_vec else _expand(f, 3, 1)
            penalty = sum(1 for f in fields[n - n_vec:] if _is_known_scalar(f))
            known = sum(1 for f in fields if f in _KNOWN_UNDERSCORED)
            score = (penalty, i, -known, len(rest) - n)
            if best is None or score < best[0]:
                best = (score, names)
    return None if best is None else (best[0][0], best[1])


_KNOWN_SCALARS = {
    "p", "p_rgh", "k", "epsilon", "omega", "nut", "nuTilda", "T", "rho",
    "alphat", "mut", "h", "e", "Co", "Q", "yPlus", "magU", "kMean", "pMean",
}


def _is_known_scalar(name: str) -> bool:
    return name in _KNOWN_SCALARS or name.startswith("alpha.")


_KNOWN_UNDERSCORED = {"p_rgh", "U_0", "T_0", "nu_t", "k_l"}


def _partitions(parts: list[str]):
    """Every way to join adjacent *parts* back together with ``_``."""
    if len(parts) > 12:  # 2**11 splits; a stem this long is not a field list
        yield parts
        return
    n = len(parts)
    for mask in range(1 << (n - 1)):
        out = [parts[0]]
        for k in range(1, n):
            if mask >> (k - 1) & 1:
                out[-1] += "_" + parts[k]
            else:
                out.append(parts[k])
        yield out


def read_table(path: str | Path) -> Table:
    """Read one function-object output file into a :class:`Table`."""
    path = Path(path)
    text = _read_text(path)
    comments: list[str] = []
    header_line: str | None = None
    probe_ids: list[str] = []
    layout: list[int] | None = None
    groups: list[int] = []
    rows: list[list[float]] = []
    skipped = 0
    csv_header: list[str] | None = None
    # Word-valued cells of the first row (a patch or field name), and their
    # value in every row -- the key :func:`_pivot` splits interleaved rows by.
    word_cells: list[int] = []
    words: list[tuple[str, ...]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            # Only the comment block before the first row names columns; a
            # header repeated mid-file is skipped like any other comment.
            if layout is None:
                m = _PROBE_RE.match(line)
                if m:
                    probe_ids.append(m.group(1))
                comments.append(line)
            continue
        if "," in line and "(" not in line:
            tokens = [t.strip() for t in line.split(",")]
            if layout is None and csv_header is None and all(
                math.isnan(_number(t)) for t in tokens
            ):
                csv_header = tokens
                continue
            cells: list[list[float]] | None = [[_number(t)] for t in tokens]
            tops: list[str | None] = list(tokens)
            is_csv = True
        else:
            is_csv = False
            cells = _cells(line)
            tops = _top_tokens(line)
        if not cells:
            skipped += 1
            continue
        shape = [len(c) for c in cells]
        if layout is None:
            layout = shape
            groups = [0] * len(cells) if is_csv else _row_groups(line)
            header_line = comments[-1] if comments else None
            word_cells = [
                i for i, (c, t) in enumerate(zip(cells, tops))
                if len(c) == 1 and math.isnan(c[0]) and t and _WORD_RE.match(t)
                and t.lower() not in _NOT_KEYS
            ]
        elif shape != layout:
            skipped += 1
            continue
        rows.append([v for c in cells for v in c])
        if word_cells:
            words.append(tuple(str(tops[i]) for i in word_cells))

    notes = [c for c in comments if c is not header_line]
    if layout is None:
        return Table(names=[], columns=[], notes=comments, skipped_rows=skipped)
    width = sum(layout)
    header = _header_tokens(header_line) if header_line else csv_header
    named = _names(path, layout, groups, header, probe_ids)
    if named is None or len(named[0]) != width:
        names, naming = ["x"] + [f"col {i}" for i in range(1, width)], "none"
        if header_line:
            notes.append(header_line)
    else:
        names, naming = named
    columns = [list(c) for c in zip(*rows)] if rows else [[] for _ in range(width)]
    table = Table(names=_unique(names), columns=columns, notes=notes, skipped_rows=skipped,
                  naming=naming)
    x = table.columns[0] if table.columns else []
    if word_cells and len(set(words)) > 1 and len(set(x)) < len(x):
        offsets = [sum(layout[:i]) for i in word_cells]
        table = _pivot(table, words, offsets)
    return table


# Words that vary row to row without naming anything: solverInfo's
# "converged" column. Never a pivot key.
_NOT_KEYS = {"true", "false", "yes", "no", "on", "off", "n/a"}
_WORD_RE = re.compile(r"^[A-Za-z_][\w.:-]*$")


def _top_tokens(line: str) -> list[str | None]:
    """Top-level tokens of a row, aligned with :func:`_cells`; groups are None."""
    out: list[str | None] = []
    depth = 0
    for tok in _TOKEN_RE.findall(line):
        if tok == "(":
            if depth == 0:
                out.append(None)
            depth += 1
        elif tok == ")":
            depth -= 1
        elif depth == 0:
            out.append(tok)
    return out


def _pivot(table: Table, keys: list[tuple[str, ...]], word_cols: list[int]) -> Table:
    """Split rows interleaved by a word cell into one column set per word.

    ``wallShearStress`` writes one row per patch and ``fieldMinMax`` one per
    field, all at the same time. Plotted as they stand the patches would be
    drawn as one zig-zag line, so each numeric column becomes
    ``<column> [<key>]`` for every distinct key, aligned on the x values.
    Columns that are words in every row are dropped; they are the key.
    """
    order: list[tuple[str, ...]] = []
    for k in keys:
        if k not in order:
            order.append(k)
    xs: list[float] = []
    x_index: dict[float, int] = {}
    for x in table.columns[0]:
        if x not in x_index:
            x_index[x] = len(xs)
            xs.append(x)
    value_cols = [
        j for j in range(1, len(table.names))
        if j not in word_cols and any(not math.isnan(v) for v in table.columns[j])
    ]
    names = [table.names[0]]
    columns: list[list[float]] = [xs]
    for key in order:
        label = " ".join(key)
        for j in value_cols:
            names.append(f"{table.names[j]} [{label}]")
            col = [NAN] * len(xs)
            for x, k, v in zip(table.columns[0], keys, table.columns[j]):
                if k == key:
                    col[x_index[x]] = v
            columns.append(col)
    return Table(names=names, columns=columns, notes=table.notes,
                 skipped_rows=table.skipped_rows, naming=table.naming)


def _names(
    path: Path,
    layout: list[int],
    groups: list[int],
    header: list[str] | None,
    probe_ids: list[str],
) -> tuple[list[str], str] | None:
    """The column names and where they came from ("header" or "file name")."""
    width = sum(layout)
    if header:
        if probe_ids and len(header) == len(layout) and all(
            h.isdigit() for h in header[1:]
        ):
            header = header[:1] + [f"probe{h}" for h in header[1:]]
        if len(header) == len(layout):
            out: list[str] = []
            for name, w, g in zip(header, layout, groups):
                out += _expand(name, w, g)
            return out, "header"
        if len(header) == width:
            return header, "header"
        if 1 < len(header) < len(layout) and all(w == 1 for w in layout):
            # One name over several columns -- OpenCFD's per-bin blade
            # files: "# Time  Cd(per bin)" over ten values. Number the rest.
            head = header[:-1]
            rest = width - len(head)
            return head + [f"{header[-1]} [{i}]" for i in range(rest)], "header"
    if path.suffix in (".xy", ".raw", ".csv", ".dat") and all(w == 1 for w in layout):
        found = []
        # One leading column is the set's `axis` coordinate -- x, y, z or the
        # distance along it, whichever the sampling dictionary chose, which
        # the file does not say -- so it is named for what all four are.
        for order, axis in enumerate((["position"], ["x", "y", "z"])):
            split = _split_field_names(path.stem, width - len(axis))
            if split is not None:
                found.append((split[0], order, axis + split[1]))
        if found:
            return min(found)[2], "file name"
    return None


def _unique(names: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    out = []
    for n in names:
        if n in seen:
            seen[n] += 1
            out.append(f"{n} ({seen[n]})")
        else:
            seen[n] = 1
            out.append(n)
    return out


def stitch(tables: list[Table]) -> Table:
    """Join the segments of a restarted run into one table.

    Segments are given in start-time order. Each later segment wins where
    they overlap: rows of the earlier ones at or after its first time are
    dropped, which is what a restart from an earlier write time means.
    Columns are matched by name; a column a segment lacks is NaN there.
    """
    tables = [t for t in tables if t.names]
    if not tables:
        return Table(names=[], columns=[])
    names = list(tables[0].names)
    for t in tables[1:]:
        names += [n for n in t.names if n not in names]
    columns: list[list[float]] = [[] for _ in names]
    notes: list[str] = []
    skipped = 0
    for k, t in enumerate(tables):
        n_rows = len(t)
        if k + 1 < len(tables) and len(tables[k + 1]):
            start = tables[k + 1].columns[0][0]
            x = t.columns[0]
            n_rows = next((i for i, v in enumerate(x) if v >= start), len(x))
        for j, name in enumerate(names):
            if name in t.names:
                columns[j] += t.columns[t.names.index(name)][:n_rows]
            else:
                columns[j] += [NAN] * n_rows
        notes += [n for n in t.notes if n not in notes]
        skipped += t.skipped_rows
    # The x column's name comes from the first segment; later segments name
    # it the same in every format surveyed, so no special case is needed.
    return Table(names=names, columns=columns, notes=notes, skipped_rows=skipped,
                 naming=tables[0].naming)


def read_log_residuals(path: str | Path) -> Table:
    """Initial residuals per time step from a solver log (``log.<solver>``).

    The first ``Initial residual`` of each field in a step is kept: PIMPLE's
    outer correctors and PISO's pressure correctors repeat the line, and the
    first one is the residual of the step, which is what convergence plots
    show. ``Time =`` (``Time = 0.1s`` in Foundation) opens a step.
    """
    times: list[float] = []
    fields: list[str] = []
    values: dict[str, list[float]] = {}
    seen: set[str] = set()
    for raw in _read_text(Path(path)).splitlines():
        m = _TIME_RE.match(raw.strip())
        if m:
            t = _number(m.group(1))
            if math.isnan(t):
                continue
            times.append(t)
            seen = set()
            for v in values.values():
                v.append(NAN)
            continue
        m = _RESIDUAL_RE.search(raw)
        if m and times:
            name = m.group(1).strip()
            if name in seen:
                continue
            seen.add(name)
            if name not in values:
                fields.append(name)
                values[name] = [NAN] * len(times)
            values[name][-1] = _number(m.group(2))
    return Table(
        names=["Time"] + fields,
        columns=[times] + [values[f] for f in fields],
        naming="log",
    )
