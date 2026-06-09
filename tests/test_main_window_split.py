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
    from ui._case_ops import _CaseOpsMixin  # noqa: F401


def test_file_ops_importable():
    from ui._file_ops import _FileOpsMixin  # noqa: F401


def test_tree_ops_importable():
    from ui._tree_ops import _TreeOpsMixin  # noqa: F401


def test_boundary_ops_importable():
    from ui._boundary_ops import _BoundaryOpsMixin  # noqa: F401


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

FILE_OPS_METHODS = [
    "_load_case_dir",
    "_reload_file_list",
    "_parse_and_update",
    "load_selected_file",
    "save_file",
    "save_all_files",
    "reset_file_list",
    "_on_create_file_requested",
    "_on_add_file_requested",
    "_create_backup",
    "_on_backup_file_requested",
    "_on_manage_extra_files",
    "_on_remove_extra_file",
    "_on_delete_file_requested",
    "_on_delete_dir_requested",
    "_on_duplicate_file_requested",
    "_on_duplicate_dir_requested",
    "_on_clean_backups",
]

TREE_OPS_METHODS = [
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
    "_node_indent",
    "_mark_parent_modified",
    "_is_commented_out_node",
    "_sync_tree_to_editor_line",
    "_find_deepest",
    "on_tree_selection",
    "_on_value_apply",
    "_on_field_value_apply",
    "apply_text_to_tree",
    "reload_text_from_tree",
    "_on_user_text_changed",
    "_on_blockmesh_vertices_changed",
    "_apply_comparison_value",
]

BOUNDARY_OPS_METHODS = [
    "_available_field_dirs",
    "_cache_parsed_root",
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


@pytest.mark.parametrize("method", CASE_OPS_METHODS)
def test_case_ops_owns_method(method):
    from ui._case_ops import _CaseOpsMixin
    assert method in _CaseOpsMixin.__dict__, f"_CaseOpsMixin missing {method}"


@pytest.mark.parametrize("method", FILE_OPS_METHODS)
def test_file_ops_owns_method(method):
    from ui._file_ops import _FileOpsMixin
    assert method in _FileOpsMixin.__dict__, f"_FileOpsMixin missing {method}"


@pytest.mark.parametrize("method", TREE_OPS_METHODS)
def test_tree_ops_owns_method(method):
    from ui._tree_ops import _TreeOpsMixin
    assert method in _TreeOpsMixin.__dict__, f"_TreeOpsMixin missing {method}"


@pytest.mark.parametrize("method", BOUNDARY_OPS_METHODS)
def test_boundary_ops_owns_method(method):
    from ui._boundary_ops import _BoundaryOpsMixin
    assert method in _BoundaryOpsMixin.__dict__, f"_BoundaryOpsMixin missing {method}"


# ── no cross-mixin duplicates ─────────────────────────────────────────────────

def test_no_duplicate_methods_across_mixins():
    from ui._case_ops import _CaseOpsMixin
    from ui._file_ops import _FileOpsMixin
    from ui._tree_ops import _TreeOpsMixin
    from ui._boundary_ops import _BoundaryOpsMixin

    all_groups = [
        ("_CaseOpsMixin", set(_CaseOpsMixin.__dict__)),
        ("_FileOpsMixin", set(_FileOpsMixin.__dict__)),
        ("_TreeOpsMixin", set(_TreeOpsMixin.__dict__)),
        ("_BoundaryOpsMixin", set(_BoundaryOpsMixin.__dict__)),
    ]
    # Only check callables (methods), skip dunder and class-level attrs
    method_groups = [
        (name, {k for k in methods if not k.startswith("__") and callable(getattr(m, k, None))})
        for (name, methods), m in zip(
            all_groups,
            [_CaseOpsMixin, _FileOpsMixin, _TreeOpsMixin, _BoundaryOpsMixin],
        )
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
    from ui._case_ops import _CaseOpsMixin
    from ui._file_ops import _FileOpsMixin
    from ui._tree_ops import _TreeOpsMixin
    from ui._boundary_ops import _BoundaryOpsMixin

    assert issubclass(MainWindow, _CaseOpsMixin)
    assert issubclass(MainWindow, _FileOpsMixin)
    assert issubclass(MainWindow, _TreeOpsMixin)
    assert issubclass(MainWindow, _BoundaryOpsMixin)


def test_main_window_mixins_before_qmainwindow(qapp):
    from PySide6.QtWidgets import QMainWindow
    from ui.main_window import MainWindow
    from ui._case_ops import _CaseOpsMixin

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
    "_save_current_buffer",
    "_after_model_edit",
    "_load_tree",
    "_clear_current_file",
    "_mark_dirty",
    "_mark_path_dirty",
    "_confirm_discard_if_needed",
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
    "closeEvent",
    "open_schema_manager",
    "show_about",
    "show_keyboard_shortcuts",
    "show_openfoam_resources",
    "_build_diff_bar",
    "_compare_with_case",
    "_clear_diff",
    "_recompute_diff",
    "_precompute_all_diff_counts",
    "_on_side_by_side_toggled",
    "_on_terminal_mode_changed",
    "_on_toggle_blockmesh_panel",
    "_on_foam_monitor_clicked",
    "_stop_foam_monitor",
    "_on_foam_monitor_poll",
    "_update_foam_monitor_btn",
    "_patched_foam_monitor",
]


@pytest.mark.parametrize("method", CORE_METHODS)
def test_core_method_in_main_window(method):
    from ui.main_window import MainWindow
    assert method in MainWindow.__dict__, f"MainWindow missing core method: {method}"
