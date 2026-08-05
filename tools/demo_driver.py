#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Drive the app through a scripted demo, reproducibly, and record it.

A demo movie is the same problem as a gallery image one dimension further on:
taken by hand it is expensive to retake, so it goes stale the moment a menu is
renamed. This script is tools/capture_screenshots.py's sibling — the scenes in
tools/demo_specs.json start from the same ui/window_state.py WindowState, and
then a list of *steps* drives the window while ffmpeg records it.

Usage:
    # what the spec defines:
    python3 tools/demo_driver.py --list

    # open a scene's start state and stop there, for recording by hand:
    DISPLAY=:1 python3 tools/demo_driver.py damBreak-end-to-end --stage

    # drive the steps, no recording (a rehearsal — watch it, fix the timings):
    DISPLAY=:1 python3 tools/demo_driver.py damBreak-end-to-end

    # drive and record:
    DISPLAY=:1 python3 tools/demo_driver.py damBreak-end-to-end \\
        --record out/damBreak.mp4

A real X display is required and DISPLAY must point at it, for the reason the
screenshot harness gives (offscreen Qt aborts VTK) plus a second one: the steps
are driven with `xdotool`, which sends real X input, so the app sees ordinary
mouse and keyboard events and the recording shows a real cursor moving over
real hover states. Nothing here reaches into the app to fake a click.

That input is also why a take runs on a *nested* display of its own (Xephyr)
rather than on the one it was started from. Real clicks and keystrokes go to
whichever window the window manager put on top and wherever focus drifted to —
on a desktop in use, that is someone's editor or chat window, and the take is
both unreliable and rude. --on-this-display opts out for a machine nobody is
sitting at; --stage never nests, because it exists to hand the window over.

Steps run on a QTimer chain rather than a nested event loop, because a modal
dialog runs an event loop of its own: a nested-loop driver would block on the
dialog it just opened, waiting for a step that can only run after it closes.
Timers fire inside the dialog's loop, so the chain keeps stepping.

Nothing is written back to app_config.json: the theme comes from the spec or
--theme rather than the saved setting, the window is never closed, so
MainWindow.closeEvent never runs, and the config singleton is pointed at a
scratch file in the workdir before the window is built (seed_app_config), so a
step that walks through a dialog which saves settings — duplicating a case does
— saves them there instead. That scratch file is also what makes a take
portable: the feature flags, the default case directory and the case library
would otherwise be whatever the recording machine last used. The case is not
touched either — a scene
copies its case to a scratch directory first, so every take starts from the
same pristine state and a demo that runs blockMesh does not litter the
repository's tutorials/.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

# Same reason as main.py: must be set before QApplication exists.
os.environ.setdefault(
    "QTWEBENGINE_CHROMIUM_FLAGS",
    "--disable-gpu --disable-vulkan --log-level=2",
)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ui.window_state import (  # noqa: E402
    WindowState,
    apply_block_mesh_view,
    apply_window_state,
    capture_window_state,
    index_for_key_path,
)

DEFAULT_SPEC = ROOT / "tools" / "demo_specs.json"
# Where a take lands when --record is given no filename. The videos there are
# gitignored and the .srt files beside them are not: a movie is regenerated
# from the spec, and video does not delta-compress, so a tracked retake would
# be a whole new blob in history forever. The published copies live on YouTube.
DEFAULT_OUT = ROOT / "docs" / "demo"
# --record with no value: resolved to DEFAULT_OUT/<scene>.mp4 once the scene is
# known, which argparse cannot do for itself at parse time.
RECORD_DEFAULT = Path("@scene")
DEFAULT_CASES = Path.home() / "OpenFOAM" / "nakagawa-v2512" / "run"
DEFAULT_WORKDIR = Path("/tmp/fode-demo")

# The themes ui/theme.py's apply_theme accepts. "system" inherits the recording
# machine's desktop palette, which is the one thing about a take that cannot be
# reproduced elsewhere — so a scene names light or dark unless it is precisely
# a default install that is being shown.
Theme = Literal["system", "light", "dark"]
THEMES: tuple[Theme, ...] = ("light", "dark", "system")

# How long to let the window settle before the first step. The 3-D panel is
# what needs it, for the reason tools/capture_screenshots.py gives.
DEFAULT_SETTLE_MS = 2500

# Cursor travel. Long enough to be followed by eye, short enough not to bore:
# a demo is watched, not read.
GLIDE_MS = 420
GLIDE_TICK_MS = 14
# After a click, before the next step is expanded. Every step can override it
# with its own "then" field; this is what a step that says nothing gets.
DEFAULT_DWELL_MS = 400
# A take that has not ended by then is stuck, and holding the display.
DEFAULT_MAX_SECONDS = 300


# ── the spec ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Scene:
    """One demo movie: a start state, then the steps that drive it."""

    name: str
    state: WindowState
    steps: list[dict[str, Any]]
    note: str = ""
    theme: Theme = "light"
    # Copied fresh to `workdir` before the window opens, so a scene that runs
    # blockMesh or setFields writes into scratch rather than into the case it
    # was authored against. When unset, `state.case_dir` is opened in place.
    case_source: str = ""
    workdir: str = ""
    # Further cases the take needs beside the one it opens, each {source, into}.
    # A comparison's reference case is the reason: it is never opened, but it
    # has to exist, and it has to be somewhere the diff bar can print without
    # putting the recording user's home directory on screen.
    copy_also: list[dict[str, str]] = field(default_factory=list)
    # Removed before the window opens, for what a *step* creates rather than
    # what the staging copies: a scene that duplicates a case writes a
    # directory neither case_source nor copy_also names, and finding it there
    # from the previous take turns the next step into an "Overwrite?" box.
    clean: list[str] = field(default_factory=list)
    # The one directory the Case Library offers for this take. Without it the
    # library is whatever the recording machine has registered, and the case
    # chooser opens somewhere different on every machine — see _library_config.
    case_library: str = ""
    # Sent to the Terminal tab during staging, before recording starts — an
    # OpenFOAM `etc/bashrc` to source, typically. Watching someone set up their
    # shell is not the demo.
    terminal_prelude: list[str] = field(default_factory=list)


