# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Guard tests running ruff and mypy so lint/type regressions surface in `pytest -q`.

There is no CI workflow in this repo yet, so these are the only automated check
that ruff/mypy stay clean. Scope matches the commands documented in DEVELOPER.md
and CLAUDE.md: ruff covers the whole repository, while mypy covers foam/,
model/, app_config/, schemas/, services/, ui/, main.py, and i18n/ (its
pyproject.toml `files` setting) — deliberately excluding tools/.
"""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("ruff")
pytest.importorskip("mypy")

ROOT = Path(__file__).resolve().parent.parent


def test_ruff_clean():
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_mypy_clean():
    result = subprocess.run(
        [sys.executable, "-m", "mypy"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _is_fixture_decorator(dec: ast.expr) -> bool:
    """True for `@pytest.fixture`, `@fixture`, or either called with args."""
    if isinstance(dec, ast.Call):
        dec = dec.func
    if isinstance(dec, ast.Attribute):
        return dec.attr == "fixture"
    if isinstance(dec, ast.Name):
        return dec.id == "fixture"
    return False


def test_no_local_qapp_fixture():
    """A local `qapp` fixture anywhere under tests/ shadows pytest-qt's own.

    pytest-qt (pinned in requirements-dev.txt) already provides a
    session-scoped `qapp` fixture that creates a single QApplication for the
    whole test run. A test file defining its own `qapp` fixture shadows that
    session-scoped instance with a file-local one -- which is exactly the bug
    Phase 1 fixed by deleting 22 duplicate definitions from tests/ui/. This
    guard keeps them from coming back.
    """
    offenders = []
    for path in sorted((ROOT / "tests").rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name != "qapp":
                continue
            if any(_is_fixture_decorator(dec) for dec in node.decorator_list):
                offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}")

    assert not offenders, (
        "Found a local `qapp` fixture, which shadows pytest-qt's own "
        "session-scoped `qapp` fixture (requirements-dev.txt pins "
        "pytest-qt>=4.4). Delete the local definition and use the fixture "
        "pytest-qt already provides:\n" + "\n".join(offenders)
    )


_WIDGET_CTOR_SUFFIXES = ("Panel", "Dialog", "Window", "Widget", "Navigator", "Menu")


def _local_non_qt_classes(tree: ast.Module) -> set[str]:
    """Classes defined in this test module that are not Qt types.

    Test doubles are named after what they stand in for -- `_RecordingPanel` for
    BlockMeshPanel -- so a name-suffix check alone flags them. A double with no Qt base
    owns no C++ object and needs no destroying.
    """
    local = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        bases = {ast.unparse(b) for b in node.bases}
        if not any(b.split(".")[-1].startswith("Q") for b in bases):
            local.add(node.name)
    return local


def _constructs_a_widget(node: ast.AST, local_doubles: set[str]) -> bool:
    """True if *node*'s body builds a `*Panel(`/`*Dialog(`/... anywhere.

    Assignment is only the commonest spelling. `yield BlockMeshPanel()` and
    `return EditorPanel()` construct one just as surely and leaked just as much -- an
    Assign-only check missed nine files' worth of them.
    """
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Call):
            continue
        func = sub.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
        if name.endswith(_WIDGET_CTOR_SUFFIXES) and name not in local_doubles:
            return True
    return False


def test_widget_fixtures_destroy_what_they_build():
    """A fixture that builds a Qt widget must also destroy it.

    Qt widgets are not reclaimed by Python. `deleteLater()` does nothing without an event
    loop, and `gc.collect()` does nothing at all, so a fixture that merely drops its
    reference leaks every widget it built for the rest of the session -- and
    `apply_theme`/`setPalette`/`setStyleSheet` are broadcasts that walk every live widget.
    Left unchecked that cost this suite 28 minutes against a little under two. See
    tests/conftest.py's `_destroy_widget` and DEVELOPER.md's "Destroying widgets in tests".

    The fixture-scoped `destroy_widget` (or `qt_widget`, for widgets a test body builds) is
    how that is paid for. This guard keeps the next widget fixture from forgetting.
    """
    offenders = []
    for path in sorted((ROOT / "tests").rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        doubles = _local_non_qt_classes(tree)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not any(_is_fixture_decorator(dec) for dec in node.decorator_list):
                continue
            if not _constructs_a_widget(node, doubles):
                continue
            source = ast.unparse(node)
            if "destroy_widget" in source or "_destroy_widget" in source:
                continue
            offenders.append(f"{path.relative_to(ROOT)}:{node.lineno} ({node.name})")

    assert not offenders, (
        "These fixtures build a Qt widget but never destroy it, so every widget they make "
        "stays alive for the rest of the session. Take the `destroy_widget` fixture and "
        "call it in the teardown, after any shutdown()/cleanup() the widget needs:\n"
        + "\n".join(offenders)
    )
