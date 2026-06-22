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

from foam.utils import read_foam_file
from i18n import tr
from services.case_files_config import CaseFilesConfig
from services.case_loader import list_case_files
from ui.panels.file_list_panel import display_file_name
from ui.layout_constants import (
    STATUS_NORMAL as _STATUS_NORMAL,
    STATUS_SHORT as _STATUS_SHORT,
    STATUS_WARNING as _STATUS_WARNING,
)


class _FileManagementOpsMixin:
    """File-management operations: create, add, backup, delete, duplicate, clean."""

    def _on_create_file_requested(self, case_dir: str, group: str) -> None:
        filename, ok = QInputDialog.getText(
            self,
            tr("New File"),
            tr("File name (will be created in {group}/):").format(group=group),
        )
        if not ok:
            return
        filename = filename.strip()
        if not filename:
            self.statusBar().showMessage(tr("File name must not be empty."), _STATUS_WARNING)
            return
        if "/" in filename or "\\" in filename:
            self.statusBar().showMessage(tr("File name must not contain path separators."), _STATUS_WARNING)
            return

        target = Path(case_dir) / group / filename
        if target.exists():
            self.statusBar().showMessage(tr("File already exists: {name}").format(name=target.name), _STATUS_WARNING)
            return

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(_foamfile_template(group, filename), encoding="utf-8")
        except OSError as e:
            QMessageBox.critical(self, tr("Create File Error"), tr("Could not create file:\n{e}").format(e=e))
            return

        if not self._is_auto_scan_group(group) and self.state.case_files_config:
            self.state.case_files_config.add_file(str(Path(group) / filename))
            self.state.case_files_config.save()

        self._reload_file_list()
        self.statusBar().showMessage(tr("Created: {group}/{filename}").format(group=group, filename=filename), _STATUS_SHORT)
        self.file_list_panel.select_file(str(target))

    def _on_add_file_requested(self, case_dir: str, group: str) -> None:
        from ui.dialogs.add_files_dialog import AddFilesDialog

        cfg = CaseFilesConfig(case_dir)
        extra = cfg.get_extra_files() or None
        extra_dirs = cfg.get_extra_dirs() or None
        loaded_set = set(list_case_files(case_dir, extra, extra_dirs or None))

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
        self.statusBar().showMessage(tr("Added {n} file(s) to the file list.").format(n=len(selected)), _STATUS_SHORT)

    def _create_backup(self, path: str) -> bool:
        """Write a .bak_<timestamp> copy. Returns True on success."""
        from datetime import datetime

        p = Path(path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = p.parent / f"{p.name}.bak_{timestamp}"

        if path in self.state.file_buffers:
            content = self.state.file_buffers[path]
            has_unsaved = self.state.file_dirty.get(path, False)
        else:
            try:
                content = read_foam_file(p)
            except Exception as e:
                QMessageBox.critical(self, tr("Backup Error"), tr("Could not read file:\n{e}").format(e=e))
                return False
            has_unsaved = False

        try:
            backup_path.write_text(content, encoding="utf-8")
        except Exception as e:
            QMessageBox.critical(self, tr("Backup Error"), tr("Could not write backup:\n{e}").format(e=e))
            return False

        rel = display_file_name(str(backup_path))
        suffix = tr(" (includes unsaved edits)") if has_unsaved else ""
        self.statusBar().showMessage(tr("Backup created: {rel}{suffix}").format(rel=rel, suffix=suffix), _STATUS_NORMAL)
        return True

    def _on_backup_file_requested(self, path: str) -> None:
        self._create_backup(path)

    def _on_manage_extra_files(self) -> None:
        if not self.state.case_files_config:
            return
        from ui.dialogs.manage_extra_files_dialog import ManageExtraFilesDialog

        old_dirs = self.state.case_files_config.get_extra_dirs()
        dlg = ManageExtraFilesDialog(
            self.state.case_files_config.get_extra_files(),
            extra_dirs=old_dirs,
            case_dir=self.state.current_case_dir,
            parent=self,
        )
        dlg.exec()

        changed = False
        for rel_path in dlg.removed_files:
            self.state.case_files_config.remove_file(rel_path)
            changed = True

        new_dirs = dlg.result_dirs
        old_dir_map = dict(old_dirs)
        old_paths = set(old_dir_map)
        new_paths = {p for p, _ in new_dirs}
        for p in old_paths - new_paths:
            self.state.case_files_config.remove_dir(p)
            changed = True
        for p, r in new_dirs:
            if p not in old_paths or old_dir_map.get(p) != r:
                self.state.case_files_config.add_dir(p, r)
                changed = True

        if changed:
            self.state.case_files_config.save()
            self._reload_file_list()
            parts = []
            if dlg.removed_files:
                parts.append(f"{len(dlg.removed_files)} file(s) removed")
            removed_n = len(old_paths - new_paths)
            added_n = len(new_paths - old_paths)
            toggled_n = sum(
                1 for p, r in new_dirs
                if p in old_paths and old_dir_map.get(p) != r
            )
            if removed_n:
                parts.append(f"{removed_n} directory(s) removed")
            if added_n:
                parts.append(f"{added_n} directory(s) added")
            if toggled_n:
                parts.append(f"{toggled_n} directory(s) updated")
            self.statusBar().showMessage(", ".join(parts) + ".", _STATUS_SHORT)

    def _on_remove_extra_file(self, abs_path: str) -> None:
        if not self.state.case_files_config or not self.state.current_case_dir:
            return
        try:
            rel = str(Path(abs_path).relative_to(Path(self.state.current_case_dir)))
        except ValueError:
            return
        self.state.case_files_config.remove_file(rel)
        self.state.case_files_config.save()
        self._reload_file_list()
        self.statusBar().showMessage(tr("Removed from extra files: {name}").format(name=display_file_name(abs_path)), _STATUS_SHORT)

    def _on_delete_file_requested(self, path: str) -> None:
        is_dirty = self.state.file_dirty.get(path, False) or (
            path == self.state.current_file and self.state.text_dirty
        )

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle(tr("Delete File"))
        msg.setText(f"Delete <b>{display_file_name(path)}</b> from disk?")
        info = tr("This action cannot be undone.")
        if is_dirty:
            info = tr("This file has unsaved changes.\nThis action cannot be undone.")
        msg.setInformativeText(info)

        backup_btn = msg.addButton(tr("Backup && Delete"), QMessageBox.ActionRole)
        delete_btn = msg.addButton(tr("Delete"), QMessageBox.DestructiveRole)
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
            QMessageBox.critical(self, tr("Delete Error"), tr("Could not delete file:\n{e}").format(e=e))
            return

        if self.state.case_files_config and self.state.current_case_dir:
            try:
                rel = str(Path(path).relative_to(Path(self.state.current_case_dir)))
                self.state.case_files_config.remove_file(rel)
                self.state.case_files_config.save()
            except ValueError:
                pass

        if path == self.state.current_file:
            self._clear_current_file()

        self._purge_file_caches(path)
        self._reload_file_list()
        self._reload_boundary_panel()
        self.statusBar().showMessage(tr("Deleted: {name}").format(name=display_file_name(path)), _STATUS_SHORT)

    def _on_duplicate_file_requested(self, path: str) -> None:
        p = Path(path)
        new_name, ok = QInputDialog.getText(
            self,
            tr("Duplicate File"),
            tr("New file name (in {dir}/):)").format(dir=p.parent.name),
            text=p.name,
        )
        if not ok:
            return
        new_name = new_name.strip()
        if not new_name:
            self.statusBar().showMessage(tr("File name must not be empty."), _STATUS_WARNING)
            return
        if "/" in new_name or "\\" in new_name:
            self.statusBar().showMessage(
                tr("File name must not contain path separators."), _STATUS_WARNING
            )
            return

        dest = p.parent / new_name
        if dest.exists():
            self.statusBar().showMessage(tr("File already exists: {name}").format(name=new_name), _STATUS_WARNING)
            return

        if self.state.file_dirty.get(path, False):
            msg = QMessageBox(self)
            msg.setWindowTitle(tr("Unsaved Changes"))
            msg.setText(tr("{name} has unsaved changes.").format(name=display_file_name(path)))
            msg.setInformativeText(tr("How would you like to duplicate this file?"))
            save_btn = msg.addButton(tr("Save and Duplicate"), QMessageBox.AcceptRole)
            msg.addButton(tr("Duplicate with Unsaved Changes"), QMessageBox.ActionRole)
            msg.addButton(QMessageBox.Cancel)
            msg.exec()
            clicked = msg.clickedButton()
            if clicked is None or msg.buttonRole(clicked) == QMessageBox.RejectRole:
                return
            if clicked == save_btn:
                self.save_file()

        content = self.state.file_buffers.get(path)
        if content is None:
            try:
                content = read_foam_file(p)
            except Exception as e:
                QMessageBox.critical(self, tr("Duplicate Error"), tr("Could not read file:\n{e}").format(e=e))
                return

        content = re.sub(r'(object\s+)\S+;', rf'\g<1>{new_name};', content, count=1)

        try:
            dest.write_text(content, encoding="utf-8")
        except OSError as e:
            QMessageBox.critical(self, tr("Duplicate Error"), tr("Could not write file:\n{e}").format(e=e))
            return

        if self.state.current_case_dir and self.state.case_files_config:
            try:
                rel = dest.relative_to(Path(self.state.current_case_dir))
                group = str(rel.parent) if rel.parent.parts else ""
                if not self._is_auto_scan_group(group):
                    self.state.case_files_config.add_file(str(rel))
                    self.state.case_files_config.save()
            except ValueError:
                pass

        self._reload_file_list()
        self.statusBar().showMessage(tr("Duplicated: {src} → {dst}").format(src=p.name, dst=new_name), _STATUS_SHORT)
        self.file_list_panel.select_file(str(dest))

    def _on_duplicate_dir_requested(self, case_dir: str, src: str, dst: str) -> None:
        src_path = Path(case_dir) / src
        dst_path = Path(case_dir) / dst
        reply = QMessageBox.question(
            self,
            tr("Duplicate Directory"),
            tr("Duplicate '{src}/' to '{dst}/'?\n\nSource:      {src_path}\nDestination: {dst_path}").format(src=src, dst=dst, src_path=src_path, dst_path=dst_path),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            shutil.copytree(str(src_path), str(dst_path))
        except Exception as e:
            QMessageBox.critical(self, tr("Duplicate Error"), tr("Failed to duplicate directory:\n{e}").format(e=e))
            return
        self._reload_file_list()
        self.statusBar().showMessage(tr("Duplicated: {src} → {dst}").format(src=src+"/", dst=dst+"/"), _STATUS_SHORT)

    def _on_delete_dir_requested(self, case_dir: str, group: str) -> None:
        dir_path = Path(case_dir) / group
        orig_path = Path(case_dir) / "0.orig"

        if not orig_path.exists():
            QMessageBox.warning(
                self,
                tr("Cannot Delete"),
                tr("The '0.orig' directory does not exist.\n\nDeletion aborted to prevent data loss."),
            )
            return

        reply = QMessageBox.warning(
            self,
            tr("Delete Directory"),
            tr("Delete the '{group}/' directory and all its contents?\n\n{path}\n\nThis cannot be undone.").format(group=group, path=dir_path),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        affected = [p for p in list(self.state.file_buffers) if Path(p).is_relative_to(dir_path)]
        for path in affected:
            if path == self.state.current_file:
                self._clear_current_file()
            self._purge_file_caches(path)

        try:
            shutil.rmtree(str(dir_path))
        except OSError as e:
            QMessageBox.critical(self, tr("Delete Error"), tr("Could not delete directory:\n{e}").format(e=e))
            return

        self._reload_file_list()
        self._reload_boundary_panel()
        self.statusBar().showMessage(tr("Deleted: {name}").format(name=group+"/"), _STATUS_SHORT)

    def _on_clean_backups(self) -> None:
        if not self.state.current_case_dir:
            return
        from ui.dialogs.clean_backups_dialog import CleanBackupsDialog, find_backup_files

        backups = find_backup_files(self.state.current_case_dir)
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
            self._purge_file_caches(path)
            if self.state.case_files_config and self.state.current_case_dir:
                try:
                    rel = str(Path(path).relative_to(Path(self.state.current_case_dir)))
                    self.state.case_files_config.remove_file(rel)
                except ValueError:
                    pass
            if path == self.state.current_file:
                self._clear_current_file()

        if self.state.case_files_config:
            self.state.case_files_config.save()

        self._reload_file_list()
        self._reload_boundary_panel()

        if errors:
            QMessageBox.warning(
                self,
                tr("Delete Errors"),
                tr("Some files could not be deleted:\n{errors}").format(errors="\n".join(errors)),
            )

        self.statusBar().showMessage(tr("Deleted {n} backup file(s).").format(n=deleted_count), _STATUS_SHORT)


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
