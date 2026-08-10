# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""One-click minimize/restore for the file list, Detail pane and editor row.

The two styles are not interchangeable and the tests say why: the Detail pane
and the file list collapse to nothing through setSizes, while the editor row is
pinned to a strip, because its splitter sets setCollapsible(..., False) and under
that flag setSizes clamps to the tab widget's minimumSizeHint instead of
collapsing.  The strip is also what keeps the tab bar -- and the editor<->tree
sync buttons riding its corner -- on screen while the row is minimized.
"""

from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QSplitter, QTextEdit

from ui.pane_minimize import PANE_BOTTOM, PANE_DETAIL, PANE_FILE_LIST, PaneMinimizer


def _double_click(app, splitter, handle_index):
    handle = splitter.handle(handle_index)
    app.sendEvent(
        handle,
        QMouseEvent(
            QEvent.Type.MouseButtonDblClick,
            QPoint(3, 3),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        ),
    )


class TestPaneMinimizer:
    """The mechanism on its own, with a plain splitter and no MainWindow."""

    def _splitter(self, qapp, sizes=(300, 500)):
        splitter = QSplitter(Qt.Orientation.Horizontal)
        for _ in sizes:
            splitter.addWidget(QTextEdit())
        splitter.resize(sum(sizes), 400)
        splitter.show()
        qapp.processEvents()
        splitter.setSizes(list(sizes))
        qapp.processEvents()
        return splitter

    def test_collapse_and_restore_round_trip(self, qapp):
        splitter = self._splitter(qapp)
        before = splitter.sizes()
        minimizer = PaneMinimizer(splitter, 0)
        minimizer.minimize()
        qapp.processEvents()
        assert splitter.sizes()[0] == 0
        assert minimizer.minimized
        minimizer.restore()
        qapp.processEvents()
        assert splitter.sizes() == before
        assert not minimizer.minimized

    def test_minimizing_twice_does_not_forget_the_restore_size(self, qapp):
        splitter = self._splitter(qapp)
        width = splitter.sizes()[0]  # not 300: the handles come out of the total
        minimizer = PaneMinimizer(splitter, 0)
        minimizer.minimize()
        minimizer.minimize()  # would otherwise remember the collapsed size
        assert minimizer.restore_size == width

    def test_restore_size_of_zero_falls_back_to_the_default(self, qapp):
        minimizer = PaneMinimizer(self._splitter(qapp), 0, default_size=180)
        minimizer.restore_size = 0
        assert minimizer.restore_size == 180

    def test_strip_style_pins_the_widget_maximum(self, qapp):
        splitter = self._splitter(qapp)
        before = splitter.sizes()
        minimizer = PaneMinimizer(splitter, 1, strip=lambda: 24)
        minimizer.minimize()
        qapp.processEvents()
        assert splitter.widget(1).maximumWidth() == 24
        assert splitter.sizes()[1] == 24
        minimizer.restore()
        qapp.processEvents()
        # Released, not left clamped -- otherwise the pane could never grow.
        assert splitter.widget(1).maximumWidth() > 24
        assert splitter.sizes() == before

    def test_freed_space_goes_to_the_other_panes(self, qapp):
        splitter = self._splitter(qapp, sizes=(200, 300, 300))
        total = sum(splitter.sizes())
        PaneMinimizer(splitter, 0).minimize()
        qapp.processEvents()
        sizes = splitter.sizes()
        assert sizes[0] == 0
        assert sum(sizes) == total
        # Proportional, so the two survivors keep their relative widths.
        assert sizes[1] == sizes[2]


class TestPanesInTheWindow:
    def test_all_three_panes_are_registered(self, main_window):
        assert set(main_window._pane_minimizers) == {
            PANE_FILE_LIST, PANE_DETAIL, PANE_BOTTOM
        }

    def test_view_menu_actions_are_checked_when_the_pane_is_shown(self, main_window):
        actions = main_window._pane_actions
        assert set(actions) == {PANE_FILE_LIST, PANE_DETAIL, PANE_BOTTOM}
        assert all(a.isChecked() for a in actions.values())
        assert [a.shortcut().toString() for a in actions.values()] == [
            "Ctrl+1", "Ctrl+2", "Ctrl+3"
        ]

    def test_unchecking_the_action_minimizes_and_rechecking_restores(self, main_window, qapp):
        splitter = main_window.right_upper_splitter
        before = splitter.sizes()
        main_window._pane_actions[PANE_DETAIL].setChecked(False)
        qapp.processEvents()
        assert splitter.sizes()[2] == 0
        main_window._pane_actions[PANE_DETAIL].setChecked(True)
        qapp.processEvents()
        assert splitter.sizes()[2] == before[2]

    def test_repeated_cycles_do_not_drift(self, main_window, qapp):
        """The pane comes back to the same place however often it is toggled.

        Qt's own distribution loses a pixel from the row the first time round --
        the hidden comparison pane's handle is in the arithmetic -- and there is
        no arguing with that. What must not happen is a pixel *per cycle*, which
        is what rebuilding the row from a single remembered width would cost;
        the whole row is remembered instead, so the second cycle and the tenth
        land on the same sizes as the first.
        """
        splitter = main_window.right_upper_splitter
        seen = []
        for _ in range(4):
            main_window.set_pane_minimized(PANE_DETAIL, True)
            qapp.processEvents()
            main_window.set_pane_minimized(PANE_DETAIL, False)
            qapp.processEvents()
            seen.append(splitter.sizes())
        assert seen[1:] == seen[:-1]

    def test_minimizing_syncs_the_action_without_recursing(self, main_window, qapp):
        main_window.set_pane_minimized(PANE_FILE_LIST, True)
        qapp.processEvents()
        assert not main_window._pane_actions[PANE_FILE_LIST].isChecked()
        assert main_window.main_splitter.sizes()[0] == 0
        main_window.set_pane_minimized(PANE_FILE_LIST, False)
        qapp.processEvents()
        assert main_window._pane_actions[PANE_FILE_LIST].isChecked()

    def test_bottom_row_minimizes_to_its_tab_bar_not_to_nothing(self, main_window, qapp):
        tabs = main_window.bottom_tabs
        main_window.set_pane_minimized(PANE_BOTTOM, True)
        qapp.processEvents()
        height = main_window.right_splitter.sizes()[1]
        assert 0 < height <= tabs.tabBar().sizeHint().height() + 2
        # The point of the strip: the tabs and the sync buttons stay reachable.
        # isHidden rather than isVisible -- the fixture never shows the window,
        # so nothing in it is "visible" in Qt's sense.
        assert not tabs.tabBar().isHidden()
        assert not tabs.cornerWidget(Qt.Corner.TopRightCorner).isHidden()

    def test_bottom_button_toggles_and_relabels(self, main_window, qapp):
        button = main_window._bottom_minimize_btn
        first = button.text()
        button.click()
        qapp.processEvents()
        assert main_window._pane_minimizers[PANE_BOTTOM].minimized
        assert button.text() != first
        button.click()
        qapp.processEvents()
        assert not main_window._pane_minimizers[PANE_BOTTOM].minimized
        assert button.text() == first

    def test_handle_double_click_toggles_the_adjacent_pane(self, main_window, qapp):
        _double_click(qapp, main_window.right_splitter, 1)
        qapp.processEvents()
        assert main_window._pane_minimizers[PANE_BOTTOM].minimized
        _double_click(qapp, main_window.right_splitter, 1)
        qapp.processEvents()
        assert not main_window._pane_minimizers[PANE_BOTTOM].minimized

    def test_handle_with_no_minimizable_neighbour_is_ignored(self, main_window, qapp):
        # right_upper handle 1 sits between the tree and the comparison pane;
        # only the Detail pane at index 2 is registered.
        _double_click(qapp, main_window.right_upper_splitter, 1)
        qapp.processEvents()
        assert not any(m.minimized for m in main_window._pane_minimizers.values())


class TestSideBySideAutoMinimize:
    def test_entering_side_by_side_parks_the_detail_pane(self, main_window, qapp):
        main_window._auto_minimize_detail_for_side_by_side(True)
        qapp.processEvents()
        assert main_window._pane_minimizers[PANE_DETAIL].minimized
        main_window._auto_minimize_detail_for_side_by_side(False)
        qapp.processEvents()
        assert not main_window._pane_minimizers[PANE_DETAIL].minimized

    def test_a_pane_the_user_minimized_first_stays_minimized(self, main_window, qapp):
        main_window.set_pane_minimized(PANE_DETAIL, True)
        main_window._auto_minimize_detail_for_side_by_side(True)
        main_window._auto_minimize_detail_for_side_by_side(False)
        qapp.processEvents()
        assert main_window._pane_minimizers[PANE_DETAIL].minimized


class TestPersistence:
    def test_capture_records_only_minimized_panes(self, main_window, qapp):
        from ui.window_state import capture_window_state

        assert capture_window_state(main_window).minimized_panes == {}
        main_window.set_pane_minimized(PANE_DETAIL, True)
        qapp.processEvents()
        captured = capture_window_state(main_window)
        assert set(captured.minimized_panes) == {PANE_DETAIL}
        assert captured.minimized_panes[PANE_DETAIL] > 0

    def test_round_trip_keeps_the_size_to_restore_to(self, main_window, qapp):
        from ui.window_state import WindowState, apply_window_state, capture_window_state

        main_window.set_pane_minimized(PANE_DETAIL, True)
        qapp.processEvents()
        remembered = main_window._pane_minimizers[PANE_DETAIL].restore_size
        state = WindowState.from_dict(capture_window_state(main_window).to_dict())
        assert state.minimized_panes[PANE_DETAIL] == remembered

        main_window.set_pane_minimized(PANE_DETAIL, False)
        qapp.processEvents()
        apply_window_state(main_window, state)
        qapp.processEvents()
        minimizer = main_window._pane_minimizers[PANE_DETAIL]
        assert minimizer.minimized
        # The restore size survives the trip: it is written after minimizing,
        # which would otherwise record the collapsed size the blob restored.
        assert minimizer.restore_size == remembered

    def test_lenient_apply_notes_an_unknown_pane(self, main_window):
        from ui.window_state import WindowState, apply_window_state

        notes = apply_window_state(
            main_window, WindowState(minimized_panes={"nope": 100}), strict=False
        )
        assert any("nope" in note for note in notes)
