# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tools > Add Function Object…: pick an installation template, fill it in.

The list and every form come from the user's own OpenFOAM installation
(services/function_templates.py): the form shows exactly the entries the
template itself sets, each with an input for its kind -- names picked from
the case's fields or patches, points as ``x y z`` per line -- and the preview
under it is the file that will be written, so what a beginner fills in is
always visible as the OpenFOAM text it becomes.
"""
from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from functools import partial

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPlainTextEdit,
    QScrollArea,
    QSplitter,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from i18n import tr
from services.function_templates import (
    CHOICES,
    SURFACES_SEPARATOR,
    FunctionTemplate,
    ParsedTemplate,
    TemplateEntry,
    form_text,
    is_valid_function_name,
    parse_template,
    render,
    value_problem,
)
from ui.fonts import monospace_font, small_font
from ui.theme import colors

_TEMPLATE_ROLE = Qt.ItemDataRole.UserRole + 1


class _NamesInput(QWidget):
    """A line of names, plus a ▾ menu of the case's names to tick in and out."""

    def __init__(self, text: str, choices: Sequence[str], single: bool) -> None:
        super().__init__()
        self.edit = QLineEdit(text)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.edit, 1)
        self._single = single
        if choices:
            button = QToolButton()
            button.setText("▾")
            button.setToolTip(tr("Pick from this case"))
            button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            menu = QMenu(button)
            for name in choices:
                action = menu.addAction(name)
                action.setCheckable(not single)
                action.triggered.connect(partial(self._toggle, name))
            menu.aboutToShow.connect(partial(self._sync_checks, menu))
            button.setMenu(menu)
            row.addWidget(button)

    def _words(self) -> list[str]:
        return self.edit.text().replace(",", " ").split()

    def _toggle(self, name: str) -> None:
        if self._single:
            self.edit.setText(name)
            return
        words = self._words()
        if name in words:
            words.remove(name)
        else:
            words.append(name)
        self.edit.setText(" ".join(words))

    def _sync_checks(self, menu: QMenu) -> None:
        words = set(self._words())
        for action in menu.actions():
            action.setChecked(action.text() in words)

    def text(self) -> str:
        return self.edit.text()


class _SurfacesInput(QWidget):
    """OpenCFD's sampled surfaces: cutting-plane rows, and the rest as text."""

    def __init__(self, value: str) -> None:
        super().__init__()
        planes, _, others = value.partition(SURFACES_SEPARATOR)
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.addWidget(QLabel(tr("Cutting planes — one per line: name  px py pz  nx ny nz")))
        self.planes = QPlainTextEdit(planes.strip("\n"))
        self.planes.setFont(monospace_font())
        self.planes.setPlaceholderText(tr("midPlane  0 0 0.005  0 0 1"))
        self.planes.setFixedHeight(self.planes.fontMetrics().lineSpacing() * 5 + 12)
        box.addWidget(self.planes)
        box.addWidget(
            QLabel(tr("Other surfaces, as written — delete those this case does not have:"))
        )
        self.others = QPlainTextEdit(others.strip("\n"))
        self.others.setFont(monospace_font())
        self.others.setFixedHeight(self.others.fontMetrics().lineSpacing() * 7 + 12)
        box.addWidget(self.others)

    def text(self) -> str:
        return (
            self.planes.toPlainText().strip("\n") + "\n" + SURFACES_SEPARATOR + "\n"
            + self.others.toPlainText().strip("\n")
        )


