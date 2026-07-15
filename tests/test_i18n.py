# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Consistency checks for the i18n translation tables."""

import ast
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _translation_keys(module_path: Path) -> list[str]:
    """Return every key literal in the module's TRANSLATIONS dict, duplicates included."""
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        target = getattr(node, "target", None) or (
            node.targets[0] if isinstance(node, ast.Assign) else None
        )
        if (
            isinstance(node, (ast.Assign, ast.AnnAssign))
            and isinstance(target, ast.Name)
            and target.id == "TRANSLATIONS"
            and isinstance(node.value, ast.Dict)
        ):
            return [ast.literal_eval(key) for key in node.value.keys]
    raise AssertionError(f"No TRANSLATIONS dict literal found in {module_path}")


def test_ja_translations_has_no_duplicate_keys():
    """Duplicate keys in a dict literal are silently dropped; keep ja.py free of them."""
    keys = _translation_keys(PROJECT_ROOT / "i18n" / "ja.py")
    duplicates = [key for key, count in Counter(keys).items() if count > 1]
    assert duplicates == [], f"Duplicate TRANSLATIONS keys in i18n/ja.py: {duplicates}"
