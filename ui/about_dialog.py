# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

_APP_NAME = "Foam Dictionary Editor (FoDE)"
_DESCRIPTION = "A PySide6-based GUI editor for OpenFOAM dictionary files.\nSupports tree view and raw text editing."

_LICENSE = (
    "Copyright © 2025-2026 Shinji NAKAGAWA\n"
    "Released under the GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later)."
)

_ACKNOWLEDGEMENTS = (
    "Built with PySide6 (Qt for Python, LGPL v3), "
    "pyVista / VTK (BSD-3-Clause), "
    "and xterm.js (MIT), loaded automatically on first launch.\n\n"
    "Special thanks to the OpenFOAM Foundation and OpenCFD / ESI Group "
    "and all contributors for developing and maintaining OpenFOAM "
    "as free, open-source CFD software."
)

DISCLAIMER = (
    "This application is not approved or endorsed by OpenCFD Limited, "
    "producer and distributor of the OpenFOAM software via www.openfoam.com, "
    "and owner of the OPENFOAM® and OpenCFD® trade marks.\n\n"
    "OPENFOAM® is a registered trade mark of OpenCFD Limited."
)

_DIALOG_WIDTH = 480


class AboutDialog(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("About Foam Dictionary Editor (FoDE)")
        self.setFixedWidth(_DIALOG_WIDTH)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ── app name ──────────────────────────────────────────────────────────
        name_label = QLabel(_APP_NAME)
        name_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(name_label)

        # ── description ───────────────────────────────────────────────────────
        desc_label = QLabel(_DESCRIPTION)
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # ── license / copyright ───────────────────────────────────────────────
        license_label = QLabel(_LICENSE)
        license_label.setAlignment(Qt.AlignCenter)
        license_label.setWordWrap(True)
        license_label.setStyleSheet("color: #555555; font-size: 12px;")
        layout.addWidget(license_label)

        # ── separator ─────────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep)

        # ── acknowledgements ──────────────────────────────────────────────────
        ack_label = QLabel(_ACKNOWLEDGEMENTS)
        ack_label.setWordWrap(True)
        ack_label.setAlignment(Qt.AlignCenter)
        ack_label.setStyleSheet("color: #555555; font-size: 12px;")
        layout.addWidget(ack_label)

        # ── disclaimer ────────────────────────────────────────────────────────
        disclaimer_label = QLabel(DISCLAIMER)
        disclaimer_label.setWordWrap(True)
        disclaimer_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        disclaimer_label.setStyleSheet(
            "color: #555555; font-size: 13px; padding: 8px;"
            "background: #f8f8f8; border: 1px solid #dddddd; border-radius: 4px;"
        )
        layout.addWidget(disclaimer_label)

        # ── close button ──────────────────────────────────────────────────────
        bottom = QHBoxLayout()
        bottom.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setDefault(True)
        close_btn.clicked.connect(self.accept)
        bottom.addWidget(close_btn)
        layout.addLayout(bottom)
