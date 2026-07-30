# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for ui/widgets/_foam_highlighter.py."""
from __future__ import annotations

import pytest
from PySide6.QtGui import QTextCharFormat, QTextDocument

from ui.widgets._foam_highlighter import (
    _IN_COMMENT,
    FoamHighlighter,
    _build_value_kw_rules,
    _collect_schema_keywords,
)

# ---------------------------------------------------------------------------
# Test helper: recording subclass
# ---------------------------------------------------------------------------

class _Rec(FoamHighlighter):
    """Records (start, length, color_hex) for every setFormat call."""

    def __init__(self, doc: QTextDocument) -> None:
        self._log: list[tuple[int, int, str]] = []
        self._doc = doc  # keep doc alive; QSyntaxHighlighter is a child of doc
        super().__init__(doc)

    def setFormat(self, start: int, count: int, fmt: QTextCharFormat) -> None:  # type: ignore[override]
        super().setFormat(start, count, fmt)
        if hasattr(fmt, "foreground"):
            self._log.append((start, count, fmt.foreground().color().name()))

    def highlight(self, text: str) -> list[tuple[int, int, str]]:
        """Set document text and return recorded format calls."""
        self.document().setPlainText(text)
        # setPlainText highlights the old (now-cleared) block before inserting;
        # clear _log here so rehighlight() below captures only the actual text.
        self._log = []
        self.rehighlight()
        return list(self._log)


@pytest.fixture
def rec(qapp):
    doc = QTextDocument()
    return _Rec(doc)


def _color_at(log: list[tuple[int, int, str]], pos: int) -> str | None:
    """Return the last-applied color hex at character position pos, or None."""
    result = None
    for start, length, color in log:
        if start <= pos < start + length:
            result = color
    return result


# ---------------------------------------------------------------------------
# // line comment
# ---------------------------------------------------------------------------

def test_line_comment_grey(rec):
    log = rec.highlight("// whole line")
    assert _color_at(log, 0) == "#808080"
    assert _color_at(log, 5) == "#808080"


def test_line_comment_after_key(rec):
    log = rec.highlight("key 1; // comment")
    assert _color_at(log, 7) == "#808080"   # inside comment
    assert _color_at(log, 4) != "#808080"   # '1' is not grey


# ---------------------------------------------------------------------------
# /* */ block comment — single line
# ---------------------------------------------------------------------------

def test_block_comment_single_line(rec):
    log = rec.highlight("/* comment */")
    assert _color_at(log, 0) == "#808080"
    assert _color_at(log, 12) == "#808080"


def test_block_comment_partial_line(rec):
    log = rec.highlight("x 1; /* comment */ y 2;")
    assert _color_at(log, 5) == "#808080"   # inside /* */
    assert _color_at(log, 20) != "#808080"  # after */


# ---------------------------------------------------------------------------
# /* */ block comment — multi-line state
# ---------------------------------------------------------------------------

def test_block_comment_state_set(rec):
    """A line with /* but no */ should leave block state = _IN_COMMENT."""
    rec.highlight("/* open\nclosed */")
    block0 = rec.document().findBlockByNumber(0)
    assert block0.userState() == _IN_COMMENT


def test_block_comment_state_cleared(rec):
    """A line inside a comment that closes it should leave state = 0."""
    rec.highlight("/* open\nclosed */")
    block1 = rec.document().findBlockByNumber(1)
    assert block1.userState() == 0


def test_block_comment_second_line_grey(rec):
    """All text on the continuation line should be grey up to */."""
    log = rec.highlight("/* open\nclosed */")
    grey_calls = [(s, length, c) for s, length, c in log if c == "#808080"]
    assert any(s == 0 for s, length, c in grey_calls), "start of line 1 should be grey"


# ---------------------------------------------------------------------------
# string literal
# ---------------------------------------------------------------------------

def test_string_green(rec):
    log = rec.highlight('key "value";')
    assert _color_at(log, 4) == "#006400"   # inside string
    assert _color_at(log, 11) != "#006400"  # semicolon after string


def test_string_does_not_bleed(rec):
    log = rec.highlight('"hello" world')
    assert _color_at(log, 8) != "#006400"   # 'w' in world — not string


# ---------------------------------------------------------------------------
# #directive
# ---------------------------------------------------------------------------

def test_directive_purple(rec):
    log = rec.highlight("#include <file>")
    assert _color_at(log, 0) == "#800080"
    assert _color_at(log, 7) == "#800080"


def test_eval_directive_purple(rec):
    log = rec.highlight("rHalf  #eval{ $r / 2 };")
    assert _color_at(log, 7) == "#800080"


# ---------------------------------------------------------------------------
# $macro
# ---------------------------------------------------------------------------

