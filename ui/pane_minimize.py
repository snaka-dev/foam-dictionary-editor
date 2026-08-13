# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""One-click collapse/restore for a single pane of a QSplitter.

Dragging a splitter handle across the window to park a pane out of the way is
several mouse moves for something the user wants as one click — most sharply in
side-by-side mode, where the Detail pane is dead weight and every pixel of it is
a pixel the 3-D view does not get.

Two collapse styles, because the panes are not alike:

``sizes``
    Set the pane's size to 0 through ``QSplitter.setSizes``. Works wherever the
    splitter permits a zero — the Detail pane and the file list — and leaves the
    handle draggable, so the pane can also be pulled back open by hand.

``strip``
    Pin the pane's maximum size to a few pixels, leaving a visible sliver.
    Needed for the Editor/Terminal row for two separate reasons. Its splitter
    sets ``setCollapsible(…, False)`` on purpose (so the handle drags smoothly
    instead of snapping shut), and under that flag ``setSizes`` silently clamps
    to the widget's ``minimumSizeHint`` — 136 px for that tab widget, and no
    amount of zeroing the pages' minimums lowers it, because QTabWidget does not
    derive its minimum hint from them. Pinning the maximum is honoured either
    way. It is also the better *design* there: the sliver left behind is the tab
    bar, which keeps the Editor/Terminal tabs and the editor↔tree sync buttons
    on screen and clickable rather than hiding them along with the pane.

While a pane is pinned its handle cannot be dragged open (there is no room to
drag into), so restoring is always through the control that minimized it — a
View-menu item, a button, or a double-click on the handle. That is why every
minimizable pane needs a control that stays visible while it is minimized: the
sizes are persisted between runs, so a pane collapsed at shutdown comes back
collapsed, and a 7-px handle at the window edge is not a way back.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QSplitter, QWidget

# Stable names for the minimizable panes, used by the View menu, by
# ui/window_state.py's ``minimized_panes`` and by the handle double-click.
PANE_FILE_LIST = "file_list"
PANE_DETAIL = "detail"
PANE_BOTTOM = "bottom"

# Qt's QWIDGETSIZE_MAX, which PySide6 does not export.
_QWIDGETSIZE_MAX = (1 << 24) - 1


