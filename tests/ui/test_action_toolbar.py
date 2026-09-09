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

from contextlib import contextmanager

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import QAbstractButton, QApplication, QLabel, QMenu, QToolBar

from i18n import get_language, set_language, tr
from ui.fonts import button_pixel_width, icon_pixel_size


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


class TestPinnedButtonWidths:
    """A handful of pinned buttons on MainWindow and file_list_panel used to
    ``setFixedWidth`` a bare figure, which caps as well as floors -- see
    ui/fonts.py's ``button_pixel_width`` and DEVELOPER.md's "setFixedWidth is
    a cap, not a starting width". Built at a large application font, where
    each figure was already tight, and the blockmesh feature enabled so the
    side-by-side corner button exists to check.
    """

    @contextmanager
    def _window(self, *, font_point_size: int, language: str):
        """Build a MainWindow at *font_point_size* in *language*, restoring after.

        A context manager rather than a returned cleanup callable: the font,
        language and feature flags are process-global, and they are mutated
        before MainWindow() runs. Handing the caller a cleanup to invoke would
        leak all three into every later test in the session if construction
        itself raised, since the caller's try/finally is not entered until
        after the call returns.
        """
        from app_config import get_app_config
        from ui.main_window import MainWindow

        cfg = get_app_config()
        original = {name: cfg.get_feature(name) for name in ("terminal", "blockmesh")}
        previous_font = QApplication.font()
        previous_language = get_language()
        win = None
        try:
            cfg.set_feature("terminal", False)
            cfg.set_feature("blockmesh", True)
            QApplication.setFont(QFont("Sans Serif", font_point_size))
            set_language(language)
            win = MainWindow()
            yield win
        finally:
            if win is not None:
                win._file_list_refresh_timer.stop()
                win.close()
            QApplication.setFont(previous_font)
            set_language(previous_language)
            for name, value in original.items():
                cfg.set_feature(name, value)

    def _clear_button(self, win) -> QAbstractButton:
        text = tr("Clear")
        return next(b for b in win.findChildren(QAbstractButton) if b.text() == text)

    def test_no_pinned_button_is_capped_below_its_own_text_at_16pt(
        self, qapp, temp_config  # noqa: ARG002 (qapp/temp_config needed for construction)
    ):
        with self._window(font_point_size=16, language="en") as win:
            assert win._bottom_minimize_btn.maximumWidth() >= button_pixel_width(
                win._bottom_minimize_btn.text()
            )
            assert win._bm_side_by_side_btn is not None
            assert win._bm_side_by_side_btn.maximumWidth() >= button_pixel_width(
                win._bm_side_by_side_btn.text()
            )
            clear_btn = self._clear_button(win)
            assert clear_btn.maximumWidth() >= button_pixel_width(clear_btn.text())
            refresh_btn = win.file_list_panel._refresh_btn
            assert refresh_btn.maximumWidth() >= button_pixel_width(refresh_btn.text())

    def test_the_japanese_clear_label_is_not_capped_either(
        self, qapp, temp_config  # noqa: ARG002 (qapp/temp_config needed for construction)
    ):
        # クリア is 11 px wider than "Clear" and hits a shared cap first.
        with self._window(font_point_size=16, language="ja") as win:
            clear_btn = self._clear_button(win)
            assert clear_btn.text() != "Clear"
            assert clear_btn.maximumWidth() >= button_pixel_width(clear_btn.text())
