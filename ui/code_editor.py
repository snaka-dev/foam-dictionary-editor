# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QTextFormat, QTextCursor
from PySide6.QtWidgets import QWidget, QPlainTextEdit, QTextEdit


_COLOR_SPAN_HIGHLIGHT    = QColor(255, 251, 190)  # amber — node source span
_COLOR_CURRENT_LINE      = QColor(232, 242, 254)  # blue  — cursor line


class LineNumberArea(QWidget):
    def __init__(self, editor: "CodeEditor"):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.code_editor.line_number_area_paint_event(event)


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._span_start_line = 0
        self._span_end_line = 0

        self.line_number_area = LineNumberArea(self)

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)

        self.update_line_number_area_width(0)
        self.highlight_current_line()

        font = self.font()
        font.setFamilies(["Consolas", "Menlo", "Monaco", "DejaVu Sans Mono", "monospace"])
        font.setPointSize(10)
        self.setFont(font)

        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)

    def line_number_area_width(self) -> int:
        digits = len(str(max(1, self.blockCount())))
        space = 12 + self.fontMetrics().horizontalAdvance("9") * digits
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor(245, 245, 245))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        painter.setPen(QColor(120, 120, 120))

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.drawText(
                    0,
                    top,
                    self.line_number_area.width() - 4,
                    self.fontMetrics().height(),
                    Qt.AlignRight,
                    number,
                )

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def set_span_highlight(self, start_line: int, end_line: int) -> None:
        self._span_start_line = start_line
        self._span_end_line = max(end_line, start_line)
        self.highlight_current_line()

    def clear_span_highlight(self) -> None:
        self._span_start_line = 0
        self._span_end_line = 0
        self.highlight_current_line()

    def highlight_current_line(self):
        extra_selections = []

        if self._span_start_line > 0:
            start_block = self.document().findBlockByLineNumber(self._span_start_line - 1)
            end_block = self.document().findBlockByLineNumber(self._span_end_line - 1)
            if not end_block.isValid():
                end_block = self.document().lastBlock()
            if start_block.isValid():
                sel = QTextEdit.ExtraSelection()
                sel.format.setBackground(_COLOR_SPAN_HIGHLIGHT)
                sel.format.setProperty(QTextFormat.FullWidthSelection, True)
                cur = QTextCursor(start_block)
                cur.setPosition(end_block.position() + max(end_block.length() - 1, 0), QTextCursor.KeepAnchor)
                sel.cursor = cur
                extra_selections.append(sel)

        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(_COLOR_CURRENT_LINE)
        selection.format.setProperty(QTextFormat.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        extra_selections.append(selection)

        self.setExtraSelections(extra_selections)

    def current_line_number(self) -> int:
        return self.textCursor().blockNumber() + 1

    def goto_line(self, line_number: int):
        if line_number < 1:
            line_number = 1

        block = self.document().findBlockByLineNumber(line_number - 1)
        if not block.isValid():
            return

        cursor = QTextCursor(block)
        self.setTextCursor(cursor)
        self.centerCursor()
