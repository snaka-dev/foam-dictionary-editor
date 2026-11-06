# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tools-menu actions against a busy terminal, Run reconstructPar…, and
Delete processor* Directories… (ui/mixins/_tools_ops.py).

A command sent while another runs only queues behind it -- or, in xterm mode,
is typed into it, where mpirun swallows it -- so every terminal action refuses
first. Deleting processor* is checked file by file before anything goes.
"""
from __future__ import annotations

import pytest
from PySide6.QtWidgets import QDialog, QMessageBox, QWidget

from tests.services._processor_cases import _reconstructed_case
from ui.dialogs.run_tool_dialog import RunToolDialog


class _Terminal(QWidget):
    def __init__(self, running=()):
        super().__init__()
        self.running = list(running)
        self.commands: list[str] = []

    def running_commands(self):
        return self.running

    def run_command(self, cmd):
        self.commands.append(cmd)

    def cleanup(self):
        pass


@pytest.fixture
def win(main_window, tmp_path):
    main_window.state.current_case_dir = str(tmp_path)
    main_window.terminal_panel = _Terminal()
    return main_window


@pytest.fixture
def boxes(monkeypatch):
    """Record every message box; question() answers Yes unless told otherwise."""
    seen: dict = {"warning": [], "information": [], "question": [], "answer": True}

    def record(kind):
        def box(parent, title, text, *a, **k):
            seen[kind].append((title, text))
            if kind == "question":
                return (
                    QMessageBox.StandardButton.Yes
                    if seen["answer"]
                    else QMessageBox.StandardButton.No
                )
            return QMessageBox.StandardButton.Ok

        return box

    for kind in ("warning", "information", "question"):
        monkeypatch.setattr(QMessageBox, kind, record(kind))
    monkeypatch.setattr(
        RunToolDialog, "exec", lambda self: QDialog.DialogCode.Accepted
    )
    return seen


# ── a busy terminal refuses every terminal action ────────────────────────────

ACTIONS = [
    "_on_run_blockmesh_clicked",
    "_on_run_snappyhexmesh_clicked",
    "_on_run_topo_set_clicked",
    "_on_run_setfields_clicked",
    "_on_run_checkmesh_clicked",
    "_on_run_solver_clicked",
    "_on_run_allrun_clicked",
    "_on_run_allclean_clicked",
    "_on_clean_case_clicked",
    "_on_restore_0dir_clicked",
]


@pytest.mark.parametrize("action", ACTIONS)
def test_busy_terminal_refuses(win, boxes, tmp_path, action):
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "controlDict").write_text("application icoFoam;\n")
    (tmp_path / "0.orig").mkdir()
    for script in ("Allrun", "Allclean"):
        (tmp_path / script).write_text("#!/bin/sh\n")
    win.terminal_panel.running = ["simpleFoam"]
    getattr(win, action)()
    assert win.terminal_panel.commands == []
    assert len(boxes["warning"]) == 1
    assert "simpleFoam is still running" in boxes["warning"][0][1]


def test_idle_terminal_runs(win, boxes):
    win._on_run_blockmesh_clicked()
    assert win.terminal_panel.commands == ["blockMesh 2>&1 | tee log.blockMesh"]
    assert boxes["warning"] == []


# ── Run reconstructPar… ──────────────────────────────────────────────────────


def test_reconstructpar_needs_a_decomposed_case(win, boxes):
    win._on_run_reconstructpar_clicked()
    assert win.terminal_panel.commands == []
    assert boxes["warning"][0][0] == "Case not decomposed"


def test_reconstructpar_default_command_and_pending_times(win, boxes, tmp_path, monkeypatch):
    (tmp_path / "processor0" / "0.5").mkdir(parents=True)
    seen = {}
    real_init = RunToolDialog.__init__

    def spy(self, spec, case_dir, last=None, warning="", *a, **k):
        seen["warning"] = warning
        real_init(self, spec, case_dir, last, warning, *a, **k)

    monkeypatch.setattr(RunToolDialog, "__init__", spy)
    win._on_run_reconstructpar_clicked()
    assert "0.5" in seen["warning"]
    assert win.terminal_panel.commands == [
        "reconstructPar -newTimes 2>&1 | tee log.reconstructPar"
    ]


def test_reconstructpar_refuses_while_running(win, boxes, tmp_path):
    (tmp_path / "processor0").mkdir()
    win.terminal_panel.running = ["mpirun"]
    win._on_run_reconstructpar_clicked()
    assert win.terminal_panel.commands == []
    assert "mpirun is still running" in boxes["warning"][0][1]


# ── Delete processor* Directories… ───────────────────────────────────────────


@pytest.fixture
def confirm(monkeypatch):
    """Answer the deletion confirmation without showing it.

    ``confirm["keep"]`` sets the keep-latest checkbox before answering (None
    leaves it as the dialog set it); ``confirm["box"]`` records what was shown.
    """
    state: dict = {"answer": True, "keep": None, "box": None}

    def fake_exec(box):
        state["box"] = {
            "text": box.text(),
            "chk": None if box.checkBox() is None else {
                "text": box.checkBox().text(),
                "checked": box.checkBox().isChecked(),
                "enabled": box.checkBox().isEnabled(),
            },
        }
        if state["keep"] is not None and box.checkBox() is not None:
            box.checkBox().setChecked(state["keep"])
        button = QMessageBox.StandardButton.Yes if state["answer"] else QMessageBox.StandardButton.No
        return button.value

    monkeypatch.setattr(QMessageBox, "exec", fake_exec)
    return state


def _proc_names(case, n):
    return sorted(p.name for p in (case / f"processor{n}").iterdir())


def test_keep_latest_is_offered_and_ticked_by_default(win, boxes, confirm, tmp_path):
    _reconstructed_case(tmp_path)
    win._on_delete_processor_dirs_clicked()
    chk = confirm["box"]["chk"]
    assert chk["checked"] and chk["enabled"] and "(1)" in chk["text"]
    assert "cannot be undone" in confirm["box"]["text"]
    assert _proc_names(tmp_path, 0) == ["1", "constant"]
    assert _proc_names(tmp_path, 1) == ["1", "constant"]


def test_unticking_deletes_everything(win, boxes, confirm, tmp_path):
    _reconstructed_case(tmp_path)
    confirm["keep"] = False
    win._on_delete_processor_dirs_clicked()
    assert not (tmp_path / "processor0").exists()
    assert not (tmp_path / "processor1").exists()
    assert (tmp_path / "1" / "U").exists()  # the root copy is untouched


def test_declining_deletes_nothing(win, boxes, confirm, tmp_path):
    _reconstructed_case(tmp_path)
    confirm["answer"] = False
    win._on_delete_processor_dirs_clicked()
    assert _proc_names(tmp_path, 0) == ["0", "0.5", "1", "constant"]


def test_root_ahead_of_the_processors_starts_unticked(win, boxes, confirm, tmp_path):
    _reconstructed_case(tmp_path)
    (tmp_path / "2").mkdir()  # a serial run carried on after reconstructing
    win._on_delete_processor_dirs_clicked()
    assert confirm["box"]["chk"]["checked"] is False
    assert "later time (2)" in confirm["box"]["text"]


def test_mesh_only_in_processors_locks_keep_on(win, boxes, confirm, tmp_path):
    import shutil

    _reconstructed_case(tmp_path)
    shutil.rmtree(tmp_path / "constant" / "polyMesh")
    confirm["keep"] = False  # a user cannot untick it -- but even if they could…
    win._on_delete_processor_dirs_clicked()
    chk = confirm["box"]["chk"]
    assert chk["checked"] and not chk["enabled"]
    assert "reconstructParMesh" in confirm["box"]["text"]
    # The only copy of the mesh survives; only earlier times went.
    assert (tmp_path / "processor0" / "constant" / "polyMesh" / "owner").exists()
    assert _proc_names(tmp_path, 0) == ["1", "constant"]


def test_data_only_in_processors_is_refused_without_asking(win, boxes, confirm, tmp_path):
    import shutil

    _reconstructed_case(tmp_path)
    shutil.rmtree(tmp_path / "0.5")
    (tmp_path / "0" / "p").unlink()
    win._on_delete_processor_dirs_clicked()
    assert _proc_names(tmp_path, 0) == ["0", "0.5", "1", "constant"]
    assert confirm["box"] is None  # never even offered
    text = boxes["warning"][0][1]
    assert "time 0.5 exists only in processor*" in text
    assert "time 0: p exist only in processor*" in text
    assert "Nothing was deleted." in text


def test_long_problem_lists_are_capped(win, boxes, confirm, tmp_path):
    for n in range(20):
        (tmp_path / "processor0" / f"{n + 1}").mkdir(parents=True)
    win._on_delete_processor_dirs_clicked()
    text = boxes["warning"][0][1]
    assert text.count("exists only in processor*") == 12
    assert "and 7 more" in text  # the 20th, the latest, is the kept one


def test_delete_refuses_while_running(win, boxes, confirm, tmp_path):
    _reconstructed_case(tmp_path)
    win.terminal_panel.running = ["simpleFoam"]
    win._on_delete_processor_dirs_clicked()
    assert (tmp_path / "processor0" / "0.5").exists()
    assert confirm["box"] is None


def test_delete_with_nothing_to_delete(win, boxes):
    win._on_delete_processor_dirs_clicked()
    assert boxes["information"][0][0] == "Nothing to delete"


def test_delete_works_without_a_terminal(win, boxes, confirm, tmp_path):
    _reconstructed_case(tmp_path)
    win.terminal_panel = None
    confirm["keep"] = False
    win._on_delete_processor_dirs_clicked()
    assert not (tmp_path / "processor0").exists()


def test_no_times_in_processors_offers_whole_deletion_only(win, boxes, confirm, tmp_path):
    from tests.services._processor_cases import _owner

    _owner(tmp_path / "constant" / "polyMesh", 8)
    _owner(tmp_path / "processor0" / "constant" / "polyMesh", 8)
    win._on_delete_processor_dirs_clicked()
    assert confirm["box"]["chk"] is None
    assert not (tmp_path / "processor0").exists()


@pytest.mark.parametrize(
    "kind, expected",
    [
        ("collated", "collated format"),
        ("mesh_missing", "reconstructParMesh"),
        ("mesh_unknown", "could not be read"),
    ],
)
def test_every_problem_kind_has_a_sentence(win, kind, expected):
    from services.solver_run import DeletionProblem

    assert expected in win._describe_deletion_problem(DeletionProblem(kind))


def test_confirmation_text_follows_the_checkbox(win, tmp_path):
    """One action and one size at a time, the question first; rewritten on toggle."""
    from foam.utils import format_size
    from services.solver_run import check_processor_deletion

    _reconstructed_case(tmp_path)
    whole = check_processor_deletion(str(tmp_path))
    keep = check_processor_deletion(str(tmp_path), keep_latest=True)
    box, chk = win._processor_delete_box(whole, keep)
    assert chk.text() == "Keep the latest time (1) and the decomposed mesh"

    text = box.text()
    first = text.split("\n\n")[0]
    assert first == f"Permanently delete {format_size(keep.total_bytes)} from the processor* directories?"
    assert "Kept: the latest time (1)" in text
    assert format_size(whole.total_bytes) not in text  # only the size that applies
    assert text.endswith("This cannot be undone.")

    chk.setChecked(False)
    text = box.text()
    assert text.split("\n\n")[0] == (
        f"Permanently delete the processor* directories entirely ({format_size(whole.total_bytes)})?"
    )
    assert "will need decomposePar again" in text and "Kept:" not in text

    chk.setChecked(True)
    assert box.text().split("\n\n")[0].startswith(
        f"Permanently delete {format_size(keep.total_bytes)}"
    )


# ── regression: the SIGBUS crash after confirming a deletion ─────────────────


def test_the_checkbox_is_owned_by_the_box_not_by_python(win, tmp_path):
    """PySide6's setCheckBox does not transfer ownership; parenting does.

    A Python-owned checkbox inside a Qt-owned box has two owners, and the
    garbage collector later destroyed one C++ had already freed: the box
    crashed FoDE with SIGBUS shortly after a deletion was confirmed.
    """
    from shiboken6 import Shiboken

    from services.solver_run import check_processor_deletion

    _reconstructed_case(tmp_path)
    box, chk = win._processor_delete_box(
        check_processor_deletion(str(tmp_path)),
        check_processor_deletion(str(tmp_path), keep_latest=True),
    )
    assert chk.parent() is not None
    assert not Shiboken.ownedByPython(chk)
    box.deleteLater()


_CRASH_SCRIPT = r"""
import gc, sys
from pathlib import Path
sys.path.insert(0, sys.argv[2])
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox
from tests.services._processor_cases import _reconstructed_case

