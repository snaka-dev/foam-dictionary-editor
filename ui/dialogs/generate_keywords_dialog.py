# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Dialog that scans an OpenFOAM installation and writes foam_keywords.json."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from i18n import tr
from ui.dialogs._worker_thread import _CancellableWorkerThread
from ui.widgets.installation_selector import InstallationSelector


class _GeneratorThread(_CancellableWorkerThread):
    finished_ok = Signal(int, str)   # count, output_path

    def __init__(self, project_dir: Path | None = None) -> None:
        super().__init__()
        self._project_dir = project_dir

    def run(self) -> None:
        try:
            from app_config.keyword_generator import generate
            count, path = generate(
                progress=lambda msg: self.progress.emit(msg),
                cancelled=lambda: self._cancelled,
                project_dir=self._project_dir,
            )
            self.finished_ok.emit(count, str(path))
        except RuntimeError as exc:
            self.finished_err.emit(str(exc))
        except Exception as exc:
            self.finished_err.emit(f"Unexpected error: {exc}")


class GenerateKeywordsDialog(QDialog):
    """Modal dialog that runs the OpenFOAM keyword scan in a background thread."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Generate OpenFOAM Keywords"))
        self.setMinimumWidth(560)
        self.setMinimumHeight(360)

        self._thread: _GeneratorThread | None = None

        layout = QVBoxLayout(self)

        self._info = QLabel(
            tr(
                "Scans the selected OpenFOAM installation (etc/caseDicts/, src/ and\n"
                "applications/ sources) and writes app_config/foam_keywords.json,\n"
                "which overrides the bundled foam_keywords.default.json."
            )
        )
        layout.addWidget(self._info)

        install_row = QHBoxLayout()
        install_row.addWidget(QLabel(tr("Installation:")))
        self._install_selector = InstallationSelector()
        self._install_selector.installations_available.connect(
            self._on_installations_available
        )
        self._install_selector.error.connect(self._append)
        install_row.addWidget(self._install_selector, 1)
        layout.addLayout(install_row)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(2000)
        layout.addWidget(self._log)

        buttons = QDialogButtonBox()
        self._generate_btn = QPushButton(tr("Generate"))
        self._cancel_btn   = QPushButton(tr("Cancel"))
        self._close_btn    = QPushButton(tr("Close"))

        buttons.addButton(self._generate_btn, QDialogButtonBox.ButtonRole.ActionRole)
        buttons.addButton(self._cancel_btn,   QDialogButtonBox.ButtonRole.RejectRole)
        buttons.addButton(self._close_btn,    QDialogButtonBox.ButtonRole.AcceptRole)
        layout.addWidget(buttons)

        self._cancel_btn.hide()
        self._close_btn.setEnabled(False)

        self._generate_btn.clicked.connect(self._on_generate)
        self._cancel_btn.clicked.connect(self._on_cancel)
        self._close_btn.clicked.connect(self.accept)

        self._install_selector.refresh()

    # ── installations ─────────────────────────────────────────────────────────

    def _on_installations_available(self, available: bool) -> None:
        if not available:
            self._append(
                tr(
                    "No OpenFOAM installation found — browse to one, or source "
                    "your OpenFOAM environment and reopen this dialog."
                )
            )

    def _current_project_dir(self) -> Path | None:
        return self._install_selector.current_root()

    # ── slots ─────────────────────────────────────────────────────────────────

    def _on_generate(self) -> None:
        self._log.clear()
        self._generate_btn.setEnabled(False)
        self._cancel_btn.show()
        self._close_btn.setEnabled(False)

        self._thread = _GeneratorThread(project_dir=self._current_project_dir())
        self._thread.progress.connect(self._append)
        self._thread.finished_ok.connect(self._on_done)
        self._thread.finished_err.connect(self._on_error)
        self._thread.start()

    def _on_cancel(self) -> None:
        if self._thread and self._thread.isRunning():
            self._thread.cancel()
            self._append(tr("Cancelling …"))
            self._cancel_btn.setEnabled(False)

    def _on_done(self, count: int, path: str) -> None:
        self._append(f"\n✓  Wrote {count} keywords → {path}")
        self._append(tr("This file overrides the bundled foam_keywords.default.json."))
        self._finish()

    def _on_error(self, msg: str) -> None:
        self._append(f"\n✗  {msg}")
        self._finish()

    def _finish(self) -> None:
        self._generate_btn.setEnabled(True)
        self._cancel_btn.hide()
        self._close_btn.setEnabled(True)
        self._thread = None

    def _append(self, msg: str) -> None:
        self._log.appendPlainText(msg)

    # ── cleanup ───────────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        if self._thread and self._thread.isRunning():
            self._thread.cancel()
            self._thread.wait(2000)
        super().closeEvent(event)
