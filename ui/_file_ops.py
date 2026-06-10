# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QMessageBox,
)

from foam.parser import OpenFoamParser, ParseError
from i18n import tr
from foam.utils import read_foam_file, is_large_non_foam_file
from services.case_files_config import CaseFilesConfig
from services.case_loader import FIELD_DIRS, list_case_files
from ui.file_list_panel import display_file_name
from ui.layout_constants import (
    BLOCKMESH_DICT_NAME as _BLOCKMESH_DICT_NAME,
    STATUS_NORMAL as _STATUS_NORMAL,
    STATUS_WARNING as _STATUS_WARNING,
    STATUS_SHORT as _STATUS_SHORT,
)


class _FileOpsMixin:
    """Per-file operations: load, save, parse; directory scan helpers."""

    # ── case directory load ───────────────────────────────────────────────────

    def _load_case_dir(self, directory: str) -> None:
        self.current_case_dir = directory
        self._case_files_config = CaseFilesConfig(directory)
        self._update_case_label()

        extra = self._case_files_config.get_extra_files() or None
        extra_dirs = self._case_files_config.get_extra_dirs() or None
        paths = list_case_files(directory, extra, extra_dirs)
        extra_dir_paths = [p for p, _ in extra_dirs] if extra_dirs else None
        self.file_list_panel.load_files(
            paths, case_dir=directory, extra_files=extra, extra_dirs=extra_dir_paths
        )

        self.file_buffers.clear()
        self.file_dirty.clear()
        self._parsed_roots.clear()
        self._clear_current_file()
        if self.terminal_panel is not None:
            self.terminal_panel.set_working_directory(directory)
        self._stop_foam_monitor()
        QTimer.singleShot(0, self._reload_boundary_panel)

    def _reload_file_list(self) -> None:
        if not self.current_case_dir or not self._case_files_config:
            return
        extra = self._case_files_config.get_extra_files() or None
        extra_dirs = self._case_files_config.get_extra_dirs() or None
        paths = list_case_files(self.current_case_dir, extra, extra_dirs)
        extra_dir_paths = [p for p, _ in extra_dirs] if extra_dirs else None
        self.file_list_panel.load_files(
            paths,
            case_dir=self.current_case_dir,
            extra_files=extra,
            extra_dirs=extra_dir_paths,
        )
        for path, dirty in self.file_dirty.items():
            if dirty:
                self.file_list_panel.mark_dirty(path, True)
        if self.current_file:
            self.file_list_panel.select_file(self.current_file)

    # ── load / save ───────────────────────────────────────────────────────────

    def _parse_and_update(self, path: str, text: str) -> OpenFoamParser:
        """Parse text, update the tree and side panels. Returns parser (check .errors). Raises ParseError."""
        _parser = OpenFoamParser(text)
        root = _parser.parse()
        self._parsed_roots[path] = root
        self._load_tree(root)
        self.boundary_panel.update_field(path, root)
        if self.block_mesh_panel is not None and Path(path).name == _BLOCKMESH_DICT_NAME:
            self.block_mesh_panel.update_block_mesh(path, root)
        self._update_bm_side_by_side_btn()
        return _parser

    def load_selected_file(self, path: str) -> None:
        if path == self.current_file:
            return

        self._save_current_buffer()

        if path in self.file_buffers:
            text = self.file_buffers[path]
        else:
            large_non_foam, size_bytes = is_large_non_foam_file(path)
            if large_non_foam:
                size_kb = size_bytes // 1024
                reply = QMessageBox.question(
                    self,
                    tr("Large Non-Dictionary File"),
                    tr(
                        "'{name}' does not appear to be an OpenFOAM dictionary ({size} KB).\n"
                        "The tree view will not be available.\n"
                        "Loading may take a while — the application will not respond during this time.\n\n"
                        "Open anyway?"
                    ).format(name=Path(path).name, size=size_kb),
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if reply != QMessageBox.Yes:
                    return
                self.statusBar().showMessage(
                    tr("Loading large file: {name} — please wait…").format(name=Path(path).name),
                    _STATUS_SHORT,
                )
            try:
                text = read_foam_file(path)
            except Exception as e:
                QMessageBox.critical(self, tr("Error"), str(e))
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
            self.statusBar().showMessage(tr("Loaded: {path}").format(path=path), _STATUS_NORMAL)

            try:
                _parser = self._parse_and_update(path, text)
                self.detail_panel.show_empty()
                if _parser.errors:
                    n = len(_parser.errors)
                    self.statusBar().showMessage(
                        tr("Parsed: {path} — {n} unrecognized {entries}").format(path=path, n=n, entries=("entry" if n == 1 else "entries")),
                        _STATUS_WARNING,
                    )
                else:
                    self.statusBar().showMessage(tr("Parsed successfully: {path}").format(path=path), _STATUS_NORMAL)
            except ParseError as e:
                self.statusBar().showMessage(tr("Parse warning: {e}").format(e=e), _STATUS_WARNING)
                QMessageBox.warning(
                    self,
                    tr("Parse Warning"),
                    tr("Text was loaded, but tree update failed.\n\n{e}\n\nYou can continue editing in the text editor.").format(e=e),
                )

        except Exception as e:
            QMessageBox.critical(self, tr("Error"), str(e))

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
            self.statusBar().showMessage(tr("Saved: {path}").format(path=self.current_file), _STATUS_NORMAL)

            try:
                _parser = self._parse_and_update(self.current_file, text)
                if _parser.errors:
                    n = len(_parser.errors)
                    self.statusBar().showMessage(
                        tr("Saved: {path} — {n} unrecognized {entries}").format(path=self.current_file, n=n, entries=("entry" if n == 1 else "entries")),
                        _STATUS_WARNING,
                    )
                else:
                    self.statusBar().showMessage(tr("Saved and parsed: {path}").format(path=self.current_file), _STATUS_NORMAL)
            except ParseError as e:
                self.statusBar().showMessage(tr("Saved, but parse failed: {e}").format(e=e), _STATUS_WARNING)
                QMessageBox.warning(
                    self,
                    tr("Saved with Parse Warning"),
                    tr("File was saved as text, but tree refresh failed.\n\n{e}").format(e=e),
                )

        except Exception as e:
            QMessageBox.critical(self, tr("Save Error"), str(e))

    def save_all_files(self) -> None:
        if self.current_file is not None:
            self.file_buffers[self.current_file] = self.editor_panel.get_text()
            self.file_dirty[self.current_file] = self.text_dirty

        dirty_paths = [p for p, dirty in self.file_dirty.items() if dirty]
        if not dirty_paths:
            self.statusBar().showMessage(tr("No unsaved files."), _STATUS_SHORT)
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
                tr("Save All - Partial Failure"),
                tr("Failed to save the following files:\n{files}").format(files=failed_names),
            )
        else:
            self.statusBar().showMessage(tr("Saved {n} file(s).").format(n=len(saved)), _STATUS_NORMAL)

    # ── file list settings ────────────────────────────────────────────────────

    def reset_file_list(self) -> None:
        if not self.current_case_dir:
            QMessageBox.information(self, tr("No Case Open"), tr("Please open a case first."))
            return
        config = CaseFilesConfig(self.current_case_dir)
        if not config.exists:
            self.statusBar().showMessage(tr("No extra files configured for this case."), _STATUS_SHORT)
            return
        reply = QMessageBox.question(
            self,
            tr("Reset File List"),
            tr(
                "Remove all user-added files and directories from the file list for this case?\n"
                "The .foam-editor-files.json file will be deleted."
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        config.delete_config_file()
        self._load_case_dir(self.current_case_dir)
        self.statusBar().showMessage(tr("File list reset to default."), _STATUS_SHORT)

    # ── scan-group / cache helpers ────────────────────────────────────────────

    def _on_add_time_dir(self, dir_name: str) -> None:
        if not self._case_files_config or not self.current_case_dir:
            return
        self._case_files_config.add_dir(dir_name)
        self._case_files_config.save()
        self._reload_file_list()
        self.statusBar().showMessage(tr("Added directory: {dir}/").format(dir=dir_name), _STATUS_SHORT)

    def _on_remove_extra_dir(self, rel_dir: str) -> None:
        if not self._case_files_config:
            return
        self._case_files_config.remove_dir(rel_dir)
        self._case_files_config.save()
        self._reload_file_list()
        self.statusBar().showMessage(tr("Removed directory from file list: {dir}/").format(dir=rel_dir), _STATUS_SHORT)

    def _purge_file_caches(self, path: str) -> None:
        self.file_buffers.pop(path, None)
        self.file_dirty.pop(path, None)
        self._parsed_roots.pop(path, None)

    def _is_auto_scan_group(self, group: str) -> bool:
        """Return True if group is fully scanned (FIELD_DIRS or extra dirs)."""
        if group.split("/")[0] in FIELD_DIRS:
            return True
        if self._case_files_config:
            return group in {p for p, _ in self._case_files_config.get_extra_dirs()}
        return False

