# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QModelIndex, QPoint, Qt
from PySide6.QtGui import QAction, QResizeEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from i18n import tr
from ui.case_navigation import CaseNavigator
from ui.fonts import button_pixel_width

# Floors, not caps, for the glyph buttons -- a wider glyph in another font must
# not be clipped. See ui/fonts.py's button_pixel_width.
_GLYPH_BTN_MIN_WIDTH = 24


class CaseNavPanel(QWidget):
    """The Cases tab: a one-level-at-a-time browser over case directories.

    Owns no operation logic. Every action is raised on the shared CaseNavigator,
    which the main window connects; the Case Browser window drives the same
    navigator over the same model, so the two cannot drift.
    """

    def __init__(self, navigator: CaseNavigator, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._nav = navigator
        self._path_text = ""

        self._up_btn = _glyph_button("↑", tr("Go to the parent folder"))
        self._up_btn.clicked.connect(self._nav.go_up)

        self._refresh_btn = _glyph_button("⟳", tr("Rescan this folder from disk"))
        self._refresh_btn.clicked.connect(self._nav.refresh_current)

        self._path_label = QLabel()
        self._path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self._browse_btn = QPushButton(tr("Browse…"))
        self._browse_btn.setToolTip(tr("Open the full Case Browser window"))
        self._browse_btn.clicked.connect(self._nav.request_browser)

        self._tree = QTreeView()
        self._tree.setModel(self._nav.model)
        self._tree.setHeaderHidden(True)
        self._tree.setRootIsDecorated(True)
        self._tree.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
        self._tree.setSelectionBehavior(QTreeView.SelectionBehavior.SelectRows)
        # Same treatment as the file list: a long case name elides rather than
        # growing a horizontal scrollbar, and the full path is on the tooltip.
        self._tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._tree.setTextElideMode(Qt.TextElideMode.ElideRight)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._on_context_menu)
        self._tree.doubleClicked.connect(self._on_double_clicked)

        path_row = QHBoxLayout()
        path_row.setContentsMargins(0, 0, 0, 0)
        path_row.setSpacing(4)
        path_row.addWidget(self._up_btn)
        path_row.addWidget(self._path_label, 1)
        path_row.addWidget(self._refresh_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addLayout(path_row)
        layout.addWidget(self._tree, 1)
        layout.addWidget(self._browse_btn)

        self._nav.location_changed.connect(self.set_location)

    # ── public API ───────────────────────────────────────────────────────────

    def set_location(self, path: str) -> None:
        """Re-root the view at *path* and update the path label."""
        self._path_text = path
        self._update_path_label()
        index = self._nav.model.index_for_path(Path(path))
        self._tree.setRootIndex(index)
        self._up_btn.setEnabled(Path(path).parent != Path(path))

    def selected_path(self) -> Path | None:
        indexes = self._tree.selectionModel().selectedIndexes() if self._tree.selectionModel() else []
        for index in indexes:
            path = self._nav.model.path_for_index(index)
            if path is not None:
                return path
        return None

    # ── internals ────────────────────────────────────────────────────────────

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._update_path_label()

    def _update_path_label(self) -> None:
        if not self._path_text:
            self._path_label.setText("")
            self._path_label.setToolTip("")
            return
        metrics = self._path_label.fontMetrics()
        width = max(40, self._path_label.width())
        # ElideMiddle, not ElideRight: the informative half of a path is its
        # tail, and the head names the drive it is under.
        self._path_label.setText(
            metrics.elidedText(self._path_text, Qt.TextElideMode.ElideMiddle, width)
        )
        self._path_label.setToolTip(self._path_text)

    def _on_double_clicked(self, index: QModelIndex) -> None:
        entry = self._nav.model.entry_for_index(index)
        if entry is None:
            return
        # A case opens rather than expanding: what is inside it is the file
        # list's job, and two browsers over one case is the confusion this
        # panel exists to remove.
        if entry.is_case:
            self._nav.request_open(entry.path)
        else:
            self._nav.go_to(entry.path)

    def _on_context_menu(self, pos: QPoint) -> None:
        index = self._tree.indexAt(pos)
        menu, actions = self._build_context_menu(index)
        chosen = menu.exec(self._tree.viewport().mapToGlobal(pos))
        handler = actions.get(chosen) if chosen is not None else None
        if handler is not None:
            handler()

    def _build_context_menu(
        self, index: QModelIndex
    ) -> tuple[QMenu, dict[QAction, Callable[[], None]]]:
        """The menu for *index*, paired with what each of its actions does.

        Split from _on_context_menu so the wiring between a menu row and the
        signal it raises can be tested without QMenu.exec(), which blocks
        waiting for a mouse an offscreen test has no way to supply.
        """
        entry = self._nav.model.entry_for_index(index)
        menu = QMenu(self)
        actions: dict[QAction, Callable[[], None]] = {}

        def add(label: str, handler: Callable[[], None]) -> QAction:
            action = menu.addAction(label)
            actions[action] = handler
            return action

        if entry is not None:
            path = entry.path
            if entry.is_case:
                add(tr("Open Case"), lambda: self._nav.request_open(path))
                add(tr("Compare with Case…"), lambda: self._nav.request_compare(path))
                add(tr("Duplicate Case…"), lambda: self._nav.request_duplicate(path))
            else:
                add(tr("Open Folder"), lambda: self._nav.go_to(path))
            menu.addSeparator()
            add(tr("Rename…"), lambda: self._nav.request_rename(path))
            add(tr("Move…"), lambda: self._nav.request_move(path))
            add(tr("Delete…"), lambda: self._nav.request_delete(path))
            menu.addSeparator()
            if entry.is_case:
                descend = add(
                    tr("Show Subfolders"),
                    lambda: self._nav.model.set_descend_override(path, not expanded),
                )
                expanded = self._nav.model.hasChildren(index)
                descend.setCheckable(True)
                descend.setChecked(expanded)

        current = self._nav.current_dir
        if current is not None:
            add(tr("New Folder…"), lambda: self._nav.request_new_folder(current))

        return menu, actions


def _glyph_button(glyph: str, tooltip: str) -> QPushButton:
    button = QPushButton(glyph)
    button.setFlat(True)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setToolTip(tooltip)
    button.setFixedWidth(max(_GLYPH_BTN_MIN_WIDTH, button_pixel_width(glyph)))
    return button
