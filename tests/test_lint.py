# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Guard tests running ruff and mypy so lint/type regressions surface in `pytest -q`.

There is no CI workflow in this repo yet, so these are the only automated check
that ruff/mypy stay clean. Scope matches the commands documented in DEVELOPER.md
and CLAUDE.md: both ruff and mypy cover the whole repository (mypy via its
pyproject.toml `files` setting, which lists every top-level package).
"""
from __future__ import annotations

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
