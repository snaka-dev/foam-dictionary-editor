# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from model.file_list_model import FileListModel
from services.case_loader import FIELD_DIRS, detect_time_dirs, list_directory_files
from i18n import tr

# Stored in headers to carry the clean group name for context-menu use.
_HEADER_GROUP_ROLE = Qt.UserRole + 1
# True on items that were added as user extra files (not default target files).
_EXTRA_FILE_ROLE = Qt.UserRole + 2

_EXTRA_FILE_COLOR = QColor("#2266AA")
# Stored on items that are symbolic links to another file.
_SYMLINK_ROLE = Qt.UserRole + 3
_SYMLINK_MARKER = " ⇢"
# Stored on the Results indicator item; value is list[str] of time dir names.
_TIME_DIRS_ROLE = Qt.UserRole + 4
# True on group-header items that correspond to a user-added extra directory.
_EXTRA_DIR_HEADER_ROLE = Qt.UserRole + 5

_EXTRA_DIR_HEADER_COLOR = QColor("#6644AA")
_DIFF_NONE_FG = QColor("#888888")    # gray  — visited, no diffs
_DIFF_HAS_FG  = QColor("#BB7700")    # amber — visited, has diffs
_DIFF_CAP = 50


def _diff_suffix(count: int | None) -> str:
    if count is None:
        return ""
    if count > _DIFF_CAP:
        return f"  ≠{_DIFF_CAP}+"
    return f"  ≠{count}"


def display_file_name(path: str) -> str:
    p = Path(path)
    parent = p.parent.name
    return f"{parent}/{p.name}" if parent else p.name




