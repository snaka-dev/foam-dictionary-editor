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

from services.case_files_config import DirEntry

_DIALOG_WIDTH = 520
_DIALOG_HEIGHT = 380


class ManageExtraFilesDialog(QDialog):
    def __init__(
        self,
        extra_files: list[str],
        extra_dirs: list[DirEntry] | None = None,
        case_dir: str | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Manage Extra Files & Directories")
        self.resize(_DIALOG_WIDTH, _DIALOG_HEIGHT)

        self._files = list(extra_files)
        self._dirs: list[DirEntry] = list(extra_dirs or [])
        self._case_dir = case_dir
        self._removed_files: list[str] = []

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

    @staticmethod
    def _set_all_check_states(widget: QListWidget, state: Qt.CheckState) -> None:
        widget.blockSignals(True)
        for i in range(widget.count()):
            widget.item(i).setCheckState(state)
        widget.blockSignals(False)

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
        self._set_all_check_states(self._files_list, Qt.Checked)
        self._update_remove_files_btn()

    def _deselect_all_files(self) -> None:
        self._set_all_check_states(self._files_list, Qt.Unchecked)
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
            QLabel(
                "Directories scanned in full (all files loaded, like 0/).\n"
                "Check items and click Toggle Recursive to enable/disable recursive scan."
            )
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
        self._toggle_recursive_btn = QPushButton("Toggle Recursive")
        btn_row.addWidget(self._toggle_recursive_btn)
        btn_row.addStretch()
        self._remove_dirs_btn = QPushButton()
        btn_row.addWidget(self._remove_dirs_btn)
        layout.addLayout(btn_row)

        self._update_dirs_btns()

        self._dirs_list.itemChanged.connect(self._update_dirs_btns)
        select_all_btn.clicked.connect(self._select_all_dirs)
        deselect_all_btn.clicked.connect(self._deselect_all_dirs)
        add_dir_btn.clicked.connect(self._add_directory)
        self._toggle_recursive_btn.clicked.connect(self._toggle_recursive_dirs)
        self._remove_dirs_btn.clicked.connect(self._remove_checked_dirs)

        if not self._case_dir:
            add_dir_btn.setEnabled(False)
            add_dir_btn.setToolTip("No case directory open")

        return w

    def _rebuild_dirs_list(self) -> None:
        self._dirs_list.blockSignals(True)
        self._dirs_list.clear()
        for path, recursive in self._dirs:
            label = f"{path}  [recursive]" if recursive else path
            item = QListWidgetItem(label)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setData(Qt.UserRole, path)
            self._dirs_list.addItem(item)
        self._dirs_list.blockSignals(False)

    def _checked_dir_paths(self) -> list[str]:
        return [
            self._dirs_list.item(i).data(Qt.UserRole)
            for i in range(self._dirs_list.count())
            if self._dirs_list.item(i).checkState() == Qt.Checked
        ]

    def _update_dirs_btns(self) -> None:
        n = len(self._checked_dir_paths())
        self._remove_dirs_btn.setText(f"Remove Selected ({n})")
        self._remove_dirs_btn.setEnabled(n > 0)
        self._toggle_recursive_btn.setEnabled(n > 0)

    def _select_all_dirs(self) -> None:
        self._set_all_check_states(self._dirs_list, Qt.Checked)
        self._update_dirs_btns()

    def _deselect_all_dirs(self) -> None:
        self._set_all_check_states(self._dirs_list, Qt.Unchecked)
        self._update_dirs_btns()

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
        if any(p == rel for p, _ in self._dirs):
            QMessageBox.information(
                self, "Already Added", f"'{rel}' is already in the directory list."
            )
            return
        self._dirs.append((rel, False))
        self._rebuild_dirs_list()
        self._update_dirs_btns()

    def _toggle_recursive_dirs(self) -> None:
        checked = set(self._checked_dir_paths())
        if not checked:
            return
        self._dirs = [
            (p, (not r) if p in checked else r)
            for p, r in self._dirs
        ]
        self._rebuild_dirs_list()
        self._update_dirs_btns()

    def _remove_checked_dirs(self) -> None:
        checked = set(self._checked_dir_paths())
        if not checked:
            QMessageBox.warning(
                self, "No Selection", "Please select a directory to remove."
            )
            return
        self._dirs = [(p, r) for p, r in self._dirs if p not in checked]
        self._rebuild_dirs_list()
        self._update_dirs_btns()

    # ── result properties ─────────────────────────────────────────────────────

    @property
    def removed_files(self) -> list[str]:
        return list(self._removed_files)

    @property
    def result_dirs(self) -> list[DirEntry]:
        return list(self._dirs)
