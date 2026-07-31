# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Structural checks on tools/capture_dialog.py's shot list.

The counterpart to TestScreenshotSpec in tests/ui/test_window_state.py: the
capture itself needs a real X display and is out of scope here, but the shot
list is plain data and a broken entry should not wait until someone runs the
tool to be noticed.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from capture_dialog import (  # noqa: E402
    _SETFIELDS_PREFIX,
    _SETFIELDS_WARNING,
    DEFAULT_CASE,
    DEFAULT_OUT,
    DIALOG_SHOTS,
    ShotContext,
)

# Shots whose inputs come from the capture machine (a run case, an OpenFOAM
# installation) versus ones whose inputs are bundled in the repository.
_CONTEXT_BACKED = ("find-examples", "log-summary")
_REPO_BACKED = ("run-tool",)


class TestDialogShots:
    def test_there_is_at_least_one_shot(self):
        assert DIALOG_SHOTS

    def test_keys_match_their_shot_names(self):
        for key, shot in DIALOG_SHOTS.items():
            assert key == shot.name

    def test_no_two_shots_write_the_same_file(self):
        written = [shot.output for shot in DIALOG_SHOTS.values()]
        assert len(written) == len(set(written))

    def test_every_shot_writes_a_png(self):
        for shot in DIALOG_SHOTS.values():
            assert shot.output.endswith(".png"), shot.name

    def test_every_shot_has_a_usable_size(self):
        # None is allowed and means "keep the dialog's own default".
        for shot in DIALOG_SHOTS.values():
            if shot.size is None:
                continue
            width, height = shot.size
            assert width > 0 and height > 0, shot.name

    def test_every_shot_is_referenced_by_the_gallery(self):
        # A shot writing a file no gallery page shows is either a stale entry or
        # a caption someone forgot; both are worth hearing about.
        for name in ("SCREENSHOTS.md", "SCREENSHOTS_ja.md"):
            page = (ROOT / "docs" / name).read_text(encoding="utf-8")
            for shot in DIALOG_SHOTS.values():
                assert shot.output in page, f"{shot.name} missing from {name}"

    def test_the_shipped_images_exist(self):
        for shot in DIALOG_SHOTS.values():
            assert (DEFAULT_OUT / shot.output).is_file(), shot.name

    def test_the_default_case_is_not_under_a_home_directory(self):
        # The log summary reproduces the log's own "Case:" line, so a case run
        # from $HOME would print the capturing user's name into the gallery.
        # See DEVELOPER.md's "Screenshot capture".
        assert not str(DEFAULT_CASE).startswith(str(Path.home()))

    def test_every_shot_is_classified_by_where_its_inputs_come_from(self):
        # Adding a shot should force a choice between the two tests below rather
        # than quietly landing in neither.
        assert set(_CONTEXT_BACKED) | set(_REPO_BACKED) == set(DIALOG_SHOTS)
        assert not set(_CONTEXT_BACKED) & set(_REPO_BACKED)

    @pytest.mark.parametrize("name", _CONTEXT_BACKED)
    def test_requires_reports_missing_inputs_rather_than_crashing(self, name, tmp_path):
        # What these shots read is produced by hand (see DEVELOPER.md), so "you
        # have not made it yet" has to be a message, not a traceback. tmp_path is
        # a real directory that is neither a run case nor an OpenFOAM install, so
        # the shot's own precondition check is the thing that fires.
        ctx = ShotContext(case_dir=tmp_path, installation=tmp_path / "nope")
        with pytest.raises(SystemExit) as excinfo:
            DIALOG_SHOTS[name].requires(ctx)
        assert str(excinfo.value).startswith("missing "), name

    @pytest.mark.parametrize("name", _REPO_BACKED)
    def test_repo_backed_shots_need_nothing_from_the_machine(self, name):
        # run-tool reads a case bundled in the repository, because the prefix it
        # exists to show only appears for a case with a 0.orig/. So its inputs
        # travel with a checkout, and a context pointing nowhere is still fine.
        nowhere = Path("/nonexistent")
        DIALOG_SHOTS[name].requires(
            ShotContext(case_dir=nowhere, installation=nowhere)
        )
        assert (ROOT / "tutorials" / "damBreak" / "0.orig").is_dir()

    def test_the_run_tool_shot_shows_what_the_app_would_actually_show(self):
        # The shot hands RunToolDialog the warning and prefix that
        # _on_run_setfields_clicked hands it, copied rather than imported (they
        # are inline literals in a mixin). If that file's wording changes, the
        # gallery would be showing a dialog the app never produces.
        import ast

        source = (ROOT / "ui" / "mixins" / "_tools_ops.py").read_text("utf-8")
        literals = {
            node.value
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        label, prefix_cmd, _checked = _SETFIELDS_PREFIX
        for text in (_SETFIELDS_WARNING, label, prefix_cmd):
            assert text in literals, f"_tools_ops.py no longer contains {text!r}"

    def test_the_find_examples_shot_reaches_only_for_attributes_that_exist(self):
        # The shot drives FindExamplesDialog through its private widgets, which
        # is the trade for not adding capture-only accessors to a production
        # dialog. Pin the names here so a rename fails in the suite rather than
        # halfway through a capture run that needs an X display.
        import ast

        source = (ROOT / "ui" / "dialogs" / "find_examples_dialog.py").read_text("utf-8")
        assigned = {
            node.attr
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store)
        }
        for attr in ("_install_combo", "_query_edit", "_results"):
            assert attr in assigned, f"FindExamplesDialog no longer sets {attr}"
        assert "_on_search" in {
            node.name for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.FunctionDef)
        }
