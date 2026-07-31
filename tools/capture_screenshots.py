#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Capture the docs/images gallery from a spec, reproducibly.

Every shot in the gallery used to be taken by hand, which made retakes
expensive enough that images went stale (the main-window shot outlived the
Tools menu, the key filter box and the case-root file group). This script
takes the same window state twice — once per theme — and produces a matched
pair that differs in nothing but colour.

Usage:
    # the whole gallery, both themes, into docs/images/:
    DISPLAY=:1 python3 tools/capture_screenshots.py --all

    # one shot, one theme, somewhere harmless first:
    DISPLAY=:1 python3 tools/capture_screenshots.py main-window-tree-editor \\
        --theme light --out /tmp/shots

    # what the spec defines:
    python3 tools/capture_screenshots.py --list

    # open a window in a shot's state and keep it: adjust the camera or the
    # splitters by hand, close it, and the state it ended in is printed as the
    # JSON to paste back into the spec.
    DISPLAY=:1 python3 tools/capture_screenshots.py main-window-tree-editor --interactive

A real X display is required and DISPLAY must point at it: offscreen Qt aborts
VTK, so there is no headless mode to fall back on. Capture goes through
ImageMagick's `import -frame`, not QWidget.grab(), for two reasons — grab()
returns black for the 3-D panel's native child window, and `-frame` keeps the
title bar and borders every existing gallery image has.

Each shot runs in its own process (this script re-executes itself), so no shot
can inherit stray state from the one before it. Nothing is written back to
app_config.json: the theme comes from --theme rather than the saved setting,
and the window is never closed, so MainWindow.closeEvent never runs.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# Same reason as main.py: must be set before QApplication exists.
os.environ.setdefault(
    "QTWEBENGINE_CHROMIUM_FLAGS",
    "--disable-gpu --disable-vulkan --log-level=2",
)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ui.window_state import WindowState, capture_window_state  # noqa: E402

DEFAULT_SPEC = ROOT / "tools" / "screenshot_specs.json"
DEFAULT_OUT = ROOT / "docs" / "images"
DEFAULT_CASES = Path.home() / "OpenFOAM" / "nakagawa-v2512" / "run"
# The gallery is captured in "light" and "dark", never "system": a system-themed
# window inherits the capture machine's desktop palette, which is the one thing
# about a shot that cannot be reproduced elsewhere. "system" is still accepted,
# for capturing what a default install actually looks like.
THEMES = ("light", "dark", "system")
GALLERY_THEMES = ("light", "dark")

# How long to let the window settle before capturing. The 3-D panel is what
# needs it: VTK re-initialises 300 ms after the terminal switches out of xterm
# mode, and the scene it then draws has to reach the screen before the X server
# is asked for those pixels.
DEFAULT_SETTLE_MS = 2500


@dataclass(frozen=True)
class Shot:
    """One gallery image: a window state plus where each theme's file goes."""

    name: str
    state: WindowState
    outputs: dict[str, str]  # theme → filename
    note: str = ""
    # Reference case for compare mode. Deliberately not a WindowState field:
    # WindowState is shared with ui/session_restore.py, so a field there would
    # change what a saved session restores — a product decision, not a
    # screenshot one — and compare mode is a consequence rather than the sort of
    # choice that module holds (starting it forces side-by-side on).
    compare_with: str = ""


def load_spec(path: Path, cases_dir: Path) -> list[Shot]:
    """Read the spec file, applying its defaults and expanding path placeholders."""
    data = json.loads(path.read_text(encoding="utf-8"))
    defaults = WindowState.from_dict(data.get("defaults") or {})

    shots: list[Shot] = []
    for name, entry in data["shots"].items():
        unknown = sorted(set(entry) - {"outputs", "state", "note", "compare_with"})
        if unknown:
            raise ValueError(f"shot {name!r}: unknown key(s) {', '.join(unknown)}")
        state = defaults.merged_with(WindowState.from_dict(entry.get("state") or {}))
        if state.case_dir:
            state = _resolve_case_dir(state, cases_dir)
        outputs = entry.get("outputs") or {}
        unknown_themes = sorted(set(outputs) - set(THEMES))
        if unknown_themes:
            raise ValueError(f"shot {name!r}: unknown theme(s) {', '.join(unknown_themes)}")
        compare_with = entry.get("compare_with") or ""
        if compare_with:
            compare_with = _expand_case_path(compare_with, cases_dir)
        shots.append(Shot(
            name=name, state=state, outputs=outputs,
            note=entry.get("note", ""), compare_with=compare_with,
        ))
    return shots


