# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Structural checks on tools/demo_specs.json's scene list.

The counterpart to TestScreenshotSpec in tests/ui/test_window_state.py and to
tests/tools/test_capture_dialog.py, and it matters more than either: a take
needs a real X display, an OpenFOAM installation and about a minute of wall
clock, so a scene that names a renamed menu item fails halfway through a
recording rather than in the suite. Everything checkable without a display is
checked here.

The step kinds are read off `Runner` rather than listed, so a new one cannot be
added to the driver and left uncovered by the spec's vocabulary check.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from demo_driver import (  # noqa: E402
    DEFAULT_OUT,
    THEMES,
    Runner,
    load_spec,
)

SPEC_PATH = ROOT / "tools" / "demo_specs.json"
DOCS = (ROOT / "docs" / "DEMO_SCRIPTS.md", ROOT / "docs" / "DEMO_SCRIPTS_ja.md")

# Placeholders _expand understands. A spec naming any other one silently
# produces a path with a brace in it.
PLACEHOLDERS = ("{repo}", "{cases}", "{work}")

# The ways a step can name what it acts on, i.e. every branch of resolve().
TARGET_KEYS = frozenset({
    "point", "menu", "menu_item", "file", "group", "tree", "cell", "tab",
    "widget", "button", "field",
})

# Steps that act on a target and so must name exactly one.
TARGETED = frozenset({"click", "move", "drag", "scroll"})

# Where a label a scene clicks is allowed to be defined. Menu items and buttons
# are literals in these files; shape rows (`ball`, `midPlane`) are data read out
# of a case, so only labels carrying an ellipsis — the convention for an action
# that opens a dialog — are held to this.
LABEL_SOURCES = (
    ROOT / "ui" / "main_window.py",
    ROOT / "ui" / "panels" / "block_mesh_panel.py",
)

STEP_KINDS = frozenset(
    name[len("_step_"):] for name in dir(Runner) if name.startswith("_step_")
)

# Buttons Qt supplies and translates itself, so there is no literal in ui/ to
# find: a QDialogButtonBox's Ok, a QMessageBox's Yes.
QT_STANDARD_BUTTONS = frozenset({
    "OK", "Cancel", "Yes", "No", "Close", "Apply", "Save", "Discard",
})

# A quoted string in the source. Crude on purpose — this only has to find the
# label literals, and every one of them is written on a single line.
_LITERAL = re.compile(r'"([^"\n]+)"')


def _matches_a_literal(label: str, literals: set[str]) -> bool:
    """True when a label names a literal in the UI source, whole or in part.

    The partial rule mirrors the driver's: _named_button and _popup_item_point
    both accept a unique substring, because some labels count what they are
    about — `Add Selected (1)` — and a spec naming the number would be
    asserting the state of a checkbox list from a step about a button.
    """
    return any(label == text or label in text for text in literals)


@pytest.fixture(scope="module")
def raw():
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def scenes():
    # Dummy roots: load_spec only expands them, and nothing on this machine has
    # to exist for the spec to be well formed.
    return load_spec(SPEC_PATH, Path("/nonexistent/cases"), Path("/nonexistent/work"))


@pytest.fixture(scope="module")
def ui_source():
    return "\n".join(path.read_text(encoding="utf-8") for path in LABEL_SOURCES)


@pytest.fixture(scope="module")
def ui_literals():
    """Every quoted string anywhere in ui/, for labels defined outside a menu."""
    literals: set[str] = set()
    for path in (ROOT / "ui").rglob("*.py"):
        literals.update(_LITERAL.findall(path.read_text(encoding="utf-8")))
    return literals


def steps_of(scenes):
    """Every (scene name, step) pair in the spec."""
    return [(scene.name, step) for scene in scenes for step in scene.steps]


class TestSpecShape:
    def test_the_spec_loads(self, scenes):
        # load_spec reads through the strict WindowState path, so this also
        # asserts every scene's start state is valid.
        assert scenes

    def test_every_scene_has_steps(self, scenes):
        for scene in scenes:
            assert scene.steps, f"{scene.name}: no steps"

    def test_every_scene_has_a_note(self, scenes):
        # The note is what --list prints; a scene without one is unexplained.
        for scene in scenes:
            assert scene.note, f"{scene.name}: no note"

    def test_every_theme_is_known(self, raw):
        for name, entry in raw["scenes"].items():
            assert entry.get("theme", "light") in THEMES, name

    def test_defaults_are_a_valid_state(self, raw):
        from ui.window_state import WindowState

        WindowState.from_dict(raw["defaults"])


