# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Plot Results' animation: frames, the plot at a frame, and the writers."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from services.plot_animation import (
    AnimationWriter,
    fixed_ranges,
    frame_spec,
    frame_times,
    frames_directory,
)
from services.plot_spec import Axis, PlotSpec, Series, resolve

LINE = "postProcessing/graph/line_U.xy"


def _case(root: Path, name: str, times: dict[str, float]) -> str:
    case = root / name
    for t, scale in times.items():
        d = case / "postProcessing" / "graph" / t
        d.mkdir(parents=True)
        # position, U_x U_y U_z
        (d / "line_U.xy").write_text(f"0 0 0 0\n1 {scale} 0 0\n2 {2 * scale} 0 0\n")
    probes = case / "postProcessing" / "probes" / "0"
    probes.mkdir(parents=True)
    (probes / "p").write_text("# Probe 0 (0 0 0)\n# Time 0\n1 1\n2 2\n")
    return str(case)


@pytest.fixture
def two(tmp_path):
    a = _case(tmp_path, "a", {"10": 1.0, "20": 2.0, "100": 3.0})
    b = _case(tmp_path, "b", {"20": 5.0, "30": 6.0})
    spec = PlotSpec(series=[
        Series(a, LINE, "U_x"),
        Series(b, LINE, "U_x"),
        Series(a, "postProcessing/probes/p", "probe0"),
    ])
    return spec, {}


def test_frames_are_every_output_time_in_numeric_order(two):
    spec, sources = two
    # "100" after "30": numbers, not strings.
    assert frame_times(spec, sources) == ["10", "20", "30", "100"]
    assert frame_times(PlotSpec(series=[spec.series[2]]), sources) == []


def test_a_frame_holds_each_line_at_its_latest_time_or_leaves_it_out(two):
    spec, sources = two
    at10 = frame_spec(spec, "10", sources)
    # b has nothing before 20: left out; the time series stays.
    assert [(s.case_dir[-1], s.time) for s in at10.series] == [("a", "10"), ("a", None)]
    at30 = frame_spec(spec, "30", sources)
    assert [s.time for s in at30.series[:2]] == ["20", "30"]
    # Colours pinned to each line's place with all present, so b keeps C1.
    assert [s.color for s in at10.series] == ["C0", "C2"]
    assert [s.color for s in at30.series] == ["C0", "C1", "C2"]
    spec.series[0].color = "#123456"
    assert frame_spec(spec, "10", sources).series[0].color == "#123456"


def test_fixed_ranges_cover_every_frame_and_keep_what_the_user_set(two):
    spec, sources = two
    times = frame_times(spec, sources)
    x, y = fixed_ranges(spec, times, sources)
    # y up to b's 2 * 6 = 12 at t = 30, with matplotlib's 5 % margin.
    assert y.max == pytest.approx(12 + 0.6) and y.min == pytest.approx(-0.6)
    spec.y = Axis(min=-1.0)
    _, y = fixed_ranges(spec, times, sources)
    assert y.min == -1.0 and y.max == pytest.approx(12.6)  # margin from the data
    # And every frame drawn with them has the same limits.
    for t in times:
        assert resolve(frame_spec(spec, t, sources, (x, y)), sources).series


@pytest.mark.parametrize("fmt", ["gif", "png", "mp4"])
def test_writers_put_every_frame_in_place(tmp_path, fmt):
    if fmt == "mp4" and shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not installed")
    from PIL import Image

    path = tmp_path / f"anim.{fmt}"
    writer = AnimationWriter(str(path), fmt, fps=4)
    for shade in (0, 128, 255):
        writer.add(bytes([shade, 0, 0, 255]) * (31 * 21), 31, 21)  # odd size: mp4 pads
    written = Path(writer.finish())
    if fmt == "png":
        assert written == Path(frames_directory(str(path)))
        assert sorted(p.name for p in written.iterdir()) == [
            "frame_0001.png", "frame_0002.png", "frame_0003.png"]
    else:
        assert written == path and path.stat().st_size > 0
    if fmt == "gif":
        with Image.open(path) as gif:
            assert gif.n_frames == 3 and gif.info["duration"] == 250
    # Ordinary permissions, not the temporary file's private ones.
    import os

    mask = os.umask(0)
    os.umask(mask)
    assert written.stat().st_mode & 0o777 == (0o777 if fmt == "png" else 0o666) & ~mask
    # Nothing temporary left beside it.
    assert not [p for p in tmp_path.iterdir() if p.name.startswith(".")]


def test_an_aborted_or_clashing_save_leaves_nothing(tmp_path):
    writer = AnimationWriter(str(tmp_path / "a.gif"), "gif", 5)
    writer.add(bytes(4 * 4), 2, 2)
    writer.abort()
    assert list(tmp_path.iterdir()) == []
    # An existing frames folder is never replaced: it may be anything.
    mine = tmp_path / "b_frames"
    mine.mkdir()
    (mine / "precious.txt").write_text("keep")
    writer = AnimationWriter(str(tmp_path / "b.png"), "png", 5)
    writer.add(bytes(4 * 4), 2, 2)
    with pytest.raises(FileExistsError):
        writer.finish()
    assert (mine / "precious.txt").read_text() == "keep"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["b_frames"]
