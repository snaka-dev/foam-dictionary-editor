# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from schemas import apply_schema_modules, get_schema_modules, save_current_config
from i18n import tr

_DIALOG_WIDTH = 600
_DIALOG_HEIGHT = 450


class SchemaManagerDialog(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(tr("Schema Module Manager"))
        self.resize(_DIALOG_WIDTH, _DIALOG_HEIGHT)

        self._modules = get_schema_modules()

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr("Currently loaded schema modules:")))

        self._list = QListWidget()
        self._list.addItems(self._modules)
        layout.addWidget(self._list)

        op_layout = QHBoxLayout()
        add_btn = QPushButton(tr("Add Module from File"))
        remove_btn = QPushButton(tr("Remove Selected"))
        op_layout.addWidget(add_btn)
        op_layout.addWidget(remove_btn)
        op_layout.addStretch()
        layout.addLayout(op_layout)

        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        cancel_btn = QPushButton(tr("Cancel"))
        save_btn = QPushButton(tr("Save & Close"))
        bottom_layout.addWidget(cancel_btn)
        bottom_layout.addWidget(save_btn)
        layout.addLayout(bottom_layout)

        add_btn.clicked.connect(self._add_module)
        remove_btn.clicked.connect(self._remove_module)
        save_btn.clicked.connect(self._save_and_close)
        cancel_btn.clicked.connect(self.reject)

    def _refresh_list(self) -> None:
        self._list.clear()
        self._list.addItems(self._modules)

    def _add_module(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("Select Schema Module File"),
            "schemas/",
            "Python Files (*.py);;All Files (*)",
        )
        if not file_path:
            return

        path = Path(file_path)
        module_name = _resolve_module_name(path)
        if module_name is None:
            QMessageBox.warning(
                self,
                "Invalid File",
                "Please select a file within the 'schemas' directory.",
            )
            return

        if module_name in self._modules:
            QMessageBox.information(
                self,
                "Already Added",
                f"Module '{module_name}' is already in the list.",
            )
            return

        self._modules.append(module_name)
        self._refresh_list()

    def _remove_module(self) -> None:
        item = self._list.currentItem()
        if item is None:
            QMessageBox.warning(self, "No Selection", "Please select a module to remove.")
            return

        module_name = item.text()
        reply = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Remove module '{module_name}' from the list?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self._modules.remove(module_name)
        self._refresh_list()

    def _save_and_close(self) -> None:
        apply_schema_modules(self._modules)
        save_current_config()
        QMessageBox.information(
            self,
            "Saved",
            "Configuration saved and schemas reloaded successfully!",
        )
        self.accept()


def _resolve_module_name(path: Path) -> str | None:
    try:
        rel_path = path.relative_to(Path.cwd())
        return str(rel_path.with_suffix("")).replace("/", ".")
    except ValueError:
        parts = path.parts
        if "schemas" not in parts:
            return None
        idx = parts.index("schemas")
        return ".".join(parts[idx:]).replace(".py", "")
