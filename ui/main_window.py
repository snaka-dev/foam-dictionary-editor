# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QFileSystemWatcher, QSortFilterProxyModel, QTimer
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
from ui.mixins._boundary_ops import _BoundaryOpsMixin
from ui.mixins._case_ops import _CaseOpsMixin
from ui.mixins._foam_monitor_ops import _FoamMonitorOpsMixin
from ui.mixins._tools_ops import _ToolsOpsMixin
from ui.mixins._diff_ops import _DiffOpsMixin
from ui.mixins._file_mgmt_ops import _FileManagementOpsMixin
from ui.mixins._file_ops import _FileOpsMixin
from ui.mixins._panel_ops import _PanelOpsMixin
from ui.mixins._model_ops import _ModelOpsMixin
from ui.mixins._ui_ops import _UiOpsMixin
from ui.mixins._tree_crud_ops import _TreeCrudOpsMixin
from ui.mixins._tree_sync_ops import _TreeSyncOpsMixin
from ui.app_state import AppState
from ui.panels.comparison_tree_panel import ComparisonTreePanel
from ui.panels.detail_panel import DetailPanel
from ui.panels.editor_panel import EditorPanel
from ui.panels.file_list_panel import FileListPanel
from ui.panels.terminal_panel import TerminalPanel
from ui.layout_constants import (
    SPLITTER_DETAIL_WIDTH,
    SPLITTER_FILE_LIST_WIDTH,
    SPLITTER_HANDLE_WIDTH,
    SPLITTER_LOWER_HEIGHT,
    SPLITTER_TREE_WIDTH,
    SPLITTER_UPPER_HEIGHT,
)


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
    _BoundaryOpsMixin,
    _DiffOpsMixin,
    _PanelOpsMixin,
    _ModelOpsMixin,
    _UiOpsMixin,
    QMainWindow,
):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("foam dictionary editor"))

        self.state = AppState()
        self._foam_monitor_action: QAction | None = None
        self._restore_0dir_action: QAction | None = None
        self._run_blockmesh_action: QAction | None = None
        self._open_paraview_action: QAction | None = None

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
        self.current_case_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.current_case_label.setToolTip(tr("Current case name"))

        self.current_file_label = QLabel("-")
        self.current_file_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.current_file_label.setToolTip(tr("Current file name"))

        save_btn = QPushButton(tr("Save File"))
        save_all_btn = QPushButton(tr("Save All Files"))
        reload_case_btn = QPushButton(tr("Reload Case"))
        apply_btn = QPushButton(tr("Apply Text to Tree"))
        reload_btn = QPushButton(tr("Reload from Tree"))
        save_btn.clicked.connect(self.save_file)
        save_all_btn.clicked.connect(self.save_all_files)
        reload_case_btn.clicked.connect(self.reload_case)
        apply_btn.clicked.connect(self.apply_text_to_tree)
        reload_btn.clicked.connect(self.reload_text_from_tree)

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
        sep.setFrameShape(QFrame.VLine)
        sep.setFrameShadow(QFrame.Sunken)

        layout = QHBoxLayout()
        layout.setContentsMargins(4, 4, 4, 2)
        layout.addWidget(save_btn)
        layout.addWidget(save_all_btn)
        layout.addWidget(reload_case_btn)
        layout.addWidget(sep)
        layout.addWidget(apply_btn)
        layout.addWidget(reload_btn)
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
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
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
        self.tree.setEditTriggers(QTreeView.DoubleClicked | QTreeView.EditKeyPressed)
        self.tree.setSelectionBehavior(QTreeView.SelectRows)

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

        from ui.panels.boundary_view_panel import BoundaryViewPanel
        self.boundary_panel = BoundaryViewPanel()

        self.block_mesh_panel = None
        self._bm_side_by_side_btn: "QPushButton | None" = None
        if _feat_blockmesh:
            from ui.panels.block_mesh_panel import BlockMeshPanel
            self.block_mesh_panel = BlockMeshPanel()
            self.block_mesh_panel.vertices_changed.connect(
                self._on_blockmesh_vertices_changed
            )

    def _build_splitters(self, tree_container: QWidget, top_bar: QHBoxLayout) -> None:
        self.right_upper_splitter = QSplitter(Qt.Horizontal)
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
        self._tree_bm_splitter = QSplitter(Qt.Horizontal)
        self._tree_bm_splitter.addWidget(right_upper_splitter)
        self._tree_bm_splitter.setMinimumSize(0, 0)

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
            self.upper_tabs.setCornerWidget(self._bm_side_by_side_btn, Qt.TopRightCorner)
        self.upper_tabs.setMinimumSize(0, 0)

        right_splitter = QSplitter(Qt.Vertical)
        right_splitter.addWidget(self.upper_tabs)
        right_splitter.addWidget(self.bottom_tabs)
        right_splitter.setSizes([SPLITTER_UPPER_HEIGHT, SPLITTER_LOWER_HEIGHT])
        right_splitter.setHandleWidth(SPLITTER_HANDLE_WIDTH)
        # Disable collapsing so the handle moves smoothly instead of snapping.
        right_splitter.setCollapsible(0, False)
        right_splitter.setCollapsible(1, False)
        right_splitter.setStyleSheet("""
            QSplitter::handle:vertical {
                background-color: #d6d6d6;
                border-top: 1px solid #b8b8b8;
                border-bottom: 1px solid #efefef;
                height: 7px;
            }
        """)

        self.main_splitter = QSplitter(Qt.Horizontal)
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
        self.tree.setColumnHidden(FoamTreeModel.COL_TYPE, True)
        self.detail_panel.show_empty()
        self._update_case_label()
        self._update_file_label()

    def _build_menu_bar(self) -> None:
        menubar = self.menuBar()

        case_menu = menubar.addMenu(tr("Case"))
        _act(case_menu, tr("Open Case"),              "Ctrl+O",       self.open_case)
        case_menu.addAction(tr("Open from Case Library...")).triggered.connect(self.open_from_library)
        case_menu.addAction(tr("Reload Case")).triggered.connect(self.reload_case)
        case_menu.addSeparator()
        _act(case_menu, tr("Save Case"),              "Ctrl+Shift+S", self.save_all_files)
        case_menu.addAction(tr("Save as New Case...")).triggered.connect(self.save_as_new_case)
        case_menu.addSeparator()
        case_menu.addAction(tr("Duplicate Case...")).triggered.connect(self.duplicate_case)
        case_menu.addAction(tr("Duplicate from Case Library...")).triggered.connect(self.duplicate_from_library)
        case_menu.addSeparator()
        case_menu.addAction(tr("Clean Backup Files...")).triggered.connect(self._on_clean_backups)
        case_menu.addSeparator()
        case_menu.addAction(tr("Compare with Case...")).triggered.connect(self._compare_with_case)
        case_menu.addSeparator()
        _act(case_menu, tr("Exit"),                   "Ctrl+Q",       self.close)

        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self.save_file)

        settings_menu = menubar.addMenu(tr("Settings"))
        settings_menu.addAction(tr("Set Default Case Directory")).triggered.connect(self.set_default_case_directory)
        settings_menu.addAction(tr("Manage Case Library…")).triggered.connect(self.manage_case_library)
        settings_menu.addAction(tr("Manage Extra Files & Directories…")).triggered.connect(self._on_manage_extra_files)
        settings_menu.addAction(tr("Reset File List")).triggered.connect(self.reset_file_list)
        settings_menu.addSeparator()
        settings_menu.addAction(tr("Manage Schema Modules")).triggered.connect(self.open_schema_manager)
        settings_menu.addAction(tr("Generate OpenFOAM Keywords…")).triggered.connect(self.generate_foam_keywords)
        settings_menu.addAction(tr("Reset Window Size")).triggered.connect(self.reset_window_size)
        settings_menu.addSeparator()
        settings_menu.addAction(tr("Reset All Settings…")).triggered.connect(self.reset_all_settings)
        settings_menu.addSeparator()
        self._build_language_menu(settings_menu)

        view_menu = menubar.addMenu(tr("View"))
        self._show_type_action = QAction(tr("Show Type Column"), self)
        self._show_type_action.setCheckable(True)
        self._show_type_action.setChecked(False)
        self._show_type_action.toggled.connect(self._on_toggle_type_column)
        view_menu.addAction(self._show_type_action)

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

        tools_menu = menubar.addMenu(tr("Tools"))
        self._foam_monitor_action = QAction(tr("foamMonitor…"), self)
        self._foam_monitor_action.setEnabled(False)
        self._foam_monitor_action.setToolTip(
            tr("Launch foamMonitor to plot residuals or other data with gnuplot")
        )
        self._foam_monitor_action.triggered.connect(self._on_foam_monitor_clicked)
        tools_menu.addAction(self._foam_monitor_action)

        tools_menu.addSeparator()
        self._restore_0dir_action = QAction(tr("Restore 0/ from 0.orig"), self)
        self._restore_0dir_action.setEnabled(False)
        self._restore_0dir_action.setToolTip(
            tr("Delete 0/ and replace it with a fresh copy of 0.orig/")
        )
        self._restore_0dir_action.triggered.connect(self._on_restore_0dir_clicked)
        tools_menu.addAction(self._restore_0dir_action)

        self._run_blockmesh_action = QAction(tr("Run blockMesh"), self)
        self._run_blockmesh_action.setEnabled(False)
        self._run_blockmesh_action.setToolTip(
            tr("Send 'blockMesh' to the terminal panel")
        )
        self._run_blockmesh_action.triggered.connect(self._on_run_blockmesh_clicked)
        tools_menu.addAction(self._run_blockmesh_action)

        self._open_paraview_action = QAction(tr("Open Mesh in ParaView…"), self)
        self._open_paraview_action.setEnabled(False)
        self._open_paraview_action.setToolTip(
            tr("Open the case's generated mesh in ParaView (paraFoam)")
        )
        self._open_paraview_action.triggered.connect(self._on_open_paraview_clicked)
        tools_menu.addAction(self._open_paraview_action)

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
        self._stop_foam_monitor()
        if self.terminal_panel is not None:
            self.terminal_panel.cleanup()
        if self.block_mesh_panel is not None:
            self.block_mesh_panel.shutdown()
        cfg = get_app_config()
        cfg.set_window_size(self.width(), self.height())
        cfg.save()
        event.accept()

    # ── diff overlay ─────────────────────────────────────────────────────────

    def _build_diff_bar(self) -> None:
        self._diff_bar = QFrame()
        self._diff_bar.setStyleSheet(
            "QFrame { background-color: #FFFBEA; border-bottom: 1px solid #E0C04C; }"
        )
        legend = QLabel(
            '<span style="background:#FFFACD;padding:0 4px;border:1px solid #ccc;">&#160;</span>'
            " changed &nbsp;"
            '<span style="background:#E3F2FD;padding:0 4px;border:1px solid #ccc;">&#160;</span>'
            " only in current &nbsp;"
            '<span style="background:#E8F5E9;padding:0 4px;border:1px solid #ccc;">&#160;</span>'
            " only in reference &nbsp;|&nbsp;"
        )
        legend.setTextFormat(Qt.RichText)
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

