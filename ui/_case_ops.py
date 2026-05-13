# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QInputDialog,
    QMessageBox,
)

from app_config import get_app_config
from app_config.defaults import DEFAULT_WINDOW_HEIGHT, DEFAULT_WINDOW_WIDTH
from services.case_copier import copy_visible_files
from services.case_loader import is_openfoam_case
from ui.layout_constants import (
    STATUS_NORMAL as _STATUS_NORMAL,
    STATUS_SHORT as _STATUS_SHORT,
)


class _CaseOpsMixin:
    """Case-level operations: open, duplicate, save-as, settings."""

    # ── open ──────────────────────────────────────────────────────────────────

    def open_case(self) -> None:
        if not self._confirm_discard_if_needed():
            return

        app_config = get_app_config()
        directory = QFileDialog.getExistingDirectory(
            self,
            "Open OpenFOAM Case",
            app_config.get_default_case_dir() or "",
        )
        if not directory:
            return

        if not self._confirm_open_dir(directory):
            return
        app_config.set_default_case_dir(str(Path(directory).parent))
        app_config.save()
        self._load_case_dir(directory)

    def open_from_library(self) -> None:
        if not self._confirm_discard_if_needed():
            return
        directory = self._pick_case_from_library("Open OpenFOAM Case from Library")
        if not directory:
            return
        if not self._confirm_open_dir(directory):
            return
        self._load_case_dir(directory)

    # ── duplicate ─────────────────────────────────────────────────────────────

    def duplicate_case(self) -> None:
        if not self.current_case_dir:
            QMessageBox.information(self, "No Case Open", "Please open a case first.")
            return

        dirty_paths = [p for p, dirty in self.file_dirty.items() if dirty]
        if self.current_file and self.text_dirty:
            dirty_paths = list({*dirty_paths, self.current_file})

        if dirty_paths:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "There are unsaved changes. Save all files before duplicating?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes,
            )
            if reply == QMessageBox.Cancel:
                return
            if reply == QMessageBox.Yes:
                self.save_all_files()

        from ui.duplicate_case_dialog import DuplicateCaseDialog

        dialog = DuplicateCaseDialog(self.current_case_dir, self)
        if dialog.exec() != QDialog.Accepted:
            return

        dest = dialog.destination_path
        if dest is None:
            return

        if dest.exists():
            reply = QMessageBox.question(
                self,
                "Destination Already Exists",
                f"The following directory already exists:\n{dest}\n\nOverwrite?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
            try:
                shutil.rmtree(dest)
            except Exception as e:
                QMessageBox.critical(self, "Duplicate Error", f"Could not remove existing directory:\n{e}")
                return

        self._run_duplicate(self.current_case_dir, dest, dialog.copy_all_files)

    def duplicate_from_library(self) -> None:
        source = self._pick_case_from_library("Select Source Case from Library")
        if not source:
            return
        cfg = get_app_config()
        default_dest = cfg.get_default_case_dir() or str(Path(source).parent)
        from ui.duplicate_case_dialog import DuplicateCaseDialog
        dialog = DuplicateCaseDialog(source, default_dest_parent=default_dest, parent=self)
        if dialog.exec() != QDialog.Accepted:
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
                "Case Library Empty",
                "No directories are registered in the Case Library.\n\n"
                "Add directories via Settings > Manage Case Library...",
            )
            return None
        if len(dirs) == 1:
            start_dir = dirs[0]
        else:
            item, ok = QInputDialog.getItem(
                self, "Select Library", "Choose a library to browse:", dirs, 0, False
            )
            if not ok:
                return None
            start_dir = item
        directory = QFileDialog.getExistingDirectory(self, title, start_dir)
        return directory or None

    def _run_duplicate(self, source_dir: str, dest: Path, copy_all: bool) -> None:
        if dest.exists():
            reply = QMessageBox.question(
                self,
                "Destination Already Exists",
                f"The following directory already exists:\n{dest}\n\nOverwrite?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
            try:
                shutil.rmtree(dest)
            except Exception as e:
                QMessageBox.critical(self, "Duplicate Error", f"Could not remove existing directory:\n{e}")
                return

        try:
            if copy_all:
                shutil.copytree(source_dir, str(dest))
            else:
                self._copy_visible_files(source_dir, dest)
        except Exception as e:
            QMessageBox.critical(self, "Duplicate Error", f"Failed to duplicate case:\n{e}")
            return

        reply = QMessageBox.question(
            self,
            "Duplicate Complete",
            f"Case duplicated to:\n{dest}\n\nOpen the duplicated case now?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            cfg = get_app_config()
            cfg.set_default_case_dir(str(dest.parent))
            cfg.save()
            self._load_case_dir(str(dest))
        else:
            self.statusBar().showMessage(f"Duplicated to: {dest}", _STATUS_NORMAL)

    # ── save as new case ──────────────────────────────────────────────────────

    def save_as_new_case(self) -> None:
        if not self.current_case_dir:
            QMessageBox.information(self, "No Case Open", "Please open a case first.")
            return

        if self.current_file is not None:
            self.file_buffers[self.current_file] = self.editor_panel.get_text()
            self.file_dirty[self.current_file] = self.text_dirty

        from ui.save_as_new_case_dialog import SaveAsNewCaseDialog

        dlg = SaveAsNewCaseDialog(self.current_case_dir, self)
        if dlg.exec() != QDialog.Accepted:
            return

        dest = dlg.destination_path
        if dest is None:
            return

        if dest.exists():
            reply = QMessageBox.question(
                self,
                "Destination Already Exists",
                f"The following directory already exists:\n{dest}\n\nOverwrite?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
            try:
                shutil.rmtree(dest)
            except Exception as e:
                QMessageBox.critical(self, "Save As Error", f"Could not remove existing directory:\n{e}")
                return

        try:
            if dlg.copy_all_files:
                shutil.copytree(self.current_case_dir, str(dest))
            else:
                self._copy_visible_files(self.current_case_dir, dest)
        except Exception as e:
            QMessageBox.critical(self, "Save As Error", f"Could not copy case files:\n{e}")
            return

        source = Path(self.current_case_dir)
        errors: list[str] = []
        for path_str, dirty in self.file_dirty.items():
            if not dirty:
                continue
            text = self.file_buffers.get(path_str)
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
                "Save As — Partial Failure",
                "Some edited files could not be written:\n" + "\n".join(errors),
            )

        cfg = get_app_config()
        cfg.set_default_case_dir(str(dest.parent))
        cfg.save()
        self._load_case_dir(str(dest))
        self.statusBar().showMessage(f"Saved as new case: {dest}", _STATUS_NORMAL)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _confirm_open_dir(self, directory: str) -> bool:
        """Return True if the directory should be opened (valid or user confirmed)."""
        if is_openfoam_case(directory):
            return True
        reply = QMessageBox.warning(
            self,
            "Possibly Not an OpenFOAM Case",
            f"The selected directory does not contain 'system' or 'constant':\n\n"
            f"{directory}\n\n"
            "This may not be a valid OpenFOAM case.\n"
            "Open anyway?",
            QMessageBox.Open | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        return reply == QMessageBox.Open

    def _copy_visible_files(self, source_dir: str, dest: Path) -> None:
        copy_visible_files(source_dir, dest)

    # ── settings ──────────────────────────────────────────────────────────────

    def set_default_case_directory(self) -> None:
        app_config = get_app_config()
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Default Case Directory",
            app_config.get_default_case_dir() or "",
        )
        if directory:
            app_config.set_default_case_dir(directory)
            app_config.save()
            QMessageBox.information(
                self,
                "Directory Saved",
                f"Default case directory set to:\n{directory}\n\n"
                "This directory will be used as the initial location when opening cases.",
            )

    def manage_case_library(self) -> None:
        from ui.case_library_dialog import CaseLibraryDialog

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
            "Reset Window Size",
            f"Reset window size to default ({DEFAULT_WINDOW_WIDTH}x{DEFAULT_WINDOW_HEIGHT})?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
            cfg = get_app_config()
            cfg.set_window_size(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
            cfg.save()
            QMessageBox.information(
                self,
                "Size Reset",
                f"Window size has been reset to default ({DEFAULT_WINDOW_WIDTH}x{DEFAULT_WINDOW_HEIGHT}).",
            )

    def reset_all_settings(self) -> None:
        from ui.reset_settings_dialog import ResetSettingsDialog

        dialog = ResetSettingsDialog(self)
        dialog.exec()
        if dialog.app_settings_reset:
            self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
