# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import dataclasses
import os
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt

from foam.include_expand import ExpandedTree, expand_includes
from foam.nodes import FoamNode
from foam.parser import OpenFoamParser
from foam.utils import is_text_only, read_foam_file
from foam.writer import write_root
from i18n import tr
from model.tree_model import FoamTreeModel
from services.include_scan import foam_etc_dirs
from ui import viewer_dicts
from ui.layout_constants import (
    STATUS_SHORT,
    STATUS_WARNING,
    TREE_EXPAND_DEPTH,
)

# What _prime_viewer reads: dictionaries live directly under these.
_PRIME_DIRS = frozenset({"system", "constant"})
# Far above any dictionary the view draws; keeps a stray large file from
# costing a parse every time the file list refreshes.
_PRIME_MAX_BYTES = 1_000_000


@dataclasses.dataclass
class _Primed:
    """One listed file as _prime_viewer last saw it."""

    stamp: tuple[int, int]  # (mtime_ns, size): re-read only when it changes
    root: FoamNode | None  # None: feeds no overlay, or could not be read
    drawn: bool  # whether its shapes are in the view now
    fresh: bool = True  # re-read since last drawn: draw again


if TYPE_CHECKING:
    from ui.mixins._protocol import MainWindowProtocol as _Base
else:
    _Base = object


