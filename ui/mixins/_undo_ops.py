# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut

from foam.parser import OpenFoamParser
from foam.utils import read_foam_file
from foam.writer import write_root
from i18n import tr
from ui.app_state import UndoSnapshot
from ui.layout_constants import STATUS_SHORT

# Stack caps: at most this many snapshots, and no more than this many bytes of
# serialized text in total (whichever is hit first), so a long editing session
# on a large file cannot grow the history without bound.
_UNDO_DEPTH = 50
_UNDO_MAX_BYTES = 16 * 1024 * 1024


if TYPE_CHECKING:
    from ui.mixins._protocol import MainWindowProtocol as _Base
else:
    _Base = object


class _UndoOpsMixin(_Base):
    """Snapshot-based undo/redo for tree edits.

    Every tree mutation already ends in a full ``write_root`` re-serialization,
    so the pre-mutation state is checkpointed as serialized text (all files the
    operation touches — boundary operations may span several). Undo re-parses
    the snapshot and reloads the tree through the existing full-rebuild path
    (``_load_tree``); tree expansion/selection state is not preserved.

    The history is a single global timeline, not per file: Ctrl+Z reverses the
    most recent tree operation wherever it happened (switching the view to the
    affected file when needed), and any new edit clears the redo branch. The
    shortcuts are widget-scoped to the tree so the text editor's native undo is
    untouched.

    Inline edits reach the model through ``setData``, whose ``about_to_change``
    signal fires *before* the edit is validated. Those are stashed as
    ``pending`` and only committed once ``_on_tree_data_changed`` confirms the
    edit actually changed the document, so a rejected or no-op edit never
    disturbs the stacks. Direct-mutation operations (CRUD, boundary, apply-text)
    call ``_checkpoint_for_undo`` explicitly and commit immediately.
    """

    def _setup_tree_undo(self) -> None:
        undo_sc = QShortcut(QKeySequence.StandardKey.Undo, self.tree)
        undo_sc.setContext(Qt.ShortcutContext.WidgetShortcut)
        undo_sc.activated.connect(self._tree_undo)

        # A literal Ctrl+Shift+Z (Cmd+Shift+Z on macOS) rather than
        # QKeySequence.Redo, which resolves to Ctrl+Y on Windows and would then
        # disagree with every "Ctrl+Shift+Z" label in the menu, dialog, and docs.
        redo_sc = QShortcut(QKeySequence("Ctrl+Shift+Z"), self.tree)
        redo_sc.setContext(Qt.ShortcutContext.WidgetShortcut)
        redo_sc.activated.connect(self._tree_redo)

    # ── checkpointing ─────────────────────────────────────────────────────────

    def _on_model_about_to_change(self) -> None:
        """Stash a pre-edit snapshot for a mutation reaching setData directly."""
        undo = self.state.undo
        if undo.restoring or undo.op_active:
            return
        key = self.state.current_file
        if key is None:
            return
        undo.pending = self._undo_snapshot_of([key])

    def _commit_pending_undo(self) -> None:
        """Commit a stashed inline-edit snapshot once the edit is confirmed real.

        Called from ``_on_tree_data_changed`` (which fires only on a successful
        ``setData``). A snapshot equal to the current state — a value-unchanged
        edit — is discarded rather than pushed.
        """
        undo = self.state.undo
        snap = undo.pending
        undo.pending = None
        if snap is None or undo.restoring:
            return
        current = self._undo_snapshot_of(list(snap.texts))
        if current is not None and current.texts == snap.texts:
            return
        undo.undo_stack.append(snap)
        undo.redo_stack.clear()
        self._trim_undo_stack()

    def _checkpoint_for_undo(self, paths: list[str] | None = None) -> None:
        """Push a pre-mutation snapshot for a direct-mutation operation.

        ``paths`` names every file the operation will change (defaults to the
        current file). The snapshot is pushed immediately because the caller
        guarantees a real mutation follows; ``op_active`` then suppresses the
        redundant ``about_to_change`` stash from any ``setData`` the operation
        performs internally.
        """
        undo = self.state.undo
        if undo.restoring:
            return
        undo.pending = None
        if paths is None:
            paths = [self.state.current_file] if self.state.current_file else []
        snap = self._undo_snapshot_of(paths)
        if snap is not None:
            undo.undo_stack.append(snap)
            undo.redo_stack.clear()
            self._trim_undo_stack()
        undo.op_active = True
        QTimer.singleShot(0, self._end_undo_op)

    def _end_undo_op(self) -> None:
        self.state.undo.op_active = False

    def _trim_undo_stack(self) -> None:
        stack = self.state.undo.undo_stack
        del stack[:-_UNDO_DEPTH]
        total = sum(len(t) for s in stack for t in s.texts.values())
        while len(stack) > 1 and total > _UNDO_MAX_BYTES:
            removed = stack.pop(0)
            total -= sum(len(t) for t in removed.texts.values())

    def _undo_snapshot_of(self, paths: list[str]) -> UndoSnapshot | None:
        texts: dict[str, str] = {}
        dirty: dict[str, bool] = {}
        for path in paths:
            text = self._undo_text_for(path)
            if text is None:
                continue
            texts[path] = text
            dirty[path] = bool(self.state.file_dirty.get(path, False))
        if not texts:
            return None
        return UndoSnapshot(texts=texts, dirty=dirty)

    def _undo_text_for(self, path: str) -> str | None:
        """The authoritative current text of one file.

        For the current file this is the editor text: when tree and editor are
        in sync it is byte-faithful to the loaded file, and when the user has
        typed unapplied free-text it is what is on screen — either way the state
        undo must be able to restore. For other files: the buffer, then the
        parse cache, then the disk file.
        """
        if path == self.state.current_file:
            return self.editor_panel.get_text()
        text = self.state.file_buffers.get(path)
        if text is not None:
            return text
        root = self.state.parsed_roots.get(path)
        if root is not None:
            return write_root(root)
        try:
            return read_foam_file(path)
        except OSError:
            return None

    def _clear_undo_stacks(self) -> None:
        undo = self.state.undo
        undo.undo_stack.clear()
        undo.redo_stack.clear()
        undo.pending = None

    # ── undo / redo ───────────────────────────────────────────────────────────

    def _tree_undo(self) -> None:
        self._undo_redo_step(
            self.state.undo.undo_stack,
            self.state.undo.redo_stack,
            tr("Nothing to undo"),
            tr("Undid tree change"),
        )

    def _tree_redo(self) -> None:
        self._undo_redo_step(
            self.state.undo.redo_stack,
            self.state.undo.undo_stack,
            tr("Nothing to redo"),
            tr("Redid tree change"),
        )

    def _undo_redo_step(
        self,
        from_stack: list[UndoSnapshot],
        to_stack: list[UndoSnapshot],
        empty_msg: str,
        done_msg: str,
    ) -> None:
        # A rejected inline edit can leave an uncommitted pending snapshot; it
        # represents no real change, so drop it before stepping the history.
        self.state.undo.pending = None
        if not from_stack:
            self.statusBar().showMessage(empty_msg, STATUS_SHORT)
            return
        snap = from_stack.pop()
        current = self._undo_snapshot_of(list(snap.texts))
        if current is not None:
            to_stack.append(current)
        self._restore_undo_snapshot(snap)
        others = sum(1 for p in snap.texts if p != self.state.current_file)
        if others:
            done_msg = tr("{msg} (+{n} more file(s))").format(msg=done_msg, n=others)
        self.statusBar().showMessage(done_msg, STATUS_SHORT)

    def _restore_undo_snapshot(self, snap: UndoSnapshot) -> None:
        undo = self.state.undo
        undo.restoring = True
        try:
            current = self.state.current_file
            for path, text in snap.texts.items():
                try:
                    root = OpenFoamParser(text).parse()
                except Exception:
                    continue
                self.state.file_buffers[path] = text
                self.state.parsed_roots[path] = root
                dirty = self._restored_dirty(path, text, snap.dirty.get(path, False))
                self.state.file_dirty[path] = dirty
                self.file_list_panel.mark_dirty(path, dirty)
                if path == current:
                    self._load_tree(root)
                    self.editor_panel.set_text(text)
                    self.state.text_dirty = dirty
                    self._update_window_title()
                    self._update_file_label()
                self._update_viewer_panels(path, root)
            self.boundary_panel.refresh()
            if current not in snap.texts:
                # None of the changed files is on screen; switch to one so the
                # undo is visible rather than silently changing a hidden buffer.
                display = next(iter(snap.texts), None)
                if display is not None:
                    self.load_selected_file(display)
                    self.file_list_panel.select_file(display)
        finally:
            undo.restoring = False

    def _restored_dirty(self, path: str, text: str, snap_dirty: bool) -> bool:
        """Dirty flag for a restored file.

        The snapshot's flag can be stale when the file was saved between the
        mutation and the undo, so a "clean" claim is verified against disk.
        """
        if snap_dirty:
            return True
        try:
            return read_foam_file(path) != text
        except OSError:
            return True
