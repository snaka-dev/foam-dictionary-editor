# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Integration tests for the Case Browser's interaction with MainWindow state.

Covers CASE_BROWSER_PLAN.md section 2's governing rule: path-keyed application
state is never rewritten in place, it is discarded and rebuilt through
_load_case_dir(). That rule is what makes rename/move of the open case safe,
what _close_case() (delete's inverse) has to clear, and what makes an
operation on an *ancestor* of the open case a hard refusal rather than
something the code would otherwise have to reconcile in place.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QMessageBox

from services.case_files_config import CaseFilesConfig
from ui.mixins import _case_ops, _ui_ops


def _make_case(tmp_path: Path, name: str = "case") -> Path:
    case_dir = tmp_path / name
    (case_dir / "system").mkdir(parents=True)
    (case_dir / "constant").mkdir()
    return case_dir


def _stub_information(monkeypatch):
    """Auto-dismiss the "Case Is Open" notice every rename/move/delete of the
    open case shows via QMessageBox.information, imported into _case_ops."""
    monkeypatch.setattr(_case_ops.QMessageBox, "information", staticmethod(lambda *a, **k: None))


def _stub_rename_text(monkeypatch, new_name: str):
    monkeypatch.setattr(
        _case_ops.QInputDialog, "getText", staticmethod(lambda *a, **k: (new_name, True))
    )


def _auto_confirm_delete_dialog(monkeypatch):
    """Resolve the "Delete Folder" confirmation box to its Move to Trash button.

    QMessageBox.exec() blocks for a real click, unavailable offscreen, so
    exec()/clickedButton() are patched to act as if whichever button carries
    QMessageBox.ButtonRole.DestructiveRole (Move to Trash, not Cancel) had
    been clicked.
    """
    monkeypatch.setattr(_case_ops.QMessageBox, "exec", lambda self: 0)
    monkeypatch.setattr(
        _case_ops.QMessageBox,
        "clickedButton",
        lambda self: next(
            (b for b in self.buttons() if self.buttonRole(b) == QMessageBox.ButtonRole.DestructiveRole),
            None,
        ),
    )


# ── refusing an operation on an ancestor of the open case ────────────────────

class TestAncestorRefusal:
    """The canonical refused-operation shape: the filesystem is unchanged, the
    open case is untouched, and QMessageBox is never called at all -- a
    refusal reports to the status bar, never as a modal."""

    @pytest.mark.parametrize(
        "invoke",
        [
            lambda win, ancestor: win._on_case_nav_rename_requested(str(ancestor)),
            lambda win, ancestor: win._on_case_nav_move_requested(str(ancestor)),
            lambda win, ancestor: win._on_case_nav_delete_requested(str(ancestor)),
        ],
        ids=["rename", "move", "delete"],
    )
    def test_operation_on_an_ancestor_of_the_open_case_is_refused(
        self, main_window, tmp_path, monkeypatch, invoke
    ):
        case_dir = _make_case(tmp_path, "case")
        main_window._load_case_dir(str(case_dir))

        mock_msgbox = MagicMock()
        monkeypatch.setattr(_case_ops, "QMessageBox", mock_msgbox)
        monkeypatch.setattr(_case_ops, "QInputDialog", MagicMock())
        monkeypatch.setattr(_case_ops, "QFileDialog", MagicMock())

        invoke(main_window, tmp_path)  # tmp_path is the parent of case_dir

        assert case_dir.exists()
        assert main_window.state.current_case_dir == str(case_dir)
        mock_msgbox.assert_not_called()
        mock_msgbox.information.assert_not_called()
        mock_msgbox.question.assert_not_called()
        mock_msgbox.warning.assert_not_called()
        mock_msgbox.critical.assert_not_called()


# ── rename/move of the open case ─────────────────────────────────────────────

class TestRenameReloadsTheOpenCase:
    def test_renaming_the_open_case_reloads_it_at_the_new_path(
        self, main_window, tmp_path, monkeypatch
    ):
        case_dir = _make_case(tmp_path, "case")
        main_window._load_case_dir(str(case_dir))
        _stub_information(monkeypatch)
        _stub_rename_text(monkeypatch, "renamed")

        main_window._on_case_nav_rename_requested(str(case_dir))

        new_path = tmp_path / "renamed"
        assert main_window.state.current_case_dir == str(new_path)
        assert main_window.state.case_files_config is not None
        assert main_window.state.case_files_config._path == new_path / ".foam-editor-files.json"
        watched = main_window._case_dir_watcher.directories()
        assert str(new_path) in watched
        assert str(case_dir) not in watched


# ── deleting the open case ───────────────────────────────────────────────────

class TestDeleteClosesTheOpenCase:
    def test_deleting_the_open_case_closes_it(self, main_window, tmp_path, monkeypatch):
        case_dir = _make_case(tmp_path, "case")
        main_window._load_case_dir(str(case_dir))
        _stub_information(monkeypatch)
        _auto_confirm_delete_dialog(monkeypatch)
        monkeypatch.setattr(main_window, "_trash_directory", lambda path: True)

        main_window._on_case_nav_delete_requested(str(case_dir))

        assert main_window.state.current_case_dir is None
        assert main_window.state.file_buffers == {}
        assert main_window.state.undo.undo_stack == []
        assert main_window.state.undo.redo_stack == []
        assert main_window._case_dir_watcher.directories() == []

    def test_cancelling_the_delete_leaves_the_open_case_open(
        self, main_window, tmp_path, monkeypatch
    ):
        """Regression: nothing is torn down before the confirmation is accepted.

        The open case used to be closed on the way *to* the delete dialog, so
        answering Cancel left the case shut and the directory still on disk --
        the one outcome the user asked for neither of.
        """
        case_dir = _make_case(tmp_path, "case")
        main_window._load_case_dir(str(case_dir))
        _stub_information(monkeypatch)
        # Resolve the confirmation to Cancel rather than Move to Trash.
        monkeypatch.setattr(_case_ops.QMessageBox, "exec", lambda self: 0)
        monkeypatch.setattr(
            _case_ops.QMessageBox,
            "clickedButton",
            lambda self: next(
                (b for b in self.buttons()
                 if self.buttonRole(b) == QMessageBox.ButtonRole.RejectRole),
                None,
            ),
        )
        trashed: list[str] = []
        monkeypatch.setattr(
            main_window, "_trash_directory", lambda path: trashed.append(str(path)) or True
        )

        main_window._on_case_nav_delete_requested(str(case_dir))

        assert trashed == []
        assert case_dir.is_dir()
        assert main_window.state.current_case_dir == str(case_dir)

    def test_foam_monitor_is_stopped_before_the_case_is_deleted(
        self, main_window, tmp_path, monkeypatch
    ):
        case_dir = _make_case(tmp_path, "case")
        main_window._load_case_dir(str(case_dir))
        _stub_information(monkeypatch)
        _auto_confirm_delete_dialog(monkeypatch)

        order: list[str] = []
        monkeypatch.setattr(
            main_window, "_stop_foam_monitor", lambda: order.append("stop_foam_monitor")
        )
        monkeypatch.setattr(
            main_window,
            "_trash_directory",
            lambda path: order.append("trash_directory") or True,
        )

        main_window._on_case_nav_delete_requested(str(case_dir))

        assert order == ["stop_foam_monitor", "trash_directory"]


# ── .foam-editor-files.json travels with a move ──────────────────────────────

class TestExtraFilesConfigSurvivesAMove:
    def test_extra_files_config_survives_a_move(self, main_window, tmp_path, monkeypatch):
        case_dir = _make_case(tmp_path, "case")
        (case_dir / "extra.dat").write_text("x", encoding="utf-8")
        cfg = CaseFilesConfig(str(case_dir))
        cfg.add_file("extra.dat")
        cfg.save()

        main_window._load_case_dir(str(case_dir))
        _stub_information(monkeypatch)
        _stub_rename_text(monkeypatch, "moved_case")

        main_window._on_case_nav_rename_requested(str(case_dir))

        new_path = tmp_path / "moved_case"
        assert new_path.is_dir()
        reloaded = CaseFilesConfig(str(new_path))
        assert reloaded.get_extra_files() == ["extra.dat"]


# ── _close_case() ─────────────────────────────────────────────────────────────

class TestCloseCase:
    def test_close_case_clears_everything(self, main_window, tmp_path):
        case_dir = _make_case(tmp_path, "case")
        main_window._load_case_dir(str(case_dir))

        main_window.state.file_buffers["x"] = "text"
        main_window.state.file_dirty["x"] = True
        main_window.state.parsed_roots["x"] = object()
        main_window.state.read_only_files.add("x")
        main_window.state.current_file = "x"
        main_window.state.text_dirty = True

        main_window._close_case()

        assert main_window.state.current_case_dir is None
        assert main_window.state.case_files_config is None
        assert main_window.state.file_buffers == {}
        assert main_window.state.file_dirty == {}
        assert main_window.state.parsed_roots == {}
        assert main_window.state.read_only_files == set()
        assert main_window.state.undo.undo_stack == []
        assert main_window.state.undo.redo_stack == []
        assert main_window.state.current_file is None
        assert main_window.state.text_dirty is False
        assert main_window.state.diff.case_dir is None
        assert main_window.state.diff.parsed_roots == {}
        assert main_window._case_dir_watcher.directories() == []


# ── cancelling the unsaved-changes prompt ────────────────────────────────────

class TestSettleOpenCaseForCancelled:
    def test_settle_open_case_for_returns_false_when_discard_is_cancelled(
        self, main_window, tmp_path, monkeypatch
    ):
        case_dir = _make_case(tmp_path, "case")
        main_window._load_case_dir(str(case_dir))
        main_window.state.text_dirty = True
        monkeypatch.setattr(
            _ui_ops.QMessageBox,
            "question",
            staticmethod(lambda *a, **k: QMessageBox.StandardButton.No),
        )
        mock_info = MagicMock()
        monkeypatch.setattr(_case_ops.QMessageBox, "information", mock_info)

        result = main_window._settle_open_case_for(case_dir, "notice text")

        assert result is False
        assert main_window.state.current_case_dir == str(case_dir)
        mock_info.assert_not_called()
