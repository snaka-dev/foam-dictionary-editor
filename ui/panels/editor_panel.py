# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QAction, QKeySequence, QShortcut, QTextCursor, QTextDocument
from PySide6.QtWidgets import (
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSizePolicy,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from foam.utils import is_script_text
from i18n import tr
from ui.fonts import icon_pixel_size
from ui.icons import icon
from ui.theme import colors
from ui.widgets.code_editor import CodeEditor

_SPACING_LARGE = 16


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

        self._cursor_label = QLabel(tr("Line: {n}").format(n=1))

        # Shown only for an `#include` target outside the case directory.
        self._read_only_label = QLabel(tr("read-only"))
        self._read_only_label.setStyleSheet(f"color: {colors().file_read_only_fg};")
        self._read_only_label.setToolTip(tr("read-only — outside the case directory"))
        self._read_only_label.setVisible(False)

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
        layout.addWidget(self._build_toolbar())
        layout.addWidget(self._editor)

    @property
    def editor(self) -> CodeEditor:
        return self._editor

    def set_text(self, text: str) -> None:
        self._updating_programmatically = True
        # Shebang → shell-script highlighting (Allrun etc.), else OpenFOAM rules.
        self._editor.set_shell_mode(is_script_text(text))
        self._editor.setPlainText(text)
        self._updating_programmatically = False
        self._update_cursor_status()

    def set_read_only(self, read_only: bool) -> None:
        """Lock the text against editing and show the read-only badge."""
        self._editor.setReadOnly(read_only)
        self._read_only_label.setVisible(read_only)

    def reload_highlighting(self) -> None:
        """Reload the highlighter's keyword list without emitting user_text_changed.

        QSyntaxHighlighter.rehighlight() fires the document's textChanged even
        though only formatting changed, so the guard is required to keep the
        file from being marked dirty.
        """
        self._updating_programmatically = True
        self._editor.reload_highlighting()
        self._updating_programmatically = False

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

    def _build_toolbar(self) -> QToolBar:
        """Build the Find row as a real QToolBar.

        A QToolBar over the plain QHBoxLayout of QToolButtons this used to
        be: its buttons default to autoRaise, so they paint flat until
        hovered instead of each drawing as its own raised, bordered
        rectangle -- see ui/main_window.py's _build_top_bar for the same fix
        applied to the main action row, and why it has to be a real toolbar
        rather than a layout for the flatness to take effect. That also
        means this panel needs no separator line of its own any more: the
        toolbar's own top edge is the separation.
        """
        from app_config import get_app_config

        toolbar = QToolBar()
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        icon_side = icon_pixel_size()
        toolbar.setIconSize(QSize(icon_side, icon_side))

        def spacer(width: int) -> QWidget:
            gap = QWidget()
            gap.setFixedWidth(width)
            return gap

        self._find_action = QAction(icon("find"), tr("Find"), self)
        self._find_action.setToolTip(tr("Find text (Ctrl+F)"))
        self._find_action.triggered.connect(self._find)
        toolbar.addAction(self._find_action)

        self._find_prev_action = QAction(icon("find-previous"), tr("Find Prev"), self)
        self._find_prev_action.setToolTip(tr("Find previous occurrence (Shift+F3)"))
        self._find_prev_action.triggered.connect(self._find_prev)
        toolbar.addAction(self._find_prev_action)

        self._find_next_action = QAction(icon("find-next"), tr("Find Next"), self)
        self._find_next_action.setToolTip(tr("Find next occurrence (F3)"))
        self._find_next_action.triggered.connect(self._find_next)
        toolbar.addAction(self._find_next_action)

        toolbar.addWidget(spacer(_SPACING_LARGE))

        self._find_in_tree_action = QAction(icon("find-in-tree"), tr("Find in Tree"), self)
        self._find_in_tree_action.setToolTip(
            tr("Select the tree entry for the current cursor line (Ctrl+Shift+T)")
        )
        self._find_in_tree_action.triggered.connect(self.find_in_tree_requested.emit)
        toolbar.addAction(self._find_in_tree_action)

        toolbar.addWidget(spacer(_SPACING_LARGE))

        cfg = get_app_config()
        self._highlight_action = QAction(icon("highlight"), tr("Highlight"), self)
        self._highlight_action.setToolTip(tr("Toggle syntax highlighting"))
        self._highlight_action.setCheckable(True)
        self._highlight_action.setChecked(cfg.get_feature("syntax_highlighting", True))

        def _toggle_highlight(checked: bool) -> None:
            self._updating_programmatically = True
            self._editor.set_highlighting_enabled(checked)
            self._updating_programmatically = False
            cfg.set_feature("syntax_highlighting", checked)
            cfg.save()

        toolbar.addAction(self._highlight_action)
        self._editor.set_highlighting_enabled(self._highlight_action.isChecked())
        self._highlight_action.toggled.connect(_toggle_highlight)

        # Expanding spacer widget: a QToolBar has no addStretch, unlike the
        # QHBoxLayout this replaces.
        stretch = QWidget()
        stretch.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(stretch)

        toolbar.addWidget(self._read_only_label)
        toolbar.addWidget(spacer(_SPACING_LARGE))
        toolbar.addWidget(self._cursor_label)
        return toolbar

    def _on_text_changed(self) -> None:
        if not self._updating_programmatically:
            self.user_text_changed.emit()

    def _update_cursor_status(self) -> None:
        self._cursor_label.setText(tr("Line: {n}").format(n=self._editor.current_line_number()))

    def _find(self) -> None:
        initial = self._editor.textCursor().selectedText() or self._last_search_text
        text, ok = QInputDialog.getText(
            self, tr("Find"), tr("Text to find:"), QLineEdit.EchoMode.Normal, initial
        )
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
        flag = QTextDocument.FindFlag.FindBackward if backward else QTextDocument.FindFlag(0)
        wrap_anchor = QTextCursor.MoveOperation.End if backward else QTextCursor.MoveOperation.Start

        found = self._editor.find(self._last_search_text, flag)
        if not found:
            cursor = self._editor.textCursor()
            cursor.movePosition(wrap_anchor)
            self._editor.setTextCursor(cursor)
            found = self._editor.find(self._last_search_text, flag)
        if not found:
            QMessageBox.information(
                self, tr("Find"),
                tr("Text not found: {text}").format(text=self._last_search_text),
            )
