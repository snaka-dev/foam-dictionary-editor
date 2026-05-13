# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import webbrowser

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app_config import get_app_config
from ui.about_dialog import DISCLAIMER

_DIALOG_WIDTH = 540

_FOUNDATION_DESC = (
    "Free, open-source CFD toolbox maintained by the OpenFOAM Foundation. "
    "Releases follow integer version numbers (v11, v12, v13 …)."
)
_OPENCFD_DESC = (
    "Developed and distributed by OpenCFD Ltd (ESI Group, Keysight). "
    "Releases follow date-based version numbers (v2412, v2506 …)."
)

_FOUNDATION_LINKS = [
    ("https://openfoam.org/", "openfoam.org"),
    ("https://cfd.direct/openfoam/user-guide/", "User Guide"),
]
_OPENCFD_LINKS = [
    ("https://www.openfoam.com/", "openfoam.com"),
    ("https://www.openfoam.com/documentation/", "Documentation"),
]


def _link_label(url: str, text: str) -> QLabel:
    label = QLabel(f'<a href="{url}">{text}</a>')
    label.setOpenExternalLinks(True)
    return label


def _make_resource_group(title: str, description: str, links: list[tuple[str, str]]) -> QGroupBox:
    box = QGroupBox(title)
    layout = QVBoxLayout(box)

    desc = QLabel(description)
    desc.setWordWrap(True)
    layout.addWidget(desc)

    link_row = QHBoxLayout()
    for url, text in links:
        link_row.addWidget(_link_label(url, text))
    link_row.addStretch()
    layout.addLayout(link_row)

    return box


# ── Add/Edit link dialog ───────────────────────────────────────────────────────

