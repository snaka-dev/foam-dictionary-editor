# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ui.code_editor import CodeEditor

_SPACING_LARGE = 16
_SPACING_MEDIUM = 8
_SPACING_SMALL = 6


class EditorPanel(QWidget):
    user_text_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_search_text = ""
        self._updating_programmatically = False

        self._editor = CodeEditor()
        self._editor.setReadOnly(False)
        self._editor.textChanged.connect(self._on_text_changed)
        self._editor.cursorPositionChanged.connect(self._update_cursor_status)

        self._cursor_label = QLabel("Line: 1")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_separator())
        layout.addSpacing(_SPACING_SMALL)
        layout.addLayout(self._build_toolbar())
        layout.addLayout(self._build_status_bar())
        layout.addWidget(self._editor)

    def set_text(self, text: str) -> None:
        self._updating_programmatically = True
        self._editor.setPlainText(text)
        self._updating_programmatically = False
        self._update_cursor_status()

    def get_text(self) -> str:
        return self._editor.toPlainText()

    # ── private ───────────────────────────────────────────────────────────────

    def _build_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        sep.setLineWidth(1)
        sep.setStyleSheet("""
            QFrame {
                color: #b8b8b8;
                background-color: #b8b8b8;
                min-height: 1px;
                max-height: 1px;
            }
        """)
        return sep

    def _build_toolbar(self) -> QHBoxLayout:
        def btn(label: str, slot) -> QToolButton:
            b = QToolButton()
            b.setText(label)
            b.clicked.connect(slot)
            return b

        toolbar = QHBoxLayout()
        toolbar.addWidget(btn("Undo", self._editor.undo))
        toolbar.addWidget(btn("Redo", self._editor.redo))
        toolbar.addSpacing(_SPACING_MEDIUM)
        toolbar.addWidget(btn("Cut", self._editor.cut))
        toolbar.addWidget(btn("Copy", self._editor.copy))
        toolbar.addWidget(btn("Paste", self._editor.paste))
        toolbar.addSpacing(_SPACING_MEDIUM)
        toolbar.addWidget(btn("Select All", self._editor.selectAll))
        toolbar.addSpacing(_SPACING_LARGE)
        toolbar.addWidget(btn("Find", self._find))
        toolbar.addWidget(btn("Find Next", self._find_next))
        toolbar.addStretch(1)
        return toolbar

    def _build_status_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.addStretch(1)
        bar.addWidget(self._cursor_label)
        return bar

    def _on_text_changed(self) -> None:
        if not self._updating_programmatically:
            self.user_text_changed.emit()

    def _update_cursor_status(self) -> None:
        self._cursor_label.setText(f"Line: {self._editor.current_line_number()}")

    def _find(self) -> None:
        initial = self._editor.textCursor().selectedText() or self._last_search_text
        text, ok = QInputDialog.getText(self, "Find", "Text to find:", QLineEdit.Normal, initial)
        if not ok or not text:
            return

        self._last_search_text = text
        found = self._editor.find(text)
        if not found:
            cursor = self._editor.textCursor()
            cursor.movePosition(cursor.Start)
            self._editor.setTextCursor(cursor)
            found = self._editor.find(text)
        if not found:
            QMessageBox.information(self, "Find", f"Text not found: {text}")

    def _find_next(self) -> None:
        if not self._last_search_text:
            self._find()
            return

        found = self._editor.find(self._last_search_text)
        if not found:
            cursor = self._editor.textCursor()
            cursor.movePosition(cursor.Start)
            self._editor.setTextCursor(cursor)
            found = self._editor.find(self._last_search_text)
        if not found:
            QMessageBox.information(self, "Find", f"Text not found: {self._last_search_text}")
