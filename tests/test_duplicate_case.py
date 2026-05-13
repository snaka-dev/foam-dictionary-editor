# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for services.case_copier.copy_visible_files."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from services.case_copier import copy_visible_files


def _make_case(base: Path, files: list[str], extra: list[str] | None = None) -> None:
    """Create a minimal fake case directory with the given relative file paths."""
    for rel in files:
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(rel, encoding="utf-8")
    for rel in extra or []:
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(rel, encoding="utf-8")


# ── what gets copied ──────────────────────────────────────────────────────────

class TestWhatIsCopied:
    def test_target_file_is_copied(self, tmp_path):
        """Files from TARGET_FILES are copied"""
        src = tmp_path / "src"
        _make_case(src, ["system/controlDict"])
        dest = tmp_path / "dest"

        copy_visible_files(str(src), dest)

        assert (dest / "system" / "controlDict").exists()

    def test_field_file_in_0_is_copied(self, tmp_path):
        """Field files inside 0/ are copied"""
        src = tmp_path / "src"
        _make_case(src, ["0/U", "0/p"])
        dest = tmp_path / "dest"

        copy_visible_files(str(src), dest)

        assert (dest / "0" / "U").exists()
        assert (dest / "0" / "p").exists()

    def test_field_file_in_0_orig_is_copied(self, tmp_path):
        """Field files inside 0.orig/ are copied"""
        src = tmp_path / "src"
        _make_case(src, ["0.orig/T"])
        dest = tmp_path / "dest"

        copy_visible_files(str(src), dest)

        assert (dest / "0.orig" / "T").exists()

    def test_non_visible_file_is_not_copied(self, tmp_path):
        """Files not shown by the app are not copied"""
        src = tmp_path / "src"
        _make_case(
            src,
            ["system/controlDict"],
            extra=[
                "constant/polyMesh/points",
                "processor0/0/U",
                "log.interFoam",
                "system/unknownDict",
            ],
        )
        dest = tmp_path / "dest"

        copy_visible_files(str(src), dest)

        assert not (dest / "constant" / "polyMesh").exists()
        assert not (dest / "processor0").exists()
        assert not (dest / "log.interFoam").exists()
        assert not (dest / "system" / "unknownDict").exists()

    def test_only_visible_files_end_up_in_dest(self, tmp_path):
        """Every file in the destination is app-visible"""
        src = tmp_path / "src"
        _make_case(
            src,
            ["system/controlDict", "system/fvSchemes", "0/U"],
            extra=["constant/polyMesh/points", "1/U"],
        )
        dest = tmp_path / "dest"

        copy_visible_files(str(src), dest)

        copied = {str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_file()}
        expected = {
            str(Path("system/controlDict")),
            str(Path("system/fvSchemes")),
            str(Path("0/U")),
        }
        assert copied == expected


# ── file content preservation ─────────────────────────────────────────────────

class TestFileContents:
    def test_file_content_is_preserved(self, tmp_path):
        """File content is identical after copying"""
        src = tmp_path / "src"
        (src / "system").mkdir(parents=True)
        (src / "system" / "controlDict").write_text(
            "application interFoam;\nendTime 1;\n", encoding="utf-8"
        )
        dest = tmp_path / "dest"

        copy_visible_files(str(src), dest)

        result = (dest / "system" / "controlDict").read_text(encoding="utf-8")
        assert result == "application interFoam;\nendTime 1;\n"

    def test_multiple_files_content_preserved(self, tmp_path):
        """Each of multiple files has its content correctly copied"""
        src = tmp_path / "src"
        files = {
            "system/controlDict": "controlDict content",
            "constant/g": "g content",
            "0/U": "U content",
        }
        for rel, content in files.items():
            p = src / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        dest = tmp_path / "dest"

        copy_visible_files(str(src), dest)

        for rel, content in files.items():
            assert (dest / rel).read_text(encoding="utf-8") == content


# ── destination directory creation ────────────────────────────────────────────