class FileListPanel(QWidget):
    file_selected = Signal(str)
    # Emitted when the user requests to create a new file: (case_dir, group_name)
    create_file_requested = Signal(str, str)
    # Emitted when the user requests to add files: (case_dir, group_name)
    add_file_requested = Signal(str, str)
    # Emitted when the user requests a backup of a file: absolute path
    backup_file_requested = Signal(str)
    # Emitted when the user opens the manage-extra-files dialog
    manage_extra_files_requested = Signal()
    # Emitted when the user removes a single extra file: absolute path
    remove_extra_file_requested = Signal(str)
    # Emitted when the user picks a time dir to add: relative dir name (e.g. "0.5")
    add_time_dir_requested = Signal(str)
    # Emitted when the user removes an extra dir from the file list: relative path
    remove_extra_dir_requested = Signal(str)
    # Emitted when the user requests to duplicate a file: absolute path
    duplicate_file_requested = Signal(str)
    # Emitted when the user requests to duplicate a directory: (case_dir, src_group, dst_group)
    duplicate_dir_requested = Signal(str, str, str)
    # Emitted when the user requests to delete a file from disk: absolute path
    delete_file_requested = Signal(str)
    # Emitted when the user requests to delete a directory: (case_dir, group_name)
    delete_dir_requested = Signal(str, str)
    save_file_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model = FileListModel()
        self._show_changed_only = False

        self._extra_btn = QPushButton()
        self._extra_btn.setFlat(True)
        self._extra_btn.setCursor(Qt.PointingHandCursor)
        self._extra_btn.setStyleSheet(
            "QPushButton { text-align: left; padding: 2px 4px;"
            " color: #2266AA; border: none; }"
            "QPushButton:hover { text-decoration: underline; }"
        )
        self._extra_btn.setVisible(False)
        self._extra_btn.clicked.connect(self.manage_extra_files_requested)

        self._changed_only_cb = QCheckBox(tr("Changed files only"))
        self._changed_only_cb.setVisible(False)
        self._changed_only_cb.toggled.connect(self._on_filter_changed)

        self._list = QListWidget()
        self._list.setAlternatingRowColors(False)
        self._list.setUniformItemSizes(True)
        self._list.itemSelectionChanged.connect(self._on_selection_changed)
        self._list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_context_menu)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._extra_btn)
        layout.addWidget(self._changed_only_cb)
        layout.addWidget(self._list)

    def load_files(
        self,
        paths: list[str],
        case_dir: str | None = None,
        extra_files: list[str] | None = None,
        extra_dirs: list[str] | None = None,
    ) -> None:
        self._model.load(paths, case_dir, extra_files, extra_dirs)
        loaded_set = set(paths)

        self._list.blockSignals(True)
        try:
            self._list.clear()
            for group, group_paths in self._model.sorted_groups():
                is_extra_dir = self._model.is_extra_dir(group)
                has_unlisted = _has_unlisted_files(
                    case_dir, group, loaded_set, self._model.extra_dir_set
                )
                self._list.addItem(_make_header(group, has_unlisted, is_extra_dir=is_extra_dir))
                for path in group_paths:
                    p = Path(path)
                    self._list.addItem(
                        _make_item(path, is_extra=self._model.is_extra_file(path), is_symlink=p.is_symlink())
                    )

            if case_dir:
                time_dirs = detect_time_dirs(case_dir, list(self._model.extra_dir_set) or None)
                if time_dirs:
                    self._list.addItem(_make_time_dirs_indicator(time_dirs))
        finally:
            self._list.blockSignals(False)

        self._update_extra_indicator(self._model.extra_file_count, self._model.extra_dir_count)

    def clear(self) -> None:
        self._list.clear()
        self._model.clear()
        self._update_extra_indicator(0, 0)

    def select_file(self, path: str) -> None:
        """Programmatically select and scroll to the item for the given path."""
        item = self._find_item_by_path(path)
        if item is not None:
            self._list.setCurrentItem(item)
            self._list.scrollToItem(item)

    def mark_dirty(self, path: str, dirty: bool) -> None:
        self._model.mark_dirty(path, dirty)
        item = self._find_item_by_path(path)
        if item is not None:
            self._refresh_item(item, path)

    def mark_diff(self, path: str, count: int) -> None:
        self._model.mark_diff(path, count)
        item = self._find_item_by_path(path)
        if item is not None:
            self._refresh_item(item, path)
            if self._show_changed_only:
                item.setHidden(count == 0)

    def clear_diff_marks(self) -> None:
        self._model.clear_diff_marks()
        for i in range(self._list.count()):
            item = self._list.item(i)
            path = item.data(Qt.UserRole)
            if path:
                self._refresh_item(item, path)

    def set_diff_filter_enabled(self, enabled: bool) -> None:
        self._changed_only_cb.setVisible(enabled)
        if not enabled:
            self._changed_only_cb.setChecked(False)
            self._show_changed_only = False
            self._apply_diff_filter()

    def _on_filter_changed(self, checked: bool) -> None:
        self._show_changed_only = checked
        self._apply_diff_filter()

    def _apply_diff_filter(self) -> None:
        for i in range(self._list.count()):
            item = self._list.item(i)
            if not self._show_changed_only:
                item.setHidden(False)
                continue
            # Headers and non-file items are always shown.
            if item.data(_HEADER_GROUP_ROLE) is not None:
                item.setHidden(False)
                continue
            path = item.data(Qt.UserRole)
            if path is None:
                item.setHidden(False)
                continue
            count = self._model.diff_count(path)
            item.setHidden(count is None or count == 0)

    def _refresh_item(self, item: "QListWidgetItem", path: str) -> None:
        dirty = self._model.is_dirty(path)
        diff_count = self._model.diff_count(path)
        is_extra = bool(item.data(_EXTRA_FILE_ROLE))

        label = f"  {display_file_name(path)}"
        if item.data(_SYMLINK_ROLE):
            label += _SYMLINK_MARKER
        if dirty:
            label += " *"
        label += _diff_suffix(diff_count)
        item.setText(label)

        if dirty:
            color = QColor("#CC6600")
        elif diff_count is not None and diff_count > 0:
            color = _DIFF_HAS_FG
        elif diff_count == 0:
            color = _DIFF_NONE_FG
        elif is_extra:
            color = _EXTRA_FILE_COLOR
        else:
            color = None
        item.setData(Qt.ForegroundRole, color)

    def _find_item_by_path(self, path: str) -> QListWidgetItem | None:
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.data(Qt.UserRole) == path:
                return item
        return None

    def _update_extra_indicator(self, file_count: int, dir_count: int) -> None:
        if file_count == 0 and dir_count == 0:
            if self._model.case_dir is None:
                self._extra_btn.setVisible(False)
                return
            self._extra_btn.setText(tr("Manage extra files…"))
        else:
            parts = []
            if file_count:
                parts.append(f"files: {file_count}")
            if dir_count:
                parts.append(f"directories: {dir_count}")
            self._extra_btn.setText(tr("Extra") + " " + ", ".join(parts) + "  —  " + tr("Manage…"))
        self._extra_btn.setVisible(True)

    def _on_selection_changed(self) -> None:
        items = self._list.selectedItems()
        if not items:
            return
        path = items[0].data(Qt.UserRole)
        if path:
            self.file_selected.emit(path)

    def _on_context_menu(self, pos) -> None:
        item = self._list.itemAt(pos)
        if item is None:
            return

        # Results indicator row: offer to add a time dir.
        time_dirs = item.data(_TIME_DIRS_ROLE)
        if time_dirs is not None:
            if self._model.case_dir is None:
                return
            menu = QMenu(self.window())
            action_map: dict = {}
            for d in time_dirs:
                action = menu.addAction(tr("Add '{d}' to file list").format(d=d))
                if self._model.is_extra_dir(d):
                    action.setEnabled(False)
                action_map[action] = d
            chosen = menu.exec(self._list.viewport().mapToGlobal(pos))
            if chosen in action_map:
                self.add_time_dir_requested.emit(action_map[chosen])
            return

        group = item.data(_HEADER_GROUP_ROLE)
        if group is not None:
            # Header row: offer to create or add files in this directory.
            if self._model.case_dir is None:
                return
            menu = QMenu(self.window())
            new_action = menu.addAction(tr("New file in '{group}'...").format(group=group))
            add_action = menu.addAction(tr("Add files from '{group}'...").format(group=group))

            remove_dir_action = None
            if item.data(_EXTRA_DIR_HEADER_ROLE):
                menu.addSeparator()
                remove_dir_action = menu.addAction(tr("Remove '{group}' from file list").format(group=group))

            dup_dir_action = None
            counterpart = None
            if group in ("0", "0.orig"):
                counterpart = "0.orig" if group == "0" else "0"
                if not (Path(self._model.case_dir) / counterpart).exists():
                    dup_dir_action = menu.addAction(
                        tr("Duplicate '{src}' → '{dst}'...").format(src=group, dst=counterpart)
                    )

            delete_0_action = None
            if group == "0" and (Path(self._model.case_dir) / "0.orig").exists():
                menu.addSeparator()
                delete_0_action = menu.addAction(tr("Delete '0' directory..."))

            chosen = menu.exec(self._list.viewport().mapToGlobal(pos))
            if chosen == new_action:
                self.create_file_requested.emit(self._model.case_dir, group)
            elif chosen == add_action:
                self.add_file_requested.emit(self._model.case_dir, group)
            elif remove_dir_action is not None and chosen == remove_dir_action:
                self.remove_extra_dir_requested.emit(group)
            elif dup_dir_action is not None and chosen == dup_dir_action:
                self.duplicate_dir_requested.emit(self._model.case_dir, group, counterpart)
            elif delete_0_action is not None and chosen == delete_0_action:
                self.delete_dir_requested.emit(self._model.case_dir, group)
            return

        path = item.data(Qt.UserRole)
        if path:
            is_extra = bool(item.data(_EXTRA_FILE_ROLE))
            menu = QMenu(self.window())
            save_action = menu.addAction(tr("Save File\tCtrl+S"))
            menu.addSeparator()
            remove_action = None
            if is_extra:
                remove_action = menu.addAction(tr("Remove from extra files"))
                menu.addSeparator()
            duplicate_action = menu.addAction(tr("Duplicate..."))
            menu.addSeparator()
            backup_action = menu.addAction(tr("Create Backup"))
            menu.addSeparator()
            delete_action = menu.addAction(tr("Delete file..."))
            action = menu.exec(self._list.viewport().mapToGlobal(pos))
            if action == save_action:
                self.save_file_requested.emit()
            elif action == backup_action:
                self.backup_file_requested.emit(path)
            elif remove_action is not None and action == remove_action:
                self.remove_extra_file_requested.emit(path)
            elif action == duplicate_action:
                self.duplicate_file_requested.emit(path)
            elif action == delete_action:
                self.delete_file_requested.emit(path)




