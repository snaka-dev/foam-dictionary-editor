# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Context menus as data: each action paired with what it does.

A context menu built here is a ``(QMenu, {QAction: handler})`` pair rather
than a ``QMenu.exec()`` followed by an ``if chosen == x_action … elif`` chain.
That keeps the blocking ``exec()`` -- which waits for a mouse an offscreen test
has no way to supply -- in one line, :func:`exec_menu`, and leaves the part
worth testing, which row raises which signal, callable without it: build the
menu, look the row up by its text, call its handler.
"""
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QPoint
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QWidget

MenuActions = dict[QAction, Callable[[], None]]
BuiltMenu = tuple[QMenu, MenuActions]


class MenuBuilder:
    """A QMenu plus the handler table its :meth:`add` fills in."""

    def __init__(self, parent: QWidget | None) -> None:
        self.menu = QMenu(parent)
        self.actions: MenuActions = {}

    def add(
        self,
        label: str,
        handler: Callable[[], None],
        *,
        enabled: bool = True,
        into: QMenu | None = None,
    ) -> QAction:
        """Add a row; ``into`` puts it in a submenu of this menu instead.

        A submenu's action still dispatches from the one table: QMenu.exec()
        on the top menu returns whichever action was chosen, at any depth.
        """
        action = (into or self.menu).addAction(label)
        action.setEnabled(enabled)
        self.actions[action] = handler
        return action

    def built(self) -> BuiltMenu:
        return self.menu, self.actions


def exec_menu(built: BuiltMenu | None, global_pos: QPoint) -> None:
    """Show *built* at *global_pos* and run the chosen row's handler."""
    if built is None:
        return
    menu, actions = built
    chosen = menu.exec(global_pos)
    handler = actions.get(chosen) if chosen is not None else None
    if handler is not None:
        handler()
