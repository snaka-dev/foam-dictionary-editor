# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Where the editor<->tree sync commands live: the bottom tab bar and the Case menu.

The buttons ride the bottom tab bar rather than sitting inside a tab page.
Putting them in the tree container or the editor page would hide them whenever
the user switched to the Boundary/BlockMesh or Terminal tab -- and
apply_text_to_tree is still meaningful there, being what refreshes the BlockMesh
overlays.  A corner widget on bottom_tabs sits on the seam between the two panes
while staying visible for every tab selection.

The Case menu duplicates both, and gives Apply Text to Tree a shortcut.  Reload
from Tree is left without one on purpose: it overwrites the editor text.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import QMenu, QPushButton, QToolBar


def _sync_buttons(win):
    """The corner widget and its two sync buttons.

    The pane-minimize button shares the same bar (see test_pane_minimize.py), so
    it is filtered out here rather than left to shift the positional unpacking.
    """
    corner = win.bottom_tabs.cornerWidget(Qt.Corner.TopRightCorner)
    assert corner is not None, "no corner widget on the bottom tab bar"
    buttons = [
        b for b in corner.findChildren(QPushButton)
        if b is not getattr(win, "_bottom_minimize_btn", None)
    ]
    return corner, buttons


class TestTreeTextSyncBar:
    def test_buttons_live_on_the_bottom_tab_bar_corner(self, main_window):
        _, buttons = _sync_buttons(main_window)
        assert [b.text() for b in buttons] == [
            "▲ Apply Text to Tree",
            "▼ Reload from Tree",
        ]
        # The arrows only read correctly if the tree really is the upper pane.
        assert main_window.right_splitter.indexOf(main_window.upper_tabs) < \
            main_window.right_splitter.indexOf(main_window.bottom_tabs)

    def test_buttons_are_outside_every_tab_page(self, main_window):
        corner, _ = _sync_buttons(main_window)
        for page in (main_window.editor_panel, main_window.upper_tabs):
            assert not page.isAncestorOf(corner), (
                "sync bar nested in a tab page -- it would vanish on tab switch"
            )

    def test_buttons_survive_a_bottom_tab_switch(self, main_window):
        corner, buttons = _sync_buttons(main_window)
        for index in range(main_window.bottom_tabs.count()):
            main_window.bottom_tabs.setCurrentIndex(index)
            assert main_window.bottom_tabs.cornerWidget(Qt.Corner.TopRightCorner) is corner
            assert all(not b.isHidden() for b in buttons)

    def test_buttons_are_wired_to_the_sync_commands(self, qapp, monkeypatch):
        # The connections are bound during __init__, so the methods have to be
        # patched on the class before the window is built for the click to be a
        # real test of the wiring rather than of a re-connection made here.
        from app_config import get_app_config
        from ui.main_window import MainWindow

        cfg = get_app_config()
        original = {name: cfg.get_feature(name) for name in ("terminal", "blockmesh")}
        cfg.set_feature("terminal", False)
        cfg.set_feature("blockmesh", False)

        called: list[str] = []
        monkeypatch.setattr(MainWindow, "apply_text_to_tree", lambda self: called.append("apply"))
        monkeypatch.setattr(
            MainWindow, "reload_text_from_tree", lambda self: called.append("reload")
        )
        win = MainWindow()
        try:
            _, (apply_btn, reload_btn) = _sync_buttons(win)
            apply_btn.click()
            reload_btn.click()
            assert called == ["apply", "reload"]
        finally:
            win._file_list_refresh_timer.stop()
            win.close()
            for name, value in original.items():
                cfg.set_feature(name, value)

    def test_case_menu_carries_both_commands(self, main_window):
        menu = next(
            m for m in main_window.menuBar().findChildren(QMenu) if m.title() == "Case"
        )
        actions = {a.text(): a for a in menu.actions() if a.text()}
        assert "Apply Text to Tree" in actions
        assert "Reload from Tree" in actions
        assert actions["Apply Text to Tree"].shortcut() == QKeySequence("Ctrl+Shift+A")
        # Reload from Tree overwrites the editor text, discarding edits not yet
        # applied, so it is menu-only on purpose.
        assert actions["Reload from Tree"].shortcut().isEmpty()

    def test_apply_shortcut_collides_with_nothing(self, main_window):
        apply_key = QKeySequence("Ctrl+Shift+A")
        clashing = [
            a.text()
            for a in main_window.findChildren(QAction)
            if a.shortcut() == apply_key and a.text() != "Apply Text to Tree"
        ]
        clashing += [
            s.key().toString()
            for s in main_window.findChildren(QShortcut)
            if s.key() == apply_key
        ]
        assert clashing == []

    def test_shortcuts_dialog_lists_the_apply_shortcut(self):
        from ui.dialogs.keyboard_shortcuts_dialog import _SECTIONS_DATA

        listed = {action: key for _, rows in _SECTIONS_DATA for action, key in rows}
        assert listed.get("Apply Text to Tree") == "Ctrl+Shift+A"

    def test_top_bar_no_longer_carries_them(self, main_window):
        """The old QPushButton-based top bar carried neither command, and its
        QToolBar replacement (see ui/main_window.py's _build_top_bar) still
        doesn't -- asserted against the toolbar's own actions rather than
        against centralWidget(), since a QToolBar added via addToolBar() sits
        outside the central widget and the original assertion would now pass
        vacuously (the QPushButton set it searched is unconditionally empty).
        """
        toolbar = main_window.findChild(QToolBar, "action_toolbar")
        assert toolbar is not None
        toolbar_texts = {a.text() for a in toolbar.actions()}
        assert "Apply Text to Tree" not in toolbar_texts
        assert "Reload from Tree" not in toolbar_texts
