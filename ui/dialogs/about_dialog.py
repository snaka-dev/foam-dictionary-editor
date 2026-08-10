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

from _version import get_version
from i18n import tr
from ui.fonts import heading_font, small_font
from ui.label_fit import fit_wrapped_labels
from ui.theme import colors

_APP_NAME = "Foam Dictionary Editor (FoDE)"
_DESCRIPTION = (
    "A PySide6-based GUI editor for OpenFOAM dictionary files.\n"
    "Supports tree view and raw text editing."
)

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
        self.setWindowTitle(tr("About Foam Dictionary Editor (FoDE)"))
        self.setFixedWidth(_DIALOG_WIDTH)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ── app name ──────────────────────────────────────────────────────────
        name_label = QLabel(_APP_NAME)
        name_label.setFont(heading_font())
        name_label.setStyleSheet("font-weight: bold;")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)

        # ── version ───────────────────────────────────────────────────────────
        version_label = QLabel(tr("Version {v}").format(v=get_version()))
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        version_label.setFont(small_font())
        version_label.setStyleSheet(f"color: {colors().hint_text};")
        layout.addWidget(version_label)

        # ── description ───────────────────────────────────────────────────────
        desc_label = QLabel(_DESCRIPTION)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # ── license / copyright ───────────────────────────────────────────────
        license_label = QLabel(_LICENSE)
        license_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        license_label.setWordWrap(True)
        license_label.setFont(small_font())
        license_label.setStyleSheet(f"color: {colors().secondary_text};")
        layout.addWidget(license_label)

        # ── separator ─────────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep)

        # ── acknowledgements ──────────────────────────────────────────────────
        ack_label = QLabel(_ACKNOWLEDGEMENTS)
        ack_label.setWordWrap(True)
        ack_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ack_label.setFont(small_font())
        ack_label.setStyleSheet(f"color: {colors().secondary_text};")
        layout.addWidget(ack_label)

        # ── disclaimer ────────────────────────────────────────────────────────
        disclaimer_label = QLabel(DISCLAIMER)
        disclaimer_label.setWordWrap(True)
        disclaimer_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        # No size of its own: a disclaimer is the one thing here that should be
        # as readable as body text, which is what the application font is.
        disclaimer_label.setStyleSheet(
            f"color: {colors().secondary_text}; padding: 8px;"
            f"background: {colors().info_box_bg}; border: 1px solid {colors().info_box_border};"
            " border-radius: 4px;"
        )
        layout.addWidget(disclaimer_label)

        # ── close button ──────────────────────────────────────────────────────
        bottom = QHBoxLayout()
        bottom.addStretch()
        close_btn = QPushButton(tr("Close"))
        close_btn.setDefault(True)
        close_btn.clicked.connect(self.accept)
        bottom.addWidget(close_btn)
        layout.addLayout(bottom)

        self._labels_fitted = False

    def showEvent(self, event):
        """Give the wrapped labels their real heights, once.

        Only after the first layout pass does a label know its width, which is
        what its height depends on — see ui/label_fit.py. Once, because the
        dialog is resizable in height and re-fitting on every show would undo
        whatever size the user had left it at.
        """
        super().showEvent(event)
        if not self._labels_fitted:
            self._labels_fitted = True
            fit_wrapped_labels(self)
            # activate() first: the new minimum heights have to travel back up
            # through the layout before the dialog's own size hint reflects
            # them. Then resize() rather than adjustSize(), because the latter
            # clamps a window to two thirds of the screen height — which on a
            # small display is exactly where the text would be cut off again.
            self.layout().activate()
            self.resize(self.width(), self.sizeHint().height())