def _expand_case_path(raw: str, cases_dir: Path) -> str:
    """Expand {repo} / {cases} and ~ in a spec path.

    Gallery shots point at cases outside the repository, which live wherever the
    person capturing them keeps their OpenFOAM runs — hence {cases} and the
    --cases-dir option, rather than an absolute path baked into the spec.
    """
    return str(Path(raw.format(repo=ROOT, cases=cases_dir)).expanduser())


def _resolve_case_dir(state: WindowState, cases_dir: Path) -> WindowState:
    """Expand the placeholders in a shot's own case directory."""
    assert state.case_dir is not None  # only called when it is set
    return dataclasses.replace(
        state, case_dir=_expand_case_path(state.case_dir, cases_dir)
    )


# ── the worker: one window, one theme, one capture ─────────────────────────────


def capture_one(shot: Shot, theme: str, out_path: Path | None, settle_ms: int) -> int:
    """Build a window in the shot's state and capture it. Returns an exit code.

    ``out_path`` of None is interactive mode: the window is left open instead,
    and the state it is closed in is printed for pasting back into the spec.
    """
    from PySide6.QtWidgets import QApplication

    from i18n import set_language
    from ui.main_window import MainWindow
    from ui.theme import apply_theme
    from ui.window_state import apply_block_mesh_view, apply_window_state

    app = QApplication([sys.argv[0]])
    apply_theme(app, theme)
    # Gallery images are English; the saved language setting must not leak in.
    set_language("en")

    window = MainWindow()
    if shot.state.window_size is not None:
        window.resize(*shot.state.window_size)
    window.show()
    # A known corner, fully on screen: `import` reads the screen, so anything
    # overlapping or off the edge would be captured instead of the window.
    window.move(0, 0)
    _process_events(app, 300)

    # The settle hook runs at the points where Qt needs an event-loop turn
    # before the next step can see the result (see apply_window_state).
    apply_window_state(window, shot.state, settle=lambda: _process_events(app, 600))
    if shot.compare_with:
        if not Path(shot.compare_with).is_dir():
            raise SystemExit(f"{shot.name}: no reference case at {shot.compare_with}")
        # The app's own entry point (Case > Compare with Case…, and the Find
        # Examples dialog, both land here), so the shot shows the real thing.
        window._start_comparison_with(shot.compare_with)
        # The per-file diff counts are precomputed on a zero-timer, and the
        # file-list marks only appear once that has run.
        _process_events(app, 800)
        # Starting a comparison un-hides the reference pane, and Qt shares the
        # new space out for itself — so any pinned sizes have to be set again
        # now rather than before. Splitter-only: every other field is None and
        # every step of apply_window_state is guarded on its own field.
        apply_window_state(
            window, WindowState(splitter_sizes=shot.state.splitter_sizes)
        )
    _process_events(app, settle_ms)
    # Re-applied because the settle window is exactly when the deferred
    # re-render that resets the camera happens.
    apply_block_mesh_view(window, shot.state)
    _process_events(app, 400)

    if out_path is None:
        print(f"[{shot.name}] window open; close it to print the state it ended in.")
        app.exec()
        print(json.dumps(capture_window_state(window).to_dict(), indent=2))
        return 0

    # Transient parse/save feedback, not layout — and it would put the capture
    # machine's absolute case path in the image.
    window.statusBar().clearMessage()
    window.raise_()
    window.activateWindow()
    _process_events(app, 300)
    if not _wait_for_active(app, window):
        # The window manager draws an unfocused title bar in a different shade,
        # which is the one part of a capture that can differ between two runs of
        # the same spec. Worth saying out loud rather than shipping the mismatch.
        print(f"warning: {shot.name} never became the active window; "
              "its title bar may not match the rest of the gallery", file=sys.stderr)

    try:
        capture_window(int(window.winId()), out_path)
    finally:
        # Not window.close(): closeEvent saves the window size to app_config.json,
        # and a capture must not change the user's settings.
        if window.block_mesh_panel is not None:
            window.block_mesh_panel.shutdown()
        if window.terminal_panel is not None:
            window.terminal_panel.cleanup()
    return 0


def _wait_for_active(app, window, attempts: int = 10) -> bool:
    """Poll until the window manager has made *window* the active window."""
    for _ in range(attempts):
        if window.isActiveWindow():
            return True
        window.activateWindow()
        _process_events(app, 200)
    return window.isActiveWindow()


