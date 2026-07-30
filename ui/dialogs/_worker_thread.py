# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Shared QThread base for FindExamplesDialog's _SearchThread and
GenerateKeywordsDialog's _GeneratorThread: both run one cancellable callable
in the background and report progress via a signal. See DEVELOPER.md.
"""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal


class _CancellableWorkerThread(QThread):
    """Base for a QThread running a single cancellable unit of work.

    Subclasses declare their own ``finished_ok`` signal (its payload differs
    per dialog) and implement ``run()``; the cancellation flag and
    ``progress``/``finished_err`` signals live here so both dialogs share one
    definition.
    """

    progress = Signal(str)
    finished_err = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True
