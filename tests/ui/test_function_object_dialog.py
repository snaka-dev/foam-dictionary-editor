# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tools > Add Function Object…: the dialog and the action that writes its result."""
from __future__ import annotations

import pytest
from PySide6.QtWidgets import QDialog, QLabel, QMessageBox, QWidget

from services.function_templates import list_templates
from tests.services.test_function_templates import FOUNDATION_FORCES, OPENCFD_PROBES
from ui.dialogs.function_object_dialog import FunctionObjectDialog, _NamesInput


@pytest.fixture
def etc(tmp_path):
    """A fake installation ``etc`` with three templates in two styles."""
    root = tmp_path / "install" / "etc" / "caseDicts" / "postProcessing"
    (root / "probes").mkdir(parents=True)
    (root / "probes" / "probes").write_text(OPENCFD_PROBES)
    (root / "probes" / "probes.cfg").write_text("type probes;\n")
    (root / "forces").mkdir()
    (root / "forces" / "forcesIncompressible").write_text(FOUNDATION_FORCES)
    (root / "solvers").mkdir()
    (root / "solvers" / "codey").write_text("const word a;\nconst word b;\n")
    return tmp_path / "install" / "etc"


@pytest.fixture
def dialog(qapp, etc, destroy_widget):
    root = etc / "caseDicts" / "postProcessing"
    dlg = FunctionObjectDialog(
        list_templates(str(root)), str(etc.parent),
        ["p", "U", "k"], ["inlet", "outlet", "walls"], {"probes"},
    )
    yield dlg
    destroy_widget(dlg)


def test_nothing_chosen_means_nothing_to_add(dialog):
    assert not dialog._ok.isEnabled()


def test_examples_prefill_and_a_taken_name_gets_a_free_one(dialog):
    assert dialog.select_template("probes", "probes")
    assert dialog.result_name() == "probes1"  # "probes" is taken in this case
    assert dialog._ok.isEnabled()
    assert dialog._inputs["probeLocations"].toPlainText() == "0 0 0"
    assert dialog.result_text() == OPENCFD_PROBES  # untouched: the template itself


def test_placeholders_must_be_filled_before_adding(dialog):
    dialog.select_template("forces", "forcesIncompressible")
    assert not dialog._ok.isEnabled()
    assert "patches: enter a value." in dialog._problem.text()
    dialog._inputs["patches"].edit.setText("walls")
    dialog._inputs["rhoInf"].setText("1.225")
    dialog._inputs["CofR"].setText("0 0")
    assert dialog._problem.text() == "CofR: three numbers are needed, as x y z."
    dialog._inputs["CofR"].setText("0 0 0")
    dialog._inputs["nPoints"].setText("100")
    assert dialog._ok.isEnabled()
    text = dialog.result_text()
    assert "patches     (walls); // Names of patches" in text
    assert "rhoInf      1.225;       // Far field density; e.g., 1.225 kg/m^3 for air" in text


def test_the_name_is_checked(dialog):
    dialog.select_template("forces", "forcesIncompressible")
    for name, ok in (("forces1", True), ("probes", False), ("2x", False)):
        dialog._name.setText(name)
        assert ("Name:" in dialog._problem.text()) is not ok


def test_the_picker_ticks_names_in_and_out(dialog):
    dialog.select_template("probes", "probes")
    picker = dialog._inputs["fields"]
    assert isinstance(picker, _NamesInput)
    assert picker.text() == "p U"
    picker._toggle("k")
    assert picker.text() == "p U k"
    picker._toggle("p")
    assert picker.text() == "U k"
    assert "fields (U k);" in dialog.result_text()


def test_search_filters_by_name_and_description(dialog):
    dialog._search.setText("pressure and viscous")
    visible = [
        dialog._tree.topLevelItem(i).text(0)
        for i in range(dialog._tree.topLevelItemCount())
        if not dialog._tree.topLevelItem(i).isHidden()
    ]
    assert visible == ["forces"]


def test_a_template_with_code_is_edited_as_text(dialog):
    dialog.select_template("solvers", "codey")
    assert dialog._inputs == {}
    assert not dialog._preview.isReadOnly()
    dialog._preview.setPlainText("edited\n")
    assert dialog.result_text() == "edited\n"


