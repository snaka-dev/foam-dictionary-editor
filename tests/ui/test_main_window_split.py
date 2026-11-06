# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Structural tests for the main_window.py mixin split.

Verifies that each mixin module exists, exports its class, and owns the
methods assigned to it during the refactor.  No Qt event loop is required.
"""
from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MIXINS_DIR = REPO_ROOT / "ui" / "mixins"

# ── import guards ─────────────────────────────────────────────────────────────

# ── method ownership ──────────────────────────────────────────────────────────

CASE_OPS_METHODS = [
    "open_case",
    "reload_case",
    "duplicate_case",
    "open_from_library",
    "duplicate_from_library",
    "_duplicate_case_from",
    "_pick_case_from_library",
    "_confirm_and_remove_existing_dir",
    "_run_duplicate",
    "_confirm_open_dir",
    "_copy_visible_files",
    "save_as_new_case",
    "set_default_case_directory",
    "manage_case_library",
    "reset_window_size",
    "reset_all_settings",
]

MENU_BAR_OPS_METHODS = [
    "_build_menu_bar",
    "_build_case_menu",
    "_build_settings_menu",
    "_build_view_menu",
    "_build_tools_menu",
    "_build_help_menu",
]

CASE_NAV_OPS_METHODS = [
    "_on_open_case_browser",
    "_on_case_nav_open_requested",
    "_on_case_nav_compare_requested",
    "_on_case_nav_duplicate_requested",
    "_on_case_nav_move_requested",
    "_on_case_nav_rename_requested",
    "_on_case_nav_delete_requested",
    "_on_case_nav_new_folder_requested",
    "_protected_case_paths",
    "_refuse_case_nav",
    "_case_nav_relates_to_open_case",
    "_settle_open_case_for",
    "_trash_directory",
    "_run_case_nav_move",
    "_close_case",
]

FOAM_MONITOR_OPS_METHODS = [
    "_on_foam_monitor_clicked",
    "_stop_foam_monitor",
    "_on_foam_monitor_poll",
    "_update_foam_monitor_btn",
]

TOOLS_OPS_METHODS = [
    "_run_in_terminal",
    "_rerun_over_results_warning",
    "_run_tool_with_options",
    "_on_restore_0dir_clicked",
    "_on_run_blockmesh_clicked",
    "_on_run_snappyhexmesh_clicked",
    "_on_run_topo_set_clicked",
    "_on_run_setfields_clicked",
    "_on_run_checkmesh_clicked",
    "_on_run_decomposepar_clicked",
    "_solver_dialog_notes",
    "_parallel_setup",
    "_on_run_solver_clicked",
    "_refuse_while_running",
    "_on_run_reconstructpar_clicked",
    "_on_delete_processor_dirs_clicked",
    "_problem_lines",
    "_processor_delete_box",
    "_describe_deletion_problem",
    "_on_run_allrun_clicked",
    "_on_run_allclean_clicked",
    "_on_clean_case_clicked",
    "_show_cached_dialog",
    "_on_view_log_summary_clicked",
    "_on_find_examples_clicked",
    "_on_example_compare_requested",
    "_on_example_duplicate_requested",
    "_on_open_paraview_clicked",
    "_update_tools_actions",
]

FILE_OPS_METHODS = [
    "_load_case_dir",
    "_case_file_paths",
    "_case_relative",
    "_reload_file_list",
    "_on_case_dir_changed_on_disk",
    "_open_included_target",
    "_parse_and_update",
    "_include_notes_for",
    "load_selected_file",
    "save_file",
    "save_all_files",
    "reset_file_list",
    "_on_add_time_dir",
    "_on_remove_extra_dir",
    "_purge_file_caches",
    "_is_auto_scan_group",
]

FILE_MGMT_OPS_METHODS = [
    "_prompt_new_filename",
    "_on_create_file_requested",
    "_on_add_file_requested",
    "_read_only_refused",
    "_create_backup",
    "_on_backup_file_requested",
    "_on_manage_extra_files",
    "_on_viewer_kind_requested",
    "_on_remove_extra_file",
    "_on_delete_file_requested",
    "_on_duplicate_file_requested",
    "_on_copy_into_case_requested",
    "_resolved_include_for",
    "_on_duplicate_dir_requested",
    "_on_delete_dir_requested",
    "_on_clean_backups",
]

TREE_CRUD_OPS_METHODS = [
    "_setup_tree_copy_paste",
    "_resolve_tree_include",
    "_on_tree_double_clicked",
    "_on_tree_context_menu",
    "_build_tree_context_menu",
    "_tree_copy_value",
    "_tree_paste_value",
    "_tree_add_entry_after",
    "_edit_first_editable_column",
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
    "_highlight_selected_block",
    "_on_value_apply",
    "_on_field_value_apply",
    "apply_text_to_tree",
    "reload_text_from_tree",
    "_on_blockmesh_vertices_changed",
    "_on_blockmesh_image_saved",
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
    "_reset_diff_for_case_dir",
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
    "_build_pane_menu_actions",
    "set_pane_minimized",
    "toggle_pane_minimized",
    "_on_pane_action_toggled",
    "_on_toggle_bottom_pane_btn",
    "_on_splitter_handle_double_click",
    "_auto_minimize_detail_for_side_by_side",
    "_update_pane_minimize_controls",
]

UNDO_OPS_METHODS = [
    "_setup_tree_undo",
    "_on_model_about_to_change",
    "_commit_pending_undo",
    "_checkpoint_for_undo",
    "_end_undo_op",
    "_trim_undo_stack",
    "_undo_snapshot_of",
    "_clear_undo_stacks",
    "_tree_undo",
    "_tree_redo",
    "_undo_redo_step",
    "_restore_undo_snapshot",
    "_restored_dirty",
]


def test_case_ops_owns_its_methods():
    from ui.mixins._case_ops import _CaseOpsMixin
    missing = [m for m in CASE_OPS_METHODS if m not in _CaseOpsMixin.__dict__]
    assert missing == [], f"_CaseOpsMixin is missing {missing}"


def test_menu_bar_ops_owns_its_methods():
    from ui.mixins._menu_bar_ops import _MenuBarOpsMixin
    missing = [m for m in MENU_BAR_OPS_METHODS if m not in _MenuBarOpsMixin.__dict__]
    assert missing == [], f"_MenuBarOpsMixin is missing {missing}"


def test_case_nav_ops_owns_its_methods():
    from ui.mixins._case_nav_ops import _CaseNavOpsMixin
    missing = [m for m in CASE_NAV_OPS_METHODS if m not in _CaseNavOpsMixin.__dict__]
    assert missing == [], f"_CaseNavOpsMixin is missing {missing}"


def test_foam_monitor_ops_owns_its_methods():
    from ui.mixins._foam_monitor_ops import _FoamMonitorOpsMixin
    missing = [m for m in FOAM_MONITOR_OPS_METHODS if m not in _FoamMonitorOpsMixin.__dict__]
    assert missing == [], f"_FoamMonitorOpsMixin is missing {missing}"


def test_tools_ops_owns_its_methods():
    from ui.mixins._tools_ops import _ToolsOpsMixin
    missing = [m for m in TOOLS_OPS_METHODS if m not in _ToolsOpsMixin.__dict__]
    assert missing == [], f"_ToolsOpsMixin is missing {missing}"


def test_file_ops_owns_its_methods():
    from ui.mixins._file_ops import _FileOpsMixin
    missing = [m for m in FILE_OPS_METHODS if m not in _FileOpsMixin.__dict__]
    assert missing == [], f"_FileOpsMixin is missing {missing}"


def test_file_mgmt_ops_owns_its_methods():
    from ui.mixins._file_mgmt_ops import _FileManagementOpsMixin
    missing = [m for m in FILE_MGMT_OPS_METHODS if m not in _FileManagementOpsMixin.__dict__]
    assert missing == [], f"_FileManagementOpsMixin is missing {missing}"


def test_tree_crud_ops_owns_its_methods():
    from ui.mixins._tree_crud_ops import _TreeCrudOpsMixin
    missing = [m for m in TREE_CRUD_OPS_METHODS if m not in _TreeCrudOpsMixin.__dict__]
    assert missing == [], f"_TreeCrudOpsMixin is missing {missing}"


def test_tree_sync_ops_owns_its_methods():
    from ui.mixins._tree_sync_ops import _TreeSyncOpsMixin
    missing = [m for m in TREE_SYNC_OPS_METHODS if m not in _TreeSyncOpsMixin.__dict__]
    assert missing == [], f"_TreeSyncOpsMixin is missing {missing}"


def test_boundary_ops_owns_its_methods():
    from ui.mixins._boundary_ops import _BoundaryOpsMixin
    missing = [m for m in BOUNDARY_OPS_METHODS if m not in _BoundaryOpsMixin.__dict__]
    assert missing == [], f"_BoundaryOpsMixin is missing {missing}"


def test_diff_ops_owns_its_methods():
    from ui.mixins._diff_ops import _DiffOpsMixin
    missing = [m for m in DIFF_OPS_METHODS if m not in _DiffOpsMixin.__dict__]
    assert missing == [], f"_DiffOpsMixin is missing {missing}"


def test_panel_ops_owns_its_methods():
    from ui.mixins._panel_ops import _PanelOpsMixin
    missing = [m for m in PANEL_OPS_METHODS if m not in _PanelOpsMixin.__dict__]
    assert missing == [], f"_PanelOpsMixin is missing {missing}"


def test_undo_ops_owns_its_methods():
    from ui.mixins._undo_ops import _UndoOpsMixin
    missing = [m for m in UNDO_OPS_METHODS if m not in _UndoOpsMixin.__dict__]
    assert missing == [], f"_UndoOpsMixin is missing {missing}"


# ── no cross-mixin duplicates ─────────────────────────────────────────────────

def test_no_duplicate_methods_across_mixins():
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
        ("_UndoOpsMixin",           set(_UndoOpsMixin.__dict__)),
    ]
    mixins = [
        _CaseOpsMixin, _FileOpsMixin, _FileManagementOpsMixin,
        _TreeCrudOpsMixin, _TreeSyncOpsMixin, _BoundaryOpsMixin,
        _DiffOpsMixin, _PanelOpsMixin, _FoamMonitorOpsMixin,
        _ToolsOpsMixin, _ModelOpsMixin, _UiOpsMixin, _UndoOpsMixin,
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
    from ui.mixins._boundary_ops import _BoundaryOpsMixin
    from ui.mixins._case_nav_ops import _CaseNavOpsMixin
    from ui.mixins._case_ops import _CaseOpsMixin
    from ui.mixins._diff_ops import _DiffOpsMixin
    from ui.mixins._file_mgmt_ops import _FileManagementOpsMixin
    from ui.mixins._file_ops import _FileOpsMixin
    from ui.mixins._foam_monitor_ops import _FoamMonitorOpsMixin
    from ui.mixins._menu_bar_ops import _MenuBarOpsMixin
    from ui.mixins._model_ops import _ModelOpsMixin
    from ui.mixins._panel_ops import _PanelOpsMixin
    from ui.mixins._tools_ops import _ToolsOpsMixin
    from ui.mixins._tree_crud_ops import _TreeCrudOpsMixin
    from ui.mixins._tree_sync_ops import _TreeSyncOpsMixin
    from ui.mixins._ui_ops import _UiOpsMixin
    from ui.mixins._undo_ops import _UndoOpsMixin

    assert issubclass(MainWindow, _CaseOpsMixin)
    assert issubclass(MainWindow, _CaseNavOpsMixin)
    assert issubclass(MainWindow, _MenuBarOpsMixin)
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
    assert issubclass(MainWindow, _UndoOpsMixin)


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
    "_build_shared_actions",
    "_build_top_bar",
    "createPopupMenu",
    "_build_tree_area",
    "_build_feature_panels",
    "_build_splitters",
    "_connect_signals",
    "closeEvent",
    "_build_diff_bar",
]

MODEL_OPS_METHODS = [
    "_save_current_buffer",
    "_after_model_edit",
    "_update_viewer_panels",
    "_viewer_kind_for",
    "_update_block_mesh_viewer",
    "_expand_includes_for_viewer",
    "_refresh_include_dependents",
    "_on_tree_data_changed",
    "_load_tree",
    "_clear_current_file",
    "_write_root_to_buffer",
    "_cache_parsed_root",
    "_is_read_only",
    "_current_text",
    "_dirty_paths",
    "_mark_dirty",
    "_mark_path_dirty",
    "_confirm_discard_if_needed",
]

UI_OPS_METHODS = [
    "_error",
    "_confirm",
    "_build_radio_menu",
    "_build_language_menu",
    "_on_language_changed",
    "_build_appearance_menu",
    "_on_theme_changed",
    "_build_ui_scale_menu",
    "_on_ui_scale_changed",
    "_on_restore_session_toggled",
    "_refresh_forget_session_action",
    "_forget_saved_session",
    "open_schema_manager",
    "generate_foam_keywords",
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


def test_core_methods_stay_in_main_window():
    from ui.main_window import MainWindow
    missing = [m for m in CORE_METHODS if m not in MainWindow.__dict__]
    assert missing == [], f"MainWindow is missing core methods: {missing}"


def test_model_ops_owns_its_methods():
    from ui.mixins._model_ops import _ModelOpsMixin
    missing = [m for m in MODEL_OPS_METHODS if m not in _ModelOpsMixin.__dict__]
    assert missing == [], f"_ModelOpsMixin is missing {missing}"


def test_ui_ops_owns_its_methods():
    from ui.mixins._ui_ops import _UiOpsMixin
    missing = [m for m in UI_OPS_METHODS if m not in _UiOpsMixin.__dict__]
    assert missing == [], f"_UiOpsMixin is missing {missing}"


# ── AST-level structural guards ─────────────────────────────────────────────
#
# The two checks below parse source with `ast` rather than importing modules,
# so they need no Qt event loop (see the module docstring) and no PySide6
# import at all -- they inspect the *text* of ui/mixins/_*.py directly.


def _non_dunder_methods(class_node: ast.ClassDef) -> dict[str, int]:
    """Map a class body's method names to their positional parameter count.

    "Positional parameter count" includes ``self`` (and any ``/``-marked
    positional-only parameters), so a stub and its real method agree on
    arity iff this count matches between them. Dunder methods (``__init__``
    etc.) are skipped -- neither the protocol nor the hand-maintained
    ownership lists below track those.
    """
    methods: dict[str, int] = {}
    for item in class_node.body:
        if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if item.name.startswith("__") and item.name.endswith("__"):
            continue
        methods[item.name] = len(item.args.posonlyargs) + len(item.args.args)
    return methods


def _mixin_classes_by_file() -> dict[str, tuple[str, dict[str, int]]]:
    """Map each mixin file's repo-relative path to its (``*Mixin`` class name, methods).

    Excludes ``_protocol.py`` (the mypy-only stand-in, not a mixin itself)
    and ``__init__.py`` (not a mixin module at all).
    """
    result: dict[str, tuple[str, dict[str, int]]] = {}
    for path in sorted(MIXINS_DIR.glob("_*.py")):
        if path.name in ("_protocol.py", "__init__.py"):
            continue
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name.endswith("Mixin"):
                result[str(path.relative_to(REPO_ROOT))] = (node.name, _non_dunder_methods(node))
    return result


def _protocol_methods() -> dict[str, int]:
    """Method name -> arity for ``MainWindowProtocol`` in ui/mixins/_protocol.py."""
    path = MIXINS_DIR / "_protocol.py"
    tree = ast.parse(path.read_text(), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "MainWindowProtocol":
            return _non_dunder_methods(node)
    raise AssertionError("MainWindowProtocol class not found in ui/mixins/_protocol.py")


def test_every_mixin_method_is_declared_in_protocol():
    """Every method a mixin defines must have a matching stub in ``MainWindowProtocol``.

    ``ui/mixins/_protocol.py`` is mypy's stand-in for the combined
    ``MainWindow`` (see its module docstring and DEVELOPER.md's "Typing the
    ui/mixins/ split"): a mixin method missing there silently loses
    type-checking for every *other* mixin that calls it via ``self``. This
    check is static AST parsing, not import + reflection, because the
    protocol's stub bodies are never executed -- reflection would only prove
    the stub exists, not that mypy accepts its signature (that half is
    `test_mypy_clean` in tests/test_lint.py).
    """
    protocol_methods = _protocol_methods()
    for rel_path, (class_name, methods) in _mixin_classes_by_file().items():
        for name, arity in methods.items():
            assert name in protocol_methods, (
                f"{class_name} in {rel_path} defines {name!r}, which has no stub in "
                "MainWindowProtocol (ui/mixins/_protocol.py). Add one there, matching "
                "the real method's signature."
            )
            assert protocol_methods[name] == arity, (
                f"{class_name}.{name} in {rel_path} takes {arity} positional "
                f"parameter(s), but its MainWindowProtocol stub (ui/mixins/_protocol.py) "
                f"takes {protocol_methods[name]}. Fix the stub there to match the real "
                "method's signature."
            )


def test_all_mixin_methods_are_assigned_to_a_list():
    """The 15 hand-maintained ``*_METHODS`` lists must, together, name every
    method actually defined across the 15 mixin classes -- exactly.

    This deliberately stays a two-way equality check against the hand lists
    rather than regenerating them from the AST: the lists document which
    mixin owns which slice of ``MainWindow``'s surface, and an AST-derived
    list would make that documentation tautological. A mixin method missing
    from every list is undocumented ownership; a listed method that no
    longer exists is stale documentation -- this test catches both.

    ``CORE_METHODS`` is deliberately excluded: it is ``MainWindow``'s own
    method list, not a mixin's.
    """
    all_lists = {
        "CASE_OPS_METHODS": CASE_OPS_METHODS,
        "CASE_NAV_OPS_METHODS": CASE_NAV_OPS_METHODS,
        "MENU_BAR_OPS_METHODS": MENU_BAR_OPS_METHODS,
        "FOAM_MONITOR_OPS_METHODS": FOAM_MONITOR_OPS_METHODS,
        "TOOLS_OPS_METHODS": TOOLS_OPS_METHODS,
        "FILE_OPS_METHODS": FILE_OPS_METHODS,
        "FILE_MGMT_OPS_METHODS": FILE_MGMT_OPS_METHODS,
        "TREE_CRUD_OPS_METHODS": TREE_CRUD_OPS_METHODS,
        "TREE_SYNC_OPS_METHODS": TREE_SYNC_OPS_METHODS,
        "BOUNDARY_OPS_METHODS": BOUNDARY_OPS_METHODS,
        "DIFF_OPS_METHODS": DIFF_OPS_METHODS,
        "PANEL_OPS_METHODS": PANEL_OPS_METHODS,
        "UNDO_OPS_METHODS": UNDO_OPS_METHODS,
        "MODEL_OPS_METHODS": MODEL_OPS_METHODS,
        "UI_OPS_METHODS": UI_OPS_METHODS,
    }
    listed: dict[str, list[str]] = {}
    for list_name, methods in all_lists.items():
        for name in methods:
            listed.setdefault(name, []).append(list_name)

    actual: dict[str, str] = {}
    for rel_path, (class_name, methods) in _mixin_classes_by_file().items():
        for name in methods:
            actual[name] = f"{class_name} ({rel_path})"

    missing = sorted(set(actual) - set(listed))
    stale = sorted(set(listed) - set(actual))

    assert not missing, (
        "Methods defined on a mixin but not present in any *_METHODS list in "
        "tests/ui/test_main_window_split.py -- add each to the list for the "
        "mixin that defines it:\n"
        + "\n".join(f"  {name} -- defined on {actual[name]}" for name in missing)
    )
    assert not stale, (
        "Methods present in a *_METHODS list in tests/ui/test_main_window_split.py "
        "but no longer defined on any mixin -- remove the stale entry:\n"
        + "\n".join(f"  {name} -- listed in {', '.join(listed[name])}" for name in stale)
    )
