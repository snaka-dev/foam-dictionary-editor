# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Variable resolution for OpenFOAM dictionary files.

Provides build_var_map / substitute_vars / eval_foam_expr, shared by
block_mesh_extractor and topo_set_extractor.
"""
from __future__ import annotations

import re

from foam.nodes import FoamNode

_EVAL_VALUE_RE = re.compile(r'^#eval\s*\{\s*([^}]+)\}')
_SAFE_EXPR_RE = re.compile(r'^[\d\s\+\-\*/\.\(\)eE]+$')


def eval_foam_expr(expr: str) -> str | None:
    """Evaluate a numeric arithmetic expression from #eval{...}.

    Returns the float result as a string, or None if the expression
    contains non-numeric tokens (e.g. unresolved $var references).
    """
    cleaned = expr.strip()
    if not _SAFE_EXPR_RE.match(cleaned):
        return None
    try:
        result = eval(cleaned, {"__builtins__": {}}, {})  # noqa: S307
        return str(float(result))
    except Exception:
        return None


def substitute_vars(text: str, var_map: dict[str, str]) -> str:
    """Replace $name and ${name} references with values from var_map."""
    if not var_map:
        return text
    for name in sorted(var_map, key=len, reverse=True):
        val = var_map[name]
        text = re.sub(r'\$\{' + re.escape(name) + r'\}', val, text)
        text = re.sub(r'\$' + re.escape(name) + r'(?!\w)', val, text)
    return text


def build_var_map(
    root: FoamNode,
    skip_keys: frozenset[str] = frozenset(),
) -> dict[str, str]:
    """Collect top-level variable definitions as a substitution map.

    Seeds from direct scalar/int values then iterates macro-resolution and
    #eval-expression passes until stable.  Multiple iterations handle chains
    like ``z1 #eval{$z0+$dz0}; z2 $z1;`` where the macro reference to z1
    cannot be resolved until #eval has run first.

    skip_keys: optional set of structural key names to ignore (e.g. the
    top-level block names in blockMeshDict such as "vertices", "blocks").
    """
    var_map: dict[str, str] = {}

    for child in root.children:
        if not child.name or child.name in skip_keys or child.value is None:
            continue
        if child.node_type in ("scalar", "int"):
            var_map[child.name] = str(child.value)

    for _ in range(len(root.children) + 1):
        prev_len = len(var_map)

        for child in root.children:
            if not child.name or child.name in skip_keys or child.value is None:
                continue
            if child.name in var_map:
                continue
            if child.node_type == "macro":
                ref = str(child.value).lstrip("$")
                if ref.startswith("{"):
                    ref = ref[1:].rstrip("}")
                if ref in var_map:
                    var_map[child.name] = var_map[ref]

        for child in root.children:
            if not child.name or child.name in skip_keys or child.value is None:
                continue
            if child.name in var_map:
                continue
            if child.node_type not in ("word", "compound"):
                continue
            val_str = str(child.value).strip()
            m = _EVAL_VALUE_RE.match(val_str)
            if not m:
                continue
            result = eval_foam_expr(substitute_vars(m.group(1), var_map))
            if result is not None:
                var_map[child.name] = result

        for child in root.children:
            if not child.name or child.name in skip_keys or child.value is None:
                continue
            if child.name in var_map:
                continue
            if child.node_type not in ("word", "compound"):
                continue
            val_str = str(child.value).strip()
            if _EVAL_VALUE_RE.match(val_str):
                continue
            substituted = substitute_vars(val_str, var_map)
            result = eval_foam_expr(substituted)
            if result is not None:
                var_map[child.name] = result

        if len(var_map) == prev_len:
            break

    return var_map
