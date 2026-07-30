# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QBrush, QColor

from foam.nodes import NON_KEY_EDITABLE, FoamNode
from foam.utils import (
    block_number,
    describe_block_entry,
    format_embedded_value,
    format_leaf_value,
    non_block_rows,
)
from foam.value_parse import set_node_value
from ui.theme import colors


class FoamTreeModel(QAbstractItemModel):
    HEADERS = ["Key", "Type", "Value"]

    COL_KEY   = 0
    COL_TYPE  = 1
    COL_VALUE = 2

    edit_rejected = Signal(str)
    # Emitted at the top of setData, before any mutation, so the owner can
    # checkpoint the pre-edit state for undo. Covers the paths that reach
    # setData without an explicit checkpoint call: the tree view's inline
    # delegate, Paste Value, and the detail-panel Apply handlers.
    about_to_change = Signal()

    @staticmethod
    def _diff_bg(status: str) -> QColor:
        """Row background for a diff *status*, resolved for the active theme."""
        c = colors()
        return QColor({
            "changed":     c.diff_changed,      # value differs
            "only_here":   c.diff_only_here,    # only in current file
            "only_in_ref": c.diff_only_in_ref,  # only in reference case
        }[status])

    def __init__(self, root: FoamNode, parent=None, read_only: bool = False):
        super().__init__(parent)
        self.root = root
        # An `#include` target outside the case dir is shown but never edited;
        # withholding ItemIsEditable disables inline edit and Paste Value alike.
        self.read_only = read_only
        self._diff: dict[FoamNode, tuple[str, FoamNode | None]] | None = None
        # Per-blocks-list rows that are not block_entry; see _block_number.
        self._non_block_rows: dict[FoamNode, list[int]] = {}
        # directive text -> note appended to its tooltip. Supplied by the app
        # after loading, so a tooltip never has to touch the disk itself.
        self._include_notes: dict[str, str] = {}
        self.attach_parents(self.root, None)

    def set_include_notes(self, notes: dict[str, str]) -> None:
        """Attach per-directive tooltip notes ("resolves to ..." / "not found")."""
        self._include_notes = dict(notes)

    def include_note(self, node: FoamNode) -> str | None:
        """Return the resolution note for a ``directive_entry`` row, if any."""
        if node.node_type != "directive_entry":
            return None
        return self._include_notes.get(str(node.value))

    def columnCount(self, parent=QModelIndex()):
        return 3

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid() and parent.column() > 0:
            return 0
        node = self._node_from_index(parent)
        return len(self._child_list(node))

    def index(self, row, column, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        parent_node = self._node_from_index(parent)
        children = self._child_list(parent_node)
        if row < 0 or row >= len(children):
            return QModelIndex()

        child = children[row]
        return self.createIndex(row, column, child)

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()

        node = index.internalPointer()
        if node is None:
            return QModelIndex()

        parent_node = getattr(node, "parent", None)
        if parent_node is None or parent_node == self.root:
            return QModelIndex()

        grand_parent = getattr(parent_node, "parent", None)
        siblings = self._child_list(grand_parent if grand_parent is not None else self.root)

        try:
            row = siblings.index(parent_node)
        except ValueError:
            row = 0

        return self.createIndex(row, 0, parent_node)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        node = index.internalPointer()

        if role in (Qt.DisplayRole, Qt.EditRole):
            return self._column_value(node, index.column(), index.row())

        if role == Qt.ToolTipRole:
            tip = self._tooltip(node, index.row())
            if self._diff:
                entry = self._diff.get(node)
                if entry is not None:
                    status, ref_node = entry
                    if status == "only_here":
                        tip += "\n(not in reference case)"
                    elif status == "only_in_ref":
                        tip += "\n(only in reference case)"
                    elif ref_node is not None:
                        tip += f"\nRef: {self._display_value(ref_node)}"
            return tip

        if role == Qt.ForegroundRole and node.node_type == "unknown_raw_entry":
            return QColor(colors().unknown_entry_fg)

        if role == Qt.BackgroundRole and self._diff:
            entry = self._diff.get(node)
            if entry:
                return QBrush(self._diff_bg(entry[0]))

        return None

    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole or not index.isValid():
            return False

        node = index.internalPointer()
        column = index.column()
        self.about_to_change.emit()

        if column == self.COL_KEY:
            if node.node_type in NON_KEY_EDITABLE:
                return False
            node.name = str(value)
            node.modified = True

        elif column == self.COL_VALUE:
            ok = set_node_value(node, value)
            if not ok:
                self.edit_rejected.emit(f'Invalid {node.node_type} value: "{value}"')
                return False

        else:
            return False

        row_start = self.index(index.row(), 0, index.parent())
        row_end = self.index(index.row(), self.COL_VALUE, index.parent())
        self.dataChanged.emit(row_start, row_end, [Qt.DisplayRole, Qt.EditRole])
        return True

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags

        node = index.internalPointer()
        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable

        if self.read_only:
            return flags

        if index.column() == self.COL_KEY and node.node_type not in NON_KEY_EDITABLE:
            flags |= Qt.ItemIsEditable

        if index.column() == self.COL_VALUE and self._is_value_editable(node):
            flags |= Qt.ItemIsEditable

        return flags

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEADERS[section]
        return None

    def _node_from_index(self, index: QModelIndex) -> FoamNode:
        if index.isValid():
            return index.internalPointer()
        return self.root

    def _child_list(self, node: FoamNode):
        if node is None:
            return []
        if node.node_type == "field_value_block":
            return node.value if isinstance(node.value, list) else []
        return node.children

    def insert_node(self, parent_node: FoamNode, position: int, new_node: FoamNode) -> QModelIndex:
        parent_index = self.index_of_node(parent_node)
        self.beginInsertRows(parent_index, position, position)
        new_node.parent = parent_node
        parent_node.children.insert(position, new_node)
        self._non_block_rows.clear()
        self.endInsertRows()
        return self.index(position, 0, parent_index)

    def remove_node(self, node: FoamNode) -> None:
        parent_node = node.parent if node.parent is not None else self.root
        siblings = parent_node.children
        try:
            row = siblings.index(node)
        except ValueError:
            return
        parent_index = self.index_of_node(parent_node)
        self.beginRemoveRows(parent_index, row, row)
        siblings.pop(row)
        node.parent = None
        self._non_block_rows.clear()
        self.endRemoveRows()

    def set_diff(
        self,
        diff: dict[FoamNode, tuple[str, FoamNode | None]],
        *,
        reverse: bool = False,
    ) -> None:
        if reverse:
            self._diff = {
                node: ("only_in_ref" if status == "only_here" else status, ref)
                for node, (status, ref) in diff.items()
            }
        else:
            self._diff = diff
        self._emit_datachanged_recursive(QModelIndex())

    def clear_diff(self) -> None:
        if self._diff is None:
            return
        self._diff = None
        self._emit_datachanged_recursive(QModelIndex())

    def _emit_datachanged_recursive(self, parent: QModelIndex) -> None:
        n = self.rowCount(parent)
        if n == 0:
            return
        self.dataChanged.emit(
            self.index(0, 0, parent),
            self.index(n - 1, self.COL_VALUE, parent),
            [Qt.ItemDataRole.BackgroundRole],
        )
        for row in range(n):
            self._emit_datachanged_recursive(self.index(row, 0, parent))

    def index_of_node(self, node: FoamNode) -> QModelIndex:
        if node is self.root or node is None:
            return QModelIndex()
        parent_node = node.parent if node.parent is not None else self.root
        siblings = self._child_list(parent_node)
        try:
            row = siblings.index(node)
        except ValueError:
            return QModelIndex()
        return self.createIndex(row, 0, node)

    def attach_parents(self, node: FoamNode, parent: FoamNode | None):
        node.parent = parent
        for child in self._child_list(node):
            if isinstance(child, FoamNode):
                self.attach_parents(child, node)

    def _column_value(self, node: FoamNode, column: int, row: int = 0):
        if column == self.COL_KEY:
            return self._display_key(node, row)
        if column == self.COL_TYPE:
            return node.node_type
        if column == self.COL_VALUE:
            return self._display_value(node)
        return None

    def _display_key(self, node: FoamNode, row: int = 0) -> str:
        if node.node_type == "field_value":
            return node.value.get("field_name", "")
        if node.node_type in {"directive_entry", "unknown_raw_entry"}:
            return ""
        if node.node_type == "block_entry":
            # Synthesised from the row, not stored on the node, so it stays
            # correct after any insert/delete and matches the 3-D viewer's
            # per-block centroid labels by construction. Must NOT be computed
            # via parent.children.index(node): the filter proxy reads every
            # row's key column on each keystroke, which would make that O(N^2).
            return f"block {self._block_number(node, row)}"
        return node.name

    def _block_number(self, node: FoamNode, row: int) -> int:
        """foam.utils.block_number for *node*, memoising the per-list scan.

        The key column is read for every row on each filter keystroke, so the
        non-block rows of each blocks list are cached (identity-keyed; FoamNode
        sets ``__hash__ = object.__hash__``) rather than rescanned per row. The
        whole cache is dropped on any structural change.
        """
        parent = node.parent
        if parent is None:
            return row
        skipped = self._non_block_rows.get(parent)
        if skipped is None:
            skipped = non_block_rows(parent)
            self._non_block_rows[parent] = skipped
        return block_number(parent, row, skipped)

    def _display_value(self, node: FoamNode) -> str:
        t = node.node_type

        if t == "dictionary":
            return f"{len(node.children)} entries"

        if t == "region_block":
            return f"{len(node.children)} regions"

        if t in {"region_entry", "named_dict_entry"}:
            return f"{len(node.children)} entries"

        if t == "named_dict_list":
            return f"{len(node.children)} entries"

        if t == "block_list":
            return f"{len(node.children)} blocks"

        if t == "field_value_block":
            count = len(node.value) if isinstance(node.value, list) else 0
            return f"{count} field values"

        if t == "field_value":
            data = node.value
            return (
                f"{data.get('field_type', '')} "
                f"{format_embedded_value(data.get('value_type'), data.get('value'), data.get('raw_value'))}"
            ).strip()

        if t == "nonuniform_list":
            parts = str(node.value).split(None, 3)
            list_type = parts[1] if len(parts) > 1 else "List"
            count_str = parts[2] if len(parts) > 2 and parts[2] != "(" else "?"
            return f"nonuniform {list_type} ({count_str} values)"

        return format_leaf_value(t, node.value)

    def _tooltip(self, node: FoamNode, row: int = 0) -> str:
        if node.node_type == "field_value":
            data = node.value
            value_str = format_embedded_value(
                data.get("value_type"), data.get("value"), data.get("raw_value")
            )
            return (
                f"type: {data.get('field_type', '')}\n"
                f"field: {data.get('field_name', '')}\n"
                f"value: {value_str}"
            )

        if node.node_type == "directive_entry":
            note = self.include_note(node)
            return f"directive\n{node.value}" + (f"\n{note}" if note else "")

        if node.node_type == "unknown_raw_entry":
            return f"unknown raw entry\n{node.value}"

        if node.node_type == "block_entry":
            name, vertices, zone, cells, grading = describe_block_entry(str(node.value))
            header = f"block {self._block_number(node, row)}" + (f" ({name})" if name else "")
            return (
                f"{header}\n"
                f"vertices: {vertices or '—'}\n"
                f"cells: {cells or '—'}\n"
                f"grading: {grading or '—'}\n"
                f"zone: {zone or '—'}"
            )

        return f"{node.name}\n{node.node_type}"

    def _is_value_editable(self, node: FoamNode) -> bool:
        return node.node_type in {
            "bool",
            "word",
            "string",
            "int",
            "scalar",
            "vector",
            "box_pair",
            "int_list",
            "scalar_list",
            "raw_list",
            "compound",
            "macro",
            "field_value",
            "directive_entry",
            "unknown_raw_entry",
            "block_entry",
        }

