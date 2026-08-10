# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from i18n import tr
from ui.theme import colors

# Sections defined as (i18n_key, [(action_key, shortcut), ...])
#
# Sections group by *what has focus*, because several keys mean different things
# in the tree and in the editor. A row therefore has to sit under the widget its
# key is scoped to, not under the panel it feels related to: Find in Tree reads
# like an editor command and has a button in the editor toolbar, but it is bound
# to the window and fires from anywhere, so it belongs under Application.
#
# The editor's Undo/Redo/Cut/Copy/Paste/Select All are QPlainTextEdit built-ins
# rather than shortcuts this app installs, so their keys are Qt's per-platform
# standard ones and are spelled out here for X11 (`QKeySequence.keyBindings`).
_SECTIONS_DATA: list[tuple[str, list[tuple[str, str]]]] = [
    ("Editor", [
        ("Find",               "Ctrl+F"),
        ("Find Next",          "F3"),
        ("Find Previous",      "Shift+F3"),
        ("Undo",               "Ctrl+Z"),
        ("Redo",               "Ctrl+Y  or  Ctrl+Shift+Z"),
        ("Cut",                "Ctrl+X"),
        ("Copy",               "Ctrl+C"),
        ("Paste",              "Ctrl+V"),
        ("Select All",         "Ctrl+A"),
        ("Zoom In",            "Ctrl++  or  Ctrl+="),
        ("Zoom Out",           "Ctrl+-"),
        ("Reset Zoom",         "Ctrl+0"),
        ("Zoom (mouse)",       "Ctrl + scroll wheel"),
    ]),
    ("Tree", [
        ("Copy Value",         "Ctrl+C"),
        ("Paste Value",        "Ctrl+V"),
        ("Undo Tree Edit",     "Ctrl+Z"),
        ("Redo Tree Edit",     "Ctrl+Shift+Z"),
    ]),
    ("Application", [
        ("Open Case",          "Ctrl+O"),
        ("Save File",          "Ctrl+S"),
        ("Save Case",          "Ctrl+Shift+S"),
        ("Apply Text to Tree", "Ctrl+Shift+A"),
        ("Find in Tree",       "Ctrl+Shift+T"),
        ("Exit",               "Ctrl+Q"),
    ]),
    ("Panes (show / minimize)", [
        ("File List",          "Ctrl+1"),
        ("Detail Pane",        "Ctrl+2"),
        ("Editor Pane",        "Ctrl+3"),
        ("Minimize a pane",    "Double-click its splitter handle"),
    ]),
    # These come from VTK's trackball interactor style and from pyvista's own
    # bindings, not from this application, so they are listed rather than
    # installed. Two more that VTK accepts are deliberately left out: P picks,
    # which nothing here is wired to, and E / Q raise VTK's ExitEvent, which
    # nothing observes — pyvistaqt only connects that to a quit in its own demo.
    ("BlockMesh 3-D viewer", [
        ("Rotate",             "Left drag"),
        ("Pan",                "Shift + left drag"),
        ("Zoom",               "Scroll wheel, right drag  or  Up / Down"),
        ("Reset camera",       "R"),
        ("Isometric view",     "V"),
        ("Fly to point",       "F"),
        ("Wireframe / Surface", "W  /  S"),
        ("Point & line size",  "+  /  -"),
    ]),
]

# A group box costs roughly this many rows' worth of height on top of its rows.
_HEADER_WEIGHT = 1.5
_COLUMNS = 2
# Largest share of the screen the dialog claims for itself when first shown.
_SCREEN_FRACTION = 0.9


def _split_into_columns(
    sections: list[tuple[str, list[tuple[str, str]]]],
) -> list[list[tuple[str, list[tuple[str, str]]]]]:
    """Deal the sections into ``_COLUMNS`` columns without reordering them.

    Source order is kept so the list still reads top-to-bottom then left-to-
    right; only the break points are chosen. A section joins the current column
    while its *midpoint* still falls in that column's share of the total
    height, which balances better than breaking once the share is used up
    (a long section landing on the boundary would otherwise go entirely into
    whichever column asked for it first). With two columns that also guarantees
    the second is used: the last section's midpoint can only fall in the first
    column's share if that section is the whole list.
    """
    weights = [len(rows) + _HEADER_WEIGHT for _, rows in sections]
    share = sum(weights) / _COLUMNS

    columns: list[list[tuple[str, list[tuple[str, str]]]]] = [[] for _ in range(_COLUMNS)]
    placed = 0.0
    index = 0
    for section, weight in zip(sections, weights):
        while index < _COLUMNS - 1 and placed + weight / 2 > share * (index + 1):
            index += 1
        columns[index].append(section)
        placed += weight
    return columns


