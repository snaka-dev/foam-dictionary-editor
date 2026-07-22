# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Combo box + Browse… row listing discovered OpenFOAM installations.

Populates from services.example_search.discover_installations() with the
persisted ``openfoam_dir`` config key as the first extra root; Browse…
validates the chosen directory via installation_from_dir, persists it, and
inserts it at the top. Shared by FindExamplesDialog and
GenerateKeywordsDialog, which differ only in how they report "no
installations" and errors — hence the two signals instead of labels here.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QPushButton,
    QWidget,
)

from app_config import get_app_config
from i18n import tr
from services.example_search import (
    FoamInstallation,
    discover_installations,
    installation_from_dir,
)


class InstallationSelector(QWidget):
    """Installation picker row: discovered installs in a combo, plus Browse…."""

    installations_available = Signal(bool)  # after refresh() and a successful browse
    error = Signal(str)                     # translated message (invalid browsed dir)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        self._combo = QComboBox()
        row.addWidget(self._combo, 1)
        browse_btn = QPushButton(tr("Browse…"))
        browse_btn.clicked.connect(self._on_browse)
        row.addWidget(browse_btn)

    @property
    def combo(self) -> QComboBox:
        return self._combo

    def refresh(self) -> None:
        """(Re)populate the combo from discovered installations."""
        cfg = get_app_config()
        saved = cfg.get_openfoam_dir()
        extra_roots = [saved] if saved else []
        installations = discover_installations(extra_roots=extra_roots)
        self._combo.clear()
        for installation in installations:
            self._combo.addItem(installation.label, installation)
        self.installations_available.emit(bool(installations))

    def current_installation(self) -> FoamInstallation | None:
        data = self._combo.currentData()
        return data if isinstance(data, FoamInstallation) else None

    def current_root(self) -> Path | None:
        installation = self.current_installation()
        return installation.root if installation is not None else None

    def _on_browse(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, tr("Select OpenFOAM Installation Directory")
        )
        if not directory:
            return
        installation = installation_from_dir(Path(directory))
        if installation is None:
            self.error.emit(
                tr("Not an OpenFOAM directory (no tutorials/ or etc/caseDicts/).")
            )
            return
        cfg = get_app_config()
        cfg.set_openfoam_dir(directory)
        cfg.save()
        self._combo.insertItem(0, installation.label, installation)
        self._combo.setCurrentIndex(0)
        self.installations_available.emit(True)
