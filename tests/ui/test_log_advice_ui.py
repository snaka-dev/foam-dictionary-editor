# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""View Log Summary's advice: the sentences, the dialog pane and its links.

The matching itself is tests/services/test_log_advice.py.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl

from services import log_advice as la
from ui.dialogs.log_summary_dialog import LogSummaryDialog
from ui.log_advice_text import advice_text, advice_title

_ARGS = {
    "patch": "inlet", "field": "U", "what": "patchField", "name": "noSlp", "suggestion": "noSlip",
    "patch_type": "empty", "field_type": "zeroGradient", "key": "deltaT", "dict": "system/controlDict",
    "present": "yes", "path": "0/p", "orig": "0.orig", "count": "4", "n": "2 1 1", "product": "2",
    "want": "4", "got": "2", "message": "Found { but expected }", "courant": "12.5", "time": "0.3",
}


def test_every_code_has_a_title_and_a_text():
    for code in la.ADVICE_CODES:
        advice = la.Advice(code, dict(_ARGS))
        for text in (advice_title(advice), advice_text(advice)):
            assert text and text != code, code
            assert "{" not in text.replace("{ but", ""), (code, text)


def test_variants():
    assert "noSlip" in advice_text(la.Advice(la.UNKNOWN_NAME, dict(_ARGS)))
    assert "noSlip" not in advice_text(la.Advice(la.UNKNOWN_NAME, {**_ARGS, "suggestion": ""}))
    assert "';'" in advice_text(la.Advice(la.MISSING_ENTRY, dict(_ARGS)))
    assert "Restore" in advice_text(la.Advice(la.MISSING_FILE, dict(_ARGS)))
    assert "Restore" not in advice_text(la.Advice(la.MISSING_FILE, {**_ARGS, "orig": ""}))
    assert "12.5" in advice_text(la.Advice(la.FLOATING_POINT, dict(_ARGS)))
    assert "checkMesh" in advice_text(la.Advice(la.FLOATING_POINT, {**_ARGS, "courant": ""}))


_LOG = (
    "Exec   : icoFoam\n"
    "--> FOAM FATAL IO ERROR: (openfoam-2606)\nCannot find patchField entry for movingWall\n\n"
    "file: 0/U/boundaryField at line 3 to 9.\n\nFOAM exiting\n"
)


def _case(tmp_path: Path, log: str = _LOG) -> Path:
    (tmp_path / "0").mkdir()
    (tmp_path / "0" / "U").write_text("a\nb\nboundaryField\n{\n}\n")
    (tmp_path / "log.icoFoam").write_text(log)
    return tmp_path


def test_dialog_shows_advice_and_opens_the_file(qtbot, tmp_path: Path):
    case = _case(tmp_path)
    dialog = LogSummaryDialog(str(case))
    qtbot.addWidget(dialog)
    assert [a.code for a in dialog.advice()] == [la.MISSING_PATCH_ENTRY]
    assert not dialog._advice_view.isHidden()
    assert "movingWall" in dialog._advice_view.toPlainText()
    assert "Open U at line 3" in dialog._advice_view.toPlainText()

    opened = []
    dialog.open_requested.connect(lambda path, line: opened.append((path, line)))
    dialog._on_advice_link(QUrl("open:0"))
    assert opened == [(str(case / "0" / "U"), 3)]
    dialog._on_advice_link(QUrl("open:7"))  # stale index: nothing
    assert len(opened) == 1


def test_dialog_hides_advice_for_a_clean_log(qtbot, tmp_path: Path):
    case = _case(tmp_path, "Exec   : icoFoam\nTime = 1\n\nEnd\n")
    dialog = LogSummaryDialog(str(case))
    qtbot.addWidget(dialog)
    assert dialog.advice() == []
    assert dialog._advice_view.isHidden()


def test_main_window_opens_advice_files(main_window, tmp_path: Path):
    win = main_window
    case = _case(tmp_path)
    win._load_case_dir(str(case))
    win._on_view_log_summary_clicked()
    dialog = win._log_summary_dialog
    assert dialog is not None
    dialog._on_advice_link(QUrl("open:0"))
    assert win.state.current_file == str(case / "0" / "U")
    assert win.editor_panel.current_line_number() == 3