# ── the action ───────────────────────────────────────────────────────────────

_CONTROL = (
    "FoamFile { version 2.0; format ascii; class dictionary; object controlDict; }\n"
    "application icoFoam;\n\n// " + "*" * 73 + " //\n"
)


@pytest.fixture
def case(main_window, tmp_path, etc, monkeypatch):
    import ui.mixins._function_object_ops as ops

    case = tmp_path / "case"
    (case / "system").mkdir(parents=True)
    (case / "system" / "controlDict").write_text(_CONTROL)
    (case / "0").mkdir()
    (case / "0" / "p").write_text("FoamFile { object p; }\ninternalField uniform 0;\n")
    monkeypatch.setattr(ops, "foam_etc_dirs", lambda: (etc,))
    main_window._load_case_dir(str(case))
    return case


def _fill_probes(monkeypatch, name="probes"):
    def fake_exec(dlg):
        dlg.select_template("probes", "probes")
        dlg._name.setText(name)
        dlg._inputs["probeLocations"].setPlainText("0.05 0.05 0.005")
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(FunctionObjectDialog, "exec", fake_exec)


def test_adding_writes_the_file_and_the_include_func(main_window, case, monkeypatch):
    _fill_probes(monkeypatch)
    main_window._on_add_function_object_clicked()
    written = (case / "system" / "probes").read_text()
    assert "probeLocations\n(\n    (0.05 0.05 0.005)\n);" in written
    assert '#includeEtc "caseDicts/postProcessing/probes/probes.cfg"' in written
    control = (case / "system" / "controlDict").read_text()
    assert "functions\n{\n    #includeFunc probes\n}" in control
    assert main_window.state.current_file == str(case / "system" / "probes")
    assert main_window.file_list_panel.has_file(str(case / "system" / "probes"))
    assert "Added function object probes" in main_window.statusBar().currentMessage()


def test_a_second_one_goes_into_the_same_block(main_window, case, monkeypatch):
    _fill_probes(monkeypatch, "probesA")
    main_window._on_add_function_object_clicked()
    _fill_probes(monkeypatch, "probesB")
    main_window._on_add_function_object_clicked()
    control = (case / "system" / "controlDict").read_text()
    assert "    #includeFunc probesA\n    #includeFunc probesB\n}" in control
    assert control.count("functions") == 1


def test_refused_while_control_dict_has_unsaved_edits(main_window, case, monkeypatch):
    seen = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: seen.append(a[2]))
    main_window.state.file_dirty[str(case / "system" / "controlDict")] = True
    main_window._on_add_function_object_clicked()
    assert "unsaved edits" in seen[0]
    assert not (case / "system" / "probes").exists()


def test_no_installation(main_window, case, monkeypatch):
    import ui.mixins._function_object_ops as ops

    seen = []
    monkeypatch.setattr(ops, "foam_etc_dirs", lambda: ())
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: seen.append(a[1]))
    main_window._on_add_function_object_clicked()
    assert seen == ["No OpenFOAM installation found"]


def test_cancel_writes_nothing(main_window, case, monkeypatch):
    monkeypatch.setattr(FunctionObjectDialog, "exec", lambda dlg: QDialog.DialogCode.Rejected)
    main_window._on_add_function_object_clicked()
    assert sorted(p.name for p in (case / "system").iterdir()) == ["controlDict"]
    assert (case / "system" / "controlDict").read_text() == _CONTROL


def test_the_dialog_offers_the_cases_fields_and_takes_existing_names(main_window, case, monkeypatch):
    seen = {}

    def fake_exec(dlg):
        seen["fields"] = dlg._fields
        seen["taken"] = dlg._taken
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(FunctionObjectDialog, "exec", fake_exec)
    main_window._on_add_function_object_clicked()
    assert seen["fields"] == ["p"]
    assert "controlDict" in seen["taken"]  # a file in system/ is a taken name



