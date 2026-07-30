# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import bisect
from pathlib import Path

from foam.nodes import FoamNode, NodeType

SCALAR_FORMAT_PRECISION = 12

_LARGE_FILE_BYTES = 100 * 1024  # 100 KB
_FOAM_SNIFF_BYTES = 512

# blockMeshDict `blocks ( … );` shape keywords the parser explodes into a
# block_list/block_entry tree (foam/parser.py's _scan_block_segments). Only
# "hex" is included: foam/block_mesh_extractor.py's _parse_hex_blocks only
# understands hex blocks, so any other shape word would desynchronise a
# tree-row index from the 3-D viewer's block index. Shared with
# foam/value_parse.py's block_entry validation.
BLOCK_SHAPE_WORDS = frozenset({"hex"})

# blockMesh accepts an optional `name <blockName>` prefix before the shape
# word (`name sideBlock hex ( … ) …`), used by the projected-geometry cases.
BLOCK_NAME_KEYWORD = "name"


def is_large_non_foam_file(path: str | Path) -> tuple[bool, int]:
    """Return (True, size_bytes) when a file is too large to be a custom dict
    without a FoamFile header — i.e. it is probably a log or output file.

    Small files (< 100 KB) always return (False, size) so that custom solver
    dictionaries without a FoamFile block are still parsed normally.
    Large files without a 'FoamFile' token in the first 512 bytes are skipped.
    """
    p = Path(path)
    try:
        size = p.stat().st_size
    except OSError:
        return False, 0
    if size < _LARGE_FILE_BYTES:
        return False, size
    try:
        with open(p, "rb") as f:
            header = f.read(_FOAM_SNIFF_BYTES)
        return b"FoamFile" not in header, size
    except OSError:
        return False, size


def is_script_text(text: str) -> bool:
    """Return True when text is a shell/interpreter script (shebang line)."""
    return text.startswith("#!")


def is_log_filename(name: str) -> bool:
    """Return True for solver/utility run logs by the ``log.<app>`` convention."""
    return name.startswith("log.")


def is_script_path(path: str | Path) -> bool:
    """Return True when the file at path starts with a shebang (``#!``)."""
    try:
        with open(path, "rb") as f:
            return f.read(2) == b"#!"
    except OSError:
        return False


def read_foam_file(path: str | Path) -> str:
    """Read a file as text, trying UTF-8 then falling back to latin-1.

    OpenFOAM files are nominally ASCII/UTF-8, but some Windows-generated
    cases contain non-UTF-8 bytes in comments or string values.  latin-1
    can decode any byte sequence without data loss.
    """
    p = Path(path)
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return p.read_text(encoding="latin-1")


def resolve_optionally_gzipped(path: Path) -> Path | None:
    """Return the on-disk file for a surface reference, transparent to gzip.

    OpenFOAM resolves a referenced file to a ``.gz`` sibling when the plain
    name is absent (and vice versa for a name that already ends in ``.gz``).
    Returns the actual existing path, or None when neither form exists.
    """
    if path.is_file():
        return path
    gz = path.parent / (path.name + ".gz")
    if gz.is_file():
        return gz
    if path.suffix == ".gz":
        stripped = path.parent / path.name[:-3]
        if stripped.is_file():
            return stripped
    return None


def is_int(text: str) -> bool:
    # "1.0" and "1e3" are intentionally treated as non-integer
    try:
        int(text)
        return "." not in text and "e" not in text.lower()
    except ValueError:
        return False


def is_number(text: str) -> bool:
    try:
        float(text)
        return True
    except ValueError:
        return False


def format_scalar(value) -> str:
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.{SCALAR_FORMAT_PRECISION}g}"
    return str(value)


