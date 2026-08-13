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

from foam.boundary_patch import get_patch_type, patch_inner_text, value_complexity
from foam.nodes import FoamNode
from i18n import tr


class BoundaryEditDialog(QDialog):
    def __init__(
        self,
        field_name: str,
        patch_name: str,
        patch_node: FoamNode,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._is_complex = value_complexity(patch_node) != ""
        self.setWindowTitle(tr("Edit boundary: {field} / {patch}").format(field=field_name, patch=patch_name))

        layout = QVBoxLayout(self)

        # Read-only info header
        info = QFormLayout()
        info.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
        for label_text, value in ((tr("Variable:"), field_name), (tr("Patch:"), patch_name)):
            key = QLabel(label_text)
            key.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            val = QLabel(f"<b>{value}</b>")
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            info.addRow(key, val)
        layout.addLayout(info)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep)

        if not self._is_complex:
            # Normal mode: edit the full patch content directly.
            # The type line is part of the content — no separate Type field needed.
            layout.addWidget(QLabel(tr("Content:")))
            self._content_edit = QPlainTextEdit(patch_inner_text(patch_node))
            font = QFont("Monospace")
            font.setStyleHint(QFont.StyleHint.TypeWriter)
            self._content_edit.setFont(font)
            self._content_edit.setMinimumHeight(160)
            layout.addWidget(self._content_edit)
            self.resize(520, 320)
        else:
            # Complex mode: only the type is editable here.
            type_row = QHBoxLayout()
            type_row.addWidget(QLabel(tr("Type:")))
            self._type_edit = QLineEdit(get_patch_type(patch_node))
            type_row.addWidget(self._type_edit)
            layout.addLayout(type_row)

            warn = QLabel(
                tr(
                    "⚠ This patch contains large or binary data.\n"
                    "The full value cannot be displayed here.\n"
                    "Use the Text Editor tab to edit the complete content."
                )
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
