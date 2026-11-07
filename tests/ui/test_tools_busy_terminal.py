# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tools-menu actions against a busy terminal, Run reconstructPar…, and
Delete processor* Directories… (ui/mixins/_tools_ops.py,
ui/mixins/_processor_ops.py, ui/mixins/_background_run_ops.py).

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

    from ui.dialogs.processor_delete_dialog import ProcessorDeleteDialog

    def fake_exec(box):
        def describe(chk):
            return None if chk is None else {
                "text": chk.text(),
                "checked": chk.isChecked(),
                "enabled": chk.isEnabled(),
            }

        state["box"] = {
            "text": box.text(),
            "chk": describe(box.keep_checkbox),
            "gz": describe(box.full_gz_checkbox),
        }
        if state["keep"] is not None and box.keep_checkbox is not None:
            box.keep_checkbox.setChecked(state["keep"])
        if state.get("full_gz") is not None and box.full_gz_checkbox is not None:
            box.full_gz_checkbox.setChecked(state["full_gz"])
        return 1 if state["answer"] else 0

    monkeypatch.setattr(ProcessorDeleteDialog, "exec", fake_exec)
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
        ("files_cut_off", "cut off"),
        ("files_bad_header", "FoamFile header"),
        ("files_wrong_size", "number of values"),
        ("processes_running", "is working in this case"),
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
    box = win._processor_delete_box(whole, keep)
    chk = box.keep_checkbox
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


# ── soundness of the case-root copy ──────────────────────────────────────────


