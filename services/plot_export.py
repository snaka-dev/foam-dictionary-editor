# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""A Plot Results data set as a table with headings: CSV, a note, the clipboard.

OpenFOAM writes some of its output without headings -- OpenCFD's sampled
sets name their fields only in the file name -- and others with vectors as
``(x y z)`` cells no spreadsheet splits. The reader has already solved both
(and stitched restarts, and pivoted per-patch rows), so an export is that
table written out: one heading row, one column per number. The original
files are never touched.

* :func:`table_csv` -- plain CSV, one heading row and no ``#`` lines, because
  a comment line is a junk first row in a spreadsheet. A gap (a field not
  solved in a step, a column a restart segment lacks) is an empty cell.
  Numbers are written back exactly: Python's ``repr`` of a float is the
  shortest text that reads back as the same value, and an integral value
  loses its ``.0`` (``281``, not ``281.0``).
* :func:`table_tsv` -- the same, tab-separated, for the clipboard: a
  spreadsheet pastes tabs into cells, while it does not parse CSV quoting
  on a paste.
* :func:`source_note` -- the ``<name>.source.txt`` beside the CSV: which
  files, in what order, which sample time, and how the headings were
  obtained -- above all when they were deduced from a file name, which is
  worth being able to check. Its first line is :data:`NOTE_MARKER`, which is
  how a later export recognises a note it wrote itself (see
  :func:`is_our_note`).

Qt-free; ``ui/dialogs/plot_results_dialog.py`` holds the words and the
questions, and ``services/plot_output.py`` the rule for where it may write.
"""
from __future__ import annotations

import csv
import io
import math
import os
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from services.plot_data import Source, Table

NOTE_MARKER = "# Exported by FoDE's Plot Results"

_NAMING = {
    "header": "from the file's own heading line (vectors split into _x/_y/_z, "
              "probes numbered probe0, probe1, ...)",
    "file name": "DEDUCED FROM THE FILE NAME: the file has no heading line, so the "
                 "field names were read from its name (<set>_<field>_<field>...) and "
                 "matched to the column count. Check them against the sampling "
                 "dictionary before relying on them. The first column is the "
                 "set's axis coordinate (x, y, z or distance, as its `axis` says).",
    "log": "from the solver log: the initial residual of each field, first "
           "occurrence per time step",
    "none": "the file names no columns, so they are numbered (x, col 1, col 2, ...)",
}


def _cell(value: float) -> str:
    if math.isnan(value):
        return ""
    if value.is_integer() and abs(value) < 1e15:
        return str(int(value))
    return repr(value)


def _rows(table: Table) -> list[list[str]]:
    rows = [list(table.names)]
    for i in range(len(table)):
        rows.append([_cell(col[i]) for col in table.columns])
    return rows


def table_csv(table: Table) -> str:
    out = io.StringIO()
    csv.writer(out, lineterminator="\n").writerows(_rows(table))
    return out.getvalue()


def table_tsv(table: Table) -> str:
    # Plain joins: a heading never holds a tab, and a number never does.
    return "".join("\t".join(row) + "\n" for row in _rows(table))


def default_stem(source: Source, time: str | None) -> str:
    """A file name for *source*: its data set, without extension, plus the time.

    ``postProcessing/lineSample/x0.1_k_p_U.xy`` at 281 gives
    ``lineSample_x0.1_k_p_U_281``.
    """
    stem = os.path.splitext(source.title)[0]
    if source.kind == "profile":
        stem += "_" + (time if time in source.times else source.times[-1])
    return re.sub(r"[^\w.-]+", "_", stem).strip("_.") or "data"


def note_path(csv_path: str) -> str:
    """``a.csv`` → ``a.source.txt``."""
    return os.path.splitext(csv_path)[0] + ".source.txt"


def free_csv_path(directory: str, stem: str) -> str:
    """``<stem>.csv`` in *directory*, numbered ``_2``, ``_3``… until neither it
    nor its note exists -- so the name offered never meets a clash."""
    candidate = os.path.join(directory, stem + ".csv")
    n = 2
    while os.path.lexists(candidate) or os.path.lexists(note_path(candidate)):
        candidate = os.path.join(directory, f"{stem}_{n}.csv")
        n += 1
    return candidate


def is_our_note(path: str) -> bool:
    """True when *path* is a note an earlier export wrote."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.readline().rstrip("\n") == NOTE_MARKER
    except OSError:
        return False


