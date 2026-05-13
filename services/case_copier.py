# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import shutil
from pathlib import Path

from services.case_files_config import CaseFilesConfig
from services.case_loader import list_case_files


def copy_visible_files(source_dir: str, dest: Path) -> None:
    """Copy only app-visible files from source_dir into dest, preserving subdirectory layout."""
    source = Path(source_dir)
    config = CaseFilesConfig(source_dir)
    extra_files = config.get_extra_files() or None

    visible_paths = list_case_files(source_dir, extra_files)
    dest.mkdir(parents=True, exist_ok=True)
    for src_path_str in visible_paths:
        rel = Path(src_path_str).relative_to(source)
        dst_path = dest / rel
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path_str, dst_path)

    # Copy the per-case config file so extra files carry over to the duplicate.
    config_src = source / config.config_filename
    if config_src.exists():
        shutil.copy2(str(config_src), dest / config.config_filename)
