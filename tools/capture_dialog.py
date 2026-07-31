#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Capture the gallery's dialog shots, reproducibly.

`capture_screenshots.py` applies a `WindowState` to a `MainWindow` and captures
that one window. A dialog is a top-level X window of its own rather than part of
the main window's frame, so it is out of that tool's reach — which is why the
gallery's dialog images were hand-taken, and why they drifted: the hand-taken
`find_foam_example.png` this replaced carried the desktop theme, window
decorations and taskbar of the machine it was captured on, none of which matched
the rest of the gallery, and it predated two of the buttons it was showing off.

The shots live in `DIALOG_SHOTS` below rather than in a JSON spec: a dialog is
constructed from typed Python arguments, and inventing a schema to express those
buys nothing while there are so few of them. Everything else follows
`capture_screenshots.py`'s rules, for the same reasons documented there — the
theme comes from `--theme` and the language is forced to English so neither is
inherited from the saved settings, capture goes through ImageMagick's
`import -frame` rather than `QWidget.grab()`, and nothing is ever written back to
`app_config.json`.

Usage:
    DISPLAY=:1 python3 tools/capture_dialog.py --all
    DISPLAY=:1 python3 tools/capture_dialog.py log-summary --out /tmp/shots
    python3 tools/capture_dialog.py --list

A real X display is required and DISPLAY must point at it; `import` reads the
screen, so the window is moved to (0, 0) and raised, and anything overlapping it
would be captured instead.

Some shots need a case, or an OpenFOAM installation, that a plain checkout does
not have. See DEVELOPER.md's "Screenshot capture" for how to produce them;
`--case-dir` and `--installation` override the defaults.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Same reason as main.py: must be set before QApplication exists.
os.environ.setdefault(
    "QTWEBENGINE_CHROMIUM_FLAGS",
    "--disable-gpu --disable-vulkan --log-level=2",
)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from capture_screenshots import (  # noqa: E402
    THEMES,
    _process_events,
    _wait_for_active,
    capture_window,
)

DEFAULT_OUT = ROOT / "docs" / "images"
# Deliberately not a path under $HOME: the log's own "Case:" line is reproduced
# in the summary, so a case run from a home directory would print the capturing
# user's name into the gallery. See DEVELOPER.md's "Screenshot capture".
DEFAULT_CASE = Path("/tmp/OpenFOAM/run/pitzDaily")
# Pinned rather than left to whichever installation discovery happens to put
# first, so the shot does not change version between two machines.
DEFAULT_INSTALLATION = Path("/usr/lib/openfoam/openfoam2606")

# What the Find Examples shot searches for and settles on. Both are pinned here
# because the caption quotes them.
_EXAMPLE_QUERY = "topoSetDict"
_EXAMPLE_SELECTION = ("multiphase", "interFoam", "RAS", "floatingObject",
                      "system", "topoSetDict")

# The bundled damBreak has a 0.orig/, which is what makes the run dialog offer
# its "restore 0/ first" prefix — the thing this shot is for.
_RUN_TOOL_CASE = ROOT / "tutorials" / "damBreak"
# Copied from ui/mixins/_tools_ops.py's _on_run_setfields_clicked rather than
# imported: they are inline literals there, and reaching into a mixin to build
# a dialog would mean standing up a MainWindow. tests/tools/test_capture_dialog.py
# asserts these still match that file, so the shot cannot quietly go fictional.
_SETFIELDS_WARNING = (
    "setFields modifies the field files in 0/ in place, so re-running "
    "it on already-set fields compounds the values."
)
_SETFIELDS_PREFIX = (
    "Restore 0/ from 0.orig/ first (start from clean initial fields)",
    "rm -rf 0 && cp -r 0.orig 0 && ",
    True,
)


@dataclass(frozen=True)
class ShotContext:
    """What a shot may need from the capture machine."""

    case_dir: Path
    installation: Path


@dataclass(frozen=True)
class DialogShot:
    """One gallery dialog image: how to build it, how big, and where it goes.

    ``requires`` checks the machine has what the shot reads, and raises
    ``SystemExit`` naming what is missing. It is separate from ``build`` so the
    answer to "can this shot run here?" does not need a ``QApplication`` — which
    is what lets the tests exercise it.

    ``prepare`` runs after ``show()``, for a dialog whose content is not ready
    at construction — one that searches in a background thread, say. It is
    handed the dialog and a ``pump(ms)`` that runs the event loop, since
    waiting is the whole reason it exists.
    """

    name: str
    output: str
    size: tuple[int, int] | None  # None keeps the dialog's own default
    requires: Callable[[ShotContext], None]
    build: Callable[[ShotContext], Any]
    prepare: Callable[[Any, Callable[[int], None]], None] | None = None
    note: str = ""


