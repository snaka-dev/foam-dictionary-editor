# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from i18n import tr
from services.tool_options import OptionValue, ToolSpec, build_command

_DIALOG_WIDTH = 560


class RunToolDialog(QDialog):
    """Generic options dialog for the Tools-menu "Run *" actions.

    Built from a ``services/tool_options.ToolSpec``: bool options become
    checkboxes, value/file options become line edits (file options get a
    Browse button). A free-text "Extra options" row covers everything the
    curated spec leaves out, and a live preview shows the exact command that
    will be sent to the terminal.

    ``warning_text`` (optional) is a pre-flight note shown at the top (e.g.
    "this case already has results"). ``prefix_option`` (optional) is a
    ``(label, shell_prefix, default_checked)`` tuple rendered as a checkbox
    that prepends ``shell_prefix`` to the command (e.g. restoring 0/ before
    setFields).
    """

    def __init__(
        self,
        spec: ToolSpec,
        case_dir: str,
        last_values: dict | None = None,
        warning_text: str = "",
        prefix_option: tuple[str, str, bool] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._spec = spec
        self._case_dir = case_dir
        self._prefix_cmd = prefix_option[1] if prefix_option else ""
        self.setWindowTitle(tr("Run {tool}").format(tool=spec.name))
        self.setMinimumWidth(_DIALOG_WIDTH)

        values = last_values or {}

        layout = QVBoxLayout(self)

        # ── pre-flight warning ────────────────────────────────────────────────
        if warning_text:
            warning = QLabel("⚠ " + warning_text)
            warning.setWordWrap(True)
            layout.addWidget(warning)
            layout.addSpacing(4)

        # ── prefix checkbox (e.g. "Restore 0/ first") ─────────────────────────
        self._prefix_chk: QCheckBox | None = None
        if prefix_option is not None:
            label, _prefix_cmd, default_checked = prefix_option
            self._prefix_chk = QCheckBox(label)
            self._prefix_chk.setChecked(default_checked)
            self._prefix_chk.toggled.connect(self._update_preview)
            layout.addWidget(self._prefix_chk)
            layout.addSpacing(4)

        # ── per-option rows from the spec ─────────────────────────────────────
        self._checks: dict[str, QCheckBox] = {}
        self._edits: dict[str, QLineEdit] = {}
        form = QFormLayout()
        form.setHorizontalSpacing(8)
        for opt in spec.options:
            value = values.get(opt.flag, opt.default)
            if opt.kind == "bool":
                chk = QCheckBox(f"{tr(opt.label)}  ({opt.flag})")
                chk.setChecked(bool(value))
                chk.toggled.connect(self._update_preview)
                self._checks[opt.flag] = chk
                form.addRow(chk)
                continue
            edit = QLineEdit(str(value))
            if opt.placeholder:
                edit.setPlaceholderText(tr(opt.placeholder))
            edit.textChanged.connect(self._update_preview)
            self._edits[opt.flag] = edit
            if opt.kind == "file":
                browse_btn = QPushButton(tr("Browse…"))
                browse_btn.clicked.connect(
                    lambda _=False, e=edit: self._browse(e)
                )
                row = QHBoxLayout()
                row.addWidget(edit, 1)
                row.addWidget(browse_btn)
                form.addRow(f"{tr(opt.label)} ({opt.flag}):", row)
            else:
                form.addRow(f"{tr(opt.label)} ({opt.flag}):", edit)

        # ── extra options ─────────────────────────────────────────────────────
        self._extra_edit = QLineEdit(str(values.get("extra", "")))
        self._extra_edit.setPlaceholderText(tr("Additional options (e.g. -time 0.5)"))
        self._extra_edit.textChanged.connect(self._update_preview)
        form.addRow(tr("Extra options:"), self._extra_edit)
        layout.addLayout(form)

        # ── command preview ───────────────────────────────────────────────────
        preview_box = QFrame()
        preview_box.setFrameShape(QFrame.StyledPanel)
        preview_layout = QVBoxLayout(preview_box)
        preview_layout.setContentsMargins(8, 6, 8, 6)
        self._preview = QLabel()
        self._preview.setWordWrap(True)
        self._preview.setTextInteractionFlags(Qt.TextSelectableByMouse)
        font = self._preview.font()
        font.setFamily("monospace")
        font.setStyleHint(font.StyleHint.Monospace)
        self._preview.setFont(font)
        preview_layout.addWidget(self._preview)
        layout.addSpacing(4)
        layout.addWidget(QLabel(tr("Command:")))
        layout.addWidget(preview_box)

        # ── buttons ───────────────────────────────────────────────────────────
        layout.addStretch()
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton(tr("Cancel"))
        self._run_btn = QPushButton(tr("Run"))
        self._run_btn.setDefault(True)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(self._run_btn)
        layout.addLayout(btn_row)

        cancel_btn.clicked.connect(self.reject)
        self._run_btn.clicked.connect(self.accept)

        self._update_preview()

    # ── results ───────────────────────────────────────────────────────────────

    def get_values(self) -> dict:
        """Current option values, in the shape ``build_command`` expects
        (plus the ``"extra"`` free-text), for session persistence."""
        values: dict[str, OptionValue] = {
            flag: chk.isChecked() for flag, chk in self._checks.items()
        }
        for flag, edit in self._edits.items():
            values[flag] = edit.text().strip()
        values["extra"] = self._extra_edit.text().strip()
        return values

    def get_command(self) -> str:
        """The full shell command to send to the terminal panel."""
        command = self._compose()
        assert command is not None  # Run is disabled while the extra text is invalid
        return command

    # ── internals ─────────────────────────────────────────────────────────────

    def _compose(self) -> str | None:
        values = self.get_values()
        extra = str(values.pop("extra", ""))
        prefix = ""
        if self._prefix_chk is not None and self._prefix_chk.isChecked():
            prefix = self._prefix_cmd
        try:
            return build_command(self._spec, values, extra, prefix)
        except ValueError:
            return None

    def _update_preview(self) -> None:
        command = self._compose()
        if command is None:
            self._preview.setText(tr("(invalid extra options — unbalanced quote?)"))
            self._run_btn.setEnabled(False)
            return
        self._preview.setText(command)
        self._run_btn.setEnabled(True)

    def _browse(self, edit: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, tr("Select dictionary file"), self._case_dir
        )
        if not path:
            return
        # OpenFOAM resolves -dict paths relative to the case directory, and a
        # relative path keeps the command line readable and portable.
        try:
            rel = os.path.relpath(path, self._case_dir)
        except ValueError:
            rel = path
        edit.setText(path if rel.startswith("..") else rel)
