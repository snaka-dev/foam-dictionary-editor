# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from foam.lexer import OpenFoamLexer

# ── lexer // behaviour (#5) ───────────────────────────────────────────────────

def test_lexer_double_slash_in_quoted_string_is_not_comment():
    # A double-slash inside a quoted string must NOT start a comment.
    tokens = OpenFoamLexer('"path//value"').tokenize()
    word_tokens = [t for t in tokens if t.kind == "STRING"]
    assert len(word_tokens) == 1
    assert word_tokens[0].text == '"path//value"'


def test_lexer_double_slash_after_whitespace_is_comment():
    tokens = OpenFoamLexer("value // comment\n").tokenize()
    kinds = [t.kind for t in tokens]
    assert "LINE_COMMENT" in kinds
    word_tokens = [t for t in tokens if t.kind == "WORD"]
    assert any(t.text == "value" for t in word_tokens)
    assert not any("comment" in t.text for t in word_tokens)


def test_lexer_double_slash_standalone_starts_comment():
    tokens = OpenFoamLexer("// entire line\n").tokenize()
    assert tokens[0].kind == "LINE_COMMENT"


# ── braced macro references (${...}) ──────────────────────────────────────────

def _words(text: str) -> list[str]:
    return [t.text for t in OpenFoamLexer(text).tokenize() if t.kind == "WORD"]


def test_lexer_braced_macro_is_one_word():
    # Without this, `{` ends the word and a bare `$` is left behind, which the
    # parser reads as an entry key and then fails demanding a `;`.
    assert _words("${__settings}") == ["${__settings}"]


def test_lexer_braced_macro_with_scope_path():
    assert _words("${../_bladeForces}") == ["${../_bladeForces}"]


def test_lexer_braced_macro_keeps_following_tokens():
    kinds = [t.kind for t in OpenFoamLexer("${a};").tokenize() if t.kind != "WHITESPACE"]
    assert kinds == ["WORD", "SEMICOLON", "EOF"]


def test_lexer_braced_macro_inside_dictionary():
    kinds = [
        t.kind
        for t in OpenFoamLexer("b\n{\n    ${../a};\n}\n").tokenize()
        if t.kind not in ("WHITESPACE", "NEWLINE")
    ]
    assert kinds == ["WORD", "LBRACE", "WORD", "SEMICOLON", "RBRACE", "EOF"]


def test_lexer_nested_braces_in_macro_are_balanced():
    assert _words("${a${b}c}") == ["${a${b}c}"]


def test_lexer_plain_macro_unchanged():
    assert _words("$minX;") == ["$minX"]


def test_lexer_unterminated_braced_macro_does_not_hang():
    # Runs to end of text rather than looping; the parser reports the rest.
    assert _words("${unclosed") == ["${unclosed"]


def test_lexer_lone_brace_still_a_token():
    # Only a `{` directly after `$` is absorbed into the word.
    kinds = [t.kind for t in OpenFoamLexer("a {").tokenize() if t.kind != "WHITESPACE"]
    assert kinds == ["WORD", "LBRACE", "EOF"]


def test_lexer_eval_directive_still_splits_on_brace():
    # #eval relies on the split: DIRECTIVE + LBRACE + body + RBRACE, so the
    # parser's depth counter finds the right closing semicolon.
    kinds = [
        t.kind
        for t in OpenFoamLexer("#eval{ 1 + 2 };").tokenize()
        if t.kind != "WHITESPACE"
    ]
    assert kinds[:2] == ["DIRECTIVE", "LBRACE"]
    assert "RBRACE" in kinds
