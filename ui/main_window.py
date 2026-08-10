# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QFileSystemWatcher, QSortFilterProxyModel, Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from app_config import get_app_config
from i18n import tr
from model.tree_model import FoamTreeModel
from ui.app_state import AppState
from ui.layout_constants import (
    SPLITTER_DETAIL_WIDTH,
    SPLITTER_FILE_LIST_WIDTH,
    SPLITTER_HANDLE_WIDTH,
    SPLITTER_LOWER_HEIGHT,
    SPLITTER_TREE_WIDTH,
    SPLITTER_UPPER_HEIGHT,
)
from ui.mixins._boundary_ops import _BoundaryOpsMixin
from ui.mixins._case_ops import _CaseOpsMixin
from ui.mixins._diff_ops import _DiffOpsMixin
from ui.mixins._file_mgmt_ops import _FileManagementOpsMixin
from ui.mixins._file_ops import _FileOpsMixin
from ui.mixins._foam_monitor_ops import _FoamMonitorOpsMixin
from ui.mixins._model_ops import _ModelOpsMixin
from ui.mixins._panel_ops import _PanelOpsMixin
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
    from ui.dialogs.find_examples_dialog import FindExamplesDialog
    from ui.dialogs.log_summary_dialog import LogSummaryDialog
    from ui.panels.block_mesh_panel import BlockMeshPanel


class _TreeView(QTreeView):
    """QTreeView that preserves the horizontal scroll position on selection."""

    def scrollTo(self, index, hint=QTreeView.EnsureVisible):
        h = self.horizontalScrollBar().value()
        super().scrollTo(index, hint)
        self.horizontalScrollBar().setValue(h)


def _act(menu, label: str, shortcut: str, slot) -> None:
    action = menu.addAction(label)
    action.setShortcut(QKeySequence(shortcut))
    action.triggered.connect(slot)


