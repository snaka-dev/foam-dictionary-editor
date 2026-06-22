# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""
Tests for backup file creation logic.

These tests verify the backup filename format and file content,
exercising the same logic used by MainWindow._on_backup_file_requested
without requiring a full Qt application.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


# ── helpers that mirror main_window backup logic ──────────────────────────────

def _make_backup_path(original: Path, timestamp: str) -> Path:
    return original.parent / f"{original.name}.bak_{timestamp}"


def _create_backup(path: Path, content: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = _make_backup_path(path, timestamp)
    backup.write_text(content, encoding="utf-8")
    return backup


# ── backup filename format ────────────────────────────────────────────────────

class TestBackupFilename:
    _PATTERN = re.compile(r"^.+\.bak_\d{8}_\d{6}$")

    def test_filename_matches_pattern(self, tmp_path):
        p = tmp_path / "system" / "controlDict"
        ts = "20260502_143022"
        backup = _make_backup_path(p, ts)
        assert self._PATTERN.match(backup.name)

    def test_filename_preserves_original_name(self, tmp_path):
        p = tmp_path / "system" / "controlDict"
        backup = _make_backup_path(p, "20260502_143022")
        assert backup.name.startswith("controlDict")

    def test_backup_in_same_directory(self, tmp_path):
        (tmp_path / "system").mkdir()
        p = tmp_path / "system" / "controlDict"
        backup = _make_backup_path(p, "20260502_143022")
        assert backup.parent == p.parent

    def test_different_timestamps_give_different_names(self, tmp_path):
        p = tmp_path / "system" / "controlDict"
        b1 = _make_backup_path(p, "20260502_143022")
        b2 = _make_backup_path(p, "20260502_143055")
        assert b1 != b2


# ── backup file content ───────────────────────────────────────────────────────

class TestBackupContent:
    def test_backup_contains_exact_content(self, tmp_path):
        (tmp_path / "system").mkdir()
        p = tmp_path / "system" / "controlDict"
        p.write_text("original content", encoding="utf-8")
        backup = _create_backup(p, "original content")
        assert backup.read_text(encoding="utf-8") == "original content"

    def test_backup_contains_unsaved_buffer_content(self, tmp_path):
        (tmp_path / "system").mkdir()
        p = tmp_path / "system" / "controlDict"
        p.write_text("disk content", encoding="utf-8")
        # Simulate unsaved buffer being different from disk
        backup = _create_backup(p, "edited content not yet saved")
        assert backup.read_text(encoding="utf-8") == "edited content not yet saved"

    def test_original_file_unchanged_after_backup(self, tmp_path):
        (tmp_path / "system").mkdir()
        p = tmp_path / "system" / "controlDict"
        p.write_text("original", encoding="utf-8")
        _create_backup(p, "original")
        assert p.read_text(encoding="utf-8") == "original"

    def test_multiple_backups_coexist(self, tmp_path):
        (tmp_path / "system").mkdir()
        p = tmp_path / "system" / "controlDict"
        b1 = _make_backup_path(p, "20260502_143000")
        b2 = _make_backup_path(p, "20260502_143001")
        b1.write_text("v1", encoding="utf-8")
        b2.write_text("v2", encoding="utf-8")
        assert b1.read_text(encoding="utf-8") == "v1"
        assert b2.read_text(encoding="utf-8") == "v2"