class KeyboardShortcutsDialog(QDialog):
    """Reference list of the application's shortcuts.

    The list has outgrown a single column that fits on screen: at an 11 pt
    desktop font it wanted 1123 px of height, and Settings > UI Scale multiplies
    that again. Two things keep it usable on a small display. The sections are
    laid out in ``_COLUMNS`` columns, which nearly halves the height (1123 px
    down to 631 px at that same 11 pt); and the whole grid sits in a
    ``QScrollArea``, so the layout's minimum height stops being the dialog's.
    Without the scroll area a ``QDialog`` cannot be resized below its content
    and simply hangs off the bottom of the screen, taking the Close button
    with it.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Keyboard Shortcuts"))
        self._sized = False

        content = QWidget()
        # A QVBoxLayout per column rather than one QGridLayout: a grid shares
        # its row heights *across* columns, so the four-row Application group
        # would be stretched to the height of the fourteen-row Editor group
        # beside it and its rows drawn spaced far apart.
        columns = QHBoxLayout(content)
        columns.setContentsMargins(0, 0, 0, 0)
        for sections in _split_into_columns(_SECTIONS_DATA):
            column = QVBoxLayout()
            for section_name, shortcuts in sections:
                column.addWidget(self._build_group(section_name, shortcuts))
            # Keep a short column top-aligned against its taller neighbour.
            column.addStretch(1)
            columns.addLayout(column)

        self._content = content
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        self._scroll.setWidget(content)

        # The button box stays outside the scroll area: Close has to be
        # reachable even when the list is taller than the screen.
        self._buttons = QDialogButtonBox(QDialogButtonBox.Close)
        self._buttons.rejected.connect(self.reject)

        self._layout = QVBoxLayout(self)
        self._layout.addWidget(self._scroll)
        self._layout.addWidget(self._buttons)

    @staticmethod
    def _build_group(section_name: str, shortcuts: list[tuple[str, str]]) -> QGroupBox:
        group = QGroupBox(tr(section_name))
        grid = QGridLayout(group)
        grid.setColumnStretch(0, 1)
        for row, (action, key) in enumerate(shortcuts):
            action_lbl = QLabel(tr(action))
            key_lbl = QLabel(key)
            key_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            key_lbl.setStyleSheet(f"font-family: monospace; color: {colors().secondary_text};")
            grid.addWidget(action_lbl, row, 0)
            grid.addWidget(key_lbl,    row, 1)
        return group

    def sizeHint(self) -> QSize:
        """How big the whole list is — which the layout cannot work out itself.

        ``QScrollArea::sizeHint`` bounds itself to 36 x 24 character cells
        whatever it holds (684 x 456 px at a 9 pt font here), so the dialog's
        own layout would ask for a window with most of the list already
        scrolled out of sight. The content widget does know its real size; the
        rest is this dialog's chrome, and the minimum size stays untouched —
        that is the scroll area's job and the point of having it.
        """
        margins = self._layout.contentsMargins()
        frame = 2 * self._scroll.frameWidth()
        content = self._content.sizeHint()
        buttons = self._buttons.sizeHint()
        return QSize(
            max(content.width() + frame, buttons.width()) + margins.left() + margins.right(),
            content.height() + frame + self._layout.spacing() + buttons.height()
            + margins.top() + margins.bottom(),
        )

    def showEvent(self, event):
        """Open at the size the content wants, capped to what the screen has.

        ``resize`` rather than ``adjustSize``, which clamps a window to two
        thirds of the screen — the same reason ui/label_fit.py avoids it. The
        cap here is deliberately looser than that and, unlike it, leaves the
        dialog free to be dragged larger or smaller afterwards.
        """
        super().showEvent(event)
        if self._sized:
            return
        self._sized = True

        self._layout.activate()
        wanted = self.sizeHint()
        screen = self.screen() or QGuiApplication.primaryScreen()
        available = screen.availableGeometry() if screen is not None else None
        if available is None:
            self.resize(wanted)
            return

        max_h = int(available.height() * _SCREEN_FRACTION)
        max_w = int(available.width() * _SCREEN_FRACTION)
        height = min(wanted.height(), max_h)
        width = min(wanted.width(), max_w)
        # A clamp on either axis brings out the scrollbar for that axis, which
        # then eats into the *other* one; spend the room now, where there is
        # any, rather than let the second scrollbar appear on top.
        if height < wanted.height():
            width = min(width + self._scroll.verticalScrollBar().sizeHint().width(), max_w)
        if width < wanted.width():
            height = min(height + self._scroll.horizontalScrollBar().sizeHint().height(), max_h)
        self.resize(width, height)