class TestCases:
    def test_case_source_names_a_workdir(self, raw):
        # Enforced by load_spec; pinned here so the rule survives a refactor.
        for name, entry in raw["scenes"].items():
            if entry.get("case_source"):
                assert entry.get("workdir"), f"{name}: case_source without workdir"

    def test_path_placeholders_are_known(self, raw):
        paths = []
        for name, entry in raw["scenes"].items():
            paths.append((name, entry.get("case_source", "")))
            paths.append((name, entry.get("workdir", "")))
            paths.append((name, entry.get("state", {}).get("case_dir", "")))
            for item in entry.get("copy_also") or []:
                paths.extend([(name, item["source"]), (name, item["into"])])
        for name, path in paths:
            if "{" not in path:
                continue
            assert any(p in path for p in PLACEHOLDERS), f"{name}: unknown placeholder in {path}"

    def test_scratch_workdirs_are_outside_the_repository(self, raw):
        # A take writes a mesh, a 0/ and logs into its workdir. Pointing that at
        # the repository would litter tutorials/ and dirty the working tree.
        for name, entry in raw["scenes"].items():
            workdir = entry.get("workdir", "")
            assert "{repo}" not in workdir, f"{name}: workdir must not be under the repository"

    def test_clean_paths_are_outside_the_repository(self, scenes):
        # `clean` is an rmtree of whatever it names, before the window opens.
        # prepare_case refuses a path inside the repository at record time;
        # this is the same rule stated where a spec is written rather than run.
        for scene in scenes:
            for path in scene.clean:
                assert not path.startswith(str(ROOT)), f"{scene.name}: clean {path}"

    def test_case_library_is_outside_the_repository(self, scenes):
        # The library is what the case chooser opens on, and the take
        # duplicates out of it. Pointing it at tutorials/ would put the
        # recording machine's checkout path on screen and risk writing there.
        for scene in scenes:
            if scene.case_library:
                assert not scene.case_library.startswith(str(ROOT)), scene.name

    def test_bundled_cases_exist(self, scenes):
        # Only the repository's own cases: a {cases} scene depends on the
        # recording machine's run directory, which no test can assume.
        for scene in scenes:
            if not scene.case_source.startswith(str(ROOT)):
                continue
            assert Path(scene.case_source).is_dir(), f"{scene.name}: {scene.case_source}"

    def test_bundled_cases_hold_the_files_a_scene_opens(self, scenes):
        # The check that would have caught a tutorial file being renamed
        # without the scene that opens it being updated.
        for scene in scenes:
            if not scene.case_source.startswith(str(ROOT)):
                continue
            case = Path(scene.case_source)
            wanted = list(scene.state.preload_files)
            if scene.state.current_file:
                wanted.append(scene.state.current_file)
            for relative in wanted:
                assert (case / relative).is_file(), f"{scene.name}: no {relative} in {case.name}"