def test_unknown_patches_are_flagged_but_not_refused(dialog):
    dialog.select_template("forces", "forcesIncompressible")
    dialog._inputs["patches"].edit.setText("patch1 walls")
    dialog._inputs["rhoInf"].setText("1")
    dialog._inputs["CofR"].setText("0 0 0")
    dialog._inputs["nPoints"].setText("10")
    assert dialog._ok.isEnabled()
    assert dialog._problem.text().startswith("Not patches of this case's mesh: patch1.")
    dialog._inputs["patches"].edit.setText("walls")
    assert dialog._problem.text() == ""


# ── phase 2: surfaces form, live preview, postProcess ────────────────────────

from tests.services.test_function_templates import OPENCFD_SURFACES  # noqa: E402


@pytest.fixture
def etc2(etc):
    root = etc / "caseDicts" / "postProcessing"
    (root / "visualization").mkdir()
    (root / "visualization" / "surfaces").write_text(OPENCFD_SURFACES)
    return etc


def _dialog(etc, **kw):
    root = etc / "caseDicts" / "postProcessing"
    return FunctionObjectDialog(
        list_templates(str(root)), str(etc.parent), ["p", "U"], ["walls"], set(), **kw
    )


def test_the_surfaces_form(qapp, etc2, destroy_widget):
    dlg = _dialog(etc2)
    try:
        dlg.select_template("visualization", "surfaces")
        widget = dlg._inputs["surfaces"]
        assert widget.planes.toPlainText() == "xNormal  0 0 0  1 0 0\nzNormal  0 0 2  0 0 1"
        assert "CAD" in widget.others.toPlainText()
        widget.planes.setPlainText("mid  0.05 0.05 0.005  0 0 1")
        widget.others.setPlainText("")
        assert dlg._ok.isEnabled()
        assert "point  (0.05 0.05 0.005);" in dlg.result_text()
        widget.planes.setPlainText("mid  0 0")
        assert "each plane line needs a name and six numbers" in dlg._problem.text()
    finally:
        destroy_widget(dlg)


def test_the_post_process_option(qapp, etc, destroy_widget):
    dlg = _dialog(etc, post_process="postProcess -func {name} -latestTime")
    try:
        dlg.select_template("probes", "probes")
        assert dlg._run_chk.text().endswith("postProcess -func probes -latestTime")
        assert not dlg.run_post_process()
        dlg._run_chk.setChecked(True)
        assert dlg.run_post_process()
    finally:
        destroy_widget(dlg)
    dlg = _dialog(etc)  # nothing to run it on: no option
    try:
        assert dlg._run_chk is None and not dlg.run_post_process()
    finally:
        destroy_widget(dlg)


def test_the_preview_signal_carries_the_file(qapp, etc, destroy_widget):
    dlg = _dialog(etc)
    seen = []
    dlg.preview_changed.connect(lambda name, text: seen.append((name, text)))
    try:
        dlg.select_template("probes", "probes")
        dlg._emit_preview()  # what the debounce timer calls
        assert seen[-1] == ("probes", dlg.result_text())
    finally:
        destroy_widget(dlg)


class _Panel(QWidget):
    """Stands in for the 3-D panel: a widget, as the tab lookup needs."""

    def __init__(self):
        super().__init__()
        self.calls = []

    def update_sampling(self, path, root, name=None):
        self.calls.append((path, name, [c.name for c in root.children]))


def test_the_live_preview_reaches_the_3d_view_and_is_cleared(main_window, case, monkeypatch):
    panel = _Panel()
    # Through monkeypatch, so the real panel is back before the window's
    # own teardown shuts it down.
    monkeypatch.setattr(main_window, "block_mesh_panel", panel)

    def fake_exec(dlg):
        dlg.select_template("probes", "probes")
        dlg._emit_preview()
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(FunctionObjectDialog, "exec", fake_exec)
    main_window._on_add_function_object_clicked()
    shown, cleared = panel.calls[0], panel.calls[-1]
    assert shown[0] == cleared[0] == "<function object preview>"
    assert shown[1] == "probes" and "probeLocations" in shown[2]
    assert cleared[2] == []  # the preview goes when the dialog does