def _process_events(app, milliseconds: int) -> None:
    """Run the event loop for a fixed time, so timers and renders complete."""
    from PySide6.QtCore import QEventLoop, QTimer

    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    loop.exec()
    app.processEvents()


# ── X-level capture ───────────────────────────────────────────────────────────


def capture_window(window_id: int, out_path: Path) -> None:
    """Save the window, decorations included, via ImageMagick's import."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["import", "-frame", "-window", str(window_id), str(out_path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or not out_path.exists():
        raise RuntimeError(f"import failed: {result.stderr.strip() or result.returncode}")


# ── the driver: one process per shot per theme ─────────────────────────────────


def run_shots(shots: list[Shot], themes: list[str], out_dir: Path, args) -> int:
    failures = 0
    for shot in shots:
        for theme in themes:
            filename = shot.outputs.get(theme)
            if filename is None:
                print(f"– {shot.name} [{theme}]: no output defined, skipped")
                continue
            out_path = out_dir / filename
            command = [
                sys.executable, str(Path(__file__).resolve()),
                shot.name, "--theme", theme,
                "--spec", str(args.spec), "--out", str(out_dir),
                "--cases-dir", str(args.cases_dir),
                "--settle", str(args.settle),
                "--_worker",
            ]
            print(f"→ {shot.name} [{theme}] → {out_path}")
            result = subprocess.run(command)
            if result.returncode != 0:
                failures += 1
                print(f"✗ {shot.name} [{theme}] failed (exit {result.returncode})")
    return 1 if failures else 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("shots", nargs="*", metavar="SHOT", help="shot names to capture")
    parser.add_argument("--all", action="store_true", help="capture every shot in the spec")
    parser.add_argument("--list", action="store_true", help="list the spec's shots and exit")
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC, metavar="FILE",
                        help=f"spec file (default: {DEFAULT_SPEC.relative_to(ROOT)})")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, metavar="DIR",
                        help=f"output directory (default: {DEFAULT_OUT.relative_to(ROOT)})")
    parser.add_argument("--theme", action="append", choices=THEMES, metavar="THEME",
                        help="capture this theme only; repeatable (default: every theme the "
                             "shot defines an output for)")
    parser.add_argument("--cases-dir", type=Path,
                        default=Path(os.environ.get("FODE_CASES_DIR") or DEFAULT_CASES),
                        metavar="DIR",
                        help="where the spec's {cases} placeholder points "
                             f"(default: $FODE_CASES_DIR or {DEFAULT_CASES})")
    parser.add_argument("--settle", type=int, default=DEFAULT_SETTLE_MS, metavar="MS",
                        help=f"settle time before capture (default: {DEFAULT_SETTLE_MS})")
    parser.add_argument("--interactive", action="store_true",
                        help="apply one shot's state, leave the window open, and print the "
                             "state it was closed in (for authoring a spec)")
    parser.add_argument("--_worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    try:
        spec = load_spec(args.spec, args.cases_dir)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        sys.exit(f"Error reading {args.spec}: {exc}")

    if args.list:
        for shot in spec:
            themes = ", ".join(f"{t}→{f}" for t, f in sorted(shot.outputs.items()))
            print(f"{shot.name}\n    {themes}" + (f"\n    {shot.note}" if shot.note else ""))
        return

    by_name = {shot.name: shot for shot in spec}
    if args.all:
        selected = spec
    else:
        unknown = [name for name in args.shots if name not in by_name]
        if unknown or not args.shots:
            sys.exit(
                f"Error: {'unknown shot(s): ' + ', '.join(unknown) if unknown else 'no shot named'}."
                f"\nKnown shots: {', '.join(by_name)}\nOr pass --all."
            )
        selected = [by_name[name] for name in args.shots]

    if not os.environ.get("DISPLAY"):
        sys.exit("Error: DISPLAY is not set. A real X display is required (offscreen Qt aborts VTK).")

    themes = args.theme or list(GALLERY_THEMES)

    if args.interactive:
        if len(selected) != 1:
            sys.exit("Error: --interactive takes exactly one shot.")
        sys.exit(capture_one(selected[0], themes[0], None, args.settle))

    if args._worker:
        shot = selected[0]
        theme = themes[0]
        filename = shot.outputs.get(theme) or f"{shot.name}-{theme}.png"
        code = capture_one(shot, theme, args.out / filename, args.settle)
        # os._exit: VTK's teardown at interpreter exit can abort even after a
        # clean shutdown(), which would report a successful capture as a failure.
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(code)

    sys.exit(run_shots(selected, themes, args.out, args))


if __name__ == "__main__":
    main()
