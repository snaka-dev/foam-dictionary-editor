# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QTextCursor, QTextFormat
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget

from ui.widgets._foam_highlighter import FoamHighlighter


_COLOR_SPAN_HIGHLIGHT    = QColor(255, 251, 190)  # amber — node source span
_COLOR_CURRENT_LINE      = QColor(232, 242, 254)  # blue  — cursor line

_FOLD_GUTTER_W = 14  # pixel width of the clickable fold-triangle column


class LineNumberArea(QWidget):
    def __init__(self, editor: "CodeEditor"):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.code_editor.line_number_area_paint_event(event)

    def mousePressEvent(self, event):
        editor = self.code_editor
        # Only act on clicks inside the fold gutter (rightmost column)
        if event.x() < self.width() - _FOLD_GUTTER_W:
            super().mousePressEvent(event)
            return
        y = event.y()
        block = editor.firstVisibleBlock()
        top = int(
            editor.blockBoundingGeometry(block)
            .translated(editor.contentOffset())
            .top()
        )
        while block.isValid():
            if not block.isVisible():
                block = block.next()
                continue
            h = int(editor.blockBoundingRect(block).height())
            if top <= y < top + h:
                ln = block.blockNumber()
                if ln in editor._fold_map:
                    editor._toggle_fold(ln)
                break
            top += h
            block = block.next()


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._span_start_line = 0
        self._span_end_line = 0
        self._fold_map: dict[int, int] = {}   # open_line → close_line
        self._folded: set[int] = set()         # set of currently-folded open lines
        self._comment_folds: dict[int, int] = {}   # comment-run start line → end line

        self._highlighter = FoamHighlighter(self.document())

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

    # ── public API ────────────────────────────────────────────────────────────

    def reload_highlighting(self) -> None:
        """Reload keyword list from disk and rehighlight the document."""
        self._highlighter.reload_keywords()

    def set_highlighting_enabled(self, enabled: bool) -> None:
        self._highlighter.set_enabled(enabled)

    def set_shell_mode(self, enabled: bool) -> None:
        """Switch the highlighter between shell-script and OpenFOAM rules."""
        self._highlighter.set_mode("shell" if enabled else "foam")

    def setPlainText(self, text: str) -> None:
        self._fold_map = {}
        self._folded = set()
        self._comment_folds = {}
        super().setPlainText(text)
        self._fold_map = self._compute_fold_map()
        self._comment_folds = self._compute_comment_folds()
        # Comment-run starts never coincide with brace-open lines, so merging is safe.
        self._fold_map.update(self._comment_folds)
        self._auto_fold_foamfile()
        self._auto_fold_header_comment()

    # ── line number / fold gutter ─────────────────────────────────────────────

    def line_number_area_width(self) -> int:
        digits = len(str(max(1, self.blockCount())))
        space = 12 + self.fontMetrics().horizontalAdvance("9") * digits + _FOLD_GUTTER_W
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(
                0, rect.y(), self.line_number_area.width(), rect.height()
            )
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

        fold_x = self.line_number_area.width() - _FOLD_GUTTER_W
        # Separator between line numbers and fold gutter
        painter.setPen(QColor(210, 210, 210))
        painter.drawLine(fold_x, event.rect().top(), fold_x, event.rect().bottom())

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(
            self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        )
        bottom = top + int(self.blockBoundingRect(block).height())
        line_h = self.fontMetrics().height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                # Line number
                painter.setPen(QColor(120, 120, 120))
                painter.drawText(
                    0, top, fold_x - 4, line_h,
                    Qt.AlignRight, str(block_number + 1),
                )

                # Fold triangle
                if block_number in self._fold_map:
                    cy = top + line_h // 2
                    cx = fold_x + _FOLD_GUTTER_W // 2
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QColor(90, 90, 90))
                    if block_number in self._folded:
                        # ▶ right-pointing (collapsed)
                        pts = [
                            QPoint(cx - 3, cy - 4),
                            QPoint(cx - 3, cy + 4),
                            QPoint(cx + 3, cy),
                        ]
                    else:
                        # ▾ down-pointing (expanded)
                        pts = [
                            QPoint(cx - 4, cy - 2),
                            QPoint(cx + 4, cy - 2),
                            QPoint(cx,     cy + 3),
                        ]
                    painter.drawPolygon(pts)

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    # ── span / line highlight ─────────────────────────────────────────────────

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
            # source_line is 1-based block number; findBlockByNumber is fold-safe
            start_block = self.document().findBlockByNumber(self._span_start_line - 1)
            end_block = self.document().findBlockByNumber(self._span_end_line - 1)
            if not end_block.isValid():
                end_block = self.document().lastBlock()
            if start_block.isValid():
                sel = QTextEdit.ExtraSelection()
                sel.format.setBackground(_COLOR_SPAN_HIGHLIGHT)
                sel.format.setProperty(QTextFormat.FullWidthSelection, True)
                cur = QTextCursor(start_block)
                cur.setPosition(
                    end_block.position() + max(end_block.length() - 1, 0),
                    QTextCursor.KeepAnchor,
                )
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

    def goto_line(self, line_number: int) -> None:
        if line_number < 1:
            line_number = 1
        # findBlockByNumber is fold-safe (source_line is 1-based block number)
        block = self.document().findBlockByNumber(line_number - 1)
        if not block.isValid():
            return
        cursor = QTextCursor(block)
        self.setTextCursor(cursor)
        self.centerCursor()

    # ── folding ───────────────────────────────────────────────────────────────

    def _compute_fold_map(self) -> dict[int, int]:
        """Scan document text and return {open_line: close_line} for every {} pair."""
        fold_map: dict[int, int] = {}
        # open_line_stack: each entry is the line number of the matching '{'
        stack: list[int] = []
        in_block_comment = False

        for ln, line in enumerate(self.toPlainText().splitlines()):
            i = 0
            while i < len(line):
                if in_block_comment:
                    if line[i : i + 2] == "*/":
                        in_block_comment = False
                        i += 2
                    else:
                        i += 1
                    continue
                if line[i : i + 2] == "//":
                    break
                if line[i : i + 2] == "/*":
                    in_block_comment = True
                    i += 2
                    continue
                if line[i] == '"':
                    i += 1
                    while i < len(line) and line[i] != '"':
                        i += 1
                    i += 1
                    continue
                if line[i] == "{":
                    stack.append(ln)
                elif line[i] == "}":
                    if stack:
                        open_ln = stack.pop()
                        if open_ln != ln:           # skip single-line { }
                            fold_map[open_ln] = ln
                i += 1

        return fold_map

    def _compute_comment_folds(self) -> dict[int, int]:
        """Return {start_line: end_line} for every run of 2+ continuous comment lines.

        A line counts as a comment line when it carries comment content and no code:
        a ``//`` line, a ``/* ... */`` block (opening, interior, and closing lines),
        but not a line with real code after ``*/``. Blank and code lines break a run.
        """
        fold_map: dict[int, int] = {}
        in_block_comment = False
        run_start: int | None = None
        prev_ln = -1

        for ln, line in enumerate(self.toPlainText().splitlines()):
            saw_comment = in_block_comment
            has_code = False
            i = 0
            while i < len(line):
                if in_block_comment:
                    if line[i : i + 2] == "*/":
                        in_block_comment = False
                        i += 2
                    else:
                        i += 1
                    continue
                ch = line[i]
                if line[i : i + 2] == "//":
                    saw_comment = True
                    break
                if line[i : i + 2] == "/*":
                    saw_comment = True
                    in_block_comment = True
                    i += 2
                    continue
                if ch == '"':
                    has_code = True
                    i += 1
                    while i < len(line) and line[i] != '"':
                        i += 1
                    i += 1
                    continue
                if not ch.isspace():
                    has_code = True
                i += 1

            is_comment_line = saw_comment and not has_code
            if is_comment_line:
                if run_start is None:
                    run_start = ln
            else:
                if run_start is not None and prev_ln > run_start:
                    fold_map[run_start] = prev_ln
                run_start = None
            prev_ln = ln

        if run_start is not None and prev_ln > run_start:
            fold_map[run_start] = prev_ln
        return fold_map

    def _toggle_fold(self, open_line: int) -> None:
        close_line = self._fold_map.get(open_line)
        if close_line is None:
            return
        doc = self.document()
        collapsing = open_line not in self._folded
        for ln in range(open_line + 1, close_line + 1):
            block = doc.findBlockByNumber(ln)
            if not block.isValid():
                break
            block.setVisible(not collapsing)
            doc.markContentsDirty(block.position(), block.length())
        if collapsing:
            self._folded.add(open_line)
        else:
            self._folded.discard(open_line)
        self.viewport().update()
        self.update_line_number_area_width(0)
        self.line_number_area.update()

    def _auto_fold_foamfile(self) -> None:
        """Collapse the FoamFile { } block automatically on load."""
        doc = self.document()
        for open_ln in sorted(self._fold_map):
            if open_ln > 10:        # FoamFile is always near the top
                break
            block = doc.findBlockByNumber(open_ln)
            if not block.isValid():
                break
            text = block.text()
            if "FoamFile" in text:
                self._toggle_fold(open_ln)
                break
            # FoamFile on the preceding line, { on this line
            if open_ln > 0:
                prev = doc.findBlockByNumber(open_ln - 1)
                if prev.isValid() and "FoamFile" in prev.text():
                    self._toggle_fold(open_ln)
                    break

    def _auto_fold_header_comment(self) -> None:
        """Collapse the top-of-file comment banner automatically on load."""
        for open_ln in sorted(self._comment_folds):
            if open_ln > 5:        # banner sits at the very top (allow a few blank lines)
                break
            self._toggle_fold(open_ln)
            break