def test_a_sampling_function_under_another_name_is_drawn(main_window, case, monkeypatch):
    from ui import viewer_dicts

    _fill_probes(monkeypatch, "probesAtInlet")
    main_window._on_add_function_object_clicked()
    config = main_window.state.case_files_config
    assert config.get_viewer_kind("system/probesAtInlet") == viewer_dicts.SAMPLING


def test_running_post_process_after_adding(main_window, case, monkeypatch):
    from tests.ui.test_tools_busy_terminal import _Terminal

    main_window.terminal_panel = _Terminal()
    (case / "0.5").mkdir()

    def fake_exec(dlg):
        dlg.select_template("probes", "probes")
        dlg._run_chk.setChecked(True)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(FunctionObjectDialog, "exec", fake_exec)
    main_window._on_add_function_object_clicked()
    assert main_window.terminal_panel.commands == [
        "postProcess -func probes -latestTime 2>&1 | tee log.postProcess"
    ]


def test_a_function_that_needs_the_solver_runs_through_it_after_adding(main_window, case, monkeypatch):
    """Plain postProcess -func forces would finish and calculate nothing."""
    from tests.ui.test_tools_busy_terminal import _Terminal

    (case / "0.5").mkdir()
    control = case / "system" / "controlDict"
    control.write_text(control.read_text().replace("application icoFoam;", "application simpleFoam;"))
    main_window._load_case_dir(str(case))
    main_window.terminal_panel = _Terminal()

    def fake_exec(dlg):
        dlg.select_template("forces", "forcesIncompressible")
        dlg._name.setText("drag")
        dlg._inputs["patches"].edit.setText("walls")
        dlg._inputs["rhoInf"].setText("1")
        dlg._inputs["CofR"].setText("0 0 0")
        dlg._inputs["nPoints"].setText("10")
        dlg._run_chk.setChecked(True)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(FunctionObjectDialog, "exec", fake_exec)
    main_window._on_add_function_object_clicked()
    assert main_window.terminal_panel.commands == [
        "simpleFoam -postProcess -func drag -latestTime 2>&1 | tee log.postProcess"
    ]


# ── starting places inside the domain ────────────────────────────────────────


def test_suggested_starting_places_and_their_note(qapp, etc, destroy_widget):
    from services.domain_bounds import DomainBounds
    from services.function_templates import suggest_values

    box = DomainBounds((0.0, 0.0, 0.0), (0.1, 0.1, 0.01), background=True)
    root = etc / "caseDicts" / "postProcessing"
    dlg = FunctionObjectDialog(
        list_templates(str(root)), str(etc.parent), [], [], set(),
        suggest=lambda parsed: suggest_values(parsed, box), background=True,
    )
    try:
        dlg.select_template("probes", "probes")
        assert dlg._inputs["probeLocations"].toPlainText() == "0.05 0.05 0.005"
        assert "probeLocations\n(\n    (0.05 0.05 0.005)\n);" in dlg.result_text()
        notes = [w.text() for w in dlg._form_area.widget().findChildren(QLabel)]
        assert any("centre of the mesh (from blockMeshDict)" in n and "background box" in n
                   for n in notes)
        dlg.select_template("forces", "forcesIncompressible")
        assert dlg._inputs["CofR"].text() == ""  # physics: no suggestion
    finally:
        destroy_widget(dlg)


def test_the_action_uses_the_cases_blockmesh(main_window, case, monkeypatch):
    (case / "system" / "blockMeshDict").write_text(
        "vertices ((0 0 0) (2 0 0) (2 1 0) (0 1 0) (0 0 1) (2 0 1) (2 1 1) (0 1 1));\n"
        "blocks ( hex (0 1 2 3 4 5 6 7) (1 1 1) simpleGrading (1 1 1) );\n"
    )
    seen = {}

    def fake_exec(dlg):
        dlg.select_template("probes", "probes")
        seen["probe"] = dlg._inputs["probeLocations"].toPlainText()
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(FunctionObjectDialog, "exec", fake_exec)
    main_window._on_add_function_object_clicked()
    assert seen["probe"] == "1 0.5 0.5"
