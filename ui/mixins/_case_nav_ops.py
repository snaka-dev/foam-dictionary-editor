# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Case Browser / Cases-tab operations: every CaseNavigator signal lands here.

Split out of ui/mixins/_case_ops.py, which was 703 lines. The section carried its own
invariant already (see the comment below), and its only coupling to the rest of MainWindow is
through methods the protocol already declares -- _load_case_dir, _confirm_discard_if_needed,
_start_comparison_with, _clear_diff, _stop_foam_monitor -- which is what made the move
mechanical. See DEVELOPER.md's "Case navigation".
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QFile
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

from app_config import get_app_config
from foam.include_expand import clear_expand_cache
from i18n import tr
from services.case_fs_ops import (
    Precheck,
    check_delete,
    check_move,
    check_new_folder,
    check_rename,
    is_cross_device,
    is_within,
    perform_move,
    perform_new_folder,
)
from services.include_scan import clear_scan_cache
from ui.case_navigation import refusal_message
from ui.layout_constants import STATUS_NORMAL, STATUS_WARNING

if TYPE_CHECKING:
    from ui.mixins._protocol import MainWindowProtocol as _Base
else:
    _Base = object


class _CaseNavOpsMixin(_Base):
    """Handlers for the Case Browser window and the Cases tab."""

    # ── case browser ──────────────────────────────────────────────────────────
    #
    # One rule governs every operation below: path-keyed application state is
    # never rewritten in place, it is discarded and rebuilt through
    # _load_case_dir(). Following a move instead would mean correctly rewriting
    # current_case_dir, current_file, file_buffers, file_dirty, read_only_files,
    # parsed_roots, case_files_config, both halves of the diff state and every
    # UndoSnapshot's two path-keyed dicts, plus the watcher, the terminal cwd,
    # the BlockMesh panel and the cached log dialog. _load_case_dir already does
    # all of that. A miss would also be silent: list_case_files returns [] for a
    # directory that does not exist, so a stale case dir empties the file list
    # with no error at all.

    def _on_open_case_browser(self) -> None:
        from ui.dialogs.case_browser_dialog import CaseBrowserDialog

        self._show_cached_dialog(
            "_case_browser_dialog",
            lambda: CaseBrowserDialog(self._case_navigator, parent=self),
        )

    def _on_case_nav_open_requested(self, path: str) -> None:
        if path == self.state.current_case_dir:
            return
        if not self._confirm_discard_if_needed():
            return
        if not self._confirm_open_dir(path):
            return
        self._load_case_dir(path)
        self.raise_()
        self.activateWindow()

    def _on_case_nav_compare_requested(self, path: str) -> None:
        if not self.state.current_case_dir:
            QMessageBox.information(self, tr("No Case Open"), tr("Please open a case first."))
            return
        self._start_comparison_with(path)

    def _on_case_nav_duplicate_requested(self, path: str) -> None:
        self._duplicate_case_from(path)

    def _on_case_nav_new_folder_requested(self, parent: str) -> None:
        name, ok = QInputDialog.getText(
            self, tr("New Folder"), tr("New folder name (in {dir}):").format(dir=parent)
        )
        if not ok or not name.strip():
            return
        parent_path = Path(parent)
        check = check_new_folder(parent_path, name.strip())
        if not check.ok:
            self._refuse_case_nav(check)
            return
        try:
            created = perform_new_folder(parent_path, name.strip())
        except OSError as e:
            self._error(tr("Create Folder Error"), tr("Could not create folder:\n{e}").format(e=e))
            return
        self._case_navigator.notify_added(created)
        self.statusBar().showMessage(
            tr("Created {name}").format(name=created.name), STATUS_NORMAL
        )

    def _on_case_nav_rename_requested(self, path: str) -> None:
        source = Path(path)
        notice = tr("The open case is about to be renamed. It will be reloaded afterwards.")
        if not self._settle_open_case_for(source, notice):
            return
        name, ok = QInputDialog.getText(
            self, tr("Rename"), tr("New name:"), text=source.name
        )
        if not ok or not name.strip() or name.strip() == source.name:
            return
        check = check_rename(source, name.strip(), self._protected_case_paths())
        if not check.ok:
            self._refuse_case_nav(check)
            return
        destination = source.parent / name.strip()
        self._run_case_nav_move(source, destination, tr("Renamed to {name}"))

    def _on_case_nav_move_requested(self, path: str) -> None:
        source = Path(path)
        # "" because the move confirmation below carries the open-case warning.
        if not self._settle_open_case_for(source, ""):
            return
        is_open = self._case_nav_relates_to_open_case(source)
        chosen = QFileDialog.getExistingDirectory(
            self, tr("Move '{name}' Into").format(name=source.name), str(source.parent)
        )
        if not chosen:
            return
        destination = Path(chosen) / source.name
        check = check_move(source, destination, self._protected_case_paths())
        if not check.ok:
            self._refuse_case_nav(check)
            return
        message = tr("Move <b>{name}</b> to a new location?").format(name=source.name)
        detail = tr("From: {src}\nTo:   {dst}").format(src=source.parent, dst=chosen)
        if is_cross_device(source, destination):
            detail += "\n\n" + tr(
                "The destination is on a different filesystem, so this is a copy "
                "followed by a delete and may take a while."
            )
        if is_open:
            detail += "\n\n" + tr(
                "This case is currently open. It will be reloaded at its new location."
            )
        # A named button rather than _confirm's Yes/No: "Move" says what will
        # happen, which matters more the moment the thing being moved is data.
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle(tr("Move Folder"))
        box.setText(message)
        box.setInformativeText(detail)
        move_btn = box.addButton(tr("Move"), QMessageBox.ButtonRole.AcceptRole)
        box.setDefaultButton(box.addButton(QMessageBox.StandardButton.Cancel))
        box.exec()
        if box.clickedButton() is not move_btn:
            return
        self._run_case_nav_move(source, destination, tr("Moved {name}"))

    def _on_case_nav_delete_requested(self, path: str) -> None:
        target = Path(path)
        check = check_delete(target, self._protected_case_paths())
        if not check.ok:
            self._refuse_case_nav(check)
            return
        # No notice of its own: the open-case warning goes into the delete
        # confirmation below instead, so the case is not closed until the
        # deletion has actually been accepted. Closing first would leave a
        # cancelled delete having shut the case anyway.
        if not self._settle_open_case_for(target, ""):
            return
        is_open = self._case_nav_relates_to_open_case(target)

        info = [str(target)]
        if target.is_symlink():
            info.append(
                tr("This is a symbolic link. Only the link will be removed; "
                   "its target is not affected.")
            )
        else:
            info.append(tr("Everything inside it goes to the trash too."))
        if is_open:
            info.append(tr("This case is currently open. It will be closed."))
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle(tr("Delete Folder"))
        box.setText(tr("Delete <b>{name}</b>?").format(name=target.name))
        box.setInformativeText("\n\n".join(info))
        trash_btn = box.addButton(tr("Move to Trash"), QMessageBox.ButtonRole.DestructiveRole)
        cancel_btn = box.addButton(QMessageBox.StandardButton.Cancel)
        box.setDefaultButton(cancel_btn)
        box.exec()
        if box.clickedButton() is not trash_btn:
            return

        # Before the removal, not after: gnuplot would otherwise keep writing
        # into a deleted inode and the temp-script cleanup would race teardown.
        self._stop_foam_monitor()
        if is_open:
            self._close_case()
        if self.state.diff.case_dir and is_within(Path(self.state.diff.case_dir), target):
            self._clear_diff()
        if not self._trash_directory(target):
            return
        self._case_navigator.notify_removed(target)

    # ── case browser helpers ──────────────────────────────────────────────────

    def _protected_case_paths(self) -> list[Path]:
        """Directories the browser must never move, rename or delete."""
        return [Path(d) for d in get_app_config().get_case_library_dirs()]

    def _refuse_case_nav(self, check: Precheck) -> None:
        """Report a refused operation to the status bar, never as a modal.

        A refusal is not a decision the user is being asked to make, so it does
        not earn a dialog; the modal budget is kept for operations that can
        actually proceed.
        """
        assert check.refusal is not None
        self.statusBar().showMessage(refusal_message(check.refusal, check.detail), STATUS_WARNING)

    def _case_nav_relates_to_open_case(self, path: Path) -> bool:
        case_dir = self.state.current_case_dir
        return bool(case_dir) and is_within(Path(str(case_dir)), path)

    def _settle_open_case_for(self, path: Path, notice: str) -> bool:
        """Clear the way for an operation on *path*, or refuse it.

        An operation on an *ancestor* of the open case is refused outright: the
        user almost certainly did not mean it, and silently closing a case they
        did not name is a surprise with data loss attached.

        *notice* is shown only when the operation has no confirmation of its
        own (rename); pass "" where the caller shows its own and folds the
        open-case warning into it, so nothing is torn down before the user has
        actually agreed to the operation. Never closes the case itself --
        that is the caller's to do once its own confirmation is accepted.
        """
        case_dir = self.state.current_case_dir
        if not case_dir or not is_within(Path(case_dir), path):
            return True
        if Path(case_dir).resolve() != path.resolve():
            self.statusBar().showMessage(
                tr("This folder contains the case that is currently open. Close the case first."),
                STATUS_WARNING,
            )
            return False
        if not self._confirm_discard_if_needed():
            return False
        if notice:
            # A whole sentence per operation rather than a verb interpolated
            # into one: a bare verb cannot be conjugated correctly by a
            # translator who never sees the sentence it lands in.
            QMessageBox.information(self, tr("Case Is Open"), notice)
        return True

    def _trash_directory(self, path: Path) -> bool:
        """Send *path* to the desktop trash, offering a permanent delete if it fails."""
        handle = QFile(str(path))
        if handle.moveToTrash():
            self.statusBar().showMessage(
                tr("Moved to trash: {name}").format(name=path.name), STATUS_NORMAL
            )
            return True
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle(tr("Could Not Move to Trash"))
        box.setText(tr("<b>{name}</b> could not be moved to the trash.").format(name=path.name))
        box.setInformativeText(
            tr("Reason: {reason}\n\nDeleting permanently cannot be undone.").format(
                reason=handle.errorString()
            )
        )
        delete_btn = box.addButton(
            tr("Delete Permanently"), QMessageBox.ButtonRole.DestructiveRole
        )
        cancel_btn = box.addButton(QMessageBox.StandardButton.Cancel)
        box.setDefaultButton(cancel_btn)
        box.exec()
        if box.clickedButton() is not delete_btn:
            return False
        try:
            shutil.rmtree(path)
        except OSError as e:
            self._error(tr("Delete Error"), tr("Could not delete folder:\n{e}").format(e=e))
            return False
        return True

    def _run_case_nav_move(self, source: Path, destination: Path, status_template: str) -> None:
        """Move or rename *source*, then re-enter the case if it was the open one."""
        was_open = self._case_nav_relates_to_open_case(source)
        was_reference = bool(self.state.diff.case_dir) and is_within(
            Path(str(self.state.diff.case_dir)), source
        )
        try:
            perform_move(source, destination)
        except OSError as e:
            # The source is left untouched on any failure. A cross-device move
            # can die after copying and before deleting, so name both paths and
            # let the user decide rather than attempting a rollback that could
            # itself destroy the only surviving copy.
            self._error(
                tr("Move Failed"),
                tr(
                    "The move did not complete:\n{e}\n\n"
                    "The original is unchanged at:\n{src}\n"
                    "An incomplete copy may exist at:\n{dst}"
                ).format(e=e, src=source, dst=destination)
            )
            return
        self._case_navigator.notify_moved(source, destination)
        if was_open:
            self._load_case_dir(str(destination))
        if was_reference:
            self._start_comparison_with(str(destination))
        self.statusBar().showMessage(
            status_template.format(name=destination.name), STATUS_NORMAL
        )

    def _close_case(self) -> None:
        """The inverse of _load_case_dir: leave the window with no case open."""
        if self._case_dir_watcher.directories():
            self._case_dir_watcher.removePaths(self._case_dir_watcher.directories())
        self._file_list_refresh_timer.stop()
        clear_scan_cache()
        clear_expand_cache()
        self.state.current_case_dir = None
        self.state.case_files_config = None
        self.state.file_buffers.clear()
        self.state.file_dirty.clear()
        self.state.parsed_roots.clear()
        self.state.viewer_include_sources.clear()
        self.state.read_only_files.clear()
        self._clear_undo_stacks()
        self._clear_current_file()
        self.file_list_panel.clear()
        if self.block_mesh_panel is not None:
            self.block_mesh_panel.clear()
        if self._log_summary_dialog is not None:
            self._log_summary_dialog.set_case_dir("")
        self._clear_diff()
        self._case_navigator.set_current_case(None)
        self._update_case_label()