def load_spec(path: Path, cases_dir: Path, workdir: Path) -> list[Scene]:
    """Read the spec file, applying its defaults and expanding path placeholders."""
    data = json.loads(path.read_text(encoding="utf-8"))
    defaults = WindowState.from_dict(data.get("defaults") or {})
    known = {
        "state", "steps", "note", "theme", "case_source", "workdir",
        "terminal_prelude", "copy_also", "clean", "case_library",
    }

    scenes: list[Scene] = []
    for name, entry in (data["scenes"] or {}).items():
        unknown = sorted(set(entry) - known)
        if unknown:
            raise ValueError(f"scene {name!r}: unknown key(s) {', '.join(unknown)}")
        state = defaults.merged_with(WindowState.from_dict(entry.get("state") or {}))
        theme = entry.get("theme", "light")
        if theme not in THEMES:
            raise ValueError(f"scene {name!r}: unknown theme {theme!r}")
        case_source = _expand(entry.get("case_source", ""), cases_dir, workdir)
        scene_workdir = _expand(entry.get("workdir", ""), cases_dir, workdir)
        if case_source and not scene_workdir:
            raise ValueError(f"scene {name!r}: case_source needs a workdir to copy into")
        if state.case_dir:
            state = _replace_state(state, _expand(state.case_dir, cases_dir, workdir))
        elif scene_workdir:
            # The common case: the window opens the copy, so the spec need not
            # name the same directory twice.
            state = _replace_state(state, scene_workdir)
        steps = list(entry.get("steps") or [])
        for step in steps:
            # A typed path is still a path: a step that types a case directory
            # into a file chooser has to reach the same scratch copy the rest
            # of the scene does, and must not hard-code where that is.
            if "text" in step:
                step["text"] = step["text"].format(
                    repo=ROOT, cases=cases_dir, work=workdir
                )
        scenes.append(Scene(
            name=name,
            state=state,
            steps=steps,
            note=entry.get("note", ""),
            theme=theme,
            case_source=case_source,
            workdir=scene_workdir,
            clean=[_expand(p, cases_dir, workdir) for p in entry.get("clean") or []],
            case_library=_expand(entry.get("case_library", ""), cases_dir, workdir),
            terminal_prelude=list(entry.get("terminal_prelude") or []),
            copy_also=[
                {"source": _expand(item["source"], cases_dir, workdir),
                 "into": _expand(item["into"], cases_dir, workdir)}
                for item in entry.get("copy_also") or []
            ],
        ))
    return scenes


def _expand(raw: str, cases_dir: Path, workdir: Path) -> str:
    """Expand {repo} / {cases} / {work} and ~ in a spec path."""
    if not raw:
        return ""
    return str(Path(
        raw.format(repo=ROOT, cases=cases_dir, work=workdir)
    ).expanduser())


def _replace_state(state: WindowState, case_dir: str) -> WindowState:
    import dataclasses
    return dataclasses.replace(state, case_dir=case_dir)


def prepare_case(scene: Scene) -> None:
    """Copy the scene's case to its scratch directory, replacing what is there.

    Deliberately unconditional: a take that started from the leftovers of the
    one before it — a mesh already built, `0/` already set — is a take that
    shows something other than what the script says.
    """
    pairs = list(scene.copy_also)
    if scene.case_source:
        pairs.insert(0, {"source": scene.case_source, "into": scene.workdir})
    for pair in pairs:
        source = Path(pair["source"])
        if not source.is_dir():
            raise SystemExit(f"{scene.name}: no case at {source}")
        dest = Path(pair["into"])
        if dest.exists():
            shutil.rmtree(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, dest)
        # Not the recording user's per-case file registrations: a case they
        # have worked in carries a .foam-editor-files.json, and the take would
        # open showing their extra files and an "Extra files: 12" banner rather
        # than the case as it ships.
        (dest / ".foam-editor-files.json").unlink(missing_ok=True)
        print(f"  case: {source} → {dest}")

    for path in scene.clean:
        target = Path(path)
        if ROOT in target.parents or target == ROOT:
            raise SystemExit(f"{scene.name}: refusing to clean {target}, inside the repository")
        if target.exists():
            shutil.rmtree(target)
            print(f"  clean: {target}")


def seed_app_config(scene: Scene, workdir: Path) -> None:
    """Point the app's config singleton at a scratch file for this take.

    Two reasons, and the second is why this runs for every scene rather than
    only the ones that ask for a library. A take must not *write* the recording
    user's settings — a dialog that answers "open the duplicated case now?" with
    Yes saves a new default case directory on the way through, and the module
    docstring's promise is otherwise only kept by never closing the window. And
    a take must not *read* them either: the feature flags, the default case
    directory and the case library all come from this file, so a movie recorded
    on one machine otherwise opens somewhere else on the next.

    Must be called before MainWindow is built, because whichever code touches
    get_app_config() first is what fixes the singleton's path.
    """
    from app_config import get_app_config

    settings: dict[str, object] = {}
    if scene.case_library:
        settings["case_library_dirs"] = [scene.case_library]
        # The library is $FOAM_TUTORIALS plus the registered directories, and
        # with two of them the app asks which one to browse before it opens the
        # chooser — a dialog whose contents depend on the recording shell.
        # Pointing the variable at the same directory collapses the two into
        # one entry, rather than unsetting it and breaking `paraFoam`, which
        # needs the rest of the OpenFOAM environment intact.
        os.environ["FOAM_TUTORIALS"] = scene.case_library
        # Where a duplicate is offered a home. Scratch, so the destination
        # field never puts the recording user's name on screen.
        settings["default_case_dir"] = str(workdir)

    path = workdir / "config" / "app_config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    get_app_config(str(path))
    print(f"  config: {path}")


# ── a display of the take's own ───────────────────────────────────────────────


