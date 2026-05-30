# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from PySide6.QtCore import QSortFilterProxyModel, Qt, Signal
from PySide6.QtWidgets import QLabel, QMenu, QTreeView, QVBoxLayout, QWidget

from foam.nodes import FoamNode
from model.tree_model import FoamTreeModel

_EXPAND_DEPTH = 2


class ComparisonTreePanel(QWidget):
    """Read-only tree view showing a reference case's version of the current file.

    Right-clicking a leaf node offers "Use this value" which emits
    ``use_value_requested`` so ``MainWindow`` can apply the value to the
    current case's tree.
    """

    use_value_requested = Signal(FoamNode)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model: FoamTreeModel | None = None
        self._type_col_visible = False  # tracks main tree's type column state

        self._proxy = QSortFilterProxyModel(self)
        self._proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self._proxy.setRecursiveFilteringEnabled(True)
        self._proxy.setFilterKeyColumn(FoamTreeModel.COL_KEY)

        self._header_label = QLabel("Reference case")
        self._header_label.setStyleSheet(
            "QLabel { background-color: #E8F5E9; padding: 2px 6px;"
            " border-bottom: 1px solid #A5D6A7; font-weight: bold; }"
        )

        self._tree = QTreeView()
        self._tree.setModel(self._proxy)
        self._tree.setAlternatingRowColors(True)
        self._tree.setUniformRowHeights(True)
        self._tree.setEditTriggers(QTreeView.NoEditTriggers)
        self._tree.setSelectionBehavior(QTreeView.SelectRows)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._on_context_menu)
        self._tree.setColumnHidden(FoamTreeModel.COL_TYPE, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._header_label)
        layout.addWidget(self._tree)

    def load(
        self,
        root: FoamNode,
        rev_diff_map: dict,
        case_name: str,
    ) -> None:
        self._model = FoamTreeModel(root)
        self._model.set_diff(rev_diff_map, reverse=True)
        self._proxy.setSourceModel(self._model)
        # setSourceModel triggers modelReset which may reset column visibility.
        self._tree.setColumnHidden(FoamTreeModel.COL_TYPE, not self._type_col_visible)
        self._header_label.setText(f"Reference: {case_name}")
        self._tree.expandToDepth(_EXPAND_DEPTH)
        self._collapse_foam_file()
        self._resize_columns()

    def clear(self) -> None:
        self._proxy.setSourceModel(None)
        self._model = None
        self._header_label.setText("Reference case")

    def set_type_column_visible(self, visible: bool) -> None:
        self._type_col_visible = visible
        self._tree.setColumnHidden(FoamTreeModel.COL_TYPE, not visible)
        if visible and self._model is not None:
            self._tree.resizeColumnToContents(FoamTreeModel.COL_TYPE)

    def _collapse_foam_file(self) -> None:
        if self._model is None:
            return
        for row in range(self._model.rowCount()):
            src_index = self._model.index(row, 0)
            node = src_index.internalPointer()
            if node is not None and node.name == "FoamFile":
                self._tree.setExpanded(self._proxy.mapFromSource(src_index), False)
                break

    def _on_context_menu(self, pos) -> None:
        if self._model is None:
            return
        index = self._tree.indexAt(pos)
        if not index.isValid():
            return
        src_index = self._proxy.mapToSource(index)
        node: FoamNode = src_index.internalPointer()
        if node is None:
            return

        can_use = self._model._is_value_editable(node)

        menu = QMenu(self)
        use_action = menu.addAction("Use this value")
        use_action.setEnabled(can_use)

        action = menu.exec(self._tree.viewport().mapToGlobal(pos))
        if action == use_action and can_use:
            self.use_value_requested.emit(node)

    def _resize_columns(self) -> None:
        if self._model is None:
            return
        for col in range(3):
            if not self._tree.isColumnHidden(col):
                self._tree.resizeColumnToContents(col)
