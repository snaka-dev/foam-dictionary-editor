# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from PySide6.QtWidgets import QButtonGroup, QGroupBox, QRadioButton, QVBoxLayout

from i18n import tr
from ui.dialogs._case_dest_dialog import _CaseDestDialogBase


class DuplicateCaseDialog(_CaseDestDialogBase):
    def __init__(
        self,
        source_case_dir: str,
        default_dest_parent: str | None = None,
        parent=None,
    ):
        super().__init__(source_case_dir, "_copy", default_dest_parent, parent)
        self.setWindowTitle(tr("Duplicate Case"))

        # Copy mode radio buttons
        self._radio_all = QRadioButton(tr("Copy all files (full directory copy)"))
        self._radio_visible = QRadioButton(
            tr(
                "Copy app-visible files only\n"
                "(system/controlDict, fvSchemes, fvSolution, …, constant/g, 0/, 0.orig/)"
            )
        )
        self._radio_all.setChecked(True)

        self._copy_mode_group = QButtonGroup(self)
        self._copy_mode_group.addButton(self._radio_all)
        self._copy_mode_group.addButton(self._radio_visible)

        copy_mode_box = QGroupBox(tr("Copy mode"))
        copy_mode_layout = QVBoxLayout(copy_mode_box)
        copy_mode_layout.addWidget(self._radio_all)
        copy_mode_layout.addWidget(self._radio_visible)

        self._finish_layout(copy_mode_box)
