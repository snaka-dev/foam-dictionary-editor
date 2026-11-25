# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Plot Results' animation: a plot's sampled lines stepped through time.

A sampled line (a ``profile`` data set) is written once per output time, so
a plot holding some can be drawn once per time and the drawings played in
order. Everything else in the plot -- time series, residuals -- is drawn
whole in every frame.

* :func:`frame_times` -- the frames: every output time any animated line
  has, in numeric order. Two cases rarely write at the same times (two
  pitzDaily runs end at 281 and 381), and keeping only the shared times
  would often leave almost nothing.
* :func:`frame_spec` -- the plot at one frame: each sampled line at its
  latest time at or before the frame's, and left out until it has one; its
  colour pinned to the one it has with every line present, so a line that
  is missing early does not shift the others' colours; the axes fixed
  (:func:`fixed_ranges`) so they do not jump from frame to frame.
* :class:`AnimationWriter` -- GIF (Pillow, always there with matplotlib),
  MP4 (``ffmpeg``, offered only when installed) or numbered PNG frames.
  Files appear only when finished: a cancelled or failed save leaves
  nothing behind, and an existing file is replaced in one rename.

Qt-free; the window's Time slider and Save Animation… are in
``ui/dialogs/plot_results_dialog.py``.
"""
from __future__ import annotations

import dataclasses
import math
import os
import shutil
import subprocess
import tempfile
from collections.abc import Sequence

from services.plot_data import Source
from services.plot_spec import Axis, PlotSpec, Series, resolve

FORMATS = ("gif", "mp4", "png")
# matplotlib's own axes margin: the padding an automatic range gets.
_MARGIN = 0.05


def _time_key(time: str) -> float:
    try:
        return float(time)
    except ValueError:
        return math.inf


def _source_of(series: Series, sources: dict[str, list[Source]]) -> Source | None:
    return next((s for s in sources.get(series.case_dir, []) if s.key == series.key), None)


def _ensure_sources(spec: PlotSpec, sources: dict[str, list[Source]]) -> None:
    from services.plot_data import find_sources

    for s in spec.series:
        if s.case_dir not in sources:
            sources[s.case_dir] = find_sources(s.case_dir)


def frame_times(spec: PlotSpec, sources: dict[str, list[Source]]) -> list[str]:
    """Every output time of the plot's sampled lines, in numeric order.

    Empty when the plot has no sampled line; a single time is one frame,
    which is no animation.
    """
    _ensure_sources(spec, sources)
    times: dict[float, str] = {}
    for s in spec.series:
        src = _source_of(s, sources)
        if src is not None and src.kind == "profile":
            for t in src.times:
                times.setdefault(_time_key(t), t)
    return [times[k] for k in sorted(times)]


def latest_at(times: Sequence[str], time: str) -> str | None:
    """The latest of *times* at or before *time*; None if all are later."""
    limit = _time_key(time)
    before = [t for t in times if _time_key(t) <= limit]
    return max(before, key=_time_key) if before else None


def frame_spec(
    spec: PlotSpec,
    time: str,
    sources: dict[str, list[Source]],
    ranges: tuple[Axis, Axis] | None = None,
) -> PlotSpec:
    """*spec* as one frame at *time* (see the module docstring).

    *ranges* -- :func:`fixed_ranges`' result -- is passed in rather than
    computed here because it covers every frame and is the same for all.
    """
    _ensure_sources(spec, sources)
    series = []
    for index, s in enumerate(spec.series):
        # Pinned before any line is left out: "C<n>" is matplotlib's n-th
        # cycle colour, the one this line has with all of them drawn.
        s = dataclasses.replace(s, color=s.color or f"C{index}")
        src = _source_of(s, sources)
        if src is not None and src.kind == "profile":
            at = latest_at(src.times, time)
            if at is None:
                continue
            s = dataclasses.replace(s, time=at)
        series.append(s)
    out = dataclasses.replace(spec, series=series)
    if ranges is not None:
        out = dataclasses.replace(out, x=ranges[0], y=ranges[1])
    return out


def _padded(lo: float, hi: float, log: bool) -> tuple[float, float]:
    if log:
        lo, hi = math.log10(lo), math.log10(hi)
    pad = (hi - lo) * _MARGIN if hi > lo else (abs(hi) * _MARGIN or 1.0)
    lo, hi = lo - pad, hi + pad
    return (10 ** lo, 10 ** hi) if log else (lo, hi)


def fixed_ranges(
    spec: PlotSpec, times: Sequence[str], sources: dict[str, list[Source]]
) -> tuple[Axis, Axis]:
    """The x and y axes with every unset Min/Max filled from all frames' data.

    A range the user set is kept; the rest cover what any frame draws, with
    matplotlib's usual margin, so the axes hold still while the lines move.
    """
    xs: list[float] = []
    ys: list[float] = []
    for t in times:
        for r in resolve(frame_spec(spec, t, sources), sources).series:
            xs += r.x
            ys += r.y
    axes = []
    for axis, values in ((spec.x, xs), (spec.y, ys)):
        if axis.log:
            values = [v for v in values if v > 0]
        if not values or (axis.min is not None and axis.max is not None):
            axes.append(axis)
            continue
        lo, hi = _padded(min(values), max(values), axis.log)
        axes.append(dataclasses.replace(
            axis,
            min=axis.min if axis.min is not None else lo,
            max=axis.max if axis.max is not None else hi,
        ))
    return axes[0], axes[1]


def stamp_text(time: str) -> str:
    return f"t = {time}"


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def frames_directory(path: str) -> str:
    """Where a PNG sequence chosen as ``a/plot.png`` goes: ``a/plot_frames``."""
    return os.path.splitext(path)[0] + "_frames"


class AnimationWriter:
    """Collect frames (RGBA bytes) and write them as *fmt* to *path* on :meth:`finish`.

    Frames go to a temporary file or directory beside *path*, which
    :meth:`finish` renames into place and :meth:`abort` removes: nothing
    half-written is ever left under the name the user chose.
    """

    def __init__(self, path: str, fmt: str, fps: float) -> None:
        if fmt not in FORMATS:
            raise ValueError(f"unknown animation format {fmt!r}")
        self.path = path
        self.fmt = fmt
        self.fps = fps
        self.count = 0
        directory = os.path.dirname(os.path.abspath(path))
        self._frames: list = []
        self._ffmpeg: subprocess.Popen | None = None
        self._size: tuple[int, int] | None = None
        if fmt == "png":
            self._tmp = tempfile.mkdtemp(prefix=".frames-", dir=directory)
        else:
            fd, self._tmp = tempfile.mkstemp(prefix=".anim-", suffix="." + fmt, dir=directory)
            os.close(fd)

    def add(self, rgba: bytes, width: int, height: int) -> None:
        from PIL import Image

        if self._size is None:
            self._size = (width, height)
        elif self._size != (width, height):
            raise ValueError("frames differ in size")
        self.count += 1
        if self.fmt == "png":
            Image.frombuffer("RGBA", (width, height), rgba, "raw", "RGBA", 0, 1).save(
                os.path.join(self._tmp, f"frame_{self.count:04d}.png")
            )
        elif self.fmt == "gif":
            # Kept as palette images, a byte a pixel: Pillow writes a GIF only
            # once it has every frame.
            image = Image.frombuffer("RGBA", (width, height), rgba, "raw", "RGBA", 0, 1)
            self._frames.append(image.convert("RGB").quantize(colors=256))
        else:
            if self._ffmpeg is None:
                self._ffmpeg = self._start_ffmpeg(width, height)
            assert self._ffmpeg.stdin is not None
            self._ffmpeg.stdin.write(rgba)

    def _start_ffmpeg(self, width: int, height: int) -> subprocess.Popen:
        return subprocess.Popen(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{width}x{height}",
                "-r", repr(float(self.fps)), "-i", "-",
                # H.264 needs even dimensions; yuv420p plays everywhere.
                "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
                "-pix_fmt", "yuv420p", "-c:v", "libx264", self._tmp,
            ],
            stdin=subprocess.PIPE, stderr=subprocess.PIPE,
        )

    def finish(self) -> str:
        """Write the result under its real name; returns that name."""
        if self.count == 0:
            self.abort()
            raise ValueError("no frames")
        if self.fmt == "gif":
            self._frames[0].save(
                self._tmp, format="GIF", save_all=True, append_images=self._frames[1:],
                duration=round(1000 / self.fps), loop=0,
            )
            self._frames = []
        elif self.fmt == "mp4":
            assert self._ffmpeg is not None and self._ffmpeg.stdin is not None
            self._ffmpeg.stdin.close()
            err = self._ffmpeg.stderr.read().decode(errors="replace") if self._ffmpeg.stderr else ""
            if self._ffmpeg.wait() != 0:
                self.abort()
                raise OSError(f"ffmpeg failed: {err.strip()}")
        if self.fmt == "png":
            target = frames_directory(self.path)
            # Never over an existing folder: it may be anything of the user's,
            # and replacing it would delete whatever it holds. The window
            # offers a free name; a clash here is a race, so refuse.
            if os.path.lexists(target):
                self.abort()
                raise FileExistsError(target)
            # mkdtemp/mkstemp make private (0700/0600) entries; the result
            # should have what any new file of the user's gets.
            os.chmod(self._tmp, 0o777 & ~_umask())
            for name in os.listdir(self._tmp):
                os.chmod(os.path.join(self._tmp, name), 0o666 & ~_umask())
            os.rename(self._tmp, target)
            return target
        try:
            mode = os.stat(self.path).st_mode & 0o7777  # a replaced file keeps its own
        except FileNotFoundError:
            mode = 0o666 & ~_umask()
        os.chmod(self._tmp, mode)
        os.replace(self._tmp, self.path)
        return self.path

    def abort(self) -> None:
        if self._ffmpeg is not None:
            self._ffmpeg.kill()
            self._ffmpeg.wait()
        self._frames = []
        if os.path.isdir(self._tmp):
            shutil.rmtree(self._tmp, ignore_errors=True)
        elif os.path.exists(self._tmp):
            os.unlink(self._tmp)


def _umask() -> int:
    mask = os.umask(0)
    os.umask(mask)
    return mask
