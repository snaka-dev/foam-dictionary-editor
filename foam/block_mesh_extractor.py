# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import re
from dataclasses import dataclass, field

from foam.nodes import FoamNode

_EVAL_VALUE_RE = re.compile(r'^#eval\s*\{\s*([^}]+)\}')
_SAFE_EXPR_RE = re.compile(r'^[\d\s\+\-\*/\.\(\)eE]+$')


@dataclass
class BlockMeshData:
    vertices: list[list[float]]
    hex_blocks: list[list[int]]
    # patch_name → (patch_type, list_of_face_vertex_lists)
    boundary_faces: dict[str, tuple[str, list[list[int]]]] = field(default_factory=dict)
    scale: float = 1.0


# ── variable resolution ───────────────────────────────────────────────────────

_BLOCKMESH_STRUCTURAL = frozenset({
    "scale", "convertToMeters", "vertices", "blocks",
    "edges", "boundary", "mergePatchPairs", "defaultPatch",
})


def _eval_foam_expr(expr: str) -> str | None:
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


def _build_var_map(root: FoamNode) -> dict[str, str]:
    """Collect top-level variable definitions as a substitution map.

    Seeds from direct scalar/int values then iterates macro-resolution and
    #eval-expression passes until stable.  Multiple iterations handle chains
    like ``z1 #eval{$z0+$dz0}; z2 #eval{$z1+$dz1}; z001 $z1;`` where the
    macro reference to z1 cannot be resolved until #eval has run first.
    """
    var_map: dict[str, str] = {}

    # Seed with direct numeric values; skip word nodes — they may be #eval strings.
    for child in root.children:
        if not child.name or child.name in _BLOCKMESH_STRUCTURAL or child.value is None:
            continue
        if child.node_type in ("scalar", "int"):
            var_map[child.name] = str(child.value)

    # Iterate macro-resolution and #eval-evaluation until no new entries appear.
    # Upper bound: a dependency DAG of N nodes resolves in at most N iterations.
    # Circular references are safe — unresolvable vars simply stay absent.
    for _ in range(len(root.children) + 1):
        prev_len = len(var_map)

        # Macro pass: resolve $ref / ${ref} one level per iteration.
        for child in root.children:
            if not child.name or child.name in _BLOCKMESH_STRUCTURAL or child.value is None:
                continue
            if child.name in var_map:
                continue
            if child.node_type == "macro":
                ref = str(child.value).lstrip("$")
                if ref.startswith("{"):
                    ref = ref[1:].rstrip("}")
                if ref in var_map:
                    var_map[child.name] = var_map[ref]

        # #eval pass: evaluate arithmetic expressions whose variables are now known.
        for child in root.children:
            if not child.name or child.name in _BLOCKMESH_STRUCTURAL or child.value is None:
                continue
            if child.name in var_map:
                continue
            if child.node_type not in ("word", "compound"):
                continue
            val_str = str(child.value).strip()
            m = _EVAL_VALUE_RE.match(val_str)
            if not m:
                continue
            result = _eval_foam_expr(_substitute_vars(m.group(1), var_map))
            if result is not None:
                var_map[child.name] = result

        if len(var_map) == prev_len:
            break

    return var_map


def _substitute_vars(text: str, var_map: dict[str, str]) -> str:
    """Replace $name and ${name} references with values from var_map."""
    if not var_map:
        return text
    # Longest names first to avoid $xMin matching before $xMinExtra
    for name in sorted(var_map, key=len, reverse=True):
        val = var_map[name]
        text = re.sub(r'\$\{' + re.escape(name) + r'\}', val, text)
        text = re.sub(r'\$' + re.escape(name) + r'(?!\w)', val, text)
    return text


# ── raw-string parsers ────────────────────────────────────────────────────────

def parse_vertices(raw: str) -> list[list[float]]:
    """Parse '(x y z) (x y z) ...' into [[x,y,z], ...]."""
    result: list[list[float]] = []
    for m in re.finditer(r'\(\s*([^)]+)\)', raw):
        nums = m.group(1).split()
        if len(nums) == 3:
            try:
                result.append([float(n) for n in nums])
            except ValueError:
                pass
    return result


def _parse_hex_blocks(raw: str) -> list[list[int]]:
    """Extract hex (v0 .. v7) vertex-index lists from blocks raw text."""
    result: list[list[int]] = []
    for m in re.finditer(r'\bhex\s*\(\s*([^)]+)\)', raw):
        nums = m.group(1).split()
        if len(nums) == 8:
            try:
                result.append([int(n) for n in nums])
            except ValueError:
                pass
    return result


