# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListView,
    QPushButton,
    QSplitter,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from i18n import tr
from ui.case_navigation import CaseNavigator
from ui.layout_constants import SPLITTER_HANDLE_WIDTH

_DIALOG_WIDTH = 900
_DIALOG_HEIGHT = 560
_TREE_PANE_WIDTH = 300


class CaseBrowserDialog(QDialog):
    """Non-modal two-pane browser over the case directories on disk.

    Deliberately non-modal, like the log-summary and find-examples dialogs: it
    is a place to work from while the main window stays usable. It owns no
    state and no operation logic — the CaseNavigator it is handed is the same
    one the Cases tab drives, so the two panes, the tab and the main window all
    move together without any of them knowing about each other.
    """

    def __init__(self, navigator: CaseNavigator, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._nav = navigator
        self.setWindowTitle(tr("Case Browser"))
        self.resize(_DIALOG_WIDTH, _DIALOG_HEIGHT)
        self.setWindowModality(Qt.WindowModality.NonModal)

        # ── path row ──────────────────────────────────────────────────────
        self._up_btn = QPushButton(tr("Up"))
        self._up_btn.setAutoDefault(False)
        self._up_btn.clicked.connect(self._nav.go_up)
        self._home_btn = QPushButton(tr("Home"))
        self._home_btn.setAutoDefault(False)
        self._home_btn.clicked.connect(lambda: self._nav.go_to(Path.home()))
        self._refresh_btn = QPushButton(tr("Refresh"))
        self._refresh_btn.setAutoDefault(False)
        self._refresh_btn.clicked.connect(self._nav.refresh_current)
        self._path_label = QLabel()
        self._path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        path_row = QHBoxLayout()
        path_row.addWidget(self._path_label, 1)
        path_row.addWidget(self._up_btn)
        path_row.addWidget(self._home_btn)
        path_row.addWidget(self._refresh_btn)

        # ── the two panes, over one model ─────────────────────────────────
        self._tree = QTreeView()
        self._tree.setModel(self._nav.model)
        self._tree.setHeaderHidden(True)
        self._tree.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
        self._tree.clicked.connect(self._on_tree_clicked)

        self._list = QListView()
        self._list.setModel(self._nav.model)
        self._list.setEditTriggers(QListView.EditTrigger.NoEditTriggers)
        self._list.doubleClicked.connect(self._on_list_activated)
        self._list.selectionModel().selectionChanged.connect(self._update_actions)

        panes = QSplitter(Qt.Orientation.Horizontal)
        panes.addWidget(self._tree)
        panes.addWidget(self._list)
        panes.setSizes([_TREE_PANE_WIDTH, _DIALOG_WIDTH - _TREE_PANE_WIDTH])
        panes.setHandleWidth(SPLITTER_HANDLE_WIDTH)

        # ── action row ────────────────────────────────────────────────────
        self._open_btn = self._action_button(tr("Open Case"), self._on_open)
        self._compare_btn = self._action_button(tr("Compare"), self._on_compare)
        self._duplicate_btn = self._action_button(tr("Duplicate…"), self._on_duplicate)
        self._move_btn = self._action_button(tr("Move…"), self._on_move)
        self._rename_btn = self._action_button(tr("Rename…"), self._on_rename)
        self._delete_btn = self._action_button(tr("Delete…"), self._on_delete)
        self._new_folder_btn = self._action_button(tr("New Folder…"), self._on_new_folder)
        close_btn = QPushButton(tr("Close"))
        close_btn.setAutoDefault(False)
        close_btn.clicked.connect(self.close)

        action_row = QHBoxLayout()
        for button in (
            self._open_btn,
            self._compare_btn,
            self._duplicate_btn,
            self._move_btn,
            self._rename_btn,
            self._delete_btn,
            self._new_folder_btn,
        ):
            action_row.addWidget(button)
        action_row.addStretch(1)
        action_row.addWidget(close_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(path_row)
        layout.addWidget(panes, 1)
        layout.addLayout(action_row)

        self._nav.location_changed.connect(self.set_location)
        current = self._nav.current_dir
        if current is not None:
            self.set_location(str(current))
        self._update_actions()

    # ── public API ───────────────────────────────────────────────────────────

    def set_location(self, path: str) -> None:
        """Re-root the listing pane and select the same directory in the tree."""
        self._path_label.setText(path)
        index = self._nav.model.index_for_path(Path(path))
        self._list.setRootIndex(index)
        if index.isValid():
            self._tree.setCurrentIndex(index)
            self._tree.scrollTo(index)
        self._up_btn.setEnabled(Path(path).parent != Path(path))
        self._update_actions()

    def selected_path(self) -> Path | None:
        """The directory selected in the listing pane, if any."""
        model = self._list.selectionModel()
        if model is None:
            return None
        for index in model.selectedIndexes():
            path = self._nav.model.path_for_index(index)
            if path is not None:
                return path
        return None

    # ── internals ────────────────────────────────────────────────────────────

    def _action_button(self, label: str, slot) -> QPushButton:
        button = QPushButton(label)
        # Qt makes a dialog's push buttons auto-default, so Return would fire
        # whichever one it picked -- New Folder…, in testing, from a stray
        # Return with nothing focused. None of these should happen by accident.
        button.setAutoDefault(False)
        button.clicked.connect(slot)
        return button

    def _update_actions(self, *_args) -> None:
        path = self.selected_path()
        entry = None
        if path is not None:
            index = self._nav.model.index_for_path(path)
            entry = self._nav.model.entry_for_index(index)
        is_case = bool(entry is not None and entry.is_case)
        has_selection = path is not None
        self._open_btn.setEnabled(is_case)
        self._compare_btn.setEnabled(is_case)
        self._duplicate_btn.setEnabled(is_case)
        self._move_btn.setEnabled(has_selection)
        self._rename_btn.setEnabled(has_selection)
        self._delete_btn.setEnabled(has_selection)
        self._new_folder_btn.setEnabled(self._nav.current_dir is not None)

    def _on_tree_clicked(self, index: QModelIndex) -> None:
        path = self._nav.model.path_for_index(index)
        if path is not None:
            self._nav.go_to(path)

    def _on_list_activated(self, index: QModelIndex) -> None:
        entry = self._nav.model.entry_for_index(index)
        if entry is None:
            return
        if entry.is_case:
            self._nav.request_open(entry.path)
        else:
            self._nav.go_to(entry.path)

    def _on_open(self) -> None:
        path = self.selected_path()
        if path is not None:
            self._nav.request_open(path)

    def _on_compare(self) -> None:
        path = self.selected_path()
        if path is not None:
            self._nav.request_compare(path)

    def _on_duplicate(self) -> None:
        path = self.selected_path()
        if path is not None:
            self._nav.request_duplicate(path)

    def _on_move(self) -> None:
        path = self.selected_path()
        if path is not None:
            self._nav.request_move(path)

    def _on_rename(self) -> None:
        path = self.selected_path()
        if path is not None:
            self._nav.request_rename(path)

    def _on_delete(self) -> None:
        path = self.selected_path()
        if path is not None:
            self._nav.request_delete(path)

    def _on_new_folder(self) -> None:
        current = self._nav.current_dir
        if current is not None:
            self._nav.request_new_folder(current)
