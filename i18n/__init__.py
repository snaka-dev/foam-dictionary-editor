# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import importlib
from pathlib import Path

_language = "en"


def set_language(lang: str) -> None:
    global _language
    _language = lang


def get_language() -> str:
    return _language


def available_languages() -> list[tuple[str, str]]:
    """Return [(code, display_name)] for all available languages, English first."""
    result = [("en", "English")]
    i18n_dir = Path(__file__).parent
    for f in sorted(i18n_dir.glob("*.py")):
        if f.stem.startswith("_"):
            continue
        try:
            mod = importlib.import_module(f"i18n.{f.stem}")
            name = getattr(mod, "LANGUAGE_NAME", f.stem)
            result.append((f.stem, name))
        except ImportError:
            pass
    return result


def tr(text: str) -> str:
    """Return the translation of text in the current language, or text itself."""
    if _language == "en":
        return text
    try:
        mod = importlib.import_module(f"i18n.{_language}")
        return mod.TRANSLATIONS.get(text, text)
    except ImportError:
        return text
