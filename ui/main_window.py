# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QSortFilterProxyModel, QTimer
from PySide6.QtGui import QAction, QActionGroup, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from app_config import get_app_config
from i18n import available_languages, get_language, tr
from foam.diff import diff_trees, diff_trees_reverse
from foam.nodes import FoamNode
from foam.parser import OpenFoamParser
from foam.utils import read_foam_file, is_large_non_foam_file
from foam.writer import write_root
from model.tree_model import FoamTreeModel
from ui._boundary_ops import _BoundaryOpsMixin
from ui._case_ops import _CaseOpsMixin
from ui._file_ops import _FileOpsMixin
from ui._tree_ops import _TreeOpsMixin
from ui.comparison_tree_panel import ComparisonTreePanel
from ui.detail_panel import DetailPanel
from ui.editor_panel import EditorPanel
from ui.file_list_panel import FileListPanel, display_file_name
from ui.terminal_panel import TerminalPanel
from ui.layout_constants import (
    BLOCKMESH_DICT_NAME as _BLOCKMESH_DICT_NAME,
    SPLITTER_COMPARISON_WIDTH,
    SPLITTER_DETAIL_WIDTH,
    SPLITTER_FILE_LIST_WIDTH,
    SPLITTER_HANDLE_WIDTH,
    SPLITTER_LOWER_HEIGHT,
    SPLITTER_TREE_WIDTH,
    SPLITTER_UPPER_HEIGHT,
    STATUS_SHORT as _STATUS_SHORT,
    STATUS_WARNING as _STATUS_WARNING,
)

_TREE_EXPAND_DEPTH = 2


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


