# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from foam.lexer import OpenFoamLexer
from foam.nodes import BOOL_WORDS, FoamNode, NodeType
from foam.utils import (
    BLOCK_NAME_KEYWORD,
    BLOCK_SHAPE_WORDS,
    classify_parenthesized_value,
    classify_simple_value,
    is_int,
    is_number,
    parse_box_pair,
)


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

    _FIELD_VALUE_KEYS: frozenset[str] = frozenset({"defaultFieldValues", "default", "fieldValues"})

    # Add new named-block entries here; _try_parse_special_parenthesized_entry needs no changes.
    _NAMED_BLOCK_PARAMS: dict[str, tuple[NodeType, NodeType]] = {
        "regions":  ("region_block",   "region_entry"),
        "boundary": ("boundary_block", "boundary_entry"),
    }

    # Like _NAMED_BLOCK_PARAMS but entries are anonymous dicts { ... } with no name prefix.
    _ANONYMOUS_BLOCK_PARAMS: dict[str, tuple[NodeType, NodeType]] = {
        "actions": ("action_list", "action_entry"),
    }

    # Keys that MAY hold a parenthesised list of named dicts (the classic
    # sampleDict style `sets ( y0.1 { … } … );`) but also legitimately appear
    # as plain word lists (topoSet's `sets (setA setB);`). A lookahead decides:
    # only `name {` content parses as a named block; anything else falls
    # through to the ordinary value path (raw_list etc.).
    _OPTIONAL_NAMED_BLOCK_PARAMS: dict[str, tuple[NodeType, NodeType]] = {
        "sets":     ("named_dict_list", "named_dict_entry"),
        "surfaces": ("named_dict_list", "named_dict_entry"),
    }

    # Keys that MAY hold a parenthesised list of anonymous "shape (...)..."
    # entries (blockMeshDict's `blocks ( hex (...) ... hex ... );`). A
    # non-consuming scan (_scan_block_segments) decides: only a list whose
    # entries all start with a word in _BLOCK_SHAPE_WORDS explodes into one
    # block_entry per shape; anything else (a bare word list, a non-hex
    # leading shape) falls through to the ordinary raw_list path. An
    # #include among the blocks is kept, as its own directive_entry child,
    # so the blocks around it still get rows -- see foam/utils.py's
    # block_number for how the numbering steps over it.
    # Row index in the tree MUST match the 3-D viewer's block index, which is
    # why only "hex" is accepted here — see foam/utils.py's BLOCK_SHAPE_WORDS.
    _POSITIONAL_BLOCK_PARAMS: dict[str, tuple[NodeType, NodeType]] = {
        "blocks": ("block_list", "block_entry"),
    }

    _BLOCK_SHAPE_WORDS = BLOCK_SHAPE_WORDS

    def __init__(self, text: str):
        self.text = text
        self.tokens = OpenFoamLexer(text).tokenize()
        self.index = 0
        self.errors: list[tuple[int, str]] = []

    def parse(self) -> FoamNode:
        root = FoamNode(name="root", node_type="dictionary")

        while True:
            leading = self._collect_trivia()
            if self._check("EOF"):
                # Trivia with no entry after it -- typically the blank lines
                # and "// ****" footer banner that close an OpenFOAM
                # dictionary. It belongs to no node, so park it on the root
                # for write_root to re-emit.
                root.trailing_trivia = leading
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
            # The `;` is optional: OpenFOAM accepts a bare `$macro` as a whole
            # statement inside a dictionary (`maxX { $minX }`, `"pcorr.*" { $p
            # … }`). Peek rather than skip, so that when there is no `;` the
            # trivia after the macro stays with the next entry and the writer
            # reproduces the source unchanged.
            if self._peek_kind_past_trivia() == "SEMICOLON":
                self._expect("SEMICOLON")

            node = FoamNode(name="", node_type="macro_entry", value=macro_text)
            return self._finalize_node(node, start_index)

        if self._check("SEMICOLON"):
            # A stray ";" closing a dictionary (`divSchemes { … };`). OpenFOAM
            # tolerates it, so it is not a parse failure and must not land in
            # self.errors -- 54 v2512 tutorial dictionaries are written this
            # way and would otherwise all report "1 unrecognized entries".
            # It still becomes its own node, because the ";" is real text that
            # has to be written back; the writer keeps it on the "}" line.
            self._advance()
            node = FoamNode(name="", node_type="unknown_raw_entry", value=";")
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

        except ParseError as e:
            pos = self.tokens[start_index].pos if start_index < len(self.tokens) else -1
            self.errors.append((pos, str(e)))
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
        node.source_line = self._token_line(start_index)
        node.source_end_line = self._token_line(self.index - 1)
        return node

    def _try_parse_special_parenthesized_entry(self, key: str, start_index: int):
        if key in self._FIELD_VALUE_KEYS:
            return self._parse_field_value_block_entry(key, start_index)
        params = self._NAMED_BLOCK_PARAMS.get(key)
        if params is not None:
            return self._parse_named_dict_block(key, start_index, *params)
        params = self._ANONYMOUS_BLOCK_PARAMS.get(key)
        if params is not None:
            return self._parse_anonymous_dict_block(key, start_index, *params)
        params = self._OPTIONAL_NAMED_BLOCK_PARAMS.get(key)
        if params is not None and self._looks_like_named_dict_list():
            return self._parse_named_dict_block(key, start_index, *params)
        params = self._POSITIONAL_BLOCK_PARAMS.get(key)
        if params is not None and self._looks_like_block_list():
            return self._parse_block_list(key, start_index, *params)
        return None

    def _looks_like_named_dict_list(self) -> bool:
        """Non-consuming lookahead: does the LPAREN open a `name { … }` list?"""
        saved = self.index
        try:
            self._expect("LPAREN")
            self._collect_trivia()
            if self._check("RPAREN") or self._check("EOF"):
                return False
            try:
                self._parse_key()
            except ParseError:
                return False
            self._collect_trivia()
            return self._check("LBRACE")
        finally:
            self.index = saved

    def _looks_like_block_list(self) -> bool:
        """Non-consuming lookahead: is this a pure `shape (...)... shape ...` list?"""
        return self._scan_block_segments() is not None

    def _next_content_tokens(self, start: int, count: int) -> list[int]:
        """Indices of the next *count* non-trivia tokens at or after *start*.

        Skips trivia without a token budget, so an arbitrary run of comments
        or blank lines between two content tokens cannot hide one from the
        lookahead. Stops early at EOF, returning fewer than *count* indices.
        """
        found: list[int] = []
        i = start
        while i < len(self.tokens) and len(found) < count:
            kind = self.tokens[i].kind
            if kind == "EOF":
                break
            if kind not in self.TRIVIA:
                found.append(i)
            i += 1
        return found

    def _block_segment_value(self, seg_start: int, seg_end: int) -> str:
        """Join a block segment's content tokens into its one-line value.

        Trivia *between* content tokens is dropped rather than flattened into
        the value: a comment inside a block would otherwise become literal
        text in the value, and re-emitting that on one line would comment out
        everything after it -- silently destroying the block's cell counts and
        grading. This mirrors _read_value_text_until_semicolon, which skips
        comment tokens for the same reason.
        """
        parts = [
            " " if tok.kind in {"LINE_COMMENT", "BLOCK_COMMENT"} else tok.text
            for tok in self.tokens[seg_start:seg_end]
        ]
        return " ".join("".join(parts).split())

    def _block_segment_shape_index(self, i: int) -> int | None:
        """Token index of the shape word if *i* opens a block entry, else None.

        A shape word opens an entry at its own index. So does blockMesh's
        optional ``name <blockName>`` prefix -- but only when a shape word
        follows the name, so that a bare ``name`` appearing as a zone name or
        inside a grading tail keeps belonging to the entry it trails. The
        returned shape index lets the caller skip that shape word, which
        would otherwise look like a second entry starting mid-prefix.
        """
        tok = self.tokens[i]
        if tok.kind != "WORD":
            return None
        if tok.text in self._BLOCK_SHAPE_WORDS:
            return i
        if tok.text != BLOCK_NAME_KEYWORD:
            return None

        following = self._next_content_tokens(i + 1, 2)
        if len(following) != 2:
            return None
        name_tok, shape_tok = (self.tokens[j] for j in following)
        if (
            name_tok.kind == "WORD"
            and shape_tok.kind == "WORD"
            and shape_tok.text in self._BLOCK_SHAPE_WORDS
        ):
            return following[1]
        return None

    def _scan_block_segments(self) -> list[tuple[int, int, bool]] | None:
        """Scan a `( shape ... shape ... )` list, non-consuming (restores self.index).

        Starting from the current position (LPAREN not yet consumed), returns
        one (start_token_index, end_token_index, is_directive) triple per
        entry, where end_token_index points just past the entry's last content
        token (NOT past any trailing trivia) -- so a blank-line separator
        between two entries lands in the next entry's leading_trivia rather
        than the previous entry's raw_text. A depth-0 DIRECTIVE (an
        `#include` contributing blocks from another file) gets its own
        triple, flagged, spanning just its line. Returns None -- reject, fall
        back to the ordinary raw_list path -- when: the list is empty; the
        first non-trivia token isn't a word in _BLOCK_SHAPE_WORDS (covers a
        bare word list and a leading non-hex shape like `prism`/`hex2D`); no
        shape entry is present at all (a list of nothing but directives has
        no blocks to explode); or parens/braces don't balance.
        """
        saved = self.index
        try:
            self._expect("LPAREN")

            segments: list[tuple[int, int, bool]] = []
            depth = 0
            seg_start: int | None = None
            seg_end = 0
            # Shape word belonging to a `name <blockName>` prefix already
            # consumed as a segment start; it must not start a second one.
            prefix_shape: int | None = None

            while True:
                tok = self.tokens[self.index]

                if tok.kind == "EOF":
                    return None

                if depth == 0 and tok.kind == "RPAREN":
                    break

                if depth == 0 and tok.kind == "DIRECTIVE":
                    # Close the shape entry in progress, then take the
                    # directive's own line as one segment. It is kept rather
                    # than rejected so the blocks around it keep their rows;
                    # the blocks it pulls in are invisible here either way.
                    if seg_start is not None:
                        segments.append((seg_start, seg_end, False))
                        seg_start = None
                    dir_start = self.index
                    while self.tokens[self.index].kind not in {
                        "EOF", "NEWLINE", "LINE_COMMENT", "BLOCK_COMMENT",
                    }:
                        self.index += 1
                    segments.append((dir_start, self.index, True))
                    seg_end = self.index
                    continue

                if depth == 0 and tok.kind not in self.TRIVIA:
                    shape_index = (
                        None
                        if self.index == prefix_shape
                        else self._block_segment_shape_index(self.index)
                    )
                    if shape_index is not None:
                        if seg_start is not None:
                            segments.append((seg_start, seg_end, False))
                        seg_start = self.index
                        prefix_shape = shape_index
                    elif seg_start is None:
                        return None  # first content token isn't a shape word

                if tok.kind in {"LPAREN", "LBRACE"}:
                    depth += 1
                elif tok.kind in {"RPAREN", "RBRACE"}:
                    depth -= 1
                    if depth < 0:
                        return None

                self.index += 1
                if tok.kind not in self.TRIVIA:
                    seg_end = self.index

            if seg_start is not None:
                segments.append((seg_start, seg_end, False))
            if not any(not is_directive for _s, _e, is_directive in segments):
                return None

            # The list must be terminated by `);` right here. Without this
            # check the gate would accept, then _parse_block_list would raise
            # on the unexpected token -- turning what the ordinary value path
            # parses cleanly (e.g. `blocks ( hex … ) tail;`) into an
            # unknown_raw_entry plus a recorded parse error.
            after = self._next_content_tokens(self.index + 1, 1)
            if not after or self.tokens[after[0]].kind != "SEMICOLON":
                return None

            return segments
        finally:
            self.index = saved

    def _parse_block_list(
        self, key: str, start_index: int, block_type: NodeType, entry_type: NodeType,
    ) -> FoamNode:
        segments = self._scan_block_segments()
        if segments is None:
            raise ParseError(f"{key!r} did not scan as a block list")

        self._expect("LPAREN")
        node = FoamNode(name=key, node_type=block_type)

        for seg_start, seg_end, is_directive in segments:
            inner_trivia = self._collect_trivia()

            entry_start = self.index
            if is_directive:
                # _parse_directive_entry advances self.index itself, to the
                # same place seg_end marks.
                entry_node = self._parse_directive_entry(entry_start)
            else:
                value = self._block_segment_value(seg_start, seg_end)
                entry_node = FoamNode(name="", node_type=entry_type, value=value)
                self.index = seg_end
                self._finalize_node(entry_node, entry_start)
            entry_node.leading_trivia = inner_trivia
            node.add_child(entry_node)

        self._collect_trivia()
        self._expect("RPAREN")
        self._expect("SEMICOLON")

        return self._finalize_node(node, start_index)

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

    def _parse_named_dict_block(
        self, key: str, start_index: int, block_type: NodeType, entry_type: NodeType,
    ) -> FoamNode:
        self._expect("LPAREN")
        node = FoamNode(name=key, node_type=block_type)

        while True:
            inner_trivia = self._collect_trivia()

            if self._check("RPAREN"):
                break
            if self._check("EOF"):
                raise ParseError(f"unexpected EOF while parsing {key!r} block")

            if self._check("DIRECTIVE"):
                # A directive standing in for entries (blockMeshDict's
                # `boundary ( #include "…caseBoundary" outlet { … } );`). It is
                # not a named dict, so it becomes its own child rather than
                # failing the whole block into unknown_raw_entry -- which used
                # to cost every *following* patch its structured parse.
                directive = self._parse_directive_entry(self.index)
                directive.leading_trivia = inner_trivia
                node.add_child(directive)
                continue

            # Capture raw_text from the name token on: an entry regenerated
            # from raw_text (unmodified sibling of a modified one) must keep
            # its name, not start at the "{".
            entry_start = self.index
            entry_name = self._parse_key()
            self._collect_trivia()

            if not self._check("LBRACE"):
                raise ParseError(
                    f"expected LBRACE after {key!r} entry '{entry_name}' "
                    f"but got {self.tokens[self.index].kind} at {self.tokens[self.index].pos}"
                )

            entry_node = self._parse_dictionary_entry(entry_name, entry_start)
            entry_node.leading_trivia = inner_trivia
            entry_node.node_type = entry_type
            node.add_child(entry_node)

        self._expect("RPAREN")
        self._expect("SEMICOLON")

        return self._finalize_node(node, start_index)

    def _parse_anonymous_dict_block(
        self, key: str, start_index: int, block_type: NodeType, entry_type: NodeType,
    ) -> FoamNode:
        self._expect("LPAREN")
        node = FoamNode(name=key, node_type=block_type)

        while True:
            inner_trivia = self._collect_trivia()

            if self._check("RPAREN"):
                break
            if self._check("EOF"):
                raise ParseError(f"unexpected EOF while parsing {key!r} block")

            if not self._check("LBRACE"):
                raise ParseError(
                    f"expected LBRACE in {key!r} anonymous-dict block "
                    f"but got {self.tokens[self.index].kind} at {self.tokens[self.index].pos}"
                )

            entry_node = self._parse_dictionary_entry("", self.index)
            entry_node.node_type = entry_type
            entry_node.leading_trivia = inner_trivia
            node.add_child(entry_node)

        self._expect("RPAREN")
        self._expect("SEMICOLON")

        return self._finalize_node(node, start_index)

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

            if tok.kind in {"LINE_COMMENT", "BLOCK_COMMENT"}:
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
        parts: list[str] = []
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

            if tok.kind in {"LINE_COMMENT", "BLOCK_COMMENT"}:
                continue

            raise ParseError(f"unexpected token {tok.kind} at {tok.pos}")

        text = "".join(parts).strip()
        if not text:
            raise ParseError("empty value before semicolon")
        return " ".join(text.split())

    def _classify_value(self, key: str, text: str) -> tuple[NodeType, object]:
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
            parts = text.split(None, 2)
            if len(parts) >= 2 and parts[0] == "nonuniform" and parts[1].startswith("List"):
                return "nonuniform_list", text
            return "compound", text

        if is_int(text):
            return "int", int(text)

        if is_number(text):
            return "scalar", float(text)

        if text in BOOL_WORDS:
            return "bool", text

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

    def _peek_kind_past_trivia(self) -> str:
        """Kind of the next non-trivia token, without consuming anything.

        Unlike _expect, this leaves self.index alone, so trivia that turns out
        to belong to the following entry is not swallowed.
        """
        i = self.index
        while self.tokens[i].kind in self.SOFT_TRIVIA:
            i += 1
        return self.tokens[i].kind

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

    def _token_line(self, token_index: int) -> int:
        if token_index >= len(self.tokens):
            return 0
        return self.text.count("\n", 0, self.tokens[token_index].pos) + 1

    def _finalize_node(self, node: FoamNode, start_index: int) -> FoamNode:
        node.inline_comment = self._collect_inline_comment()
        node.raw_text = self._tokens_text(start_index, self.index)
        node.source_line = self._token_line(start_index)
        node.source_end_line = self._token_line(self.index - 1)
        return node
