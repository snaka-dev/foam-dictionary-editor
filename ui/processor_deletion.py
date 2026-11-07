# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Run a verified processor* deletion off the GUI thread, with progress.

Deleting a large decomposed case takes long enough -- gigabytes, tens of
thousands of files -- that doing it on the GUI thread froze the window, and
the clicks a user made meanwhile queued up and fired afterwards. Here the
deletion runs on a worker thread behind an application-modal progress dialog:
the window keeps repainting, nothing can be clicked behind it, and **Stop**
ends it between two time directories, which is always safe because every
target was verified before the run began (see services/solver_run.py).

Two checks run on the same thread first, because they are the ones whose
answer can change between the confirmation and the deletion, or that take
too long to run before asking: whether any process is working in the case,
and -- when the user asked for it -- whether every compressed root file
decompresses to its closing line. Either finding stops the run before
anything is deleted.
"""
from __future__ import annotations

from PySide6.QtCore import QEventLoop, Qt, Signal
from PySide6.QtWidgets import QProgressDialog, QWidget

from i18n import tr
from services.solver_run import (
    DeletionCheck,
    DeletionResult,
    case_activity_problem,
    delete_processor_data,
    verify_compressed,
)
from ui.dialogs._worker_thread import _CancellableWorkerThread

_PERMILLE = 1000


class _DeletionThread(_CancellableWorkerThread):
    step = Signal(int, int, str)  # done, total, case-relative path
    checking = Signal(int, str)  # permille of compressed bytes read, path

    def __init__(self, case_dir: str, check: DeletionCheck, full_gz: bool) -> None:
        super().__init__()
        self._case_dir = case_dir
        self._check = check
        self._full_gz = full_gz
        self.result: DeletionResult | None = None

    def run(self) -> None:
        targets = 0
        busy = case_activity_problem(self._case_dir)
        if busy is not None:
            self.result = DeletionResult((), False, 0, targets, (busy,))
            return
        if self._full_gz and self._check.unverified_gz:
            def report(done: int, total: int, rel: str) -> None:
                self.checking.emit(done * _PERMILLE // max(total, 1), rel)

            found = verify_compressed(
                self._case_dir, self._check, report, lambda: self._cancelled
            )
            if found is None:
                self.result = DeletionResult((), True, 0, targets)
                return
            if found:
                self.result = DeletionResult((), False, 0, targets, found)
                return
        self.result = delete_processor_data(
            self._case_dir,
            self._check,
            progress=lambda done, total, rel: self.step.emit(done, total, rel),
            cancelled=lambda: self._cancelled,
        )


def run_deletion_with_progress(
    parent: QWidget, case_dir: str, check: DeletionCheck, *, full_gz: bool = False
) -> DeletionResult:
    """Delete what *check* covers, showing progress; return once it is done.

    ``full_gz`` first reads every file in ``check.unverified_gz`` to its end.
    """
    dialog = QProgressDialog(tr("Deleting processor* data…"), tr("Stop"), 0, 0, parent)
    dialog.setWindowTitle(tr("Delete processor* directories"))
    dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
    dialog.setAutoClose(False)
    dialog.setAutoReset(False)
    # Shown at once rather than after QProgressDialog's usual 4 s delay: the
    # point is that the window never looks frozen.
    dialog.setMinimumDuration(0)

    thread = _DeletionThread(case_dir, check, full_gz)

    def on_checking(permille: int, rel: str) -> None:
        if not thread._cancelled:
            dialog.setMaximum(_PERMILLE)
            dialog.setValue(permille)
            if rel:
                dialog.setLabelText(tr("Checking {path}…").format(path=rel))

    def on_step(done: int, total: int, rel: str) -> None:
        dialog.setMaximum(total)
        dialog.setValue(done)
        dialog.setLabelText(tr("Deleting {path}…").format(path=rel))

    def on_stop() -> None:
        thread.cancel()
        dialog.setLabelText(tr("Stopping…"))

    loop = QEventLoop()
    thread.checking.connect(on_checking)
    thread.step.connect(on_step)
    thread.finished.connect(loop.quit)
    dialog.canceled.connect(on_stop)

    dialog.show()
    thread.start()
    loop.exec()
    thread.wait()

    dialog.close()
    dialog.deleteLater()
    assert thread.result is not None
    return thread.result
