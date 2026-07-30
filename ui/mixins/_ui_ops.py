# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMessageBox

from app_config import get_app_config
from i18n import available_languages, get_language, tr
from model.tree_model import FoamTreeModel
from ui.dialogs.about_dialog import AboutDialog
from ui.dialogs.generate_keywords_dialog import GenerateKeywordsDialog
from ui.dialogs.keyboard_shortcuts_dialog import KeyboardShortcutsDialog
from ui.dialogs.openfoam_resources_dialog import OpenFOAMResourcesDialog
from ui.dialogs.schema_manager_dialog import SchemaManagerDialog
from ui.panels.file_list_panel import display_file_name
from ui.theme import colors

if TYPE_CHECKING:
    from ui.mixins._protocol import MainWindowProtocol as _Base
else:
    _Base = object


class _UiOpsMixin(_Base):
    """Tree view helpers, label/title updates, and auxiliary dialog launchers."""

    # ── shared dialogs ────────────────────────────────────────────────────────

    def _confirm(self, title: str, message: str) -> bool:
        """Show a Yes/No confirmation dialog defaulting to No."""
        reply = QMessageBox.question(
            self, title, message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    # ── help dialogs ──────────────────────────────────────────────────────────

    def _build_radio_menu(self, parent_menu, title, options, current, slot) -> None:
        """Build a checkable QActionGroup radio-menu under *parent_menu*.

        *options* is an iterable of (value, label) pairs; the action whose
        value equals *current* starts checked. Shared by the Language and
        Appearance settings submenus.
        """
        menu = parent_menu.addMenu(title)
        group = QActionGroup(self)
        group.setExclusive(True)
        for value, label in options:
            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(value == current)
            action.setData(value)
            group.addAction(action)
        group.triggered.connect(slot)

    def _build_language_menu(self, parent_menu) -> None:
        self._build_radio_menu(
            parent_menu, tr("Language"), available_languages(), get_language(),
            self._on_language_changed,
        )

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

    def _build_appearance_menu(self, parent_menu) -> None:
        self._build_radio_menu(
            parent_menu,
            tr("Appearance"),
            (
                ("system", tr("Follow System")),
                ("light", tr("Light")),
                ("dark", tr("Dark")),
            ),
            get_app_config().get_theme(),
            self._on_theme_changed,
        )

    def _on_theme_changed(self, action: QAction) -> None:
        mode = action.data()
        cfg = get_app_config()
        if mode == cfg.get_theme():
            return
        cfg.set_theme(mode)
        cfg.save()
        # Panel stylesheets and item colours are baked in at widget construction,
        # so a live switch would leave the window half-themed. Restart instead —
        # same contract as the language setting.
        QMessageBox.information(
            self,
            tr("Appearance Changed"),
            tr("The theme will change after restarting the application."),
        )

    def open_schema_manager(self) -> None:
        SchemaManagerDialog(self).exec()

    def generate_foam_keywords(self) -> None:
        dlg = GenerateKeywordsDialog(self)
        dlg.exec()
        self.editor_panel.reload_highlighting()

    def show_about(self) -> None:
        AboutDialog(self).exec()

    def show_keyboard_shortcuts(self) -> None:
        KeyboardShortcutsDialog(self).exec()

    def show_openfoam_resources(self) -> None:
        OpenFOAMResourcesDialog(self).exec()

    # ── tree view helpers ─────────────────────────────────────────────────────

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
        for row in range(self.state.current_model.rowCount()):
            src_index = self.state.current_model.index(row, 0)
            node = src_index.internalPointer()
            if node is not None and node.name == "FoamFile":
                self.tree.setExpanded(self._to_proxy(src_index), False)
                break

    # ── label / title updates ─────────────────────────────────────────────────

    def _update_case_label(self) -> None:
        if self.state.current_case_dir:
            name = Path(self.state.current_case_dir).name or self.state.current_case_dir
            self.current_case_label.setText(name)
            self.current_case_label.setToolTip(self.state.current_case_dir)
        else:
            self.current_case_label.setText("-")
            self.current_case_label.setToolTip(tr("No case opened"))
        self._update_foam_monitor_btn()
        self._update_tools_actions()

    def _update_file_label(self) -> None:
        if self.state.current_file:
            dirty_mark = "*" if self.state.file_dirty.get(self.state.current_file, False) else ""
            self.current_file_label.setText(f"{display_file_name(self.state.current_file)}{dirty_mark}")
            self.current_file_label.setToolTip(self.state.current_file)
        else:
            self.current_file_label.setText("-")
            self.current_file_label.setToolTip(tr("No file loaded"))

    def _update_window_title(self) -> None:
        mark = "*" if self.state.text_dirty else ""
        self.setWindowTitle(f"{tr('foam dictionary editor')}{mark}")

    def _update_sync_checkbox(self) -> None:
        stale = self.state.current_file is not None and not self.state.source_lines_valid
        if stale:
            self.editor_autoscroll_checkbox.setText(tr("Auto-scroll editor (stale)"))
            self.editor_autoscroll_checkbox.setStyleSheet(f"color: {colors().hint_text};")
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
