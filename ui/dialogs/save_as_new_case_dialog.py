# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from PySide6.QtWidgets import QButtonGroup, QGroupBox, QLabel, QRadioButton, QVBoxLayout

from i18n import tr
from ui.dialogs._case_dest_dialog import _CaseDestDialogBase
from ui.label_fit import fit_wrapped_labels
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

        self._labels_fitted = False

    def showEvent(self, event):
        """Give the wrapped labels their real heights, once.

        A wrapped QLabel's sizeHint is measured at a width Qt guesses, not the one it gets,
        so a fixed-width dialog under-allocates and the last lines are never drawn -- see
        ui/label_fit.py. Only after the first layout pass does a label know its real width.
        """
        super().showEvent(event)
        if self._labels_fitted:
            return
        self._labels_fitted = True
        fit_wrapped_labels(self)
        # activate() first, so the new minimum heights travel back up through the layout
        # before the dialog's own size hint reflects them. Then resize() rather than
        # adjustSize(), which clamps a window to two thirds of the screen height.
        self.layout().activate()
        self.resize(self.width(), self.sizeHint().height())
