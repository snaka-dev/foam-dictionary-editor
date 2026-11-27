# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from services.case_files_config import CaseFilesConfig, is_inside_case
from services.case_loader import list_case_files
from services.case_paths import editable


@dataclass
class CopyReport:
    """What :func:`copy_visible_files` copied and what it left out, case-relative."""

    copied: list[str] = field(default_factory=list)
    # Listed, but its real location is outside the source case: a symlink, a
    # file under a linked directory, or a linked case config. Never copied,
    # so the new case cannot carry a copy of a file from elsewhere on disk.
    skipped: list[str] = field(default_factory=list)


def copy_visible_files(source_dir: str, dest: Path) -> CopyReport:
    """Copy only app-visible files from source_dir into dest, preserving subdirectory layout.

    Every source file must resolve inside the source case (services/case_paths.py);
    the rest are skipped and reported. *dest* is a fresh directory the caller has
    checked (``case_paths.copy_destination_problem``); everything under it is
    created here, so no link inside it can redirect a write.
    """
    source = Path(source_dir)
    config = CaseFilesConfig(source_dir)
    extra_files = config.get_extra_files() or None
    report = CopyReport()

    visible_paths = list_case_files(source_dir, extra_files)
    dest.mkdir(parents=True, exist_ok=True)
    for src_path_str in visible_paths:
        # CaseFilesConfig already refuses entries that leave the case by their
        # text; resolving on disk catches the links that text cannot show.
        try:
            rel = Path(src_path_str).relative_to(source)
        except ValueError:
            continue
        if not is_inside_case(str(rel)) or not editable(src_path_str, source):
            report.skipped.append(str(rel))
            continue
        dst_path = dest / rel
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path_str, dst_path)
        report.copied.append(str(rel))

    # Copy the per-case config file so extra files carry over to the duplicate.
    config_src = source / config.config_filename
    if os.path.lexists(config_src):
        if editable(config_src, source):
            shutil.copy2(str(config_src), dest / config.config_filename)
        else:
            report.skipped.append(config.config_filename)
    return report
