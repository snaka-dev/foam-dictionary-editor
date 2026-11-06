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


# ── every tr() call has a Japanese entry ────────────────────────────────────
#
# The reverse of the duplicate-key check above: every English string passed
# to tr() should have a matching i18n/ja.py entry, so the language actually
# changes instead of silently falling back to English. _UNTRANSLATED is now
# **empty**: it was a seeded exception list measured off the tree, it only ever
# shrank, and the last 36 entries were translated together. Keep it that way —
# a new tr() call ships with its translation, and adding a name here to get a
# commit through puts an English string in front of a Japanese user with
# nothing to say so. The empty frozenset is kept rather than deleted because it
# is the statement. It intentionally does not check the opposite direction (every
# ja.py key has a call site): ~40 keys legitimately reach tr() only through
# a data table (e.g. keyboard_shortcuts_dialog.py's _SECTIONS_DATA), so that
# direction is noise, not signal.
_UNTRANSLATED: frozenset[str] = frozenset({
})


def _tr_call_literal_keys(root: Path) -> set[str]:
    """Every string literal passed as tr()'s sole argument under ui/.

    Only ui/ (and ui/session_restore.py, which lives under it) import tr();
    a non-literal argument (an f-string, a variable) cannot be checked this
    way and is not this test's concern -- it is either already a translated
    key looked up dynamically, or outside what a static scan can verify.
    """
    keys: set[str] = set()
    for path in sorted((root / "ui").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "tr"
                and len(node.args) == 1
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                keys.add(node.args[0].value)
    return keys


def test_every_tr_call_has_a_ja_translation():
    """A new tr("...") call must ship with its i18n/ja.py entry.

    Fix: add the English string as a key in i18n/ja.py with its Japanese
    translation. If it is a genuine pre-existing gap you are not touching,
    it is already covered by _UNTRANSLATED above -- do not add new entries
    to that list for code you are writing now.
    """
    ja_keys = set(_translation_keys(PROJECT_ROOT / "i18n" / "ja.py"))
    call_keys = _tr_call_literal_keys(PROJECT_ROOT)
    missing = call_keys - ja_keys - _UNTRANSLATED
    assert not missing, (
        "tr() call(s) with no i18n/ja.py entry (add the translation, or if "
        "this is a deliberate pre-existing gap, add it to _UNTRANSLATED "
        f"in this file): {sorted(missing)}"
    )


def test_untranslated_allowlist_has_no_stale_entries():
    """Anti-rot: an _UNTRANSLATED entry that ja.py now translates, or that no
    longer appears as a tr() call, is stale -- keep the list matching reality
    in both directions, the same rule tests/ui/test_translatable_strings.py
    applies to its own allowlists.
    """
    ja_keys = set(_translation_keys(PROJECT_ROOT / "i18n" / "ja.py"))
    call_keys = _tr_call_literal_keys(PROJECT_ROOT)
    now_translated = sorted(_UNTRANSLATED & ja_keys)
    assert not now_translated, (
        f"_UNTRANSLATED lists key(s) i18n/ja.py now translates -- remove them: {now_translated}"
    )
    phantom = sorted(_UNTRANSLATED - call_keys)
    assert not phantom, (
        f"_UNTRANSLATED lists key(s) no longer reached by any tr() call -- remove them: {phantom}"
    )
