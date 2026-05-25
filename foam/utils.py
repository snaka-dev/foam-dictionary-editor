# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from pathlib import Path


SCALAR_FORMAT_PRECISION = 12


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


def classify_parenthesized_value(text: str) -> tuple[str, object]:
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


def classify_simple_value(text: str) -> tuple[str, object]:
    """Classify a normalised scalar/vector/list value text into (node_type, value)."""
    text = text.strip()
    if text.startswith("(") and text.endswith(")"):
        return classify_parenthesized_value(text)
    if is_int(text):
        return "int", int(text)
    if is_number(text):
        return "scalar", float(text)
    return "word", text


def format_embedded_value(value_type: str, value, raw_value) -> str:
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