def test_a_cut_off_root_field_is_refused_without_asking(win, boxes, confirm, tmp_path):
    import os

    from tests.services._processor_cases import _sound_case

    _sound_case(tmp_path)
    f = tmp_path / "0.5" / "p"
    os.truncate(f, f.stat().st_size // 2)
    win._on_delete_processor_dirs_clicked()
    assert confirm["box"] is None
    text = boxes["warning"][0][1]
    assert "time 0.5: p at the case root are cut off" in text
    assert "reconstructPar -time 0.5" in text
    assert (tmp_path / "processor0" / "0.5" / "p").exists()


def test_a_process_working_in_the_case_is_refused(win, boxes, confirm, tmp_path, monkeypatch):
    import ui.mixins._processor_ops as ops
    from services.solver_run import DeletionProblem
    from tests.services._processor_cases import _sound_case

    _sound_case(tmp_path)
    busy = DeletionProblem("processes_running", detail=("reconstructPar (pid 4242)",))
    monkeypatch.setattr(ops, "case_activity_problem", lambda case_dir: busy)
    win._on_delete_processor_dirs_clicked()
    assert confirm["box"] is None
    assert "reconstructPar (pid 4242) is working in this case" in boxes["warning"][0][1]


def test_a_process_started_after_confirming_still_stops_it(
    win, boxes, confirm, tmp_path, monkeypatch
):
    import ui.processor_deletion as worker
    from services.solver_run import DeletionProblem
    from tests.services._processor_cases import _sound_case

    _sound_case(tmp_path)
    busy = DeletionProblem("processes_running", detail=("simpleFoam (pid 7)",))
    monkeypatch.setattr(worker, "case_activity_problem", lambda case_dir: busy)
    confirm["keep"] = False
    win._on_delete_processor_dirs_clicked()
    assert confirm["box"] is not None  # it was asked…
    assert (tmp_path / "processor0").exists()  # …but nothing went
    assert "Nothing was deleted." in boxes["warning"][0][1]


@pytest.fixture
def large_gz(monkeypatch):
    """Make every compressed test file "large": read at its start only."""
    import services.field_integrity as fi

    monkeypatch.setattr(fi, "_HEAD_BYTES", 200)


def test_the_full_gz_check_is_offered_ticked(win, boxes, confirm, tmp_path, large_gz):
    from tests.services._processor_cases import _sound_case

    _sound_case(tmp_path, gz=True)
    confirm["keep"] = False
    win._on_delete_processor_dirs_clicked()
    gz = confirm["box"]["gz"]
    assert gz["checked"] and gz["enabled"]
    assert "Read compressed files to the end first (2 .gz files" in gz["text"]
    assert "checked at their start only" not in confirm["box"]["text"]
    assert not (tmp_path / "processor0").exists()


def test_no_gz_option_without_compressed_files(win, boxes, confirm, tmp_path):
    from tests.services._processor_cases import _sound_case

    _sound_case(tmp_path)
    win._on_delete_processor_dirs_clicked()
    assert confirm["box"]["gz"] is None


def test_unticking_the_gz_check_says_what_is_not_checked(win, tmp_path, large_gz):
    from services.solver_run import check_processor_deletion
    from tests.services._processor_cases import _sound_case

    _sound_case(tmp_path, gz=True)
    box = win._processor_delete_box(
        check_processor_deletion(str(tmp_path)),
        check_processor_deletion(str(tmp_path), keep_latest=True),
    )
    # Keep mode reads only 0.5's two files; the kept time 1 is not deleted.
    assert "(2 .gz files" in box.full_gz_checkbox.text()
    box.keep_checkbox.setChecked(False)
    assert "(4 .gz files" in box.full_gz_checkbox.text()
    box.full_gz_checkbox.setChecked(False)
    assert "4 compressed files" in box.text() and "would not be detected" in box.text()
    assert box.text().endswith("This cannot be undone.")
    box.deleteLater()


def test_the_full_gz_check_finds_a_cut_off_file_and_deletes_nothing(
    win, boxes, confirm, tmp_path, large_gz
):
    import os

    from tests.services._processor_cases import _sound_case

    _sound_case(tmp_path, gz=True)
    f = tmp_path / "0.5" / "p.gz"
    os.truncate(f, f.stat().st_size - 20)
    confirm["keep"] = False
    win._on_delete_processor_dirs_clicked()
    assert confirm["box"] is not None
    assert "time 0.5: p.gz at the case root are cut off" in boxes["warning"][0][1]
    assert (tmp_path / "processor0" / "0.5").exists()


def test_without_the_full_gz_check_the_deletion_goes_ahead(
    win, boxes, confirm, tmp_path, large_gz
):
    import os

    from tests.services._processor_cases import _sound_case

    _sound_case(tmp_path, gz=True)
    f = tmp_path / "0.5" / "p.gz"
    os.truncate(f, f.stat().st_size - 20)
    confirm["keep"] = False
    confirm["full_gz"] = False  # the user's choice, made knowingly
    win._on_delete_processor_dirs_clicked()
    assert not (tmp_path / "processor0").exists()


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
    box = win._processor_delete_box(
        check_processor_deletion(str(tmp_path)),
        check_processor_deletion(str(tmp_path), keep_latest=True),
    )
    chk = box.keep_checkbox
    assert chk.parent() is not None
    assert not Shiboken.ownedByPython(chk)
    box.deleteLater()


_CRASH_SCRIPT = r"""
import gc, sys
from pathlib import Path
sys.path.insert(0, sys.argv[2])
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from tests.services._processor_cases import _reconstructed_case
from ui.dialogs.processor_delete_dialog import ProcessorDeleteDialog

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
        if isinstance(top, ProcessorDeleteDialog) and top.isVisible():
            top.yes_button.click()
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


# ── background runs ──────────────────────────────────────────────────────────

_CONTROL = "application icoFoam;\nstopAt          endTime;\nendTime 1;\n"


@pytest.fixture
def background_run(tmp_path):
    """A live process working in the case, recorded as FoDE's background run."""
    import subprocess
    import sys

    from services.background_run import PID_FILE

    if not sys.platform.startswith("linux"):
        pytest.skip("reads /proc")
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], cwd=tmp_path)
    (tmp_path / PID_FILE).write_text(f"{child.pid} icoFoam log.icoFoam\n")
    yield child
    child.kill()
    child.wait()


def _end(child):
    child.kill()
    child.wait()


@pytest.mark.parametrize("action", ACTIONS)
def test_a_background_run_refuses_every_terminal_action(
    win, boxes, tmp_path, background_run, action
):
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "controlDict").write_text(_CONTROL)
    (tmp_path / "0.orig").mkdir()
    for script in ("Allrun", "Allclean"):
        (tmp_path / script).write_text("#!/bin/sh\n")
    getattr(win, action)()
    assert win.terminal_panel.commands == []
    title, text = boxes["warning"][0]
    assert title == "Background run in progress"
    assert f"icoFoam is running in the background in this case (pid {background_run.pid})" in text


def _accept_solver_dialog(monkeypatch, *, background):
    from ui.dialogs.run_solver_dialog import RunSolverDialog

    seen = {}

    def fake_exec(dlg):
        seen["offered"] = dlg._background_chk is not None
        if dlg._background_chk is not None:
            dlg._background_chk.setChecked(background)
            seen["note_shown"] = not dlg._background_note.isHidden()
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(RunSolverDialog, "exec", fake_exec)
    return seen


