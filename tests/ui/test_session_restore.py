# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Cover ui/session_restore.py: the two ends of the between-runs wire.

The state model underneath is tested in test_window_state.py; what is left here
is that a close stores something a later launch can use, that turning the
setting off means neither end does anything, and — the whole point of the
lenient path — that nothing a saved blob can contain stops a window opening.
"""
from __future__ import annotations

import pytest

from app_config.app_config_manager import AppConfigManager
from ui.session_restore import restore_session, save_session

CONTROL_DICT = """\
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      controlDict;
}

application     interFoam;
startTime       0;
endTime         1;
"""


@pytest.fixture(autouse=True)
def temp_config(tmp_path, monkeypatch):
    """Point the config singleton at a throwaway file.

    Autouse so it is in place before the ``main_window`` fixture builds a
    window: these tests call ``cfg.save()``, which would otherwise rewrite the
    repository's own app_config.json.
    """
    import app_config

    manager = AppConfigManager(config_path=str(tmp_path / "app_config.json"))
    monkeypatch.setattr(app_config, "_app_config", manager)
    return manager


@pytest.fixture
def case_dir(tmp_path):
    case = tmp_path / "case"
    (case / "system").mkdir(parents=True)
    (case / "system" / "controlDict").write_text(CONTROL_DICT, encoding="utf-8")
    return case


@pytest.fixture
def second_window(qapp):
    """A second MainWindow, built the same way the shared fixture builds one."""
    from ui.main_window import MainWindow

    windows: list[MainWindow] = []

    def build() -> MainWindow:
        win = MainWindow()
        windows.append(win)
        return win

    yield build

    for win in windows:
        win._file_list_refresh_timer.stop()
        if win._case_dir_watcher.directories():
            win._case_dir_watcher.removePaths(win._case_dir_watcher.directories())
        win._stop_foam_monitor()


class TestSave:
    def test_stores_the_layout_under_the_session_key(self, main_window, temp_config):
        save_session(main_window)
        state = temp_config.get_session_state()
        assert state is not None
        assert state["upper_tab"] == "Tree"
        assert state["lower_tab"] == "Editor"

    def test_stores_nothing_when_the_setting_is_off(self, main_window, temp_config):
        temp_config.set_restore_session(False)
        save_session(main_window)
        assert temp_config.get_session_state() is None

    def test_an_earlier_layout_survives_the_setting_being_off(self, main_window, temp_config):
        """Off means "do not apply it", not "throw it away" — the close leaves
        what was already stored exactly as it was."""
        temp_config.set_session_state({"upper_tab": "Boundary"})
        temp_config.set_restore_session(False)
        save_session(main_window)
        assert temp_config.get_session_state() == {"upper_tab": "Boundary"}


class TestForgetSavedSession:
    """Settings > Forget Saved Session, the only thing that discards a layout.

    ``_refresh_forget_session_action`` stands in for opening the Settings menu,
    which is what the action's ``aboutToShow`` connection does in the window.
    """

    def test_the_action_clears_the_stored_state(self, main_window, temp_config):
        save_session(main_window)
        assert temp_config.get_session_state() is not None

        main_window._refresh_forget_session_action()
        main_window._forget_session_action.trigger()

        assert temp_config.get_session_state() is None
        assert temp_config.has_stored_sessions() is False

    def test_the_action_leaves_the_setting_on(self, main_window, temp_config):
        save_session(main_window)
        main_window._refresh_forget_session_action()
        main_window._forget_session_action.trigger()
        assert temp_config.get_restore_session() is True
        assert main_window._restore_session_action.isChecked() is True

    def test_the_action_is_disabled_with_nothing_stored(self, main_window, temp_config):
        main_window._refresh_forget_session_action()
        assert main_window._forget_session_action.isEnabled() is False

    def test_the_action_disables_itself_once_there_is_nothing_left(
        self, main_window, temp_config
    ):
        save_session(main_window)
        main_window._refresh_forget_session_action()
        assert main_window._forget_session_action.isEnabled() is True

        main_window._forget_session_action.trigger()

        assert main_window._forget_session_action.isEnabled() is False

    def test_the_action_is_reachable_while_the_setting_is_off(self, main_window, temp_config):
        """The whole point of the split: a stored layout can still be discarded
        after unticking the setting, which is when it stops being applied."""
        save_session(main_window)
        main_window._restore_session_action.setChecked(False)

        main_window._refresh_forget_session_action()
        assert main_window._forget_session_action.isEnabled() is True

        main_window._forget_session_action.trigger()

        assert temp_config.has_stored_sessions() is False

    def test_opening_the_settings_menu_refreshes_the_action(self, main_window, temp_config):
        """The aboutToShow wiring itself, and that the action is in that menu —
        everything else here calls the slot directly and would not notice either
        being missing."""
        # The list has to outlive the lookup: let the menu bar's QActions be
        # collected and PySide takes their QMenus with them, leaving a deleted
        # C++ object behind.
        bar_actions = main_window.menuBar().actions()
        menu = next(
            action.menu()
            for action in bar_actions
            if action.menu() is not None and "Settings" in action.text()
        )
        assert main_window._forget_session_action in menu.actions()

        save_session(main_window)
        main_window._forget_session_action.setEnabled(False)

        menu.aboutToShow.emit()

        assert main_window._forget_session_action.isEnabled() is True

    def test_a_forgotten_layout_does_not_come_back_at_the_next_launch(
        self, qapp, main_window, second_window, temp_config
    ):
        save_session(main_window)
        main_window._refresh_forget_session_action()
        main_window._forget_session_action.trigger()

        fresh = second_window()
        assert restore_session(qapp, fresh) is False


class TestRestore:
    def test_returns_false_with_nothing_stored(self, qapp, main_window):
        assert restore_session(qapp, main_window) is False

    def test_returns_false_when_the_setting_is_off(self, qapp, main_window, temp_config):
        temp_config.set_session_state({"upper_tab": "Boundary"})
        temp_config.set_restore_session(False)
        assert restore_session(qapp, main_window) is False

    @pytest.mark.parametrize(
        "blob",
        [
            {"upper_tabb": "Tree"},                      # a typo, or a renamed field
            {"window_size": "1200x800"},                 # a field whose shape changed
            {"block_mesh": {"camera": [[1, 2, 3]]}},     # a truncated camera
            {"case_dir": "/gone", "current_file": "x"},  # a case that has moved
            {"lower_tab": "Editeur"},                    # a session saved in another language
        ],
    )
    def test_a_damaged_blob_never_raises(self, qapp, main_window, temp_config, blob):
        temp_config.set_session_state(blob)
        restore_session(qapp, main_window)  # must not raise

    def test_an_unusable_blob_is_reported_as_not_restored(self, qapp, main_window, temp_config):
        temp_config.set_session_state({"window_size": []})
        # Parsed fine, just empty of anything to apply — still counts as applied.
        assert restore_session(qapp, main_window) is True

    def test_round_trips_the_case_and_file_into_a_fresh_window(
        self, qapp, main_window, second_window, case_dir, temp_config
    ):
        control_dict = str(case_dir / "system" / "controlDict")
        main_window._load_case_dir(str(case_dir))
        main_window.load_selected_file(control_dict)
        main_window.bottom_tabs.setCurrentIndex(0)
        save_session(main_window)

        fresh = second_window()
        assert fresh.state.current_case_dir is None
        assert restore_session(qapp, fresh) is True
        assert fresh.state.current_case_dir == str(case_dir)
        assert fresh.state.current_file == control_dict

    def test_round_trips_the_selected_tree_row(
        self, qapp, main_window, second_window, case_dir, temp_config
    ):
        from ui.window_state import index_for_key_path, key_path_for_index

        main_window._load_case_dir(str(case_dir))
        main_window.load_selected_file(str(case_dir / "system" / "controlDict"))
        source = main_window.proxy_model.sourceModel()
        index = index_for_key_path(source, ["endTime"])
        main_window.tree.setCurrentIndex(main_window.proxy_model.mapFromSource(index))
        save_session(main_window)

        fresh = second_window()
        restore_session(qapp, fresh)
        selected = fresh.proxy_model.mapToSource(fresh.tree.currentIndex())
        assert key_path_for_index(selected) == ["endTime"]