class NestedDisplay:
    """A private X server for the take, nested in a window on the real one.

    Driving a demo with real X input on the desktop someone is *using* goes
    wrong in both directions: their window manager raises a chat window over
    the app and the click lands in it, and the keystrokes a step types go
    wherever focus drifted. Neither is a thing to discover from the recording.

    Xephyr costs a few seconds at startup and settles both: the app is the only
    client on the display, so nothing can cover it, and the input goes to that
    server rather than to the one with the person's work on it. It has no
    window manager, which is a bonus rather than a compromise — no title bar
    means the recording is the application and nothing else.
    """

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.display = ""
        self._proc: subprocess.Popen | None = None

    def start(self) -> str:
        if shutil.which("Xephyr") is None:
            raise SystemExit(
                "Error: Xephyr is required for --isolated (apt install xserver-xephyr).\n"
                "Without it, pass --display to name a display of your own."
            )
        self.display = _free_display()
        self._proc = subprocess.Popen(
            ["Xephyr", self.display, "-screen", f"{self.width}x{self.height}",
             "-title", "FoDE demo — recording", "-no-host-grab"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        for _ in range(50):
            time.sleep(0.2)
            probe = subprocess.run(
                ["xdotool", "getdisplaygeometry"],
                env={**os.environ, "DISPLAY": self.display},
                capture_output=True, text=True,
            )
            if probe.returncode == 0:
                print(f"  display: {self.display} ({self.width}x{self.height}, nested)")
                return self.display
        self.stop()
        raise SystemExit(f"Error: Xephyr on {self.display} never came up.")

    def stop(self) -> None:
        if self._proc is None:
            return
        self._proc.terminate()
        try:
            self._proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._proc.kill()
        self._proc = None


def _free_display() -> str:
    """Pick a display number nothing is listening on."""
    for number in range(90, 100):
        if not Path(f"/tmp/.X11-unix/X{number}").exists():
            return f":{number}"
    raise SystemExit("Error: no free display between :90 and :99.")


# ── real X input ──────────────────────────────────────────────────────────────


class Pointer:
    """The mouse and keyboard, driven through xdotool.

    Every step goes through here rather than through Qt, so the app cannot tell
    the demo from a person and the recording shows what a person would see: the
    cursor travelling, buttons lighting up under it, menus opening on a real
    press.
    """

    def __init__(self) -> None:
        if shutil.which("xdotool") is None:
            raise SystemExit("Error: xdotool is required to drive a demo (apt install xdotool).")
        self.x = 0
        self.y = 0

    def move(self, x: int, y: int) -> None:
        # A move to where the pointer already is must not be issued at all:
        # --sync waits for a motion event that such a move never generates, and
        # blocks for seconds. Easing rounds several ticks of a slow stretch to
        # the same pixel, so this is the common case, not the corner one.
        if (int(x), int(y)) == (self.x, self.y):
            return
        self.x, self.y = int(x), int(y)
        # --sync: return once the pointer has actually moved, so the next
        # click cannot land at the position before this one.
        self._run(["mousemove", "--sync", str(self.x), str(self.y)])

    def click(self, button: int = 1, count: int = 1) -> None:
        self._run(["click", "--repeat", str(count), "--delay", "80", str(button)])

    def press(self, button: int = 1) -> None:
        self._run(["mousedown", str(button)])

    def release(self, button: int = 1) -> None:
        self._run(["mouseup", str(button)])

    def wheel(self, up: bool, count: int) -> None:
        # X wheel buttons: 4 up, 5 down. VTK reads them as zoom.
        self._run(["click", "--repeat", str(count), "--delay", "90", "4" if up else "5"])

    def type_text(self, text: str, delay_ms: int = 55) -> None:
        # --clearmodifiers: a modifier left held by an earlier key step would
        # turn the text into shortcuts.
        self._run(["type", "--clearmodifiers", "--delay", str(delay_ms), text])

    def key(self, keys: str) -> None:
        self._run(["key", "--clearmodifiers", keys])

    @staticmethod
    def _run(args: list[str]) -> None:
        subprocess.run(["xdotool", *args], check=False, capture_output=True)


def ease(t: float) -> float:
    """Ease-in-out, so the cursor starts and stops like a hand rather than a motor."""
    return 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2


# ── resolving a step's target to a point on screen ─────────────────────────────


class TargetError(RuntimeError):
    """A step named something that is not on screen."""


def resolve(window, target: dict[str, Any]):
    """Turn a step's target description into a global QPoint.

    Resolution happens when the step runs, not when it is read: a menu item
    does not exist until the click before it has opened the menu.
    """
    from PySide6.QtWidgets import QApplication

    if "point" in target:
        from PySide6.QtCore import QPoint
        x, y = target["point"]
        return QPoint(int(x), int(y))
    if "menu" in target:
        return _menu_bar_point(window, target["menu"])
    if "menu_item" in target:
        return _popup_item_point(target["menu_item"])
    if "file" in target:
        return _file_row_point(window, target["file"])
    if "group" in target:
        return _file_group_point(window, target["group"])
    if "tree" in target:
        return _tree_row_point(window, target["tree"], int(target.get("col", 0)))
    if "cell" in target:
        return _table_cell_point(window, target["cell"])
    if "tab" in target:
        return _tab_point(window, target["tab"])
    if "widget" in target:
        return _centre(_attr_path(window, target["widget"]))
    if "button" in target:
        # Dialogs come first: while one is up it is what the step is about, and
        # a main-window button of the same name would be unreachable anyway.
        root = QApplication.activeModalWidget() or QApplication.activeWindow() or window
        return _centre(_named_button(root, target["button"]))
    if "field" in target:
        root = QApplication.activeModalWidget() or QApplication.activeWindow() or window
        return _centre(_labelled_field(root, target["field"]))
    raise TargetError(f"step target names nothing resolvable: {target!r}")


def _centre(widget):
    if widget is None:
        raise TargetError("target widget is not there")
    if not widget.isVisible():
        raise TargetError(f"target {widget.objectName() or widget} is not visible")
    return widget.mapToGlobal(widget.rect().center())


def _attr_path(window, dotted: str):
    """Follow a dotted attribute path from the window, e.g. `editor_panel`."""
    obj: Any = window
    for part in dotted.split("."):
        obj = getattr(obj, part, None)
        if obj is None:
            raise TargetError(f"no widget at {dotted!r}")
    return obj


def _menu_bar_point(window, title: str):
    bar = window.menuBar()
    for action in bar.actions():
        if _plain(action.text()) == _plain(title):
            rect = bar.actionGeometry(action)
            return bar.mapToGlobal(rect.center())
    raise TargetError(f"no menu titled {title!r}")


def _popup_item_point(label: str):
    """Find an item in whichever menu is currently open.

    An exact label wins; failing that, a *unique* substring match does. The
    overlay menus in the 3-D panel are the reason for the second rule — their
    rows are generated (``box0  ·  boxToCell``, colour swatch and all), so a
    spec that had to name one exactly would be unwritable and would break on
    every change to the format. An ambiguous substring is an error rather than
    a guess: picking whichever row sorted first is how a take ends up quietly
    demonstrating the wrong shape.
    """
    from PySide6.QtWidgets import QApplication, QMenu

    # Every visible menu, not just the active popup: hovering a submenu open
    # makes *it* the active popup, and the row the next step wants is usually
    # still in the parent menu behind it.
    popup = QApplication.activePopupWidget()
    menus = [w for w in QApplication.topLevelWidgets()
             if isinstance(w, QMenu) and w.isVisible()]
    if isinstance(popup, QMenu) and popup in menus:
        menus.remove(popup)
        menus.insert(0, popup)
    if not menus:
        raise TargetError(f"no menu is open to hold an item {label!r}")

    wanted = _plain(label)
    partial: list[tuple[QMenu, Any]] = []
    for menu in menus:
        for action in menu.actions():
            text = _plain(action.text())
            if text == wanted:
                return _action_point(menu, action, label)
            if wanted in text:
                partial.append((menu, action))
    if len(partial) == 1:
        return _action_point(partial[0][0], partial[0][1], label)
    if partial:
        names = ", ".join(repr(_plain(a.text())) for _m, a in partial[:4])
        raise TargetError(f"menu item {label!r} matches more than one row: {names}")
    raise TargetError(f"no open menu holds an item {label!r}")


def _action_point(menu, action, label: str):
    if not action.isEnabled():
        raise TargetError(f"menu item {label!r} is disabled")
    return menu.mapToGlobal(menu.actionGeometry(action).center())


def _file_row_point(window, relative: str):
    panel = window.file_list_panel
    case_dir = window.state.current_case_dir or ""
    absolute = str(Path(case_dir) / relative) if case_dir else relative
    item = panel._find_item_by_path(absolute)
    if item is None:
        raise TargetError(f"no file row for {relative!r}")
    view = panel._list
    view.scrollToItem(item)
    return view.viewport().mapToGlobal(view.visualItemRect(item).center())


def _file_group_point(window, group: str):
    """A directory *header* row in the file list, e.g. `system`.

    Separate from `file` because a header names no file: the rows carry their
    group on ui/panels/file_list_panel.py's _HEADER_GROUP_ROLE and leave the
    path role empty, so _find_item_by_path cannot see them. The context menu a
    header offers — new file, add files from this directory — is only reachable
    by right-clicking one.
    """
    from ui.panels.file_list_panel import _HEADER_GROUP_ROLE

    panel = window.file_list_panel
    view = panel._list
    for i in range(view.count()):
        item = view.item(i)
        if item.data(_HEADER_GROUP_ROLE) == group:
            view.scrollToItem(item)
            return view.viewport().mapToGlobal(view.visualItemRect(item).center())
    raise TargetError(f"no file-list group header for {group!r}")


def _tree_row_point(window, key_path: list[str | int], column: int):
    tree = window.tree
    model = tree.model()
    if model is None:
        raise TargetError("the tree has no model — is a file open?")
    index = index_for_key_path(model, key_path)
    if not index.isValid():
        raise TargetError(f"no tree row at {_path_label(key_path)}")
    index = index.siblingAtColumn(column)
    tree.scrollTo(index)
    rect = tree.visualRect(index)
    if rect.isEmpty():
        raise TargetError(f"tree row {_path_label(key_path)} is collapsed or off-view")
    return tree.viewport().mapToGlobal(rect.center())


def _table_cell_point(window, names: list[str]):
    """A cell of the boundary table, named by its two headers.

    Order-independent — `["U", "movingWall"]` finds the same cell whichever way
    the table is turned — because Transpose swaps which of the pair is the row
    and which is the column, and a spec should not have to say which it
    currently is. The panel's centre is not an alternative: on a case with
    three patches the table occupies the top corner of it and the middle of the
    widget is empty space, where a click lands on nothing at all.
    """
    table = window.boundary_panel._table
    wanted = {_plain(name) for name in names}
    for row in range(table.rowCount()):
        head_row = table.verticalHeaderItem(row)
        if head_row is None:
            continue
        for col in range(table.columnCount()):
            head_col = table.horizontalHeaderItem(col)
            if head_col is None:
                continue
            if {_plain(head_row.text()), _plain(head_col.text())} != wanted:
                continue
            index = table.model().index(row, col)
            table.scrollTo(index)
            rect = table.visualRect(index)
            if rect.isEmpty():
                raise TargetError(f"boundary cell {names!r} is not on view")
            return table.viewport().mapToGlobal(rect.center())
    raise TargetError(f"no boundary cell for {names!r}")


def _tab_point(window, label: str):
    for tabs in (window.upper_tabs, window.bottom_tabs):
        bar = tabs.tabBar()
        for i in range(tabs.count()):
            if _plain(tabs.tabText(i)) == _plain(label):
                return bar.mapToGlobal(bar.tabRect(i).center())
    raise TargetError(f"no tab labelled {label!r}")


def _named_button(root, label: str):
    """A button by its visible text, exactly, or by a unique substring of it.

    The substring rule is _popup_item_point's, for the same reason: some labels
    count what they are about — the add-files dialog's button reads `Add
    Selected (1)` — and a spec that had to name the number would be asserting
    the state of a checkbox list in a step that is about clicking a button.
    """
    from PySide6.QtWidgets import QAbstractButton

    wanted = _plain(label)
    buttons = [b for b in root.findChildren(QAbstractButton) if b.isVisible()]
    partial = []
    for button in buttons:
        text = _plain(button.text())
        if text == wanted:
            return button
        if wanted in text:
            partial.append(button)
    if len(partial) == 1:
        return partial[0]
    if partial:
        names = ", ".join(repr(_plain(b.text())) for b in partial[:4])
        raise TargetError(f"button {label!r} matches more than one: {names}")
    raise TargetError(f"no button labelled {label!r} in {root.windowTitle() or root}")


def _labelled_field(root, label: str):
    """The input a form row's label belongs to, e.g. `New case name:`.

    A dialog's own widgets are not reachable by attribute path — that grammar
    starts at MainWindow — and its inputs carry no text of their own to be
    named by. What they do carry is the label beside them, which is what the
    person watching reads too.
    """
    from PySide6.QtWidgets import QFormLayout, QLabel

    wanted = _plain(label)
    for form in root.findChildren(QFormLayout):
        for row in range(form.rowCount()):
            item = form.itemAt(row, QFormLayout.ItemRole.LabelRole)
            widget = item.widget() if item is not None else None
            if not isinstance(widget, QLabel) or _plain(widget.text()) != wanted:
                continue
            field = form.itemAt(row, QFormLayout.ItemRole.FieldRole)
            if field is None:
                break
            if field.widget() is not None:
                return field.widget()
            # A row holding a layout — an edit with a Browse button beside it.
            # The input is the first thing in it, which is also the leftmost.
            inner = field.layout()
            if inner is not None and inner.count():
                return inner.itemAt(0).widget()
    raise TargetError(f"no form field labelled {label!r} in {root.windowTitle() or root}")


def _path_label(key_path: list[str | int]) -> str:
    """A tree key path as it reads in an error — block rows address by index."""
    return "/".join(str(part) for part in key_path)


def _plain(text: str) -> str:
    """Compare menu and button labels ignoring accelerators and ellipsis style."""
    return text.replace("&", "").replace("…", "...").strip()


# ── the step machine ──────────────────────────────────────────────────────────

Atom = tuple[int, Callable[[], None]]  # (delay before running, what to do)


class Runner:
    """Runs a scene's steps as a chain of timers.

    A step expands into atoms — resolve a target, glide the cursor, click — and
    an atom may push more atoms in front of the rest, which is how a target
    that only exists once the previous atom ran (a menu item) is resolved late.
    """

    def __init__(self, window, pointer: Pointer, steps: list[dict[str, Any]],
                 captions: Captions, on_finish: Callable[[int], None]) -> None:
        self.window = window
        self.pointer = pointer
        self.captions = captions
        self._steps = deque(steps)
        self._queue: deque[Atom] = deque()
        self._on_finish = on_finish
        self._failed = 0
        self._popup_was_open = False

    def push(self, atoms: list[Atom]) -> None:
        self._queue.extendleft(reversed(atoms))

    def start(self) -> None:
        self._tick()

    # ── the chain ─────────────────────────────────────────────────────────────

    def _tick(self) -> None:
        from PySide6.QtCore import QTimer

        if not self._queue:
            if not self._steps:
                self._on_finish(self._failed)
                return
            step = self._steps.popleft()
            if not self._guarded(lambda: self._expand(step)):
                return
            QTimer.singleShot(0, self._tick)
            return
        delay, action = self._queue.popleft()

        def run() -> None:
            if self._guarded(action):
                self._tick()

        QTimer.singleShot(delay, run)

    def _guarded(self, action: Callable[[], None]) -> bool:
        """Run one atom, ending the take on anything it raises.

        Broad on purpose: this runs inside a timer callback, where an escaping
        exception is printed and then *ignored* — the loop would keep spinning
        over a demo that had already stopped making sense, and the take would
        have to be killed from outside.
        """
        try:
            action()
            return True
        except TargetError as exc:
            # A demo is authored against a UI that moves; saying which step lost
            # its target beats a traceback from inside a timer, and a frame of
            # what was actually on screen beats both.
            print(f"  ✗ {exc}", file=sys.stderr)
        except Exception:
            import traceback
            traceback.print_exc()
        _dump_failure(self.window)
        self._failed += 1
        self._on_finish(self._failed)
        return False

    def _expand(self, step: dict[str, Any]) -> None:
        kind = step.get("do")
        if not kind:
            raise TargetError(f"step has no 'do': {step!r}")
        beat = step.get("beat", "")
        dwell = int(step.get("then", DEFAULT_DWELL_MS))
        atoms: list[Atom] = []
        if beat or "say" in step:
            atoms.append((0, lambda: self.captions.mark(beat, step.get("say", ""))))

        handler = getattr(self, f"_step_{kind}", None)
        if handler is None:
            raise TargetError(f"unknown step {kind!r}")
        atoms.extend(handler(step))
        atoms.append((400, self._clear_closed_popup))
        atoms.append((dwell, lambda: None))
        self.push(atoms)

    def _clear_closed_popup(self) -> None:
        """Scrub the pixels a menu leaves behind when it closes.

        On the nested display a dismissed menu stays on screen over anything
        that does not redraw itself. The 3-D view is immune — VTK repaints it —
        so what is left is a menu-shaped hole over the editor, for as long as
        it takes something else to draw there. `repaint()` does not shift it
        and neither does `xrefresh`; a resize does, because it invalidates
        every widget's geometry rather than just its contents. One pixel, for
        one frame, and put straight back.
        """
        from PySide6.QtWidgets import QApplication

        open_now = QApplication.activePopupWidget() is not None
        if self._popup_was_open and not open_now:
            size = self.window.size()
            self.window.resize(size.width(), size.height() - 1)
            self.window.resize(size)
        self._popup_was_open = open_now

    # ── step kinds ────────────────────────────────────────────────────────────

    def _step_wait(self, step: dict[str, Any]) -> list[Atom]:
        return [(int(step.get("ms", 1000)), lambda: None)]

    def _step_move(self, step: dict[str, Any]) -> list[Atom]:
        return [(0, lambda: self.push(self._glide_atoms(step)))]

    def _step_click(self, step: dict[str, Any]) -> list[Atom]:
        # "with", not "button": `button` is already a target — the name of the
        # push button to click — and a step naming one would otherwise be read
        # as asking for a mouse button called "Save File".
        buttons = {"left": 1, "middle": 2, "right": 3}
        which = step.get("with", "left")
        if which not in buttons:
            raise TargetError(f"no mouse button {which!r} (left, middle or right)")
        button = buttons[which]
        count = 2 if step.get("double") else 1

        def go() -> None:
            # One push, in order: the glide's atoms and then the click. Two
            # pushes would put the second in front of the first — push prepends,
            # which is what lets an atom schedule work before what follows it.
            atoms = self._glide_atoms(step)
            atoms.append((120, lambda: self.pointer.click(button, count)))
            self.push(atoms)

        return [(0, go)]

    def _step_drag(self, step: dict[str, Any]) -> list[Atom]:
        """Press at the target, move by `by`, release — an orbit of the 3-D view."""
        dx, dy = step["by"]

        def go() -> None:
            atoms = self._glide_atoms(step)
            atoms.append((200, self.pointer.press))
            x0, y0 = None, None

            def start() -> None:
                nonlocal x0, y0
                x0, y0 = self.pointer.x, self.pointer.y

            atoms.append((0, start))
            # Dragged in its own ticks rather than one jump, because VTK orbits
            # by the *increments* it is sent: a single large delta spins the
            # camera the same amount but skips every frame in between, and the
            # recording is of those frames.
            #
            # `ticks` is worth setting per scene. Each one costs a re-render,
            # and a heavy scene re-renders slowly enough that the default turns
            # a 1.4-second orbit into a 24-second one — the motorBike surface
            # does exactly that. Fewer, larger steps stay smooth because the
            # frames are what is slow, not the motion.
            ticks = int(step.get("ticks", 0)) or max(
                1, int(step.get("ms", 900)) // GLIDE_TICK_MS
            )
            for i in range(1, ticks + 1):
                f = ease(i / ticks)

                def hop(f: float = f) -> None:
                    assert x0 is not None and y0 is not None
                    self.pointer.move(round(x0 + dx * f), round(y0 + dy * f))

                atoms.append((GLIDE_TICK_MS, hop))
            atoms.append((150, self.pointer.release))
            self.push(atoms)

        return [(0, go)]

    def _step_scroll(self, step: dict[str, Any]) -> list[Atom]:
        up = step.get("direction", "up") == "up"
        count = int(step.get("amount", 3))

        def go() -> None:
            atoms = self._glide_atoms(step)
            atoms.append((150, lambda: self.pointer.wheel(up, count)))
            self.push(atoms)

        return [(0, go)]

    def _step_type(self, step: dict[str, Any]) -> list[Atom]:
        text = step["text"]
        return [(0, lambda: self.pointer.type_text(text, int(step.get("delay", 55))))]

    def _step_key(self, step: dict[str, Any]) -> list[Atom]:
        return [(0, lambda: self.pointer.key(step["keys"]))]

    def _step_say(self, step: dict[str, Any]) -> list[Atom]:
        # The caption was already marked by _expand; this is just its dwell.
        return [(int(step.get("ms", 0)), lambda: None)]

    def _glide_atoms(self, step: dict[str, Any]) -> list[Atom]:
        """The atoms that walk the cursor to the step's target, as a hand would."""
        point = resolve(self.window, step)
        x0, y0 = self.pointer.x, self.pointer.y
        x1, y1 = point.x(), point.y()
        ticks = max(1, GLIDE_MS // GLIDE_TICK_MS)
        atoms: list[Atom] = []
        for i in range(1, ticks + 1):
            f = ease(i / ticks)
            step_x, step_y = round(x0 + (x1 - x0) * f), round(y0 + (y1 - y0) * f)

            def hop(x: int = step_x, y: int = step_y) -> None:
                self.pointer.move(x, y)

            atoms.append((GLIDE_TICK_MS, hop))
        return atoms


def _dump_failure(window) -> None:
    """Save what was on screen when a step lost its target."""
    path = Path("/tmp") / f"fode-demo-failure-{int(time.time())}.png"
    result = subprocess.run(
        ["import", "-window", "root", str(path)], capture_output=True, text=True,
    )
    if result.returncode == 0 and path.exists():
        print(f"  screen at failure → {path}", file=sys.stderr)


class Captions:
    """Records what was said and when, as a subtitle file beside the video.

    The narration is not spoken by the tool — it is written next to the frames
    it belongs to, so whoever records the voice-over, or writes the blog post
    the movie sits in, is reading a script that is already in sync.
    """

    def __init__(self) -> None:
        self.started = time.monotonic()
        self.entries: list[tuple[float, str, str]] = []

    def mark(self, beat: str, say: str) -> None:
        at = time.monotonic() - self.started
        self.entries.append((at, beat, say))
        label = say or beat
        if label:
            print(f"  {at:6.1f}s  {label}")

    def write_srt(self, path: Path) -> None:
        spoken = [(at, text) for at, _beat, text in self.entries if text]
        if not spoken:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []
        for i, (at, text) in enumerate(spoken, start=1):
            end = spoken[i][0] if i < len(spoken) else at + 4.0
            lines.append(f"{i}\n{_srt_time(at)} --> {_srt_time(end)}\n{text}\n")
        path.write_text("\n".join(lines), encoding="utf-8")
        print(f"  captions → {path}")


def _srt_time(seconds: float) -> str:
    ms = int(seconds * 1000)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ── recording ─────────────────────────────────────────────────────────────────


class Recorder:
    """ffmpeg's x11grab, pointed at the window's own rectangle."""

    def __init__(self, out_path: Path, rect, fps: int) -> None:
        if shutil.which("ffmpeg") is None:
            raise SystemExit("Error: ffmpeg is required to record (apt install ffmpeg).")
        self.out_path = out_path
        # A GIF is encoded from the video afterwards rather than grabbed
        # directly: x11grab straight to GIF has no palette pass and bands badly.
        self.video_path = (
            out_path if out_path.suffix.lower() != ".gif"
            else out_path.with_suffix(".mp4")
        )
        # libx264 needs even dimensions; cropping a pixel beats being rejected.
        self.width = rect.width() - rect.width() % 2
        self.height = rect.height() - rect.height() % 2
        self.x, self.y = max(0, rect.x()), max(0, rect.y())
        self.fps = fps
        self._proc: subprocess.Popen | None = None

    def start(self) -> None:
        self.video_path.parent.mkdir(parents=True, exist_ok=True)
        display = os.environ.get("DISPLAY", ":0")
        command = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "x11grab", "-draw_mouse", "1",
            "-framerate", str(self.fps),
            "-video_size", f"{self.width}x{self.height}",
            "-i", f"{display}+{self.x},{self.y}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p",
            str(self.video_path),
        ]
        self._proc = subprocess.Popen(command, stdin=subprocess.PIPE)
        print(f"  recording {self.width}x{self.height} at {self.x},{self.y} → {self.video_path}")

    def stop(self) -> None:
        if self._proc is None:
            return
        # SIGINT, not kill: ffmpeg has to write the container's index, and a
        # killed recording is a file no player will seek in.
        self._proc.send_signal(signal.SIGINT)
        try:
            self._proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            self._proc.kill()
        self._proc = None
        if self.out_path is not self.video_path:
            self._to_gif()

    def _to_gif(self) -> None:
        """Two-pass palette encode — the only way a GIF of a UI stays readable."""
        palette = self.video_path.with_suffix(".palette.png")
        scale = "fps=12,scale=900:-1:flags=lanczos"
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(self.video_path),
             "-vf", f"{scale},palettegen=stats_mode=diff", str(palette)],
            check=True,
        )
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(self.video_path),
             "-i", str(palette), "-lavfi",
             f"{scale}[v];[v][1:v]paletteuse=dither=bayer:bayer_scale=3",
             str(self.out_path)],
            check=True,
        )
        palette.unlink(missing_ok=True)
        print(f"  gif → {self.out_path}")


