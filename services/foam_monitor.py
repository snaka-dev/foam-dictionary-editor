# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Qt-free support for launching foamMonitor.

patched_foam_monitor() applies the same fix as foamMonitor_gnuplot_reread_fix.patch
(repository root) to a temp copy of the installed foamMonitor script, since newer
gnuplot versions deprecate `reread`. Used by ui/mixins/_foam_monitor_ops.py.
"""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path


def patched_foam_monitor() -> str | None:
    """Return path to a temp copy of foamMonitor with the gnuplot reread fix.

    Newer gnuplot versions deprecate `reread`.  The fix replaces it with
    `load ARG0` and changes the invocation to `gnuplot -e "load '$GPFILE'"`
    so that ARG0 is set to the script path before the loop starts.
    """
    original = shutil.which("foamMonitor")
    if original is None:
        return None
    try:
        src = Path(original).read_text(encoding="utf-8")
    except OSError:
        return None

    src = src.replace(
        '$GNUPLOT "$GPFILE" &',
        '$GNUPLOT -e "load \'$GPFILE\'" &',
    )
    src = src.replace("\nreread\n", "\nload ARG0\n")

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".sh", delete=False, encoding="utf-8"
    )
    tmp.write(src)
    tmp.close()
    os.chmod(tmp.name, 0o755)
    return tmp.name