def _requires_log_summary(ctx: ShotContext) -> None:
    log = ctx.case_dir / "log.simpleFoam"
    if not log.is_file():
        raise SystemExit(
            f"missing {log}\n"
            "See DEVELOPER.md's \"Screenshot capture\" for how to produce this case."
        )


def _build_log_summary(ctx: ShotContext):
    from ui.dialogs.log_summary_dialog import LogSummaryDialog

    log = ctx.case_dir / "log.simpleFoam"
    return LogSummaryDialog(str(ctx.case_dir), initial_file=str(log))


def _requires_find_examples(ctx: ShotContext) -> None:
    if not ctx.installation.is_dir():
        raise SystemExit(
            f"missing OpenFOAM installation {ctx.installation}\n"
            "Pass --installation to point at one this machine has."
        )


def _build_find_examples(ctx: ShotContext):
    from ui.dialogs.find_examples_dialog import FindExamplesDialog

    dialog = FindExamplesDialog()
    # The dialog offers whatever discovery found; pick the pinned one rather
    # than whichever sorted first here.
    combo = dialog._install_combo
    for index in range(combo.count()):
        data = combo.itemData(index)
        if data is not None and Path(data.root) == ctx.installation:
            combo.setCurrentIndex(index)
            break
    else:
        raise SystemExit(
            f"{ctx.installation} is not among the installations the dialog found"
        )
    dialog._query_edit.setText(_EXAMPLE_QUERY)
    return dialog


def _prepare_find_examples(dialog, pump: Callable[[int], None]) -> None:
    """Run the search, wait for it, and settle on one result.

    Reaches past the dialog's private widgets, which is the trade for not
    adding capture-only accessors to a production dialog. Names drifting is
    the risk, and tests/tools/test_capture_dialog.py pins them so a rename
    fails in the suite rather than here.
    """
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QAbstractItemView

    results = dialog._results
    dialog._on_search()
    # The search runs in a QThread; the tree filling is the public sign it is
    # done. A cap rather than a wait forever: a capture must not hang.
    for _ in range(60):
        pump(250)
        if results.topLevelItemCount():
            break
    else:
        raise SystemExit(f"search for {_EXAMPLE_QUERY!r} returned nothing in time")

    wanted = os.path.join(*_EXAMPLE_SELECTION)
    stack = [results.topLevelItem(i) for i in range(results.topLevelItemCount())]
    while stack:
        item = stack.pop()
        hit = item.data(0, Qt.ItemDataRole.UserRole)
        if hit is not None and str(hit.file).endswith(wanted):
            results.setCurrentItem(item)
            # Centred, not merely made visible: the default hint scrolls just
            # far enough, which leaves the selected row on the bottom edge
            # with its neighbour clipped under it.
            results.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)
            pump(400)
            return
        stack.extend(item.child(i) for i in range(item.childCount()))
    raise SystemExit(f"no result matching {wanted} to select")


def _requires_run_tool(ctx: ShotContext) -> None:
    # Pinned to the bundled case rather than ctx.case_dir: the shot is about the
    # restore-0/ prefix, which only appears when the case has a 0.orig/.
    if not (_RUN_TOOL_CASE / "0.orig").is_dir():
        raise SystemExit(
            f"missing {_RUN_TOOL_CASE / '0.orig'}\n"
            "The run dialog only offers its restore prefix when 0.orig/ exists."
        )


def _build_run_tool(ctx: ShotContext):
    from services.tool_options import TOOL_SPECS
    from ui.dialogs.run_tool_dialog import RunToolDialog

    return RunToolDialog(
        TOOL_SPECS["setFields"],
        str(_RUN_TOOL_CASE),
        warning_text=_SETFIELDS_WARNING,
        prefix_option=_SETFIELDS_PREFIX,
    )