def _has_unlisted_files(
    case_dir: str | None,
    group: str,
    loaded_set: set[str],
    extra_dir_set: set[str] | None = None,
) -> bool:
    """Return True if group directory has files on disk not present in loaded_set."""
    if case_dir is None:
        return False
    if group in FIELD_DIRS:
        return False  # field dirs always load all files
    if extra_dir_set and group in extra_dir_set:
        return False  # extra dirs also load all files
    for f in list_directory_files(case_dir, group):
        if f not in loaded_set:
            return True
    return False


def _make_time_dirs_indicator(dirs: list[str]) -> QListWidgetItem:
    _MAX_SHOWN = 6
    shown = dirs[:_MAX_SHOWN]
    label = "Results: " + "  ".join(shown)
    if len(dirs) > _MAX_SHOWN:
        label += f"  … (+{len(dirs) - _MAX_SHOWN} more)"
    item = QListWidgetItem(label)
    item.setFlags(Qt.ItemIsEnabled)
    font = QFont(item.font())
    font.setBold(True)
    item.setFont(font)
    item.setForeground(QColor("#888888"))
    item.setData(_TIME_DIRS_ROLE, dirs)
    n = len(dirs)
    tip = f"{n} result dir(s) — right-click to add to file list"
    if n > 1:
        tip += f":  {dirs[0]} … {dirs[-1]}"
    elif n == 1:
        tip += f":  {dirs[0]}"
    item.setToolTip(tip)
    return item