def test_macro_orange(rec):
    log = rec.highlight("nu $nu;")
    assert _color_at(log, 3) == "#cc6600"


def test_macro_braced_orange(rec):
    log = rec.highlight("x ${xMax};")
    assert _color_at(log, 2) == "#cc6600"


# ---------------------------------------------------------------------------
# keywords
# ---------------------------------------------------------------------------

def test_keyword_blue_bold(rec):
    log = rec.highlight("FoamFile { version 2.0; }")
    assert _color_at(log, 0) == "#0000cc"


def test_true_false_keywords(rec):
    for kw in ("true", "false", "on", "off", "yes", "no"):
        log = rec.highlight(f"flag {kw};")
        assert _color_at(log, 5) == "#0000cc", f"{kw!r} should be blue"


def test_uniform_keyword(rec):
    log = rec.highlight("internalField   uniform 0;")
    idx = rec.document().findBlockByNumber(0).text().index("uniform")
    assert _color_at(log, idx) == "#0000cc"


def test_structural_keyword_not_split_on_dot(rec):
    """'off.1' must not have its 'off' prefix coloured — the dot glues it to
    the rest of the identifier, just like the number-rule guard."""
    text = "field off.1;"
    log = rec.highlight(text)
    assert _color_at(log, text.index("off")) != "#0000cc"


# ---------------------------------------------------------------------------
# numbers
# ---------------------------------------------------------------------------

def test_integer_teal(rec):
    log = rec.highlight("nCells 100;")
    assert _color_at(log, 7) == "#008080"


def test_float_teal(rec):
    log = rec.highlight("nu 1.5e-5;")
    assert _color_at(log, 3) == "#008080"


def test_negative_exponent_teal(rec):
    text = "startTime -1e-05;"
    log = rec.highlight(text)
    assert _color_at(log, text.index("-1e-05")) == "#008080"


def test_vector_components_teal(rec):
    text = "value (0 1 0);"
    for pos in (text.index("0"), text.index("1"), text.rindex("0")):
        log = rec.highlight(text)
        assert _color_at(log, pos) == "#008080"


def test_digit_in_patch_name_not_number(rec):
    """Trailing digits of identifiers like 'wall0' must not be teal."""
    text = "myPatch wall0;"
    log = rec.highlight(text)
    assert _color_at(log, text.index("0")) != "#008080"


def test_digit_after_hyphen_in_name_not_number(rec):
    text = "myPatch inlet-1;"
    log = rec.highlight(text)
    assert _color_at(log, text.index("1")) != "#008080"


def test_leading_digit_of_identifier_not_number(rec):
    text = "myPatch 0wall;"
    log = rec.highlight(text)
    assert _color_at(log, text.index("0")) != "#008080"


# ---------------------------------------------------------------------------
# value keywords (BC types, scheme words, solver names) — dark-cyan #007070
# ---------------------------------------------------------------------------

def test_bc_type_darkcyan(rec):
    for kw in ("zeroGradient", "fixedValue", "noSlip", "empty", "symmetry", "wall"):
        text = f"type {kw};"
        log = rec.highlight(text)
        idx = text.index(kw)
        assert _color_at(log, idx) == "#007070", f"{kw!r} should be dark-cyan"


def test_scheme_word_darkcyan(rec):
    log = rec.highlight("default Gauss linear;")
    assert _color_at(log, 8) == "#007070"   # 'Gauss'
    assert _color_at(log, 14) == "#007070"  # 'linear'


def test_solver_name_darkcyan(rec):
    for kw in ("PCG", "GAMG", "smoothSolver", "GaussSeidel"):
        text = f"solver {kw};"
        log = rec.highlight(text)
        idx = text.index(kw)
        assert _color_at(log, idx) == "#007070", f"{kw!r} should be dark-cyan"


def test_schema_keyword_darkcyan(rec):
    """Words from schema ChoiceItems (not in static list) are also dark-cyan."""
    log = rec.highlight("default leastSquares;")
    idx = "default leastSquares;".index("leastSquares")
    assert _color_at(log, idx) == "#007070"


def test_collect_schema_keywords_nonempty(qapp):
    kw = _collect_schema_keywords()
    assert len(kw) > 0
    assert "leastSquares" in kw   # choice value from fv_schemes schema
    assert "GAMG" in kw           # choice value from fv_solution schema


def test_collect_schema_keywords_includes_key_names(qapp):
    """Schema key names (not just choice values) are now returned."""
    kw = _collect_schema_keywords()
    assert "startFrom" in kw      # plain key from controlDict schema


