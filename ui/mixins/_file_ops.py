# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QMessageBox,
)

from foam.include_resolver import ResolvedInclude
from foam.nodes import FoamNode
from foam.parser import OpenFoamParser, ParseError
from foam.utils import is_large_non_foam_file, is_log_filename, is_script_text, read_foam_file
from i18n import tr
from services.case_files_config import CaseFilesConfig
from services.case_loader import FIELD_DIRS, list_case_files
from services.include_scan import (
    clear_scan_cache,
    included_files,
    resolve_directive_text,
    scan_includes,
)
from ui.layout_constants import (
    STATUS_NORMAL as _STATUS_NORMAL,
)
from ui.layout_constants import (
    STATUS_SHORT as _STATUS_SHORT,
)
from ui.layout_constants import (
    STATUS_WARNING as _STATUS_WARNING,
)
from ui.panels.file_list_panel import display_file_name

if TYPE_CHECKING:
    from ui.mixins._protocol import MainWindowProtocol as _Base
else:
    _Base = object


def _include_failure_message(resolved: ResolvedInclude) -> tuple[str, int]:
    """Return (status text, timeout) for an include that did not resolve.

    An optional include that is simply absent is legal OpenFOAM, so it reports
    plainly rather than as a warning.
    """
    if resolved.status == "missing_optional":
        return (
            tr("Optional include not present: {target}").format(target=resolved.ref.arg),
            _STATUS_SHORT,
        )
    if resolved.status == "no_installation":
        return (
            tr("No OpenFOAM installation found — #includeEtc/#includeFunc cannot be resolved."),
            _STATUS_WARNING,
        )
    return (
        tr("Include not found: {target}").format(target=resolved.ref.arg),
        _STATUS_WARNING,
    )