def test_run_solver_in_the_background(win, boxes, tmp_path, monkeypatch):
    import ui.mixins._tools_ops as ops

    monkeypatch.setattr(ops, "background_supported", lambda: True)
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "controlDict").write_text(_CONTROL)
    seen = _accept_solver_dialog(monkeypatch, background=True)
    win._on_run_solver_clicked()
    assert seen["offered"] and seen["note_shown"]
    (cmd,) = win.terminal_panel.commands
    assert "setsid -f sh -c" in cmd and cmd.endswith("log.icoFoam; else cat log.icoFoam; fi")
    assert "| tee" not in cmd


def test_run_solver_without_background_support(win, boxes, tmp_path, monkeypatch):
    import ui.mixins._tools_ops as ops

    monkeypatch.setattr(ops, "background_supported", lambda: False)
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "controlDict").write_text(_CONTROL)
    seen = _accept_solver_dialog(monkeypatch, background=True)
    win._on_run_solver_clicked()
    assert not seen["offered"]
    assert win.terminal_panel.commands == ["icoFoam 2>&1 | tee log.icoFoam"]


def test_run_solver_warns_about_a_stopping_stop_at(win, boxes, tmp_path, monkeypatch):
    from ui.dialogs.run_solver_dialog import RunSolverDialog

    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "controlDict").write_text(_CONTROL.replace("endTime;", "writeNow;"))
    seen = {}
    real_init = RunSolverDialog.__init__

    def spy(self, case_dir, exe, last, warning, *a, **k):
        seen["warning"] = warning
        real_init(self, case_dir, exe, last, warning, *a, **k)

    monkeypatch.setattr(RunSolverDialog, "__init__", spy)
    monkeypatch.setattr(RunSolverDialog, "exec", lambda self: QDialog.DialogCode.Rejected)
    win._on_run_solver_clicked()
    assert "stopAt writeNow, so the solver will stop right after it starts" in seen["warning"]


@pytest.mark.parametrize("logs", [False, True])
def test_allrun_in_the_background(win, boxes, tmp_path, monkeypatch, logs):
    import ui.mixins._background_run_ops as ops

    monkeypatch.setattr(ops, "background_supported", lambda: True)
    (tmp_path / "Allrun").write_text("#!/bin/sh\n")
    if logs:
        (tmp_path / "log.blockMesh").write_text("")

    def fake_exec(box):
        box.checkBox().setChecked(True)
        return QMessageBox.StandardButton.Yes.value

    monkeypatch.setattr(QMessageBox, "exec", fake_exec)
    if logs:
        monkeypatch.setattr(
            QMessageBox, "clickedButton",
            lambda self: next(b for b in self.buttons() if b.text() == "Clean, then run"),
        )
    win._on_run_allrun_clicked()
    (cmd,) = win.terminal_panel.commands
    assert "setsid -f sh -c" in cmd and " sh ./Allrun && " in cmd
    assert cmd.startswith("foamCleanTutorials && : > log.Allrun" if logs else ": > log.Allrun")


def test_stop_with_no_background_run(win, boxes, tmp_path):
    win._on_stop_background_run_clicked()
    assert boxes["information"][0][0] == "No background run"


def _reports(win):
    return [
        b for b in win.findChildren(QMessageBox)
        if b.windowTitle() == "Background run stopped" and b.isVisible()
    ]


def test_stop_and_restore(win, boxes, tmp_path, background_run):
    from services.background_run import pending_restore, read_stop_at

    (tmp_path / "system").mkdir()
    control = tmp_path / "system" / "controlDict"
    control.write_text(_CONTROL)
    (tmp_path / "log.icoFoam").write_text("Time = 0.3\n\nEnd\n")
    (tmp_path / "0.3").mkdir()
    win._on_stop_background_run_clicked()
    title, text = boxes["question"][0]
    assert f"Ask icoFoam (pid {background_run.pid}) to write the current time" in text
    assert read_stop_at(control.read_text()) == "writeNow"
    assert win._background_run_timer.isActive()
    assert "FoDE tells you when it has" in win.statusBar().currentMessage()

    win._poll_background_run()  # still running: nothing restored, nothing reported
    assert read_stop_at(control.read_text()) == "writeNow"
    assert _reports(win) == []

    _end(background_run)
    win._poll_background_run()
    assert control.read_text() == _CONTROL
    assert not pending_restore(str(tmp_path))
    assert not win._background_run_timer.isActive()
    (report,) = _reports(win)
    assert report.icon() == QMessageBox.Icon.Information
    assert report.text() == (
        "icoFoam has stopped. Last time written: 0.3.\n\n"
        "stopAt in controlDict is back to endTime."
    )
    assert not report.isModal()
    report.close()


