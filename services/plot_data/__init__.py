# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Plot Results' data layer: find and read the text output of a case.

Qt-free. ``_reader`` parses one file and is self-contained (the exported
Python script embeds its source); ``_discover`` finds a case's data sets
and loads them through a stamp-keyed cache. See DEVELOPER.md's
"Plot Results".
"""
from services.plot_data._discover import (
    POST_PROCESSING,
    Source,
    SourceKind,
    clear_cache,
    find_sources,
    load_source,
    profile_path,
    source_for_key,
)
from services.plot_data._reader import Table, read_log_residuals, read_table, stitch

__all__ = [
    "POST_PROCESSING",
    "Source",
    "SourceKind",
    "Table",
    "clear_cache",
    "find_sources",
    "load_source",
    "profile_path",
    "read_log_residuals",
    "read_table",
    "source_for_key",
    "stitch",
]
