# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QFileSystemWatcher, QSize, QSortFilterProxyModel, Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QToolButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from app_config import get_app_config
from i18n import tr
from model.tree_model import FoamTreeModel
from services.background_run import BackgroundRun
from ui.app_state import AppState
from ui.case_navigation import CaseNavigator
from ui.fonts import button_pixel_width, icon_pixel_size
from ui.icons import icon
from ui.layout_constants import (
    SPLITTER_DETAIL_WIDTH,
    SPLITTER_FILE_LIST_WIDTH,
    SPLITTER_HANDLE_WIDTH,
    SPLITTER_LOWER_HEIGHT,
    SPLITTER_TREE_WIDTH,
    SPLITTER_UPPER_HEIGHT,
    STATUS_NORMAL,
)
from ui.mixins._background_run_ops import _BackgroundRunOpsMixin
from ui.mixins._boundary_ops import _BoundaryOpsMixin
from ui.mixins._case_nav_ops import _CaseNavOpsMixin
from ui.mixins._case_ops import _CaseOpsMixin
from ui.mixins._diff_ops import _DiffOpsMixin
from ui.mixins._file_mgmt_ops import _FileManagementOpsMixin
from ui.mixins._file_ops import _FileOpsMixin
from ui.mixins._foam_monitor_ops import _FoamMonitorOpsMixin
from ui.mixins._function_object_ops import _FunctionObjectOpsMixin
from ui.mixins._menu_bar_ops import _MenuBarOpsMixin
from ui.mixins._model_ops import _ModelOpsMixin
from ui.mixins._panel_ops import _PanelOpsMixin
from ui.mixins._processor_ops import _ProcessorOpsMixin
from ui.mixins._tools_ops import _ToolsOpsMixin
from ui.mixins._tree_crud_ops import _TreeCrudOpsMixin
from ui.mixins._tree_sync_ops import _TreeSyncOpsMixin
from ui.mixins._ui_ops import _UiOpsMixin
from ui.mixins._undo_ops import _UndoOpsMixin
from ui.pane_minimize import (
    PANE_BOTTOM,
    PANE_DETAIL,
    PANE_FILE_LIST,
    PaneMinimizer,
    install_handle_double_click,
)
from ui.panels.case_nav_panel import CaseNavPanel
from ui.panels.comparison_tree_panel import ComparisonTreePanel
from ui.panels.detail_panel import DetailPanel
from ui.panels.editor_panel import EditorPanel
from ui.panels.file_list_panel import FileListPanel
from ui.panels.terminal_panel import TerminalPanel
from ui.session_restore import save_session
from ui.theme import colors, splitter_qss

if TYPE_CHECKING:
    # Only imported for their types: block_mesh_panel is deliberately imported
    # lazily at runtime in _build_feature_panels() (below) so the vtk/pyvista
    # stack is not loaded unless the BlockMesh feature is enabled; the two
    # dialogs are imported lazily in ui/mixins/_tools_ops.py since they are
    # only ever needed once the user opens them.
    from ui.dialogs.case_browser_dialog import CaseBrowserDialog
    from ui.dialogs.find_examples_dialog import FindExamplesDialog
    from ui.dialogs.log_summary_dialog import LogSummaryDialog
    from ui.panels.block_mesh_panel import BlockMeshPanel

# Floors, not caps, for a handful of pinned buttons -- see ui/fonts.py's
# button_pixel_width for why setFixedWidth needs one rather than a bare figure.
_BOTTOM_MINIMIZE_BTN_MIN_WIDTH = 28
_BM_SIDE_BY_SIDE_BTN_MIN_WIDTH = 28
_DIFF_CLEAR_BTN_MIN_WIDTH = 60


class _TreeView(QTreeView):
    """QTreeView that preserves the horizontal scroll position on selection."""

    def scrollTo(self, index, hint=QTreeView.EnsureVisible):
        h = self.horizontalScrollBar().value()
        super().scrollTo(index, hint)
        self.horizontalScrollBar().setValue(h)


