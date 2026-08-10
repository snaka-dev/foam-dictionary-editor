# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction, QKeySequence

from i18n import tr
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
    TOPOSET_DICT_NAME as _TOPOSET_DICT_NAME,
)
from ui.pane_minimize import PANE_BOTTOM, PANE_DETAIL, PANE_FILE_LIST

if TYPE_CHECKING:
    from ui.mixins._protocol import MainWindowProtocol as _Base
else:
    _Base = object


class _PanelOpsMixin(_Base):
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
            QTimer.singleShot(0, self.block_mesh_panel.init_plotter)
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
            QTimer.singleShot(0, self.block_mesh_panel.init_plotter)
        else:
            # addTab reparents the panel from the splitter back to upper_tabs.
            self.upper_tabs.addTab(self.block_mesh_panel, tr("BlockMesh"))
        self._auto_minimize_detail_for_side_by_side(checked)

    def _update_bm_side_by_side_btn(self) -> None:
        if self._bm_side_by_side_btn is None:
            return
        is_3d_viewable_file = bool(
            self.state.current_file
            and Path(self.state.current_file).name
            in (
                _BLOCKMESH_DICT_NAME,
                _TOPOSET_DICT_NAME,
                _SNAPPY_HEX_MESH_DICT_NAME,
                _SETFIELDS_DICT_NAME,
                *_SAMPLING_DICT_NAMES,
            )
        )
        xterm_active = (
            self.terminal_panel is not None and self.terminal_panel.use_xterm
        )
        bm_panel_on = (
            self._blockmesh_action is None or self._blockmesh_action.isChecked()
        )
        enabled = is_3d_viewable_file and not xterm_active and bm_panel_on
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
                QTimer.singleShot(300, self.block_mesh_panel.init_plotter)
        self._update_bm_side_by_side_btn()

    # ── pane minimize ─────────────────────────────────────────────────────────

    def _build_pane_menu_actions(self, view_menu) -> None:
        """Add the View-menu toggles for the minimizable panes.

        Checked means *shown*, matching View > Show Type Column and View >
        BlockMesh 3-D Panel. These items are also the guaranteed way back: a
        minimized pane is persisted between runs, and for the pinned bottom row
        its handle cannot be dragged open, so a control that is always visible
        has to exist somewhere (see ui/pane_minimize.py).
        """
        bottom_label = (
            tr("Editor / Terminal Pane") if self.terminal_panel is not None
            else tr("Editor Pane")
        )
        specs = (
            (PANE_FILE_LIST, tr("File List"), "Ctrl+1"),
            (PANE_DETAIL, tr("Detail Pane"), "Ctrl+2"),
            (PANE_BOTTOM, bottom_label, "Ctrl+3"),
        )
        self._pane_actions = {}
        for name, label, shortcut in specs:
            action = QAction(label, self)
            action.setCheckable(True)
            action.setChecked(True)
            action.setShortcut(QKeySequence(shortcut))
            action.toggled.connect(partial(self._on_pane_action_toggled, name))
            view_menu.addAction(action)
            self._pane_actions[name] = action

    def set_pane_minimized(self, name: str, minimized: bool) -> None:
        """Minimize or restore a pane and bring every control for it into line."""
        minimizer = self._pane_minimizers.get(name)
        if minimizer is None or minimizer.minimized == minimized:
            return
        minimizer.set_minimized(minimized)
        action = self._pane_actions.get(name)
        if action is not None and action.isChecked() == minimized:
            # The action reflects the pane; toggling it back would re-enter here.
            blocked = action.blockSignals(True)
            action.setChecked(not minimized)
            action.blockSignals(blocked)
        self._update_pane_minimize_controls()

    def toggle_pane_minimized(self, name: str) -> None:
        minimizer = self._pane_minimizers.get(name)
        if minimizer is not None:
            self.set_pane_minimized(name, not minimizer.minimized)

    def _on_pane_action_toggled(self, name: str, checked: bool) -> None:
        self.set_pane_minimized(name, not checked)

    def _on_toggle_bottom_pane_btn(self) -> None:
        self.toggle_pane_minimized(PANE_BOTTOM)

    def _on_splitter_handle_double_click(self, splitter, index: int) -> None:
        """Toggle the minimizable pane a double-clicked handle sits next to.

        The handle at *index* separates panes ``index - 1`` and ``index``. The
        later pane wins when both are registered, which never happens in today's
        layout — each splitter has at most one minimizable pane — but keeps the
        rule decided rather than accidental.
        """
        for candidate in (index, index - 1):
            for name, minimizer in self._pane_minimizers.items():
                if minimizer.splitter is splitter and minimizer.index == candidate:
                    self.toggle_pane_minimized(name)
                    return

    def _auto_minimize_detail_for_side_by_side(self, side_by_side: bool) -> None:
        """Park the Detail pane while the 3-D view is beside the tree.

        The pane has nothing to say about a file being inspected in 3-D, and the
        width it holds is width the 3-D view does not get. Restoring on the way
        out is conditional on this having been the thing that minimized it, so a
        user who parked the pane by hand beforehand does not find it reopened.
        """
        if PANE_DETAIL not in self._pane_minimizers:
            return
        if side_by_side:
            if not self._pane_minimizers[PANE_DETAIL].minimized:
                self.set_pane_minimized(PANE_DETAIL, True)
                self._detail_auto_minimized = True
        elif getattr(self, "_detail_auto_minimized", False):
            self._detail_auto_minimized = False
            self.set_pane_minimized(PANE_DETAIL, False)

    def _update_pane_minimize_controls(self) -> None:
        """Keep the bottom row's button showing what the next click will do."""
        button = getattr(self, "_bottom_minimize_btn", None)
        if button is None:
            return
        minimizer = self._pane_minimizers.get(PANE_BOTTOM)
        minimized = minimizer is not None and minimizer.minimized
        button.setText("▔" if minimized else "▁")
        button.setToolTip(
            tr("Restore the editor pane") if minimized
            else tr("Minimize the editor pane to its tab bar")
        )
