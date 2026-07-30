# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Non-modal browser that searches example usages of OpenFOAM keywords in the
tutorials and etc/caseDicts of a local installation (services/example_search).
Kept non-modal, like LogSummaryDialog, so it can sit beside the main window
while the tree/editor stay usable."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from i18n import tr
from services.example_search import (
    SOURCE_CASEDICTS,
    SOURCE_TUTORIALS,
    FoamInstallation,
    SearchHit,
    search_examples,
)
from ui.dialogs._worker_thread import _CancellableWorkerThread
from ui.widgets.code_editor import CodeEditor
from ui.widgets.installation_selector import InstallationSelector

_DIALOG_WIDTH = 900
_DIALOG_HEIGHT = 600

_FILE_FILTERS = (
    "controlDict",
    "fvSchemes",
    "fvSolution",
    "blockMeshDict",
    "snappyHexMeshDict",
    "topoSetDict",
    "transportProperties",
    "turbulenceProperties",
)


def _case_label(hit: SearchHit) -> str:
    """Display label of the hit's case directory, relative to the tutorials root."""
    assert hit.case_root is not None
    depth = len(hit.file.relative_to(hit.case_root).parts)
    parts = Path(hit.rel_label).parts[:-depth]
    return str(Path(*parts)) if parts else hit.case_root.name


class _SearchThread(_CancellableWorkerThread):
    finished_ok = Signal(list)   # list[SearchHit]

    def __init__(
        self,
        installation: FoamInstallation,
        query: str,
        sources: tuple[str, ...],
        file_name: str | None,
    ) -> None:
        super().__init__()
        self._installation = installation
        self._query = query
        self._sources = sources
        self._file_name = file_name

    def run(self) -> None:
        try:
            hits = search_examples(
                self._installation,
                self._query,
                sources=self._sources,  # type: ignore[arg-type]
                file_name=self._file_name,
                progress=lambda msg: self.progress.emit(msg),
                cancelled=lambda: self._cancelled,
            )
            self.finished_ok.emit(hits)
        except Exception as exc:
            self.finished_err.emit(str(exc))


