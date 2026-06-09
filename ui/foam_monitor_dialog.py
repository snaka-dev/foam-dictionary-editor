# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from i18n import tr

_DIALOG_WIDTH = 520


class FoamMonitorDialog(QDialog):
    """Options dialog for launching foamMonitor."""

    def __init__(
        self,
        case_dir: str,
        last_file: str = "",
        last_options: dict | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("foamMonitor"))
        self.setMinimumWidth(_DIALOG_WIDTH)

        opts = last_options or {}

        layout = QVBoxLayout(self)

        # ── file row ──────────────────────────────────────────────────────────
        file_label = QLabel(tr("File:"))
        self._file_edit = QLineEdit(last_file)
        self._file_edit.setPlaceholderText(
            tr("e.g. log.icoFoam or postProcessing/residuals/0/residuals.dat")
        )
        browse_btn = QPushButton(tr("Browse…"))
        browse_btn.clicked.connect(lambda: self._browse(case_dir))

        file_row = QHBoxLayout()
        file_row.addWidget(file_label)
        file_row.addWidget(self._file_edit, 1)
        file_row.addWidget(browse_btn)
        layout.addLayout(file_row)

        # ── options ───────────────────────────────────────────────────────────
        self._logscale_chk = QCheckBox(tr("Log scale  (-l)"))
        self._logscale_chk.setChecked(opts.get("logscale", False))
        self._grid_chk = QCheckBox(tr("Grid  (-g)"))
        self._grid_chk.setChecked(opts.get("grid", False))

        chk_row = QHBoxLayout()
        chk_row.addWidget(self._logscale_chk)
        chk_row.addSpacing(16)
        chk_row.addWidget(self._grid_chk)
        chk_row.addStretch()
        layout.addLayout(chk_row)

        self._refresh_spin = QSpinBox()
        self._refresh_spin.setRange(1, 3600)
        self._refresh_spin.setValue(opts.get("refresh", 10))
        self._refresh_spin.setSuffix(" s")

        self._idle_spin = QSpinBox()
        self._idle_spin.setRange(1, 86400)
        self._idle_spin.setValue(opts.get("idle", 60))
        self._idle_spin.setSuffix(" s")

        form = QFormLayout()
        form.setHorizontalSpacing(8)
        form.addRow(tr("Refresh (-r):"), self._refresh_spin)
        form.addRow(tr("Idle timeout (-i):"), self._idle_spin)
        layout.addLayout(form)

        self._extra_edit = QLineEdit(opts.get("extra", ""))
        self._extra_edit.setPlaceholderText(tr("Additional options (e.g. -y [0:1])"))
        extra_row = QHBoxLayout()
        extra_row.addWidget(QLabel(tr("Extra:")))
        extra_row.addWidget(self._extra_edit, 1)
        layout.addLayout(extra_row)

        # ── buttons ───────────────────────────────────────────────────────────
        layout.addStretch()
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton(tr("Cancel"))
        launch_btn = QPushButton(tr("Launch"))
        launch_btn.setDefault(True)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(launch_btn)
        layout.addLayout(btn_row)

        cancel_btn.clicked.connect(self.reject)
        launch_btn.clicked.connect(self.accept)

    def get_file(self) -> str:
        return self._file_edit.text().strip()

    def get_args(self) -> list[str]:
        args: list[str] = []
        if self._logscale_chk.isChecked():
            args.append("-l")
        if self._grid_chk.isChecked():
            args.append("-g")
        args += ["-r", str(self._refresh_spin.value())]
        args += ["-i", str(self._idle_spin.value())]
        import shlex
        extra = self._extra_edit.text().strip()
        if extra:
            args += shlex.split(extra)
        return args

    def get_options(self) -> dict:
        return {
            "logscale": self._logscale_chk.isChecked(),
            "grid": self._grid_chk.isChecked(),
            "refresh": self._refresh_spin.value(),
            "idle": self._idle_spin.value(),
            "extra": self._extra_edit.text().strip(),
        }

    def _browse(self, case_dir: str) -> None:
        path, _ = QFileDialog.getOpenFileName(self, tr("Select file to monitor"), case_dir)
        if path:
            self._file_edit.setText(path)
