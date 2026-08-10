# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Help > Keyboard Shortcuts stays honest, and stays on screen.

The list is a hand-written table, so nothing stopped it drifting from the
shortcuts the window actually installs — Ctrl+S was bound with no menu item and
no entry here for several releases. `TestCoverage` closes that gap. The rest
guards the layout: the table had grown to a height no small display could show,
and a QDialog with no scroll area cannot be resized below its content.
"""
from __future__ import annotations

import pytest
from PySide6.QtGui import QAction, QGuiApplication, QKeySequence
from PySide6.QtWidgets import QGroupBox

from ui.dialogs.keyboard_shortcuts_dialog import (
    _COLUMNS,
    _SCREEN_FRACTION,
    _SECTIONS_DATA,
    KeyboardShortcutsDialog,
    _split_into_columns,
)


def _portable(sequence: QKeySequence) -> str:
    return sequence.toString(QKeySequence.PortableText)


def _documented() -> set[str]:
    """Every key sequence the dialog spells out, normalised.

    Rows describing a mouse gesture ("Ctrl + scroll wheel") or an action rather
    than a key ("Double-click its splitter handle") do not parse to a sequence
    and drop out; that is fine, since this set is only ever used as the thing a
    real shortcut must be found in.
    """
    documented = set()
    for _section, rows in _SECTIONS_DATA:
        for _action, keys in rows:
            for part in keys.split(" or "):
                text = _portable(QKeySequence(part.strip()))
                if text:
                    documented.add(text)
    return documented


def _installed(window) -> dict[str, str]:
    """Key sequence → what installed it, for every shortcut under *window*.

    Covers both ways the app binds a key: a ``QShortcut`` (the tree's copy/paste
    and undo, the editor's find and zoom) and a ``QAction`` shortcut (everything
    on the menu bar). ``findChildren`` is recursive, so menu actions two levels
    down the menu bar are included.
    """
    from PySide6.QtGui import QShortcut

    found: dict[str, str] = {}
    for shortcut in window.findChildren(QShortcut):
        text = _portable(shortcut.key())
        if text:
            found.setdefault(text, f"QShortcut on {type(shortcut.parent()).__name__}")
    for action in window.findChildren(QAction):
        for sequence in action.shortcuts():
            text = _portable(sequence)
            if text:
                found.setdefault(text, f"QAction {action.text()!r}")
    return found


class TestCoverage:
    def test_every_installed_shortcut_is_documented(self, main_window):
        missing = {
            keys: origin
            for keys, origin in _installed(main_window).items()
            if keys not in _documented()
        }
        assert not missing, (
            "shortcuts the window installs but Help > Keyboard Shortcuts does "
            f"not list: {missing}"
        )

    def test_save_file_is_listed(self):
        assert "Ctrl+S" in _documented()

    def test_save_file_is_on_the_case_menu(self, main_window):
        """USER_GUIDE.md documents Ctrl+S as *Case > Save File*.

        It was a bare window-level QShortcut, so the menu bar advertised nothing
        and the only hint was the file list's context menu.
        """
        actions = {
            action.text(): action
            for action in main_window.findChildren(QAction)
        }
        assert "Save File" in actions
        assert _portable(actions["Save File"].shortcut()) == "Ctrl+S"


class TestTranslated:
    """Every string in the table has Japanese, and keeps it.

    Ten of them did not — Find, Undo, Cut, Copy Value and friends rendered in
    English inside an otherwise translated dialog. tests/test_i18n.py checks
    ja.py only for duplicate keys, so nothing noticed. This is deliberately
    scoped to this one dialog rather than every tr() call in the app.
    """

    def test_no_section_or_row_is_untranslated(self):
        from i18n.ja import TRANSLATIONS

        untranslated = [
            text
            for section, rows in _SECTIONS_DATA
            for text in (section, *(action for action, _keys in rows))
            if text not in TRANSLATIONS
        ]
        assert not untranslated, f"no Japanese for: {untranslated}"


class TestColumns:
    def test_every_section_is_placed_exactly_once(self):
        columns = _split_into_columns(_SECTIONS_DATA)
        placed = [section for column in columns for section in column]
        assert placed == _SECTIONS_DATA

    def test_no_column_is_left_empty(self):
        assert all(_split_into_columns(_SECTIONS_DATA))

    def test_the_columns_are_roughly_balanced(self):
        rows = [
            sum(len(shortcuts) for _name, shortcuts in column)
            for column in _split_into_columns(_SECTIONS_DATA)
        ]
        assert max(rows) - min(rows) <= max(len(s) for _n, s in _SECTIONS_DATA)

    def test_the_grid_holds_every_group(self, qapp):  # noqa: ARG002
        dialog = KeyboardShortcutsDialog()
        assert len(dialog.findChildren(QGroupBox)) == len(_SECTIONS_DATA)


class TestFitsASmallDisplay:
    @pytest.fixture
    def dialog(self, qapp):  # noqa: ARG002
        dialog = KeyboardShortcutsDialog()
        dialog.show()
        yield dialog
        dialog.close()

    def test_it_can_be_resized_far_below_its_content(self, dialog):
        """The point of the scroll area.

        Without it the layout's minimum *is* the dialog's, so a list taller than
        the screen hangs off the bottom with the Close button on it.
        """
        content = dialog._content.sizeHint().height()
        assert dialog.minimumSizeHint().height() < content / 2

    def test_two_columns_are_shorter_than_one(self, dialog):
        one_column = sum(
            group.sizeHint().height() for group in dialog.findChildren(QGroupBox)
        )
        assert dialog._content.sizeHint().height() < one_column * 0.8

    def test_it_opens_no_larger_than_the_screen_allows(self, dialog):
        available = QGuiApplication.primaryScreen().availableGeometry()
        assert dialog.height() <= int(available.height() * _SCREEN_FRACTION) + 1
        assert dialog.width() <= int(available.width() * _SCREEN_FRACTION) + 1

    def test_close_stays_outside_the_scrolled_area(self, dialog):
        assert dialog._buttons.parent() is dialog
        assert dialog._scroll.widget() is dialog._content
        assert _COLUMNS >= 2