def _make_header(
    group_name: str, has_unlisted: bool = False, is_extra_dir: bool = False
) -> QListWidgetItem:
    label = f"{group_name} [+]" if has_unlisted else group_name
    item = QListWidgetItem(label)
    font = QFont(item.font())
    font.setBold(True)
    item.setFont(font)
    # ItemIsEnabled so context menus work; not ItemIsSelectable so clicks skip it.
    item.setFlags(Qt.ItemIsEnabled)
    item.setData(_HEADER_GROUP_ROLE, group_name)
    if is_extra_dir:
        item.setData(_EXTRA_DIR_HEADER_ROLE, True)
        item.setForeground(_EXTRA_DIR_HEADER_COLOR)
    return item


def _make_item(path: str, is_extra: bool = False, is_symlink: bool = False) -> QListWidgetItem:
    label = f"  {display_file_name(path)}"
    if is_symlink:
        label += _SYMLINK_MARKER
    item = QListWidgetItem(label)
    item.setData(Qt.UserRole, path)
    item.setData(_EXTRA_FILE_ROLE, is_extra)
    item.setData(_SYMLINK_ROLE, is_symlink)

    tooltip = path
    if is_symlink:
        arrow = _SYMLINK_MARKER.strip()
        try:
            target = Path(path).readlink()
            tooltip += f"\n{arrow} {target}"
        except (OSError, NotImplementedError):
            tooltip += f"\n{arrow} (symlink)"
    item.setToolTip(tooltip)

    if is_extra:
        item.setForeground(_EXTRA_FILE_COLOR)
    if is_symlink:
        font = QFont(item.font())
        font.setItalic(True)
        item.setFont(font)
    return item
