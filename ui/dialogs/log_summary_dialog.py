# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Non-modal viewer that condenses an OpenFOAM run log (log.blockMesh,
log.snappyHexMesh, log.topoSet, ...) into a short summary, with a Raw Log tab
for the untouched text. Kept non-modal so it can sit beside the main window
while the tree/editor stay usable (like find_examples_dialog, unlike the
app's other, modal dialogs)."""
from __future__ import annotations

import glob
import html
import os

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from i18n import tr
from services.log_advice import Advice, advise
from services.log_summary import format_summary, parse_log
from ui.log_advice_text import advice_text, advice_title

_DIALOG_WIDTH = 640
_DIALOG_HEIGHT = 480


def _default_log_file(case_dir: str) -> str:
    candidates = glob.glob(os.path.join(case_dir, "log.*"))
    if not candidates:
        return ""
    return max(candidates, key=os.path.getmtime)


class LogSummaryDialog(QDialog):
    """Non-modal dialog showing a condensed summary of a chosen run log."""

    # Absolute path and 1-based line of a file an advice links to.
    open_requested = Signal(str, int)

    def __init__(
        self,
        case_dir: str,
        initial_file: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("View Log Summary"))
        self.resize(_DIALOG_WIDTH, _DIALOG_HEIGHT)
        self.setWindowModality(Qt.WindowModality.NonModal)

        self._case_dir = case_dir

        layout = QVBoxLayout(self)

        file_label = QLabel(tr("Log file:"))
        self._file_edit = QLineEdit(initial_file or _default_log_file(case_dir))
        browse_btn = QPushButton(tr("Browse…"))
        browse_btn.clicked.connect(self._browse)

        file_row = QHBoxLayout()
        file_row.addWidget(file_label)
        file_row.addWidget(self._file_edit, 1)
        file_row.addWidget(browse_btn)
        layout.addLayout(file_row)

        mono_font = QFont("Monospace")
        mono_font.setStyleHint(QFont.StyleHint.TypeWriter)

        self._summary_text = QPlainTextEdit()
        self._summary_text.setReadOnly(True)
        self._summary_text.setFont(mono_font)

        self._raw_text = QPlainTextEdit()
        self._raw_text.setReadOnly(True)
        self._raw_text.setFont(mono_font)

        tabs = QTabWidget()
        tabs.addTab(self._summary_text, tr("Summary"))
        tabs.addTab(self._raw_text, tr("Raw Log"))

        # Plain-language advice for the errors the log holds (services/
        # log_advice.py); hidden when there is none.
        self._advice: list[Advice] = []
        self._advice_view = QTextBrowser()
        self._advice_view.setOpenLinks(False)
        self._advice_view.anchorClicked.connect(self._on_advice_link)
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self._advice_view)
        splitter.addWidget(tabs)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton(tr("Close"))
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        self._file_edit.returnPressed.connect(self._reload)
        self._reload()

    def show_log(self, path: str) -> None:
        """Summarize *path* (Allrun Steps' "Open Log")."""
        self._file_edit.setText(path)
        self._reload()

    def set_case_dir(self, case_dir: str) -> None:
        self._case_dir = case_dir
        self._file_edit.setText(_default_log_file(case_dir))
        self._reload()

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, tr("Select log file"), self._case_dir)
        if path:
            self._file_edit.setText(path)
            self._reload()

    def _reload(self) -> None:
        path = self._file_edit.text().strip()
        if not path or not os.path.isfile(path):
            self._summary_text.setPlainText(tr("Select a log file to summarize."))
            self._raw_text.setPlainText("")
            self._set_advice([])
            return
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError as exc:
            self._summary_text.setPlainText(tr("Could not read file: {error}").format(error=exc))
            self._raw_text.setPlainText("")
            self._set_advice([])
            return
        self._raw_text.setPlainText(text)
        summary = parse_log(text)
        self._summary_text.setPlainText(format_summary(summary))
        # A log's relative "file:" references point into the case it was
        # written in, which is the directory holding it.
        self._set_advice(advise(text, os.path.dirname(os.path.abspath(path))))

    def advice(self) -> list[Advice]:
        """The advice currently shown (for tests)."""
        return list(self._advice)

    def _set_advice(self, advice: list[Advice]) -> None:
        self._advice = advice
        self._advice_view.setVisible(bool(advice))
        if not advice:
            self._advice_view.clear()
            return
        parts = ["<h3>" + html.escape(tr("What went wrong")) + "</h3>"]
        for i, item in enumerate(advice):
            body = "<p><b>" + html.escape(advice_title(item)) + "</b><br>"
            body += html.escape(advice_text(item))
            if item.path:
                where = os.path.basename(item.path)
                label = (
                    tr("Open {file} at line {line}").format(file=where, line=item.line)
                    if item.line else tr("Open {file}").format(file=where)
                )
                body += f'<br><a href="open:{i}">' + html.escape(label) + "</a>"
            parts.append(body + "</p>")
        self._advice_view.setHtml("".join(parts))

    def _on_advice_link(self, url: QUrl) -> None:
        text = url.toString()
        if not text.startswith("open:"):
            return
        try:
            item = self._advice[int(text[5:])]
        except (ValueError, IndexError):
            return
        if item.path:
            self.open_requested.emit(item.path, item.line)