# ── the worker: one window, one scene ─────────────────────────────────────────


def play(scene: Scene, out_path: Path | None, settle_ms: int, fps: int,
         stage_only: bool, max_seconds: int, workdir: Path) -> int:
    """Open the window in the scene's start state and run its steps."""
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from i18n import set_language
    from ui.main_window import MainWindow
    from ui.theme import apply_theme

    prepare_case(scene)
    seed_app_config(scene, workdir)

    from PySide6.QtCore import Qt

    # Qt's own file dialog rather than the desktop's, for two reasons that both
    # only apply to a take. The portal chooser cannot be driven — it is another
    # process, so none of its widgets are reachable and its keyboard shortcuts
    # differ per desktop — and it opens on the home directory with the user's
    # account name across the top, which is the one thing a published movie
    # must not show. Users see whichever their desktop provides; this is the
    # recording rig, not a change to the app.
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeDialogs, True)

    app = QApplication([sys.argv[0]])
    apply_theme(app, scene.theme)
    # Demo movies are English; the saved language setting must not leak in.
    set_language("en")
    _disable_ui_effects(app)

    window = MainWindow()
    if scene.state.window_size is not None:
        window.resize(*scene.state.window_size)
    window.show()
    # A known corner, fully on screen: x11grab reads the screen, so a window
    # hanging off the edge would record the desktop instead.
    window.move(0, 0)
    _process_events(app, 300)

    apply_window_state(window, scene.state, settle=lambda: _process_events(app, 600))
    _process_events(app, settle_ms)
    # Re-applied because the settle window is exactly when the deferred
    # re-render that resets the camera happens.
    apply_block_mesh_view(window, scene.state)
    _process_events(app, 400)

    for command in scene.terminal_prelude:
        if window.terminal_panel is None:
            print("  warning: scene has a terminal_prelude but this variant has no "
                  "terminal", file=sys.stderr)
            break
        window.terminal_panel.run_command(command)
        _process_events(app, 1200)

    # Transient parse/save feedback, and it would put the machine's absolute
    # case path on screen for the whole take.
    window.statusBar().clearMessage()
    window.raise_()
    window.activateWindow()
    _process_events(app, 500)

    if stage_only:
        print(f"[{scene.name}] staged; close the window to print the state it ended in.")
        app.exec()
        print(json.dumps(capture_window_state(window).to_dict(), indent=2))
        return 0

    pointer = Pointer()
    # Park the cursor where it is out of the way but inside the window, so the
    # first glide starts from somewhere sensible rather than wherever the last
    # person left the mouse.
    frame = window.frameGeometry()
    pointer.move(frame.center().x(), frame.bottom() - 30)

    captions = Captions()
    recorder = Recorder(out_path, frame, fps) if out_path else None
    if recorder is not None:
        recorder.start()
        # Let the first frames be the untouched window, and let ffmpeg get
        # going before anything worth seeing happens.
        _process_events(app, 1200)
        captions.started = time.monotonic()

    code = 0
    done = False

    def finish(failures: int) -> None:
        nonlocal code, done
        if done:
            return
        done = True
        code = 1 if failures else 0
        _process_events(app, 800)  # a beat of stillness to end on
        # A modal dialog runs its own event loop, and app.quit() only ends the
        # outermost one — so a take that stopped with a dialog still up would
        # hang here, waiting for a click that is never coming.
        for _ in range(5):
            modal = QApplication.activeModalWidget()
            if modal is None:
                break
            print(f"  closing {modal.windowTitle() or 'a dialog'} left open by the take")
            modal.close()
            _process_events(app, 250)
        app.quit()

    runner = Runner(window, pointer, scene.steps, captions, finish)
    # The watchdog exists because the failure it catches is the expensive one:
    # a take that hangs holds the display, and whoever started it finds out by
    # noticing, not by being told.
    watchdog = QTimer()
    watchdog.setSingleShot(True)
    def give_up() -> None:
        print(f"  ✗ watchdog: no end after {max_seconds}s", file=sys.stderr)
        _dump_failure(window)
        finish(1)

    watchdog.timeout.connect(give_up)
    watchdog.start(max_seconds * 1000)
    runner.start()
    app.exec()

    if recorder is not None:
        recorder.stop()
        captions.write_srt(recorder.out_path.with_suffix(".srt"))

    # Not window.close(): closeEvent saves the window size and the session to
    # app_config.json, and a demo must not change the user's settings.
    if window.block_mesh_panel is not None:
        window.block_mesh_panel.shutdown()
    if window.terminal_panel is not None:
        window.terminal_panel.cleanup()
    return code


