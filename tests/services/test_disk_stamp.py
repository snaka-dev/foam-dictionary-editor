# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for services/disk_stamp.py (has a file changed since FoDE read it?)."""
from __future__ import annotations

import os
from pathlib import Path

from services.disk_stamp import CHANGED, DELETED, UNCHANGED, changed_since, take_stamp


def _bump(path: Path) -> None:
    """Move the mtime on, so the cheap stat test cannot pass by coincidence."""
    st = path.stat()
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))


def test_unchanged(tmp_path: Path):
    f = tmp_path / "controlDict"
    f.write_text("endTime 1;\n")
    stamp = take_stamp(str(f), "endTime 1;\n")
    assert stamp is not None
    assert changed_since(str(f), stamp) == UNCHANGED


def test_rewritten_by_another_program(tmp_path: Path):
    f = tmp_path / "controlDict"
    f.write_text("endTime 1;\n")
    stamp = take_stamp(str(f), "endTime 1;\n")
    f.write_text("endTime 2;\n")
    _bump(f)
    assert changed_since(str(f), stamp) == CHANGED


def test_same_size_rewrite_is_caught_by_the_text(tmp_path: Path):
    f = tmp_path / "controlDict"
    f.write_text("endTime 1;\n")
    stamp = take_stamp(str(f), "endTime 1;\n")
    f.write_text("endTime 9;\n")
    _bump(f)
    assert changed_since(str(f), stamp) == CHANGED


def test_touch_or_identical_rewrite_is_not_a_change(tmp_path: Path):
    f = tmp_path / "controlDict"
    f.write_text("endTime 1;\n")
    stamp = take_stamp(str(f), "endTime 1;\n")
    f.write_text("endTime 1;\n")
    _bump(f)
    assert changed_since(str(f), stamp) == UNCHANGED


def test_deleted(tmp_path: Path):
    f = tmp_path / "controlDict"
    f.write_text("endTime 1;\n")
    stamp = take_stamp(str(f), "endTime 1;\n")
    f.unlink()
    assert changed_since(str(f), stamp) == DELETED


def test_no_stamp_for_a_missing_file(tmp_path: Path):
    assert take_stamp(str(tmp_path / "nothing"), "") is None
