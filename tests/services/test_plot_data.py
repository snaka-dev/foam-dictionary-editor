# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Plot Results' reader and discovery (services/plot_data/).

Every file body below is a shape found in real output: OpenCFD v2512/v2606
runs, or Foundation 7/dev source where no Foundation build was available to
run (see DEVELOPER.md's "Plot Results").
"""
from __future__ import annotations

import gzip
import math
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from services.plot_data import find_sources, load_source, read_log_residuals, read_table, stitch
from services.plot_data._reader import Table


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


# ── read_table: one file ────────────────────────────────────────────────────

def test_opencfd_forces_names_every_column(tmp_path):
    t = read_table(_write(tmp_path / "force.dat", (
        "# Force           \n"
        "# CofR            : (0 0 0)\n"
        "#\n"
        "# Time            \ttotal_x total_y total_z\tpressure_x pressure_y pressure_z\n"
        "0.001  1 2 3 4 5 6\n"
        "0.002  7 8 9 10 11 12\n"
    )))
    assert t.names == ["Time", "total_x", "total_y", "total_z",
                       "pressure_x", "pressure_y", "pressure_z"]
    assert t.column("pressure_z") == [6.0, 12.0]
    assert "# CofR            : (0 0 0)" in t.notes


def test_foundation_forces_nested_vectors_are_flattened_and_named(tmp_path):
    # forcesBase.C: "forces" << "(pressure viscous)", rows ((p) (v)) ((p) (v)).
    t = read_table(_write(tmp_path / "forces.dat", (
        "# Forces\n# CofR : (0 0 0)\n"
        "# Time forces(pressure viscous) moments(pressure viscous)\n"
        "0.1\t((1 2 3) (4 5 6)) ((7 8 9) (10 11 12))\n"
    )))
    assert t.names[:4] == ["Time", "forces_pressure_x", "forces_pressure_y", "forces_pressure_z"]
    assert t.column("moments_viscous_z") == [12.0]
    assert len(t.names) == 13


def test_probes_vector_columns_are_named_per_probe(tmp_path):
    t = read_table(_write(tmp_path / "U", (
        "# Probe 0 (0 0 0)\n# Probe 1 (1 0 0)\n"
        "# Time        0             1\n"
        "0.1  (1 2 3)  (4 5 6)\n"
    )))
    assert t.names == ["Time", "probe0_x", "probe0_y", "probe0_z",
                       "probe1_x", "probe1_y", "probe1_z"]


def test_solver_info_words_are_not_plottable(tmp_path):
    t = read_table(_write(tmp_path / "solverInfo.dat", (
        "# Solver information\n"
        "# Time  p_solver  p_initial  p_final  p_iters  p_converged\n"
        "1  GAMG  0.5  0.01  3  false\n"
        "2  GAMG  N/A  0.01  3  true\n"
    )))
    assert t.numeric_names() == ["Time", "p_initial", "p_final", "p_iters"]
    assert math.isnan(t.column("p_initial")[1])


def test_a_header_repeated_mid_file_is_skipped(tmp_path):
    # surfaceFieldValue after a mesh topology change.
    t = read_table(_write(tmp_path / "surfaceFieldValue.dat", (
        "# Region type : patch inlet\n# Time  \tsum(phi)\n0.1\t-1e-4\n"
        "# Region type : patch inlet\n# Time  \tsum(phi)\n0.2\t-2e-4\n"
    )))
    assert t.names == ["Time", "sum(phi)"]
    assert t.column("sum(phi)") == [-1e-4, -2e-4]


def test_rows_of_another_width_are_counted_not_misread(tmp_path):
    t = read_table(_write(tmp_path / "x.dat", "# Time a b\n1 2 3\n2 3\n3 4 5\n"))
    assert t.columns[0] == [1.0, 3.0]
    assert t.skipped_rows == 1


def test_interleaved_patch_rows_become_one_column_set_per_patch(tmp_path):
    t = read_table(_write(tmp_path / "wallShearStress.dat", (
        "# Wall shear stress\n# Time  patch  min  max\n"
        "1 lower (1 2 3) (4 5 6)\n1 upper (7 8 9) (1 1 1)\n"
        "2 lower (1 2 3) (4 5 6)\n2 upper (7 8 9) (2 2 2)\n"
    )))
    assert t.columns[0] == [1.0, 2.0]
    assert "min_x [lower]" in t.names and "max_z [upper]" in t.names
    assert t.column("max_z [upper]") == [1.0, 2.0]
    assert "patch" not in t.names


def test_one_patch_needs_no_pivot(tmp_path):
    t = read_table(_write(tmp_path / "wallShearStress.dat", (
        "# Time  patch  min\n1 plate 0.5\n2 plate 0.6\n"
    )))
    assert t.numeric_names() == ["Time", "min"]


@pytest.mark.parametrize(("stem", "n_values", "expected"), [
    # OpenCFD writes scalars before vectors and names the fields in the file.
    ("line_alpha.water_p_U", 5, ["alpha.water", "p", "U_x", "U_y", "U_z"]),
    ("centreLine_T_U", 4, ["T", "U_x", "U_y", "U_z"]),
    ("line_p_rgh_U", 4, ["p_rgh", "U_x", "U_y", "U_z"]),
    ("line_k", 1, ["k"]),
    # Four columns read either way: position + vector U, or x y z + scalar U.
    ("line_U", 3, ["U_x", "U_y", "U_z"]),
    ("line_wallShearStress", 3, ["wallShearStress_x", "wallShearStress_y", "wallShearStress_z"]),
])
def test_headerless_sample_names_come_from_the_file_name(tmp_path, stem, n_values, expected):
    row = "\t".join(["0.5"] + ["1"] * n_values)
    t = read_table(_write(tmp_path / f"{stem}.xy", row + "\n" + row + "\n"))
    assert t.names == ["position"] + expected


def test_headerless_sample_with_xyz_axis(tmp_path):
    t = read_table(_write(tmp_path / "pts_p.xy", "0 0 0 1\n1 0 0 2\n"))
    assert t.names == ["x", "y", "z", "p"]


def test_one_header_name_over_several_columns_is_numbered(tmp_path):
    t = read_table(_write(tmp_path / "C_d.dat", (
        "# Drag coefficient\n# number of radial bins: 3\n"
        "# Time        \tCd(per bin)   \n1e-5  0 2.5 1.4\n"
    )))
    assert t.names == ["Time", "Cd(per bin) [0]", "Cd(per bin) [1]", "Cd(per bin) [2]"]


def test_names_that_cannot_be_decoded_are_numbered(tmp_path):
    t = read_table(_write(tmp_path / "mystery.xy", "0 1 2\n1 2 3\n"))
    assert t.names[1:] == ["col 1", "col 2"]


def test_foundation_dev_sample_header_and_segments(tmp_path):
    # rawSetWriter: '#' then the header row; a blank line pair between segments.
    t = read_table(_write(tmp_path / "graph.xy", (
        "#      distance      U_x      U_y      U_z        p\n"
        "0 1 0 0 5\n0.1 2 0 0 6\n\n\n0.5 3 0 0 7\n"
    )))
    assert t.names == ["distance", "U_x", "U_y", "U_z", "p"]
    assert t.column("p") == [5.0, 6.0, 7.0]


def test_csv_with_a_header_line(tmp_path):
    t = read_table(_write(tmp_path / "line_p.csv", "x,y,z,p\n0,0,0,1\n1,0,0,2\n"))
    assert t.names == ["x", "y", "z", "p"]
    assert t.column("p") == [1.0, 2.0]


def test_gzipped_file(tmp_path):
    path = tmp_path / "p"
    path.write_bytes(gzip.compress(b"# Time a\n1 2\n"))
    assert read_table(path).column("a") == [2.0]


def test_empty_and_comment_only_files(tmp_path):
    assert read_table(_write(tmp_path / "a.dat", "")).names == []
    assert read_table(_write(tmp_path / "b.dat", "# Time a\n")).names == []


# ── stitch: restarts ────────────────────────────────────────────────────────

def test_a_restart_overrides_the_overlap():
    first = Table(["Time", "a"], [[1.0, 2.0, 3.0], [10.0, 20.0, 30.0]])
    second = Table(["Time", "a"], [[2.0, 3.0, 4.0], [21.0, 31.0, 41.0]])
    out = stitch([first, second])
    assert out.columns == [[1.0, 2.0, 3.0, 4.0], [10.0, 21.0, 31.0, 41.0]]


def test_a_column_one_segment_lacks_is_nan_there():
    first = Table(["Time", "a"], [[1.0], [1.0]])
    second = Table(["Time", "a", "b"], [[2.0], [2.0], [5.0]])
    out = stitch([first, second])
    assert out.names == ["Time", "a", "b"]
    assert math.isnan(out.column("b")[0]) and out.column("b")[1] == 5.0


# ── residuals from a solver log ─────────────────────────────────────────────

def test_log_residuals_take_the_first_of_each_step(tmp_path):
    log = _write(tmp_path / "log.pimpleFoam", (
        "Starting time loop\n\n"
        "Courant Number mean: 0.1 max: 0.5\n"
        "Time = 0.1\n\n"
        "smoothSolver:  Solving for Ux, Initial residual = 1, Final residual = 1e-6, No Iterations 3\n"
        "GAMG:  Solving for p, Initial residual = 0.5, Final residual = 1e-3, No Iterations 4\n"
        "GAMG:  Solving for p, Initial residual = 0.05, Final residual = 1e-7, No Iterations 9\n"
        "Time = 0.2s\n\n"
        "GAMG:  Solving for p, Initial residual = 0.2, Final residual = 1e-3, No Iterations 4\n"
        "ExecutionTime = 1 s\n"
    ))
    t = read_log_residuals(log)
    assert t.names == ["Time", "Ux", "p"]
    assert t.columns[0] == [0.1, 0.2]
    assert t.column("p") == [0.5, 0.2]
    assert t.column("Ux")[0] == 1.0 and math.isnan(t.column("Ux")[1])


# ── discovery ───────────────────────────────────────────────────────────────

def _case(tmp_path: Path) -> Path:
    case = tmp_path / "case"
    pp = case / "postProcessing"
    _write(pp / "forces" / "0" / "force.dat", "# Time a\n0.1 1\n0.2 2\n0.3 3\n")
    # A restart from 0.2: a new time directory...
    _write(pp / "forces" / "0.2" / "force.dat", "# Time a\n0.2 20\n0.4 40\n")
    # ... and OpenCFD's _<time> name when the file exists already.
    _write(pp / "forces" / "0.2" / "force_0.2.dat", "# Time a\n0.3 30\n")
    _write(pp / "probes" / "0" / "p", "# Probe 0 (0 0 0)\n# Time 0\n0.1 5\n")
    for t in ("0.1", "0.2"):
        _write(pp / "graph" / t / "line_p.xy", f"0 {t}\n1 {t}\n")
        _write(pp / "graph" / t / "line_p.vtp", "<VTKFile>")
    _write(pp / "cutting" / "0.1" / "plane.vtp", "<VTKFile>")
    _write(pp / "regionA" / "fo" / "0" / "x.dat", "# Time q\n1 2\n")
    _write(case / "log.simpleFoam", "Time = 1\nsmoothSolver: Solving for Ux, Initial residual = 1, Final")
    _write(case / "log.blockMesh", "Creating block mesh\n")
    _write(case / "log.fluentMeshToFoam", "No time loop here\n")
    return case


def test_find_sources_groups_files_into_data_sets(tmp_path):
    sources = {s.key: s for s in find_sources(_case(tmp_path))}
    assert set(sources) == {
        "postProcessing/forces/force.dat",
        "postProcessing/probes/p",
        "postProcessing/graph/line_p.xy",
        "postProcessing/regionA/fo/x.dat",
        "log.simpleFoam",
    }
    assert sources["postProcessing/graph/line_p.xy"].kind == "profile"
    assert sources["postProcessing/graph/line_p.xy"].times == ("0.1", "0.2")
    assert sources["postProcessing/forces/force.dat"].kind == "series"
    assert len(sources["postProcessing/forces/force.dat"].paths) == 3
    assert sources["log.simpleFoam"].kind == "residuals"


def test_restart_segments_are_stitched_in_order(tmp_path):
    sources = {s.key: s for s in find_sources(_case(tmp_path))}
    t = load_source(sources["postProcessing/forces/force.dat"])
    # 0..0.2 from the first run, 0.2 from the restart, then the _0.2 file.
    assert t.columns[0] == [0.1, 0.2, 0.3]
    assert t.column("a") == [1.0, 20.0, 30.0]


def test_profile_loads_the_latest_time_unless_told(tmp_path):
    src = next(s for s in find_sources(_case(tmp_path)) if s.kind == "profile")
    assert load_source(src).column("p") == [0.2, 0.2]
    assert load_source(src, "0.1").column("p") == [0.1, 0.1]


def test_a_case_without_output_has_no_sources(tmp_path):
    assert find_sources(tmp_path) == []


def test_the_cache_rereads_a_changed_file(tmp_path):
    case = _case(tmp_path)
    src = next(s for s in find_sources(case) if s.key.endswith("probes/p"))
    assert load_source(src).column("probe0") == [5.0]
    _write(Path(src.paths[0]), "# Probe 0 (0 0 0)\n# Time 0\n0.1 5\n0.2 6\n")
    assert load_source(src).column("probe0") == [5.0, 6.0]


def test_reader_is_self_contained(tmp_path):
    """The exported script embeds _reader.py; it must import nothing of FoDE's."""
    src = Path(__file__).resolve().parents[2] / "services" / "plot_data" / "_reader.py"
    shutil.copy(src, tmp_path / "reader_copy.py")
    data = _write(tmp_path / "d" / "f.dat", "# Time a\n1 2\n")
    code = f"import reader_copy; print(reader_copy.read_table({str(data)!r}).names)"
    out = subprocess.run(
        [sys.executable, "-I", "-c", f"import sys; sys.path.insert(0, {str(tmp_path)!r}); {code}"],
        capture_output=True, text=True, check=True,
    )
    assert out.stdout.strip() == "['Time', 'a']"


def test_a_half_written_last_row_is_dropped_only_while_the_file_is_written(tmp_path):
    import os
    import time

    path = tmp_path / "p"
    path.write_text("# Time p\n1 1\n2 2\n3 1.2")  # "1.2" of a row still being written
    assert read_table(path).column("p") == [1.0, 2.0]
    # A finished file whose last row lacks a newline keeps it.
    old = time.time() - 60
    os.utime(path, (old, old))
    assert read_table(path).column("p") == [1.0, 2.0, 1.2]