def source_note(
    table: Table,
    source: Source,
    files: Sequence[str],
    time: str | None,
    csv_name: str,
    version: str = "",
    now: datetime | None = None,
) -> str:
    """The text of ``<name>.source.txt`` for *table*, exported as *csv_name*."""
    when = (now or datetime.now()).isoformat(timespec="seconds")
    lines = [
        NOTE_MARKER,
        "",
        f"Table:     {csv_name}",
        f"Exported:  {when}" + (f" by FoDE {version}" if version else ""),
        f"Case:      {source.case_dir}",
        f"Data set:  {source.title}",
    ]
    if source.kind == "profile":
        lines.append(f"Time:      {time if time in source.times else source.times[-1]}"
                     + ("" if time in source.times else " (the latest)"))
    lines += ["", "Read from" + (", joined in this order (a later segment replaces "
                                 "the overlap; restarted run):" if len(files) > 1 else ":")]
    lines += [f"  {os.path.relpath(f, source.case_dir)}" for f in files]
    lines += [
        "",
        f"Rows:      {len(table)}",
        f"Columns:   {', '.join(table.names)}",
        f"Headings:  {_NAMING.get(table.naming, _NAMING['none'])}",
    ]
    if table.skipped_rows:
        lines.append(f"Skipped:   {table.skipped_rows} line(s) of another shape "
                     "(a repeated heading, a partly written last line, ...)")
    if any(math.isnan(v) for col in table.columns for v in col):
        lines.append("Gaps:      empty cells are values the files do not have "
                     "(a field not solved in a step, a column a segment lacks)")
    lines.append("Units:     none recorded; OpenFOAM's output files do not carry them")
    if table.notes:
        lines += ["", "Comment lines in the source:"]
        lines += [f"  {n}" for n in table.notes]
    return "\n".join(lines) + "\n"


# ── what is plotted ──────────────────────────────────────────────────────────


@dataclass
class PlottedLine:
    """One plotted line, with the table it was read from."""

    label: str
    source: Source
    table: Table
    column: str
    time: str | None
    files: Sequence[str]
    # Plotted along x; empty means the table's first column.
    x_column: str = ""

    @property
    def x_name(self) -> str:
        return self.x_column or self.table.names[0]

    def same_data_set(self, other: PlottedLine) -> bool:
        """Same table and the same x column: the lines share their x values."""
        return (os.path.normpath(self.source.case_dir), self.source.key, self.time,
                self.x_name) == (os.path.normpath(other.source.case_dir),
                                 other.source.key, other.time, other.x_name)


def plotted_table(lines: Sequence[PlottedLine]) -> tuple[Table, bool]:
    """The plotted lines as one table, and whether they share their x column.

    Lines of one data set share its x column: ``x, col, col…``. Lines of
    different ones (two cases' time steps, a probe beside a sampled line)
    have no x values in common, and putting them in one column would mean
    interpolating -- changing the data -- so each line keeps its own x and y
    as a pair of columns, side by side, the shorter padded with empty cells.
    Headings are then ``<legend label>: <column>``.
    """
    if not lines:
        return Table(names=[], columns=[]), True
    first = lines[0]
    if all(line.same_data_set(first) for line in lines[1:]):
        names = [first.x_name]
        columns = [list(first.table.column(first.x_name))]
        for line in lines:
            if line.column not in names:
                names.append(line.column)
                columns.append(list(line.table.column(line.column)))
        return Table(names=names, columns=columns), True
    height = max(len(line.table) for line in lines)
    names, columns = [], []
    for line in lines:
        for name in (line.x_name, line.column):
            values = list(line.table.column(name))
            names.append(f"{line.label}: {name}")
            columns.append(values + [math.nan] * (height - len(values)))
    return Table(names=names, columns=columns), False


def plotted_note(
    lines: Sequence[PlottedLine],
    shared: bool,
    csv_name: str,
    version: str = "",
    now: datetime | None = None,
) -> str:
    """The ``.source.txt`` for :func:`plotted_table`'s CSV: every line's origin."""
    when = (now or datetime.now()).isoformat(timespec="seconds")
    lines_out = [
        NOTE_MARKER,
        "",
        f"Table:     {csv_name}",
        f"Exported:  {when}" + (f" by FoDE {version}" if version else ""),
        "Contents:  the lines of a plot, "
        + ("sharing their data set's x column." if shared else
           "each as its own pair of columns (x, y): they do not share x values, "
           "and none were interpolated. Shorter pairs end in empty cells."),
        "Units:     none recorded; OpenFOAM's output files do not carry them",
    ]
    for n, line in enumerate(lines, 1):
        src = line.source
        lines_out += [
            "",
            f"Line {n}:    {line.label}",
            f"  Case:      {src.case_dir}",
            f"  Data set:  {src.title}",
            f"  Column:    {line.column}",
            f"  Along x:   {line.x_name}",
        ]
        if src.kind == "profile":
            lines_out.append(f"  Time:      {line.time if line.time in src.times else src.times[-1]}")
        lines_out.append("  Read from:" + (" (joined in this order)" if len(line.files) > 1 else ""))
        lines_out += [f"    {os.path.relpath(f, src.case_dir)}" for f in line.files]
        lines_out.append(
            f"  Headings:  {_NAMING.get(line.table.naming, _NAMING['none'])}"
        )
    return "\n".join(lines_out) + "\n"
