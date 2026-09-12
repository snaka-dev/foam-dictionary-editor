# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QFile
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QInputDialog,
    QMessageBox,
)

from app_config import get_app_config
from app_config.defaults import DEFAULT_WINDOW_HEIGHT, DEFAULT_WINDOW_WIDTH
from foam.include_expand import clear_expand_cache
from i18n import tr
from services.case_copier import copy_visible_files
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
from services.case_loader import is_openfoam_case
from services.include_scan import clear_scan_cache
from ui.case_navigation import refusal_message
from ui.dialogs.case_library_dialog import CaseLibraryDialog
from ui.dialogs.duplicate_case_dialog import DuplicateCaseDialog
from ui.dialogs.reset_settings_dialog import ResetSettingsDialog
from ui.dialogs.save_as_new_case_dialog import SaveAsNewCaseDialog
from ui.layout_constants import STATUS_NORMAL, STATUS_WARNING

if TYPE_CHECKING:
    from ui.mixins._protocol import MainWindowProtocol as _Base
else:
    _Base = object


class _CaseOpsMixin(_Base):
    """Case-level operations: open, duplicate, save-as, settings."""

    # ── open ──────────────────────────────────────────────────────────────────

    def open_case(self) -> None:
        if not self._confirm_discard_if_needed():
            return

        app_config = get_app_config()
        directory = QFileDialog.getExistingDirectory(
            self,
            tr("Open OpenFOAM Case"),
            app_config.get_default_case_dir() or "",
        )
        if not directory:
            return

        if not self._confirm_open_dir(directory):
            return
        app_config.set_default_case_dir(str(Path(directory).parent))
        app_config.save()
        self._load_case_dir(directory)

    def reload_case(self) -> None:
        if not self.state.current_case_dir:
            QMessageBox.information(self, tr("No Case Open"), tr("Please open a case first."))
            return

        dirty_count = sum(1 for d in self.state.file_dirty.values() if d)
        if dirty_count > 0:
            reply = QMessageBox.question(
                self,
                tr("Reload Case"),
                tr("Reloading will discard unsaved changes in {count} file(s).\n\nReload from disk?").format(
                    count=dirty_count
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self._load_case_dir(self.state.current_case_dir)
        self.statusBar().showMessage(
            tr("Case reloaded: {path}").format(path=self.state.current_case_dir), STATUS_NORMAL
        )

    def open_from_library(self) -> None:
        if not self._confirm_discard_if_needed():
            return
        directory = self._pick_case_from_library(tr("Open OpenFOAM Case from Library"))
        if not directory:
            return
        if not self._confirm_open_dir(directory):
            return
        self._load_case_dir(directory)

    # ── duplicate ─────────────────────────────────────────────────────────────

    def duplicate_case(self) -> None:
        if not self.state.current_case_dir:
            QMessageBox.information(self, tr("No Case Open"), tr("Please open a case first."))
            return

        dirty_paths = [p for p, dirty in self.state.file_dirty.items() if dirty]
        if self.state.current_file and self.state.text_dirty:
            dirty_paths = list({*dirty_paths, self.state.current_file})

        if dirty_paths:
            reply = QMessageBox.question(
                self,
                tr("Unsaved Changes"),
                tr("There are unsaved changes. Save all files before duplicating?"),
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes,
            )
            if reply == QMessageBox.StandardButton.Cancel:
                return
            if reply == QMessageBox.StandardButton.Yes:
                self.save_all_files()

        dialog = DuplicateCaseDialog(self.state.current_case_dir, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        dest = dialog.destination_path
        if dest is None:
            return

        self._run_duplicate(self.state.current_case_dir, dest, dialog.copy_all_files)

    def duplicate_from_library(self) -> None:
        source = self._pick_case_from_library(tr("Select Source Case from Library"))
        if not source:
            return
        self._duplicate_case_from(source)

    def _duplicate_case_from(
        self, source: str, fallback_dest_parent: str | None = None
    ) -> None:
        """Show DuplicateCaseDialog for *source* and run the copy on accept.

        The destination defaults to the configured default case directory;
        when unset, *fallback_dest_parent* is offered instead (callers whose
        source sits in a read-only location, e.g. an OpenFOAM installation's
        tutorials, should pass a writable one), else the source's parent.
        """
        cfg = get_app_config()
        default_dest = (
            cfg.get_default_case_dir() or fallback_dest_parent or str(Path(source).parent)
        )
        dialog = DuplicateCaseDialog(source, default_dest_parent=default_dest, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        dest = dialog.destination_path
        if dest is None:
            return
        self._run_duplicate(source, dest, dialog.copy_all_files)

    def _pick_case_from_library(self, title: str) -> str | None:
        dirs = get_app_config().get_case_library_dirs()
        if not dirs:
            QMessageBox.information(
                self,
                tr("Case Library Empty"),
                tr(
                    "No directories are registered in the Case Library.\n\n"
                    "Add directories via Settings > Manage Case Library..."
                ),
            )
            return None
        if len(dirs) == 1:
            start_dir = dirs[0]
        else:
            item, ok = QInputDialog.getItem(
                self, tr("Select Library"), tr("Choose a library to browse:"), dirs, 0, False
            )
            if not ok:
                return None
            start_dir = item
        directory = QFileDialog.getExistingDirectory(self, title, start_dir)
        return directory or None

    def _confirm_and_remove_existing_dir(self, dest: Path, error_title: str) -> bool:
        if not dest.exists():
            return True
        reply = QMessageBox.question(
            self,
            tr("Destination Already Exists"),
            tr("The following directory already exists:\n{dest}\n\nOverwrite?").format(dest=dest),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return False
        try:
            shutil.rmtree(dest)
        except Exception as e:
            QMessageBox.critical(
                self, error_title,
                tr("Could not remove existing directory:\n{e}").format(e=e)
            )
            return False
        return True

    def _run_duplicate(self, source_dir: str, dest: Path, copy_all: bool) -> None:
        if not self._confirm_and_remove_existing_dir(dest, tr("Duplicate Error")):
            return

        try:
            if copy_all:
                shutil.copytree(source_dir, str(dest))
            else:
                self._copy_visible_files(source_dir, dest)
        except Exception as e:
            QMessageBox.critical(
                self, tr("Duplicate Error"),
                tr("Failed to duplicate case:\n{e}").format(e=e)
            )
            return

        reply = QMessageBox.question(
            self,
            tr("Duplicate Complete"),
            tr("Case duplicated to:\n{dest}\n\nOpen the duplicated case now?").format(dest=dest),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            cfg = get_app_config()
            cfg.set_default_case_dir(str(dest.parent))
            cfg.save()
            self._load_case_dir(str(dest))
        else:
            self.statusBar().showMessage(
                tr("Duplicated to: {dest}").format(dest=dest), STATUS_NORMAL
            )

    # ── save as new case ──────────────────────────────────────────────────────

    def save_as_new_case(self) -> None:
        if not self.state.current_case_dir:
            QMessageBox.information(self, tr("No Case Open"), tr("Please open a case first."))
            return

        if self.state.current_file is not None:
            self.state.file_buffers[self.state.current_file] = self.editor_panel.get_text()
            self.state.file_dirty[self.state.current_file] = self.state.text_dirty

        dlg = SaveAsNewCaseDialog(self.state.current_case_dir, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        dest = dlg.destination_path
        if dest is None:
            return

        if not self._confirm_and_remove_existing_dir(dest, tr("Save As Error")):
            return

        try:
            if dlg.copy_all_files:
                shutil.copytree(self.state.current_case_dir, str(dest))
            else:
                self._copy_visible_files(self.state.current_case_dir, dest)
        except Exception as e:
            QMessageBox.critical(
                self, tr("Save As Error"),
                tr("Could not copy case files:\n{e}").format(e=e)
            )
            return

        source = Path(self.state.current_case_dir)
        errors: list[str] = []
        for path_str, dirty in self.state.file_dirty.items():
            if not dirty:
                continue
            text = self.state.file_buffers.get(path_str)
            if text is None:
                continue
            try:
                rel = Path(path_str).relative_to(source)
                dest_file = dest / rel
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                dest_file.write_text(text, encoding="utf-8")
            except Exception as e:
                errors.append(f"{Path(path_str).name}: {e}")

        if errors:
            QMessageBox.warning(
                self,
                tr("Save As — Partial Failure"),
                tr("Some edited files could not be written:\n{errors}").format(
                    errors="\n".join(errors)
                ),
            )

        cfg = get_app_config()
        cfg.set_default_case_dir(str(dest.parent))
        cfg.save()
        self._load_case_dir(str(dest))
        self.statusBar().showMessage(
            tr("Saved as new case: {dest}").format(dest=dest), STATUS_NORMAL
        )

    # ── helpers ───────────────────────────────────────────────────────────────

    def _confirm_open_dir(self, directory: str) -> bool:
        """Return True if the directory should be opened (valid or user confirmed)."""
        if is_openfoam_case(directory):
            return True
        reply = QMessageBox.warning(
            self,
            tr("Possibly Not an OpenFOAM Case"),
            tr(
                "The selected directory does not contain 'system' or 'constant':\n\n"
                "{directory}\n\n"
                "This may not be a valid OpenFOAM case.\nOpen anyway?"
            ).format(directory=directory),
            QMessageBox.StandardButton.Open | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        return reply == QMessageBox.StandardButton.Open

    def _copy_visible_files(self, source_dir: str, dest: Path) -> None:
        copy_visible_files(source_dir, dest)

    # ── settings ──────────────────────────────────────────────────────────────

    def set_default_case_directory(self) -> None:
        app_config = get_app_config()
        directory = QFileDialog.getExistingDirectory(
            self,
            tr("Select Default Case Directory"),
            app_config.get_default_case_dir() or "",
        )
        if directory:
            app_config.set_default_case_dir(directory)
            app_config.save()
            QMessageBox.information(
                self,
                tr("Directory Saved"),
                tr(
                    "Default case directory set to:\n{directory}\n\n"
                    "This directory will be used as the initial location when opening cases."
                ).format(directory=directory),
            )

    def manage_case_library(self) -> None:
        cfg = get_app_config()
        dialog = CaseLibraryDialog(cfg.get_user_library_dirs(), self)
        dialog.exec()
        new_dirs = dialog.library_dirs
        if new_dirs != cfg.get_user_library_dirs():
            for d in cfg.get_user_library_dirs():
                cfg.remove_case_library_dir(d)
            for d in new_dirs:
                cfg.add_case_library_dir(d)
            cfg.save()

    def reset_window_size(self) -> None:
        reply = QMessageBox.question(
            self,
            tr("Reset Window Size"),
            tr("Reset window size to default ({w}x{h})?").format(
                w=DEFAULT_WINDOW_WIDTH, h=DEFAULT_WINDOW_HEIGHT
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
            cfg = get_app_config()
            cfg.set_window_size(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
            # Otherwise the next session restore reapplies the saved geometry
            # and the window comes back the size just reset away from.
            cfg.clear_session_geometry()
            cfg.save()
            QMessageBox.information(
                self,
                tr("Size Reset"),
                tr("Window size has been reset to default ({w}x{h}).").format(
                    w=DEFAULT_WINDOW_WIDTH, h=DEFAULT_WINDOW_HEIGHT
                ),
            )

    def reset_all_settings(self) -> None:
        dialog = ResetSettingsDialog(self)
        dialog.exec()
        if dialog.app_settings_reset:
            self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)

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
            QMessageBox.critical(
                self, tr("Create Folder Error"), tr("Could not create folder:\n{e}").format(e=e)
            )
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
            QMessageBox.critical(
                self, tr("Delete Error"), tr("Could not delete folder:\n{e}").format(e=e)
            )
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
            QMessageBox.critical(
                self,
                tr("Move Failed"),
                tr(
                    "The move did not complete:\n{e}\n\n"
                    "The original is unchanged at:\n{src}\n"
                    "An incomplete copy may exist at:\n{dst}"
                ).format(e=e, src=source, dst=destination),
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

    # ── foamMonitor launcher ──────────────────────────────────────────────────