def test_a_run_that_ends_without_end_is_reported_as_such(win, boxes, tmp_path, background_run):
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "controlDict").write_text(_CONTROL)
    (tmp_path / "log.icoFoam").write_text("Time = 0.3\nCourant Number mean: 0.1\n")
    win._on_stop_background_run_clicked()
    _end(background_run)
    win._poll_background_run()
    (report,) = _reports(win)
    assert report.icon() == QMessageBox.Icon.Warning
    assert "ended without finishing cleanly" in report.text()
    assert "Check log.icoFoam." in report.text()
    report.close()


@pytest.mark.parametrize(
    "restored, last, clean, expected",
    [
        ("endTime", "1", True, "icoFoam has stopped. Last time written: 1."),
        (None, "1", True, "was changed while the run stopped, so FoDE left it"),
        ("endTime", None, True, "No time directory was written."),
        ("endTime", "1", None, "Allrun has stopped."),
    ],
)
def test_stop_report_texts(win, restored, last, clean, expected):
    from services.background_run import StopReport

    label = "Allrun" if clean is None else "icoFoam"
    failed, text = win._stop_report_text(StopReport(label, "log.x", restored, last, clean))
    assert not failed and expected in text


def test_a_run_finishing_on_its_own_gets_a_status_line(win, boxes, tmp_path, background_run):
    win._poll_background_run()  # FoDE sees it running…
    assert win._background_run_timer.isActive()
    _end(background_run)
    win._poll_background_run()  # …and then gone, with no stop asked for
    assert _reports(win) == []
    assert win.statusBar().currentMessage() == (
        "icoFoam has finished in the background; its output is in log.icoFoam."
    )
    assert not win._background_run_timer.isActive()


def test_stop_declined_changes_nothing(win, boxes, tmp_path, background_run):
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "controlDict").write_text(_CONTROL)
    boxes["answer"] = False
    win._on_stop_background_run_clicked()
    assert (tmp_path / "system" / "controlDict").read_text() == _CONTROL


def test_stop_refused_with_run_time_modifiable_off(win, boxes, tmp_path, background_run):
    (tmp_path / "system").mkdir()
    text = _CONTROL + "runTimeModifiable false;\n"
    (tmp_path / "system" / "controlDict").write_text(text)
    win._on_stop_background_run_clicked()
    # The minus: the recorded pid is the run's wrapper, and only the group
    # reaches the solver (services/background_run.py).
    assert f"kill -- -{background_run.pid}" in boxes["warning"][0][1]
    assert (tmp_path / "system" / "controlDict").read_text() == text


def test_stop_refused_while_control_dict_has_unsaved_edits(win, boxes, tmp_path, background_run):
    (tmp_path / "system").mkdir()
    control = tmp_path / "system" / "controlDict"
    control.write_text(_CONTROL)
    win.state.file_dirty[str(control)] = True
    win._on_stop_background_run_clicked()
    assert "unsaved edits" in boxes["warning"][0][1]
    assert control.read_text() == _CONTROL


def test_the_open_control_dict_shows_the_stop(win, boxes, tmp_path, background_run):
    (tmp_path / "system").mkdir()
    control = tmp_path / "system" / "controlDict"
    control.write_text(_CONTROL)
    win.load_selected_file(str(control))
    win._on_stop_background_run_clicked()
    assert "stopAt          writeNow;" in win.editor_panel.get_text()
    _end(background_run)
    win._poll_background_run()
    assert "stopAt          endTime;" in win.editor_panel.get_text()
    for box in _reports(win):
        box.close()


def test_opening_the_case_restores_a_stop_from_an_earlier_session(main_window, tmp_path):
    from services.background_run import request_stop

    (tmp_path / "system").mkdir()
    control = tmp_path / "system" / "controlDict"
    control.write_text(_CONTROL)
    request_stop(str(tmp_path))  # FoDE was closed before the run ended
    main_window._load_case_dir(str(tmp_path))
    assert control.read_text() == _CONTROL


def test_the_watcher_follows_the_first_processor_directory(main_window, tmp_path):
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "controlDict").write_text(_CONTROL)
    (tmp_path / "constant").mkdir()
    main_window._load_case_dir(str(tmp_path))
    assert set(main_window._case_dir_watcher.directories()) == {
        str(tmp_path), str(tmp_path / "constant")
    }
    for n in range(2):
        (tmp_path / f"processor{n}" / "0").mkdir(parents=True)
    main_window._reload_file_list()  # decomposePar ran: the file list reloads
    assert str(tmp_path / "processor0") in main_window._case_dir_watcher.directories()
    assert str(tmp_path / "processor1") not in main_window._case_dir_watcher.directories()
    import shutil

    shutil.rmtree(tmp_path / "processor0")
    shutil.rmtree(tmp_path / "processor1")
    main_window._reload_file_list()
    assert set(main_window._case_dir_watcher.directories()) == {
        str(tmp_path), str(tmp_path / "constant")
    }


