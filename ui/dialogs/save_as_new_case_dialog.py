# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from PySide6.QtWidgets import QButtonGroup, QGroupBox, QLabel, QRadioButton, QVBoxLayout

from i18n import tr
from ui.dialogs._case_dest_dialog import _CaseDestDialogBase
from ui.theme import colors


class SaveAsNewCaseDialog(_CaseDestDialogBase):
    """Pick a destination and copy mode for Save as New Case.

    Files are copied from disk according to the selected mode; any unsaved
    in-memory edits are then written on top so the new case reflects the
    current editor state.
    """

    def __init__(self, source_case_dir: str, parent=None):
        super().__init__(source_case_dir, "_new", parent=parent)
        self.setWindowTitle(tr("Save as New Case"))

        # Copy mode
        self._radio_visible = QRadioButton(
            tr(
                "Copy app-visible files only\n"
                "(system/controlDict, fvSchemes, fvSolution, …, constant/g, 0/, 0.orig/)"
            )
        )
        self._radio_all = QRadioButton(tr("Copy all files (full directory copy)"))
        self._radio_visible.setChecked(True)

        self._copy_mode_group = QButtonGroup(self)
        self._copy_mode_group.addButton(self._radio_visible)
        self._copy_mode_group.addButton(self._radio_all)

        copy_mode_box = QGroupBox(tr("Copy mode"))
        copy_mode_layout = QVBoxLayout(copy_mode_box)
        copy_mode_layout.addWidget(self._radio_visible)
        copy_mode_layout.addWidget(self._radio_all)

        note = QLabel(
            tr(
                "Unsaved edits in the current session are written into the new case.\n"
                "The original case is not modified."
            )
        )
        note.setStyleSheet(f"color: {colors().secondary_text}; font-style: italic;")
        note.setWordWrap(True)

        self._finish_layout(copy_mode_box, [note])