def parse_box_pair(text: str) -> list[list[float]] | None:
    """Parse '(x y z) (x y z)' into two float vectors, or return None on failure."""
    parts = []
    i, n = 0, len(text)
    while i < n:
        while i < n and text[i].isspace():
            i += 1
        if i >= n:
            break
        if text[i] != "(":
            return None
        start, depth = i, 0
        while i < n:
            if text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
                if depth == 0:
                    i += 1
                    break
            i += 1
        parts.append(text[start:i].strip())
    if len(parts) != 2:
        return None
    vectors = []
    for part in parts:
        if not (part.startswith("(") and part.endswith(")")):
            return None
        items = part[1:-1].strip().split()
        if len(items) != 3 or not all(is_number(x) for x in items):
            return None
        vectors.append([float(x) for x in items])
    return vectors


def classify_parenthesized_value(text: str) -> tuple[NodeType, object]:
    """Classify '(...)' text into (node_type, value). text must already be stripped."""
    inner = text[1:-1].strip()
    if not inner:
        return "raw_list", ""
    items = inner.split()
    if len(items) == 3 and all(is_number(x) for x in items):
        return "vector", [float(x) for x in items]
    if all(is_int(x) for x in items):
        return "int_list", [int(x) for x in items]
    if all(is_number(x) for x in items):
        return "scalar_list", [float(x) for x in items]
    return "raw_list", inner


def classify_simple_value(text: str) -> tuple[NodeType, object]:
    """Classify a normalised scalar/vector/list value text into (node_type, value)."""
    text = text.strip()
    if text.startswith("(") and text.endswith(")"):
        return classify_parenthesized_value(text)
    if is_int(text):
        return "int", int(text)
    if is_number(text):
        return "scalar", float(text)
    return "word", text


def format_leaf_value(node_type: NodeType, value) -> str:
    """Format a leaf node's value as it appears in the dictionary source.

    Shared by foam/writer.py (serialisation) and model/tree_model.py (Value
    column display) so the two cannot drift for the common leaf types.
    Structural and display-only types (dictionary, field_value, the
    nonuniform_list summary, …) are handled by the callers.
    """
    if node_type in {"vector", "scalar_list"}:
        return "(" + " ".join(format_scalar(x) for x in value) + ")"
    if node_type == "box_pair":
        p1, p2 = value
        return (
            "(" + " ".join(format_scalar(x) for x in p1) + ") "
            "(" + " ".join(format_scalar(x) for x in p2) + ")"
        )
    if node_type == "int_list":
        return "(" + " ".join(str(x) for x in value) + ")"
    if node_type == "raw_list":
        return "(" + str(value) + ")"
    if node_type == "scalar":
        return format_scalar(value)
    return "" if value is None else str(value)


def split_block_entry_tokens(text: str) -> list[str]:
    """Split a normalised block_entry value into top-level tokens.

    Each bare word (e.g. ``hex``, a zone name, a grading keyword, a ``$macro``
    tail) is one token; each parenthesised group (e.g. ``(0 1 2 3 4 5 6 7)``)
    is one token including its own parentheses, with nested parens kept
    intact. Shared by foam/value_parse.py's block_entry validation and
    model/tree_model.py's block_entry tooltip, so both read the same
    shape/vertices/zone/cells/grading positions off the same split.
    """
    tokens: list[str] = []
    i, n = 0, len(text)
    while i < n:
        while i < n and text[i].isspace():
            i += 1
        if i >= n:
            break
        if text[i] == "(":
            start, depth = i, 0
            while i < n:
                if text[i] == "(":
                    depth += 1
                elif text[i] == ")":
                    depth -= 1
                    if depth == 0:
                        i += 1
                        break
                i += 1
            tokens.append(text[start:i])
        else:
            start = i
            while i < n and not text[i].isspace() and text[i] != "(":
                i += 1
            tokens.append(text[start:i])
    return tokens