class _LinkEditDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, label: str = "", url: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Link")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Label:"))
        self._label_edit = QLineEdit(label)
        layout.addWidget(self._label_edit)

        layout.addWidget(QLabel("URL:"))
        self._url_edit = QLineEdit(url)
        self._url_edit.setPlaceholderText("https://")
        layout.addWidget(self._url_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        if not self._url_edit.text().strip():
            QMessageBox.warning(self, "Missing URL", "Please enter a URL.")
            return
        self.accept()

    def result_label(self) -> str:
        return self._label_edit.text().strip()

    def result_url(self) -> str:
        return self._url_edit.text().strip()


# ── My Links tab ──────────────────────────────────────────────────────────────

class _MyLinksTab(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._dirty = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        hint = QLabel("Double-click a link to open it in your browser.")
        hint.setStyleSheet("color: #666;")
        layout.addWidget(hint)

        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._open_link)
        layout.addWidget(self._list)

        btn_row = QHBoxLayout()
        self._add_btn = QPushButton("Add")
        self._edit_btn = QPushButton("Edit")
        self._remove_btn = QPushButton("Remove")
        self._up_btn = QPushButton("Move Up")
        self._down_btn = QPushButton("Move Down")

        for btn in (self._add_btn, self._edit_btn, self._remove_btn):
            btn_row.addWidget(btn)
        btn_row.addStretch()
        btn_row.addWidget(self._up_btn)
        btn_row.addWidget(self._down_btn)
        layout.addLayout(btn_row)

        self._add_btn.clicked.connect(self._add)
        self._edit_btn.clicked.connect(self._edit)
        self._remove_btn.clicked.connect(self._remove)
        self._up_btn.clicked.connect(self._move_up)
        self._down_btn.clicked.connect(self._move_down)
        self._list.currentRowChanged.connect(self._update_buttons)

        self._load()
        self._update_buttons()

    def _load(self) -> None:
        self._list.clear()
        for link in get_app_config().get_user_links():
            self._append_item(link["label"], link["url"])

    def _append_item(self, label: str, url: str) -> QListWidgetItem:
        display = label if label else url
        item = QListWidgetItem(display)
        item.setToolTip(url)
        item.setData(Qt.UserRole, {"label": label, "url": url})
        self._list.addItem(item)
        return item

    def _collect_links(self) -> list[dict]:
        return [self._list.item(i).data(Qt.UserRole) for i in range(self._list.count())]

    def save_if_dirty(self) -> None:
        if not self._dirty:
            return
        cfg = get_app_config()
        cfg.set_user_links(self._collect_links())
        cfg.save()
        self._dirty = False

    def _open_link(self, item: QListWidgetItem) -> None:
        url = item.data(Qt.UserRole)["url"]
        QDesktopServices.openUrl(QUrl(url))

    def _add(self) -> None:
        dlg = _LinkEditDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        item = self._append_item(dlg.result_label(), dlg.result_url())
        self._list.setCurrentItem(item)
        self._dirty = True
        self._update_buttons()

    def _edit(self) -> None:
        row = self._list.currentRow()
        if row < 0:
            return
        item = self._list.item(row)
        data = item.data(Qt.UserRole)
        dlg = _LinkEditDialog(self, label=data["label"], url=data["url"])
        if dlg.exec() != QDialog.Accepted:
            return
        new_label = dlg.result_label()
        new_url = dlg.result_url()
        item.setText(new_label if new_label else new_url)
        item.setToolTip(new_url)
        item.setData(Qt.UserRole, {"label": new_label, "url": new_url})
        self._dirty = True

    def _remove(self) -> None:
        row = self._list.currentRow()
        if row < 0:
            return
        self._list.takeItem(row)
        self._dirty = True
        self._update_buttons()

    def _move_up(self) -> None:
        row = self._list.currentRow()
        if row <= 0:
            return
        item = self._list.takeItem(row)
        self._list.insertItem(row - 1, item)
        self._list.setCurrentRow(row - 1)
        self._dirty = True

    def _move_down(self) -> None:
        row = self._list.currentRow()
        if row < 0 or row >= self._list.count() - 1:
            return
        item = self._list.takeItem(row)
        self._list.insertItem(row + 1, item)
        self._list.setCurrentRow(row + 1)
        self._dirty = True

    def _update_buttons(self) -> None:
        row = self._list.currentRow()
        count = self._list.count()
        has = row >= 0
        self._edit_btn.setEnabled(has)
        self._remove_btn.setEnabled(has)
        self._up_btn.setEnabled(has and row > 0)
        self._down_btn.setEnabled(has and row < count - 1)


# ── Main dialog ───────────────────────────────────────────────────────────────

class OpenFOAMResourcesDialog(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Resources")
        self.setFixedWidth(_DIALOG_WIDTH)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        tabs.addTab(self._make_openfoam_tab(), "OpenFOAM")

        self._my_links_tab = _MyLinksTab()
        tabs.addTab(self._my_links_tab, "My Links")

        bottom = QHBoxLayout()
        bottom.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setDefault(True)
        close_btn.clicked.connect(self.accept)
        bottom.addWidget(close_btn)
        layout.addLayout(bottom)

    def _make_openfoam_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        intro = QLabel(
            "OpenFOAM has two main distributions maintained by separate organizations. "
            "This application is not affiliated with either."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        layout.addWidget(_make_resource_group(
            "OpenCFD / ESI Group  (openfoam.com)",
            _OPENCFD_DESC,
            _OPENCFD_LINKS,
        ))
        layout.addWidget(_make_resource_group(
            "OpenFOAM Foundation  (openfoam.org)",
            _FOUNDATION_DESC,
            _FOUNDATION_LINKS,
        ))

        disclaimer_label = QLabel(DISCLAIMER)
        disclaimer_label.setWordWrap(True)
        disclaimer_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        disclaimer_label.setStyleSheet(
            "color: #555555; font-size: 13px; padding: 8px;"
            "background: #f8f8f8; border: 1px solid #dddddd; border-radius: 4px;"
        )
        layout.addWidget(disclaimer_label)
        layout.addStretch()

        return tab

    def closeEvent(self, event) -> None:
        self._my_links_tab.save_if_dirty()
        super().closeEvent(event)

    def accept(self) -> None:
        self._my_links_tab.save_if_dirty()
        super().accept()