def _extract_boundary_from_tree(boundary_node: FoamNode) -> dict[str, tuple[str, list[list[int]]]]:
    """Walk a parsed boundary_block FoamNode and extract patch data."""
    result: dict[str, tuple[str, list[list[int]]]] = {}
    for patch in boundary_node.children:
        if patch.node_type != "boundary_entry":
            continue
        patch_type = ""
        faces: list[list[int]] = []
        for item in patch.children:
            if item.name == "type":
                patch_type = str(item.value)
            elif item.name == "faces" and item.node_type == "raw_list":
                for fm in re.finditer(r"\(([^)]+)\)", str(item.value)):
                    nums = fm.group(1).split()
                    if len(nums) >= 3:
                        try:
                            faces.append([int(x) for x in nums])
                        except ValueError:
                            pass
        result[patch.name] = (patch_type, faces)
    return result


def _parse_boundary_block(raw: str) -> dict[str, tuple[str, list[list[int]]]]:
    """Parse the raw text of a boundary (...); block.

    Returns {patch_name: (patch_type, [[v0,v1,...], ...])}
    """
    # Strip outer ( ... );
    raw = raw.strip()
    if raw.startswith("("):
        raw = raw[1:]
    if raw.endswith(";"):
        raw = raw[:-1]
    raw = raw.rstrip()
    if raw.endswith(")"):
        raw = raw[:-1]

    result: dict[str, tuple[str, list[list[int]]]] = {}
    i = 0
    n = len(raw)

    while i < n:
        # Skip whitespace
        while i < n and raw[i] in " \t\n\r":
            i += 1
        if i >= n:
            break

        # Read identifier (patch name)
        if not (raw[i].isalpha() or raw[i] == "_"):
            i += 1
            continue
        j = i
        while j < n and (raw[j].isalnum() or raw[j] in "_-."):
            j += 1
        patch_name = raw[i:j]
        i = j

        # Advance to opening {
        while i < n and raw[i] != "{":
            i += 1
        if i >= n:
            break
        i += 1  # skip {

        # Find matching }
        depth = 1
        block_start = i
        while i < n and depth > 0:
            if raw[i] == "{":
                depth += 1
            elif raw[i] == "}":
                depth -= 1
            i += 1
        patch_content = raw[block_start : i - 1]

        # Extract patch type
        type_m = re.search(r"\btype\s+(\w+)", patch_content)
        patch_type = type_m.group(1) if type_m else ""

        # Find faces ( ... )
        faces_m = re.search(r"\bfaces\s*\(", patch_content)
        if not faces_m:
            continue

        # Walk to matching ) for the faces list
        fi = faces_m.end() - 1  # index of opening (
        fj = fi + 1
        fdepth = 1
        while fj < len(patch_content) and fdepth > 0:
            if patch_content[fj] == "(":
                fdepth += 1
            elif patch_content[fj] == ")":
                fdepth -= 1
            fj += 1
        faces_raw = patch_content[fi + 1 : fj - 1]

        faces: list[list[int]] = []
        for fm in re.finditer(r"\(([^)]+)\)", faces_raw):
            nums = fm.group(1).split()
            if len(nums) >= 3:
                try:
                    faces.append([int(x) for x in nums])
                except ValueError:
                    pass

        result[patch_name] = (patch_type, faces)

    return result


# ── public entry point ────────────────────────────────────────────────────────

def extract_block_mesh_data(root: FoamNode) -> BlockMeshData:
    """Walk a parsed blockMeshDict FoamNode tree and extract geometry data."""
    scale = 1.0
    vertices: list[list[float]] = []
    hex_blocks: list[list[int]] = []
    boundary_faces: dict[str, tuple[str, list[list[int]]]] = {}

    var_map = _build_var_map(root)

    children = root.children
    n_children = len(children)

    for idx, child in enumerate(children):
        name = child.name

        if name in ("scale", "convertToMeters") and isinstance(child.value, (int, float)):
            scale = float(child.value)

        elif name == "vertices" and child.node_type == "raw_list":
            vertices = parse_vertices(_substitute_vars(str(child.value), var_map))

        elif name == "blocks" and child.node_type == "raw_list":
            hex_blocks = _parse_hex_blocks(_substitute_vars(str(child.value), var_map))

        elif name == "boundary" and child.node_type == "boundary_block":
            boundary_faces = _extract_boundary_from_tree(child)

        elif (
            child.node_type == "unknown_raw_entry"
            and str(child.value).strip() == "boundary"
            and idx + 1 < n_children
        ):
            # Fallback: older raw-text path for files that failed structured parsing
            nxt = children[idx + 1]
            if nxt.node_type == "unknown_raw_entry" and str(nxt.value).lstrip().startswith("("):
                boundary_faces = _parse_boundary_block(str(nxt.value))

    # Apply scale factor to vertex coordinates
    if scale != 1.0:
        vertices = [[coord * scale for coord in v] for v in vertices]

    return BlockMeshData(
        vertices=vertices,
        hex_blocks=hex_blocks,
        boundary_faces=boundary_faces,
        scale=scale,
    )
