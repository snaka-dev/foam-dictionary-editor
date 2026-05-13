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


class SaveAsNewCaseDialog(QDialog):
    """Pick a destination and copy mode for Save as New Case.

    Files are copied from disk according to the selected mode; any unsaved
    in-memory edits are then written on top so the new case reflects the
    current editor state.
    """

    def __init__(self, source_case_dir: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save as New Case")
        self.setMinimumWidth(500)

        self._source = Path(source_case_dir)
        self._result_path: Path | None = None

        source_label = QLabel(str(self._source))
        source_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        source_label.setStyleSheet("color: #555;")

        self._dest_parent_edit = QLineEdit(str(self._source.parent))
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_parent)
        parent_row = QHBoxLayout()
        parent_row.addWidget(self._dest_parent_edit)
        parent_row.addWidget(browse_btn)

        self._name_edit = QLineEdit(self._source.name + "_new")

        self._preview_label = QLabel()
        self._preview_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._preview_label.setStyleSheet("font-weight: bold;")

        self._dest_parent_edit.textChanged.connect(self._update_preview)
        self._name_edit.textChanged.connect(self._update_preview)

        # Copy mode
        self._radio_visible = QRadioButton(
            "Copy app-visible files only\n"
            "(system/controlDict, fvSchemes, fvSolution, …, constant/g, 0/, 0.orig/)"
        )
        self._radio_all = QRadioButton("Copy all files (full directory copy)")
        self._radio_visible.setChecked(True)

        self._copy_mode_group = QButtonGroup(self)
        self._copy_mode_group.addButton(self._radio_visible)
        self._copy_mode_group.addButton(self._radio_all)

        copy_mode_box = QGroupBox("Copy mode")
        copy_mode_layout = QVBoxLayout(copy_mode_box)
        copy_mode_layout.addWidget(self._radio_visible)
        copy_mode_layout.addWidget(self._radio_all)

        note = QLabel(
            "Unsaved edits in the current session are written into the new case.\n"
            "The original case is not modified."
        )
        note.setStyleSheet("color: #555; font-style: italic;")
        note.setWordWrap(True)

        form = QFormLayout()
        form.addRow("Source case:", source_label)
        form.addRow("Save in:", parent_row)
        form.addRow("New case name:", self._name_edit)
        form.addRow("Destination:", self._preview_label)

        self._buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._buttons.accepted.connect(self._on_accept)
        self._buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(copy_mode_box)
        layout.addWidget(note)
        layout.addWidget(self._buttons)

        self._update_preview()

    def _browse_parent(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Destination Directory",
            self._dest_parent_edit.text(),
        )
        if directory:
            self._dest_parent_edit.setText(directory)

    def _update_preview(self) -> None:
        parent = self._dest_parent_edit.text().strip()
        name = self._name_edit.text().strip()
        ok_btn = self._buttons.button(QDialogButtonBox.Ok)
        if parent and name:
            self._preview_label.setText(str(Path(parent) / name))
            if ok_btn:
                ok_btn.setEnabled(True)
        else:
            self._preview_label.setText("(incomplete)")
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
