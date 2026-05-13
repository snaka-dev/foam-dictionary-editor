# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
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
from foam.nodes import FoamNode
from foam.writer import write_root
from model.tree_model import FoamTreeModel
from ui._boundary_ops import _BoundaryOpsMixin
from ui._case_ops import _CaseOpsMixin
from ui._file_ops import _FileOpsMixin
from ui._tree_ops import _TreeOpsMixin
from ui.detail_panel import DetailPanel
from ui.editor_panel import EditorPanel
from ui.file_list_panel import FileListPanel, display_file_name
from ui.terminal_panel import TerminalPanel
from ui.layout_constants import (
    SPLITTER_DETAIL_WIDTH,
    SPLITTER_FILE_LIST_WIDTH,
    SPLITTER_HANDLE_WIDTH,
    SPLITTER_LOWER_HEIGHT,
    SPLITTER_TREE_WIDTH,
    SPLITTER_UPPER_HEIGHT,
    STATUS_SHORT as _STATUS_SHORT,
)

_TREE_EXPAND_DEPTH = 2


class MainWindow(_CaseOpsMixin, _FileOpsMixin, _TreeOpsMixin, _BoundaryOpsMixin, QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("foam dictionary editor")

        self.current_case_dir: str | None = None
        self.current_file: str | None = None
        self.current_root = FoamNode(name="root", node_type="dictionary")
        self.current_model = FoamTreeModel(self.current_root)

        self.file_buffers: dict[str, str] = {}
        self.file_dirty: dict[str, bool] = {}
        self.text_dirty = False
        self._case_files_config = None
        self._parsed_roots: dict[str, FoamNode] = {}

        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.setStatusBar(QStatusBar(self))

        self.file_list_panel = FileListPanel()
        self.detail_panel = DetailPanel()
        self.editor_panel = EditorPanel()

        self.tree = QTreeView()
        self.tree.setModel(self.current_model)
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setEditTriggers(QTreeView.DoubleClicked | QTreeView.EditKeyPressed)
        self.tree.setSelectionBehavior(QTreeView.SelectRows)

        self.current_case_label = QLabel("-")
        self.current_case_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.current_case_label.setToolTip("Current case name")

        self.current_file_label = QLabel("-")
        self.current_file_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.current_file_label.setToolTip("Current file name")

        save_btn = QPushButton("Save File")
        save_all_btn = QPushButton("Save All Files")
        apply_btn = QPushButton("Apply Text to Tree")
        reload_btn = QPushButton("Reload from Tree")

        save_btn.clicked.connect(self.save_file)
        save_all_btn.clicked.connect(self.save_all_files)
        apply_btn.clicked.connect(self.apply_text_to_tree)
        reload_btn.clicked.connect(self.reload_text_from_tree)

        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(4, 4, 4, 2)
        top_bar.addWidget(save_btn)
        top_bar.addWidget(save_all_btn)
        top_bar.addWidget(apply_btn)
        top_bar.addWidget(reload_btn)
        top_bar.addWidget(QLabel("Case:"))
        top_bar.addWidget(self.current_case_label)
        top_bar.addSpacing(16)
        top_bar.addWidget(QLabel("File:"))
        top_bar.addWidget(self.current_file_label)
        top_bar.addStretch(1)

        self.terminal_panel = TerminalPanel()

        self.bottom_tabs = QTabWidget()
        self.bottom_tabs.addTab(self.editor_panel, "Editor")
        self.bottom_tabs.addTab(self.terminal_panel, self.terminal_panel.tab_label)

        right_upper_splitter = QSplitter(Qt.Horizontal)
        right_upper_splitter.addWidget(self.tree)
        right_upper_splitter.addWidget(self.detail_panel)
        right_upper_splitter.setSizes([SPLITTER_TREE_WIDTH, SPLITTER_DETAIL_WIDTH])

        # Allow all panes to shrink freely regardless of child minimum hints.
        self.tree.setMinimumSize(0, 0)
        self.detail_panel.setMinimumSize(0, 0)
        right_upper_splitter.setMinimumSize(0, 0)

        from ui.boundary_view_panel import BoundaryViewPanel
        self.boundary_panel = BoundaryViewPanel()

        self.upper_tabs = QTabWidget()
        self.upper_tabs.addTab(right_upper_splitter, "Tree")
        self.upper_tabs.addTab(self.boundary_panel, "Boundary")
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
        layout.addWidget(self.main_splitter, 1)
        self.setCentralWidget(central)

        self.file_list_panel.file_selected.connect(self.load_selected_file)
        self.file_list_panel.create_file_requested.connect(self._on_create_file_requested)
        self.file_list_panel.add_file_requested.connect(self._on_add_file_requested)
        self.file_list_panel.backup_file_requested.connect(self._on_backup_file_requested)
        self.file_list_panel.manage_extra_files_requested.connect(self._on_manage_extra_files)
        self.file_list_panel.remove_extra_file_requested.connect(self._on_remove_extra_file)
        self.file_list_panel.duplicate_file_requested.connect(self._on_duplicate_file_requested)
        self.file_list_panel.duplicate_dir_requested.connect(self._on_duplicate_dir_requested)
        self.file_list_panel.delete_file_requested.connect(self._on_delete_file_requested)
        self.file_list_panel.save_file_requested.connect(self.save_file)
        self.file_list_panel.add_time_dir_requested.connect(self._on_add_time_dir)
        self.file_list_panel.remove_extra_dir_requested.connect(self._on_remove_extra_dir)
        self.boundary_panel.patch_edit_requested.connect(self._on_patch_edit_requested)
        self.boundary_panel.patch_create_requested.connect(self._on_patch_create_requested)
        self.boundary_panel.patch_delete_requested.connect(self._on_patch_delete_requested)
        self.boundary_panel.patch_paste_requested.connect(self._on_patch_paste_requested)
        self.boundary_panel.patch_delete_all_requested.connect(self._on_patch_delete_all_requested)
        self.boundary_panel.patch_add_all_requested.connect(self._on_patch_add_all_requested)
        self.detail_panel.value_apply_requested.connect(self._on_value_apply)
        self.detail_panel.field_value_apply_requested.connect(self._on_field_value_apply)
        self.editor_panel.user_text_changed.connect(self._on_user_text_changed)

        self._connect_tree_selection()
        self._setup_tree_copy_paste()
        self.tree.setColumnHidden(FoamTreeModel.COL_TYPE, True)
        self.detail_panel.show_empty()
        self._update_case_label()
        self._update_file_label()

        menubar = self.menuBar()

        case_menu = menubar.addMenu("Case")
        case_menu.addAction("Open Case\tCtrl+O").triggered.connect(self.open_case)
        case_menu.addAction("Open from Case Library...").triggered.connect(self.open_from_library)
        case_menu.addSeparator()
        case_menu.addAction("Save Case\tCtrl+Shift+S").triggered.connect(self.save_all_files)
        case_menu.addAction("Save as New Case...").triggered.connect(self.save_as_new_case)
        case_menu.addSeparator()
        case_menu.addAction("Duplicate Case...").triggered.connect(self.duplicate_case)
        case_menu.addAction("Duplicate from Case Library...").triggered.connect(self.duplicate_from_library)
        case_menu.addSeparator()
        case_menu.addAction("Clean Backup Files...").triggered.connect(self._on_clean_backups)
        case_menu.addSeparator()
        case_menu.addAction("Exit\tCtrl+Q").triggered.connect(self.close)

        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(self.open_case)
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self.save_file)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self).activated.connect(self.save_all_files)
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self.close)

        settings_menu = menubar.addMenu("Settings")
        settings_menu.addAction("Set Default Case Directory").triggered.connect(self.set_default_case_directory)
        settings_menu.addAction("Manage Case Library…").triggered.connect(self.manage_case_library)
        settings_menu.addAction("Manage Extra Files & Directories…").triggered.connect(self._on_manage_extra_files)
        settings_menu.addAction("Reset File List").triggered.connect(self.reset_file_list)
        settings_menu.addSeparator()
        settings_menu.addAction("Manage Schema Modules").triggered.connect(self.open_schema_manager)
        settings_menu.addAction("Reset Window Size").triggered.connect(self.reset_window_size)
        settings_menu.addSeparator()
        settings_menu.addAction("Reset All Settings…").triggered.connect(self.reset_all_settings)

        view_menu = menubar.addMenu("View")
        self._show_type_action = QAction("Show Type Column", self)
        self._show_type_action.setCheckable(True)
        self._show_type_action.setChecked(False)
        self._show_type_action.toggled.connect(self._on_toggle_type_column)
        view_menu.addAction(self._show_type_action)

        help_menu = menubar.addMenu("Help")
        help_menu.addAction("About Foam Dictionary Editor (FoDE)...").triggered.connect(self.show_about)
        help_menu.addSeparator()
        help_menu.addAction("Resources...").triggered.connect(self.show_openfoam_resources)

    # ── window lifecycle ──────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        if not self._confirm_discard_if_needed():
            event.ignore()
            return
        cfg = get_app_config()
        cfg.set_window_size(self.width(), self.height())
        cfg.save()
        event.accept()

    # ── schema / help ─────────────────────────────────────────────────────────

    def open_schema_manager(self) -> None:
        from ui.schema_manager_dialog import SchemaManagerDialog

        SchemaManagerDialog(self).exec()

    def show_about(self) -> None:
        from ui.about_dialog import AboutDialog

        AboutDialog(self).exec()

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
        self._resize_tree_columns()
        self.on_tree_selection()
        self.statusBar().showMessage("Tree changes applied to text editor", _STATUS_SHORT)

    def _load_tree(self, root: FoamNode) -> None:
        self.current_root = root
        self.current_model = FoamTreeModel(root)
        self.tree.setModel(self.current_model)
        self.tree.expandToDepth(_TREE_EXPAND_DEPTH)
        self._collapse_foam_file()
        self._connect_tree_selection()
        self._resize_tree_columns()

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
            "Unsaved Changes",
            "Text editor has unsaved changes. Discard them?",
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
        if not indexes:
            return self.tree.currentIndex()
        return self.current_model.index(indexes[0].row(), 0, indexes[0].parent())

    def _on_toggle_type_column(self, checked: bool) -> None:
        self.tree.setColumnHidden(FoamTreeModel.COL_TYPE, not checked)
        if checked:
            self.tree.resizeColumnToContents(FoamTreeModel.COL_TYPE)

    def _resize_tree_columns(self) -> None:
        for col in range(3):
            if not self.tree.isColumnHidden(col):
                self.tree.resizeColumnToContents(col)

    def _collapse_foam_file(self) -> None:
        for row in range(self.current_model.rowCount()):
            index = self.current_model.index(row, 0)
            node = index.internalPointer()
            if node is not None and node.name == "FoamFile":
                self.tree.setExpanded(index, False)
                break

    # ── label / title updates ─────────────────────────────────────────────────

    def _update_case_label(self) -> None:
        if self.current_case_dir:
            name = Path(self.current_case_dir).name or self.current_case_dir
            self.current_case_label.setText(name)
            self.current_case_label.setToolTip(self.current_case_dir)
        else:
            self.current_case_label.setText("-")
            self.current_case_label.setToolTip("No case opened")

    def _update_file_label(self) -> None:
        if self.current_file:
            dirty_mark = "*" if self.file_dirty.get(self.current_file, False) else ""
            self.current_file_label.setText(f"{display_file_name(self.current_file)}{dirty_mark}")
            self.current_file_label.setToolTip(self.current_file)
        else:
            self.current_file_label.setText("-")
            self.current_file_label.setToolTip("No file loaded")

    def _update_window_title(self) -> None:
        mark = "*" if self.text_dirty else ""
        self.setWindowTitle(f"foam dictionary editor{mark}")
