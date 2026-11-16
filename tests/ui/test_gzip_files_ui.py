# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Opening, saving, backing up and duplicating a compressed field in the app."""
from __future__ import annotations

import gzip
from pathlib import Path

import pytest

U = (
    "FoamFile\n{\n    version 2.0;\n    format ascii;\n    class volVectorField;\n    object U;\n}\n"
    "dimensions [0 1 -1 0 0 0 0];\ninternalField uniform (0 0 0);\n"
    "boundaryField\n{\n    inlet { type fixedValue; value uniform (1 0 0); }\n}\n"
)


@pytest.fixture
def case(tmp_path: Path) -> Path:
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "controlDict").write_text("FoamFile { object controlDict; }\nendTime 1;\n")
    (tmp_path / "0").mkdir()
    (tmp_path / "0" / "U.gz").write_bytes(gzip.compress(U.encode()))
    return tmp_path


def gz_text(path: Path) -> str:
    return gzip.decompress(path.read_bytes()).decode()


def test_open_shows_text_and_parses(main_window, case):
    win = main_window
    win._load_case_dir(str(case))
    path = str(case / "0" / "U.gz")
    assert win.file_list_panel.has_file(path)
    win.load_selected_file(path)
    assert win.editor_panel.get_text() == U
    assert win.state.parsed_roots[path] is not None


def test_ctrl_s_keeps_it_gzip(main_window, case):
    win = main_window
    win._load_case_dir(str(case))
    path = case / "0" / "U.gz"
    win.load_selected_file(str(path))
    win.save_file()  # unedited: the habitual Ctrl+S that used to corrupt it
    assert gz_text(path) == U
    win.editor_panel.set_text(U.replace("(1 0 0)", "(2 0 0)"))
    win.state.text_dirty = True
    win.save_file()
    assert "(2 0 0)" in gz_text(path)


def test_save_case_keeps_it_gzip(main_window, case):
    win = main_window
    win._load_case_dir(str(case))
    path = case / "0" / "U.gz"
    win.load_selected_file(str(path))
    win.editor_panel.set_text(U.replace("(1 0 0)", "(3 0 0)"))
    win.state.text_dirty = True
    win.save_all_files()
    assert "(3 0 0)" in gz_text(path)


def test_backup_keeps_the_format(main_window, case):
    win = main_window
    win._load_case_dir(str(case))
    path = case / "0" / "U.gz"
    assert win._create_backup(str(path))
    backups = list((case / "0").glob("U.gz.bak_*"))
    assert len(backups) == 1
    assert gz_text(backups[0]) == U


def test_unchanged_compressed_file_is_not_reported_as_changed(main_window, case):
    win = main_window
    win._load_case_dir(str(case))
    path = str(case / "0" / "U.gz")
    win.load_selected_file(path)
    assert win._changed_outside([path]) == {}
