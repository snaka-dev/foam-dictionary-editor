# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Shared dialog stubs for the UI tests.

Six near-identical helpers for "answer this dialog without showing it" had grown across
three test modules, each re-deriving the same monkeypatch. They are fixtures rather than
importable functions for the reason `destroy_widget` is: `tests/` has no `__init__.py`,
so requesting by name is how a test module reaches this file -- and each one closes over
`monkeypatch`, so a call site says what it wants answered and nothing about how.

They pair with `no_unstubbed_modals` in the parent conftest, which makes *forgetting* to
stub a dialog fail immediately instead of hanging the run. That guard says what went
wrong; these are how it is put right.
"""
from __future__ import annotations

import importlib

import pytest


@pytest.fixture
def stub_dialog(monkeypatch):
    """Replace a dialog class with one that never shows, carrying the attributes given.

        stub_dialog("ui.mixins._file_mgmt_ops.CleanBackupsDialog", paths_to_delete=[p])
        stub_dialog("ui.mixins._case_ops.SaveAsNewCaseDialog", accepted=False)

    The target is the name *as the handler sees it* -- the module under test imported the
    class, so patching it there is what takes effect. `accepted` drives `exec()`'s return;
    every other keyword becomes an attribute the handler can read back.
    """
    from PySide6.QtWidgets import QDialog

    def stub(target: str, accepted: bool = True, **attrs):
        module_path, _, class_name = target.rpartition(".")
        module = importlib.import_module(module_path)

        class _Stub:
            def __init__(self, *a, **k):
                for key, value in attrs.items():
                    setattr(self, key, value)

            def exec(self):
                return QDialog.DialogCode.Accepted if accepted else QDialog.DialogCode.Rejected

        monkeypatch.setattr(module, class_name, _Stub)
        return _Stub

    return stub


@pytest.fixture
def answer_message_box(monkeypatch):
    """Answer QMessageBox's static prompts with one button.

        answer_message_box(QMessageBox.StandardButton.Yes)

    Patches `question`, `warning`, `information` and `critical` together: a handler often
    reaches more than one, and a test that stubs only the one it was thinking of hangs on
    the other -- which is the mistake `no_unstubbed_modals` exists to catch.
    Returns the list the prompts' *messages* are appended to, for asserting on what the
    user was actually asked.
    """
    from PySide6.QtWidgets import QMessageBox

    asked: list[str] = []

    def answer(button):
        def prompt(*args, **kwargs):
            # (parent, title, text, ...) for every one of these
            if len(args) > 2 and isinstance(args[2], str):
                asked.append(args[2])
            return button

        for name in ("question", "warning", "information", "critical"):
            monkeypatch.setattr(QMessageBox, name, staticmethod(prompt))
        return asked

    return answer


@pytest.fixture
def choose_directory(monkeypatch):
    """Answer QFileDialog.getExistingDirectory. Pass None or "" for a cancelled chooser."""
    from PySide6.QtWidgets import QFileDialog

    def choose(path):
        monkeypatch.setattr(
            QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: str(path or ""))
        )

    return choose


@pytest.fixture
def answer_input(monkeypatch):
    """Answer QInputDialog.getText / getItem. `ok=False` is the user cancelling."""
    from PySide6.QtWidgets import QInputDialog

    def answer(value, ok: bool = True):
        monkeypatch.setattr(
            QInputDialog, "getText", staticmethod(lambda *a, **k: (value, ok))
        )
        monkeypatch.setattr(
            QInputDialog, "getItem", staticmethod(lambda *a, **k: (value, ok))
        )

    return answer
