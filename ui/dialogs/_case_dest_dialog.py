# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Shared base for DuplicateCaseDialog and SaveAsNewCaseDialog: both pick a
destination (parent directory + new-case name, with Browse... and a live
"parent/name" preview) plus a copy-mode (all files vs. app-visible files
only). See DEVELOPER.md's ui/dialogs bullet list.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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
    QWidget,
)

from i18n import tr
from ui.theme import colors


class _CaseDestDialogBase(QDialog):
    """Source label + destination parent/name + live preview + OK/Cancel.

    Subclasses build their own copy-mode radio group (setting
    ``self._radio_all``, which `copy_all_files` reads) and any extra widgets,
    then call `_finish_layout` to assemble and wire the dialog.
    """

    def __init__(
        self,
        source_case_dir: str,
        name_suffix: str,
        default_dest_parent: str | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setMinimumWidth(500)

        self._source = Path(source_case_dir)
        self._result_path: Path | None = None
        self._radio_all: QRadioButton  # set by subclass

        source_label = QLabel(str(self._source))
        source_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        source_label.setStyleSheet(f"color: {colors().secondary_text};")
        self._source_label = source_label

        dest_default = default_dest_parent if default_dest_parent else str(self._source.parent)
        self._dest_parent_edit = QLineEdit(dest_default)
        browse_btn = QPushButton(tr("Browse..."))
        browse_btn.clicked.connect(self._browse_parent)
        self._parent_row = QHBoxLayout()
        self._parent_row.addWidget(self._dest_parent_edit)
        self._parent_row.addWidget(browse_btn)

        self._name_edit = QLineEdit(self._source.name + name_suffix)

        self._preview_label = QLabel()
        self._preview_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._preview_label.setStyleSheet("font-weight: bold;")

        self._dest_parent_edit.textChanged.connect(self._update_preview)
        self._name_edit.textChanged.connect(self._update_preview)

    def _finish_layout(
        self, copy_mode_box: QGroupBox, extra_widgets: list[QWidget] | None = None
    ) -> None:
        form = QFormLayout()
        form.addRow(tr("Source case:"), self._source_label)
        form.addRow(tr("Save in:"), self._parent_row)
        form.addRow(tr("New case name:"), self._name_edit)
        form.addRow(tr("Destination:"), self._preview_label)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.accepted.connect(self._on_accept)
        self._buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(copy_mode_box)
        for widget in extra_widgets or []:
            layout.addWidget(widget)
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
        ok_btn = self._buttons.button(QDialogButtonBox.StandardButton.Ok)
        if parent and name:
            self._preview_label.setText(str(Path(parent) / name))
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
