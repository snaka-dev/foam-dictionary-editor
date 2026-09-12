# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

from PySide6.QtCore import QAbstractItemModel, QModelIndex, QObject, QPersistentModelIndex, Qt
from PySide6.QtGui import QColor, QFont

from services.case_scan import DirEntry, list_subdirectories
from ui.theme import colors

# Marker prepended to a case directory's name. A glyph rather than an icon:
# ui/icons.py's ICON_NAMES is asserted both ways against the files on disk, and
# the file list already marks rows this way (" ⇢" for symlinks, " ↳" for
# includes). It also survives selection, which a ForegroundRole colour does not.
CASE_MARKER = "◆ "


class _Node:
    """One directory in the lazily-built tree."""

    __slots__ = ("entry", "parent", "children", "fetched")

    def __init__(self, entry: DirEntry | None, parent: _Node | None) -> None:
        self.entry = entry
        self.parent = parent
        self.children: list[_Node] = []
        self.fetched = False

    @property
    def path(self) -> Path:
        # Only the invisible root has no entry, and set_root gives it one.
        assert self.entry is not None
        return self.entry.path


class CaseTreeModel(QAbstractItemModel):
    """Directories under a root, with OpenFOAM cases marked and not descended into.

    Deliberately not QFileSystemModel. Three of the four things this view needs
    contradict that class's contract rather than merely extending it — chiefly
    "do not descend into a case", which QFileSystemModel populates anyway and
    which a proxy cannot suppress without reporting fewer rows than its source.
    What it would buy is a faithful mirror of the filesystem; this is a *case*
    browser whose node set is deliberately not the filesystem's.

    Populated one level at a time through canFetchMore/fetchMore, so the cost of
    classifying a directory is paid only for rows that are actually shown.
    """

    COL_NAME = 0

    #: The row's DirEntry, for controllers that need the raw facts.
    ENTRY_ROLE = Qt.ItemDataRole.UserRole + 1

    def __init__(
        self,
        *,
        describe: Callable[[DirEntry], str] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        # Tooltip text is injected rather than built here: tests/test_i18n.py
        # only scans ui/, so a tr() literal in this module would never be
        # checked against i18n/ja.py and would ship untranslated in silence.
        self._describe = describe
        self._root = _Node(None, None)
        self._open_case: str | None = None
        self._descend_overrides: set[Path] = set()
        self._include_hidden = False

    # ── population ───────────────────────────────────────────────────────────

    def set_root(self, root: Path) -> None:
        """Rebuild the tree beneath *root*. Overrides and expansion are dropped."""
        self.beginResetModel()
        self._descend_overrides.clear()
        self._root = _Node(_root_entry(root), None)
        self.endResetModel()

    def root_path(self) -> Path | None:
        return self._root.entry.path if self._root.entry is not None else None

    def set_include_hidden(self, include: bool) -> None:
        if include == self._include_hidden:
            return
        self._include_hidden = include
        root_path = self.root_path()
        if root_path is not None:
            self.set_root(root_path)

    def set_open_case(self, case_dir: str | None) -> None:
        """Mark *case_dir* as the case currently open in the window (drawn bold)."""
        if case_dir == self._open_case:
            return
        previous = self._open_case
        self._open_case = case_dir
        for path in (previous, case_dir):
            if path:
                self._emit_changed_for_path(Path(path))

    def set_descend_override(self, path: Path, descend: bool) -> None:
        """Allow (or stop allowing) descending into the case directory *path*.

        is_openfoam_case is loose — any directory holding `system/` or
        `constant/` qualifies — so a false positive would hide a whole subtree.
        This is the per-path escape hatch, rather than a stricter rule that
        would stop marking real cases the app is willing to open.
        """
        resolved = _safe_resolve(path)
        if descend:
            self._descend_overrides.add(resolved)
        else:
            self._descend_overrides.discard(resolved)
        index = self.index_for_path(path)
        self.refresh(index)

    def refresh(self, index: QModelIndex | None = None) -> None:
        """Re-scan one node from disk, dropping anything already loaded below it."""
        target = QModelIndex() if index is None else index
        node = self._node_for_index(target)
        if node.children:
            self.beginRemoveRows(target, 0, len(node.children) - 1)
            node.children = []
            self.endRemoveRows()
        node.fetched = False
        if node.entry is not None and node is not self._root:
            # has_subdirs / is_case may have changed on disk since it was listed.
            node.entry = _restat(node.entry, self._include_hidden)
            self.dataChanged.emit(target, target)
        if self.canFetchMore(target):
            self.fetchMore(target)

    # ── path <-> index ───────────────────────────────────────────────────────

    def index_for_path(self, path: Path) -> QModelIndex:
        """Index of *path*, fetching each level on the way down. Invalid if absent."""
        root_path = self.root_path()
        if root_path is None:
            return QModelIndex()
        target = _safe_resolve(path)
        root_resolved = _safe_resolve(root_path)
        if target == root_resolved:
            return QModelIndex()
        try:
            parts = target.relative_to(root_resolved).parts
        except ValueError:
            return QModelIndex()
        index = QModelIndex()
        for part in parts:
            if self.canFetchMore(index):
                self.fetchMore(index)
            node = self._node_for_index(index)
            for row, child in enumerate(node.children):
                if child.path.name == part:
                    index = self.createIndex(row, 0, child)
                    break
            else:
                return QModelIndex()
        return index

    def path_for_index(self, index: QModelIndex) -> Path | None:
        entry = self.entry_for_index(index)
        if entry is not None:
            return entry.path
        return self.root_path() if not index.isValid() else None

    def entry_for_index(self, index: QModelIndex) -> DirEntry | None:
        if not index.isValid():
            return None
        node = index.internalPointer()
        return node.entry if isinstance(node, _Node) else None

    # ── QAbstractItemModel ───────────────────────────────────────────────────

    def index(
        self,
        row: int,
        column: int,
        parent: QModelIndex | QPersistentModelIndex = QModelIndex(),
    ) -> QModelIndex:
        parent_index = _as_index(parent)
        if not self.hasIndex(row, column, parent_index):
            return QModelIndex()
        children = self._node_for_index(parent_index).children
        if row >= len(children):
            return QModelIndex()
        return self.createIndex(row, column, children[row])

    def parent(  # type: ignore[override]
        self, index: QModelIndex | QPersistentModelIndex = QModelIndex()
    ) -> QModelIndex:
        if not index.isValid():
            return QModelIndex()
        node = cast(QModelIndex, index).internalPointer()
        if not isinstance(node, _Node):
            return QModelIndex()
        parent_node = node.parent
        if parent_node is None or parent_node is self._root:
            return QModelIndex()
        grandparent = parent_node.parent
        siblings = grandparent.children if grandparent is not None else []
        try:
            row = siblings.index(parent_node)
        except ValueError:
            return QModelIndex()
        return self.createIndex(row, 0, parent_node)

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        parent_index = _as_index(parent)
        if parent_index.column() > 0:
            return 0
        return len(self._node_for_index(parent_index).children)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return 1

    def hasChildren(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> bool:
        parent_index = _as_index(parent)
        node = self._node_for_index(parent_index)
        entry = node.entry
        if entry is None:
            # No set_root() yet. Saying True here would have canFetchMore
            # promise children that fetchMore cannot go and get.
            return False
        if node is self._root:
            return True
        if entry.is_case and _safe_resolve(entry.path) not in self._descend_overrides:
            # A case is a leaf here: what is inside it is the file list's job.
            return False
        if not entry.readable:
            return False
        return entry.has_subdirs if not node.fetched else bool(node.children)

    def canFetchMore(self, parent: QModelIndex | QPersistentModelIndex, /) -> bool:
        parent_index = _as_index(parent)
        node = self._node_for_index(parent_index)
        return not node.fetched and self.hasChildren(parent_index)

    def fetchMore(self, parent: QModelIndex | QPersistentModelIndex, /) -> None:
        parent_index = _as_index(parent)
        node = self._node_for_index(parent_index)
        if node.fetched or node.entry is None:
            # entry is None only before the first set_root(); hasChildren says
            # False in that state, and this keeps the two answers consistent
            # for a caller that reaches fetchMore without asking first.
            return
        entries = list_subdirectories(node.path, include_hidden=self._include_hidden)
        node.fetched = True
        if not entries:
            return
        self.beginInsertRows(parent_index, 0, len(entries) - 1)
        node.children = [_Node(entry, node) for entry in entries]
        self.endInsertRows()

    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        /,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object:
        entry = self.entry_for_index(_as_index(index))
        if entry is None:
            return None
        if role == self.ENTRY_ROLE:
            return entry
        if role == Qt.ItemDataRole.DisplayRole:
            return f"{CASE_MARKER}{entry.name}" if entry.is_case else entry.name
        if role == Qt.ItemDataRole.ToolTipRole:
            return self._describe(entry) if self._describe is not None else str(entry.path)
        if role == Qt.ItemDataRole.FontRole:
            if self._open_case and _safe_resolve(Path(self._open_case)) == _safe_resolve(entry.path):
                font = QFont()
                font.setBold(True)
                return font
            return None
        if role == Qt.ItemDataRole.ForegroundRole and not entry.readable:
            return QColor(colors().disabled_fg)
        return None

    def flags(self, index: QModelIndex | QPersistentModelIndex, /) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        entry = self.entry_for_index(_as_index(index))
        if entry is not None and not entry.readable:
            return Qt.ItemFlag.ItemIsEnabled
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    # ── internals ────────────────────────────────────────────────────────────

    def _node_for_index(self, index: QModelIndex) -> _Node:
        if index.isValid():
            node = index.internalPointer()
            if isinstance(node, _Node):
                return node
        return self._root

    def _emit_changed_for_path(self, path: Path) -> None:
        index = self.index_for_path(path)
        if index.isValid():
            self.dataChanged.emit(index, index)


def _as_index(index: QModelIndex | QPersistentModelIndex) -> QModelIndex:
    """Narrow a model index to QModelIndex.

    Qt declares these virtuals as taking either kind, so the overrides have to
    accept both to satisfy Liskov, but Qt itself only ever passes a plain
    QModelIndex to a model's own methods. The cast is a typing formality, not a
    runtime conversion.
    """
    return cast(QModelIndex, index)


def _safe_resolve(path: Path) -> Path:
    """Resolve *path* without raising on a broken link or a vanished directory."""
    try:
        return path.resolve()
    except OSError:
        return Path(str(path))


def _root_entry(root: Path) -> DirEntry:
    """A DirEntry for the invisible root node, which is never itself displayed."""
    return DirEntry(
        path=root,
        name=root.name or str(root),
        is_case=False,
        is_symlink=False,
        readable=True,
        has_subdirs=True,
    )


def _restat(entry: DirEntry, include_hidden: bool) -> DirEntry:
    """Re-read the facts about one already-listed directory."""
    siblings = list_subdirectories(entry.path.parent, include_hidden=include_hidden)
    for fresh in siblings:
        if fresh.path.name == entry.path.name:
            return fresh
    return entry
