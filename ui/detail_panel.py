# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from foam.nodes import FoamNode
from model.tree_model import FoamTreeModel
from schemas import (
    choice_description_for_value,
    choice_note_for_value,
    choice_supported_in_for_value,
    choices_for_file_key,
    schema_for_file_key,
    schema_note_text,
    schema_supported_in_text,
)

_PAGE_EMPTY = 0
_PAGE_NORMAL = 1
_PAGE_FIELD_VALUE = 2


class DetailPanel(QWidget):
    value_apply_requested = Signal(str)
    field_value_apply_requested = Signal(str, str)  # field_type, raw_value

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_file: str | None = None
        self._current_node_name: str | None = None
        self._current_parent_key: str | None = None
        self._current_grandparent_key: str | None = None

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_empty_page())
        self._stack.addWidget(self._build_normal_page())
        self._stack.addWidget(self._build_field_value_page())

        scroll = QScrollArea()
        scroll.setWidget(self._stack)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)

    def show_empty(self) -> None:
        self._stack.setCurrentIndex(_PAGE_EMPTY)

    def show_for_node(self, node: FoamNode, model: FoamTreeModel, file_path: str | None) -> None:
        self._current_file = file_path
        self._current_node_name = node.name
        self._current_parent_key = node.parent.name if node.parent else None
        self._current_grandparent_key = (
            node.parent.parent.name
            if node.parent and node.parent.parent
            else None
        )
        self._populate_normal(node, model, file_path)
        self._stack.setCurrentIndex(_PAGE_NORMAL)

    def show_field_value_for_node(self, node: FoamNode, model: FoamTreeModel) -> None:
        self._populate_field_value(node, model)
        self._stack.setCurrentIndex(_PAGE_FIELD_VALUE)

    # ── page builders ─────────────────────────────────────────────────────────

    def _build_empty_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("No item selected"))
        layout.addStretch(1)
        return page

    def _build_normal_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        self._key_label = QLabel("-")
        self._type_label = QLabel("-")

        self._key_description_label = QLabel("")
        self._key_description_label.setWordWrap(True)
        self._key_description_label.setVisible(False)

        self._key_supported_in_label = QLabel("")
        self._key_supported_in_label.setWordWrap(True)
        self._key_supported_in_label.setVisible(False)

        self._key_note_label = QLabel("")
        self._key_note_label.setWordWrap(True)
        self._key_note_label.setVisible(False)

        self._value_edit = QLineEdit()

        self._value_combo = QComboBox()
        self._value_combo.setEditable(True)
        self._value_combo.setInsertPolicy(QComboBox.NoInsert)
        self._value_combo.setVisible(False)
        self._value_combo.currentTextChanged.connect(self._on_combo_changed)

        self._choice_hint_label = QLabel("")
        self._choice_hint_label.setWordWrap(True)
        self._choice_hint_label.setVisible(False)

        self._choice_description_label = QLabel("")
        self._choice_description_label.setWordWrap(True)
        self._choice_description_label.setVisible(False)

        self._choice_supported_in_label = QLabel("")
        self._choice_supported_in_label.setWordWrap(True)
        self._choice_supported_in_label.setVisible(False)

        self._choice_note_label = QLabel("")
        self._choice_note_label.setWordWrap(True)
        self._choice_note_label.setVisible(False)

        self._apply_button = QPushButton("Apply Value")
        self._apply_button.clicked.connect(self._on_apply_value)

        form = QFormLayout()
        form.addRow("Key", self._key_label)
        form.addRow("Type", self._type_label)
        form.addRow("Key Help", self._key_description_label)
        form.addRow("Key Supported In", self._key_supported_in_label)
        form.addRow("Key Note", self._key_note_label)
        form.addRow("Value", self._value_edit)
        form.addRow("Choices", self._value_combo)
        form.addRow("Choice Help", self._choice_description_label)
        form.addRow("Choice Supported In", self._choice_supported_in_label)
        form.addRow("Choice Note", self._choice_note_label)
        form.addRow("", self._choice_hint_label)
        form.addRow("", self._apply_button)

        layout.addLayout(form)
        layout.addStretch(1)
        return page

    def _build_field_value_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        self._fv_type_edit = QLineEdit()
        self._fv_name_label = QLabel("-")
        self._fv_value_edit = QLineEdit()
        self._fv_apply_button = QPushButton("Apply Field Value")
        self._fv_apply_button.clicked.connect(self._on_apply_field_value)

        form = QFormLayout()
        form.addRow("Field Type", self._fv_type_edit)
        form.addRow("Field Name", self._fv_name_label)
        form.addRow("Value", self._fv_value_edit)
        form.addRow("", self._fv_apply_button)

        layout.addLayout(form)
        layout.addStretch(1)
        return page

    # ── populate ──────────────────────────────────────────────────────────────

    def _populate_normal(self, node: FoamNode, model: FoamTreeModel, file_path: str | None) -> None:
        self._key_label.setText(node.name or "-")
        self._type_label.setText(node.node_type)

        current_value = model._display_value(node)
        editable = model._is_value_editable(node)
        parent_key = self._current_parent_key
        grandparent_key = self._current_grandparent_key
        choices = choices_for_file_key(file_path, node.name, parent_key, grandparent_key)
        schema = schema_for_file_key(file_path, node.name, parent_key, grandparent_key)

        if schema is not None and schema.description:
            self._key_description_label.setText(schema.description)
            self._key_description_label.setVisible(True)
        else:
            self._key_description_label.clear()
            self._key_description_label.setVisible(False)

        key_supported_in = schema_supported_in_text(file_path, node.name, parent_key, grandparent_key)
        self._key_supported_in_label.setText(key_supported_in)
        self._key_supported_in_label.setVisible(bool(key_supported_in))

        key_note = schema_note_text(file_path, node.name, parent_key, grandparent_key)
        self._key_note_label.setText(key_note)
        self._key_note_label.setVisible(bool(key_note))

        self._apply_button.setEnabled(editable)

        if editable and choices:
            self._show_choice_editor(node.name, current_value, choices, editable)
        else:
            self._show_text_editor(current_value, editable)

    def _populate_field_value(self, node: FoamNode, model: FoamTreeModel) -> None:
        data = node.value
        with QSignalBlocker(self._fv_type_edit):
            self._fv_type_edit.setText(data.get("field_type", ""))
        self._fv_name_label.setText(data.get("field_name", "-"))
        with QSignalBlocker(self._fv_value_edit):
            self._fv_value_edit.setText(
                model._format_embedded_value(
                    data.get("value_type"),
                    data.get("value"),
                    data.get("raw_value"),
                )
            )

    # ── value editor helpers ──────────────────────────────────────────────────

    def _show_choice_editor(self, node_name: str, current_value: str, choices: list[str], editable: bool) -> None:
        with QSignalBlocker(self._value_combo):
            self._value_combo.clear()
            self._value_combo.addItems(choices)
            if current_value and current_value not in choices:
                self._value_combo.insertItem(0, current_value)
                self._value_combo.setCurrentIndex(0)
            elif current_value in choices:
                self._value_combo.setCurrentText(current_value)
            elif choices:
                self._value_combo.setCurrentIndex(0)

        self._value_edit.setVisible(False)
        self._value_edit.setEnabled(False)
        self._value_combo.setVisible(True)
        self._value_combo.setEnabled(editable)
        self._choice_hint_label.setText("Select a suggested value or type a custom value.")
        self._choice_hint_label.setVisible(True)
        self._update_choice_help(node_name, self._value_combo.currentText())

    def _show_text_editor(self, current_value: str, editable: bool) -> None:
        with QSignalBlocker(self._value_edit):
            self._value_edit.setText(current_value)

        self._value_combo.setVisible(False)
        self._value_combo.setEnabled(False)
        self._value_combo.clear()
        self._choice_hint_label.clear()
        self._choice_hint_label.setVisible(False)
        self._clear_choice_help()
        self._value_edit.setVisible(True)
        self._value_edit.setEnabled(editable)

    def _update_choice_help(self, node_name: str, value: str) -> None:
        parent_key = self._current_parent_key
        grandparent_key = self._current_grandparent_key
        description = choice_description_for_value(self._current_file, node_name, value, parent_key, grandparent_key)
        supported_in = choice_supported_in_for_value(self._current_file, node_name, value, parent_key, grandparent_key)
        note = choice_note_for_value(self._current_file, node_name, value, parent_key, grandparent_key)

        self._choice_description_label.setText(description)
        self._choice_description_label.setVisible(bool(description))
        self._choice_supported_in_label.setText(supported_in)
        self._choice_supported_in_label.setVisible(bool(supported_in))
        self._choice_note_label.setText(note)
        self._choice_note_label.setVisible(bool(note))

    def _clear_choice_help(self) -> None:
        self._choice_description_label.clear()
        self._choice_description_label.setVisible(False)
        self._choice_supported_in_label.clear()
        self._choice_supported_in_label.setVisible(False)
        self._choice_note_label.clear()
        self._choice_note_label.setVisible(False)

    # ── slots ─────────────────────────────────────────────────────────────────

    def _on_combo_changed(self, text: str) -> None:
        if self._current_node_name:
            self._update_choice_help(self._current_node_name, text)

    def _on_apply_value(self) -> None:
        if self._value_combo.isVisible():
            value = self._value_combo.currentText().strip()
        else:
            value = self._value_edit.text().strip()
        self.value_apply_requested.emit(value)

    def _on_apply_field_value(self) -> None:
        field_type = self._fv_type_edit.text().strip()
        raw_value = self._fv_value_edit.text()
        self.field_value_apply_requested.emit(field_type, raw_value)