def _disable_ui_effects(app) -> None:
    """Turn off menu and tooltip animation for the take.

    A dismissed menu is faded out through a top-level window of its own, and on
    a display with no compositor that window can be left on screen — the next
    beat then plays under a ghost menu that Qt no longer believes exists, which
    is why repainting everything underneath does not clear it. Switching the
    effects off removes the extra window rather than the symptom, and a
    recording wants deterministic frames regardless.
    """
    from PySide6.QtCore import Qt

    for effect in (
        Qt.UIEffect.UI_AnimateMenu,
        Qt.UIEffect.UI_FadeMenu,
        Qt.UIEffect.UI_AnimateCombo,
        Qt.UIEffect.UI_AnimateTooltip,
        Qt.UIEffect.UI_FadeTooltip,
        Qt.UIEffect.UI_AnimateToolBox,
    ):
        app.setEffectEnabled(effect, False)


def _process_events(app, milliseconds: int) -> None:
    """Run the event loop for a fixed time, so timers and renders complete."""
    from PySide6.QtCore import QEventLoop, QTimer

    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    loop.exec()
    app.processEvents()


# ── entry point ───────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("scene", nargs="?", metavar="SCENE", help="scene name to play")
    parser.add_argument("--list", action="store_true", help="list the spec's scenes and exit")
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC, metavar="FILE",
                        help=f"spec file (default: {DEFAULT_SPEC.relative_to(ROOT)})")
    parser.add_argument("--record", type=Path, nargs="?", const=RECORD_DEFAULT,
                        metavar="FILE",
                        help="record the take (.mp4, or .gif for a two-pass palette encode); "
                             f"with no filename, {DEFAULT_OUT.relative_to(ROOT)}/<scene>.mp4")
    parser.add_argument("--stage", action="store_true",
                        help="apply the start state and stop there, leaving the window open "
                             "for recording by hand; prints the state it was closed in")
    parser.add_argument("--theme", choices=THEMES, metavar="THEME",
                        help="override the scene's theme")
    parser.add_argument("--on-this-display", action="store_true",
                        help="drive the take on $DISPLAY instead of a nested one. Only for a "
                             "desktop nobody is using: the steps are real mouse and keyboard "
                             "input, so another window raising itself takes the clicks, and "
                             "whatever a step types goes wherever focus went")
    parser.add_argument("--display", metavar=":N",
                        help="drive the take on this display, already running")
    parser.add_argument("--fps", type=int, default=30, metavar="N", help="recording frame rate")
    parser.add_argument("--cases-dir", type=Path,
                        default=Path(os.environ.get("FODE_CASES_DIR") or DEFAULT_CASES),
                        metavar="DIR",
                        help="where the spec's {cases} placeholder points "
                             f"(default: $FODE_CASES_DIR or {DEFAULT_CASES})")
    parser.add_argument("--workdir", type=Path, default=DEFAULT_WORKDIR, metavar="DIR",
                        help=f"where {{work}} points — scratch case copies (default: {DEFAULT_WORKDIR})")
    parser.add_argument("--settle", type=int, default=DEFAULT_SETTLE_MS, metavar="MS",
                        help=f"settle time before the first step (default: {DEFAULT_SETTLE_MS})")
    parser.add_argument("--max-seconds", type=int, default=DEFAULT_MAX_SECONDS, metavar="S",
                        help="give up on a take that has not ended by then "
                             f"(default: {DEFAULT_MAX_SECONDS})")
    args = parser.parse_args()

    try:
        spec = load_spec(args.spec, args.cases_dir, args.workdir)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        sys.exit(f"Error reading {args.spec}: {exc}")

    if args.list:
        for scene in spec:
            print(f"{scene.name}\n    {len(scene.steps)} steps, theme {scene.theme}"
                  + (f"\n    {scene.note}" if scene.note else ""))
        return

    by_name = {scene.name: scene for scene in spec}
    if args.scene not in by_name:
        sys.exit(f"Error: {'unknown scene ' + repr(args.scene) if args.scene else 'no scene named'}."
                 f"\nKnown scenes: {', '.join(by_name)}")
    scene = by_name[args.scene]
    if args.theme:
        import dataclasses
        scene = dataclasses.replace(scene, theme=args.theme)

    if not os.environ.get("DISPLAY"):
        sys.exit("Error: DISPLAY is not set. A real X display is required "
                 "(offscreen Qt aborts VTK, and xdotool has nothing to drive).")

    record = args.record
    if record == RECORD_DEFAULT:
        record = DEFAULT_OUT / f"{scene.name}.mp4"

    print(f"→ {scene.name}")
    # A nested display unless told otherwise, because the default has to be the
    # safe one: a take driven across someone's desktop types into whatever
    # window happened to take focus. --stage is the exception — its whole point
    # is to hand the window to a person, who needs it where they can see it.
    nested: NestedDisplay | None = None
    if args.display:
        os.environ["DISPLAY"] = args.display
    elif not args.on_this_display and not args.stage:
        width, height = scene.state.window_size or (1280, 800)
        nested = NestedDisplay(width, height)
        os.environ["DISPLAY"] = nested.start()

    try:
        code = play(scene, record, args.settle, args.fps, args.stage,
                    args.max_seconds, Path(args.workdir))
    finally:
        if nested is not None:
            nested.stop()
    # os._exit: VTK's teardown at interpreter exit can abort even after a clean
    # shutdown(), which would report a finished take as a failure.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)


if __name__ == "__main__":
    main()
