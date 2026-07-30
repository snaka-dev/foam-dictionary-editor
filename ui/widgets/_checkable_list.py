# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Shared helpers for the checkable-QListWidget pattern used by
CleanBackupsDialog and ManageExtraFilesDialog: collecting the checked items
and bulk-setting every item's check state for Select All / Deselect All
buttons. See DEVELOPER.md's ui/widgets bullet list.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidget, QListWidgetItem


def checked_items(widget: QListWidget) -> list[QListWidgetItem]:
    """Return the items in *widget* whose check state is Qt.Checked."""
    return [
        widget.item(i)
        for i in range(widget.count())
        if widget.item(i).checkState() == Qt.CheckState.Checked
    ]


def set_all_check_states(widget: QListWidget, state: Qt.CheckState) -> None:
    """Set every item in *widget* to *state* in one batch.

    Signals are blocked for the duration so Select All / Deselect All emits a
    single follow-up update instead of one itemChanged per row.
    """
    widget.blockSignals(True)
    for i in range(widget.count()):
        widget.item(i).setCheckState(state)
    widget.blockSignals(False)