class _FileOpsMixin(_Base):
    """Per-file operations: load, save, parse; directory scan helpers."""

    # ── case directory load ───────────────────────────────────────────────────

    def _load_case_dir(self, directory: str) -> None:
        previous_dir = self.state.current_case_dir
        self.state.current_case_dir = directory
        self.state.case_files_config = CaseFilesConfig(directory)
        self._update_case_label()

        if self._case_dir_watcher.directories():
            self._case_dir_watcher.removePaths(self._case_dir_watcher.directories())
        self._case_dir_watcher.addPath(directory)
        constant_dir = str(Path(directory) / "constant")
        if Path(constant_dir).is_dir():
            self._case_dir_watcher.addPath(constant_dir)

        clear_scan_cache()  # the memos are per case; bound them on a switch
        paths, extra, extra_dir_paths, origins = self._case_file_paths(directory)
        self.file_list_panel.load_files(
            paths,
            case_dir=directory,
            extra_files=extra,
            extra_dirs=extra_dir_paths,
            included_files=origins,
        )

        self.state.file_buffers.clear()
        self.state.file_dirty.clear()
        self.state.parsed_roots.clear()
        self._clear_undo_stacks()
        if self.block_mesh_panel is not None:
            self.block_mesh_panel.clear()
        self._clear_current_file()
        if self.terminal_panel is not None:
            self.terminal_panel.set_working_directory(directory)
        if self._log_summary_dialog is not None:
            self._log_summary_dialog.set_case_dir(directory)
        self._stop_foam_monitor()
        self._reset_diff_for_case_dir(directory, previous_dir)
        QTimer.singleShot(0, self._reload_boundary_panel)

    def _case_file_paths(
        self, case_dir: str
    ) -> tuple[list[str], list[str] | None, list[str] | None, dict[str, str]]:
        """Return (paths, extra_files, extra_dir_paths, include origin labels).

        The case's own files come from ``list_case_files``; the targets of their
        ``#include`` directives are appended after it, so ``list_case_files``
        stays the pure case allow-list that ``services/case_copier`` and the
        Add-files dialog also rely on. Also refreshes
        ``state.read_only_files``, which gates every write path.
        """
        config = self.state.case_files_config
        extra = config.get_extra_files() or None if config else None
        extra_dirs = config.get_extra_dirs() or None if config else None
        paths = list_case_files(case_dir, extra, extra_dirs)
        extra_dir_paths = [p for p, _ in extra_dirs] if extra_dirs else None

        included, origins, read_only = included_files(case_dir, paths)
        self.state.read_only_files = read_only
        return paths + included, extra, extra_dir_paths, origins

    def _reload_file_list(self) -> None:
        if not self.state.current_case_dir or not self.state.case_files_config:
            return
        paths, extra, extra_dir_paths, origins = self._case_file_paths(
            self.state.current_case_dir
        )
        self.file_list_panel.load_files(
            paths,
            case_dir=self.state.current_case_dir,
            extra_files=extra,
            extra_dirs=extra_dir_paths,
            included_files=origins,
        )
        for path, dirty in self.state.file_dirty.items():
            if dirty:
                self.file_list_panel.mark_dirty(path, True)
        if self.state.current_file:
            self.file_list_panel.select_file(self.state.current_file)

    def _on_case_dir_changed_on_disk(self, path: str) -> None:
        self._file_list_refresh_timer.start()

    def _open_included_target(self, directive_text: str) -> None:
        """Open the file a `#include` directive refers to, reporting failures.

        Goes through the normal load path, refreshing the file list first when
        the target has no row yet so the selection has something to land on.
        """
        case_dir = self.state.current_case_dir
        source = self.state.current_file
        if not case_dir or not source:
            return

        resolved = resolve_directive_text(directive_text, source, case_dir)
        if resolved is None:
            return  # not an include directive (#eval, #codeStream, ...)

        if resolved.path is None:
            self.statusBar().showMessage(*_include_failure_message(resolved))
            return

        target = str(resolved.path)
        if not self.file_list_panel.has_file(target):
            self._reload_file_list()
        self.load_selected_file(target)
        self.file_list_panel.select_file(target)

    # ── load / save ───────────────────────────────────────────────────────────

    def _parse_and_update(self, path: str, text: str) -> OpenFoamParser:
        """Parse text, update the tree and side panels. Returns parser (check .errors). Raises ParseError."""
        _parser = OpenFoamParser(text)
        root = _parser.parse()
        self.state.parsed_roots[path] = root
        self._load_tree(root)
        self.state.current_model.set_include_notes(self._include_notes_for(path))
        self._update_viewer_panels(path, root)
        self._update_bm_side_by_side_btn()
        return _parser

    def _include_notes_for(self, path: str) -> dict[str, str]:
        """Tooltip notes for this file's `#include` rows, keyed by directive text.

        Reads the per-file scan memo rather than the disk, so showing a tooltip
        costs nothing.
        """
        case_dir = self.state.current_case_dir
        if not case_dir:
            return {}
        notes: dict[str, str] = {}
        for hit in scan_includes(case_dir, [path]):
            if hit.resolved.path is not None:
                notes[hit.text] = tr("resolves to {path}").format(path=hit.resolved.path)
            else:
                notes[hit.text] = _include_failure_message(hit.resolved)[0]
        return notes

    def load_selected_file(self, path: str) -> None:
        if path == self.state.current_file:
            return

        self._save_current_buffer()

        if path in self.state.file_buffers:
            text = self.state.file_buffers[path]
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
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
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
            self.state.file_buffers[path] = text
            self.state.file_dirty[path] = False

        try:
            self.state.current_file = path
            self.editor_panel.set_text(text)
            self.editor_panel.set_read_only(self._is_read_only(path))
            self.state.text_dirty = self.state.file_dirty.get(path, False)
            self._update_window_title()
            self._update_file_label()
            self.file_list_panel.mark_dirty(path, self.state.text_dirty)
            self.statusBar().showMessage(tr("Loaded: {path}").format(path=path), _STATUS_NORMAL)

            if is_script_text(text) or is_log_filename(Path(path).name):
                # Shell script (Allrun, …) or run log: text editing only, no tree.
                self.state.parsed_roots.pop(path, None)
                self._load_tree(FoamNode(name="root", node_type="dictionary"))
                self._update_bm_side_by_side_btn()
                self.detail_panel.show_empty()
                message = (
                    tr("Script file — text editing only: {path}")
                    if is_script_text(text)
                    else tr("Text file — no dictionary tree: {path}")
                )
                self.statusBar().showMessage(message.format(path=path), _STATUS_NORMAL)
                return
            try:
                _parser = self._parse_and_update(path, text)
                self.detail_panel.show_empty()
                if _parser.errors:
                    n = len(_parser.errors)
                    self.statusBar().showMessage(
                        tr("Parsed: {path} — {n} unrecognized {entries}").format(
                            path=path, n=n, entries=("entry" if n == 1 else "entries")
                        ),
                        _STATUS_WARNING,
                    )
                else:
                    self.statusBar().showMessage(
                        tr("Parsed successfully: {path}").format(path=path), _STATUS_NORMAL
                    )
            except ParseError as e:
                self.statusBar().showMessage(tr("Parse warning: {e}").format(e=e), _STATUS_WARNING)
                QMessageBox.warning(
                    self,
                    tr("Parse Warning"),
                    tr(
                        "Text was loaded, but tree update failed.\n\n{e}\n\n"
                        "You can continue editing in the text editor."
                    ).format(e=e),
                )

        except Exception as e:
            QMessageBox.critical(self, tr("Error"), str(e))

    def save_file(self) -> None:
        if not self.state.current_file:
            return
        if self._is_read_only(self.state.current_file):
            self.statusBar().showMessage(
                tr("Read-only file — outside the case directory: {name}").format(
                    name=Path(self.state.current_file).name
                ),
                _STATUS_WARNING,
            )
            return

        text = self.editor_panel.get_text()
        try:
            Path(self.state.current_file).write_text(text, encoding="utf-8")
            self.state.file_buffers[self.state.current_file] = text
            self.state.file_dirty[self.state.current_file] = False
            self.state.text_dirty = False
            self._update_window_title()
            self._update_file_label()
            self.file_list_panel.mark_dirty(self.state.current_file, False)
            self._reload_file_list()
            self.statusBar().showMessage(
                tr("Saved: {path}").format(path=self.state.current_file), _STATUS_NORMAL
            )

            if is_script_text(text) or is_log_filename(Path(self.state.current_file).name):
                return  # shell script or run log: no tree to refresh

            try:
                _parser = self._parse_and_update(self.state.current_file, text)
                if _parser.errors:
                    n = len(_parser.errors)
                    self.statusBar().showMessage(
                        tr("Saved: {path} — {n} unrecognized {entries}").format(
                            path=self.state.current_file,
                            n=n,
                            entries=("entry" if n == 1 else "entries"),
                        ),
                        _STATUS_WARNING,
                    )
                else:
                    self.statusBar().showMessage(
                        tr("Saved and parsed: {path}").format(path=self.state.current_file),
                        _STATUS_NORMAL,
                    )
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
        if self.state.current_file is not None:
            self.state.file_buffers[self.state.current_file] = self.editor_panel.get_text()
            self.state.file_dirty[self.state.current_file] = self.state.text_dirty

        # A read-only file should never be dirty (_mark_dirty refuses); filtering
        # here too keeps one stray flag from writing into the OpenFOAM install.
        dirty_paths = [
            p for p, dirty in self.state.file_dirty.items() if dirty and not self._is_read_only(p)
        ]
        if not dirty_paths:
            self.statusBar().showMessage(tr("No unsaved files."), _STATUS_SHORT)
            return

        saved = []
        failed = []
        for path in dirty_paths:
            text = self.state.file_buffers.get(path, "")
            try:
                Path(path).write_text(text, encoding="utf-8")
                self.state.file_buffers[path] = text
                self.state.file_dirty[path] = False
                self.file_list_panel.mark_dirty(path, False)
                saved.append(path)
            except Exception as e:
                failed.append((path, str(e)))

        if saved:
            self._reload_file_list()

        if self.state.current_file in saved:
            self.state.text_dirty = False
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
        if not self.state.current_case_dir:
            QMessageBox.information(self, tr("No Case Open"), tr("Please open a case first."))
            return
        config = CaseFilesConfig(self.state.current_case_dir)
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
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        config.delete_config_file()
        self._load_case_dir(self.state.current_case_dir)
        self.statusBar().showMessage(tr("File list reset to default."), _STATUS_SHORT)

    # ── scan-group / cache helpers ────────────────────────────────────────────

    def _on_add_time_dir(self, dir_name: str) -> None:
        if not self.state.case_files_config or not self.state.current_case_dir:
            return
        self.state.case_files_config.add_dir(dir_name)
        self.state.case_files_config.save()
        self._reload_file_list()
        self.statusBar().showMessage(tr("Added directory: {dir}/").format(dir=dir_name), _STATUS_SHORT)

    def _on_remove_extra_dir(self, rel_dir: str) -> None:
        if not self.state.case_files_config:
            return
        self.state.case_files_config.remove_dir(rel_dir)
        self.state.case_files_config.save()
        self._reload_file_list()
        self.statusBar().showMessage(
            tr("Removed directory from file list: {dir}/").format(dir=rel_dir), _STATUS_SHORT
        )

    def _purge_file_caches(self, path: str) -> None:
        self.state.file_buffers.pop(path, None)
        self.state.file_dirty.pop(path, None)
        self.state.parsed_roots.pop(path, None)

    def _is_auto_scan_group(self, group: str) -> bool:
        """Return True if group is fully scanned (FIELD_DIRS or extra dirs)."""
        if group.split("/")[0] in FIELD_DIRS:
            return True
        if self.state.case_files_config:
            return group in {p for p, _ in self.state.case_files_config.get_extra_dirs()}
        return False