class MainWindow(
    _MenuBarOpsMixin,
    _CaseOpsMixin,
    _CaseNavOpsMixin,
    _FoamMonitorOpsMixin,
    _ToolsOpsMixin,
    _ProcessorOpsMixin,
    _BackgroundRunOpsMixin,
    _FunctionObjectOpsMixin,
    _FileOpsMixin,
    _FileManagementOpsMixin,
    _TreeCrudOpsMixin,
    _TreeSyncOpsMixin,
    _UndoOpsMixin,
    _BoundaryOpsMixin,
    _DiffOpsMixin,
    _PanelOpsMixin,
    _ModelOpsMixin,
    _UiOpsMixin,
    QMainWindow,
):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(tr("foam dictionary editor"))

        self.state = AppState()
        # " — icoFoam running" in the window title while the open case has a
        # background run; set by _update_background_badge.
        self._background_title = ""
        # Every case whose background run FoDE has seen this session, so the
        # close-time reminder covers runs in cases no longer open.
        self._background_cases: set[str] = set()
        self._foam_monitor_action: QAction | None = None
        self._restore_0dir_action: QAction | None = None
        self._run_blockmesh_action: QAction | None = None
        self._run_snappyhexmesh_action: QAction | None = None
        self._run_topo_set_action: QAction | None = None
        self._run_setfields_action: QAction | None = None
        self._run_checkmesh_action: QAction | None = None
        self._run_decomposepar_action: QAction | None = None
        self._run_solver_action: QAction | None = None
        self._add_function_object_action: QAction | None = None
        self._run_post_process_action: QAction | None = None
        # Whether the open Add Function Object dialog has brought the 3-D
        # view forward yet (ui/mixins/_function_object_ops.py).
        self._preview_shown = False
        self._stop_background_run_action: QAction | None = None
        self._run_reconstructpar_action: QAction | None = None
        self._delete_processor_dirs_action: QAction | None = None
        self._run_allrun_action: QAction | None = None
        self._run_allclean_action: QAction | None = None
        self._clean_case_action: QAction | None = None
        self._open_paraview_action: QAction | None = None
        self._view_log_summary_action: QAction | None = None
        self._log_summary_dialog: LogSummaryDialog | None = None
        self._find_examples_dialog: FindExamplesDialog | None = None
        self._case_browser_dialog: CaseBrowserDialog | None = None

        self._build_ui()
        self.setAcceptDrops(True)
        self.editor_panel.editor.viewport().installEventFilter(self)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.setStatusBar(QStatusBar(self))
        self.file_list_panel = FileListPanel()
        self.comparison_panel = ComparisonTreePanel()
        self.detail_panel = DetailPanel()
        self.editor_panel = EditorPanel()
        self.right_upper_splitter: QSplitter | None = None
        # Before _build_top_bar() and _build_menu_bar() (the latter already
        # runs last): both add these same QAction objects to their own widget
        # rather than building duplicate ones, so the actions have to exist first.
        self._build_shared_actions()
        self._build_top_bar()
        tree_container = self._build_tree_area()
        self._build_feature_panels()
        self._build_diff_bar()
        self._build_splitters(tree_container)
        self._connect_signals()
        self._build_menu_bar()

    def _build_shared_actions(self) -> None:
        """QActions the top toolbar and the Case menu both add.

        One QAction added to two widgets keeps its label, tooltip, shortcut
        and enabled state in sync for free and installs the shortcut once --
        Qt's ambiguous-shortcut warning is about two *different* actions
        sharing a key, not this. `_find_examples_action` (Case + Tools menus)
        and `_view_log_summary_action` (Tools + View menus) already use the
        same trick for a menu/menu pair; this is a toolbar/menu pair.

        `Save Case` is the label on both sides now. The top bar used to say
        "Save All Files" while the Case menu said "Save Case" for the same
        `save_all_files` command; sharing one QAction forces one label, and
        Save Case wins since it is already what the keyboard-shortcuts
        dialog, i18n/ja.py, and USER_GUIDE.md call it.
        """
        self._open_case_action = QAction(icon("open-case"), tr("Open Case…"), self)
        self._open_case_action.setShortcut(QKeySequence("Ctrl+O"))
        self._open_case_action.setToolTip(tr("Open Case…"))
        self._open_case_action.triggered.connect(self.open_case)

        self._save_file_action = QAction(icon("save-file"), tr("Save File"), self)
        self._save_file_action.setShortcut(QKeySequence("Ctrl+S"))
        self._save_file_action.setToolTip(tr("Save File"))
        self._save_file_action.triggered.connect(self.save_file)

        self._save_case_action = QAction(icon("save-case"), tr("Save Case"), self)
        self._save_case_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self._save_case_action.setToolTip(tr("Save Case"))
        self._save_case_action.triggered.connect(self.save_all_files)

        # No shortcut, matching the Case menu entry this replaces: Reload
        # Case discards unsaved tree edits, and a key near Save's would
        # invite that mistake (the same reasoning Reload from Tree already
        # documents below, in _build_case_menu).
        self._reload_case_action = QAction(icon("reload-case"), tr("Reload Case"), self)
        self._reload_case_action.setToolTip(tr("Reload Case"))
        self._reload_case_action.triggered.connect(self.reload_case)

    def _build_top_bar(self) -> None:
        """Build the main action toolbar and dock it above the central widget.

        A real QToolBar via QMainWindow.addToolBar, not a QHBoxLayout stacked
        into the central widget's own layout: the "the buttons look like
        tabs" complaint traces to QPushButton always painting a raised,
        bordered rectangle, while an autoRaise QToolButton -- what a QToolBar
        builds its actions into -- paints flat until hovered. That flatness,
        not the toolbar's background, is what stops the row reading as a
        second tab bar sitting right above upper_tabs.
        """
        self.current_case_label = QLabel("-")
        self.current_case_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.current_case_label.setToolTip(tr("Current case name"))

        # Shown beside the case name only while the case has a background
        # run: the file list's row says the same, but the bottom of a list is
        # the last place anyone looks. Click for the run's two actions.
        self.background_run_btn = QToolButton()
        self.background_run_btn.setAutoRaise(True)
        self.background_run_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        badge_menu = QMenu(self.background_run_btn)
        badge_menu.addAction(tr("Stop Background Run"), self._on_stop_background_run_clicked)
        badge_menu.addAction(tr("View Log Summary…"), self._on_view_log_summary_clicked)
        self.background_run_btn.setMenu(badge_menu)

        self.current_file_label = QLabel("-")
        self.current_file_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.current_file_label.setToolTip(tr("Current file name"))

        self._foam_monitor_timer = QTimer(self)
        self._foam_monitor_timer.setInterval(2000)
        self._foam_monitor_timer.timeout.connect(self._on_foam_monitor_poll)

        self._case_dir_watcher = QFileSystemWatcher(self)
        self._case_dir_watcher.directoryChanged.connect(self._on_case_dir_changed_on_disk)
        self._file_list_refresh_timer = QTimer(self)
        self._file_list_refresh_timer.setSingleShot(True)
        self._file_list_refresh_timer.setInterval(400)
        self._file_list_refresh_timer.timeout.connect(self._reload_file_list)
        # Re-armed by _poll_background_run while the open case has a background
        # run or a pending stop (ui/mixins/_background_run_ops.py); _background_seen is
        # the run it last saw, so it can tell "finished" from "never started".
        self._background_run_timer = QTimer(self)
        self._background_run_timer.setSingleShot(True)
        self._background_run_timer.setInterval(2000)
        self._background_run_timer.timeout.connect(self._poll_background_run)
        self._background_seen: tuple[str, BackgroundRun] | None = None
        # The listed files _prime_viewer has read for the 3-D view, by path.
        self._viewer_primed: dict = {}

        self._action_toolbar = QToolBar(self)
        # Harmless today -- there is nothing to save/restore a toolbar layout
        # for yet -- but QMainWindow.saveState() warns about an unnamed
        # toolbar, so this keeps that door open.
        self._action_toolbar.setObjectName("action_toolbar")
        self._action_toolbar.setMovable(False)
        self._action_toolbar.setFloatable(False)
        self._action_toolbar.setAllowedAreas(Qt.ToolBarArea.TopToolBarArea)
        self._action_toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        icon_side = icon_pixel_size()
        self._action_toolbar.setIconSize(QSize(icon_side, icon_side))
        # Fusion's PM_ToolBarIconSize default (24 px) ignores the font
        # entirely, so -- unlike ui/icons.py's own icon() calls, which read
        # icon_pixel_size() themselves -- the toolbar's icon size has to be
        # set explicitly here too, or the two would drift apart.
        #
        # A stylesheet naming only colour/border/spacing, mirroring what
        # _build_diff_bar already does with the same theme field: under
        # Fusion a bare QToolBar paints with the window brush and no border,
        # which on its own may not read as separate from upper_tabs sitting
        # right below it. Any stylesheet on a widget routes its children
        # through QStyleSheetStyle, which risks the autoRaise flatness this
        # whole toolbar is built to get -- confirmed unaffected here (see the
        # implementation report for how). If a future style/icon change ever
        # does un-flatten the buttons, drop this setStyleSheet call and add a
        # plain 1-px QFrame HLine instead (QFrame.Shape.HLine, styled the way
        # _build_diff_bar's border-bottom is, min/max-height 1px so it cannot
        # stretch) as the first widget of the central layout in
        # _build_splitters; nothing else in this method depends on which of
        # the two supplies the separation line.
        self._action_toolbar.setStyleSheet(
            f"QToolBar {{ border: none; border-bottom: 1px solid {colors().separator};"
            f" spacing: 4px; }}"
        )
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self._action_toolbar)

        self._action_toolbar.addAction(self._open_case_action)
        self._action_toolbar.addSeparator()
        self._action_toolbar.addAction(self._save_file_action)
        self._action_toolbar.addAction(self._save_case_action)
        self._action_toolbar.addAction(self._reload_case_action)
        self._action_toolbar.addSeparator()
        self._action_toolbar.addWidget(QLabel(tr("Case:")))
        self._action_toolbar.addWidget(self.current_case_label)
        # A toolbar widget is hidden through the action addWidget returns.
        self._background_badge_action = self._action_toolbar.addWidget(self.background_run_btn)
        self._background_badge_action.setVisible(False)
        # QToolBar has no addSpacing; a fixed-width empty widget is the
        # native equivalent of the old layout's addSpacing(16) between the
        # two labels.
        label_gap = QWidget()
        label_gap.setFixedWidth(16)
        self._action_toolbar.addWidget(label_gap)
        self._action_toolbar.addWidget(QLabel(tr("File:")))
        self._action_toolbar.addWidget(self.current_file_label)

    def createPopupMenu(self) -> None:  # type: ignore[override]
        """Disable QMainWindow's built-in toolbar/dock-widget context menu.

        Right-clicking the toolbar, or the empty menu-bar strip beside it,
        otherwise opens a menu whose one entry hides action_toolbar -- and
        with no dock widgets to also list there, that is the *only* entry.
        Once hidden it stays hidden: this same menu is the only route back,
        and it no longer has anything to show once the toolbar is gone. There
        being nothing else worth keeping in that menu, it is disabled
        outright rather than filtered down to nothing.

        The ignore is for PySide6's stub, not Qt: the real virtual returns a
        nullable ``QMenu*`` (Qt's own docs say returning null is how a
        subclass disables the menu), but the bundled ``.pyi`` types it as a
        plain, non-Optional ``QMenu``.
        """
        return None

    def _build_tree_area(self) -> QWidget:
        self.proxy_model = QSortFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.state.current_model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy_model.setRecursiveFilteringEnabled(True)
        self.proxy_model.setFilterKeyColumn(FoamTreeModel.COL_KEY)

        self.tree_filter_input = QLineEdit()
        self.tree_filter_input.setPlaceholderText(tr("Filter keys…"))
        self.tree_filter_input.setClearButtonEnabled(True)
        self.tree_filter_input.textChanged.connect(self.proxy_model.setFilterFixedString)

        self.editor_autoscroll_checkbox = QCheckBox(tr("Auto-scroll editor"))
        self.editor_autoscroll_checkbox.setChecked(True)
        self._update_sync_checkbox()

        self.tree = _TreeView()
        self.tree.setModel(self.proxy_model)
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setEditTriggers(QTreeView.EditTrigger.DoubleClicked | QTreeView.EditTrigger.EditKeyPressed)
        self.tree.setSelectionBehavior(QTreeView.SelectionBehavior.SelectRows)

        filter_bar = QHBoxLayout()
        filter_bar.setContentsMargins(0, 0, 0, 0)
        filter_bar.setSpacing(6)
        filter_bar.addWidget(self.tree_filter_input)
        filter_bar.addWidget(self.editor_autoscroll_checkbox)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addLayout(filter_bar)
        layout.addWidget(self.tree)
        return container

    def _build_tree_text_sync_bar(self) -> QWidget:
        """Build the editor↔tree sync buttons that sit on the bottom tab bar.

        These two commands are the seam between the tree (upper pane) and the
        editor text (lower pane), so they live on the boundary between the two
        rather than in the top bar with the disk operations.  Riding the tab bar
        as a corner widget costs no extra vertical space and keeps them visible
        whichever tab either tab widget is showing.  The arrows read against the
        vertical splitter: the tree is above, the editor below.

        The pane-minimize button shares the bar because it is the one control
        that has to survive its own pane collapsing — minimizing this row leaves
        the tab bar as the visible sliver, so the button stays where the user
        last clicked it (see ui/pane_minimize.py).
        """
        self._apply_text_btn = QPushButton("▲ " + tr("Apply Text to Tree"))
        self._apply_text_btn.setToolTip(tr("Re-parse the editor text and rebuild the tree above"))
        self._apply_text_btn.clicked.connect(self.apply_text_to_tree)

        self._reload_text_btn = QPushButton("▼ " + tr("Reload from Tree"))
        self._reload_text_btn.setToolTip(tr("Regenerate the editor text from the tree above"))
        self._reload_text_btn.clicked.connect(self.reload_text_from_tree)

        # The splitters do not exist yet (see _build_splitters), so the click is
        # routed through a method that looks the minimizer up when it fires.
        self._bottom_minimize_btn = QPushButton("▁")
        self._bottom_minimize_btn.setFixedWidth(
            max(_BOTTOM_MINIMIZE_BTN_MIN_WIDTH, button_pixel_width("▁"))
        )
        self._bottom_minimize_btn.clicked.connect(self._on_toggle_bottom_pane_btn)

        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 6, 0)
        layout.setSpacing(4)
        layout.addWidget(self._apply_text_btn)
        layout.addWidget(self._reload_text_btn)
        layout.addWidget(self._bottom_minimize_btn)
        return bar

    def _build_feature_panels(self) -> None:
        cfg = get_app_config()
        _feat_terminal  = cfg.get_feature("terminal")
        _feat_blockmesh = cfg.get_feature("blockmesh")

        self.terminal_panel: TerminalPanel | None = None
        if _feat_terminal:
            self.terminal_panel = TerminalPanel()

        self.bottom_tabs = QTabWidget()
        self.bottom_tabs.addTab(self.editor_panel, tr("Editor"))
        if self.terminal_panel is not None:
            self.bottom_tabs.addTab(self.terminal_panel, self.terminal_panel.tab_label)
        self.bottom_tabs.setCornerWidget(
            self._build_tree_text_sync_bar(), Qt.Corner.TopRightCorner
        )

        # One navigator drives both the Cases tab and the Case Browser window,
        # so the two share a model and a location rather than each keeping
        # their own. See ui/case_navigation.py.
        self._case_navigator = CaseNavigator(self)
        self.case_nav_panel = CaseNavPanel(self._case_navigator)

        from ui.panels.boundary_view_panel import BoundaryViewPanel
        self.boundary_panel = BoundaryViewPanel()

        self.block_mesh_panel: BlockMeshPanel | None = None
        self._bm_side_by_side_btn: QPushButton | None = None
        if _feat_blockmesh:
            from ui.panels.block_mesh_panel import BlockMeshPanel
            self.block_mesh_panel = BlockMeshPanel()
            self.block_mesh_panel.vertices_changed.connect(
                self._on_blockmesh_vertices_changed
            )
            self.block_mesh_panel.image_saved.connect(self._on_blockmesh_image_saved)

    def _build_splitters(self, tree_container: QWidget) -> None:
        self.right_upper_splitter = QSplitter(Qt.Orientation.Horizontal)
        right_upper_splitter = self.right_upper_splitter
        right_upper_splitter.addWidget(tree_container)
        right_upper_splitter.addWidget(self.comparison_panel)
        right_upper_splitter.addWidget(self.detail_panel)
        right_upper_splitter.setSizes([SPLITTER_TREE_WIDTH, 0, SPLITTER_DETAIL_WIDTH])
        right_upper_splitter.setCollapsible(1, True)
        self.comparison_panel.hide()

        # Allow all panes to shrink freely regardless of child minimum hints.
        tree_container.setMinimumSize(0, 0)
        self.tree.setMinimumSize(0, 0)
        self.comparison_panel.setMinimumSize(0, 0)
        self.detail_panel.setMinimumSize(0, 0)
        right_upper_splitter.setMinimumSize(0, 0)

        # Outer splitter that holds the tree area on the left and, when
        # side-by-side mode is active, the BlockMesh 3-D panel on the right.
        # block_mesh_panel is NOT added here at startup; it lives in upper_tabs as
        # a normal tab.  It is reparented into this splitter only when the user
        # activates side-by-side mode, and moved back to a tab when they deactivate.
        self._tree_bm_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._tree_bm_splitter.addWidget(right_upper_splitter)
        self._tree_bm_splitter.setMinimumSize(0, 0)
        # Neither the tree side nor the BlockMesh panel may snap closed when
        # the handle is dragged past a pane's minimum width (also applies to
        # the panel when it is reparented in later for side-by-side mode).
        self._tree_bm_splitter.setChildrenCollapsible(False)

        self.upper_tabs = QTabWidget()
        self.upper_tabs.addTab(self._tree_bm_splitter, tr("Tree"))
        self.upper_tabs.addTab(self.boundary_panel, tr("Boundary"))
        if self.block_mesh_panel is not None:
            # When terminal is present, BlockMesh tab visibility depends on
            # whether xterm is active (xterm and VTK share the OpenGL context).
            # When there is no terminal, show BlockMesh unconditionally.
            show_bm = (self.terminal_panel is None) or (not self.terminal_panel.use_xterm)
            if show_bm:
                self.upper_tabs.addTab(self.block_mesh_panel, tr("BlockMesh"))
            # Corner button to enter/exit side-by-side mode.
            self._bm_side_by_side_btn = QPushButton("⊞")
            self._bm_side_by_side_btn.setCheckable(True)
            self._bm_side_by_side_btn.setFixedWidth(
                max(_BM_SIDE_BY_SIDE_BTN_MIN_WIDTH, button_pixel_width("⊞"))
            )
            self._bm_side_by_side_btn.setToolTip(
                tr("Show BlockMesh 3-D view alongside the tree (side-by-side)")
            )
            self._bm_side_by_side_btn.setEnabled(False)
            self._bm_side_by_side_btn.clicked.connect(self._on_toggle_bm_side_by_side)
            self.upper_tabs.setCornerWidget(self._bm_side_by_side_btn, Qt.Corner.TopRightCorner)
        self.upper_tabs.setMinimumSize(0, 0)

        # Kept as an attribute so the whole splitter layout can be read back and
        # restored as one (see ui/window_state.py).
        self.right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_splitter = self.right_splitter
        right_splitter.addWidget(self.upper_tabs)
        right_splitter.addWidget(self.bottom_tabs)
        right_splitter.setSizes([SPLITTER_UPPER_HEIGHT, SPLITTER_LOWER_HEIGHT])
        right_splitter.setHandleWidth(SPLITTER_HANDLE_WIDTH)
        # Disable collapsing so the handle moves smoothly instead of snapping.
        right_splitter.setCollapsible(0, False)
        right_splitter.setCollapsible(1, False)
        right_splitter.setStyleSheet(splitter_qss())

        # The left column holds two tabs rather than the file list alone. The
        # tab bar is its own switcher, so no extra button is needed, and
        # PANE_FILE_LIST goes on addressing main_splitter index 0 -- the
        # minimizer takes an index, not a widget, and this splitter leaves its
        # children collapsible, so setSizes still closes the column fully.
        self.left_tabs = QTabWidget()
        self.left_tabs.setDocumentMode(True)
        self.left_tabs.addTab(self.file_list_panel, tr("Files"))
        self.left_tabs.addTab(self.case_nav_panel, tr("Cases"))
        self.left_tabs.setMinimumSize(0, 0)
        self.file_list_panel.setMinimumSize(0, 0)
        self.case_nav_panel.setMinimumSize(0, 0)
        # Keep the tab bar's own minimum small, or a restore would come back
        # wider than SPLITTER_FILE_LIST_WIDTH.
        tab_bar = self.left_tabs.tabBar()
        tab_bar.setExpanding(False)
        tab_bar.setElideMode(Qt.TextElideMode.ElideRight)
        tab_bar.setUsesScrollButtons(True)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.addWidget(self.left_tabs)
        self.main_splitter.addWidget(right_splitter)
        self.main_splitter.setSizes([SPLITTER_FILE_LIST_WIDTH, SPLITTER_TREE_WIDTH + SPLITTER_DETAIL_WIDTH])

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._diff_bar)
        layout.addWidget(self.main_splitter, 1)
        self.setCentralWidget(central)

        self._build_pane_minimizers()

    def _build_pane_minimizers(self) -> None:
        """Register the minimizable panes and the double-click on their handles.

        Called once every splitter has all of its widgets, because
        ``install_handle_double_click`` can only watch the handles that exist.
        ``_tree_bm_splitter`` is deliberately left out: it sets
        ``setChildrenCollapsible(False)`` so that neither the tree nor the 3-D
        panel can snap shut on the other, and a minimize control there would be
        arguing with that.
        """
        right_upper = self.right_upper_splitter
        assert right_upper is not None  # built by _build_splitters just above
        self._pane_minimizers = {
            PANE_FILE_LIST: PaneMinimizer(
                self.main_splitter, 0, default_size=SPLITTER_FILE_LIST_WIDTH
            ),
            PANE_DETAIL: PaneMinimizer(
                right_upper, 2, default_size=SPLITTER_DETAIL_WIDTH
            ),
            # A strip, not a collapse: the sliver left behind is the tab bar,
            # which carries the Editor/Terminal tabs and the sync buttons.
            PANE_BOTTOM: PaneMinimizer(
                self.right_splitter,
                1,
                strip=lambda: self.bottom_tabs.tabBar().sizeHint().height() + 2,
                default_size=SPLITTER_LOWER_HEIGHT,
            ),
        }
        self._handle_filters = [
            install_handle_double_click(splitter, self, self._on_splitter_handle_double_click)
            for splitter in (self.main_splitter, self.right_splitter, right_upper)
        ]

    def _connect_signals(self) -> None:
        self.file_list_panel.file_selected.connect(self.load_selected_file)
        self.file_list_panel.create_file_requested.connect(self._on_create_file_requested)
        self.file_list_panel.add_file_requested.connect(self._on_add_file_requested)
        self.file_list_panel.backup_file_requested.connect(self._on_backup_file_requested)
        self.file_list_panel.manage_extra_files_requested.connect(self._on_manage_extra_files)
        self.file_list_panel.remove_extra_file_requested.connect(self._on_remove_extra_file)
        self.file_list_panel.viewer_kind_requested.connect(
            self._on_viewer_kind_requested
        )
        self.file_list_panel.duplicate_file_requested.connect(self._on_duplicate_file_requested)
        self.file_list_panel.duplicate_dir_requested.connect(self._on_duplicate_dir_requested)
        self.file_list_panel.delete_file_requested.connect(self._on_delete_file_requested)
        self.file_list_panel.delete_dir_requested.connect(self._on_delete_dir_requested)
        self.file_list_panel.save_file_requested.connect(self.save_file)
        self.file_list_panel.add_time_dir_requested.connect(self._on_add_time_dir)
        self.file_list_panel.remove_extra_dir_requested.connect(self._on_remove_extra_dir)
        self.file_list_panel.refresh_requested.connect(self._reload_file_list)
        self.file_list_panel.copy_into_case_requested.connect(self._on_copy_into_case_requested)
        flp = self.file_list_panel
        flp.reconstruct_requested.connect(self._on_run_reconstructpar_clicked)
        flp.delete_processors_requested.connect(self._on_delete_processor_dirs_clicked)
        flp.stop_background_requested.connect(self._on_stop_background_run_clicked)
        flp.view_log_summary_requested.connect(self._on_view_log_summary_clicked)
        flp.run_post_process_requested.connect(self._on_run_post_process_for_file)
        nav = self._case_navigator
        nav.browser_requested.connect(self._on_open_case_browser)
        nav.open_case_requested.connect(self._on_case_nav_open_requested)
        nav.compare_case_requested.connect(self._on_case_nav_compare_requested)
        nav.duplicate_case_requested.connect(self._on_case_nav_duplicate_requested)
        nav.move_requested.connect(self._on_case_nav_move_requested)
        nav.rename_requested.connect(self._on_case_nav_rename_requested)
        nav.delete_requested.connect(self._on_case_nav_delete_requested)
        nav.new_folder_requested.connect(self._on_case_nav_new_folder_requested)
        nav.status_message.connect(
            lambda message: self.statusBar().showMessage(message, STATUS_NORMAL)
        )
        nav.go_to(nav.initial_location(self.state.current_case_dir))
        self.boundary_panel.patch_edit_requested.connect(self._on_patch_edit_requested)
        self.boundary_panel.patch_create_requested.connect(self._on_patch_create_requested)
        self.boundary_panel.patch_delete_requested.connect(self._on_patch_delete_requested)
        self.boundary_panel.patch_paste_requested.connect(self._on_patch_paste_requested)
        self.boundary_panel.patch_delete_all_requested.connect(self._on_patch_delete_all_requested)
        self.boundary_panel.patch_add_all_requested.connect(self._on_patch_add_all_requested)
        self.boundary_panel.patch_rename_requested.connect(self._on_rename_boundary_by_name)
        self.boundary_panel.patch_selected.connect(self._on_patch_selected)
        self.detail_panel.value_apply_requested.connect(self._on_value_apply)
        self.detail_panel.field_value_apply_requested.connect(self._on_field_value_apply)
        self.editor_panel.user_text_changed.connect(self._on_user_text_changed)
        self.editor_panel.find_in_tree_requested.connect(self._sync_tree_to_editor_line)
        find_tree_sc = QShortcut(QKeySequence("Ctrl+Shift+T"), self)
        find_tree_sc.activated.connect(self._sync_tree_to_editor_line)
        if self.terminal_panel is not None:
            self.terminal_panel.mode_changed.connect(self._on_terminal_mode_changed)

        self.comparison_panel.use_value_requested.connect(self._apply_comparison_value)
        self._connect_tree_selection()
        self._setup_tree_copy_paste()
        self._setup_tree_undo()
        self.tree.setColumnHidden(FoamTreeModel.COL_TYPE, True)
        self.detail_panel.show_empty()
        self._update_case_label()
        self._update_file_label()


    # ── drag-and-drop ─────────────────────────────────────────────────────────

    def _dir_from_drop(self, mime_data) -> str | None:
        urls = mime_data.urls()
        if len(urls) == 1 and urls[0].isLocalFile():
            path = urls[0].toLocalFile()
            if Path(path).is_dir():
                return path
        return None

    def dragEnterEvent(self, event) -> None:
        if self._dir_from_drop(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        path = self._dir_from_drop(event.mimeData())
        if path and self._confirm_discard_if_needed():
            self._load_case_dir(path)

    def eventFilter(self, obj, event):
        # QPlainTextEdit (the code editor) accepts drops by default; intercept
        # directory drops before they reach it.
        if event.type() == QEvent.DragEnter:
            if self._dir_from_drop(event.mimeData()):
                event.acceptProposedAction()
                return True
        elif event.type() == QEvent.Drop:
            path = self._dir_from_drop(event.mimeData())
            if path:
                if self._confirm_discard_if_needed():
                    self._load_case_dir(path)
                return True
        return False

    # ── window lifecycle ──────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        # First, because it is the costlier loss: unsaved text can be saved in
        # the prompt that follows, a run killed mid-step cannot be resumed.
        if self.terminal_panel is not None and not self.terminal_panel.confirm_stop_running(
            self, tr("Closing FoDE")
        ):
            event.ignore()
            return
        if not self._confirm_discard_if_needed():
            event.ignore()
            return
        # After both questions that can cancel the close, so it only appears
        # when FoDE really is closing; before the save, so "Don't remind me
        # again" is stored.
        self._remind_background_runs()
        cfg = get_app_config()
        # "Reset All Settings" deleted app_config.json earlier in this run.
        # Capturing the layout and window size below would recreate the file and
        # undo the reset, so this run persists nothing — the dialog has already
        # told the user to restart.
        persist = not cfg.settings_were_reset
        if persist:
            # Before the panels are torn down: a shut-down BlockMesh panel has no
            # camera left to read, and a cleaned-up terminal no mode.
            save_session(self)
        self._stop_foam_monitor()
        if self.terminal_panel is not None:
            self.terminal_panel.cleanup()
        if self.block_mesh_panel is not None:
            self.block_mesh_panel.shutdown()
        if persist:
            cfg.set_window_size(self.width(), self.height())
            cfg.save()
        event.accept()

    # ── diff overlay ─────────────────────────────────────────────────────────

    def _build_diff_bar(self) -> None:
        c = colors()
        self._diff_bar = QFrame()
        self._diff_bar.setStyleSheet(
            f"QFrame {{ background-color: {c.legend_bg}; color: {c.legend_fg};"
            f" border-bottom: 1px solid {c.legend_border}; }}"
        )

        # Swatches must match FoamTreeModel's diff row backgrounds exactly, so
        # both sides read them from the same theme fields.
        def swatch(fill: str) -> str:
            return (
                f'<span style="background:{fill};padding:0 4px;'
                f'border:1px solid {c.separator};">&#160;</span>'
            )

        legend = QLabel(
            swatch(c.diff_changed) + " changed &nbsp;"
            + swatch(c.diff_only_here) + " only in current &nbsp;"
            + swatch(c.diff_only_in_ref) + " only in reference &nbsp;|&nbsp;"
        )
        legend.setTextFormat(Qt.TextFormat.RichText)
        self._diff_path_label = QLabel()
        self._side_by_side_cb = QCheckBox(tr("Side by side"))
        self._side_by_side_cb.toggled.connect(self._on_side_by_side_toggled)
        clear_text = tr("Clear")
        clear_btn = QPushButton(clear_text)
        # Measured from clear_text rather than a fresh tr("Clear"): the width has
        # to be measured from the very string the button shows, and the Japanese
        # クリア is wider than "Clear" -- a translation can overflow a cap the
        # original still fits.
        clear_btn.setFixedWidth(max(_DIFF_CLEAR_BTN_MIN_WIDTH, button_pixel_width(clear_text)))
        clear_btn.clicked.connect(self._clear_diff)
        bar_layout = QHBoxLayout(self._diff_bar)
        bar_layout.setContentsMargins(8, 2, 8, 2)
        bar_layout.addWidget(legend)
        bar_layout.addWidget(self._diff_path_label, 1)
        bar_layout.addWidget(self._side_by_side_cb)
        bar_layout.addWidget(clear_btn)
        self._diff_bar.hide()

