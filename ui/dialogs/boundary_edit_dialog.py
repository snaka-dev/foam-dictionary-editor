# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from foam.nodes import FoamNode
from i18n import tr

# Thresholds for deciding whether a patch value is too large/complex
# to display in the edit dialog — edit in Text Editor instead.
_COMPLEX_VALUE_CHAR_LIMIT = 500
_COMPLEX_VALUE_LINE_LIMIT = 12


def _value_complexity(patch_node: FoamNode) -> str:
    """Return 'binary', 'large', or '' (not complex).

    'binary' takes priority: non-printable bytes are detected before size checks.
    """
    for child in patch_node.children:
        if child.node_type == "field_value_block":
            return "large"
        raw = child.raw_text or ""
        if any(c < "\x09" for c in raw[:_COMPLEX_VALUE_CHAR_LIMIT]):
            return "binary"
        if len(raw) > _COMPLEX_VALUE_CHAR_LIMIT or raw.count("\n") > _COMPLEX_VALUE_LINE_LIMIT:
            return "large"
    return ""


def _value_is_complex(patch_node: FoamNode) -> bool:
    return _value_complexity(patch_node) != ""


def _get_patch_type(patch_node: FoamNode) -> str:
    for child in patch_node.children:
        if child.name == "type":
            return str(child.value) if child.value is not None else ""
    return ""


def _patch_inner_text(patch_node: FoamNode) -> str:
    """Return the content inside the patch dict braces, preserving indentation."""
    rt = patch_node.raw_text.strip() if patch_node.raw_text else ""
    if rt:
        start = rt.find("{")
        end = rt.rfind("}")
        if start != -1 and end > start:
            return rt[start + 1 : end].strip("\n")
    # Fallback: serialise children via write_root on a temporary root
    from foam.writer import write_root

    temp = FoamNode(name="_tmp", node_type="dictionary")
    temp.children = list(patch_node.children)
    return write_root(temp).strip()


def _parse_patch_content(text: str) -> list[FoamNode]:
    """Parse inner patch text and return the list of child FoamNodes."""
    from foam.parser import OpenFoamParser

    wrapped = f"_patch\n{{\n{text}\n}}\n"
    root = OpenFoamParser(wrapped).parse()
    for child in root.children:
        if child.name == "_patch" and child.node_type == "dictionary":
            result = list(child.children)
            for c in result:
                c.parent = None  # caller sets parent
            return result
    return []


class BoundaryEditDialog(QDialog):
    def __init__(
        self,
        field_name: str,
        patch_name: str,
        patch_node: FoamNode,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._is_complex = _value_complexity(patch_node) != ""
        self.setWindowTitle(tr("Edit boundary: {field} / {patch}").format(field=field_name, patch=patch_name))

        layout = QVBoxLayout(self)

        # Read-only info header
        info = QFormLayout()
        info.setRowWrapPolicy(QFormLayout.DontWrapRows)
        for label_text, value in ((tr("Variable:"), field_name), (tr("Patch:"), patch_name)):
            key = QLabel(label_text)
            key.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            val = QLabel(f"<b>{value}</b>")
            val.setTextInteractionFlags(Qt.TextSelectableByMouse)
            info.addRow(key, val)
        layout.addLayout(info)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep)

        if not self._is_complex:
            # Normal mode: edit the full patch content directly.
            # The type line is part of the content — no separate Type field needed.
            layout.addWidget(QLabel(tr("Content:")))
            self._content_edit = QPlainTextEdit(_patch_inner_text(patch_node))
            font = QFont("Monospace")
            font.setStyleHint(QFont.TypeWriter)
            self._content_edit.setFont(font)
            self._content_edit.setMinimumHeight(160)
            layout.addWidget(self._content_edit)
            self.resize(520, 320)
        else:
            # Complex mode: only the type is editable here.
            type_row = QHBoxLayout()
            type_row.addWidget(QLabel(tr("Type:")))
            self._type_edit = QLineEdit(_get_patch_type(patch_node))
            type_row.addWidget(self._type_edit)
            layout.addLayout(type_row)

            warn = QLabel(
                tr("⚠ This patch contains large or binary data.\nThe full value cannot be displayed here.\nUse the Text Editor tab to edit the complete content.")
            )
            warn.setWordWrap(True)
            layout.addWidget(warn)
            self.resize(420, 180)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton(tr("OK"))
        cancel_btn = QPushButton(tr("Cancel"))
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

    @property
    def is_complex_mode(self) -> bool:
        return self._is_complex

    @property
    def new_type(self) -> str:
        """The edited type value. Only meaningful in complex mode."""
        if self._is_complex:
            return self._type_edit.text().strip()
        return ""

    @property
    def new_dict_text(self) -> str:
        """The edited full patch content. Only meaningful in normal mode."""
        if not self._is_complex:
            return self._content_edit.toPlainText()
        return ""
