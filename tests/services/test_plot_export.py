# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""A Plot Results data set as a CSV with headings, its .source.txt, the clipboard."""
from __future__ import annotations

import csv
import io
import math
from datetime import datetime
from pathlib import Path

from services.plot_data import Table, find_sources, load_source
from services.plot_export import (
    NOTE_MARKER,
    default_stem,
    free_csv_path,
    is_our_note,
    note_path,
    source_note,
    table_csv,
    table_tsv,
)

NAN = math.nan


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_csv_has_one_heading_row_exact_numbers_and_empty_gaps():
    table = Table(names=["Time", "p", "U_x"],
                  columns=[[1.0, 2.0], [0.1, NAN], [1e-05, -3.25]])
    rows = list(csv.reader(io.StringIO(table_csv(table))))
    assert rows == [["Time", "p", "U_x"], ["1", "0.1", "1e-05"], ["2", "", "-3.25"]]
    # Every value reads back as the same float.
    assert float(rows[1][1]) == 0.1
    assert table_tsv(table).splitlines()[0] == "Time\tp\tU_x"


def test_a_heading_with_a_comma_is_quoted():
    table = Table(names=["x", "a,b"], columns=[[0.0], [1.0]])
    assert table_csv(table).splitlines()[0] == 'x,"a,b"'


def test_names_offered_are_free(tmp_path):
    assert free_csv_path(str(tmp_path), "line_281") == str(tmp_path / "line_281.csv")
    (tmp_path / "line_281.csv").write_text("")
    assert free_csv_path(str(tmp_path), "line_281").endswith("line_281_2.csv")
    # A note left alone counts too: its CSV's name is not offered.
    (tmp_path / "line_281_2.source.txt").write_text("")
    assert free_csv_path(str(tmp_path), "line_281").endswith("line_281_3.csv")
    assert note_path("/a/b.csv") == "/a/b.source.txt"


def test_a_headerless_set_exports_with_headings_and_says_where_they_came_from(tmp_path):
    case = tmp_path / "case"
    for t in ("100", "281"):
        _write(case / "postProcessing/lineSample" / t / "x0.1_k_p_U.xy",
               f"-0.02 0.8 -3.8 {t} 0 0\n0.02 0.9 -3.9 9.5 0.1 0\n")
    src = find_sources(str(case))[0]
    table = load_source(src, "100")
    assert table.names == ["position", "k", "p", "U_x", "U_y", "U_z"]
    assert table_csv(table).splitlines()[0] == "position,k,p,U_x,U_y,U_z"
    assert default_stem(src, "100") == "lineSample_x0.1_k_p_U_100"
    note = source_note(table, src, [src.paths[0]], "100", "out.csv",
                       version="1.2.3", now=datetime(2026, 11, 25, 9, 0))
    assert note.startswith(NOTE_MARKER + "\n")
    assert "Time:      100\n" in note
    assert "postProcessing/lineSample/100/x0.1_k_p_U.xy" in note
    assert "DEDUCED FROM THE FILE NAME" in note
    assert "by FoDE 1.2.3" in note


def test_a_restarted_series_lists_its_files_in_order(tmp_path):
    case = tmp_path / "case"
    _write(case / "postProcessing/probes/0/p", "# Probe 0 (0 0 0)\n# Time 0\n1 1\n2 2\n")
    _write(case / "postProcessing/probes/2/p", "# Probe 0 (0 0 0)\n# Time 0\n2 5\n3 6\n")
    src = find_sources(str(case))[0]
    table = load_source(src)
    note = source_note(table, src, list(src.paths), None, "p.csv")
    assert "joined in this order" in note
    assert note.index("probes/0/p") < note.index("probes/2/p")
    assert "from the file's own heading" in note
    assert "Time:" not in note  # a time series has no sample time


def test_our_note_is_recognised(tmp_path):
    ours = _write(tmp_path / "a.source.txt", NOTE_MARKER + "\nTable: a.csv\n")
    theirs = _write(tmp_path / "b.source.txt", "my own notes\n")
    assert is_our_note(str(ours)) and not is_our_note(str(theirs))
    assert not is_our_note(str(tmp_path / "missing.source.txt"))


# ── what is plotted ──────────────────────────────────────────────────────────

def _lines_of(case: Path, columns, label_prefix=""):
    from services.plot_export import PlottedLine

    src = find_sources(str(case))[0]
    table = load_source(src)
    return [PlottedLine(label=f"{label_prefix}{c}", source=src, table=table, column=c,
                        time=None, files=list(src.paths)) for c in columns]


def test_lines_of_one_data_set_share_its_x_column(tmp_path):
    from services.plot_export import plotted_table

    case = tmp_path / "case"
    _write(case / "postProcessing/probes/0/p",
           "# Probe 0 (0 0 0)\n# Probe 1 (1 0 0)\n# Time 0 1\n1 1 10\n2 2 20\n")
    table, shared = plotted_table(_lines_of(case, ["probe1", "probe0"]))
    assert shared
    assert table_csv(table).splitlines() == ["Time,probe1,probe0", "1,10,1", "2,20,2"]


def test_lines_of_different_cases_keep_their_own_x_none_interpolated(tmp_path):
    from services.plot_export import plotted_note, plotted_table

    a, b = tmp_path / "a", tmp_path / "b"
    _write(a / "postProcessing/probes/0/p", "# Probe 0 (0 0 0)\n# Time 0\n1 1\n2 2\n3 3\n")
    _write(b / "postProcessing/probes/0/p", "# Probe 0 (0 0 0)\n# Time 0\n0.5 7\n")
    lines = _lines_of(a, ["probe0"], "a: ") + _lines_of(b, ["probe0"], "b: ")
    table, shared = plotted_table(lines)
    assert not shared
    assert table_csv(table).splitlines() == [
        "a: probe0: Time,a: probe0: probe0,b: probe0: Time,b: probe0: probe0",
        "1,1,0.5,7",
        "2,2,,",
        "3,3,,",
    ]
    note = plotted_note(lines, shared, "plot.csv")
    assert note.startswith(NOTE_MARKER)
    assert "none were interpolated" in note
    assert note.count("Line ") == 2 and str(b) in note


def test_a_chosen_x_column_is_exported_and_splits_shared_x(tmp_path):
    from services.plot_export import plotted_table

    case = tmp_path / "case"
    _write(case / "postProcessing/probes/0/p",
           "# Probe 0 (0 0 0)\n# Probe 1 (1 0 0)\n# Time 0 1\n1 1 10\n2 2 20\n")
    a, b = _lines_of(case, ["probe1", "probe1"])
    b.x_column = "probe0"  # the same column, plotted against another one
    table, shared = plotted_table([b])
    assert shared and table.names == ["probe0", "probe1"]
    table, shared = plotted_table([a, b])
    assert not shared
    assert table.names == ["probe1: Time", "probe1: probe1", "probe1: probe0", "probe1: probe1"]