class FunctionObjectDialog(QDialog):
    """The template list beside the chosen template's form and preview.

    ``taken`` are names already in use -- in controlDict's ``functions``, or
    as a file in ``system/`` -- so the name field can refuse them before
    anything is written. :meth:`result_name`/:meth:`result_text` give what
    to write once accepted.

    ``preview_changed(name, text)`` carries the file to be written, at most
    a few times a second, for the main window's 3-D view to draw live.
    ``post_process`` is the command offered for results that already exist,
    with ``{name}`` for the function's name (``postProcess -func {name}
    -latestTime``, Foundation 11+'s ``foamPostProcess``, or an ``mpirun …
    -parallel`` form); "" hides the option.
    """

    preview_changed = Signal(str, str)

    def __init__(
        self,
        templates: Sequence[FunctionTemplate],
        source: str,
        field_names: Sequence[str],
        patch_names: Sequence[str],
        taken: set[str],
        parent: QWidget | None = None,
        *,
        post_process: str = "",
        legacy_plane_keys: bool = False,
        suggest: Callable[[ParsedTemplate], dict[str, tuple[str, str]]] | None = None,
        background: bool = False,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Add Function Object"))
        self.resize(980, 640)
        self._fields = list(field_names)
        self._patches = list(patch_names)
        self._taken = taken
        self._template: FunctionTemplate | None = None
        self._parsed: ParsedTemplate | None = None
        self._inputs: dict[str, QWidget] = {}

        layout = QVBoxLayout(self)
        intro = QLabel(
            tr(
                "Choose a function object from your OpenFOAM installation's "
                "templates and fill in its settings. FoDE writes it to "
                "system/<name> and adds #includeFunc <name> to controlDict, "
                "as the tutorials do."
            )
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        src = QLabel(tr("Templates from: {path}").format(path=source))
        src.setFont(small_font())
        src.setStyleSheet(f"color: {colors().hint_text};")
        src.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(src)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter, 1)

        left = QWidget()
        left_box = QVBoxLayout(left)
        left_box.setContentsMargins(0, 0, 0, 0)
        self._search = QLineEdit()
        self._search.setPlaceholderText(tr("Search (name or description)"))
        self._search.textChanged.connect(self._filter)
        left_box.addWidget(self._search)
        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        left_box.addWidget(self._tree, 1)
        splitter.addWidget(left)

        right = QWidget()
        right_box = QVBoxLayout(right)
        right_box.setContentsMargins(0, 0, 0, 0)
        self._description = QLabel(tr("Choose a template on the left."))
        self._description.setWordWrap(True)
        right_box.addWidget(self._description)
        name_row = QFormLayout()
        self._name = QLineEdit()
        self._name.textChanged.connect(self._update)
        name_row.addRow(tr("Name:"), self._name)
        right_box.addLayout(name_row)
        self._form_area = QScrollArea()
        self._form_area.setWidgetResizable(True)
        # The form gets the larger share: its notes (where a value came from)
        # are what a beginner reads, and the preview is there to glance at.
        right_box.addWidget(self._form_area, 3)
        right_box.addWidget(QLabel(tr("File to be written:")))
        self._preview = QPlainTextEdit()
        self._preview.setFont(monospace_font())
        self._preview.setReadOnly(True)
        self._preview.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        right_box.addWidget(self._preview, 2)
        self._problem = QLabel()
        self._problem.setWordWrap(True)
        self._problem.setStyleSheet(f"color: {colors().warning_text};")
        right_box.addWidget(self._problem)
        self._post_process = post_process
        self._legacy_plane_keys = legacy_plane_keys
        # Starting places for probes, lines and planes inside the domain
        # (services/function_templates.suggest_values); *background* says the
        # domain is only snappyHexMesh's background box.
        self._suggest = suggest
        self._background = background
        self._run_chk: QCheckBox | None = None
        if post_process:
            self._run_chk = QCheckBox()
            self._run_chk.setToolTip(
                tr(
                    "Applies the function object to the latest results that "
                    "already exist, in the Terminal tab — through the solver "
                    "when the function needs its models (forces, yPlus, …). It "
                    "runs with the solver from now on either way."
                )
            )
            right_box.addWidget(self._run_chk)
        # Debounced: the 3-D view re-parses and re-draws on each change.
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(250)
        self._preview_timer.timeout.connect(self._emit_preview)
        splitter.addWidget(right)
        splitter.setSizes([300, 680])

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._ok = self._buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._ok.setText(tr("Add"))
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        self._fill_tree(templates)
        self._tree.currentItemChanged.connect(self._on_choice)
        self._update()

    # ── results ───────────────────────────────────────────────────────────────

    def result_name(self) -> str:
        return self._name.text().strip()

    def result_text(self) -> str:
        return self._preview.toPlainText()

    def run_post_process(self) -> bool:
        """Whether to run the function object on existing results after adding."""
        return self._run_chk is not None and self._run_chk.isChecked()

    def _emit_preview(self) -> None:
        if self._parsed is not None:
            self.preview_changed.emit(self.result_name(), self.result_text())

    # ── choosing ──────────────────────────────────────────────────────────────

    def _fill_tree(self, templates: Sequence[FunctionTemplate]) -> None:
        groups: dict[str, QTreeWidgetItem] = {}
        for t in templates:
            parent = groups.get(t.category)
            if parent is None:
                parent = QTreeWidgetItem([t.category or tr("(other)")])
                parent.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self._tree.addTopLevelItem(parent)
                groups[t.category] = parent
            item = QTreeWidgetItem([t.name])
            item.setData(0, _TEMPLATE_ROLE, t)
            item.setToolTip(0, t.description)
            parent.addChild(item)

    def _filter(self, text: str) -> None:
        needle = text.strip().lower()
        for i in range(self._tree.topLevelItemCount()):
            group = self._tree.topLevelItem(i)
            if group is None:
                continue
            shown = 0
            for j in range(group.childCount()):
                item = group.child(j)
                t: FunctionTemplate = item.data(0, _TEMPLATE_ROLE)
                hit = not needle or needle in t.name.lower() or needle in t.description.lower()
                item.setHidden(not hit)
                shown += hit
            group.setHidden(shown == 0)
            group.setExpanded(bool(needle) and shown > 0)

    def select_template(self, category: str, name: str) -> bool:
        """Select a template by category and name; True if found (for tests)."""
        for i in range(self._tree.topLevelItemCount()):
            group = self._tree.topLevelItem(i)
            if group is None:
                continue
            for j in range(group.childCount()):
                item = group.child(j)
                t: FunctionTemplate = item.data(0, _TEMPLATE_ROLE)
                if t.category == category and t.name == name:
                    self._tree.setCurrentItem(item)
                    return True
        return False

    def _on_choice(self, item: QTreeWidgetItem | None, _previous=None) -> None:
        t = item.data(0, _TEMPLATE_ROLE) if item is not None else None
        if t is None:
            return
        try:
            with open(t.path, encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError as e:
            self._description.setText(str(e))
            return
        self._template = t
        self._parsed = parse_template(text)
        self._description.setText(t.description or t.name)
        self._name.blockSignals(True)
        self._name.setText(self._free_name(t.name))
        self._name.blockSignals(False)
        self._build_form()
        self._update()

    def _free_name(self, base: str) -> str:
        if base not in self._taken:
            return base
        n = 1
        while f"{base}{n}" in self._taken:
            n += 1
        return f"{base}{n}"

    # ── the form ──────────────────────────────────────────────────────────────

    def _build_form(self) -> None:
        self._inputs = {}
        holder = QWidget()
        form = QFormLayout(holder)
        assert self._parsed is not None
        self._preview.setReadOnly(self._parsed.formable)
        if not self._parsed.formable:
            note = QLabel(
                tr(
                    "This template holds code FoDE cannot turn into a form. "
                    "Edit it as text below."
                )
            )
            note.setWordWrap(True)
            form.addRow(note)
        elif not self._parsed.entries:
            form.addRow(QLabel(tr("This function object has no settings to fill in.")))
        suggested = self._suggest(self._parsed) if self._suggest is not None else {}
        for entry in self._parsed.entries:
            start = suggested.get(entry.key)
            widget = self._input_for(entry, start[0] if start else None)
            self._inputs[entry.key] = widget
            label = entry.key + (" *" if entry.required else "")
            form.addRow(label, widget)
            hint = entry.hint or _kind_hint(entry.kind)
            if start is not None:
                # Say where a value FoDE chose came from, and its limit.
                hint = _suggestion_note(start[1], self._background) + (
                    "\n" + hint if hint else ""
                )
            if hint:
                note = QLabel(hint)
                note.setWordWrap(True)
                note.setFont(small_font())
                note.setStyleSheet(f"color: {colors().hint_text};")
                form.addRow("", note)
        self._form_area.setWidget(holder)
        if not self._parsed.formable:
            self._preview.setPlainText(self._parsed.text)

    def _input_for(self, entry: TemplateEntry, start: str | None = None) -> QWidget:
        """The input for *entry*, starting at *start* (form text) if given."""
        text = start if start is not None else form_text(entry.kind, entry.value)
        if entry.kind == "surfaces":
            surfaces = _SurfacesInput(start if start is not None else entry.value)
            surfaces.planes.textChanged.connect(self._update)
            surfaces.others.textChanged.connect(self._update)
            return surfaces
        if entry.kind in ("fields", "patches", "field", "patch"):
            names = self._fields if entry.kind.startswith("field") else self._patches
            picker = _NamesInput(text, names, single=entry.kind in ("field", "patch"))
            picker.edit.textChanged.connect(self._update)
            picker.edit.setPlaceholderText(_kind_placeholder(entry.kind))
            return picker
        if entry.kind == "points" or (entry.kind == "text" and "\n" in text):
            edit = QPlainTextEdit(text)
            edit.setFont(monospace_font())
            edit.setFixedHeight(edit.fontMetrics().lineSpacing() * 3 + 12)
            edit.setPlaceholderText(_kind_placeholder(entry.kind))
            edit.textChanged.connect(self._update)
            return edit
        choices: tuple[str, ...] = CHOICES.get(entry.key) or (
            ("true", "false") if entry.kind == "bool" else ()
        )
        if choices:
            combo = QComboBox()
            combo.setEditable(True)
            combo.addItems(list(choices) if text in choices or not text else [text, *choices])
            combo.setCurrentText(text)
            combo.editTextChanged.connect(self._update)
            return combo
        edit_line = QLineEdit(text)
        edit_line.setPlaceholderText(_kind_placeholder(entry.kind))
        edit_line.textChanged.connect(self._update)
        return edit_line

    def _values(self) -> dict[str, str]:
        values = {}
        for key, widget in self._inputs.items():
            if isinstance(widget, (_NamesInput, _SurfacesInput)):
                values[key] = widget.text()
            elif isinstance(widget, QPlainTextEdit):
                values[key] = widget.toPlainText()
            elif isinstance(widget, QComboBox):
                values[key] = widget.currentText()
            elif isinstance(widget, QLineEdit):
                values[key] = widget.text()
        return values

    # ── checking ──────────────────────────────────────────────────────────────

    def _update(self) -> None:
        problem = self._problem_text()
        if self._parsed is not None and self._parsed.formable:
            values = self._values()
            text = render(self._parsed, values, legacy_plane_keys=self._legacy_plane_keys)
            if text != self._preview.toPlainText():
                self._preview.setPlainText(text)
                self._preview.verticalScrollBar().setValue(_first_setting_line(text))
        note = "" if problem else self._unknown_patch_note()
        color = colors().warning_text if problem else colors().attention_text
        self._problem.setStyleSheet(f"color: {color};")
        self._problem.setText(problem or note)
        self._ok.setEnabled(self._parsed is not None and not problem)
        if self._run_chk is not None:
            self._run_chk.setText(
                tr("Also run it on the latest existing results now:  {command}").format(
                    command=self._post_process.format(name=self.result_name() or "<name>")
                )
            )
        if self._parsed is not None:
            self._preview_timer.start()

    def _unknown_patch_note(self) -> str:
        """Patch names this mesh does not have -- a warning, not a refusal.

        OpenCFD's templates pre-fill ``patches (patch1 patch2)``, which would
        only fail inside the solver. Not blocking, because a patch group
        (``inGroups``) is also accepted there and is not among the names.
        """
        if not self._patches or self._parsed is None:
            return ""
        known = set(self._patches)
        kinds = {e.key: e.kind for e in self._parsed.entries}
        unknown: list[str] = []
        for key, value in self._values().items():
            if kinds.get(key) in ("patches", "patch"):
                unknown += [w for w in value.replace(",", " ").split() if w not in known]
        if not unknown:
            return ""
        return tr(
            "Not patches of this case's mesh: {names}. Fine for a patch group; "
            "otherwise pick from ▾ before running."
        ).format(names=", ".join(dict.fromkeys(unknown)))

    def _problem_text(self) -> str:
        if self._parsed is None:
            return ""
        name = self.result_name()
        if not is_valid_function_name(name):
            return tr("Name: letters, digits and _ only, starting with a letter.")
        if name in self._taken:
            return tr(
                "Name: {name} is already used in this case (in controlDict or "
                "as system/{name}) — choose another."
            ).format(name=name)
        by_key = {e.key: e for e in self._parsed.entries}
        for key, value in self._values().items():
            entry = by_key[key]
            code = value_problem(entry.kind, value)
            if entry.kind == "text" and code not in ("placeholder", "empty"):
                code = ""
            if code:
                return _problem_sentence(key, code)
        return ""


def _first_setting_line(text: str) -> int:
    """The line after a template's banner comment, where its settings begin.

    The preview scrolls there, so what the form is filling in is on screen
    rather than OpenFOAM's ASCII-art header.
    """
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line.rstrip().endswith("*/"):
            return i + 1
    return 0


def _suggestion_note(reason: str, background: bool) -> str:
    """Where FoDE's starting value came from, for the note under the field."""
    text = {
        "centre": tr("Placed at the centre of the mesh (from blockMeshDict)."),
        "line": tr(
            "Along the mesh's longest direction, through its centre (from blockMeshDict)."
        ),
        "plane": tr(
            "Through the centre of the mesh, across its thinnest direction (from "
            "blockMeshDict) — a 2-D case's mid-plane."
        ),
        "planes": tr("Moved to the centre of the mesh (from blockMeshDict)."),
    }.get(reason, "")
    if background:
        text += " " + tr(
            "This is snappyHexMesh's background box: check the 3-D view that it "
            "is in the fluid, not inside a solid body."
        )
    return text


def _kind_placeholder(kind: str) -> str:
    return {
        "fields": tr("field names, e.g. p U"),
        "field": tr("a field name, e.g. p"),
        "patches": tr("patch names, e.g. inlet outlet"),
        "patch": tr("a patch name"),
        "points": tr("one point per line: x y z"),
        "vector": tr("x y z"),
        "number": tr("a number"),
    }.get(kind, "")


def _kind_hint(kind: str) -> str:
    return {
        "fields": tr("Field names, separated by spaces. ▾ lists this case's fields."),
        "field": tr("▾ lists this case's fields."),
        "patches": tr("Patch names, separated by spaces. ▾ lists this case's patches."),
        "patch": tr("▾ lists this case's patches."),
        "points": tr("One point per line, as x y z, in the mesh's coordinates."),
        "vector": tr("Three numbers: x y z."),
    }.get(kind, "")


def _problem_sentence(key: str, code: str) -> str:
    message = {
        "empty": tr("{key}: enter a value."),
        "placeholder": tr("{key}: replace the <…> placeholder with a value."),
        "number": tr("{key}: a number is needed."),
        "vector": tr("{key}: three numbers are needed, as x y z."),
        "points": tr("{key}: each line needs three numbers, as x y z."),
        "names": tr("{key}: names only — letters, digits and _ . : + -."),
        "planes": tr(
            "{key}: each plane line needs a name and six numbers: name  px py pz  nx ny nz."
        ),
    }.get(code, tr("{key}: this value cannot be written."))
    return message.format(key=key)


def existing_names(case_dir: str, functions: set[str]) -> set[str]:
    """Names a new function object may not take in *case_dir*."""
    system = os.path.join(case_dir, "system")
    try:
        files = set(os.listdir(system))
    except OSError:
        files = set()
    return functions | files
