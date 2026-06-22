# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)
from i18n import tr


class DuplicateCaseDialog(QDialog):
    def __init__(
        self,
        source_case_dir: str,
        default_dest_parent: str | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(tr("Duplicate Case"))
        self.setMinimumWidth(500)

        self._source = Path(source_case_dir)
        self._result_path: Path | None = None

        source_label = QLabel(str(self._source))
        source_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        source_label.setStyleSheet("color: #555;")

        dest_default = default_dest_parent if default_dest_parent else str(self._source.parent)
        self._dest_parent_edit = QLineEdit(dest_default)
        browse_btn = QPushButton(tr("Browse..."))
        browse_btn.clicked.connect(self._browse_parent)
        parent_row = QHBoxLayout()
        parent_row.addWidget(self._dest_parent_edit)
        parent_row.addWidget(browse_btn)

        self._name_edit = QLineEdit(self._source.name + "_copy")

        self._preview_label = QLabel()
        self._preview_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._preview_label.setStyleSheet("font-weight: bold;")

        self._dest_parent_edit.textChanged.connect(self._update_preview)
        self._name_edit.textChanged.connect(self._update_preview)

        # Copy mode radio buttons
        self._radio_all = QRadioButton(tr("Copy all files (full directory copy)"))
        self._radio_visible = QRadioButton(
            tr("Copy app-visible files only\n(system/controlDict, fvSchemes, fvSolution, …, constant/g, 0/, 0.orig/)")
        )
        self._radio_all.setChecked(True)

        self._copy_mode_group = QButtonGroup(self)
        self._copy_mode_group.addButton(self._radio_all)
        self._copy_mode_group.addButton(self._radio_visible)

        copy_mode_box = QGroupBox(tr("Copy mode"))
        copy_mode_layout = QVBoxLayout(copy_mode_box)
        copy_mode_layout.addWidget(self._radio_all)
        copy_mode_layout.addWidget(self._radio_visible)

        form = QFormLayout()
        form.addRow(tr("Source case:"), source_label)
        form.addRow(tr("Save in:"), parent_row)
        form.addRow(tr("New case name:"), self._name_edit)
        form.addRow(tr("Destination:"), self._preview_label)

        self._buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._buttons.accepted.connect(self._on_accept)
        self._buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(copy_mode_box)
        layout.addWidget(self._buttons)

        self._update_preview()

    def _browse_parent(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            tr("Select Destination Directory"),
            self._dest_parent_edit.text(),
        )
        if directory:
            self._dest_parent_edit.setText(directory)

    def _update_preview(self) -> None:
        parent = self._dest_parent_edit.text().strip()
        name = self._name_edit.text().strip()
        ok_btn = self._buttons.button(QDialogButtonBox.Ok)
        if parent and name:
            dest = Path(parent) / name
            self._preview_label.setText(str(dest))
            if ok_btn:
                ok_btn.setEnabled(True)
        else:
            self._preview_label.setText(tr("(incomplete)"))
            if ok_btn:
                ok_btn.setEnabled(False)

    def _on_accept(self) -> None:
        parent = self._dest_parent_edit.text().strip()
        name = self._name_edit.text().strip()
        if not parent or not name:
            return
        self._result_path = Path(parent) / name
        self.accept()

    @property
    def destination_path(self) -> Path | None:
        return self._result_path

    @property
    def copy_all_files(self) -> bool:
        return self._radio_all.isChecked()
