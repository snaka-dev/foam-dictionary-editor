# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""OpenFOAM dictionary syntax highlighter for use with QPlainTextEdit."""
from __future__ import annotations

import json
import re
from pathlib import Path

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat

_APP_CONFIG_DIR = Path(__file__).parent.parent.parent / "app_config"
_KW_FILE = _APP_CONFIG_DIR / "foam_keywords.json"                  # user-generated (gitignored)
_KW_DEFAULT_FILE = _APP_CONFIG_DIR / "foam_keywords.default.json"  # shipped baseline
_VALID_KW_RE = re.compile(r"^[A-Za-z]\w+$")

# Numbers and keywords alike are guarded on both sides so tokens glued to
# identifiers (patch names like "wall0", "inlet-1", "0wall") or dotted names
# (set names like "y0.1") are not partially highlighted, while standalone
# matches ("0.05", "-1e-05", "(0 1 0)", "off") still work.
_NUMBER_RE = r"(?<![\w.])(?<![\w.][-+])[-+]?\d+(\.\d*)?([eE][-+]?\d+)?(?![\w.])"


def _fmt(color: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
    f = QTextCharFormat()
    f.setForeground(QColor(color))
    if bold:
        f.setFontWeight(QFont.Weight.Bold)
    if italic:
        f.setFontItalic(True)
    return f


_IN_COMMENT = 1  # block user-state: inside /* */ comment

# Structural / boolean keywords — blue bold
_KEYWORD_RE = (
    r"(?<![\w.])(FoamFile"
    r"|true|false|on|off|yes|no"
    r"|uniform|nonuniform"
    r"|ascii|binary"
    r"|latestTime|firstTime|startTime|adjustableRunTime|timeStep|runTime|clockTime|cpuTime"
    r")(?![\w.])"
)

# Shell mode: OpenFOAM RunFunctions/CleanFunctions helpers + core sh keywords — blue bold
_SHELL_KEYWORD_RE = (
    r"(?<![\w.])(runApplication|runParallel|restore0Dir|cleanCase0?|foamCleanTutorials"
    r"|getApplication|getNumberOfProcessors|canCompile|isTest|foamDictionary"
    r"|if|then|else|elif|fi|for|in|do|done|case|esac|while|until"
    r"|exit|cd|source|set|echo|rm|cp|mv|mkdir|touch|export"
    r")(?![\w.])"
)

def _load_foam_keywords() -> frozenset[str]:
    """Load the keyword list: the user-generated foam_keywords.json when present,
    otherwise the shipped foam_keywords.default.json.

    Returns an empty set silently when both files are absent or malformed.
    Run tools/generate_foam_keywords.py (or Settings > Generate OpenFOAM
    Keywords…) to (re)generate the user file from an OpenFOAM installation.
    """
    for path in (_KW_FILE, _KW_DEFAULT_FILE):
        try:
            data = json.loads(path.read_text())
            return frozenset(
                w for w in data.get("keywords", [])
                if isinstance(w, str) and _VALID_KW_RE.match(w)
            )
        except Exception:
            continue
    return frozenset()


def _collect_schema_keywords() -> frozenset[str]:
    """Extract keywords from the schema registry: key names and choice-item values.

    Key names: dotted keys like "snapControls.nRelaxIter" are split on "." so each
    segment is added independently.  Choice values are split on whitespace.
    Tokens shorter than 3 characters or purely numeric are skipped.
    Returns an empty set silently if the schema registry is unavailable.
    """
    try:
        import schemas  # noqa: PLC0415 — local import; schemas may not be ready at parse time
        words: set[str] = set()
        for file_schemas in schemas._registry._file_key_schemas.values():
            for key, ks in file_schemas.items():
                for part in key.split("."):
                    if len(part) >= 3:
                        words.add(part)
                for ci in ks.choices:
                    for tok in ci.value.split():
                        if len(tok) >= 3 and not tok.replace(".", "").replace("-", "").isdigit():
                            words.add(tok)
        return frozenset(words)
    except Exception:
        return frozenset()


_VALUE_KW_FMT = None  # set lazily to avoid Qt init at import time
_KW_CHUNK = 1000      # PCRE2 "too large" error above ~2300 tokens; 1000/chunk is safe


def _build_value_kw_rules() -> list[tuple["QRegularExpression", "QTextCharFormat"]]:
    """Build value-keyword rules split into PCRE2-safe chunks."""
    global _VALUE_KW_FMT
    if _VALUE_KW_FMT is None:
        _VALUE_KW_FMT = _fmt("#007070")
    all_kw = sorted(_load_foam_keywords() | _collect_schema_keywords())
    rules = []
    for i in range(0, max(len(all_kw), 1), _KW_CHUNK):
        pat = r"(?<![\w.])(" + "|".join(all_kw[i : i + _KW_CHUNK]) + r")(?![\w.])"
        rules.append((QRegularExpression(pat), _VALUE_KW_FMT))
    return rules


class FoamHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for OpenFOAM dictionary files.

    Inline rules (lower priority, applied first):
      numbers, keywords, #directives, $macros, string literals, // comments.
    Block comment /* */ (highest priority, overrides inline rules).
    """

    def __init__(self, document):
        super().__init__(document)
        self._enabled = True
        self._mode = "foam"
        self._comment_fmt = _fmt("#808080", italic=True)
        self._rules = self._build_rules()
        self._bc_start = QRegularExpression(r"/\*")
        self._bc_end   = QRegularExpression(r"\*/")

    def _build_rules(self) -> list[tuple[QRegularExpression, QTextCharFormat]]:
        """Build the inline rule list for the current mode (later rules win)."""
        kw_rules = _build_value_kw_rules()
        if self._mode == "shell":
            return kw_rules + [
                (QRegularExpression(_SHELL_KEYWORD_RE), _fmt("#0000CC", bold=True)),
                (QRegularExpression(r"\$\{?\w+\}?"),    _fmt("#CC6600")),
                (QRegularExpression(r'"[^"]*"'),         _fmt("#006400")),
                (QRegularExpression(r"'[^']*'"),         _fmt("#006400")),
                (QRegularExpression(r"#.*"),             self._comment_fmt),
            ]
        return (
            [(QRegularExpression(_NUMBER_RE), _fmt("#008080"))]
            + kw_rules
            + [
                (QRegularExpression(_KEYWORD_RE),         _fmt("#0000CC", bold=True)),
                (QRegularExpression(r"#[A-Za-z]\w*"),     _fmt("#800080", bold=True)),
                (QRegularExpression(r"\$\{?\w+\}?"),      _fmt("#CC6600")),
                (QRegularExpression(r'"[^"]*"'),           _fmt("#006400")),
                (QRegularExpression(r"//.*"),              self._comment_fmt),
            ]
        )

    def reload_keywords(self) -> None:
        """Rebuild value-keyword rules from the current JSON + schema state and rehighlight."""
        self._rules = self._build_rules()
        self.rehighlight()

    def set_mode(self, mode: str) -> None:
        """Switch between "foam" (dictionary) and "shell" (Allrun script) rules."""
        if mode not in ("foam", "shell"):
            raise ValueError(f"unknown highlighter mode: {mode!r}")
        if mode == self._mode:
            return
        self._mode = mode
        self._rules = self._build_rules()
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:
        if not self._enabled:
            return

        # Inline rules (lower priority)
        for pattern, fmt in self._rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)

        if self._mode == "shell":
            # No /* */ block comments in shell scripts.
            self.setCurrentBlockState(0)
            return

        # Multi-line block comment (highest priority — grey overrides inline rules)
        self.setCurrentBlockState(0)
        start = 0
        if self.previousBlockState() != _IN_COMMENT:
            m = self._bc_start.match(text)
            if not m.hasMatch():
                return
            start = m.capturedStart()

        while start >= 0:
            m_end = self._bc_end.match(text, start)
            if m_end.hasMatch():
                end_pos = m_end.capturedEnd()
                self.setFormat(start, end_pos - start, self._comment_fmt)
                m_next = self._bc_start.match(text, end_pos)
                start = m_next.capturedStart() if m_next.hasMatch() else -1
            else:
                self.setCurrentBlockState(_IN_COMMENT)
                self.setFormat(start, len(text) - start, self._comment_fmt)
                return

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self.rehighlight()
