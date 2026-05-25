# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations
from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QBrush, QColor
from foam.utils import classify_simple_value, format_embedded_value, format_scalar, is_int, is_number, parse_box_pair
from foam.nodes import BOOL_WORDS, FoamNode, NON_KEY_EDITABLE, STRING_TYPES


class FoamTreeModel(QAbstractItemModel):
    HEADERS = ["Key", "Type", "Value"]

    COL_KEY   = 0
    COL_TYPE  = 1
    COL_VALUE = 2

    edit_rejected = Signal(str)

    _DIFF_BG: dict[str, QColor] = {
        "changed":   QColor("#FFFACD"),  # light yellow
        "only_here": QColor("#E3F2FD"),  # light blue
    }

    def __init__(self, root: FoamNode, parent=None):
        super().__init__(parent)
        self.root = root
        self._diff: "dict[FoamNode, tuple[str, FoamNode | None]] | None" = None
        self._attach_parents(self.root, None)

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
            return self._column_value(node, index.column())

        if role == Qt.ToolTipRole:
            tip = self._tooltip(node)
            if self._diff:
                entry = self._diff.get(node)
                if entry is not None:
                    status, ref_node = entry
                    if status == "only_here":
                        tip += "\n(not in reference case)"
                    elif ref_node is not None:
                        tip += f"\nRef: {self._display_value(ref_node)}"
            return tip

        if role == Qt.ForegroundRole and node.node_type == "unknown_raw_entry":
            return QColor("#B8860B")

        if role == Qt.BackgroundRole and self._diff:
            entry = self._diff.get(node)
            if entry:
                return QBrush(self._DIFF_BG[entry[0]])

        return None

    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole or not index.isValid():
            return False

        node = index.internalPointer()
        column = index.column()

        if column == self.COL_KEY:
            if node.node_type in NON_KEY_EDITABLE:
                return False
            node.name = str(value)
            node.modified = True

        elif column == self.COL_VALUE:
            ok = self._set_node_value(node, value)
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
        parent_index = self._index_of_node(parent_node)
        self.beginInsertRows(parent_index, position, position)
        new_node.parent = parent_node
        parent_node.children.insert(position, new_node)
        self.endInsertRows()
        return self.index(position, 0, parent_index)

    def remove_node(self, node: FoamNode) -> None:
        parent_node = node.parent if node.parent is not None else self.root
        siblings = parent_node.children
        try:
            row = siblings.index(node)
        except ValueError:
            return
        parent_index = self._index_of_node(parent_node)
        self.beginRemoveRows(parent_index, row, row)
        siblings.pop(row)
        node.parent = None
        self.endRemoveRows()

    def set_diff(self, diff: "dict[FoamNode, tuple[str, FoamNode | None]]") -> None:
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
            [Qt.BackgroundRole],
        )
        for row in range(n):
            self._emit_datachanged_recursive(self.index(row, 0, parent))

    def _index_of_node(self, node: FoamNode) -> QModelIndex:
        if node is self.root or node is None:
            return QModelIndex()
        parent_node = node.parent if node.parent is not None else self.root
        siblings = self._child_list(parent_node)
        try:
            row = siblings.index(node)
        except ValueError:
            return QModelIndex()
        return self.createIndex(row, 0, node)

    def _attach_parents(self, node: FoamNode, parent: FoamNode | None):
        node.parent = parent
        for child in self._child_list(node):
            if isinstance(child, FoamNode):
                self._attach_parents(child, node)

    def _column_value(self, node: FoamNode, column: int):
        if column == self.COL_KEY:
            return self._display_key(node)
        if column == self.COL_TYPE:
            return node.node_type
        if column == self.COL_VALUE:
            return self._display_value(node)
        return None

    def _display_key(self, node: FoamNode) -> str:
        if node.node_type == "field_value":
            return node.value.get("field_name", "")
        if node.node_type in {"directive_entry", "unknown_raw_entry"}:
            return ""
        return node.name

    def _display_value(self, node: FoamNode) -> str:
        t = node.node_type

        if t == "dictionary":
            return f"{len(node.children)} entries"

        if t == "region_block":
            return f"{len(node.children)} regions"

        if t == "region_entry":
            return f"{len(node.children)} entries"

        if t == "field_value_block":
            count = len(node.value) if isinstance(node.value, list) else 0
            return f"{count} field values"

        if t == "field_value":
            data = node.value
            return (
                f"{data.get('field_type', '')} "
                f"{format_embedded_value(data.get('value_type'), data.get('value'), data.get('raw_value'))}"
            ).strip()

        if t == "bool":
            return str(node.value)

        if t == "nonuniform_list":
            parts = str(node.value).split(None, 3)
            list_type = parts[1] if len(parts) > 1 else "List"
            count = parts[2] if len(parts) > 2 and parts[2] != "(" else "?"
            return f"nonuniform {list_type} ({count} values)"

        if t in {"directive_entry", "unknown_raw_entry", "macro_entry"}:
            return str(node.value)

        if t == "box_pair":
            p1, p2 = node.value
            left = "(" + " ".join(format_scalar(x) for x in p1) + ")"
            right = "(" + " ".join(format_scalar(x) for x in p2) + ")"
            return f"{left} {right}"

        if t in {"vector", "scalar_list"}:
            return "(" + " ".join(format_scalar(x) for x in node.value) + ")"

        if t in {"int_list", "list"}:
            return "(" + " ".join(str(x) for x in node.value) + ")"

        if t == "raw_list":
            return "(" + str(node.value) + ")"

        if t in STRING_TYPES:
            return str(node.value)

        if t in {"int", "scalar"}:
            return format_scalar(node.value)

        return "" if node.value is None else str(node.value)

    def _tooltip(self, node: FoamNode) -> str:
        if node.node_type == "field_value":
            data = node.value
            return (
                f"type: {data.get('field_type', '')}\n"
                f"field: {data.get('field_name', '')}\n"
                f"value: {format_embedded_value(data.get('value_type'), data.get('value'), data.get('raw_value'))}"
            )

        if node.node_type == "directive_entry":
            return f"directive\n{node.value}"

        if node.node_type == "unknown_raw_entry":
            return f"unknown raw entry\n{node.value}"

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
        }

    def _set_node_value(self, node: FoamNode, value) -> bool:
        text = str(value).strip()

        if node.node_type == "field_value":
            value_type, parsed = classify_simple_value(text)
            node.value["value_type"] = value_type
            node.value["value"] = parsed
            node.value["raw_value"] = text
            node.modified = True
            return True

        if node.node_type in {"directive_entry", "unknown_raw_entry"}:
            node.value = text
            node.modified = True
            return True

        value_type, parsed = self._parse_text_for_node_type(node.node_type, text)
        if value_type is None:
            return False

        node.node_type = value_type
        node.value = parsed
        node.modified = True
        return True

    def _parse_text_for_node_type(self, node_type: str, text: str):
        if node_type == "int":
            try:
                return "int", int(text)
            except ValueError:
                if is_number(text):
                    return "scalar", float(text)
                return None, None

        if node_type == "scalar":
            try:
                return "scalar", float(text)
            except ValueError:
                return None, None

        if node_type == "vector":
            nums = self._parse_parenthesized_numbers(text)
            if nums is None or len(nums) != 3:
                return None, None
            return "vector", nums

        if node_type == "box_pair":
            parsed = parse_box_pair(text)
            if parsed is None:
                return None, None
            return "box_pair", parsed

        if node_type == "int_list":
            nums = self._parse_parenthesized_numbers(text, force_int=True)
            if nums is None:
                return None, None
            return "int_list", nums

        if node_type == "scalar_list":
            nums = self._parse_parenthesized_numbers(text)
            if nums is None:
                return None, None
            return "scalar_list", nums

        if node_type == "raw_list":
            if text.startswith("(") and text.endswith(")"):
                return "raw_list", text[1:-1].strip()
            return "raw_list", text

        if node_type == "bool":
            if text.lower() not in BOOL_WORDS:
                return None, None
            return "bool", text.lower()

        if node_type in STRING_TYPES:
            return node_type, text

        return None, None

    def _parse_parenthesized_numbers(self, text: str, force_int: bool = False):
        text = text.strip()
        if not (text.startswith("(") and text.endswith(")")):
            return None

        body = text[1:-1].strip()
        if not body:
            return []

        parts = body.split()

        if force_int:
            if not all(is_int(x) for x in parts):
                return None
            return [int(x) for x in parts]

        if not all(is_number(x) for x in parts):
            return None

        return [float(x) for x in parts]