def strip_block_name_prefix(tokens: list[str]) -> tuple[str, list[str]]:
    """Split blockMesh's optional ``name <blockName>`` prefix off a block entry.

    Returns (block_name, remaining_tokens) with the shape word first in
    *remaining_tokens*; block_name is "" when there is no prefix. Shared by
    block_entry validation and the tooltip so both agree on where an entry's
    shape word starts. The parser's segment scanner applies the same rule at
    the token level (it has no split text to work from) -- keep the two in
    step when changing what counts as a prefix.
    """
    if (
        len(tokens) >= 3
        and tokens[0] == BLOCK_NAME_KEYWORD
        and not tokens[1].startswith("(")
        and tokens[2] in BLOCK_SHAPE_WORDS
    ):
        return tokens[1], tokens[2:]
    return "", tokens


def non_block_rows(parent: FoamNode) -> list[int]:
    """Ascending rows of *parent*'s children that are not ``block_entry``.

    Precomputed input for :func:`block_number` when the same list is consulted
    for many rows (the Tree view's key column).
    """
    return [
        i for i, child in enumerate(parent.children)
        if child.node_type != "block_entry"
    ]


def block_number(
    parent: FoamNode | None, row: int, skipped: list[int] | None = None
) -> int:
    """The 3-D viewer's block index for the ``block_entry`` at *row*.

    Normally *row* itself. A ``blocks ( … )`` list may also hold
    ``directive_entry`` children -- an ``#include`` contributing blocks
    defined in another file -- which take a row without being a block, while
    the viewer numbers hex entries only. Without this correction the first
    real block below an ``#include`` would be labelled "block 1" where the
    viewer draws a 0.

    Note both sides are then numbering only the blocks written *in this file*:
    what the ``#include`` pulls in is invisible to FoDE (in the tutorial case
    that motivated this, it is a symlink Allrun creates at run time), so these
    indices can differ from blockMesh's own once it resolves the include.
    """
    if parent is None:
        return row
    if skipped is None:
        skipped = non_block_rows(parent)
    return row - bisect.bisect_left(skipped, row)


def describe_block_entry(text: str) -> tuple[str, str, str, str, str]:
    """Decompose a block_entry value into (name, vertices, zone, cells, grading).

    Reads positionally off split_block_entry_tokens: an optional
    ``name <blockName>`` prefix, the shape word, the vertices group, an
    optional zone name, an optional cells group, and an optional
    "gradingKeyword (…)" pair. Pieces that are absent (a bare macro tail, a
    missing group) come back as "". Used by the Tree view's block_entry
    tooltip.
    """
    block_name, tokens = strip_block_name_prefix(split_block_entry_tokens(text))
    vertices = zone = cells = grading = ""
    i = 1  # tokens[0] is the shape word

    if i < len(tokens) and tokens[i].startswith("("):
        vertices = tokens[i][1:-1].strip()
        i += 1

    if i < len(tokens) and not tokens[i].startswith("("):
        # A bare word here is either a zone name (followed by a cells group)
        # or a standalone macro tail (nothing meaningful follows).
        if i + 1 < len(tokens) and tokens[i + 1].startswith("("):
            zone = tokens[i]
            i += 1
        else:
            return block_name, vertices, zone, cells, grading

    if i < len(tokens) and tokens[i].startswith("("):
        cells = tokens[i][1:-1].strip()
        i += 1

    if (
        i + 1 < len(tokens)
        and not tokens[i].startswith("(")
        and tokens[i + 1].startswith("(")
    ):
        grading = f"{tokens[i]} {tokens[i + 1]}"

    return block_name, vertices, zone, cells, grading


def format_embedded_value(value_type: NodeType, value, raw_value) -> str:
    if value_type in {"vector", "scalar_list"}:
        return "(" + " ".join(format_scalar(x) for x in value) + ")"
    if value_type == "int_list":
        return "(" + " ".join(str(x) for x in value) + ")"
    if value_type == "raw_list":
        raw = raw_value if raw_value is not None else value
        raw_str = str(raw)
        if raw_str.startswith("(") and raw_str.endswith(")"):
            return raw_str
        return "(" + raw_str + ")"
    if value_type in {"int", "scalar"}:
        return format_scalar(value)
    return str(raw_value if raw_value is not None else value)
