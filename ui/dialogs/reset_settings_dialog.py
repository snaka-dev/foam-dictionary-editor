# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app_config import get_app_config
from app_config.defaults import DEFAULT_WINDOW_HEIGHT, DEFAULT_WINDOW_WIDTH
from i18n import tr
from ui.theme import colors

_DIALOG_WIDTH = 500
_DIALOG_HEIGHT = 300


class ResetSettingsDialog(QDialog):
    """Dialog for selectively resetting application and schema settings.

    After exec(), check `app_settings_reset` to know whether the caller
    should resize the main window to the default size.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(tr("Reset Settings"))
        self.resize(_DIALOG_WIDTH, _DIALOG_HEIGHT)
        self.app_settings_reset = False

        layout = QVBoxLayout(self)

        info = QLabel(
            tr("Select which settings to reset to default values.\nThis action cannot be undone.")
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        group = QGroupBox(tr("Reset Options"))
        group_layout = QVBoxLayout()
        self._app_cb = QCheckBox(tr("Application Settings (app_config.json)"))
        self._app_cb.setToolTip(
            tr("Reset the case directory, window size, saved session, theme, "
               "language, case library, and links")
        )
        self._schema_cb = QCheckBox(tr("Schema Module Settings (schema_config.json)"))
        self._schema_cb.setToolTip(tr("Reset schema modules to default (controlDict, fvSchemes, fvSolution)"))
        group_layout.addWidget(self._app_cb)
        group_layout.addWidget(self._schema_cb)
        group.setLayout(group_layout)
        layout.addWidget(group)

        warning = QLabel(
            tr("⚠️ Warning: This will delete the selected configuration files and restore default settings.")
        )
        warning.setWordWrap(True)
        warning.setStyleSheet(f"color: {colors().warning_text}; font-weight: bold;")
        layout.addWidget(warning)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton(tr("Cancel"))
        reset_btn = QPushButton(tr("Reset Selected"))
        reset_btn.setStyleSheet(f"background-color: {colors().warning_text}; color: white;")
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(reset_btn)
        layout.addLayout(btn_layout)

        cancel_btn.clicked.connect(self.reject)
        reset_btn.clicked.connect(self._perform_reset)

    def _perform_reset(self) -> None:
        if not self._app_cb.isChecked() and not self._schema_cb.isChecked():
            QMessageBox.warning(self, tr("No Selection"), tr("Please select at least one option to reset."))
            return

        items = ""
        if self._app_cb.isChecked():
            items += tr("• Application Settings\n")
        if self._schema_cb.isChecked():
            items += tr("• Schema Module Settings\n")

        reply = QMessageBox.question(
            self,
            tr("Confirm Reset"),
            tr("Are you sure you want to reset:\n\n{items}\nThis action cannot be undone.")
            .format(items=items),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        messages = []

        if self._app_cb.isChecked():
            try:
                get_app_config().delete_config_file()
                self.app_settings_reset = True
                messages.append(
                    tr("✓ Application settings reset successfully\n"
                       "  (window size restored to {w}x{h})")
                    .format(w=DEFAULT_WINDOW_WIDTH, h=DEFAULT_WINDOW_HEIGHT)
                )
                # The reset only holds if nothing writes the file back. Closing
                # the window persists nothing from here on (see closeEvent), so
                # say what that costs rather than let it surprise anyone.
                messages.append(
                    tr("  The window layout and size of this session are not saved.")
                )
            except Exception as e:
                messages.append(tr("✗ Failed to reset app settings: {e}").format(e=e))

        if self._schema_cb.isChecked():
            try:
                from schemas import delete_schema_config

                delete_schema_config()
                messages.append(tr("✓ Schema module settings reset successfully"))
            except Exception as e:
                messages.append(tr("✗ Failed to reset schema settings: {e}").format(e=e))

        QMessageBox.information(
            self,
            tr("Reset Complete"),
            "\n".join(messages)
            + tr("\n\nPlease restart the application for all changes to take effect."),
        )
        self.accept()