class _ModelOpsMixin(_Base):
    """File buffer, dirty tracking, tree load/clear, and parse-cache helpers."""

    # ── buffer / tree state ───────────────────────────────────────────────────

    def _save_current_buffer(self) -> None:
        if self.state.current_file is None:
            return
        self.state.file_buffers[self.state.current_file] = self.editor_panel.get_text()
        self.state.file_dirty[self.state.current_file] = self.state.text_dirty
        self.file_list_panel.mark_dirty(self.state.current_file, self.state.text_dirty)

    def _after_model_edit(self) -> None:
        self.editor_panel.set_text(write_root(self.state.current_root))
        self._mark_dirty()
        if self.state.current_file:
            self._update_viewer_panels(self.state.current_file, self.state.current_root)
        self._resize_tree_columns()
        self.on_tree_selection()
        self.statusBar().showMessage(tr("Tree changes applied to text editor"), STATUS_SHORT)

    def _expand_includes_for_viewer(self, path: str, root: FoamNode) -> ExpandedTree:
        """Resolve `#include`d entries into a read-only copy of one file's tree.

        Only the 3-D viewer gets this tree. Everything that writes -- the tree
        view, the editor, the writer, the boundary table -- keeps the original
        root, so nothing can save another file's entries into this one.

        Unsaved editor buffers are served ahead of the file on disk, so editing
        the included file updates the view before it is saved.
        """
        case_dir = self.state.current_case_dir
        if case_dir is None:
            return ExpandedTree(root=root)

        def read_buffer(target: Path) -> str | None:
            # Unsaved text only: expand_includes reads (and memoises) the disk
            # copy itself when this returns None.
            return self._current_text(str(target), fallback=False)

        try:
            return expand_includes(
                root,
                source_file=Path(path),
                case_dir=Path(case_dir),
                etc_dirs=foam_etc_dirs(),
                read_text=read_buffer,
            )
        except OSError:
            # An unreadable include must never stop the viewer updating; it
            # simply renders what the unexpanded tree holds, as before.
            return ExpandedTree(root=root)

    def _prime_viewer(self) -> None:
        """Draw every dictionary the case lists that feeds the 3-D view.

        The view used to show a file's shapes only once that file had been
        opened, so a freshly opened case looked emptier than it is -- a mesh
        with none of its probes, regions or snappy geometry. This reads the
        listed ``system/`` and ``constant/`` files for drawing only: no
        buffer is created, nothing is marked edited, the tree and editor are
        untouched. A file open in FoDE is skipped, since its own text (with
        any unsaved edits) already drives the view; files over
        ``_PRIME_MAX_BYTES`` are skipped; each is re-read only when its
        modification time or size changes. A file whose content reaches the
        view through another's ``#include`` (damBreak's ``system/sampling``,
        pulled into controlDict by ``#sinclude``) is not drawn a second time
        on its own, and a file gone from the list takes its shapes with it.
        """
        panel = self.block_mesh_panel
        case_dir = self.state.current_case_dir
        if panel is None or not case_dir:
            return
        listed: set[str] = set()
        for path in self.file_list_panel.file_paths():
            rel = self._case_relative(path)
            if rel is None or Path(rel).parts[0] not in _PRIME_DIRS or len(Path(rel).parts) != 2:
                continue
            listed.add(path)
            if path in self.state.file_buffers:
                continue
            try:
                st = os.stat(path)
            except OSError:
                continue
            stamp = (st.st_mtime_ns, st.st_size)
            known = self._viewer_primed.get(path)
            if known is not None and known.stamp == stamp:
                continue
            root = None
            if st.st_size <= _PRIME_MAX_BYTES:
                try:
                    text = read_foam_file(path)
                    if not is_text_only(text, path):
                        root = OpenFoamParser(text).parse()
                except Exception:
                    root = None  # unreadable or unparseable: draw nothing, quietly
            kind = self._viewer_kind_for(path, root) if root is not None else None
            drawn = known.drawn if known is not None else False
            self._viewer_primed[path] = _Primed(stamp, root if kind else None, drawn, fresh=True)

        # Gone from the list: take its shapes with it.
        for path in [p for p in self._viewer_primed if p not in listed]:
            primed = self._viewer_primed.pop(path)
            if primed.drawn and path not in self.state.file_buffers:
                panel.forget_file(path)

        # Changed so that it no longer feeds the view.
        for path, primed in self._viewer_primed.items():
            if primed.root is None and primed.drawn and path not in self.state.file_buffers:
                panel.forget_file(path)
                primed.drawn = False

        def drawn_includers() -> set[str]:
            covered: set[str] = set()
            for includer, sources in self.state.viewer_include_sources.items():
                if includer in self.state.file_buffers or (
                    includer in self._viewer_primed and self._viewer_primed[includer].drawn
                ):
                    covered |= {os.path.realpath(s) for s in sources}
            return covered

        # Includers first, so what they pull in is known before deciding on
        # the included files themselves.
        pending = [p for p, d in self._viewer_primed.items() if d.root is not None]
        for path in sorted(pending, key=lambda p: Path(p).name != "controlDict"):
            primed = self._viewer_primed[path]
            if path in self.state.file_buffers or primed.root is None:
                continue
            if os.path.realpath(path) in drawn_includers():
                if primed.drawn:
                    panel.forget_file(path)
                    primed.drawn = False
                continue
            if primed.drawn and not primed.fresh:
                continue  # unchanged and already in the view
            self._update_block_mesh_viewer(path, primed.root)
            primed.drawn = True
            primed.fresh = False
        # Any order can draw an included file before its includer: withdraw it.
        covered = drawn_includers()
        for path, primed in self._viewer_primed.items():
            if primed.drawn and os.path.realpath(path) in covered:
                panel.forget_file(path)
                primed.drawn = False

    def _update_viewer_panels(self, path: str, root: FoamNode) -> None:
        """Refresh the boundary table and the 3-D viewer for one file's tree."""
        self.boundary_panel.update_field(path, root)
        self._update_block_mesh_viewer(path, root)
        self._refresh_include_dependents(path)

    def _viewer_kind_for(self, path: str, root: FoamNode | None) -> str | None:
        """Which 3-D overlay *path* feeds, honouring the user's "show as" override.

        The single place the override is read, so the viewer dispatch and the
        side-by-side button can never disagree about whether a file is viewable.
        """
        config = self.state.case_files_config
        rel = self._case_relative(path)
        override = config.get_viewer_kind(rel) if config is not None and rel else ""
        return viewer_dicts.viewer_dict_kind(path, root, override)

    def _update_block_mesh_viewer(self, path: str, root: FoamNode) -> None:
        """Push one file's tree at the 3-D viewer, with its includes resolved."""
        if self.block_mesh_panel is None:
            return
        # Recognised by the FoamFile header when the name is not one of the defaults, so
        # a hand-named `topoSetDict-slices` reaches the viewer -- see ui/viewer_dicts.py.
        updates = {
            viewer_dicts.BLOCK_MESH: self.block_mesh_panel.update_block_mesh,
            viewer_dicts.TOPO_SET: self.block_mesh_panel.update_topo_set,
            viewer_dicts.SNAPPY_HEX_MESH: self.block_mesh_panel.update_snappy_hex_mesh,
            viewer_dicts.SET_FIELDS: self.block_mesh_panel.update_set_fields,
            viewer_dicts.SAMPLING: self.block_mesh_panel.update_sampling,
        }
        kind = self._viewer_kind_for(path, root)
        if kind is None:
            return
        update = updates.get(kind)
        if update is None:
            return
        expanded = self._expand_includes_for_viewer(path, root)
        if expanded.expanded:
            self.state.viewer_include_sources[path] = expanded.sources
        else:
            self.state.viewer_include_sources.pop(path, None)
        update(path, expanded.root)

    def _refresh_include_dependents(self, path: str) -> None:
        """Re-render any viewer dict whose last expansion consumed *path*.

        The file just edited may be a parameter file rather than a dictionary
        the viewer knows -- a `settings-region` holding every dimension matches
        no name in the table above -- so without this the 3-D view would keep
        showing the values it was built with.

        Only the 3-D half is re-run: the boundary table is keyed on the file the
        user is actually looking at, and a dependent dictionary is not it.
        """
        # Snapshot first: _update_block_mesh_viewer rewrites this dict as it
        # re-renders each dependent.
        for dict_path, sources in list(self.state.viewer_include_sources.items()):
            if dict_path == path or path not in sources:
                continue
            dependent_root = self.state.parsed_roots.get(dict_path)
            if dependent_root is None:
                dependent_root = self._cache_parsed_root(dict_path)
            if dependent_root is not None:
                self._update_block_mesh_viewer(dict_path, dependent_root)

    def _on_tree_data_changed(self, top_left, bottom_right, roles) -> None:
        # Catches edits made directly in the tree view (inline cell editing), which
        # call FoamTreeModel.setData() without going through _after_model_edit().
        if Qt.ItemDataRole.EditRole in roles:
            self._after_model_edit()
            # dataChanged(EditRole) only fires on a successful setData, so this
            # is the point at which a stashed inline-edit snapshot is known to
            # represent a real change and can be committed to the undo stack.
            self._commit_pending_undo()

    def _load_tree(self, root: FoamNode) -> None:
        self.state.current_root = root
        self.state.current_model = FoamTreeModel(
            root, read_only=self._is_read_only(self.state.current_file)
        )
        self.state.current_model.edit_rejected.connect(
            lambda msg: self.statusBar().showMessage(msg, STATUS_WARNING)
        )
        self.state.current_model.about_to_change.connect(self._on_model_about_to_change)
        self.state.current_model.dataChanged.connect(self._on_tree_data_changed)
        self.proxy_model.setSourceModel(self.state.current_model)
        self.tree_filter_input.clear()
        self.tree.expandToDepth(TREE_EXPAND_DEPTH)
        self._collapse_foam_file()
        self._connect_tree_selection()
        self._resize_tree_columns()
        self.state.source_lines_valid = True
        self._update_sync_checkbox()
        self.editor_panel.clear_node_highlight()
        self._recompute_diff()

    def _clear_current_file(self) -> None:
        self.state.current_file = None
        self.state.text_dirty = False
        self.editor_panel.set_text("")
        self.editor_panel.set_read_only(False)
        self._load_tree(FoamNode(name="root", node_type="dictionary"))
        self._update_window_title()
        self._update_file_label()
        self._update_bm_side_by_side_btn()

    # ── root write helpers ────────────────────────────────────────────────────

    def _write_root_to_buffer(self, path: str, root: FoamNode) -> str:
        """Serialize root, store in file_buffers, and mark path dirty. Returns the text."""
        text = write_root(root)
        self.state.file_buffers[path] = text
        self._mark_path_dirty(path)
        return text

    # ── parse cache ───────────────────────────────────────────────────────────

    def _cache_parsed_root(self, path: str) -> FoamNode | None:
        text = self.state.file_buffers.get(path)
        if text is None:
            try:
                text = read_foam_file(path)
            except OSError:
                return None
        try:
            root = OpenFoamParser(text).parse()
            self.state.parsed_roots[path] = root
            return root
        except Exception:
            return None

    # ── dirty tracking ────────────────────────────────────────────────────────

    def _is_read_only(self, path: str | None) -> bool:
        """True for an `#include` target outside the case directory.

        The single read-only predicate. Editing such a file would change one
        shared by every case — usually inside the OpenFOAM installation — so
        every write path consults this. See DEVELOPER.md's "Include resolution".
        """
        return bool(path) and path in self.state.read_only_files

    def _current_text(self, path: str, *, fallback: bool = True) -> str | None:
        """The freshest text of one file, as the user currently sees it.

        The single answer to "what does this file say right now". For the open
        file that is the editor, not ``file_buffers``: ``apply_text_to_tree``
        parses the editor directly and never flushes it there, so the buffer
        can hold the text as it was when the file was opened. For any other
        file, the buffer. With ``fallback``, a file with no buffer is then
        served from the parse cache and finally from disk; without it, None --
        for a caller such as the include expansion that reads and memoises the
        disk copy itself.
        """
        path = str(Path(path))
        if self.state.current_file is not None and path == str(
            Path(self.state.current_file)
        ):
            return self.editor_panel.get_text()
        text = self.state.file_buffers.get(path)
        if text is not None or not fallback:
            return text
        root = self.state.parsed_roots.get(path)
        if root is not None:
            return write_root(root)
        try:
            return read_foam_file(path)
        except OSError:
            return None

    def _dirty_paths(self) -> list[str]:
        """Every file with unsaved changes that may be written.

        A read-only file should never be dirty (``_mark_dirty`` refuses);
        filtering here too keeps one stray flag from writing into the OpenFOAM
        install. The open file counts through ``text_dirty`` even before its
        flag in ``file_dirty`` has been flushed.
        """
        paths = [
            p
            for p, dirty in self.state.file_dirty.items()
            if dirty and not self._is_read_only(p)
        ]
        current = self.state.current_file
        if (
            self.state.text_dirty
            and current is not None
            and current not in paths
            and not self._is_read_only(current)
        ):
            paths.append(current)
        return paths

    def _mark_dirty(self) -> None:
        # Never letting a read-only file go dirty is what disables the `*`
        # marker, Save All, and the unsaved-changes prompts for it, all at once.
        if self._is_read_only(self.state.current_file):
            return
        self.state.text_dirty = True
        if self.state.current_file:
            self.state.file_dirty[self.state.current_file] = True
        self._update_window_title()
        self._update_file_label()
        if self.state.current_file:
            self.file_list_panel.mark_dirty(self.state.current_file, True)

    def _mark_path_dirty(self, path: str) -> None:
        if self._is_read_only(path):
            return
        self.state.file_dirty[path] = True
        self.file_list_panel.mark_dirty(path, True)
        if path == self.state.current_file:
            self.state.text_dirty = True
            self._update_window_title()
            self._update_file_label()

    def _confirm_discard_if_needed(self) -> bool:
        if not self.state.text_dirty:
            return True
        return self._confirm(
            tr("Unsaved Changes"),
            tr("Text editor has unsaved changes. Discard them?"),
        )