DIALOG_SHOTS: dict[str, DialogShot] = {
    "log-summary": DialogShot(
        name="log-summary",
        output="log-summary-dialog.png",
        # Tall enough for the whole summary; the dialog's own default cuts the
        # last two lines off, and a scrolled-away verdict is the one line of a
        # run report a reader most wants to see.
        size=(660, 515),
        requires=_requires_log_summary,
        build=_build_log_summary,
        note="View Log Summary over a pitzDaily simpleFoam run.",
    ),
    "run-tool": DialogShot(
        name="run-tool",
        output="run-tool-dialog.png",
        # Wider than the dialog's own minimum, which wraps the composed command
        # onto a second line mid-pipeline and elides the -dict placeholder.
        size=(700, 295),
        requires=_requires_run_tool,
        build=_build_run_tool,
        note="Run setFields options dialog, with its pre-flight and command preview.",
    ),
    "find-examples": DialogShot(
        name="find-examples",
        output="find_foam_example.png",
        size=None,
        requires=_requires_find_examples,
        build=_build_find_examples,
        prepare=_prepare_find_examples,
        note=f"Find OpenFOAM Examples, searched for {_EXAMPLE_QUERY!r}.",
    ),
}


def capture_shot(shot: DialogShot, theme: str, ctx: ShotContext, out_path: Path) -> None:
    """Build the dialog, let it settle, and capture it with its decorations."""
    from PySide6.QtWidgets import QApplication

    from i18n import set_language
    from ui.theme import apply_theme

    app = QApplication([sys.argv[0]])
    apply_theme(app, theme)
    # Gallery images are English; the saved language setting must not leak in.
    set_language("en")

    shot.requires(ctx)
    dialog = shot.build(ctx)
    if shot.size is not None:
        dialog.resize(*shot.size)
    dialog.show()
    # A known corner, fully on screen, for the same reason as the main-window
    # capture: `import` reads the screen, not the widget.
    dialog.move(0, 0)
    _process_events(app, 400)
    if shot.prepare is not None:
        shot.prepare(dialog, lambda ms: _process_events(app, ms))
    dialog.raise_()
    dialog.activateWindow()
    _process_events(app, 300)
    if not _wait_for_active(app, dialog):
        # An unfocused title bar is drawn in a different shade, which is the one
        # part of a capture that can differ between two runs of the same shot.
        print(f"warning: {shot.name} never became the active window; "
              "its title bar may not match the rest of the gallery", file=sys.stderr)

    capture_window(int(dialog.winId()), out_path)
    print(f"→ {shot.name} [{theme}] → {out_path}")


def _run_workers(names: list[str], args) -> int:
    """Re-execute this script once per shot; returns non-zero if any failed."""
    failures = 0
    for name in names:
        command = [
            sys.executable, str(Path(__file__).resolve()), name,
            "--theme", args.theme,
            "--case-dir", str(args.case_dir),
            "--installation", str(args.installation),
            "--out", str(args.out),
            "--_worker",
        ]
        result = subprocess.run(command)
        if result.returncode != 0:
            failures += 1
            print(f"✗ {name} failed (exit {result.returncode})", file=sys.stderr)
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("shots", nargs="*", metavar="SHOT",
                        help="shot names to capture (default: none; use --all)")
    parser.add_argument("--all", action="store_true", help="capture every shot")
    parser.add_argument("--list", action="store_true", help="list the shots and exit")
    parser.add_argument("--theme", choices=THEMES, default="light",
                        help="theme to capture in (default: light, as the gallery uses)")
    parser.add_argument("--case-dir", type=Path, default=DEFAULT_CASE, metavar="DIR",
                        help=f"case the shots read from (default: {DEFAULT_CASE})")
    parser.add_argument("--installation", type=Path, default=DEFAULT_INSTALLATION,
                        metavar="DIR",
                        help="OpenFOAM installation the shots search "
                             f"(default: {DEFAULT_INSTALLATION})")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, metavar="DIR",
                        help=f"where the images go (default: {DEFAULT_OUT})")
    parser.add_argument("--_worker", action="store_true",
                        help=argparse.SUPPRESS)  # internal: capture one shot in-process
    args = parser.parse_args(argv)

    if args.list:
        for shot in DIALOG_SHOTS.values():
            print(f"{shot.name}\n    {shot.output}\n    {shot.note}")
        return 0

    names = list(DIALOG_SHOTS) if args.all else args.shots
    if not names:
        parser.error("name a shot, or pass --all (--list shows what there is)")
    unknown = [n for n in names if n not in DIALOG_SHOTS]
    if unknown:
        parser.error(f"unknown shot(s): {', '.join(unknown)}")

    ctx = ShotContext(case_dir=args.case_dir, installation=args.installation)
    if not args._worker:
        # One process per shot, for the reason capture_screenshots.py gives:
        # no shot should inherit stray state from the one before it. Here there
        # is a harder reason too — a QApplication is a singleton, so a second
        # shot in this process cannot have one.
        return _run_workers(names, args)
    for name in names:
        shot = DIALOG_SHOTS[name]
        capture_shot(shot, args.theme, ctx, args.out / shot.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