class TestSteps:
    def test_every_step_kind_is_known(self, scenes):
        for name, step in steps_of(scenes):
            assert step.get("do") in STEP_KINDS, f"{name}: unknown step {step.get('do')!r}"

    def test_targeted_steps_name_exactly_one_target(self, scenes):
        for name, step in steps_of(scenes):
            if step["do"] not in TARGETED:
                continue
            named = TARGET_KEYS & set(step)
            assert len(named) == 1, f"{name}: {step['do']} names {sorted(named) or 'no target'}"

    def test_untargeted_steps_name_no_target(self, scenes):
        # A `wait` that carries a target is a step someone meant to make a
        # click, and it would sit there doing nothing.
        for name, step in steps_of(scenes):
            if step["do"] in TARGETED:
                continue
            assert not (TARGET_KEYS & set(step)), f"{name}: {step['do']} names a target"

    def test_type_and_key_steps_carry_their_payload(self, scenes):
        for name, step in steps_of(scenes):
            if step["do"] == "type":
                assert step.get("text"), f"{name}: type without text"
            if step["do"] == "key":
                assert step.get("keys"), f"{name}: key without keys"

    def test_drag_steps_carry_a_delta(self, scenes):
        for name, step in steps_of(scenes):
            if step["do"] != "drag":
                continue
            by = step.get("by")
            assert isinstance(by, list) and len(by) == 2, f"{name}: drag without a two-item `by`"

    def test_mouse_button_is_spelled_with(self, scenes):
        # `button` is a target — the label of a push button to click — so a step
        # meaning the *mouse* button says `with`. Writing `"button": "left"`
        # parses as a target named "left" and fails only at record time.
        for name, step in steps_of(scenes):
            assert step.get("button") not in ("left", "middle", "right"), (
                f"{name}: `button` is a target; use `with` for the mouse button"
            )
            if "with" in step:
                assert step["with"] in ("left", "middle", "right"), f"{name}: {step['with']!r}"

    def test_dwell_and_duration_values_are_positive(self, scenes):
        for name, step in steps_of(scenes):
            for field in ("then", "ms", "ticks", "amount", "delay"):
                if field in step:
                    assert int(step[field]) > 0, f"{name}: {field} is {step[field]}"

    def test_step_text_placeholders_are_known(self, raw):
        # A typed path goes through the same expansion as a spec path.
        for name, entry in raw["scenes"].items():
            for step in entry.get("steps") or []:
                text = step.get("text", "")
                if "{" not in text:
                    continue
                assert any(p in text for p in PLACEHOLDERS), f"{name}: {text}"


class TestLabels:
    def test_menu_bar_titles_exist_in_the_ui(self, scenes, ui_source):
        for name, step in steps_of(scenes):
            title = step.get("menu")
            if title:
                assert f'"{title}"' in ui_source, f"{name}: no menu titled {title!r}"

    def test_dialog_opening_menu_items_exist_in_the_ui(self, scenes, ui_source):
        # Only labels with an ellipsis: those are actions defined as literals.
        # A row like `ball` is a shape name read out of a case at run time.
        for name, step in steps_of(scenes):
            label = step.get("menu_item", "")
            if "…" not in label and "..." not in label:
                continue
            assert label in ui_source, f"{name}: no menu item {label!r} in the UI source"

    def test_button_labels_exist_in_the_ui(self, scenes, ui_literals):
        for name, step in steps_of(scenes):
            label = step.get("button")
            if not label or label in QT_STANDARD_BUTTONS:
                continue
            assert _matches_a_literal(label, ui_literals), (
                f"{name}: no button labelled {label!r}"
            )

    def test_field_labels_exist_in_the_ui(self, scenes, ui_literals):
        # A form row's label, which is also what the person watching reads.
        for name, step in steps_of(scenes):
            label = step.get("field")
            if not label:
                continue
            assert _matches_a_literal(label, ui_literals), (
                f"{name}: no form field labelled {label!r}"
            )

    def test_widget_paths_look_like_real_attributes(self, scenes):
        source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ROOT / "ui").rglob("*.py")
        )
        for name, step in steps_of(scenes):
            dotted = step.get("widget")
            if not dotted:
                continue
            # Only that the name exists somewhere in ui/. Resolving the path
            # for real needs a MainWindow, and standing one up would drag a
            # QApplication into a suite that otherwise needs no display.
            for part in dotted.split("."):
                assert part in source, f"{name}: no widget attribute {part!r} anywhere in ui/"


class TestDocumentation:
    def test_every_scene_is_documented(self, scenes):
        for path in DOCS:
            text = path.read_text(encoding="utf-8")
            for scene in scenes:
                assert scene.name in text, f"{scene.name} missing from {path.name}"

    def test_both_documents_list_the_same_scenes(self, scenes):
        # The pair drifts silently otherwise; every other doc is mirrored too.
        english, japanese = (path.read_text(encoding="utf-8") for path in DOCS)
        for scene in scenes:
            assert (scene.name in english) == (scene.name in japanese), scene.name

    def test_published_captions_belong_to_a_scene(self, scenes):
        # The .srt files are tracked and the videos are not, so a renamed scene
        # leaves an orphan caption file behind with nothing to pair it to.
        known = {scene.name for scene in scenes}
        for caption in sorted(DEFAULT_OUT.glob("*.srt")):
            assert caption.stem in known, f"{caption.name} matches no scene"
