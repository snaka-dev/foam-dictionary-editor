# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Give word-wrapped labels the height they actually need.

``QLabel.sizeHint()`` for a wrapped label is measured at a width Qt guesses,
not the width the label ends up with. In a dialog of fixed width that guess is
usually wrong and always optimistic: the About dialog's acknowledgements label
reports 102 px at a 16 pt desktop font while needing 176 px at its real 458 px
width, so the layout hands it 102 and the last lines are cut off. The disclaimer
box loses its second paragraph the same way, at font sizes as ordinary as 11 pt.

The cure has to run *after* the first layout pass, because that is the first
moment a label knows its width. Hence a one-shot call from ``showEvent`` rather
than anything at construction time: ask each wrapped label how tall it needs to
be at the width it was given, pin that as its minimum, and let the dialog
``adjustSize()`` to the total.

Note that the usual suggestion — turning on ``QSizePolicy.setHeightForWidth`` —
does nothing here. ``hasHeightForWidth()`` is already true for these labels; the
layout is not ignoring height-for-width, it is being told a sizeHint that
disagrees with it.

Dialogs grow taller as a result, which is the point: the alternative is text the
user cannot read. A dialog whose contents genuinely exceed the screen would need
a scroll area, which none of these are near.
"""
from __future__ import annotations

from PySide6.QtWidgets import QLabel, QWidget


def fit_wrapped_labels(root: QWidget) -> None:
    """Pin every wrapped label under *root* to the height its width needs.

    Call after the widget has been laid out — from ``showEvent``, not from
    ``__init__``, where a label still has whatever default width Qt gave it and
    the height derived from that would be pinned for good. The zero-width guard
    below is only insurance; calling at the right time is the real protection.

    Minimums are raised, never lowered, so a label that was already given room
    keeps it.
    """
    for label in root.findChildren(QLabel):
        if not label.wordWrap():
            continue
        width = label.width()
        if width <= 0:
            continue
        needed = label.heightForWidth(width)
        if needed > label.minimumHeight():
            label.setMinimumHeight(needed)
