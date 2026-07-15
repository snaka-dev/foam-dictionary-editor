# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""
Tests for ui/dialogs/find_examples_dialog.py.
"""
from __future__ import annotations

import sys

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTreeWidgetItem

import ui.dialogs.find_examples_dialog as fed_module
from services.example_search import installation_from_dir
from ui.dialogs.find_examples_dialog import FindExamplesDialog

_CONTROL_DICT = """\
application     simpleFoam;

functions
{
    #includeFunc mag
}
"""


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])
    yield app


@pytest.fixture
def fake_install(tmp_path):
    root = tmp_path / "openfoam9999"
    case = root / "tutorials" / "incompressible" / "pitzDaily"
    (case / "system").mkdir(parents=True)
    (case / "system" / "controlDict").write_text(_CONTROL_DICT)
    fields = root / "etc" / "caseDicts" / "postProcessing" / "fields"
    fields.mkdir(parents=True)
    (fields / "mag").write_text("type            mag;\n")
    return root


@pytest.fixture
def dialog(qapp, fake_install, monkeypatch):
    installation = installation_from_dir(fake_install)
    assert installation is not None
    monkeypatch.setattr(
        fed_module, "discover_installations", lambda **kwargs: [installation]
    )
    dlg = FindExamplesDialog()
    yield dlg
    dlg.close()
    dlg.deleteLater()


def _run_search(qapp, dlg: FindExamplesDialog, query: str) -> None:
    dlg._query_edit.setText(query)
    dlg._on_search()
    assert dlg._thread is not None
    dlg._thread.wait(5000)
    qapp.processEvents()


def _leaf_items(dlg: FindExamplesDialog) -> list[QTreeWidgetItem]:
    leaves: list[QTreeWidgetItem] = []

    def walk(item: QTreeWidgetItem) -> None:
        if item.childCount() == 0:
            leaves.append(item)
        for i in range(item.childCount()):
            walk(item.child(i))

    for i in range(dlg._results.topLevelItemCount()):
        walk(dlg._results.topLevelItem(i))
    return leaves


def test_dialog_is_non_modal(dialog):
    assert dialog.windowModality() == Qt.WindowModality.NonModal


def test_installation_combo_populated(dialog):
    assert dialog._install_combo.count() == 1
    assert dialog._install_combo.itemText(0) == "openfoam9999"
    assert dialog._hint_label.isHidden()


def test_search_populates_grouped_results(qapp, dialog):
    _run_search(qapp, dialog, "mag")
    top_labels = [
        dialog._results.topLevelItem(i).text(0)
        for i in range(dialog._results.topLevelItemCount())
    ]
    assert top_labels == ["Tutorials", "caseDicts templates"]
    leaves = _leaf_items(dialog)
    assert len(leaves) == 2
    assert "matching file(s) found" in dialog._status_label.text()


def test_tutorial_hit_enables_compare_and_fills_preview(qapp, dialog, fake_install):
    _run_search(qapp, dialog, "mag")
    tutorial_leaf = next(
        item
        for item in _leaf_items(dialog)
        if item.data(0, Qt.ItemDataRole.UserRole).case_root is not None
    )
    dialog._results.setCurrentItem(tutorial_leaf)
    qapp.processEvents()
    assert "#includeFunc mag" in dialog._preview.toPlainText()
    assert dialog._compare_btn.isEnabled()
    assert dialog._copy_btn.isEnabled()
    # The label itself may be elided; the tooltip always holds the full path.
    assert str(fake_install) in dialog._path_label.toolTip()


def test_casedicts_hit_disables_compare(qapp, dialog):
    _run_search(qapp, dialog, "mag")
    template_leaf = next(
        item
        for item in _leaf_items(dialog)
        if item.data(0, Qt.ItemDataRole.UserRole).case_root is None
    )
    dialog._results.setCurrentItem(template_leaf)
    qapp.processEvents()
    assert not dialog._compare_btn.isEnabled()
    assert dialog._copy_btn.isEnabled()


def test_copy_file_puts_preview_on_clipboard(qapp, dialog):
    _run_search(qapp, dialog, "mag")
    dialog._results.setCurrentItem(_leaf_items(dialog)[0])
    qapp.processEvents()
    dialog._on_copy_file()
    assert "mag" in QApplication.clipboard().text()


def test_copy_selection_follows_preview_selection(qapp, dialog):
    _run_search(qapp, dialog, "mag")
    dialog._results.setCurrentItem(_leaf_items(dialog)[0])
    qapp.processEvents()
    assert not dialog._copy_selection_btn.isEnabled()
    dialog._preview.selectAll()
    qapp.processEvents()
    assert dialog._copy_selection_btn.isEnabled()
    dialog._on_copy_selection()
    assert "mag" in QApplication.clipboard().text()


def test_path_label_cannot_force_pane_width(qapp, dialog):
    from PySide6.QtWidgets import QSizePolicy

    policy = dialog._path_label.sizePolicy()
    assert policy.horizontalPolicy() == QSizePolicy.Policy.Ignored


def test_compare_emits_case_root(qapp, dialog, fake_install):
    _run_search(qapp, dialog, "mag")
    tutorial_leaf = next(
        item
        for item in _leaf_items(dialog)
        if item.data(0, Qt.ItemDataRole.UserRole).case_root is not None
    )
    dialog._results.setCurrentItem(tutorial_leaf)
    qapp.processEvents()
    received: list[str] = []
    dialog.compare_requested.connect(received.append)
    dialog._on_compare()
    expected = str(fake_install / "tutorials" / "incompressible" / "pitzDaily")
    assert received == [expected]


def test_no_matches_message(qapp, dialog):
    _run_search(qapp, dialog, "definitely-not-present")
    assert _leaf_items(dialog) == []
    assert "No matches" in dialog._status_label.text()


def test_blank_query_shows_hint_without_thread(dialog):
    dialog._query_edit.setText("   ")
    dialog._on_search()
    assert dialog._thread is None
    assert "keyword" in dialog._status_label.text().lower()


def test_no_sources_selected_shows_hint(dialog):
    dialog._tutorials_cb.setChecked(False)
    dialog._casedicts_cb.setChecked(False)
    dialog._query_edit.setText("mag")
    dialog._on_search()
    assert dialog._thread is None
    assert "source" in dialog._status_label.text().lower()


def test_file_filter_limits_results(qapp, dialog):
    dialog._file_filter.setCurrentText("controlDict")
    _run_search(qapp, dialog, "mag")
    leaves = _leaf_items(dialog)
    assert len(leaves) == 1
    hit = leaves[0].data(0, Qt.ItemDataRole.UserRole)
    assert hit.file.name == "controlDict"
