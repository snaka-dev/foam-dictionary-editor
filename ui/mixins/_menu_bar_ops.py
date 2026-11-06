# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""MainWindow's menu bar.

Split out of ui/main_window.py, which was 968 lines. This is a build-time concern only: the
six builders below run once from `_build_ui` and never again, and everything they wire is
either a shared QAction from `_build_shared_actions` or a slot the protocol declares.

The `tr()` literals stay here, in a `ui/` module, because tests/ui/test_translatable_strings.py
scans `ui/` and tests/test_i18n.py checks each literal against i18n/ja.py -- moving them to a
constants table elsewhere would take them out of both nets.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QAction, QKeySequence

from app_config import get_app_config
from i18n import tr

if TYPE_CHECKING:
    from ui.mixins._protocol import MainWindowProtocol as _Base
else:
    _Base = object


def _act(menu, label: str, shortcut: str, slot) -> None:
    action = menu.addAction(label)
    action.setShortcut(QKeySequence(shortcut))
    action.triggered.connect(slot)


class _MenuBarOpsMixin(_Base):
    """Builds the Case / Settings / View / Tools / Help menus."""

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
        # Open Case / Reload Case / Save File / Save Case: the same QAction
        # objects the top toolbar uses (see _build_shared_actions), so label,
        # tooltip, shortcut and enabled state stay in sync automatically.
        case_menu.addAction(self._open_case_action)
        case_menu.addAction(tr("Open from Case Library…")).triggered.connect(self.open_from_library)
        case_menu.addAction(self._reload_case_action)
        case_menu.addSeparator()
        case_menu.addAction(self._save_file_action)
        case_menu.addAction(self._save_case_action)
        case_menu.addAction(tr("Save as New Case…")).triggered.connect(self.save_as_new_case)
        case_menu.addSeparator()
        # Also on the bottom tab bar (see _build_tree_text_sync_bar).  Reload
        # from Tree deliberately has no shortcut: it overwrites the editor text,
        # discarding edits not yet applied, and any key near "Reload Case" would
        # invite exactly that mistake.
        _act(case_menu, tr("Apply Text to Tree"),     "Ctrl+Shift+A", self.apply_text_to_tree)
        case_menu.addAction(tr("Reload from Tree")).triggered.connect(self.reload_text_from_tree)
        case_menu.addSeparator()
        case_menu.addAction(tr("Duplicate Case…")).triggered.connect(self.duplicate_case)
        case_menu.addAction(tr("Duplicate from Case Library…")).triggered.connect(
            self.duplicate_from_library
        )
        case_menu.addAction(self._find_examples_action)
        case_menu.addAction(tr("Case Browser…")).triggered.connect(self._on_open_case_browser)
        case_menu.addSeparator()
        # File-list housekeeping, grouped: Clean Backup Files and Manage Extra
        # Files & Directories both moved here from Settings (they act on a
        # single open case, not on application-wide settings), and Reset File
        # List -- which only ever undoes what Manage Extra Files added -- joins
        # them rather than sitting alone.
        case_menu.addAction(tr("Clean Backup Files…")).triggered.connect(self._on_clean_backups)
        case_menu.addAction(tr("Manage Extra Files & Directories…")).triggered.connect(
            self._on_manage_extra_files
        )
        case_menu.addAction(tr("Reset File List")).triggered.connect(self.reset_file_list)
        case_menu.addSeparator()
        case_menu.addAction(tr("Compare with Case…")).triggered.connect(self._compare_with_case)
        case_menu.addSeparator()
        _act(case_menu, tr("Exit"),                   "Ctrl+Q",       self.close)

    def _build_settings_menu(self, menubar) -> None:
        settings_menu = menubar.addMenu(tr("Settings"))
        settings_menu.addAction(tr("Set Default Case Directory…")).triggered.connect(
            self.set_default_case_directory
        )
        settings_menu.addAction(tr("Manage Case Library…")).triggered.connect(self.manage_case_library)
        settings_menu.addSeparator()
        # Manage Extra Files & Directories, Reset File List, and Reset Window
        # Size moved out of here: they each act on one open case or one window,
        # not on application settings -- see _build_case_menu and
        # _build_view_menu.
        settings_menu.addAction(tr("Manage Schema Modules…")).triggered.connect(self.open_schema_manager)
        settings_menu.addAction(tr("Generate OpenFOAM Keywords…")).triggered.connect(
            self.generate_foam_keywords
        )
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
        # Joins the pane-toggle group rather than starting a new one: it too
        # is about the window's on-screen geometry, and it moved here from
        # Settings for the same reason the toggles above it live here.
        view_menu.addAction(tr("Reset Window Size")).triggered.connect(self.reset_window_size)

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
            # The panel's own QAction, not a second one: the toolbar button in
            # the panel and this menu item are the same object, so their label,
            # tooltip, shortcut and enabled state cannot drift. It is None when
            # pyvista is missing, since the panel never builds its controls then.
            if self.block_mesh_panel.save_image_action is not None:
                view_menu.addAction(self.block_mesh_panel.save_image_action)

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
        tools_menu.addSeparator()
        # Running the case itself, rather than preparing it.
        self._run_decomposepar_action = _tool_act(
            tr("Run decomposePar…"),
            tr(
                "Choose options and run decomposePar in the terminal panel to "
                "split the case for a parallel run (system/decomposeParDict)"
            ),
            self._on_run_decomposepar_clicked,
        )
        self._run_solver_action = _tool_act(
            tr("Run Solver…"),
            tr(
                "Run the solver named in system/controlDict (or another one) "
                "in the terminal panel, optionally in parallel"
            ),
            self._on_run_solver_clicked,
        )
        self._run_reconstructpar_action = _tool_act(
            tr("Run reconstructPar…"),
            tr(
                "Choose options and run reconstructPar in the terminal panel to "
                "merge a parallel run's processor* results back into the case"
            ),
            self._on_run_reconstructpar_clicked,
        )
        self._delete_processor_dirs_action = _tool_act(
            tr("Delete processor* Directories…"),
            tr(
                "Permanently delete the processor* directories, only after "
                "checking that everything in them also exists at the case root"
            ),
            self._on_delete_processor_dirs_clicked,
        )
        tools_menu.addSeparator()
        # A whole workflow, not one more per-utility action -- its own group.
        self._run_allrun_action = _tool_act(
            tr("Run Allrun Script"),
            tr(
                "Send './Allrun' to the terminal panel — runs the case's full "
                "workflow, including the solver"
            ),
            self._on_run_allrun_clicked,
        )
        tools_menu.addSeparator()
        # A viewer, not a run -- its own group too.
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
        # No ellipsis on any of these three: each only displays information,
        # it never asks for anything first.
        help_menu.addAction(tr("About Foam Dictionary Editor (FoDE)")).triggered.connect(self.show_about)
        help_menu.addSeparator()
        help_menu.addAction(tr("Keyboard Shortcuts")).triggered.connect(self.show_keyboard_shortcuts)
        help_menu.addAction(tr("Resources")).triggered.connect(self.show_openfoam_resources)
