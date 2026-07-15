# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Structural tests for the main_window.py mixin split.

Verifies that each mixin module exists, exports its class, and owns the
methods assigned to it during the refactor.  No Qt event loop is required.
"""
from __future__ import annotations

import inspect

import pytest


# ── import guards ─────────────────────────────────────────────────────────────

def test_case_ops_importable():
    from ui.mixins._case_ops import _CaseOpsMixin  # noqa: F401


def test_foam_monitor_ops_importable():
    from ui.mixins._foam_monitor_ops import _FoamMonitorOpsMixin  # noqa: F401


def test_tools_ops_importable():
    from ui.mixins._tools_ops import _ToolsOpsMixin  # noqa: F401


def test_file_ops_importable():
    from ui.mixins._file_ops import _FileOpsMixin  # noqa: F401


def test_file_mgmt_ops_importable():
    from ui.mixins._file_mgmt_ops import _FileManagementOpsMixin  # noqa: F401


def test_tree_crud_ops_importable():
    from ui.mixins._tree_crud_ops import _TreeCrudOpsMixin  # noqa: F401


def test_tree_sync_ops_importable():
    from ui.mixins._tree_sync_ops import _TreeSyncOpsMixin  # noqa: F401


def test_boundary_ops_importable():
    from ui.mixins._boundary_ops import _BoundaryOpsMixin  # noqa: F401


def test_diff_ops_importable():
    from ui.mixins._diff_ops import _DiffOpsMixin  # noqa: F401


def test_panel_ops_importable():
    from ui.mixins._panel_ops import _PanelOpsMixin  # noqa: F401


def test_model_ops_importable():
    from ui.mixins._model_ops import _ModelOpsMixin  # noqa: F401


def test_ui_ops_importable():
    from ui.mixins._ui_ops import _UiOpsMixin  # noqa: F401


# ── method ownership ──────────────────────────────────────────────────────────

CASE_OPS_METHODS = [
    "open_case",
    "reload_case",
    "duplicate_case",
    "open_from_library",
    "duplicate_from_library",
    "_pick_case_from_library",
    "_run_duplicate",
    "_confirm_open_dir",
    "_copy_visible_files",
    "save_as_new_case",
    "set_default_case_directory",
    "manage_case_library",
    "reset_window_size",
    "reset_all_settings",
]

FOAM_MONITOR_OPS_METHODS = [
    "_on_foam_monitor_clicked",
    "_stop_foam_monitor",
    "_on_foam_monitor_poll",
    "_update_foam_monitor_btn",
    "_patched_foam_monitor",
]

TOOLS_OPS_METHODS = [
    "_on_restore_0dir_clicked",
    "_on_run_blockmesh_clicked",
    "_on_run_snappyhexmesh_clicked",
    "_on_run_topo_set_clicked",
    "_on_run_setfields_clicked",
    "_on_run_checkmesh_clicked",
    "_on_run_allrun_clicked",
    "_on_run_allclean_clicked",
    "_on_clean_case_clicked",
    "_on_open_paraview_clicked",
    "_on_find_examples_clicked",
    "_on_example_compare_requested",
    "_update_tools_actions",
]

FILE_OPS_METHODS = [
    "_load_case_dir",
    "_reload_file_list",
    "_on_case_dir_changed_on_disk",
    "_parse_and_update",
    "load_selected_file",
    "save_file",
    "save_all_files",
    "reset_file_list",
]

FILE_MGMT_OPS_METHODS = [
    "_on_create_file_requested",
    "_on_add_file_requested",
    "_create_backup",
    "_on_backup_file_requested",
    "_on_manage_extra_files",
    "_on_remove_extra_file",
    "_on_delete_file_requested",
    "_on_duplicate_file_requested",
    "_on_duplicate_dir_requested",
    "_on_delete_dir_requested",
    "_on_clean_backups",
]

TREE_CRUD_OPS_METHODS = [
    "_setup_tree_copy_paste",
    "_on_tree_context_menu",
    "_tree_copy_value",
    "_tree_paste_value",
    "_tree_add_entry_after",
    "_tree_add_child_entry",
    "_tree_duplicate",
    "_tree_comment_out",
    "_tree_delete",
    "_tree_restore_comment",
    "_apply_comparison_value",
    "_node_indent",
    "_mark_parent_modified",
    "_is_commented_out_node",
]

TREE_SYNC_OPS_METHODS = [
    "_sync_tree_to_editor_line",
    "_find_deepest",
    "on_tree_selection",
    "_on_value_apply",
    "_on_field_value_apply",
    "apply_text_to_tree",
    "reload_text_from_tree",
    "_on_blockmesh_vertices_changed",
    "_on_user_text_changed",
]

BOUNDARY_OPS_METHODS = [
    "_available_field_dirs",
    "_reload_boundary_panel",
    "_on_patch_edit_requested",
    "_on_patch_create_requested",
    "_on_patch_paste_requested",
    "_on_patch_delete_requested",
    "_on_patch_delete_all_requested",
    "_on_patch_add_all_requested",
    "_on_rename_boundary_by_name",
    "_on_patch_selected",
    "_apply_boundary_root_change",
]

DIFF_OPS_METHODS = [
    "_on_side_by_side_toggled",
    "_compare_with_case",
    "_start_comparison_with",
    "_clear_diff",
    "_recompute_diff",
    "_precompute_all_diff_counts",
    "_precompute_diff_step",
]

PANEL_OPS_METHODS = [
    "_on_toggle_blockmesh_panel",
    "_on_toggle_bm_side_by_side",
    "_update_bm_side_by_side_btn",
    "_on_terminal_mode_changed",
]


@pytest.mark.parametrize("method", CASE_OPS_METHODS)
def test_case_ops_owns_method(method):
    from ui.mixins._case_ops import _CaseOpsMixin
    assert method in _CaseOpsMixin.__dict__, f"_CaseOpsMixin missing {method}"


@pytest.mark.parametrize("method", FOAM_MONITOR_OPS_METHODS)
def test_foam_monitor_ops_owns_method(method):
    from ui.mixins._foam_monitor_ops import _FoamMonitorOpsMixin
    assert method in _FoamMonitorOpsMixin.__dict__, f"_FoamMonitorOpsMixin missing {method}"


@pytest.mark.parametrize("method", TOOLS_OPS_METHODS)
def test_tools_ops_owns_method(method):
    from ui.mixins._tools_ops import _ToolsOpsMixin
    assert method in _ToolsOpsMixin.__dict__, f"_ToolsOpsMixin missing {method}"


@pytest.mark.parametrize("method", FILE_OPS_METHODS)
def test_file_ops_owns_method(method):
    from ui.mixins._file_ops import _FileOpsMixin
    assert method in _FileOpsMixin.__dict__, f"_FileOpsMixin missing {method}"


@pytest.mark.parametrize("method", FILE_MGMT_OPS_METHODS)
def test_file_mgmt_ops_owns_method(method):
    from ui.mixins._file_mgmt_ops import _FileManagementOpsMixin
    assert method in _FileManagementOpsMixin.__dict__, f"_FileManagementOpsMixin missing {method}"


@pytest.mark.parametrize("method", TREE_CRUD_OPS_METHODS)
def test_tree_crud_ops_owns_method(method):
    from ui.mixins._tree_crud_ops import _TreeCrudOpsMixin
    assert method in _TreeCrudOpsMixin.__dict__, f"_TreeCrudOpsMixin missing {method}"


@pytest.mark.parametrize("method", TREE_SYNC_OPS_METHODS)
def test_tree_sync_ops_owns_method(method):
    from ui.mixins._tree_sync_ops import _TreeSyncOpsMixin
    assert method in _TreeSyncOpsMixin.__dict__, f"_TreeSyncOpsMixin missing {method}"


@pytest.mark.parametrize("method", BOUNDARY_OPS_METHODS)
def test_boundary_ops_owns_method(method):
    from ui.mixins._boundary_ops import _BoundaryOpsMixin
    assert method in _BoundaryOpsMixin.__dict__, f"_BoundaryOpsMixin missing {method}"


@pytest.mark.parametrize("method", DIFF_OPS_METHODS)
def test_diff_ops_owns_method(method):
    from ui.mixins._diff_ops import _DiffOpsMixin
    assert method in _DiffOpsMixin.__dict__, f"_DiffOpsMixin missing {method}"


@pytest.mark.parametrize("method", PANEL_OPS_METHODS)
def test_panel_ops_owns_method(method):
    from ui.mixins._panel_ops import _PanelOpsMixin
    assert method in _PanelOpsMixin.__dict__, f"_PanelOpsMixin missing {method}"


# ── no cross-mixin duplicates ─────────────────────────────────────────────────

def test_no_duplicate_methods_across_mixins():
    from ui.mixins._case_ops import _CaseOpsMixin
    from ui.mixins._file_ops import _FileOpsMixin
    from ui.mixins._file_mgmt_ops import _FileManagementOpsMixin
    from ui.mixins._tree_crud_ops import _TreeCrudOpsMixin
    from ui.mixins._tree_sync_ops import _TreeSyncOpsMixin
    from ui.mixins._boundary_ops import _BoundaryOpsMixin
    from ui.mixins._diff_ops import _DiffOpsMixin
    from ui.mixins._panel_ops import _PanelOpsMixin
    from ui.mixins._foam_monitor_ops import _FoamMonitorOpsMixin
    from ui.mixins._tools_ops import _ToolsOpsMixin
    from ui.mixins._model_ops import _ModelOpsMixin
    from ui.mixins._ui_ops import _UiOpsMixin

    all_groups = [
        ("_CaseOpsMixin",           set(_CaseOpsMixin.__dict__)),
        ("_FileOpsMixin",           set(_FileOpsMixin.__dict__)),
        ("_FileManagementOpsMixin", set(_FileManagementOpsMixin.__dict__)),
        ("_TreeCrudOpsMixin",       set(_TreeCrudOpsMixin.__dict__)),
        ("_TreeSyncOpsMixin",       set(_TreeSyncOpsMixin.__dict__)),
        ("_BoundaryOpsMixin",       set(_BoundaryOpsMixin.__dict__)),
        ("_DiffOpsMixin",           set(_DiffOpsMixin.__dict__)),
        ("_PanelOpsMixin",          set(_PanelOpsMixin.__dict__)),
        ("_FoamMonitorOpsMixin",    set(_FoamMonitorOpsMixin.__dict__)),
        ("_ToolsOpsMixin",          set(_ToolsOpsMixin.__dict__)),
        ("_ModelOpsMixin",          set(_ModelOpsMixin.__dict__)),
        ("_UiOpsMixin",             set(_UiOpsMixin.__dict__)),
    ]
    mixins = [
        _CaseOpsMixin, _FileOpsMixin, _FileManagementOpsMixin,
        _TreeCrudOpsMixin, _TreeSyncOpsMixin, _BoundaryOpsMixin,
        _DiffOpsMixin, _PanelOpsMixin, _FoamMonitorOpsMixin,
        _ToolsOpsMixin, _ModelOpsMixin, _UiOpsMixin,
    ]
    method_groups = [
        (name, {k for k in methods if not k.startswith("__") and callable(getattr(m, k, None))})
        for (name, methods), m in zip(all_groups, mixins)
    ]

    seen: dict[str, str] = {}
    duplicates: list[str] = []
    for cls_name, methods in method_groups:
        for m in methods:
            if m in seen:
                duplicates.append(f"{m}: {seen[m]} and {cls_name}")
            else:
                seen[m] = cls_name

    assert not duplicates, "Duplicate methods found across mixins:\n" + "\n".join(duplicates)


# ── MainWindow MRO ────────────────────────────────────────────────────────────

def test_main_window_inherits_all_mixins(qapp):
    from ui.main_window import MainWindow
    from ui.mixins._case_ops import _CaseOpsMixin
    from ui.mixins._file_ops import _FileOpsMixin
    from ui.mixins._file_mgmt_ops import _FileManagementOpsMixin
    from ui.mixins._tree_crud_ops import _TreeCrudOpsMixin
    from ui.mixins._tree_sync_ops import _TreeSyncOpsMixin
    from ui.mixins._boundary_ops import _BoundaryOpsMixin
    from ui.mixins._diff_ops import _DiffOpsMixin
    from ui.mixins._panel_ops import _PanelOpsMixin
    from ui.mixins._foam_monitor_ops import _FoamMonitorOpsMixin
    from ui.mixins._tools_ops import _ToolsOpsMixin
    from ui.mixins._model_ops import _ModelOpsMixin
    from ui.mixins._ui_ops import _UiOpsMixin

    assert issubclass(MainWindow, _CaseOpsMixin)
    assert issubclass(MainWindow, _FileOpsMixin)
    assert issubclass(MainWindow, _FileManagementOpsMixin)
    assert issubclass(MainWindow, _TreeCrudOpsMixin)
    assert issubclass(MainWindow, _TreeSyncOpsMixin)
    assert issubclass(MainWindow, _BoundaryOpsMixin)
    assert issubclass(MainWindow, _DiffOpsMixin)
    assert issubclass(MainWindow, _PanelOpsMixin)
    assert issubclass(MainWindow, _FoamMonitorOpsMixin)
    assert issubclass(MainWindow, _ToolsOpsMixin)
    assert issubclass(MainWindow, _ModelOpsMixin)
    assert issubclass(MainWindow, _UiOpsMixin)


def test_main_window_mixins_before_qmainwindow(qapp):
    from PySide6.QtWidgets import QMainWindow
    from ui.main_window import MainWindow
    from ui.mixins._case_ops import _CaseOpsMixin

    mro = MainWindow.__mro__
    assert mro.index(_CaseOpsMixin) < mro.index(QMainWindow)


# ── core methods remain in MainWindow ─────────────────────────────────────────

CORE_METHODS = [
    "__init__",
    "_build_ui",
    "_build_top_bar",
    "_build_tree_area",
    "_build_feature_panels",
    "_build_splitters",
    "_connect_signals",
    "_build_menu_bar",
    "closeEvent",
    "_build_diff_bar",
]

MODEL_OPS_METHODS = [
    "_save_current_buffer",
    "_after_model_edit",
    "_update_viewer_panels",
    "_load_tree",
    "_clear_current_file",
    "_write_root_to_buffer",
    "_cache_parsed_root",
    "_mark_dirty",
    "_mark_path_dirty",
    "_confirm_discard_if_needed",
]

UI_OPS_METHODS = [
    "_confirm",
    "_build_language_menu",
    "_on_language_changed",
    "open_schema_manager",
    "show_about",
    "show_keyboard_shortcuts",
    "show_openfoam_resources",
    "_connect_tree_selection",
    "_current_primary_index",
    "_to_source",
    "_to_proxy",
    "_on_toggle_type_column",
    "_resize_tree_columns",
    "_collapse_foam_file",
    "_update_case_label",
    "_update_file_label",
    "_update_window_title",
    "_update_sync_checkbox",
]


@pytest.mark.parametrize("method", CORE_METHODS)
def test_core_method_in_main_window(method):
    from ui.main_window import MainWindow
    assert method in MainWindow.__dict__, f"MainWindow missing core method: {method}"


@pytest.mark.parametrize("method", MODEL_OPS_METHODS)
def test_model_ops_owns_method(method):
    from ui.mixins._model_ops import _ModelOpsMixin
    assert method in _ModelOpsMixin.__dict__, f"_ModelOpsMixin missing {method}"


@pytest.mark.parametrize("method", UI_OPS_METHODS)
def test_ui_ops_owns_method(method):
    from ui.mixins._ui_ops import _UiOpsMixin
    assert method in _UiOpsMixin.__dict__, f"_UiOpsMixin missing {method}"
