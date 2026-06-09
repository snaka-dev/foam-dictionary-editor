# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Token:
    kind: str
    text: str
    pos: int


_SINGLE_CHAR_TOKENS = {
    "{": "LBRACE",
    "}": "RBRACE",
    "(": "LPAREN",
    ")": "RPAREN",
    ";": "SEMICOLON",
}


class OpenFoamLexer:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.length = len(text)

    def tokenize(self) -> list[Token]:
        tokens = []
        while self.pos < self.length:
            ch = self.text[self.pos]

            if ch in " \t":
                tokens.append(self._read_whitespace())
                continue

            if ch == "\n":
                tokens.append(Token("NEWLINE", "\n", self.pos))
                self.pos += 1
                continue

            if ch == "/" and self._peek(1) == "/":
                tokens.append(self._read_line_comment())
                continue

            if ch == "/" and self._peek(1) == "*":
                tokens.append(self._read_block_comment())
                continue

            if ch in _SINGLE_CHAR_TOKENS:
                tokens.append(Token(_SINGLE_CHAR_TOKENS[ch], ch, self.pos))
                self.pos += 1
                continue

            if ch == "#":
                tokens.append(self._read_directive())
                continue

            if ch == '"':
                tokens.append(self._read_string())
                continue

            tokens.append(self._read_word())

        tokens.append(Token("EOF", "", self.pos))
        return tokens

    def _peek(self, offset: int) -> str:
        idx = self.pos + offset
        if idx >= self.length:
            return ""
        return self.text[idx]

    def _read_whitespace(self) -> Token:
        start = self.pos
        while self.pos < self.length and self.text[self.pos] in " \t":
            self.pos += 1
        return Token("WHITESPACE", self.text[start:self.pos], start)

    def _read_line_comment(self) -> Token:
        start = self.pos
        self.pos += 2
        end = self.text.find("\n", self.pos)
        self.pos = end if end != -1 else self.length
        return Token("LINE_COMMENT", self.text[start:self.pos], start)

    def _read_block_comment(self) -> Token:
        start = self.pos
        self.pos += 2
        end = self.text.find("*/", self.pos)
        self.pos = end + 2 if end != -1 else self.length
        return Token("BLOCK_COMMENT", self.text[start:self.pos], start)

    def _read_directive(self) -> Token:
        start = self.pos
        self.pos += 1
        # Stop at whitespace OR '{' so that '#eval{...}' is split into
        # DIRECTIVE '#eval' + LBRACE + body + RBRACE, letting the parser's
        # depth counter find the correct closing semicolon.
        while self.pos < self.length and not self.text[self.pos].isspace() and self.text[self.pos] != "{":
            self.pos += 1
        return Token("DIRECTIVE", self.text[start:self.pos], start)

    def _read_string(self) -> Token:
        start = self.pos
        self.pos += 1
        end = self.text.find('"', self.pos)
        self.pos = end + 1 if end != -1 else self.length
        return Token("STRING", self.text[start:self.pos], start)

    def _read_word(self) -> Token:
        # Per OpenFOAM syntax, // and /* always start a comment — even mid-word.
        # Quoted strings (handled by _read_string) are the only context where
        # // does not start a comment.
        start = self.pos
        while self.pos < self.length:
            ch = self.text[self.pos]
            if ch in " \t\n{}();" or (ch == "/" and self._peek(1) in "/*"):
                break
            self.pos += 1
        return Token("WORD", self.text[start:self.pos], start)
