# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""The main action toolbar (Open/Save/Reload Case + Case/File labels).

Regression coverage for the "the top bar looks like a tab bar" report: a plain
QHBoxLayout of QPushButtons, stacked into the central widget's own layout
right above upper_tabs, drew as a row of same-height bordered rectangles under
Fusion -- indistinguishable from the tab bar directly below it. The fix is a
real QToolBar added via QMainWindow.addToolBar rather than a layout inside the
central widget: its QToolButtons default to autoRaise and so paint flat until
hovered, which a QPushButton never does regardless of what surrounds it.

See ui/main_window.py's _build_top_bar / _build_shared_actions / createPopupMenu.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QAbstractButton, QLabel, QMenu, QToolBar

from ui.fonts import icon_pixel_size


def _toolbar(main_window) -> QToolBar:
    toolbar = main_window.findChild(QToolBar, "action_toolbar")
    assert toolbar is not None, "no QToolBar named 'action_toolbar' on the window"
    return toolbar


def _case_menu(main_window) -> QMenu:
    return next(
        m for m in main_window.menuBar().findChildren(QMenu) if m.title() == "Case"
    )


class TestActionToolbar:
    def test_is_a_real_toolbar_docked_at_the_top(self, main_window):
        toolbar = _toolbar(main_window)
        assert isinstance(toolbar, QToolBar)
        assert main_window.toolBarArea(toolbar) == Qt.ToolBarArea.TopToolBarArea
        assert toolbar.isMovable() is False
        assert toolbar.isFloatable() is False

    def test_toolbar_is_outside_the_central_widget(self, main_window):
        """The original complaint, as a regression guard.

        A QToolBar added via addToolBar() docks against the QMainWindow
        itself, not against centralWidget() -- the earlier QHBoxLayout-based
        top bar lived *inside* the central widget's own layout, which is
        exactly what made it draw flush against upper_tabs one row below.
        """
        toolbar = _toolbar(main_window)
        assert not main_window.centralWidget().isAncestorOf(toolbar)

    def test_toolbar_style_and_icon_size(self, main_window):
        toolbar = _toolbar(main_window)
        assert toolbar.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        assert toolbar.iconSize().width() == icon_pixel_size()

    def test_toolbar_actions_are_the_case_menu_actions(self, main_window):
        """Identity, not equality: this is what buys enabled-state and label
        sync between the toolbar and the Case menu for free."""
        toolbar = _toolbar(main_window)
        case_menu = _case_menu(main_window)
        toolbar_by_text = {a.text(): a for a in toolbar.actions() if a.text()}
        case_by_text = {a.text(): a for a in case_menu.actions() if a.text()}
        for label in ("Open Case…", "Save File", "Save Case", "Reload Case"):
            assert label in toolbar_by_text, f"{label!r} missing from the toolbar"
            assert label in case_by_text, f"{label!r} missing from the Case menu"
            assert toolbar_by_text[label] is case_by_text[label], (
                f"toolbar's {label!r} action is not the same object as the Case menu's"
            )

    def test_create_popup_menu_is_disabled(self, main_window):
        """QMainWindow's built-in toolbar/dock right-click menu is disabled.

        Its only entry with no dock widgets present would be hiding
        action_toolbar, with no obvious way to bring it back.
        """
        assert main_window.createPopupMenu() is None

    def test_case_and_file_labels_still_update(self, main_window, tmp_path):
        """current_case_label / current_file_label keep their names and still
        respond to _update_case_label / _update_file_label after moving onto
        the toolbar."""
        assert main_window.current_case_label.text() == "-"
        assert main_window.current_file_label.text() == "-"

        main_window.state.current_case_dir = str(tmp_path)
        main_window._update_case_label()
        assert main_window.current_case_label.text() == tmp_path.name

        case_file = tmp_path / "controlDict"
        main_window.state.current_file = str(case_file)
        main_window._update_file_label()
        assert "controlDict" in main_window.current_file_label.text()

    def test_no_save_all_files_string_survives(self, main_window):
        """"Save All Files" is dead: one shared QAction forces a single label
        ("Save Case") for both the toolbar and the Case menu."""
        forbidden = "Save All Files"
        texts = [a.text() for a in main_window.findChildren(QAction)]
        texts += [b.text() for b in main_window.findChildren(QAbstractButton)]
        texts += [lbl.text() for lbl in main_window.findChildren(QLabel)]
        assert forbidden not in texts
        tooltips = [a.toolTip() for a in main_window.findChildren(QAction)]
        assert forbidden not in tooltips

    def test_toolbar_actions_are_wired_to_the_commands(self, qapp, monkeypatch):
        # Patched on the class before construction -- see
        # test_tree_text_sync_bar.py::test_buttons_are_wired_to_the_sync_commands
        # for why: the connections are made during __init__, so a patch applied
        # to an already-built window would not be exercised by the trigger below.
        from app_config import get_app_config
        from ui.main_window import MainWindow

        cfg = get_app_config()
        original = {name: cfg.get_feature(name) for name in ("terminal", "blockmesh")}
        cfg.set_feature("terminal", False)
        cfg.set_feature("blockmesh", False)

        called: list[str] = []
        monkeypatch.setattr(MainWindow, "open_case", lambda self: called.append("open_case"))
        monkeypatch.setattr(MainWindow, "save_file", lambda self: called.append("save_file"))
        monkeypatch.setattr(
            MainWindow, "save_all_files", lambda self: called.append("save_all_files")
        )
        monkeypatch.setattr(MainWindow, "reload_case", lambda self: called.append("reload_case"))
        win = MainWindow()
        try:
            toolbar = _toolbar(win)
            by_text = {a.text(): a for a in toolbar.actions() if a.text()}
            by_text["Open Case…"].trigger()
            by_text["Save File"].trigger()
            by_text["Save Case"].trigger()
            by_text["Reload Case"].trigger()
            assert called == ["open_case", "save_file", "save_all_files", "reload_case"]
        finally:
            win._file_list_refresh_timer.stop()
            win.close()
            for name, value in original.items():
                cfg.set_feature(name, value)
