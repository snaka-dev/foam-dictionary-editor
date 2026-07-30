# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt

from foam.nodes import FoamNode
from foam.parser import OpenFoamParser
from foam.utils import read_foam_file
from foam.writer import write_root
from i18n import tr
from model.tree_model import FoamTreeModel
from ui.layout_constants import (
    BLOCKMESH_DICT_NAME as _BLOCKMESH_DICT_NAME,
)
from ui.layout_constants import (
    SAMPLING_DICT_NAMES as _SAMPLING_DICT_NAMES,
)
from ui.layout_constants import (
    SETFIELDS_DICT_NAME as _SETFIELDS_DICT_NAME,
)
from ui.layout_constants import (
    SNAPPY_HEX_MESH_DICT_NAME as _SNAPPY_HEX_MESH_DICT_NAME,
)
from ui.layout_constants import (
    STATUS_SHORT as _STATUS_SHORT,
)
from ui.layout_constants import (
    STATUS_WARNING as _STATUS_WARNING,
)
from ui.layout_constants import (
    TOPOSET_DICT_NAME as _TOPOSET_DICT_NAME,
)
from ui.layout_constants import (
    TREE_EXPAND_DEPTH as _TREE_EXPAND_DEPTH,
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
        self.statusBar().showMessage(tr("Tree changes applied to text editor"), _STATUS_SHORT)

    def _update_viewer_panels(self, path: str, root: FoamNode) -> None:
        """Refresh the boundary table and the 3-D viewer for one file's tree."""
        self.boundary_panel.update_field(path, root)
        if self.block_mesh_panel is None:
            return
        name = Path(path).name
        update = {
            _BLOCKMESH_DICT_NAME: self.block_mesh_panel.update_block_mesh,
            _TOPOSET_DICT_NAME: self.block_mesh_panel.update_topo_set,
            _SNAPPY_HEX_MESH_DICT_NAME: self.block_mesh_panel.update_snappy_hex_mesh,
            _SETFIELDS_DICT_NAME: self.block_mesh_panel.update_set_fields,
        }.get(name)
        if update is None and name in _SAMPLING_DICT_NAMES:
            update = self.block_mesh_panel.update_sampling
        if update is not None:
            update(path, root)

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
            lambda msg: self.statusBar().showMessage(msg, _STATUS_WARNING)
        )
        self.state.current_model.about_to_change.connect(self._on_model_about_to_change)
        self.state.current_model.dataChanged.connect(self._on_tree_data_changed)
        self.proxy_model.setSourceModel(self.state.current_model)
        self.tree_filter_input.clear()
        self.tree.expandToDepth(_TREE_EXPAND_DEPTH)
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
