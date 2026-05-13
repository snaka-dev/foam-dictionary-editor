# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

_DIALOG_WIDTH = 520
_DIALOG_HEIGHT = 380


class ManageExtraFilesDialog(QDialog):
    def __init__(
        self,
        extra_files: list[str],
        extra_dirs: list[str] | None = None,
        case_dir: str | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Manage Extra Files & Directories")
        self.resize(_DIALOG_WIDTH, _DIALOG_HEIGHT)

        self._files = list(extra_files)
        self._dirs = list(extra_dirs or [])
        self._case_dir = case_dir
        self._removed_files: list[str] = []
        self._removed_dirs: list[str] = []
        self._added_dirs: list[str] = []

        tabs = QTabWidget()
        tabs.addTab(self._build_files_tab(), "Extra Files")
        tabs.addTab(self._build_dirs_tab(), "Extra Directories")

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)

        close_row = QHBoxLayout()
        close_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)

    # ── Files tab ─────────────────────────────────────────────────────────────

    def _build_files_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Extra files registered for this case:"))

        sel_row = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        deselect_all_btn = QPushButton("Deselect All")
        sel_row.addWidget(select_all_btn)
        sel_row.addWidget(deselect_all_btn)
        sel_row.addStretch()
        layout.addLayout(sel_row)

        self._files_list = QListWidget()
        self._rebuild_files_list()
        layout.addWidget(self._files_list)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._remove_files_btn = QPushButton()
        btn_row.addWidget(self._remove_files_btn)
        layout.addLayout(btn_row)

        self._update_remove_files_btn()

        self._files_list.itemChanged.connect(self._update_remove_files_btn)
        select_all_btn.clicked.connect(self._select_all_files)
        deselect_all_btn.clicked.connect(self._deselect_all_files)
        self._remove_files_btn.clicked.connect(self._remove_checked_files)

        return w

    def _rebuild_files_list(self) -> None:
        self._files_list.blockSignals(True)
        self._files_list.clear()
        for path in self._files:
            item = QListWidgetItem(path)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self._files_list.addItem(item)
        self._files_list.blockSignals(False)

    def _checked_file_items(self) -> list[QListWidgetItem]:
        return [
            self._files_list.item(i)
            for i in range(self._files_list.count())
            if self._files_list.item(i).checkState() == Qt.Checked
        ]

    def _update_remove_files_btn(self) -> None:
        n = len(self._checked_file_items())
        self._remove_files_btn.setText(f"Remove Selected ({n})")
        self._remove_files_btn.setEnabled(n > 0)

    def _select_all_files(self) -> None:
        self._files_list.blockSignals(True)
        for i in range(self._files_list.count()):
            self._files_list.item(i).setCheckState(Qt.Checked)
        self._files_list.blockSignals(False)
        self._update_remove_files_btn()

    def _deselect_all_files(self) -> None:
        self._files_list.blockSignals(True)
        for i in range(self._files_list.count()):
            self._files_list.item(i).setCheckState(Qt.Unchecked)
        self._files_list.blockSignals(False)
        self._update_remove_files_btn()

    def _remove_checked_files(self) -> None:
        checked = self._checked_file_items()
        if not checked:
            QMessageBox.warning(self, "No Selection", "Please select a file to remove.")
            return
        for item in checked:
            rel_path = item.text()
            self._removed_files.append(rel_path)
            self._files.remove(rel_path)
        self._rebuild_files_list()
        self._update_remove_files_btn()

    # ── Directories tab ───────────────────────────────────────────────────────

    def _build_dirs_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(
            QLabel("Directories scanned in full (all files loaded, like 0/):")
        )

        sel_row = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        deselect_all_btn = QPushButton("Deselect All")
        sel_row.addWidget(select_all_btn)
        sel_row.addWidget(deselect_all_btn)
        sel_row.addStretch()
        layout.addLayout(sel_row)

        self._dirs_list = QListWidget()
        self._rebuild_dirs_list()
        layout.addWidget(self._dirs_list)

        btn_row = QHBoxLayout()
        add_dir_btn = QPushButton("Add Directory…")
        btn_row.addWidget(add_dir_btn)
        btn_row.addStretch()
        self._remove_dirs_btn = QPushButton()
        btn_row.addWidget(self._remove_dirs_btn)
        layout.addLayout(btn_row)

        self._update_remove_dirs_btn()

        self._dirs_list.itemChanged.connect(self._update_remove_dirs_btn)
        select_all_btn.clicked.connect(self._select_all_dirs)
        deselect_all_btn.clicked.connect(self._deselect_all_dirs)
        add_dir_btn.clicked.connect(self._add_directory)
        self._remove_dirs_btn.clicked.connect(self._remove_checked_dirs)

        if not self._case_dir:
            add_dir_btn.setEnabled(False)
            add_dir_btn.setToolTip("No case directory open")

        return w

    def _rebuild_dirs_list(self) -> None:
        self._dirs_list.blockSignals(True)
        self._dirs_list.clear()
        for rel in self._dirs:
            item = QListWidgetItem(rel)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self._dirs_list.addItem(item)
        self._dirs_list.blockSignals(False)

    def _checked_dir_items(self) -> list[QListWidgetItem]:
        return [
            self._dirs_list.item(i)
            for i in range(self._dirs_list.count())
            if self._dirs_list.item(i).checkState() == Qt.Checked
        ]

    def _update_remove_dirs_btn(self) -> None:
        n = len(self._checked_dir_items())
        self._remove_dirs_btn.setText(f"Remove Selected ({n})")
        self._remove_dirs_btn.setEnabled(n > 0)

    def _select_all_dirs(self) -> None:
        self._dirs_list.blockSignals(True)
        for i in range(self._dirs_list.count()):
            self._dirs_list.item(i).setCheckState(Qt.Checked)
        self._dirs_list.blockSignals(False)
        self._update_remove_dirs_btn()

    def _deselect_all_dirs(self) -> None:
        self._dirs_list.blockSignals(True)
        for i in range(self._dirs_list.count()):
            self._dirs_list.item(i).setCheckState(Qt.Unchecked)
        self._dirs_list.blockSignals(False)
        self._update_remove_dirs_btn()

    def _add_directory(self) -> None:
        if not self._case_dir:
            return
        chosen = QFileDialog.getExistingDirectory(
            self,
            "Select Directory to Add",
            self._case_dir,
        )
        if not chosen:
            return
        try:
            rel = str(Path(chosen).relative_to(Path(self._case_dir)))
        except ValueError:
            QMessageBox.warning(
                self,
                "Invalid Directory",
                "Please select a directory inside the case folder.",
            )
            return
        if rel in self._dirs:
            QMessageBox.information(
                self, "Already Added", f"'{rel}' is already in the directory list."
            )
            return
        self._dirs.append(rel)
        self._added_dirs.append(rel)
        self._rebuild_dirs_list()
        self._update_remove_dirs_btn()

    def _remove_checked_dirs(self) -> None:
        checked = self._checked_dir_items()
        if not checked:
            QMessageBox.warning(
                self, "No Selection", "Please select a directory to remove."
            )
            return
        for item in checked:
            rel = item.text()
            self._removed_dirs.append(rel)
            self._dirs.remove(rel)
            self._added_dirs = [d for d in self._added_dirs if d != rel]
        self._rebuild_dirs_list()
        self._update_remove_dirs_btn()

    # ── result properties ─────────────────────────────────────────────────────

    @property
    def removed_files(self) -> list[str]:
        return list(self._removed_files)

    @property
    def removed_dirs(self) -> list[str]:
        return list(self._removed_dirs)

    @property
    def added_dirs(self) -> list[str]:
        return list(self._added_dirs)
