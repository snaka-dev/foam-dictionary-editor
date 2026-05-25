# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut, QTextCursor, QTextDocument
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
_SPACING_SMALL = 6


class EditorPanel(QWidget):
    user_text_changed = Signal()
    find_in_tree_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_search_text = ""
        self._updating_programmatically = False

        self._editor = CodeEditor()
        self._editor.setReadOnly(False)
        self._editor.textChanged.connect(self._on_text_changed)
        self._editor.cursorPositionChanged.connect(self._update_cursor_status)

        self._cursor_label = QLabel("Line: 1")

        for key, slot in [
            ("Ctrl+F",   self._find),
            ("F3",       self._find_next),
            ("Shift+F3", self._find_prev),
        ]:
            sc = QShortcut(QKeySequence(key), self)
            sc.setContext(Qt.WidgetWithChildrenShortcut)
            sc.activated.connect(slot)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_separator())
        layout.addSpacing(_SPACING_SMALL)
        layout.addLayout(self._build_toolbar())
        layout.addWidget(self._editor)

    def set_text(self, text: str) -> None:
        self._updating_programmatically = True
        self._editor.setPlainText(text)
        self._updating_programmatically = False
        self._update_cursor_status()

    def get_text(self) -> str:
        return self._editor.toPlainText()

    def current_line_number(self) -> int:
        return self._editor.current_line_number()

    def jump_to_node(self, source_line: int, source_end_line: int, scroll: bool = True) -> None:
        self._editor.set_span_highlight(source_line, source_end_line)
        if scroll:
            self._editor.goto_line(source_line)

    def clear_node_highlight(self) -> None:
        self._editor.clear_span_highlight()

    def jump_to_text(self, text: str, scroll: bool = True) -> bool:
        """Search for text from the top of the document and highlight its line.

        Uses whole-word matching. Returns True if found.
        """
        cursor = self._editor.document().find(
            text, 0, QTextDocument.FindFlag.FindWholeWords
        )
        if cursor.isNull():
            return False
        line = cursor.blockNumber() + 1
        self._editor.set_span_highlight(line, line)
        if scroll:
            self._editor.goto_line(line)
        return True

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
        def btn(label: str, slot, tip: str = "") -> QToolButton:
            b = QToolButton()
            b.setText(label)
            b.clicked.connect(slot)
            if tip:
                b.setToolTip(tip)
            return b

        toolbar = QHBoxLayout()
        toolbar.addWidget(btn("Find",      self._find,      "Find text (Ctrl+F)"))
        toolbar.addWidget(btn("Find Prev", self._find_prev, "Find previous occurrence (Shift+F3)"))
        toolbar.addWidget(btn("Find Next", self._find_next, "Find next occurrence (F3)"))
        toolbar.addSpacing(_SPACING_LARGE)
        toolbar.addWidget(btn(
            "Find in Tree", self.find_in_tree_requested.emit,
            "Select the tree entry for the current cursor line (Ctrl+Shift+T)",
        ))
        toolbar.addStretch(1)
        toolbar.addWidget(self._cursor_label)
        return toolbar

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
        self._do_find(backward=False)

    def _find_next(self) -> None:
        if not self._last_search_text:
            self._find()
            return
        self._do_find(backward=False)

    def _find_prev(self) -> None:
        if not self._last_search_text:
            self._find()
            return
        self._do_find(backward=True)

    def _do_find(self, backward: bool) -> None:
        flag = QTextDocument.FindFlag.FindBackward if backward else QTextDocument.FindFlags()
        wrap_anchor = QTextCursor.MoveOperation.End if backward else QTextCursor.MoveOperation.Start

        found = self._editor.find(self._last_search_text, flag)
        if not found:
            cursor = self._editor.textCursor()
            cursor.movePosition(wrap_anchor)
            self._editor.setTextCursor(cursor)
            found = self._editor.find(self._last_search_text, flag)
        if not found:
            QMessageBox.information(self, "Find", f"Text not found: {self._last_search_text}")