class FindExamplesDialog(QDialog):
    """Non-modal dialog to search OpenFOAM tutorials/caseDicts for examples."""

    compare_requested = Signal(str)    # absolute path of a tutorial case root
    duplicate_requested = Signal(str)  # absolute path of a tutorial case root

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Find OpenFOAM Examples"))
        self.resize(_DIALOG_WIDTH, _DIALOG_HEIGHT)
        self.setWindowModality(Qt.WindowModality.NonModal)

        self._thread: _SearchThread | None = None

        layout = QVBoxLayout(self)

        # ── installation row ──────────────────────────────────────────────
        install_row = QHBoxLayout()
        install_row.addWidget(QLabel(tr("OpenFOAM installation:")))
        self._install_selector = InstallationSelector()
        self._install_selector.installations_available.connect(
            self._on_installations_available
        )
        self._install_selector.error.connect(self._on_selector_error)
        self._install_combo = self._install_selector.combo  # kept for tests
        install_row.addWidget(self._install_selector, 1)
        layout.addLayout(install_row)

        self._hint_label = QLabel(
            tr("No OpenFOAM installation found — browse to one to enable searching.")
        )
        self._hint_label.hide()
        layout.addWidget(self._hint_label)

        # ── search row ────────────────────────────────────────────────────
        search_row = QHBoxLayout()
        self._query_edit = QLineEdit()
        self._query_edit.setPlaceholderText(tr("Keyword or setting, e.g. #includeFunc"))
        self._query_edit.setClearButtonEnabled(True)
        self._query_edit.returnPressed.connect(self._on_search)
        search_row.addWidget(self._query_edit, 1)
        self._file_filter = QComboBox()
        self._file_filter.setEditable(True)
        self._file_filter.addItem(tr("All files"))
        self._file_filter.addItems(_FILE_FILTERS)
        search_row.addWidget(self._file_filter)
        self._tutorials_cb = QCheckBox(tr("Tutorials"))
        self._tutorials_cb.setChecked(True)
        search_row.addWidget(self._tutorials_cb)
        self._casedicts_cb = QCheckBox(tr("caseDicts templates"))
        self._casedicts_cb.setChecked(True)
        search_row.addWidget(self._casedicts_cb)
        self._search_btn = QPushButton(tr("Search"))
        self._search_btn.clicked.connect(self._on_search)
        search_row.addWidget(self._search_btn)
        self._cancel_btn = QPushButton(tr("Cancel"))
        self._cancel_btn.clicked.connect(self._on_cancel)
        self._cancel_btn.hide()
        search_row.addWidget(self._cancel_btn)
        layout.addLayout(search_row)

        # ── results + preview ─────────────────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._results = QTreeWidget()
        self._results.setColumnCount(2)
        self._results.setHeaderLabels([tr("File"), tr("First match")])
        self._results.setColumnWidth(0, 320)
        self._results.currentItemChanged.connect(self._on_result_selected)
        splitter.addWidget(self._results)

        preview_box = QWidget()
        preview_layout = QVBoxLayout(preview_box)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        self._path_text = ""
        self._path_label = QLabel("")
        self._path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        # Ignored horizontal policy + middle-elided text: a long absolute path
        # must not become the pane's minimum width and squeeze the results tree.
        self._path_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        preview_layout.addWidget(self._path_label)
        self._preview = CodeEditor()
        self._preview.setReadOnly(True)
        preview_layout.addWidget(self._preview)
        splitter.addWidget(preview_box)
        splitter.setSizes([_DIALOG_WIDTH // 2, _DIALOG_WIDTH // 2])
        layout.addWidget(splitter, 1)

        # ── bottom row ────────────────────────────────────────────────────
        bottom_row = QHBoxLayout()
        self._copy_btn = QPushButton(tr("Copy File"))
        self._copy_btn.setEnabled(False)
        self._copy_btn.clicked.connect(self._on_copy_file)
        bottom_row.addWidget(self._copy_btn)
        self._copy_selection_btn = QPushButton(tr("Copy Selection"))
        self._copy_selection_btn.setEnabled(False)
        self._copy_selection_btn.clicked.connect(self._on_copy_selection)
        bottom_row.addWidget(self._copy_selection_btn)
        self._preview.selectionChanged.connect(self._on_preview_selection_changed)
        self._compare_btn = QPushButton(tr("Compare with this case"))
        self._compare_btn.setEnabled(False)
        self._compare_btn.clicked.connect(self._on_compare)
        bottom_row.addWidget(self._compare_btn)
        self._duplicate_btn = QPushButton(tr("Duplicate this case…"))
        self._duplicate_btn.setEnabled(False)
        self._duplicate_btn.clicked.connect(self._on_duplicate)
        bottom_row.addWidget(self._duplicate_btn)
        self._status_label = QLabel("")
        bottom_row.addWidget(self._status_label, 1)
        close_btn = QPushButton(tr("Close"))
        close_btn.clicked.connect(self.close)
        bottom_row.addWidget(close_btn)
        layout.addLayout(bottom_row)

        self._install_selector.refresh()

    # ── installations ─────────────────────────────────────────────────────

    def _on_installations_available(self, available: bool) -> None:
        self._hint_label.setVisible(not available)
        if available:
            self._status_label.setText("")

    def _on_selector_error(self, msg: str) -> None:
        self._status_label.setText(msg)

    def _current_installation(self) -> FoamInstallation | None:
        return self._install_selector.current_installation()

    # ── search ────────────────────────────────────────────────────────────

    def _selected_sources(self) -> tuple[str, ...]:
        sources: list[str] = []
        if self._tutorials_cb.isChecked():
            sources.append(SOURCE_TUTORIALS)
        if self._casedicts_cb.isChecked():
            sources.append(SOURCE_CASEDICTS)
        return tuple(sources)

    def _selected_file_name(self) -> str | None:
        text = self._file_filter.currentText().strip()
        if not text or text == tr("All files"):
            return None
        return text

    def _on_search(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            return
        installation = self._current_installation()
        if installation is None:
            self._status_label.setText(tr("Select an OpenFOAM installation first."))
            return
        query = self._query_edit.text().strip()
        if not query:
            self._status_label.setText(tr("Enter a search keyword."))
            return
        sources = self._selected_sources()
        if not sources:
            self._status_label.setText(tr("Select at least one source to search."))
            return

        self._results.clear()
        self._preview.setPlainText("")
        self._set_path_text("")
        self._copy_btn.setEnabled(False)
        self._copy_selection_btn.setEnabled(False)
        self._compare_btn.setEnabled(False)
        self._duplicate_btn.setEnabled(False)
        self._search_btn.hide()
        self._cancel_btn.show()
        self._cancel_btn.setEnabled(True)
        self._status_label.setText(tr("Searching…"))

        self._thread = _SearchThread(
            installation, query, sources, self._selected_file_name()
        )
        self._thread.progress.connect(self._status_label.setText)
        self._thread.finished_ok.connect(self._on_results_ready)
        self._thread.finished_err.connect(self._on_search_error)
        self._thread.start()

    def _on_cancel(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            self._thread.cancel()
            self._cancel_btn.setEnabled(False)
            self._status_label.setText(tr("Cancelling…"))

    def _finish_search(self) -> None:
        self._cancel_btn.hide()
        self._search_btn.show()
        self._thread = None

    def _on_results_ready(self, hits: list[SearchHit]) -> None:
        self._finish_search()
        tutorials_root: QTreeWidgetItem | None = None
        casedicts_root: QTreeWidgetItem | None = None
        case_items: dict[str, QTreeWidgetItem] = {}
        for hit in hits:
            if hit.source == SOURCE_TUTORIALS:
                if tutorials_root is None:
                    tutorials_root = QTreeWidgetItem(self._results, [tr("Tutorials")])
                    tutorials_root.setExpanded(True)
                if hit.case_root is not None:
                    case_label = _case_label(hit)
                    parent = case_items.get(case_label)
                    if parent is None:
                        parent = QTreeWidgetItem(tutorials_root, [case_label])
                        case_items[case_label] = parent
                    label = str(hit.file.relative_to(hit.case_root))
                else:
                    parent = tutorials_root
                    label = hit.rel_label
            else:
                if casedicts_root is None:
                    casedicts_root = QTreeWidgetItem(
                        self._results, [tr("caseDicts templates")]
                    )
                    casedicts_root.setExpanded(True)
                parent = casedicts_root
                label = hit.rel_label
            item = QTreeWidgetItem(parent, [label, hit.snippet])
            item.setData(0, Qt.ItemDataRole.UserRole, hit)
            item.setToolTip(0, str(hit.file))
        if hits:
            self._status_label.setText(
                tr("{count} matching file(s) found.").format(count=len(hits))
            )
        else:
            self._status_label.setText(tr("No matches found."))

    def _on_search_error(self, msg: str) -> None:
        self._finish_search()
        self._status_label.setText(tr("Search failed: {msg}").format(msg=msg))

    # ── result selection / actions ────────────────────────────────────────

    def _current_hit(self) -> SearchHit | None:
        item = self._results.currentItem()
        if item is None:
            return None
        data = item.data(0, Qt.ItemDataRole.UserRole)
        return data if isinstance(data, SearchHit) else None

    def _on_result_selected(self) -> None:
        hit = self._current_hit()
        if hit is None:
            self._copy_btn.setEnabled(False)
            self._compare_btn.setEnabled(False)
            self._duplicate_btn.setEnabled(False)
            return
        try:
            text = hit.file.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            self._status_label.setText(tr("Could not read file: {msg}").format(msg=exc))
            return
        self._preview.setPlainText(text)
        if hit.line_numbers:
            first = hit.line_numbers[0]
            self._preview.set_span_highlight(first, first)
            self._preview.goto_line(first)
        self._set_path_text(
            tr("{path}  ({count} matching line(s))").format(
                path=str(hit.file), count=len(hit.line_numbers)
            )
        )
        self._copy_btn.setEnabled(True)
        self._compare_btn.setEnabled(hit.case_root is not None)
        self._duplicate_btn.setEnabled(hit.case_root is not None)

    def _set_path_text(self, text: str) -> None:
        self._path_text = text
        self._path_label.setToolTip(text)
        self._refresh_path_label()

    def _refresh_path_label(self) -> None:
        metrics = self._path_label.fontMetrics()
        width = max(self._path_label.width() - 4, 50)
        self._path_label.setText(
            metrics.elidedText(self._path_text, Qt.TextElideMode.ElideMiddle, width)
        )

    def _on_preview_selection_changed(self) -> None:
        self._copy_selection_btn.setEnabled(self._preview.textCursor().hasSelection())

    def _on_copy_file(self) -> None:
        QApplication.clipboard().setText(self._preview.toPlainText())
        self._status_label.setText(tr("File contents copied."))

    def _on_copy_selection(self) -> None:
        selected = self._preview.textCursor().selectedText()
        if not selected:
            return
        # QTextCursor uses U+2029 as the paragraph separator in selections
        QApplication.clipboard().setText(selected.replace("\u2029", "\n"))
        self._status_label.setText(tr("Selection copied."))

    def _on_compare(self) -> None:
        hit = self._current_hit()
        if hit is None or hit.case_root is None:
            return
        self.compare_requested.emit(str(hit.case_root))

    def _on_duplicate(self) -> None:
        hit = self._current_hit()
        if hit is None or hit.case_root is None:
            return
        self.duplicate_requested.emit(str(hit.case_root))

    # ── cleanup ───────────────────────────────────────────────────────────

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh_path_label()

    def closeEvent(self, event) -> None:
        if self._thread is not None and self._thread.isRunning():
            self._thread.cancel()
            self._thread.wait(2000)
        super().closeEvent(event)