# ── the toolbar badge and window title ───────────────────────────────────────


def test_no_badge_without_a_background_run(win, tmp_path):
    win._poll_background_run()
    assert not win._background_badge_action.isVisible()
    assert win.windowTitle() == "foam dictionary editor"


def test_the_badge_follows_a_run_through_its_stop(win, boxes, tmp_path, background_run):
    from ui.theme import colors

    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "controlDict").write_text(_CONTROL)
    win._poll_background_run()
    btn = win.background_run_btn
    assert win._background_badge_action.isVisible()
    assert btn.text() == "● icoFoam running in background"
    assert f"pid {background_run.pid}" in btn.toolTip()
    assert win.windowTitle() == "foam dictionary editor — icoFoam running"

    win._on_stop_background_run_clicked()
    assert btn.text() == "■ Stopping icoFoam…"
    assert colors().attention_text.lower() in btn.styleSheet().lower()
    assert win.windowTitle() == "foam dictionary editor — stopping icoFoam"

    _end(background_run)
    win._poll_background_run()
    assert not win._background_badge_action.isVisible()
    assert win.windowTitle() == "foam dictionary editor"
    for box in _reports(win):
        box.close()


def test_the_badge_menu_reaches_the_real_handlers(win, boxes, tmp_path, monkeypatch):
    actions = win.background_run_btn.menu().actions()
    assert [a.text() for a in actions] == ["Stop Background Run", "View Log Summary…"]
    actions[0].trigger()  # no run in this case: the real handler says so
    assert boxes["information"][0][0] == "No background run"
    shown = []
    monkeypatch.setattr(
        "ui.mixins._tools_ops.LogSummaryDialog.show", lambda self: shown.append(self)
    )
    actions[1].trigger()
    assert len(shown) == 1


def test_the_dirty_mark_and_the_run_share_the_title(win, tmp_path, background_run):
    win._poll_background_run()
    win.state.text_dirty = True
    win._update_window_title()
    assert win.windowTitle() == "foam dictionary editor* — icoFoam running"


def test_a_failed_run_that_wrote_nothing(win):
    from services.background_run import StopReport

    failed, text = win._stop_report_text(StopReport("icoFoam", "log.icoFoam", "endTime", None, False))
    assert failed
    assert "No time directory was written. Check log.icoFoam." in text
    assert "(none)" not in text


# ── the close-time reminder ─────────────────────────────────────────────────


@pytest.fixture
def reminder(monkeypatch):
    """Answer the reminder box; ``quiet`` ticks "Don't remind me again"."""
    seen: dict = {"shown": [], "quiet": False}

    def fake_exec(box):
        if box.windowTitle() == "Background runs continue":
            seen["shown"].append(box.text())
            box.checkBox().setChecked(seen["quiet"])
        return QMessageBox.StandardButton.Ok.value

    monkeypatch.setattr(QMessageBox, "exec", fake_exec)
    return seen


def test_no_reminder_without_a_background_run(win, reminder):
    win._remind_background_runs()
    assert reminder["shown"] == []


def test_the_reminder_names_the_run_and_how_to_find_it(win, reminder, tmp_path, background_run):
    from app_config import get_app_config

    win._remind_background_runs()
    (text,) = reminder["shown"]
    assert f"• icoFoam in {tmp_path.name} (pid {background_run.pid})" in text
    assert "open its case in FoDE again" in text
    assert "Shutting down or logging out of the computer ends it." in text
    assert get_app_config().get_remind_background_runs()


def test_dont_remind_me_again(win, reminder, tmp_path, background_run):
    from app_config import get_app_config

    reminder["quiet"] = True
    win._remind_background_runs()
    assert not get_app_config().get_remind_background_runs()
    win._remind_background_runs()  # silent from now on
    assert len(reminder["shown"]) == 1


def test_a_run_in_a_case_no_longer_open_is_included(win, reminder, tmp_path, background_run):
    other = tmp_path / "other"
    other.mkdir()
    win._poll_background_run()  # FoDE sees the run in tmp_path…
    win.state.current_case_dir = str(other)  # …and the user opens another case
    win._remind_background_runs()
    (text,) = reminder["shown"]
    assert f"icoFoam in {tmp_path.name}" in text


def test_closing_fode_shows_the_reminder(main_window, reminder, tmp_path, background_run):
    main_window.state.current_case_dir = str(tmp_path)
    main_window.terminal_panel = None  # the terminal's own close question is tested elsewhere
    main_window.close()
    assert len(reminder["shown"]) == 1
