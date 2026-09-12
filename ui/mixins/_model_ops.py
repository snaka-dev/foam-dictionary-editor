# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt

from foam.include_expand import ExpandedTree, expand_includes
from foam.nodes import FoamNode
from foam.parser import OpenFoamParser
from foam.utils import read_foam_file
from foam.writer import write_root
from i18n import tr
from model.tree_model import FoamTreeModel
from services.include_scan import foam_etc_dirs
from ui.layout_constants import (
    BLOCKMESH_DICT_NAME,
    SAMPLING_DICT_NAMES,
    SETFIELDS_DICT_NAME,
    SNAPPY_HEX_MESH_DICT_NAME,
    STATUS_SHORT,
    STATUS_WARNING,
    TOPOSET_DICT_NAME,
    TREE_EXPAND_DEPTH,
)

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
            # The open file's freshest text is in the editor, not in
            # file_buffers: apply_text_to_tree parses the editor directly and
            # never flushes it there, so reading the buffer would serve the
            # text as it was when the file was opened.
            if self.state.current_file is not None and str(target) == self.state.current_file:
                return self.editor_panel.get_text()
            return self.state.file_buffers.get(str(target))

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

    def _update_viewer_panels(self, path: str, root: FoamNode) -> None:
        """Refresh the boundary table and the 3-D viewer for one file's tree."""
        self.boundary_panel.update_field(path, root)
        self._update_block_mesh_viewer(path, root)
        self._refresh_include_dependents(path)

    def _update_block_mesh_viewer(self, path: str, root: FoamNode) -> None:
        """Push one file's tree at the 3-D viewer, with its includes resolved."""
        if self.block_mesh_panel is None:
            return
        name = Path(path).name
        update = {
            BLOCKMESH_DICT_NAME: self.block_mesh_panel.update_block_mesh,
            TOPOSET_DICT_NAME: self.block_mesh_panel.update_topo_set,
            SNAPPY_HEX_MESH_DICT_NAME: self.block_mesh_panel.update_snappy_hex_mesh,
            SETFIELDS_DICT_NAME: self.block_mesh_panel.update_set_fields,
        }.get(name)
        if update is None and name in SAMPLING_DICT_NAMES:
            update = self.block_mesh_panel.update_sampling
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