class MainWindow(_CaseOpsMixin, _FileOpsMixin, _TreeOpsMixin, _BoundaryOpsMixin, QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("foam dictionary editor"))

        self.current_case_dir: str | None = None
        self.current_file: str | None = None
        self.current_root = FoamNode(name="root", node_type="dictionary")
        self.current_model = FoamTreeModel(self.current_root)

        self.file_buffers: dict[str, str] = {}
        self.file_dirty: dict[str, bool] = {}
        self.text_dirty = False
        self._source_lines_valid = False
        self._syncing = False
        self._case_files_config = None
        self._parsed_roots: dict[str, FoamNode] = {}
        self._diff_case_dir: str | None = None
        self._diff_parsed_roots: dict[str, FoamNode] = {}

        self._build_ui()

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
        apply_btn = QPushButton(tr("Apply Text to Tree"))
        reload_btn = QPushButton(tr("Reload from Tree"))
        save_btn.clicked.connect(self.save_file)
        save_all_btn.clicked.connect(self.save_all_files)
        apply_btn.clicked.connect(self.apply_text_to_tree)
        reload_btn.clicked.connect(self.reload_text_from_tree)

        layout = QHBoxLayout()
        layout.setContentsMargins(4, 4, 4, 2)
        layout.addWidget(save_btn)
        layout.addWidget(save_all_btn)
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
        self.proxy_model.setSourceModel(self.current_model)
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

        from ui.boundary_view_panel import BoundaryViewPanel
        self.boundary_panel = BoundaryViewPanel()

        self.block_mesh_panel = None
        if _feat_blockmesh:
            from ui.block_mesh_panel import BlockMeshPanel
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

        # Allow all panes to shrink freely regardless of child minimum hints.
        tree_container.setMinimumSize(0, 0)
        self.tree.setMinimumSize(0, 0)
        self.comparison_panel.setMinimumSize(0, 0)
        self.detail_panel.setMinimumSize(0, 0)
        right_upper_splitter.setMinimumSize(0, 0)

        self.upper_tabs = QTabWidget()
        self.upper_tabs.addTab(right_upper_splitter, tr("Tree"))
        self.upper_tabs.addTab(self.boundary_panel, tr("Boundary"))
        if self.block_mesh_panel is not None:
            # When terminal is present, BlockMesh tab visibility depends on
            # whether xterm is active (xterm and VTK share the OpenGL context).
            # When there is no terminal, show BlockMesh unconditionally.
            show_bm = (self.terminal_panel is None) or (not self.terminal_panel.use_xterm)
            if show_bm:
                self.upper_tabs.addTab(self.block_mesh_panel, tr("BlockMesh"))
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

        help_menu = menubar.addMenu(tr("Help"))
        help_menu.addAction(tr("About Foam Dictionary Editor (FoDE)...")).triggered.connect(self.show_about)
        help_menu.addSeparator()
        help_menu.addAction(tr("Keyboard Shortcuts...")).triggered.connect(self.show_keyboard_shortcuts)
        help_menu.addAction(tr("Resources...")).triggered.connect(self.show_openfoam_resources)

    # ── window lifecycle ──────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        if not self._confirm_discard_if_needed():
            event.ignore()
            return
        if self.terminal_panel is not None:
            self.terminal_panel.cleanup()
        if self.block_mesh_panel is not None:
            self.block_mesh_panel.shutdown()
        cfg = get_app_config()
        cfg.set_window_size(self.width(), self.height())
        cfg.save()
        event.accept()

    # ── schema / help ─────────────────────────────────────────────────────────

    def _build_language_menu(self, parent_menu) -> None:
        lang_menu = parent_menu.addMenu(tr("Language"))
        group = QActionGroup(self)
        group.setExclusive(True)
        for code, name in available_languages():
            action = lang_menu.addAction(name)
            action.setCheckable(True)
            action.setChecked(code == get_language())
            action.setData(code)
            group.addAction(action)
        group.triggered.connect(self._on_language_changed)

    def _on_language_changed(self, action: QAction) -> None:
        code = action.data()
        cfg = get_app_config()
        cfg.set_language(code)
        cfg.save()
        QMessageBox.information(
            self,
            tr("Language Changed"),
            tr("The language will change after restarting the application."),
        )

    def open_schema_manager(self) -> None:
        from ui.schema_manager_dialog import SchemaManagerDialog

        SchemaManagerDialog(self).exec()

    def show_about(self) -> None:
        from ui.about_dialog import AboutDialog

        AboutDialog(self).exec()

    def show_keyboard_shortcuts(self) -> None:
        from ui.keyboard_shortcuts_dialog import KeyboardShortcutsDialog

        KeyboardShortcutsDialog(self).exec()

    def show_openfoam_resources(self) -> None:
        from ui.openfoam_resources_dialog import OpenFOAMResourcesDialog

        OpenFOAMResourcesDialog(self).exec()

    # ── buffer / tree state ───────────────────────────────────────────────────

    def _save_current_buffer(self) -> None:
        if self.current_file is None:
            return
        self.file_buffers[self.current_file] = self.editor_panel.get_text()
        self.file_dirty[self.current_file] = self.text_dirty
        self.file_list_panel.mark_dirty(self.current_file, self.text_dirty)

    def _after_model_edit(self) -> None:
        self.editor_panel.set_text(write_root(self.current_root))
        self._mark_dirty()
        if self.current_file:
            self.boundary_panel.update_field(self.current_file, self.current_root)
            if self.block_mesh_panel is not None and Path(self.current_file).name == _BLOCKMESH_DICT_NAME:
                self.block_mesh_panel.update_block_mesh(self.current_file, self.current_root)
        self._resize_tree_columns()
        self.on_tree_selection()
        self.statusBar().showMessage(tr("Tree changes applied to text editor"), _STATUS_SHORT)

    def _load_tree(self, root: FoamNode) -> None:
        self.current_root = root
        self.current_model = FoamTreeModel(root)
        self.current_model.edit_rejected.connect(
            lambda msg: self.statusBar().showMessage(msg, _STATUS_WARNING)
        )
        self.proxy_model.setSourceModel(self.current_model)
        self.tree_filter_input.clear()
        self.tree.expandToDepth(_TREE_EXPAND_DEPTH)
        self._collapse_foam_file()
        self._connect_tree_selection()
        self._resize_tree_columns()
        self._source_lines_valid = True
        self._update_sync_checkbox()
        self.editor_panel.clear_node_highlight()
        self._recompute_diff()

    def _clear_current_file(self) -> None:
        self.current_file = None
        self.text_dirty = False
        self.editor_panel.set_text("")
        self._load_tree(FoamNode(name="root", node_type="dictionary"))
        self._update_window_title()
        self._update_file_label()

    # ── dirty tracking ────────────────────────────────────────────────────────

    def _mark_dirty(self) -> None:
        self.text_dirty = True
        if self.current_file:
            self.file_dirty[self.current_file] = True
        self._update_window_title()
        self._update_file_label()
        if self.current_file:
            self.file_list_panel.mark_dirty(self.current_file, True)

    def _mark_path_dirty(self, path: str) -> None:
        self.file_dirty[path] = True
        self.file_list_panel.mark_dirty(path, True)
        if path == self.current_file:
            self.text_dirty = True
            self._update_window_title()
            self._update_file_label()

    def _confirm_discard_if_needed(self) -> bool:
        if not self.text_dirty:
            return True
        reply = QMessageBox.question(
            self,
            tr("Unsaved Changes"),
            tr("Text editor has unsaved changes. Discard them?"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return reply == QMessageBox.Yes

    # ── tree helpers ──────────────────────────────────────────────────────────

    def _connect_tree_selection(self) -> None:
        if self.tree.selectionModel() is not None:
            self.tree.selectionModel().selectionChanged.connect(self.on_tree_selection)

    def _current_primary_index(self):
        indexes = self.tree.selectedIndexes()
        proxy_idx = (
            self.proxy_model.index(indexes[0].row(), 0, indexes[0].parent())
            if indexes
            else self.tree.currentIndex()
        )
        return self.proxy_model.mapToSource(proxy_idx)

    def _to_source(self, proxy_index):
        return self.proxy_model.mapToSource(proxy_index)

    def _to_proxy(self, source_index):
        return self.proxy_model.mapFromSource(source_index)

    def _on_toggle_blockmesh_panel(self, checked: bool) -> None:
        if self.block_mesh_panel is None:
            return
        from PySide6.QtCore import QTimer
        if checked:
            idx = self.upper_tabs.indexOf(self.block_mesh_panel)
            if idx < 0:
                self.upper_tabs.addTab(self.block_mesh_panel, tr("BlockMesh"))
            QTimer.singleShot(0, self.block_mesh_panel._init_plotter)
        else:
            self.block_mesh_panel.shutdown()
            idx = self.upper_tabs.indexOf(self.block_mesh_panel)
            if idx >= 0:
                self.upper_tabs.removeTab(idx)

    def _on_toggle_type_column(self, checked: bool) -> None:
        self.tree.setColumnHidden(FoamTreeModel.COL_TYPE, not checked)
        if checked:
            self.tree.resizeColumnToContents(FoamTreeModel.COL_TYPE)
        self.comparison_panel.set_type_column_visible(checked)

    def _resize_tree_columns(self) -> None:
        for col in range(3):
            if not self.tree.isColumnHidden(col):
                self.tree.resizeColumnToContents(col)

    def _collapse_foam_file(self) -> None:
        for row in range(self.current_model.rowCount()):
            src_index = self.current_model.index(row, 0)
            node = src_index.internalPointer()
            if node is not None and node.name == "FoamFile":
                self.tree.setExpanded(self._to_proxy(src_index), False)
                break

    # ── label / title updates ─────────────────────────────────────────────────

    def _update_case_label(self) -> None:
        if self.current_case_dir:
            name = Path(self.current_case_dir).name or self.current_case_dir
            self.current_case_label.setText(name)
            self.current_case_label.setToolTip(self.current_case_dir)
        else:
            self.current_case_label.setText("-")
            self.current_case_label.setToolTip(tr("No case opened"))

    def _update_file_label(self) -> None:
        if self.current_file:
            dirty_mark = "*" if self.file_dirty.get(self.current_file, False) else ""
            self.current_file_label.setText(f"{display_file_name(self.current_file)}{dirty_mark}")
            self.current_file_label.setToolTip(self.current_file)
        else:
            self.current_file_label.setText("-")
            self.current_file_label.setToolTip(tr("No file loaded"))

    def _update_window_title(self) -> None:
        mark = "*" if self.text_dirty else ""
        self.setWindowTitle(f"{tr('foam dictionary editor')}{mark}")

    def _update_sync_checkbox(self) -> None:
        stale = self.current_file is not None and not self._source_lines_valid
        if stale:
            self.editor_autoscroll_checkbox.setText(tr("Auto-scroll editor (stale)"))
            self.editor_autoscroll_checkbox.setStyleSheet("color: gray;")
            self.editor_autoscroll_checkbox.setToolTip(
                tr(
                    "Source lines are stale — the editor text has changed since the last parse.\n"
                    "Apply Text to Tree to re-enable jump-to-line and span highlight."
                )
            )
        else:
            self.editor_autoscroll_checkbox.setText(tr("Auto-scroll editor"))
            self.editor_autoscroll_checkbox.setStyleSheet("")
            self.editor_autoscroll_checkbox.setToolTip(
                tr(
                    "When checked, the editor scrolls to the selected tree entry.\n"
                    "The span highlight is always shown regardless of this setting."
                )
            )

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
        self._side_by_side_cb.setChecked(True)
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

    def _on_side_by_side_toggled(self, checked: bool) -> None:
        if self.right_upper_splitter is None:
            return
        if checked:
            self.right_upper_splitter.setSizes(
                [SPLITTER_TREE_WIDTH // 2, SPLITTER_COMPARISON_WIDTH, SPLITTER_DETAIL_WIDTH]
            )
        else:
            self.right_upper_splitter.setSizes(
                [SPLITTER_TREE_WIDTH, 0, SPLITTER_DETAIL_WIDTH]
            )

    def _compare_with_case(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            tr("Select Reference Case Directory"),
            self.current_case_dir or "",
        )
        if not directory:
            return
        self._diff_case_dir = directory
        name = Path(directory).name or directory
        self._diff_path_label.setText(
            tr("Comparing with: <b>{name}</b>  ({directory})").format(name=name, directory=directory)
        )
        self._diff_path_label.setTextFormat(Qt.RichText)
        self._diff_bar.show()
        self._recompute_diff()
        QTimer.singleShot(0, self._precompute_all_diff_counts)
        self._side_by_side_cb.setChecked(True)

    def _clear_diff(self) -> None:
        self._diff_case_dir = None
        self._diff_parsed_roots.clear()
        self._diff_bar.hide()
        self.current_model.clear_diff()
        self.comparison_panel.clear()
        self.file_list_panel.clear_diff_marks()
        self.file_list_panel.set_diff_filter_enabled(False)
        if self.right_upper_splitter is not None:
            self.right_upper_splitter.setSizes(
                [SPLITTER_TREE_WIDTH, 0, SPLITTER_DETAIL_WIDTH]
            )
        self.statusBar().showMessage(tr("Diff cleared."), _STATUS_SHORT)

    def _recompute_diff(self) -> None:
        if not self._diff_case_dir or not self.current_file or not self.current_case_dir:
            return
        try:
            rel = Path(self.current_file).relative_to(Path(self.current_case_dir))
        except ValueError:
            return
        other_path = Path(self._diff_case_dir) / rel
        other_key = str(other_path)
        if other_key not in self._diff_parsed_roots:
            if not other_path.exists():
                self.current_model.clear_diff()
                self.comparison_panel.clear()
                self.statusBar().showMessage(
                    tr("Diff: {rel} not found in reference case.").format(rel=rel), _STATUS_SHORT
                )
                return
            try:
                self._diff_parsed_roots[other_key] = OpenFoamParser(
                    read_foam_file(other_key)
                ).parse()
            except Exception:
                self.current_model.clear_diff()
                self.comparison_panel.clear()
                return
        other_root = self._diff_parsed_roots[other_key]
        diff_map = diff_trees(self.current_root, other_root)
        rev_diff_map = diff_trees_reverse(other_root, self.current_root)
        self.current_model.set_diff(diff_map)
        case_name = Path(self._diff_case_dir).name or self._diff_case_dir
        self.comparison_panel.load(other_root, rev_diff_map, case_name)
        n = len(diff_map)
        self.file_list_panel.mark_diff(self.current_file, n)
        self.statusBar().showMessage(
            tr("Diff: {n} difference{s} in {rel}.").format(n=n, s="s" if n != 1 else "", rel=rel),
            _STATUS_SHORT,
        )

    def _precompute_all_diff_counts(self) -> None:
        if not self._diff_case_dir or not self.current_case_dir:
            return
        case_path = Path(self.current_case_dir)
        diff_path = Path(self._diff_case_dir)
        paths = [
            item.data(Qt.UserRole)
            for item in (
                self.file_list_panel._list.item(i)
                for i in range(self.file_list_panel._list.count())
            )
            if item.data(Qt.UserRole)
        ]
        self._precompute_diff_step(paths, 0, case_path, diff_path)

    def _precompute_diff_step(
        self, paths: list, idx: int, case_path: Path, diff_path: Path
    ) -> None:
        if not self._diff_case_dir:
            return
        if idx >= len(paths):
            self.file_list_panel.set_diff_filter_enabled(True)
            return
        path = paths[idx]
        advance = lambda: QTimer.singleShot(  # noqa: E731
            0, lambda: self._precompute_diff_step(paths, idx + 1, case_path, diff_path)
        )
        try:
            rel = Path(path).relative_to(case_path)
        except ValueError:
            advance()
            return
        other_path = diff_path / rel
        other_key = str(other_path)
        if other_key not in self._diff_parsed_roots:
            if not other_path.exists():
                self.file_list_panel.mark_diff(path, 0)
                advance()
                return
            if is_large_non_foam_file(str(other_path))[0]:
                advance()
                return
            try:
                self._diff_parsed_roots[other_key] = OpenFoamParser(
                    read_foam_file(other_key)
                ).parse()
            except Exception:
                advance()
                return
        other_root = self._diff_parsed_roots[other_key]
        if path == self.current_file:
            a_root = self.current_root
        elif path in self._parsed_roots:
            a_root = self._parsed_roots[path]
        else:
            if is_large_non_foam_file(path)[0]:
                advance()
                return
            try:
                a_root = OpenFoamParser(read_foam_file(path)).parse()
                self._parsed_roots[path] = a_root
            except Exception:
                advance()
                return
        d = diff_trees(a_root, other_root)
        self.file_list_panel.mark_diff(path, len(d))
        advance()

    # ── terminal mode switch ──────────────────────────────────────────────────

    def _on_terminal_mode_changed(self, use_xterm: bool) -> None:
        if self.block_mesh_panel is None:
            return
        from PySide6.QtCore import QTimer
        if use_xterm:
            # xterm needs GPU/Vulkan — shut down VTK first and hide the tab.
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
            # Simple terminal is GPU-free — restore BlockMesh tab if user wants it.
            if self._blockmesh_action is not None:
                self._blockmesh_action.setEnabled(True)
                self._blockmesh_action.setText(tr("BlockMesh 3-D Panel"))
            user_wants_bm = (
                self._blockmesh_action is None or self._blockmesh_action.isChecked()
            )
            if user_wants_bm:
                idx = self.upper_tabs.indexOf(self.block_mesh_panel)
                if idx < 0:
                    self.upper_tabs.addTab(self.block_mesh_panel, tr("BlockMesh"))
                # Brief delay lets the WebEngine GPU process finish cleaning up
                # before VTK claims the OpenGL context.
                QTimer.singleShot(300, self.block_mesh_panel._init_plotter)
