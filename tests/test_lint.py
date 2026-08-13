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
