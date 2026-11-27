# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QInputDialog,
    QMessageBox,
)

from app_config import get_app_config
from app_config.defaults import DEFAULT_WINDOW_HEIGHT, DEFAULT_WINDOW_WIDTH
from foam.utils import write_foam_file
from i18n import tr
from services.case_copier import CopyReport, copy_visible_files
from services.case_files_config import is_inside_case
from services.case_loader import is_openfoam_case
from services.case_paths import (
    DEST_CONTAINS_SOURCE,
    DEST_INSIDE_SOURCE,
    DEST_IS_LINK,
    DEST_IS_SOURCE,
    DEST_PARENT_MISSING,
    SOURCE_UNRESOLVABLE,
    conflicting_writes,
    copy_destination_problem,
    creatable,
    editable,
    writable,
)
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

    def _destination_refused(self, source: str, dest: Path, error_title: str) -> bool:
        """Report and return True when *dest* cannot receive a copy of *source*.

        Checked before anything is removed: overwriting means ``rmtree``, so a
        destination that is the source, lies inside it or contains it -- by any
        spelling, ``..`` and symlinks included -- would delete the case being
        copied, or the folder holding it.
        """
        problem = copy_destination_problem(source, dest)
        if problem is None:
            return False
        messages = {
            DEST_IS_SOURCE: tr("The destination is the case being copied."),
            DEST_INSIDE_SOURCE: tr("The destination is inside the case being copied."),
            DEST_CONTAINS_SOURCE: tr("The destination contains the case being copied."),
            DEST_IS_LINK: tr("The destination is a symbolic link."),
            DEST_PARENT_MISSING: tr("The destination's parent folder does not exist."),
            SOURCE_UNRESOLVABLE: tr("The case being copied cannot be read."),
        }
        self._error(
            error_title,
            tr("Cannot copy the case to:\n{dest}\n\n{reason}").format(
                dest=dest, reason=messages.get(problem, problem)
            ),
        )
        return True

    def _confirm_and_remove_existing_dir(
        self, dest: Path, error_title: str, source: str
    ) -> bool:
        if self._destination_refused(source, dest, error_title):
            return False
        if not dest.exists():
            return True
        if not self._confirm(
            tr("Destination Already Exists"),
            tr("The following directory already exists:\n{dest}\n\nOverwrite?").format(dest=dest),
        ):
            return False
        # Again, now that the prompt has returned: it can stay open for any
        # length of time, and what is removed must be what was checked.
        if self._destination_refused(source, dest, error_title):
            return False
        if not dest.exists():
            return True
        try:
            shutil.rmtree(dest)
        except Exception as e:
            self._error(error_title, tr("Could not remove existing directory:\n{e}").format(e=e))
            return False
        return True

    def _copy_case(self, source_dir: str, dest: Path, copy_all: bool) -> list[str]:
        """Copy the case; return the case-relative files left out.

        Copy-all keeps symlinks as symlinks, so a link's outside target is never
        copied in (the new case lists it read-only, like the source did). The
        visible-files copy skips anything whose real location is outside.
        """
        if copy_all:
            shutil.copytree(source_dir, str(dest), symlinks=True)
            return []
        return self._copy_visible_files(source_dir, dest).skipped

    def _run_duplicate(self, source_dir: str, dest: Path, copy_all: bool) -> None:
        if not self._confirm_and_remove_existing_dir(dest, tr("Duplicate Error"), source_dir):
            return

        try:
            skipped = self._copy_case(source_dir, dest, copy_all)
        except Exception as e:
            self._error(tr("Duplicate Error"), tr("Failed to duplicate case:\n{e}").format(e=e))
            return

        message = tr("Case duplicated to:\n{dest}\n\nOpen the duplicated case now?").format(
            dest=dest
        )
        if skipped:
            message += "\n\n" + _skipped_note(skipped)
        if self._confirm(tr("Duplicate Complete"), message):
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

        source_dir = self.state.current_case_dir
        if not self._confirm_and_remove_existing_dir(dest, tr("Save As Error"), source_dir):
            return

        try:
            skipped = self._copy_case(source_dir, dest, dlg.copy_all_files)
        except Exception as e:
            self._error(tr("Save As Error"), tr("Could not copy case files:\n{e}").format(e=e))
            return

        errors = self._write_dirty_buffers_to(source_dir, dest, set(skipped))
        if errors:
            # Opening the new case clears every buffer, and these edits are in
            # neither case on disk. The case they belong to stays open.
            parts = [
                tr(
                    "The new case was created, but these unsaved edits could not be "
                    "written to it:\n{errors}"
                ).format(errors="\n".join(errors)),
                tr(
                    "The original case stays open, with the edits still unsaved. "
                    "The new case is at:\n{dest}"
                ).format(dest=dest),
            ]
            if skipped:
                parts.append(_skipped_note(skipped))
            QMessageBox.warning(self, tr("Save As — Partial Failure"), "\n\n".join(parts))
            self.statusBar().showMessage(
                tr("New case created without some unsaved edits: {dest}").format(dest=dest),
                STATUS_WARNING,
            )
            return
        if skipped:
            QMessageBox.warning(self, tr("Save As — Partial Failure"), _skipped_note(skipped))

        cfg = get_app_config()
        cfg.set_default_case_dir(str(dest.parent))
        cfg.save()
        self._load_case_dir(str(dest))
        if skipped:
            done = tr("Saved as new case, with omissions: {dest}").format(dest=dest)
        else:
            done = tr("Saved as new case: {dest}").format(dest=dest)
        self.statusBar().showMessage(done, STATUS_WARNING if skipped else STATUS_NORMAL)

    def _write_dirty_buffers_to(self, source_dir: str, dest: Path, skipped: set[str]) -> list[str]:
        """Write each unsaved buffer of *source_dir* to its place in *dest*.

        Returns one line per buffer not written. Both ends are checked on disk:
        the buffer must belong to a file inside the source case, and in the new
        case the file must be a regular file inside it or a name that can be
        created there. A copy-all keeps links, so a copied link -- or a linked
        directory above the file -- must never take a buffer write.
        """
        source = Path(source_dir)
        errors: list[str] = []
        dirty_texts = {
            p: text
            for p, dirty in self.state.file_dirty.items()
            if dirty and (text := self.state.file_buffers.get(p)) is not None
        }
        conflicts = conflicting_writes(dirty_texts)
        planned: dict[str, tuple[Path, str, bool]] = {}
        for path_str, text in dirty_texts.items():
            if path_str in conflicts:
                errors.append(
                    f"{self._case_relative(path_str) or Path(path_str).name}: "
                    + tr("another unsaved file is the same file on disk")
                )
                continue
            name = Path(path_str).name
            rel = _case_relative_name(path_str, source)
            if rel is None:
                errors.append(f"{name}: " + tr("not part of the case"))
                continue
            if (str(rel) in skipped or not is_inside_case(str(rel))
                    or not writable(path_str, source)
                    or not _names_same_file(path_str, source / rel)):
                errors.append(f"{rel}: " + tr("leads outside the case directory"))
                continue
            dest_file = dest / rel
            exists = os.path.lexists(dest_file)
            if not (editable(dest_file, dest) if exists else creatable(dest_file, dest)):
                errors.append(f"{rel}: " + tr("leads outside the new case directory"))
                continue
            planned[str(dest_file)] = (rel, text, exists)
        # Two source files can be one file in the new case (names differing
        # only in letter case, copied to a filesystem that ignores it).
        collisions = conflicting_writes({d: text for d, (_, text, _) in planned.items()})
        for dest_name, (rel, text, exists) in planned.items():
            if dest_name in collisions:
                errors.append(f"{rel}: " + tr("another unsaved file is the same file on disk"))
                continue
            try:
                Path(dest_name).parent.mkdir(parents=True, exist_ok=True)
                write_foam_file(dest_name, text, exclusive=not exists)
            except Exception as e:
                errors.append(f"{rel}: {e}")
        return errors

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

    def _copy_visible_files(self, source_dir: str, dest: Path) -> CopyReport:
        return copy_visible_files(source_dir, dest)

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
        if self._confirm(
            tr("Reset Window Size"),
            tr("Reset window size to default ({w}x{h})?").format(
                w=DEFAULT_WINDOW_WIDTH, h=DEFAULT_WINDOW_HEIGHT
            ),
        ):
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


    # ── foamMonitor launcher ──────────────────────────────────────────────────


def _case_relative_name(path: str, case: Path) -> Path | None:
    """*path* as a name under *case* with ``.`` and ``..`` folded away, or None.

    An ``#include "../constant/x"`` is listed as ``system/../constant/x``; Save
    writes it, so Save As must carry it too, as ``constant/x``. Folding is
    textual, which is only right when no link sits before the ``..`` --
    :func:`_names_same_file` is the check that it was.
    """
    try:
        return Path(os.path.normpath(path)).relative_to(Path(os.path.normpath(case)))
    except ValueError:
        return None


def _names_same_file(path: str, folded: Path) -> bool:
    """True when the folded name is the file *path* names (or *path* had nothing to fold)."""
    if Path(path) == folded:
        return True
    try:
        return os.path.samefile(path, folded)
    except OSError:
        return False


def _skipped_note(skipped: list[str]) -> str:
    """The files a copy left out because they lead outside the case."""
    shown = skipped[:10]
    more = len(skipped) - len(shown)
    lines = "\n".join(shown) + (f"\n… (+{more})" if more else "")
    return tr("Not copied — these lead outside the case directory:\n{files}").format(files=lines)
