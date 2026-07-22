# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for services/case_copier.py (service level, no UI)."""
from __future__ import annotations

import json

import pytest

from services.case_copier import copy_visible_files
from services.case_files_config import CaseFilesConfig


@pytest.fixture
def case_dir(tmp_path):
    """A minimal case with visible files plus entries list_case_files hides."""
    case = tmp_path / "myCase"
    (case / "system").mkdir(parents=True)
    (case / "constant").mkdir()
    (case / "0").mkdir()
    (case / "system" / "controlDict").write_text("application interFoam;\n")
    (case / "system" / "blockMeshDict").write_text("vertices ();\n")
    (case / "constant" / "transportProperties").write_text("nu 1e-06;\n")
    (case / "0" / "U").write_text("dimensions [0 1 -1 0 0 0 0];\n")
    (case / "Allrun").write_text("#!/bin/sh\nblockMesh\n")
    # Entries the file list never shows: run logs, results, unlisted files.
    (case / "log.blockMesh").write_text("Build: 12\n")
    (case / "0.5").mkdir()
    (case / "0.5" / "U").write_text("results\n")
    (case / "notes.txt").write_text("scratch\n")
    return case


class TestCopyVisibleFiles:
    def test_copies_visible_files_preserving_layout(self, case_dir, tmp_path):
        dest = tmp_path / "copy"
        copy_visible_files(str(case_dir), dest)
        assert (dest / "system" / "controlDict").read_text() == "application interFoam;\n"
        assert (dest / "system" / "blockMeshDict").is_file()
        assert (dest / "constant" / "transportProperties").is_file()
        assert (dest / "0" / "U").is_file()
        assert (dest / "Allrun").is_file()

    def test_skips_hidden_entries(self, case_dir, tmp_path):
        dest = tmp_path / "copy"
        copy_visible_files(str(case_dir), dest)
        assert not (dest / "log.blockMesh").exists()
        assert not (dest / "0.5").exists()
        assert not (dest / "notes.txt").exists()

    def test_extra_files_and_config_carry_over(self, case_dir, tmp_path):
        config = CaseFilesConfig(str(case_dir))
        config.add_file("notes.txt")
        config.save()
        dest = tmp_path / "copy"
        copy_visible_files(str(case_dir), dest)
        assert (dest / "notes.txt").is_file()
        config_copy = dest / config.config_filename
        assert config_copy.is_file()
        assert "notes.txt" in json.loads(config_copy.read_text())["extra_files"]

    def test_works_without_config_file(self, case_dir, tmp_path):
        dest = tmp_path / "copy"
        copy_visible_files(str(case_dir), dest)
        assert not (dest / CaseFilesConfig(str(case_dir)).config_filename).exists()

    def test_creates_nested_destination(self, case_dir, tmp_path):
        dest = tmp_path / "a" / "b" / "copy"
        copy_visible_files(str(case_dir), dest)
        assert (dest / "system" / "controlDict").is_file()
