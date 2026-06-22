# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer

from i18n import tr
from ui.layout_constants import BLOCKMESH_DICT_NAME as _BLOCKMESH_DICT_NAME


class _PanelOpsMixin:
    """Panel visibility management: BlockMesh tab/splitter and terminal mode switching."""

    def _on_toggle_blockmesh_panel(self, checked: bool) -> None:
        if self.block_mesh_panel is None:
            return
        if not checked and self.state.bm_side_by_side:
            # Exit side-by-side first so the panel is back in a tab before shutdown.
            self._on_toggle_bm_side_by_side(False)
        if checked:
            if not self.state.bm_side_by_side:
                idx = self.upper_tabs.indexOf(self.block_mesh_panel)
                if idx < 0:
                    self.upper_tabs.addTab(self.block_mesh_panel, tr("BlockMesh"))
            QTimer.singleShot(0, self.block_mesh_panel._init_plotter)
        else:
            self.block_mesh_panel.shutdown()
            idx = self.upper_tabs.indexOf(self.block_mesh_panel)
            if idx >= 0:
                self.upper_tabs.removeTab(idx)
        self._update_bm_side_by_side_btn()

    def _on_toggle_bm_side_by_side(self, checked: bool) -> None:
        if self.block_mesh_panel is None or self._bm_side_by_side_btn is None:
            return
        self.state.bm_side_by_side = checked
        self._bm_side_by_side_btn.setChecked(checked)
        if checked:
            # Switch to Tree tab FIRST so the splitter is visible when the
            # panel is reparented into it — this is what makes show() reliable.
            self.upper_tabs.setCurrentIndex(0)
            idx = self.upper_tabs.indexOf(self.block_mesh_panel)
            if idx >= 0:
                self.upper_tabs.removeTab(idx)
            self._tree_bm_splitter.addWidget(self.block_mesh_panel)
            self.block_mesh_panel.show()   # explicit; removeTab hides the widget
            # Defer setSizes until the layout pass after show() has run.
            QTimer.singleShot(0, lambda: self._tree_bm_splitter.setSizes([1, 1]))
            QTimer.singleShot(0, self.block_mesh_panel._init_plotter)
        else:
            # addTab reparents the panel from the splitter back to upper_tabs.
            self.upper_tabs.addTab(self.block_mesh_panel, tr("BlockMesh"))

    def _update_bm_side_by_side_btn(self) -> None:
        if self._bm_side_by_side_btn is None:
            return
        is_bm_file = bool(
            self.state.current_file
            and Path(self.state.current_file).name == _BLOCKMESH_DICT_NAME
        )
        xterm_active = (
            self.terminal_panel is not None and self.terminal_panel.use_xterm
        )
        bm_panel_on = (
            self._blockmesh_action is None or self._blockmesh_action.isChecked()
        )
        enabled = is_bm_file and not xterm_active and bm_panel_on
        self._bm_side_by_side_btn.setEnabled(enabled)
        if not enabled and self.state.bm_side_by_side:
            self._on_toggle_bm_side_by_side(False)

    def _on_terminal_mode_changed(self, use_xterm: bool) -> None:
        if self.block_mesh_panel is None:
            return
        if use_xterm:
            # Exit side-by-side so the panel is back in a tab before shutdown.
            if self.state.bm_side_by_side:
                self._on_toggle_bm_side_by_side(False)
            self.block_mesh_panel.shutdown()
            idx = self.upper_tabs.indexOf(self.block_mesh_panel)
            if idx >= 0:
                self.upper_tabs.removeTab(idx)
            if self._blockmesh_action is not None:
                self._blockmesh_action.setEnabled(False)
                self._blockmesh_action.setText(
                    tr("BlockMesh 3-D Panel  (unavailable: xterm active)")
                )
        else:
            if self._blockmesh_action is not None:
                self._blockmesh_action.setEnabled(True)
                self._blockmesh_action.setText(tr("BlockMesh 3-D Panel"))
            user_wants_bm = (
                self._blockmesh_action is None or self._blockmesh_action.isChecked()
            )
            if user_wants_bm and not self.state.bm_side_by_side:
                idx = self.upper_tabs.indexOf(self.block_mesh_panel)
                if idx < 0:
                    self.upper_tabs.addTab(self.block_mesh_panel, tr("BlockMesh"))
                QTimer.singleShot(300, self.block_mesh_panel._init_plotter)
        self._update_bm_side_by_side_btn()
