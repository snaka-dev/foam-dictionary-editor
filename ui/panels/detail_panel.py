# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtGui import QResizeEvent
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
from foam.utils import format_embedded_value
from i18n import tr
from model.tree_model import FoamTreeModel
from schemas import (
    KeySchema,
    choice_for_value,
    has_unmeasured_successor,
    schema_for_file_key,
    supported_in_text,
)
from ui.label_fit import fit_wrapped_labels
from ui.theme import colors


def _qualified_supported_in(schema_or_choice: object) -> str:
    """`supported_in_text`, plus a caveat when a label stops at the newest
    release that was actually measured.

    Without it a Foundation 14 user reads "Foundation v7-v13" on a core key as
    "not available in the release I am running". The span is a verification
    record rather than a claim of absence (see `schemas/_base.py`), and saying
    so costs one clause and needs no re-measurement when the fork ships again.
    """
    text = supported_in_text(schema_or_choice)  # type: ignore[arg-type]
    if not text:
        return text
    # A `deprecated_since` means the span ends for a reason we established, not
    # for want of looking — so the caveat would be actively wrong there.
    if getattr(schema_or_choice, "deprecated_since", ""):
        return text
    tags = getattr(schema_or_choice, "supported_in", ())
    if has_unmeasured_successor(tags):
        return f"{text} {tr('(newer releases not yet measured)')}"
    return text


def _if_omitted_text(schema: KeySchema | None) -> str:
    """One line answering "what happens if I leave this key out?".

    `default` and `required` are two spellings of one question, so they share a
    row rather than each getting one: a key either falls back to something or it
    does not, never both (`schemas/_base.py` states the exclusivity and
    `tests/schemas/test_default_and_required.py` enforces it). Returning "" for
    a schema that records neither keeps the row hidden, which is the common case
    -- most entries carry their default in `description` prose and say nothing
    here.
    """
    if schema is None:
        return ""
    if schema.default:
        return tr("Defaults to {0}.").format(schema.default)
    if schema.required:
        return tr("Required — OpenFOAM reads no default for this key.")
    return ""


_PAGE_EMPTY = 0
_PAGE_NORMAL = 1
_PAGE_FIELD_VALUE = 2