def test_dict_key_darkcyan(rec):
    """blockMeshDict structural keys are highlighted dark cyan."""
    for kw in ("vertices", "blocks", "edges", "boundary", "mergePatchPairs"):
        text = f"{kw}\n("
        log = rec.highlight(text)
        assert _color_at(log, 0) == "#007070", f"{kw!r} should be dark-cyan"


def test_build_value_kw_rules_chunked(qapp):
    """Value-keyword rules are split into PCRE2-safe chunks, all valid."""
    rules = _build_value_kw_rules()
    assert len(rules) >= 1
    for qre, _fmt in rules:
        assert qre.isValid(), f"chunk pattern invalid: {qre.errorString()}"


def test_json_keywords_loaded(qapp, tmp_path, monkeypatch):
    """The shipped default list is loaded when no user file exists."""
    import ui.widgets._foam_highlighter as mod

    monkeypatch.setattr(mod, "_KW_FILE", tmp_path / "absent.json")
    kw = mod._load_foam_keywords()
    assert "zeroGradient" in kw   # in baseline foam_keywords.default.json
    assert "icoFoam" in kw        # in baseline foam_keywords.default.json
    # controlDict keys collected by the dictionary-read-call scan
    assert "application" in kw
    assert "writePrecision" in kw
    assert "timePrecision" in kw


def test_loader_prefers_user_file(qapp, tmp_path, monkeypatch):
    import json

    import ui.widgets._foam_highlighter as mod

    user = tmp_path / "foam_keywords.json"
    default = tmp_path / "foam_keywords.default.json"
    user.write_text(json.dumps({"keywords": ["userWord"]}))
    default.write_text(json.dumps({"keywords": ["defaultWord"]}))
    monkeypatch.setattr(mod, "_KW_FILE", user)
    monkeypatch.setattr(mod, "_KW_DEFAULT_FILE", default)
    kw = mod._load_foam_keywords()
    assert "userWord" in kw
    assert "defaultWord" not in kw


def test_loader_falls_back_to_default(qapp, tmp_path, monkeypatch):
    import json

    import ui.widgets._foam_highlighter as mod

    default = tmp_path / "foam_keywords.default.json"
    default.write_text(json.dumps({"keywords": ["defaultWord"]}))
    monkeypatch.setattr(mod, "_KW_FILE", tmp_path / "absent.json")
    monkeypatch.setattr(mod, "_KW_DEFAULT_FILE", default)
    assert "defaultWord" in mod._load_foam_keywords()


def test_loader_empty_when_both_missing(qapp, tmp_path, monkeypatch):
    import ui.widgets._foam_highlighter as mod

    monkeypatch.setattr(mod, "_KW_FILE", tmp_path / "a.json")
    monkeypatch.setattr(mod, "_KW_DEFAULT_FILE", tmp_path / "b.json")
    assert mod._load_foam_keywords() == frozenset()


def test_controldict_keys_darkcyan(qapp, tmp_path, monkeypatch):
    """controlDict keys from the shipped default list are highlighted."""
    import ui.widgets._foam_highlighter as mod

    monkeypatch.setattr(mod, "_KW_FILE", tmp_path / "absent.json")
    doc = QTextDocument()
    rec = _Rec(doc)
    for kw in ("application", "writePrecision", "timePrecision"):
        text = f"{kw} value;"
        log = rec.highlight(text)
        assert _color_at(log, 0) == "#007070", f"{kw!r} should be dark-cyan"


def test_dotted_identifier_value_keyword_not_split(qapp, tmp_path, monkeypatch):
    """A dotted set name like 'y0.1' must not have its 'y0' prefix coloured
    as the value keyword 'y0' — the dot glues it to the rest of the name."""
    import ui.widgets._foam_highlighter as mod

    monkeypatch.setattr(mod, "_KW_FILE", tmp_path / "absent.json")
    doc = QTextDocument()
    rec = _Rec(doc)
    text = "sets ( y0.1 { } );"
    log = rec.highlight(text)
    idx = text.index("y0.1")
    assert _color_at(log, idx) != "#007070"       # 'y'
    assert _color_at(log, idx + 1) != "#007070"   # '0'
    assert _color_at(log, idx) is None


def test_plain_y0_still_darkcyan(qapp, tmp_path, monkeypatch):
    """Regression guard: 'y0' on its own (not dotted) is still a real keyword."""
    import ui.widgets._foam_highlighter as mod

    monkeypatch.setattr(mod, "_KW_FILE", tmp_path / "absent.json")
    doc = QTextDocument()
    rec = _Rec(doc)
    text = "name y0;"
    log = rec.highlight(text)
    assert _color_at(log, text.index("y0")) == "#007070"


