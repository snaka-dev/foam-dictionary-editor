# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations
from foam.utils import classify_parenthesized_value, classify_simple_value, is_int, is_number, parse_box_pair
from foam.lexer import OpenFoamLexer
from foam.nodes import FoamNode

class ParseError(Exception):
    pass


class OpenFoamParser:
    TRIVIA = {"WHITESPACE", "NEWLINE", "LINE_COMMENT", "BLOCK_COMMENT"}
    SOFT_TRIVIA = {"WHITESPACE", "NEWLINE"}

    FIELD_VALUE_TYPES = {
        "volScalarFieldValue",
        "volVectorFieldValue",
        "volTensorFieldValue",
        "volSymmTensorFieldValue",
        "volSphericalTensorFieldValue",
        "surfaceScalarFieldValue",
        "surfaceVectorFieldValue",
    }

    def __init__(self, text: str):
        self.text = text
        self.tokens = OpenFoamLexer(text).tokenize()
        self.index = 0

    def parse(self) -> FoamNode:
        root = FoamNode(name="root", node_type="dictionary")

        while True:
            leading = self._collect_trivia()
            if self._check("EOF"):
                break

            node = self._parse_entry()
            node.leading_trivia = leading
            root.add_child(node)

        return root

    def _parse_entry(self) -> FoamNode:
        self._skip_soft_trivia()
        start_index = self.index

        if self._check("DIRECTIVE"):
            return self._parse_directive_entry(start_index)

        if self._is_macro_only_entry():
            macro_text = self._advance().text
            self._expect("SEMICOLON")

            node = FoamNode(name="", node_type="macro_entry", value=macro_text)
            return self._finalize_node(node, start_index)

        try:
            key = self._parse_key()
            self._skip_soft_trivia()

            if self._check("LBRACE"):
                return self._parse_dictionary_entry(key, start_index)

            if self._check("LPAREN"):
                special = self._try_parse_special_parenthesized_entry(key, start_index)
                if special is not None:
                    return special

            value_text = self._read_value_text_until_semicolon()
            self._expect("SEMICOLON")

            node_type, value = self._classify_value(key, value_text)

            node = FoamNode(name=key, node_type=node_type, value=value)
            return self._finalize_node(node, start_index)

        except ParseError:
            self.index = start_index
            return self._parse_unknown_raw_entry(start_index)

    def _parse_directive_entry(self, start_index: int) -> FoamNode:
        parts = []

        while True:
            tok = self.tokens[self.index]

            if tok.kind in {"EOF", "NEWLINE", "LINE_COMMENT", "BLOCK_COMMENT"}:
                break

            parts.append(tok.text)
            self.index += 1

        if not parts:
            raise ParseError("empty directive entry")

        text = "".join(parts).strip()
        node = FoamNode(name="", node_type="directive_entry", value=text)
        return self._finalize_node(node, start_index)

    def _parse_unknown_raw_entry(self, start_index: int) -> FoamNode:
        parts = []
        depth = 0

        while True:
            tok = self.tokens[self.index]

            if tok.kind == "EOF":
                break

            if depth == 0 and tok.kind == "SEMICOLON":
                parts.append(tok.text)
                self.index += 1
                break

            if depth == 0 and tok.kind in {"NEWLINE", "LINE_COMMENT"} and parts:
                break

            if tok.kind == "LPAREN":
                depth += 1
            elif tok.kind == "RPAREN":
                depth = max(0, depth - 1)

            parts.append(tok.text)
            self.index += 1

        text = "".join(parts).strip()
        if not text:
            raise ParseError("could not parse unknown raw entry")

        node = FoamNode(name="", node_type="unknown_raw_entry", value=text)
        return self._finalize_node(node, start_index)

    def _parse_dictionary_entry(self, key: str, start_index: int) -> FoamNode:
        self._expect("LBRACE")
        node = FoamNode(name=key, node_type="dictionary")

        while True:
            inner_trivia = self._collect_trivia()
            if self._check("RBRACE"):
                break
            if self._check("EOF"):
                raise ParseError("unexpected EOF while parsing dictionary")

            child = self._parse_entry()
            child.leading_trivia = inner_trivia
            node.add_child(child)

        self._expect("RBRACE")
        node.raw_text = self._tokens_text(start_index, self.index)
        return node

    def _try_parse_special_parenthesized_entry(self, key: str, start_index: int):
        if key in {"defaultFieldValues", "default", "fieldValues"}:
            return self._parse_field_value_block_entry(key, start_index)

        if key == "regions":
            return self._parse_regions_entry(key, start_index)

        return None

    def _parse_field_value_block_entry(self, key: str, start_index: int) -> FoamNode:
        self._expect("LPAREN")
        values = []

        while True:
            self._skip_soft_trivia()

            if self._check("RPAREN"):
                break
            if self._check("EOF"):
                raise ParseError("unexpected EOF while parsing fieldValues block")

            values.append(self._parse_field_value_item())

        self._expect("RPAREN")
        self._expect("SEMICOLON")

        node = FoamNode(name=key, node_type="field_value_block", value=values)
        return self._finalize_node(node, start_index)

    def _parse_field_value_item(self):
        self._skip_soft_trivia()

        field_type_tok = self._advance()
        if field_type_tok.kind != "WORD" or field_type_tok.text not in self.FIELD_VALUE_TYPES:
            raise ParseError(
                f"unexpected token {field_type_tok.kind} at {field_type_tok.pos} "
                f"while parsing field value item"
            )

        self._skip_soft_trivia()
        field_name = self._parse_key()
        self._skip_soft_trivia()

        value = self._parse_embedded_value()

        return FoamNode(
            name=field_name,
            node_type="field_value",
            value={
                "field_type": field_type_tok.text,
                "field_name": field_name,
                "value_type": value["value_type"],
                "value": value["value"],
                "raw_value": value["raw_value"],
            },
        )

    def _parse_regions_entry(self, key: str, start_index: int) -> FoamNode:
        self._expect("LPAREN")
        node = FoamNode(name=key, node_type="region_block")

        while True:
            inner_trivia = self._collect_trivia()

            if self._check("RPAREN"):
                break
            if self._check("EOF"):
                raise ParseError("unexpected EOF while parsing regions block")

            region_name = self._parse_key()
            self._skip_soft_trivia()

            if not self._check("LBRACE"):
                raise ParseError(
                    f"expected LBRACE after region selector '{region_name}' "
                    f"but got {self.tokens[self.index].kind} at {self.tokens[self.index].pos}"
                )

            region_node = self._parse_dictionary_entry(region_name, self.index - 1)
            region_node.leading_trivia = inner_trivia
            region_node.node_type = "region_entry"
            node.add_child(region_node)

        self._expect("RPAREN")
        self._expect("SEMICOLON")

        node.inline_comment = self._collect_inline_comment()
        node.raw_text = self._tokens_text(start_index, self.index)
        return node

    def _parse_embedded_value(self):
        self._skip_soft_trivia()
        tok = self.tokens[self.index]

        if tok.kind == "LPAREN":
            text = self._read_parenthesized_text()
            value_type, value = classify_simple_value(text)
            return {"value_type": value_type, "value": value, "raw_value": text}

        if tok.kind in {"WORD", "STRING"}:
            text = self._advance().text
            value_type, value = classify_simple_value(text)
            return {"value_type": value_type, "value": value, "raw_value": text}

        raise ParseError(f"unexpected token {tok.kind} at {tok.pos} while parsing embedded value")

    def _read_parenthesized_text(self) -> str:
        self._skip_soft_trivia()
        if not self._check("LPAREN"):
            raise ParseError("expected LPAREN")

        parts = []
        depth = 0

        while True:
            tok = self._advance()

            if tok.kind == "LPAREN":
                depth += 1
                parts.append(tok.text)
                continue

            if tok.kind == "RPAREN":
                depth -= 1
                parts.append(tok.text)
                if depth == 0:
                    break
                continue

            if tok.kind == "EOF":
                raise ParseError("unexpected EOF while parsing parenthesized value")

            if tok.kind in self.SOFT_TRIVIA:
                if parts and not parts[-1].endswith((" ", "\n", "\t")):
                    parts.append(" ")
                continue

            parts.append(tok.text)

        return " ".join("".join(parts).split())

    def _is_macro_only_entry(self) -> bool:
        tok = self.tokens[self.index]
        return tok.kind == "WORD" and tok.text.startswith("$")

    def _parse_key(self) -> str:
        tok = self._advance()
        if tok.kind == "WORD":
            key = tok.text
            if self._check("LPAREN"):          # handles keys like grad(p), div(phi,U)
                rest = self._read_parenthesized_text()
                return key + rest
            return key
        if tok.kind == "STRING":
            return tok.text
        raise ParseError(f"unexpected token {tok.kind} at {tok.pos} while parsing key")

    def _read_value_text_until_semicolon(self) -> str:
        parts = []
        depth = 0

        while True:
            tok = self.tokens[self.index]

            if tok.kind == "EOF":
                raise ParseError("unexpected EOF while parsing entry value")

            if depth == 0 and tok.kind == "SEMICOLON":
                break

            if depth == 0 and tok.kind in {"LINE_COMMENT", "BLOCK_COMMENT"}:
                break

            self.index += 1

            if tok.kind in self.SOFT_TRIVIA:
                if parts and not parts[-1].endswith((" ", "\n", "\t")):
                    parts.append(" ")
                continue

            if tok.kind == "LPAREN":
                depth += 1
                parts.append(tok.text)
                continue

            if tok.kind == "RPAREN":
                depth -= 1
                if depth < 0:
                    raise ParseError(f"unexpected token RPAREN at {tok.pos}")
                parts.append(tok.text)
                continue

            if tok.kind == "LBRACE":
                depth += 1
                parts.append(tok.text)
                continue

            if tok.kind == "RBRACE":
                depth -= 1
                if depth < 0:
                    raise ParseError(f"unexpected RBRACE at {tok.pos}")
                parts.append(tok.text)
                continue

            if tok.kind in {"WORD", "STRING", "DIRECTIVE"}:
                parts.append(tok.text)
                continue

            raise ParseError(f"unexpected token {tok.kind} at {tok.pos}")

        text = "".join(parts).strip()
        if not text:
            raise ParseError("empty value before semicolon")
        return " ".join(text.split())

    def _classify_value(self, key: str, text: str):
        if key == "box":
            box_pair = parse_box_pair(text)
            if box_pair is not None:
                return "box_pair", box_pair

        if text.startswith("(") and text.endswith(")"):
            return classify_parenthesized_value(text)

        if text.startswith('"') and text.endswith('"'):
            return "string", text

        if text.startswith("$"):
            return "macro", text

        if " " in text:
            return "compound", text

        if is_int(text):
            return "int", int(text)

        if is_number(text):
            return "scalar", float(text)

        return "word", text

    def _collect_trivia(self) -> list[str]:
        parts = []
        while self.tokens[self.index].kind in self.TRIVIA:
            parts.append(self.tokens[self.index].text)
            self.index += 1
        return parts

    def _collect_inline_comment(self) -> str:
        saved = self.index
        parts = []

        while self.tokens[self.index].kind == "WHITESPACE":
            parts.append(self.tokens[self.index].text)
            self.index += 1

        if self.tokens[self.index].kind in {"LINE_COMMENT", "BLOCK_COMMENT"}:
            parts.append(self.tokens[self.index].text)
            self.index += 1
            return "".join(parts)

        self.index = saved
        return ""

    def _skip_soft_trivia(self) -> None:
        while self.tokens[self.index].kind in self.SOFT_TRIVIA:
            self.index += 1

    def _tokens_text(self, start: int, end: int) -> str:
        return "".join(tok.text for tok in self.tokens[start:end])

    def _check(self, kind: str) -> bool:
        return self.tokens[self.index].kind == kind

    def _advance(self):
        tok = self.tokens[self.index]
        self.index += 1
        return tok

    def _expect(self, kind: str):
        self._skip_soft_trivia()
        tok = self._advance()
        if tok.kind != kind:
            raise ParseError(f"expected {kind} but got {tok.kind} at {tok.pos}")
        return tok

    def _finalize_node(self, node: FoamNode, start_index: int) -> FoamNode:
        node.inline_comment = self._collect_inline_comment()
        node.raw_text = self._tokens_text(start_index, self.index)
        return node
