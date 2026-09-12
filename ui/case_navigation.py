# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Shared controller behind the Cases tab and the Case Browser window.

One navigator owns one CaseTreeModel, one current location and every signal the
two views raise, so neither view knows the other exists and neither owns any
operation logic. MainWindow connects the signals once; the widgets only emit.

Translatable prose lives here rather than in model/ or services/ because
tests/test_i18n.py scans ui/ only -- a tr() literal in a lower layer would never
be checked against i18n/ja.py and would ship untranslated in silence. That is
also why services/case_fs_ops.py returns a Refusal code and this module turns it
into a sentence.
"""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from app_config import get_app_config
from i18n import tr
from model.case_tree_model import CaseTreeModel
from services.case_fs_ops import Refusal
from services.case_scan import DirEntry, case_summary


def refusal_message(refusal: Refusal, detail: str = "") -> str:
    """Turn a services/case_fs_ops refusal code into a translated sentence."""
    if refusal is Refusal.DESTINATION_EXISTS:
        return tr("'{name}' already exists there.").format(name=detail)
    if refusal is Refusal.INTO_OWN_SUBTREE:
        return tr("A folder cannot be moved or copied into itself.")
    if refusal is Refusal.SAME_PATH:
        return tr("The source and the destination are the same folder.")
    if refusal is Refusal.NOT_A_DIRECTORY:
        return tr("'{name}' is not a folder.").format(name=detail)
    if refusal is Refusal.SOURCE_MISSING:
        return tr("'{name}' no longer exists.").format(name=detail)
    if refusal is Refusal.PROTECTED_PATH:
        return tr("'{name}' is protected and cannot be changed from here.").format(name=detail)
    if refusal is Refusal.NAME_HAS_SEPARATOR:
        return tr("A name cannot contain a path separator.")
    if refusal is Refusal.NAME_EMPTY:
        return tr("Enter a name.")
    if refusal is Refusal.ESCAPES_PARENT:
        return tr("A name cannot point outside its own folder.")
    return tr("Permission denied.")


def describe_entry(entry: DirEntry) -> str:
    """Tooltip for one directory row, injected into CaseTreeModel."""
    if not entry.readable:
        return tr("{path}\nNot readable.").format(path=entry.path)
    if not entry.is_case:
        return str(entry.path)
    summary = case_summary(entry.path)
    lines = [str(entry.path), tr("OpenFOAM case")]
    if summary.time_dirs:
        lines.append(tr("{n} time directories").format(n=len(summary.time_dirs)))
    if summary.mesh is not None and summary.mesh.n_cells:
        lines.append(tr("{n} cells").format(n=f"{summary.mesh.n_cells:,}"))
    return "\n".join(lines)


class CaseNavigator(QObject):
    """Current location, the shared tree model, and the intents the views raise."""

    #: The directory both views are showing.
    location_changed = Signal(str)
    #: The compact tab's "Browse…" button was pressed.
    browser_requested = Signal()

    open_case_requested = Signal(str)       # case root
    compare_case_requested = Signal(str)    # case root
    duplicate_case_requested = Signal(str)  # case root
    move_requested = Signal(str)            # source directory
    rename_requested = Signal(str)          # directory to rename
    delete_requested = Signal(str)          # directory to delete
    new_folder_requested = Signal(str)      # parent directory
    status_message = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.model = CaseTreeModel(describe=describe_entry, parent=self)
        # Rooted at the filesystem root so anywhere is reachable; each view
        # narrows to the interesting subtree with setRootIndex.
        self.model.set_root(Path(os.path.abspath(os.sep)))
        self._current: Path | None = None

    # ── location ─────────────────────────────────────────────────────────────

    @property
    def current_dir(self) -> Path | None:
        return self._current

    def initial_location(self, open_case: str | None = None) -> Path:
        """Where to open: last browsed, else the default case dir, else home."""
        cfg = get_app_config()
        for candidate in (cfg.get_case_browser_dir(), cfg.get_default_case_dir()):
            if candidate and Path(candidate).is_dir():
                return Path(candidate)
        if open_case:
            parent = Path(open_case).parent
            if parent.is_dir():
                return parent
        return Path.home()

    def go_to(self, path: Path) -> None:
        """Show *path*, remembering it as the location to reopen at."""
        if not path.is_dir():
            self.status_message.emit(
                tr("'{name}' no longer exists.").format(name=path.name or str(path))
            )
            nearest = self._nearest_existing(path)
            if nearest is None or nearest == self._current:
                return
            path = nearest
        if self._current is not None and path == self._current:
            return
        self._current = path
        # Populate before announcing it: a view about to be re-rooted here
        # would fetch anyway, and doing it first means rowCount() is already
        # meaningful to anything that reacts to the signal.
        index = self.model.index_for_path(path)
        if self.model.canFetchMore(index):
            self.model.fetchMore(index)
        get_app_config().set_case_browser_dir(str(path))
        self.location_changed.emit(str(path))

    def go_up(self) -> None:
        if self._current is None:
            return
        parent = self._current.parent
        if parent != self._current:
            self.go_to(parent)

    def refresh_current(self) -> None:
        if self._current is not None:
            self.model.refresh(self.model.index_for_path(self._current))

    # ── called into by MainWindow ────────────────────────────────────────────

    def set_current_case(self, case_dir: str | None) -> None:
        """Bold the case the window has open. Does not move the view."""
        self.model.set_open_case(case_dir)

    def notify_added(self, path: Path) -> None:
        self._refresh_parent_of(path)

    def notify_removed(self, path: Path) -> None:
        self._refresh_parent_of(path)

    def notify_moved(self, old: Path, new: Path) -> None:
        self._refresh_parent_of(old)
        if new.parent != old.parent:
            self._refresh_parent_of(new)

    # ── raised by the views ──────────────────────────────────────────────────

    def request_browser(self) -> None:
        self.browser_requested.emit()

    def request_open(self, path: Path) -> None:
        self.open_case_requested.emit(str(path))

    def request_compare(self, path: Path) -> None:
        self.compare_case_requested.emit(str(path))

    def request_duplicate(self, path: Path) -> None:
        self.duplicate_case_requested.emit(str(path))

    def request_move(self, path: Path) -> None:
        self.move_requested.emit(str(path))

    def request_rename(self, path: Path) -> None:
        self.rename_requested.emit(str(path))

    def request_delete(self, path: Path) -> None:
        self.delete_requested.emit(str(path))

    def request_new_folder(self, parent: Path) -> None:
        self.new_folder_requested.emit(str(parent))

    # ── internals ────────────────────────────────────────────────────────────

    def _refresh_parent_of(self, path: Path) -> None:
        parent = path.parent
        self.model.refresh(self.model.index_for_path(parent))

    @staticmethod
    def _nearest_existing(path: Path) -> Path | None:
        """Walk up until something still on disk is found."""
        candidate = path.parent
        while True:
            if candidate.is_dir():
                return candidate
            if candidate.parent == candidate:
                return None
            candidate = candidate.parent
