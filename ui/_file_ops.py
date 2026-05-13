# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import re
import shutil
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QInputDialog,
    QMessageBox,
)

from foam.parser import OpenFoamParser, ParseError
from services.case_files_config import CaseFilesConfig
from services.case_loader import FIELD_DIRS, list_case_files
from ui.file_list_panel import display_file_name
from ui.layout_constants import (
    STATUS_NORMAL as _STATUS_NORMAL,
    STATUS_WARNING as _STATUS_WARNING,
    STATUS_SHORT as _STATUS_SHORT,
)


class _FileOpsMixin:
    """Per-file operations: load, save, create, duplicate, delete, backup."""

    # ── case directory load ───────────────────────────────────────────────────

    def _load_case_dir(self, directory: str) -> None:
        self.current_case_dir = directory
        self._case_files_config = CaseFilesConfig(directory)
        self._update_case_label()

        extra = self._case_files_config.get_extra_files() or None
        extra_dirs = self._case_files_config.get_extra_dirs() or None
        paths = list_case_files(directory, extra, extra_dirs)
        self.file_list_panel.load_files(
            paths, case_dir=directory, extra_files=extra, extra_dirs=extra_dirs
        )

        self.file_buffers.clear()
        self.file_dirty.clear()
        self._parsed_roots.clear()
        self._clear_current_file()
        self.terminal_panel.set_working_directory(directory)
        self._reload_boundary_panel()

    def _reload_file_list(self) -> None:
        if not self.current_case_dir or not self._case_files_config:
            return
        extra = self._case_files_config.get_extra_files() or None
        extra_dirs = self._case_files_config.get_extra_dirs() or None
        paths = list_case_files(self.current_case_dir, extra, extra_dirs)
        self.file_list_panel.load_files(
            paths,
            case_dir=self.current_case_dir,
            extra_files=extra,
            extra_dirs=extra_dirs,
        )
        for path, dirty in self.file_dirty.items():
            if dirty:
                self.file_list_panel.mark_dirty(path, True)
        if self.current_file:
            self.file_list_panel.select_file(self.current_file)

    # ── load / save ───────────────────────────────────────────────────────────

    def load_selected_file(self, path: str) -> None:
        if path == self.current_file:
            return

        self._save_current_buffer()

        if path in self.file_buffers:
            text = self.file_buffers[path]
        else:
            try:
                text = Path(path).read_text(encoding="utf-8")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
                return
            self.file_buffers[path] = text
            self.file_dirty[path] = False

        try:
            self.current_file = path
            self.editor_panel.set_text(text)
            self.text_dirty = self.file_dirty.get(path, False)
            self._update_window_title()
            self._update_file_label()
            self.file_list_panel.mark_dirty(path, self.text_dirty)
            self.statusBar().showMessage(f"Loaded: {path}", _STATUS_NORMAL)

            try:
                root = OpenFoamParser(text).parse()
                self._parsed_roots[path] = root
                self._load_tree(root)
                self.boundary_panel.update_field(path, root)
                self.detail_panel.show_empty()
                self.statusBar().showMessage(f"Parsed successfully: {path}", _STATUS_NORMAL)
            except ParseError as e:
                self.statusBar().showMessage(f"Parse warning: {e}", _STATUS_WARNING)
                QMessageBox.warning(
                    self,
                    "Parse Warning",
                    "Text was loaded, but tree update failed.\n\n"
                    f"{e}\n\n"
                    "You can continue editing in the text editor.",
                )

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def save_file(self) -> None:
        if not self.current_file:
            return

        text = self.editor_panel.get_text()
        try:
            Path(self.current_file).write_text(text, encoding="utf-8")
            self.file_buffers[self.current_file] = text
            self.file_dirty[self.current_file] = False
            self.text_dirty = False
            self._update_window_title()
            self._update_file_label()
            self.file_list_panel.mark_dirty(self.current_file, False)
            self.statusBar().showMessage(f"Saved: {self.current_file}", _STATUS_NORMAL)

            try:
                root = OpenFoamParser(text).parse()
                self._parsed_roots[self.current_file] = root
                self._load_tree(root)
                self.boundary_panel.update_field(self.current_file, root)
                self.statusBar().showMessage(f"Saved and parsed: {self.current_file}", _STATUS_NORMAL)
            except ParseError as e:
                self.statusBar().showMessage(f"Saved, but parse failed: {e}", _STATUS_WARNING)
                QMessageBox.warning(
                    self,
                    "Saved with Parse Warning",
                    f"File was saved as text, but tree refresh failed.\n\n{e}",
                )

        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))

    def save_all_files(self) -> None:
        if self.current_file is not None:
            self.file_buffers[self.current_file] = self.editor_panel.get_text()
            self.file_dirty[self.current_file] = self.text_dirty

        dirty_paths = [p for p, dirty in self.file_dirty.items() if dirty]
        if not dirty_paths:
            self.statusBar().showMessage("No unsaved files.", _STATUS_SHORT)
            return

        saved = []
        failed = []
        for path in dirty_paths:
            text = self.file_buffers.get(path, "")
            try:
                Path(path).write_text(text, encoding="utf-8")
                self.file_buffers[path] = text
                self.file_dirty[path] = False
                self.file_list_panel.mark_dirty(path, False)
                saved.append(path)
            except Exception as e:
                failed.append((path, str(e)))

        if self.current_file in saved:
            self.text_dirty = False
            self._update_window_title()
            self._update_file_label()

        if failed:
            failed_names = ", ".join(display_file_name(p) for p, _ in failed)
            QMessageBox.warning(
                self,
                "Save All - Partial Failure",
                f"Failed to save the following files:\n{failed_names}",
            )
        else:
            self.statusBar().showMessage(f"Saved {len(saved)} file(s).", _STATUS_NORMAL)

    # ── file list settings ────────────────────────────────────────────────────

    def reset_file_list(self) -> None:
        if not self.current_case_dir:
            QMessageBox.information(self, "No Case Open", "Please open a case first.")
            return
        config = CaseFilesConfig(self.current_case_dir)
        if not config.exists:
            self.statusBar().showMessage("No extra files configured for this case.", _STATUS_SHORT)
            return
        reply = QMessageBox.question(
            self,
            "Reset File List",
            "Remove all user-added files and directories from the file list for this case?\n"
            "The .foam-editor-files.json file will be deleted.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        config.delete_config_file()
        self._load_case_dir(self.current_case_dir)
        self.statusBar().showMessage("File list reset to default.", _STATUS_SHORT)

    # ── file list panel signals ───────────────────────────────────────────────

    def _on_create_file_requested(self, case_dir: str, group: str) -> None:
        filename, ok = QInputDialog.getText(
            self,
            "New File",
            f"File name (will be created in {group}/):",
        )
        if not ok:
            return
        filename = filename.strip()
        if not filename:
            self.statusBar().showMessage("File name must not be empty.", _STATUS_WARNING)
            return
        if "/" in filename or "\\" in filename:
            self.statusBar().showMessage(
                "File name must not contain path separators.", _STATUS_WARNING
            )
            return

        target = Path(case_dir) / group / filename
        if target.exists():
            self.statusBar().showMessage(
                f"File already exists: {target.name}", _STATUS_WARNING
            )
            return

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(_foamfile_template(group, filename), encoding="utf-8")
        except OSError as e:
            QMessageBox.critical(self, "Create File Error", f"Could not create file:\n{e}")
            return

        if not self._is_auto_scan_group(group) and self._case_files_config:
            self._case_files_config.add_file(str(Path(group) / filename))
            self._case_files_config.save()

        self._reload_file_list()
        self.statusBar().showMessage(f"Created: {group}/{filename}", _STATUS_SHORT)
        self.file_list_panel.select_file(str(target))

    def _on_add_file_requested(self, case_dir: str, group: str) -> None:
        from ui.add_files_dialog import AddFilesDialog

        cfg = CaseFilesConfig(case_dir)
        extra = cfg.get_extra_files() or None
        extra_dirs = cfg.get_extra_dirs() or None
        loaded_set = set(list_case_files(case_dir, extra, extra_dirs))

        dialog = AddFilesDialog(case_dir, group, loaded_set, self)
        if dialog.exec() != QDialog.Accepted:
            return

        selected = dialog.selected_paths
        if not selected:
            return

        base = Path(case_dir)
        config = CaseFilesConfig(case_dir)
        for abs_path in selected:
            try:
                rel = str(Path(abs_path).relative_to(base))
                config.add_file(rel)
            except ValueError:
                pass
        config.save()
        self._load_case_dir(case_dir)
        self.statusBar().showMessage(
            f"Added {len(selected)} file(s) to the file list.", _STATUS_SHORT
        )

    def _create_backup(self, path: str) -> bool:
        """Write a .bak_<timestamp> copy. Returns True on success."""
        from datetime import datetime

        p = Path(path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = p.parent / f"{p.name}.bak_{timestamp}"

        if path in self.file_buffers:
            content = self.file_buffers[path]
            has_unsaved = self.file_dirty.get(path, False)
        else:
            try:
                content = p.read_text(encoding="utf-8")
            except Exception as e:
                QMessageBox.critical(self, "Backup Error", f"Could not read file:\n{e}")
                return False
            has_unsaved = False

        try:
            backup_path.write_text(content, encoding="utf-8")
        except Exception as e:
            QMessageBox.critical(self, "Backup Error", f"Could not write backup:\n{e}")
            return False

        rel = display_file_name(str(backup_path))
        suffix = " (includes unsaved edits)" if has_unsaved else ""
        self.statusBar().showMessage(f"Backup created: {rel}{suffix}", _STATUS_NORMAL)
        return True

    def _on_backup_file_requested(self, path: str) -> None:
        self._create_backup(path)

    def _on_manage_extra_files(self) -> None:
        if not self._case_files_config:
            return
        from ui.manage_extra_files_dialog import ManageExtraFilesDialog

        dlg = ManageExtraFilesDialog(
            self._case_files_config.get_extra_files(),
            extra_dirs=self._case_files_config.get_extra_dirs(),
            case_dir=self.current_case_dir,
            parent=self,
        )
        dlg.exec()

        changed = False
        for rel_path in dlg.removed_files:
            self._case_files_config.remove_file(rel_path)
            changed = True
        for rel_dir in dlg.removed_dirs:
            self._case_files_config.remove_dir(rel_dir)
            changed = True
        for rel_dir in dlg.added_dirs:
            self._case_files_config.add_dir(rel_dir)
            changed = True

        if changed:
            self._case_files_config.save()
            self._reload_file_list()
            parts = []
            if dlg.removed_files:
                parts.append(f"{len(dlg.removed_files)} file(s) removed")
            if dlg.removed_dirs:
                parts.append(f"{len(dlg.removed_dirs)} directory(s) removed")
            if dlg.added_dirs:
                parts.append(f"{len(dlg.added_dirs)} directory(s) added")
            self.statusBar().showMessage(", ".join(parts) + ".", _STATUS_SHORT)

    def _on_remove_extra_file(self, abs_path: str) -> None:
        if not self._case_files_config or not self.current_case_dir:
            return
        try:
            rel = str(Path(abs_path).relative_to(Path(self.current_case_dir)))
        except ValueError:
            return
        self._case_files_config.remove_file(rel)
        self._case_files_config.save()
        self._reload_file_list()
        self.statusBar().showMessage(
            f"Removed from extra files: {display_file_name(abs_path)}", _STATUS_SHORT
        )

    def _on_add_time_dir(self, dir_name: str) -> None:
        if not self._case_files_config or not self.current_case_dir:
            return
        self._case_files_config.add_dir(dir_name)
        self._case_files_config.save()
        self._reload_file_list()
        self.statusBar().showMessage(f"Added directory: {dir_name}/", _STATUS_SHORT)

    def _on_remove_extra_dir(self, rel_dir: str) -> None:
        if not self._case_files_config:
            return
        self._case_files_config.remove_dir(rel_dir)
        self._case_files_config.save()
        self._reload_file_list()
        self.statusBar().showMessage(
            f"Removed directory from file list: {rel_dir}/", _STATUS_SHORT
        )

    def _is_auto_scan_group(self, group: str) -> bool:
        """Return True if group is fully scanned (FIELD_DIRS or extra dirs)."""
        if group.split("/")[0] in FIELD_DIRS:
            return True
        if self._case_files_config:
            return group in set(self._case_files_config.get_extra_dirs())
        return False

    def _on_delete_file_requested(self, path: str) -> None:
        is_dirty = self.file_dirty.get(path, False) or (
            path == self.current_file and self.text_dirty
        )

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Delete File")
        msg.setText(f"Delete <b>{display_file_name(path)}</b> from disk?")
        info = "This action cannot be undone."
        if is_dirty:
            info = "This file has unsaved changes.\n" + info
        msg.setInformativeText(info)

        backup_btn = msg.addButton("Backup && Delete", QMessageBox.ActionRole)
        delete_btn = msg.addButton("Delete", QMessageBox.DestructiveRole)
        cancel_btn = msg.addButton(QMessageBox.Cancel)
        msg.setDefaultButton(cancel_btn)
        msg.setEscapeButton(cancel_btn)

        msg.exec()
        clicked = msg.clickedButton()
        if clicked is None or clicked is cancel_btn:
            return

        if clicked is backup_btn:
            if not self._create_backup(path):
                return

        try:
            Path(path).unlink()
        except OSError as e:
            QMessageBox.critical(self, "Delete Error", f"Could not delete file:\n{e}")
            return

        self.file_buffers.pop(path, None)
        self.file_dirty.pop(path, None)

        if self._case_files_config and self.current_case_dir:
            try:
                rel = str(Path(path).relative_to(Path(self.current_case_dir)))
                self._case_files_config.remove_file(rel)
                self._case_files_config.save()
            except ValueError:
                pass

        if path == self.current_file:
            self._clear_current_file()

        self._parsed_roots.pop(path, None)
        self._reload_file_list()
        self._reload_boundary_panel()
        self.statusBar().showMessage(f"Deleted: {display_file_name(path)}", _STATUS_SHORT)

    def _on_duplicate_file_requested(self, path: str) -> None:
        p = Path(path)
        new_name, ok = QInputDialog.getText(
            self,
            "Duplicate File",
            f"New file name (in {p.parent.name}/):",
            text=p.name,
        )
        if not ok:
            return
        new_name = new_name.strip()
        if not new_name:
            self.statusBar().showMessage("File name must not be empty.", _STATUS_WARNING)
            return
        if "/" in new_name or "\\" in new_name:
            self.statusBar().showMessage(
                "File name must not contain path separators.", _STATUS_WARNING
            )
            return

        dest = p.parent / new_name
        if dest.exists():
            self.statusBar().showMessage(f"File already exists: {new_name}", _STATUS_WARNING)
            return

        if self.file_dirty.get(path, False):
            msg = QMessageBox(self)
            msg.setWindowTitle("Unsaved Changes")
            msg.setText(f"{display_file_name(path)} has unsaved changes.")
            msg.setInformativeText("How would you like to duplicate this file?")
            save_btn = msg.addButton("Save and Duplicate", QMessageBox.AcceptRole)
            msg.addButton("Duplicate with Unsaved Changes", QMessageBox.ActionRole)
            msg.addButton(QMessageBox.Cancel)
            msg.exec()
            clicked = msg.clickedButton()
            if clicked is None or msg.buttonRole(clicked) == QMessageBox.RejectRole:
                return
            if clicked == save_btn:
                self.save_file()

        content = self.file_buffers.get(path)
        if content is None:
            try:
                content = p.read_text(encoding="utf-8")
            except Exception as e:
                QMessageBox.critical(self, "Duplicate Error", f"Could not read file:\n{e}")
                return

        content = re.sub(r'(object\s+)\S+;', rf'\g<1>{new_name};', content, count=1)

        try:
            dest.write_text(content, encoding="utf-8")
        except OSError as e:
            QMessageBox.critical(self, "Duplicate Error", f"Could not write file:\n{e}")
            return

        if self.current_case_dir and self._case_files_config:
            try:
                rel = dest.relative_to(Path(self.current_case_dir))
                group = str(rel.parent) if rel.parent.parts else ""
                if not self._is_auto_scan_group(group):
                    self._case_files_config.add_file(str(rel))
                    self._case_files_config.save()
            except ValueError:
                pass

        self._reload_file_list()
        self.statusBar().showMessage(f"Duplicated: {p.name} → {new_name}", _STATUS_SHORT)
        self.file_list_panel.select_file(str(dest))

    def _on_duplicate_dir_requested(self, case_dir: str, src: str, dst: str) -> None:
        src_path = Path(case_dir) / src
        dst_path = Path(case_dir) / dst
        reply = QMessageBox.question(
            self,
            "Duplicate Directory",
            f"Duplicate '{src}/' to '{dst}/'?\n\nSource:      {src_path}\nDestination: {dst_path}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            shutil.copytree(str(src_path), str(dst_path))
        except Exception as e:
            QMessageBox.critical(self, "Duplicate Error", f"Failed to duplicate directory:\n{e}")
            return
        self._reload_file_list()
        self.statusBar().showMessage(f"Duplicated: {src}/ → {dst}/", _STATUS_SHORT)

    def _on_clean_backups(self) -> None:
        if not self.current_case_dir:
            return
        from ui.clean_backups_dialog import CleanBackupsDialog, find_backup_files

        backups = find_backup_files(self.current_case_dir)
        dlg = CleanBackupsDialog(backups, parent=self)
        if dlg.exec() != QDialog.Accepted:
            return

        paths = dlg.paths_to_delete
        if not paths:
            return

        errors: list[str] = []
        deleted_count = 0
        for path in paths:
            try:
                Path(path).unlink()
                deleted_count += 1
            except OSError as e:
                errors.append(f"{Path(path).name}: {e}")

        for path in paths:
            self.file_buffers.pop(path, None)
            self.file_dirty.pop(path, None)
            self._parsed_roots.pop(path, None)
            if self._case_files_config and self.current_case_dir:
                try:
                    rel = str(Path(path).relative_to(Path(self.current_case_dir)))
                    self._case_files_config.remove_file(rel)
                except ValueError:
                    pass
            if path == self.current_file:
                self._clear_current_file()

        if self._case_files_config:
            self._case_files_config.save()

        self._reload_file_list()
        self._reload_boundary_panel()

        if errors:
            QMessageBox.warning(
                self,
                "Delete Errors",
                "Some files could not be deleted:\n" + "\n".join(errors),
            )

        self.statusBar().showMessage(
            f"Deleted {deleted_count} backup file(s).", _STATUS_SHORT
        )


def _foamfile_template(group: str, filename: str) -> str:
    """Return a minimal FoamFile dictionary header for a newly created file."""
    return (
        "FoamFile\n"
        "{\n"
        "    version     2.0;\n"
        "    format      ascii;\n"
        "    class       dictionary;\n"
        f'    location    "{group}";\n'
        f"    object      {filename};\n"
        "}\n"
        "// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //\n"
    )