class TestDestinationCreation:
    def test_dest_directory_created_if_not_exists(self, tmp_path):
        """Destination directory is created automatically when it does not exist"""
        src = tmp_path / "src"
        _make_case(src, ["system/controlDict"])
        dest = tmp_path / "new_dest"

        assert not dest.exists()
        copy_visible_files(str(src), dest)
        assert dest.is_dir()

    def test_dest_nested_directory_created(self, tmp_path):
        """Destination is created even when the path is deeply nested"""
        src = tmp_path / "src"
        _make_case(src, ["system/controlDict"])
        dest = tmp_path / "a" / "b" / "c"

        copy_visible_files(str(src), dest)

        assert (dest / "system" / "controlDict").exists()

    def test_subdirectory_structure_preserved(self, tmp_path):
        """Subdirectory structure (system/, constant/, 0/) is preserved"""
        src = tmp_path / "src"
        _make_case(src, [
            "system/controlDict",
            "constant/transportProperties",
            "0/p",
            "0.orig/p",
        ])
        dest = tmp_path / "dest"

        copy_visible_files(str(src), dest)

        assert (dest / "system").is_dir()
        assert (dest / "constant").is_dir()
        assert (dest / "0").is_dir()
        assert (dest / "0.orig").is_dir()

    def test_empty_case_creates_dest_only(self, tmp_path):
        """Destination directory is created even when there are no visible files"""
        src = tmp_path / "src"
        src.mkdir()
        dest = tmp_path / "dest"

        copy_visible_files(str(src), dest)

        assert dest.is_dir()
        assert list(dest.iterdir()) == []


# ── comparison: app-visible copy vs full copytree ─────────────────────────────

class TestCopyAllVsVisible:
    def test_visible_copy_fewer_files_than_full_copy(self, tmp_path):
        """Visible-only copy has fewer files than a full copytree when non-visible files exist"""
        src = tmp_path / "src"
        _make_case(
            src,
            ["system/controlDict", "0/U"],
            extra=["constant/polyMesh/points", "log.run"],
        )
        dest_full = tmp_path / "dest_full"
        dest_visible = tmp_path / "dest_visible"

        shutil.copytree(str(src), str(dest_full))
        copy_visible_files(str(src), dest_visible)

        full_files = {p.relative_to(dest_full) for p in dest_full.rglob("*") if p.is_file()}
        visible_files = {p.relative_to(dest_visible) for p in dest_visible.rglob("*") if p.is_file()}
        assert len(visible_files) < len(full_files)

    def test_visible_copy_is_subset_of_full_copy(self, tmp_path):
        """The visible-only file set is a subset of the full copytree file set"""
        src = tmp_path / "src"
        _make_case(
            src,
            ["system/fvSchemes", "constant/g", "0/p"],
            extra=["1/p", "processor0/0/p"],
        )
        dest_full = tmp_path / "dest_full"
        dest_visible = tmp_path / "dest_visible"

        shutil.copytree(str(src), str(dest_full))
        copy_visible_files(str(src), dest_visible)

        full_files = {p.relative_to(dest_full) for p in dest_full.rglob("*") if p.is_file()}
        visible_files = {p.relative_to(dest_visible) for p in dest_visible.rglob("*") if p.is_file()}
        assert visible_files <= full_files


# ── extra files via .foam-editor-files.json ───────────────────────────────────

import json


class TestExtraFilesCopied:
    def test_extra_file_is_copied_when_listed_in_config(self, tmp_path):
        """A file listed in .foam-editor-files.json extra_files is included in the copy"""
        src = tmp_path / "src"
        _make_case(src, ["system/controlDict"])
        (src / "system" / "myCustomDict").write_text("custom", encoding="utf-8")
        (src / ".foam-editor-files.json").write_text(
            json.dumps({"extra_files": ["system/myCustomDict"]}), encoding="utf-8"
        )
        dest = tmp_path / "dest"

        copy_visible_files(str(src), dest)

        assert (dest / "system" / "myCustomDict").exists()

    def test_config_file_is_copied_to_dest(self, tmp_path):
        """The .foam-editor-files.json is copied alongside visible files"""
        src = tmp_path / "src"
        _make_case(src, ["system/controlDict"])
        (src / ".foam-editor-files.json").write_text(
            json.dumps({"extra_files": []}), encoding="utf-8"
        )
        dest = tmp_path / "dest"

        copy_visible_files(str(src), dest)

        assert (dest / ".foam-editor-files.json").exists()

    def test_no_config_file_does_not_raise(self, tmp_path):
        """copy_visible_files does not raise when no .foam-editor-files.json exists"""
        src = tmp_path / "src"
        _make_case(src, ["system/controlDict"])
        dest = tmp_path / "dest"

        copy_visible_files(str(src), dest)  # must not raise

        assert (dest / "system" / "controlDict").exists()
        assert not (dest / ".foam-editor-files.json").exists()
