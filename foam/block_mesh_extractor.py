# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import re
from dataclasses import dataclass, field

from foam.nodes import FoamNode
from foam.var_resolver import build_var_map, eval_foam_expr, substitute_vars

_EVAL_VALUE_RE = re.compile(r'^#eval\s*\{\s*([^}]+)\}')  # still used by parse_vertices


@dataclass
class BlockMeshData:
    vertices: list[list[float]]
    hex_blocks: list[list[int]]
    # patch_name → (patch_type, list_of_face_vertex_lists)
    boundary_faces: dict[str, tuple[str, list[list[int]]]] = field(default_factory=dict)
    # Exterior block faces not claimed by any boundary patch — blockMesh's
    # implicit defaultFaces patch (type "empty" unless defaultPatch overrides).
    default_faces: list[list[int]] = field(default_factory=list)
    scale: float = 1.0


# ── variable resolution ───────────────────────────────────────────────────────

_BLOCKMESH_STRUCTURAL = frozenset({
    "scale", "convertToMeters", "vertices", "blocks",
    "edges", "boundary", "mergePatchPairs", "defaultPatch",
})


def _eval_foam_expr(expr: str) -> str | None:
    return eval_foam_expr(expr)


def _build_var_map(root: FoamNode) -> dict[str, str]:
    return build_var_map(root, skip_keys=_BLOCKMESH_STRUCTURAL)


def _substitute_vars(text: str, var_map: dict[str, str]) -> str:
    return substitute_vars(text, var_map)


# ── hex face index table ─────────────────────────────────────────────────────
# Local vertex indices (0-7 within a hex block) for each of the 6 block faces.
# Matches OpenFOAM's blockMesh convention: face 0 = -x, 1 = +x, 2 = -y,
# 3 = +y, 4 = -z, 5 = +z.
_HEX_FACE_VERTICES: list[list[int]] = [
    [0, 4, 7, 3],  # 0: -x
    [1, 2, 6, 5],  # 1: +x
    [0, 1, 5, 4],  # 2: -y
    [2, 3, 7, 6],  # 3: +y
    [0, 3, 2, 1],  # 4: -z
    [4, 5, 6, 7],  # 5: +z
]


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


def _expand_compact_faces(
    boundary_faces: dict[str, tuple[str, list[list[int]]]],
    hex_blocks: list[list[int]],
) -> dict[str, tuple[str, list[list[int]]]]:
    """Convert (blockIndex, faceIndex) compact entries to 4-vertex lists.

    Old-style 4-vertex entries are passed through unchanged.
    """
    expanded: dict[str, tuple[str, list[list[int]]]] = {}
    for patch_name, (patch_type, faces) in boundary_faces.items():
        new_faces: list[list[int]] = []
        for f in faces:
            if len(f) == 4:
                new_faces.append(f)
            elif len(f) == 2:
                block_idx, face_idx = f
                if 0 <= block_idx < len(hex_blocks) and 0 <= face_idx < 6:
                    block = hex_blocks[block_idx]
                    new_faces.append([block[i] for i in _HEX_FACE_VERTICES[face_idx]])
        expanded[patch_name] = (patch_type, new_faces)
    return expanded


def _compute_default_faces(
    hex_blocks: list[list[int]],
    boundary_faces: dict[str, tuple[str, list[list[int]]]],
) -> list[list[int]]:
    """Return exterior block faces not claimed by any boundary patch.

    blockMesh collects these into its implicit defaultFaces patch. Quasi-2-D
    cases (e.g. damBreak) leave their large front/back faces unlisted in
    boundary, so without this the 3-D viewer draws no visible boundary at all.
    Expects boundary_faces already expanded to 4-vertex form. A face shared by
    two blocks is interior; fully collapsed faces (degenerate blocks) are
    skipped.
    """
    seen: dict[frozenset[int], tuple[list[int], int]] = {}
    for block in hex_blocks:
        for local in _HEX_FACE_VERTICES:
            face = [block[i] for i in local]
            key = frozenset(face)
            if len(key) < 3:
                continue
            prev = seen.get(key)
            seen[key] = (face, (prev[1] + 1) if prev else 1)
    claimed = {
        frozenset(f)
        for _patch_type, faces in boundary_faces.values()
        for f in faces
    }
    return [face for key, (face, n) in seen.items() if n == 1 and key not in claimed]


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
                    if len(nums) in (2, 4):
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
            if len(nums) in (2, 4):
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

        elif name == "blocks" and child.node_type == "block_list":
            for entry in child.children:
                hex_blocks.extend(
                    _parse_hex_blocks(_substitute_vars(str(entry.value), var_map))
                )

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

    # Expand compact (blockIndex, faceIndex) notation to 4-vertex lists
    boundary_faces = _expand_compact_faces(boundary_faces, hex_blocks)

    default_faces = _compute_default_faces(hex_blocks, boundary_faces)

    # Apply scale factor to vertex coordinates
    if scale != 1.0:
        vertices = [[coord * scale for coord in v] for v in vertices]

    return BlockMeshData(
        vertices=vertices,
        hex_blocks=hex_blocks,
        boundary_faces=boundary_faces,
        default_faces=default_faces,
        scale=scale,
    )