class PaneMinimizer:
    """Collapses and restores one pane of *splitter*.

    *strip* returns how many pixels to leave visible; ``None`` collapses the
    pane to nothing through ``setSizes``. *default_size* is what a restore falls
    back to when there is no remembered size to go back to — a pane minimized in
    one run and restored in the next has only what was persisted, and a saved
    size of 0 would restore to nothing at all.
    """

    def __init__(
        self,
        splitter: QSplitter,
        index: int,
        *,
        strip: Callable[[], int] | None = None,
        default_size: int = 200,
    ) -> None:
        self.splitter = splitter
        self.index = index
        self._strip = strip
        self._default_size = default_size
        self._restore_size = default_size
        # The whole row of sizes as it was when this pane collapsed. Restoring
        # it verbatim is what keeps a collapse/restore cycle exact: rebuilding
        # the row from one remembered number rounds, and the rounding is a pixel
        # per cycle that never comes back. Dropped whenever it can no longer be
        # trusted -- a different pane count, a resized splitter, or a restore
        # size that came from a persisted session rather than from a collapse.
        self._restore_sizes: list[int] | None = None
        self._minimized = False

    # ── state ─────────────────────────────────────────────────────────────────

    @property
    def minimized(self) -> bool:
        return self._minimized

    @property
    def restore_size(self) -> int:
        """The size a restore would go back to; persisted across runs."""
        return self._restore_size

    @restore_size.setter
    def restore_size(self, value: int) -> None:
        self._restore_size = value if value > 0 else self._default_size
        # A size set from outside describes this pane only; the row it was
        # captured beside is not this row.
        self._restore_sizes = None

    # ── operations ────────────────────────────────────────────────────────────

    def set_minimized(self, minimized: bool) -> None:
        if minimized:
            self.minimize()
        else:
            self.restore()

    def minimize(self) -> None:
        """Collapse the pane, remembering its current size.

        A no-op when already minimized: re-running it would remember the
        collapsed size and there would be nothing to restore to.
        """
        if self._minimized:
            return
        sizes = self.splitter.sizes()
        if self.index >= len(sizes):
            return
        self.restore_size = sizes[self.index]
        self._restore_sizes = list(sizes)
        self._minimized = True
        target = self._strip() if self._strip is not None else 0
        if self._strip is not None:
            self._pin(target)
        self.splitter.setSizes(self._with_size(sizes, target))

    def restore(self) -> None:
        if not self._minimized:
            return
        self._minimized = False
        if self._strip is not None:
            self._pin(None)
        sizes = self.splitter.sizes()
        if self.index >= len(sizes):
            return
        remembered = self._restore_sizes
        if remembered is not None and len(remembered) == len(sizes) \
                and sum(remembered) == sum(sizes):
            self.splitter.setSizes(remembered)
        else:
            self.splitter.setSizes(self._with_size(sizes, self._restore_size))
        self._restore_sizes = None

    # ── internals ─────────────────────────────────────────────────────────────

    def _widget(self) -> QWidget | None:
        return self.splitter.widget(self.index)

    def _pin(self, size: int | None) -> None:
        """Clamp (or release) the pane widget's maximum along the split axis."""
        widget = self._widget()
        if widget is None:
            return
        limit = _QWIDGETSIZE_MAX if size is None else size
        if self.splitter.orientation() == Qt.Orientation.Vertical:
            widget.setMaximumHeight(limit)
        else:
            widget.setMaximumWidth(limit)

    def _with_size(self, sizes: list[int], target: int) -> list[int]:
        """Give the pane *target* pixels and hand the difference to the others.

        Split in proportion to what the other panes already hold, so a
        three-pane row does not shuffle its two survivors while one collapses.
        When they are all at zero — the tree/comparison/detail row, where the
        comparison pane is normally hidden — the space goes to the pane before
        this one, or after it when this is the first.
        """
        new = list(sizes)
        delta = new[self.index] - target
        new[self.index] = target
        others = [i for i in range(len(new)) if i != self.index]
        if not others:
            return new
        pool = sum(new[i] for i in others)
        if pool <= 0:
            fallback = self.index - 1 if self.index > 0 else self.index + 1
            if 0 <= fallback < len(new):
                new[fallback] += delta
            return new
        given = 0
        for i in others[:-1]:
            share = round(delta * new[i] / pool)
            new[i] += share
            given += share
        new[others[-1]] += delta - given
        return new


class _HandleDoubleClickFilter(QObject):
    """Turns a double-click on a splitter handle into a callback.

    An event filter rather than a QSplitter/QSplitterHandle subclass: the window
    builds four splitters in three different places, and subclassing would mean
    touching all of them to gain a behaviour that is entirely about the handle.
    """

    def __init__(self, parent: QObject, splitter: QSplitter,
                 callback: Callable[[QSplitter, int], None]) -> None:
        super().__init__(parent)
        self._splitter = splitter
        self._callback = callback

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.MouseButtonDblClick:
            for index in range(1, self._splitter.count()):
                if self._splitter.handle(index) is watched:
                    self._callback(self._splitter, index)
                    return True
        return False


def install_handle_double_click(
    splitter: QSplitter,
    owner: QObject,
    callback: Callable[[QSplitter, int], None],
) -> _HandleDoubleClickFilter:
    """Watch every handle *splitter* has now; the filter is owned by *owner*.

    Handles created later are not covered, which is why this is called after a
    splitter has all of its widgets.
    """
    handle_filter = _HandleDoubleClickFilter(owner, splitter, callback)
    for index in range(1, splitter.count()):
        handle = splitter.handle(index)
        if handle is not None:
            handle.installEventFilter(handle_filter)
    return handle_filter