class DetailPanel(QWidget):
    value_apply_requested = Signal(str)
    field_value_apply_requested = Signal(str, str)  # field_type, raw_value

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_file: str | None = None
        self._current_node_name: str | None = None
        self._current_parent_key: str | None = None
        self._current_grandparent_key: str | None = None

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_empty_page())
        self._stack.addWidget(self._build_normal_page())
        self._stack.addWidget(self._build_field_value_page())

        self._scroll = QScrollArea()
        self._scroll.setWidget(self._stack)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._scroll)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Re-fit wrapped labels whenever the panel's width changes.

        Unlike the two dialogs `ui/label_fit.py` was written for -- laid out
        once and fitted once from `showEvent` -- this panel lives in the
        `right_upper` splitter and gets a new width every time that splitter
        moves, independent of any repopulation. Without this override, a label
        fitted at a wide splitter position stays under-sized after the splitter
        narrows, clipping its last line again.
        """
        super().resizeEvent(event)
        self._refit_labels()

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
        # The page must already be current before _populate_normal runs: its
        # trailing _refit_labels() call measures each wrapped label's width to
        # compute the height it needs, and a QStackedWidget only assigns a
        # non-current page's children their real geometry once it becomes
        # current. Fitting first and switching after would measure whatever
        # stale width the page last had (0 for the very first selection),
        # under-sizing every label exactly like the bug this fixes.
        self._stack.setCurrentIndex(_PAGE_NORMAL)
        self._populate_normal(node, model, file_path)

    def show_field_value_for_node(self, node: FoamNode, model: FoamTreeModel) -> None:
        # See show_for_node: the page has to be current before populating it.
        self._stack.setCurrentIndex(_PAGE_FIELD_VALUE)
        self._populate_field_value(node, model)

    # ── page builders ─────────────────────────────────────────────────────────

    def _build_empty_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel(tr("No item selected")))
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

        self._key_provenance_label = QLabel("")
        self._key_provenance_label.setWordWrap(True)
        self._key_provenance_label.setVisible(False)

        self._key_supported_in_label = QLabel("")
        self._key_supported_in_label.setWordWrap(True)
        self._key_supported_in_label.setVisible(False)

        self._key_default_label = QLabel("")
        self._key_default_label.setWordWrap(True)
        self._key_default_label.setVisible(False)

        self._key_note_label = QLabel("")
        self._key_note_label.setWordWrap(True)
        self._key_note_label.setVisible(False)

        self._value_edit = QLineEdit()

        self._value_combo = QComboBox()
        self._value_combo.setEditable(True)
        self._value_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
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

        self._apply_button = QPushButton(tr("Apply Value"))
        self._apply_button.clicked.connect(self._on_apply_value)

        form = QFormLayout()
        form.addRow(tr("Key"), self._key_label)
        form.addRow(tr("Type"), self._type_label)
        form.addRow(tr("Key Help"), self._key_description_label)
        form.addRow(tr("Key Status"), self._key_provenance_label)
        form.addRow(tr("Key Supported In"), self._key_supported_in_label)
        form.addRow(tr("If Omitted"), self._key_default_label)
        form.addRow(tr("Key Note"), self._key_note_label)
        form.addRow(tr("Value"), self._value_edit)
        form.addRow(tr("Choices"), self._value_combo)
        form.addRow(tr("Choice Help"), self._choice_description_label)
        form.addRow(tr("Choice Supported In"), self._choice_supported_in_label)
        form.addRow(tr("Choice Note"), self._choice_note_label)
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
        self._fv_apply_button = QPushButton(tr("Apply Field Value"))
        self._fv_apply_button.clicked.connect(self._on_apply_field_value)

        form = QFormLayout()
        form.addRow(tr("Field Type"), self._fv_type_edit)
        form.addRow(tr("Field Name"), self._fv_name_label)
        form.addRow(tr("Value"), self._fv_value_edit)
        form.addRow("", self._fv_apply_button)

        layout.addLayout(form)
        layout.addStretch(1)
        return page

    # ── populate ──────────────────────────────────────────────────────────────

    def _populate_normal(self, node: FoamNode, model: FoamTreeModel, file_path: str | None) -> None:
        self._key_label.setText(node.name or "-")
        self._type_label.setText(node.node_type)

        current_value = model._display_value(node)
        # A read-only model is an `#include` target outside the case directory.
        editable = model._is_value_editable(node) and not model.read_only
        parent_key = self._current_parent_key
        grandparent_key = self._current_grandparent_key
        schema = schema_for_file_key(file_path, node.name, parent_key, grandparent_key)
        choices = [item.value for item in schema.choices] if schema is not None else []

        if schema is not None and schema.description:
            self._key_description_label.setText(schema.description)
            self._key_description_label.setVisible(True)
        else:
            self._key_description_label.clear()
            self._key_description_label.setVisible(False)

        self._apply_provenance(schema)

        key_supported_in = _qualified_supported_in(schema)
        self._key_supported_in_label.setText(key_supported_in)
        self._key_supported_in_label.setVisible(bool(key_supported_in))

        omitted = _if_omitted_text(schema)
        self._key_default_label.setText(omitted)
        self._key_default_label.setVisible(bool(omitted))

        # A directive row has no schema, so the note line is free to carry where
        # its `#include` resolved to (or why it did not).
        key_note = model.include_note(node) or (schema.note if schema is not None else "")
        self._key_note_label.setText(key_note)
        self._key_note_label.setVisible(bool(key_note))

        self._apply_button.setEnabled(editable)

        if editable and choices:
            self._show_choice_editor(node.name, current_value, choices, editable)
        else:
            self._show_text_editor(current_value, editable)

        self._refit_labels()

    def _apply_provenance(self, schema: KeySchema | None) -> None:
        """Show whether a key is current, a historical name, or a dead entry.

        The `ineffective` case is the one worth the screen space: keys such as
        `minFlatness` are copied out of the official tutorials into thousands of
        cases, and OpenFOAM reads straight past them without a word.
        """
        text = ""
        warn = False

        if schema is not None:
            if schema.status == "renamed" and schema.use_instead:
                since = f" in {schema.deprecated_since}" if schema.deprecated_since else ""
                text = tr("Historical name — OpenFOAM reads '{0}'{1}.").format(
                    schema.use_instead, since
                )
            elif schema.status == "ineffective":
                target = schema.use_instead
                text = (
                    tr("Has no effect — OpenFOAM reads '{0}' instead.").format(target)
                    if target
                    else tr("Has no effect — no OpenFOAM reader consumes this entry.")
                )
                warn = True
            elif schema.renamed_from:
                text = tr("Formerly {0}.").format(
                    ", ".join(f"'{name}'" for name in schema.renamed_from)
                )

        if warn:
            self._key_provenance_label.setStyleSheet(f"color: {colors().warning_text};")
        else:
            self._key_provenance_label.setStyleSheet("")
        self._key_provenance_label.setText(text)
        self._key_provenance_label.setVisible(bool(text))

    def _populate_field_value(self, node: FoamNode, model: FoamTreeModel) -> None:
        data = node.value
        with QSignalBlocker(self._fv_type_edit):
            self._fv_type_edit.setText(data.get("field_type", ""))
        self._fv_name_label.setText(data.get("field_name", "-"))
        with QSignalBlocker(self._fv_value_edit):
            self._fv_value_edit.setText(
                format_embedded_value(
                    data.get("value_type"),
                    data.get("value"),
                    data.get("raw_value"),
                )
            )

        self._refit_labels()

    def _refit_labels(self) -> None:
        """Re-run `fit_wrapped_labels` from scratch for the panel's current width.

        `fit_wrapped_labels` only ever *raises* a label's minimum height, which
        is correct for a dialog fitted once at a fixed width. This panel is
        fitted repeatedly -- on every tree selection and every splitter drag --
        so a minimum raised for a wide width would survive a later narrow one
        and leave a gap below a label that no longer needs the room. Clearing
        the minimums first makes each call start from the label's true
        unwrapped height, same as a first call would.
        """
        for label in self.findChildren(QLabel):
            if label.wordWrap():
                label.setMinimumHeight(0)

        page = self._stack.currentWidget()
        page_layout = page.layout() if page is not None else None

        # First activate(): a label this call just made visible (a schema
        # note/description that was previously hidden) is still carrying
        # whatever width it had the last time the layout touched it -- 0 for
        # one that has never been shown. fit_wrapped_labels reads
        # label.width() to size against, so measuring before this pass would
        # silently skip that label (the width <= 0 guard) and leave its
        # minimum at 0, no matter how long its text is.
        if page_layout is not None:
            page_layout.activate()

        fit_wrapped_labels(self)

        # Second activate(): apply the minimums fit_wrapped_labels just set.
        # Both calls are needed because raising a widget's minimum height only
        # invalidates the layout that manages it -- recomputing the actual
        # geometry (what label.height() reports) needs an explicit activate(),
        # same as the two dialogs ui/label_fit.py was written for, which do it
        # once from showEvent. This panel repopulates continuously, so it does
        # the same on every call instead.
        if page_layout is not None:
            page_layout.activate()

        # activate() only redistributes space *within* the page's current
        # rect; it does not grow the page itself, so a page that now needs
        # more room than it currently has would otherwise leave the extra
        # height invisible below the scroll area's tracked range. The scroll
        # area only picks up a widget's new sizeHint on its own once it
        # processes a resize -- driving that resize here (rather than waiting
        # for one) is what makes the extra scroll range available immediately.
        self._stack.resize(self._stack.width(), self._stack.sizeHint().height())

    # ── value editor helpers ──────────────────────────────────────────────────

    def _show_choice_editor(
        self, node_name: str, current_value: str, choices: list[str], editable: bool
    ) -> None:
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
        self._choice_hint_label.setText(tr("Select a suggested value or type a custom value."))
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
        item = choice_for_value(self._current_file, node_name, value, parent_key, grandparent_key)
        description = item.description if item else ""
        supported_in = _qualified_supported_in(item)
        note = item.note if item else ""

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