class MainWindow(
    _CaseOpsMixin,
    _FoamMonitorOpsMixin,
    _ToolsOpsMixin,
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
        self._foam_monitor_action: QAction | None = None
        self._restore_0dir_action: QAction | None = None
        self._run_blockmesh_action: QAction | None = None
        self._run_snappyhexmesh_action: QAction | None = None
        self._run_topo_set_action: QAction | None = None
        self._run_setfields_action: QAction | None = None
        self._run_checkmesh_action: QAction | None = None
        self._run_allrun_action: QAction | None = None
        self._run_allclean_action: QAction | None = None
        self._clean_case_action: QAction | None = None
        self._open_paraview_action: QAction | None = None
        self._view_log_summary_action: QAction | None = None
        self._log_summary_dialog: LogSummaryDialog | None = None
        self._find_examples_dialog: FindExamplesDialog | None = None

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
        top_bar = self._build_top_bar()
        tree_container = self._build_tree_area()
        self._build_feature_panels()
        self._build_diff_bar()
        self._build_splitters(tree_container, top_bar)
        self._connect_signals()
        self._build_menu_bar()

    def _build_top_bar(self) -> QHBoxLayout:
        self.current_case_label = QLabel("-")
        self.current_case_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.current_case_label.setToolTip(tr("Current case name"))

        self.current_file_label = QLabel("-")
        self.current_file_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.current_file_label.setToolTip(tr("Current file name"))

        save_btn = QPushButton(tr("Save File"))
        save_all_btn = QPushButton(tr("Save All Files"))
        reload_case_btn = QPushButton(tr("Reload Case"))
        save_btn.clicked.connect(self.save_file)
        save_all_btn.clicked.connect(self.save_all_files)
        reload_case_btn.clicked.connect(self.reload_case)

        self._foam_monitor_timer = QTimer(self)
        self._foam_monitor_timer.setInterval(2000)
        self._foam_monitor_timer.timeout.connect(self._on_foam_monitor_poll)

        self._case_dir_watcher = QFileSystemWatcher(self)
        self._case_dir_watcher.directoryChanged.connect(self._on_case_dir_changed_on_disk)
        self._file_list_refresh_timer = QTimer(self)
        self._file_list_refresh_timer.setSingleShot(True)
        self._file_list_refresh_timer.setInterval(400)
        self._file_list_refresh_timer.timeout.connect(self._reload_file_list)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)

        layout = QHBoxLayout()
        layout.setContentsMargins(4, 4, 4, 2)
        layout.addWidget(save_btn)
        layout.addWidget(save_all_btn)
        layout.addWidget(reload_case_btn)
        layout.addWidget(sep)
        layout.addWidget(QLabel(tr("Case:")))
        layout.addWidget(self.current_case_label)
        layout.addSpacing(16)
        layout.addWidget(QLabel(tr("File:")))
        layout.addWidget(self.current_file_label)
        layout.addStretch(1)
        return layout

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
        self._bottom_minimize_btn.setFixedWidth(28)
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

    def _build_splitters(self, tree_container: QWidget, top_bar: QHBoxLayout) -> None:
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
            self._bm_side_by_side_btn.setFixedWidth(28)
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

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.addWidget(self.file_list_panel)
        self.main_splitter.addWidget(right_splitter)
        self.main_splitter.setSizes([SPLITTER_FILE_LIST_WIDTH, SPLITTER_TREE_WIDTH + SPLITTER_DETAIL_WIDTH])

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(top_bar)
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
        self.file_list_panel.duplicate_file_requested.connect(self._on_duplicate_file_requested)
        self.file_list_panel.duplicate_dir_requested.connect(self._on_duplicate_dir_requested)
        self.file_list_panel.delete_file_requested.connect(self._on_delete_file_requested)
        self.file_list_panel.delete_dir_requested.connect(self._on_delete_dir_requested)
        self.file_list_panel.save_file_requested.connect(self.save_file)
        self.file_list_panel.add_time_dir_requested.connect(self._on_add_time_dir)
        self.file_list_panel.remove_extra_dir_requested.connect(self._on_remove_extra_dir)
        self.file_list_panel.refresh_requested.connect(self._reload_file_list)
        self.file_list_panel.copy_into_case_requested.connect(self._on_copy_into_case_requested)
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

    def _build_menu_bar(self) -> None:
        menubar = self.menuBar()

        # One action, two menus (Case and Tools): searching the tutorials is
        # both a reference lookup and the entry point for starting a new case
        # from a duplicated example.
        self._find_examples_action = QAction(tr("Find OpenFOAM Examples…"), self)
        self._find_examples_action.setToolTip(
            tr("Search example usages in the OpenFOAM tutorials and etc/caseDicts templates")
        )
        self._find_examples_action.triggered.connect(self._on_find_examples_clicked)

        self._build_case_menu(menubar)
        self._build_settings_menu(menubar)
        view_menu = self._build_view_menu(menubar)
        self._build_tools_menu(menubar, view_menu)
        self._build_help_menu(menubar)

    def _build_case_menu(self, menubar) -> None:
        case_menu = menubar.addMenu(tr("Case"))
        _act(case_menu, tr("Open Case"),              "Ctrl+O",       self.open_case)
        case_menu.addAction(tr("Open from Case Library...")).triggered.connect(self.open_from_library)
        case_menu.addAction(tr("Reload Case")).triggered.connect(self.reload_case)
        case_menu.addSeparator()
        _act(case_menu, tr("Save File"),              "Ctrl+S",       self.save_file)
        _act(case_menu, tr("Save Case"),              "Ctrl+Shift+S", self.save_all_files)
        case_menu.addAction(tr("Save as New Case...")).triggered.connect(self.save_as_new_case)
        case_menu.addSeparator()
        # Also on the bottom tab bar (see _build_tree_text_sync_bar).  Reload
        # from Tree deliberately has no shortcut: it overwrites the editor text,
        # discarding edits not yet applied, and any key near "Reload Case" would
        # invite exactly that mistake.
        _act(case_menu, tr("Apply Text to Tree"),     "Ctrl+Shift+A", self.apply_text_to_tree)
        case_menu.addAction(tr("Reload from Tree")).triggered.connect(self.reload_text_from_tree)
        case_menu.addSeparator()
        case_menu.addAction(tr("Duplicate Case...")).triggered.connect(self.duplicate_case)
        case_menu.addAction(tr("Duplicate from Case Library...")).triggered.connect(
            self.duplicate_from_library
        )
        case_menu.addAction(self._find_examples_action)
        case_menu.addSeparator()
        case_menu.addAction(tr("Clean Backup Files...")).triggered.connect(self._on_clean_backups)
        case_menu.addSeparator()
        case_menu.addAction(tr("Compare with Case...")).triggered.connect(self._compare_with_case)
        case_menu.addSeparator()
        _act(case_menu, tr("Exit"),                   "Ctrl+Q",       self.close)

    def _build_settings_menu(self, menubar) -> None:
        settings_menu = menubar.addMenu(tr("Settings"))
        settings_menu.addAction(tr("Set Default Case Directory")).triggered.connect(
            self.set_default_case_directory
        )
        settings_menu.addAction(tr("Manage Case Library…")).triggered.connect(self.manage_case_library)
        settings_menu.addAction(tr("Manage Extra Files & Directories…")).triggered.connect(
            self._on_manage_extra_files
        )
        settings_menu.addAction(tr("Reset File List")).triggered.connect(self.reset_file_list)
        settings_menu.addSeparator()
        settings_menu.addAction(tr("Manage Schema Modules")).triggered.connect(self.open_schema_manager)
        settings_menu.addAction(tr("Generate OpenFOAM Keywords…")).triggered.connect(
            self.generate_foam_keywords
        )
        settings_menu.addAction(tr("Reset Window Size")).triggered.connect(self.reset_window_size)
        settings_menu.addSeparator()
        self._restore_session_action = QAction(tr("Restore Last Session on Startup"), self)
        self._restore_session_action.setCheckable(True)
        self._restore_session_action.setChecked(get_app_config().get_restore_session())
        self._restore_session_action.setToolTip(
            tr("Reopen the window layout, case and files from the last time the "
               "application was closed. Unticking this keeps what is stored; use "
               "Forget Saved Session to discard it.")
        )
        self._restore_session_action.toggled.connect(self._on_restore_session_toggled)
        settings_menu.addAction(self._restore_session_action)
        self._forget_session_action = QAction(tr("Forget Saved Session"), self)
        self._forget_session_action.setToolTip(
            tr("Discard the stored window layouts, including those of the other "
               "variants. The next launch opens a default window.")
        )
        self._forget_session_action.setEnabled(get_app_config().has_stored_sessions())
        self._forget_session_action.triggered.connect(self._forget_saved_session)
        settings_menu.addAction(self._forget_session_action)
        # The stored layout changes at close, long after this menu was built.
        settings_menu.aboutToShow.connect(self._refresh_forget_session_action)
        settings_menu.addSeparator()
        settings_menu.addAction(tr("Reset All Settings…")).triggered.connect(self.reset_all_settings)
        settings_menu.addSeparator()
        self._build_appearance_menu(settings_menu)
        self._build_ui_scale_menu(settings_menu)
        self._build_language_menu(settings_menu)

    def _build_view_menu(self, menubar):
        view_menu = menubar.addMenu(tr("View"))
        self._show_type_action = QAction(tr("Show Type Column"), self)
        self._show_type_action.setCheckable(True)
        self._show_type_action.setChecked(False)
        self._show_type_action.toggled.connect(self._on_toggle_type_column)
        view_menu.addAction(self._show_type_action)

        view_menu.addSeparator()
        self._build_pane_menu_actions(view_menu)

        self._blockmesh_action: QAction | None = None
        if self.block_mesh_panel is not None:
            view_menu.addSeparator()
            self._blockmesh_action = QAction(tr("BlockMesh 3-D Panel"), self)
            self._blockmesh_action.setCheckable(True)
            xterm_active = (
                self.terminal_panel is not None and self.terminal_panel.use_xterm
            )
            self._blockmesh_action.setChecked(not xterm_active)
            self._blockmesh_action.setEnabled(not xterm_active)
            if xterm_active:
                self._blockmesh_action.setText(
                    tr("BlockMesh 3-D Panel  (unavailable: xterm active)")
                )
            self._blockmesh_action.toggled.connect(self._on_toggle_blockmesh_panel)
            view_menu.addAction(self._blockmesh_action)

        return view_menu

    def _build_tools_menu(self, menubar, view_menu) -> None:
        tools_menu = menubar.addMenu(tr("Tools"))

        def _tool_act(label: str, tooltip: str, slot, enabled: bool = False) -> QAction:
            action = QAction(label, self)
            action.setEnabled(enabled)
            action.setToolTip(tooltip)
            action.triggered.connect(slot)
            tools_menu.addAction(action)
            return action

        self._foam_monitor_action = _tool_act(
            tr("foamMonitor…"),
            tr("Launch foamMonitor to plot residuals or other data with gnuplot"),
            self._on_foam_monitor_clicked,
        )
        tools_menu.addSeparator()
        self._restore_0dir_action = _tool_act(
            tr("Restore 0/ from 0.orig"),
            tr("Delete 0/ and replace it with a fresh copy of 0.orig/"),
            self._on_restore_0dir_clicked,
        )
        self._run_blockmesh_action = _tool_act(
            tr("Run blockMesh…"),
            tr("Choose options and run blockMesh in the terminal panel"),
            self._on_run_blockmesh_clicked,
        )
        self._run_snappyhexmesh_action = _tool_act(
            tr("Run snappyHexMesh…"),
            tr("Choose options and run snappyHexMesh in the terminal panel"),
            self._on_run_snappyhexmesh_clicked,
        )
        self._run_topo_set_action = _tool_act(
            tr("Run topoSet…"),
            tr("Choose options and run topoSet in the terminal panel"),
            self._on_run_topo_set_clicked,
        )
        self._run_setfields_action = _tool_act(
            tr("Run setFields…"),
            tr(
                "Choose options and run setFields in the terminal panel — sets "
                "initial field regions in 0/ from system/setFieldsDict"
            ),
            self._on_run_setfields_clicked,
        )
        self._run_checkmesh_action = _tool_act(
            tr("Run checkMesh…"),
            tr(
                "Choose options and run checkMesh in the terminal panel to "
                "validate the mesh"
            ),
            self._on_run_checkmesh_clicked,
        )
        self._run_allrun_action = _tool_act(
            tr("Run Allrun Script"),
            tr(
                "Send './Allrun' to the terminal panel — runs the case's full "
                "workflow, including the solver"
            ),
            self._on_run_allrun_clicked,
        )
        self._open_paraview_action = _tool_act(
            tr("Open Mesh in ParaView…"),
            tr("Open the case's generated mesh in ParaView (paraFoam)"),
            self._on_open_paraview_clicked,
        )
        tools_menu.addSeparator()
        self._run_allclean_action = _tool_act(
            tr("Run Allclean Script"),
            tr("Send './Allclean' to the terminal panel to clean the case"),
            self._on_run_allclean_clicked,
        )
        self._clean_case_action = _tool_act(
            tr("Clean Case (foamCleanTutorials)"),
            tr(
                "Clean the case with foamCleanTutorials; runs ./Allclean "
                "when the case has one"
            ),
            self._on_clean_case_clicked,
        )
        tools_menu.addSeparator()
        self._view_log_summary_action = _tool_act(
            tr("View Log Summary…"),
            tr(
                "Show a condensed summary of a log.* file "
                "(blockMesh, snappyHexMesh, topoSet, setFields, checkMesh, ...)"
            ),
            self._on_view_log_summary_clicked,
        )
        # Users reasonably look for "View Log Summary" under View, so the same
        # QAction is listed there too (one action, two menus — enablement and
        # behaviour stay in sync automatically).
        view_menu.addSeparator()
        view_menu.addAction(self._view_log_summary_action)
        tools_menu.addSeparator()
        tools_menu.addAction(self._find_examples_action)

    def _build_help_menu(self, menubar) -> None:
        help_menu = menubar.addMenu(tr("Help"))
        help_menu.addAction(tr("About Foam Dictionary Editor (FoDE)...")).triggered.connect(self.show_about)
        help_menu.addSeparator()
        help_menu.addAction(tr("Keyboard Shortcuts...")).triggered.connect(self.show_keyboard_shortcuts)
        help_menu.addAction(tr("Resources...")).triggered.connect(self.show_openfoam_resources)

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
        if not self._confirm_discard_if_needed():
            event.ignore()
            return
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
        clear_btn = QPushButton(tr("Clear"))
        clear_btn.setFixedWidth(60)
        clear_btn.clicked.connect(self._clear_diff)
        bar_layout = QHBoxLayout(self._diff_bar)
        bar_layout.setContentsMargins(8, 2, 8, 2)
        bar_layout.addWidget(legend)
        bar_layout.addWidget(self._diff_path_label, 1)
        bar_layout.addWidget(self._side_by_side_cb)
        bar_layout.addWidget(clear_btn)
        self._diff_bar.hide()