def test_json_keywords_filter_rejects_special_chars(qapp, tmp_path, monkeypatch):
    """Tokens with regex-special chars in the JSON must be silently dropped."""
    import json

    import ui.widgets._foam_highlighter as mod

    bad_json = tmp_path / "foam_keywords.json"
    bad_json.write_text(json.dumps({"keywords": [
        "validToken",
        "CoProcessor()",   # parentheses
        "Pipeline:",       # colon
        "n-heptane",       # hyphen at non-start
        "C8H18(L)",        # parens mid-word
        "123numeric",      # starts with digit — not an identifier
    ]}))
    monkeypatch.setattr(mod, "_KW_FILE", bad_json)
    kw = mod._load_foam_keywords()
    assert "validToken" in kw
    assert "CoProcessor()" not in kw
    assert "Pipeline:" not in kw
    assert "n-heptane" not in kw
    assert "C8H18(L)" not in kw
    assert "123numeric" not in kw


def test_ascii_binary_blue(rec):
    for kw in ("ascii", "binary"):
        text = f"writeFormat {kw};"
        log = rec.highlight(text)
        idx = text.index(kw)
        assert _color_at(log, idx) == "#0000cc", f"{kw!r} should be blue"


# ---------------------------------------------------------------------------
# plain text has no special colour
# ---------------------------------------------------------------------------

def test_plain_word_no_color(rec):
    # 'myOwnWord' is a plain identifier — no special colour ('nu' no longer
    # qualifies: the dictionary-read-call scan collects it as a real keyword)
    log = rec.highlight("myOwnWord 1e-6;")
    assert _color_at(log, 0) is None


# ---------------------------------------------------------------------------
# comment overrides inline tokens
# ---------------------------------------------------------------------------

def test_comment_overrides_keyword(rec):
    log = rec.highlight("// true false")
    assert _color_at(log, 3) == "#808080"   # 'true' inside comment → grey


def test_block_comment_overrides_macro(rec):
    log = rec.highlight("/* $var */")
    assert _color_at(log, 3) == "#808080"   # '$var' inside block comment → grey


# ---------------------------------------------------------------------------
# shell mode (Allrun / Allclean scripts)
# ---------------------------------------------------------------------------

def test_shell_hash_comment_grey(rec):
    rec.set_mode("shell")
    log = rec.highlight("#!/bin/sh")
    assert _color_at(log, 0) == "#808080"


def test_shell_runfunction_blue(rec):
    rec.set_mode("shell")
    log = rec.highlight("runApplication blockMesh")
    assert _color_at(log, 0) == "#0000cc"


def test_shell_utility_name_darkcyan(rec):
    rec.set_mode("shell")
    text = "runApplication blockMesh"
    log = rec.highlight(text)
    assert _color_at(log, text.index("blockMesh")) == "#007070"


def test_shell_keyword_not_split_on_dot(rec):
    """'config.fi' must not have its 'fi' suffix coloured as the shell
    keyword 'fi' — the dot glues it to the rest of the filename."""
    rec.set_mode("shell")
    text = "echo config.fi"
    log = rec.highlight(text)
    assert _color_at(log, text.index("fi", text.index("config"))) != "#0000cc"


def test_shell_variable_orange(rec):
    rec.set_mode("shell")
    log = rec.highlight("echo $case")
    assert _color_at(log, 5) == "#cc6600"


def test_shell_single_quoted_string_green(rec):
    rec.set_mode("shell")
    log = rec.highlight("echo 'hello'")
    assert _color_at(log, 6) == "#006400"


def test_shell_comment_overrides_keywords(rec):
    rec.set_mode("shell")
    log = rec.highlight("# runApplication blockMesh")
    assert _color_at(log, 2) == "#808080"


def test_shell_no_block_comment_state(rec):
    """/* is not a comment opener in shell mode — no multi-line state."""
    rec.set_mode("shell")
    rec.highlight("/* just punctuation")
    assert rec.document().findBlockByNumber(0).userState() == 0


def test_mode_switch_back_to_foam(rec):
    rec.set_mode("shell")
    rec.set_mode("foam")
    log = rec.highlight("// comment")
    assert _color_at(log, 0) == "#808080"


def test_set_mode_rejects_unknown(rec):
    with pytest.raises(ValueError):
        rec.set_mode("python")


# ---------------------------------------------------------------------------
# enable / disable toggle
# ---------------------------------------------------------------------------

def test_set_enabled_false_produces_no_formats(rec):
    rec.set_enabled(False)
    log = rec.highlight("true 1.0 // comment")
    assert log == [], "disabled highlighter should apply no formats"


def test_set_enabled_true_restores_highlighting(rec):
    rec.set_enabled(False)
    rec.set_enabled(True)
    log = rec.highlight("// comment")
    assert any(color == "#808080" for _, _, color in log), (
        "re-enabled highlighter should colour comments grey"
    )