case = Path(sys.argv[1])
_reconstructed_case(case, times=("0", "0.5", "1"))
app = QApplication([])
from app_config import get_app_config
cfg = get_app_config()
cfg.set_feature("terminal", False)
cfg.set_feature("blockmesh", False)
from ui.main_window import MainWindow
w = MainWindow()
w._load_case_dir(str(case))

def click_yes():
    for top in app.topLevelWidgets():
        if isinstance(top, QMessageBox) and top.isVisible():
            top.button(QMessageBox.StandardButton.Yes).click()
            return
    QTimer.singleShot(20, click_yes)

for _ in range(3):  # the real menu action, the real dialog, then a collection
    QTimer.singleShot(20, click_yes)
    w._delete_processor_dirs_action.trigger()
    gc.collect()
print("ok")
"""


def test_confirming_a_deletion_survives_garbage_collection(tmp_path):
    """End to end in a subprocess, since the failure mode is a hard crash."""
    import os
    import subprocess
    import sys
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", FODE_CONFIG=str(tmp_path / "cfg.json"))
    case = tmp_path / "case"
    case.mkdir()
    proc = subprocess.run(
        [sys.executable, "-X", "faulthandler", "-c", _CRASH_SCRIPT, str(case), str(repo)],
        cwd=repo, env=env, capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "ok" in proc.stdout
