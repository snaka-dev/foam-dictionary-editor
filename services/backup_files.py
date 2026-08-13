# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Locate the timestamped backup files a case directory has accumulated.

Shared by ui/dialogs/clean_backups_dialog.py (lists them for deletion) and
ui/mixins/_file_mgmt_ops.py (feeds that dialog). Backups are created by
MainWindow's manual "Backup File" action as ``<name>.bak_YYYYMMDD_HHMMSS``
next to the original.
"""
from __future__ import annotations

import re
from pathlib import Path

_BAK_RE = re.compile(r"\.bak_\d{8}_\d{6}$")


def find_backup_files(case_dir: str) -> list[tuple[str, str, int]]:
    """Return [(abs_path, rel_path, size_bytes)] for .bak_YYYYMMDD_HHMMSS files."""
    base = Path(case_dir)
    result = []
    for p in sorted(base.rglob("*"), key=lambda x: str(x.relative_to(base)).lower()):
        if p.is_file() and _BAK_RE.search(p.name):
            try:
                size = p.stat().st_size
            except OSError:
                size = 0
            result.append((str(p), str(p.relative_to(base)), size))
    return result
