# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""A read-only window onto one data file Plot Results read.

Not the main editor: Plot Results holds several cases, and a file of a case
other than the open one has no place in the main window's file list, its
buffers or its tree. These files are also data, not dictionaries -- the
parser would only turn them into raw entries -- and a forces or probes file
can run to tens of MB, so a large file shows its head (where the column
names are) and its tail (the latest values), with a note saying so.
"""
from __future__ import annotations

import collections
import gzip
import os

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QTextOption
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from i18n import tr
from ui.fonts import monospace_font

# A file up to this size is shown whole.
FULL_LIMIT = 16 * 1024 * 1024
# Otherwise: this many lines from the start, and this many bytes from the end.
HEAD_LINES = 200
TAIL_BYTES = 4 * 1024 * 1024


def _decode(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def _open_binary(path: str):
    with open(path, "rb") as fh:
        compressed = fh.read(2) == b"\x1f\x8b"
    return gzip.open(path, "rb") if compressed else open(path, "rb")


def read_for_view(
    path: str,
    full_limit: int = FULL_LIMIT,
    head_lines: int = HEAD_LINES,
    tail_bytes: int = TAIL_BYTES,
) -> tuple[str, int, bool]:
    """The text to show for *path*, its (uncompressed) size, and whether it was cut.

    A file larger than *full_limit* gives its first *head_lines* lines and
    the whole lines in its last *tail_bytes*. Gzipped files are read through,
    as the plot reader reads them. Raises ``OSError`` like ``open``.
    """
    head: list[bytes] = []
    tail: collections.deque[bytes] = collections.deque()
    tail_size = 0
    size = 0
    with _open_binary(path) as fh:
        for line in fh:
            size += len(line)
            if len(head) < head_lines:
                head.append(line)
                continue
            tail.append(line)
            tail_size += len(line)
            # Keep whole lines only, and never more than both limits need.
            while tail and tail_size - len(tail[0]) >= tail_bytes and size > full_limit:
                tail_size -= len(tail.popleft())
    if size <= full_limit:
        return _decode(b"".join(head) + b"".join(tail)), size, False
    skipped = tr("… {size} MB not shown …").format(
        size=f"{(size - sum(map(len, head)) - tail_size) / 2**20:.1f}"
    )
    text = _decode(b"".join(head)) + f"\n{skipped}\n\n" + _decode(b"".join(tail))
    return text, size, True


def show_in_folder(path: str) -> None:
    """Open the folder holding *path* in the desktop's file manager."""
    QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(path)))


class DataFileViewer(QDialog):
    """Non-modal, read-only view of one data file, with Reload."""

    def __init__(self, path: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.path = path
        # The last three parts -- probes/0/U -- since a bare "U" or "p" says
        # nothing about which of a case's files this is.
        self.setWindowTitle("/".join(path.replace(os.sep, "/").split("/")[-3:]))
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.resize(900, 600)
        layout = QVBoxLayout(self)
        self.path_label = QLabel(path)
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.path_label.setWordWrap(True)
        layout.addWidget(self.path_label)
        self.note = QLabel()
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setFont(monospace_font())
        self.text.setWordWrapMode(QTextOption.WrapMode.NoWrap)
        layout.addWidget(self.text, 1)
        buttons = QHBoxLayout()
        reload_btn = QPushButton(tr("Reload"))
        reload_btn.setToolTip(tr("Read the file again, for data written since"))
        reload_btn.clicked.connect(self.reload)
        folder_btn = QPushButton(tr("Show in Folder"))
        folder_btn.clicked.connect(lambda: show_in_folder(self.path))
        close_btn = QPushButton(tr("Close"))
        close_btn.clicked.connect(self.close)
        buttons.addWidget(reload_btn)
        buttons.addWidget(folder_btn)
        buttons.addStretch(1)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)
        self.reload()

    def reload(self) -> None:
        try:
            text, size, cut = read_for_view(self.path, FULL_LIMIT)
        except OSError as exc:
            self.text.setPlainText("")
            self.note.setText(tr("Cannot read this file: {error}").format(error=exc))
            self.note.show()
            return
        self.text.setPlainText(text)
        if cut:
            self.note.setText(tr(
                "This file is {size} MB, too large to show whole: shown are its first "
                "{lines} lines and its last {tail} MB. Show in Folder opens it elsewhere."
            ).format(size=f"{size / 2**20:.1f}", lines=HEAD_LINES, tail=TAIL_BYTES // 2**20))
            self.note.show()
        else:
            self.note.hide()
        if cut:
            # The latest values are what one usually opens a data file for.
            self.text.moveCursor(self.text.textCursor().MoveOperation.End)
