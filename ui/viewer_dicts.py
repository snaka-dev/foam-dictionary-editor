# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Which 3-D viewer overlay, if any, a given dictionary file feeds.

A case can hold the same dictionary more than once under a non-default name --
`topoSetDict-slices` and `topoSetDict-background` alongside each other, or the
`topoSetDict.1` / `.2` / `.3` form the tutorials use -- and `topoSet -dict <name>`
runs each in turn. Matching on the file name alone means none of them reach the
viewer, which is how a hand-named dictionary came to render as an empty scene.

The identity used here is OpenFOAM's own: the `object` entry of the file's
`FoamFile` header, which names what the dictionary *is* regardless of what it is
called. Measured over both forks' tutorial trees, of 138 files named like one of
the viewer's dictionaries but not exactly so, 118 carry an `object` naming the
base dictionary and 12 more name the variant (`object topoSetDict.1`), which the
prefix test below covers.

The remaining 4 are the reason this does not simply match on the file name:
`blockMeshDict.resolvedBlocks` and its siblings are `#include` *fragments* -- a
bare list of `hex (...)` entries with no enclosing dictionary -- and routing one
to the block-mesh extractor would replace the real blockMeshDict's scene with an
empty one. They carry no `FoamFile` header precisely because they are not
dictionaries, so reading the header both finds the files that should render and
skips the ones that should not.

Two things this deliberately does not do. A file whose header disagrees with its
name is believed, because the header is what OpenFOAM reads. And sampling dicts
are matched by name only: a standalone `sample`/`probes`/`surfaces` file is one
function-object entry with no `FoamFile` header at all, so there is nothing to
read -- a renamed one still needs adding under a known name.
"""
from __future__ import annotations

from pathlib import Path

from foam.nodes import FoamNode
from foam.tree_utils import find_child
from ui.layout_constants import (
    BLOCKMESH_DICT_NAME,
    SAMPLING_DICT_NAMES,
    SETFIELDS_DICT_NAME,
    SNAPPY_HEX_MESH_DICT_NAME,
    TOPOSET_DICT_NAME,
)

# Overlay key -> the dictionary name that feeds it. The keys are what callers
# dispatch on; they are not user-visible.
BLOCK_MESH = "block_mesh"
TOPO_SET = "topo_set"
SNAPPY_HEX_MESH = "snappy_hex_mesh"
SET_FIELDS = "set_fields"
SAMPLING = "sampling"

_BY_DICT_NAME = {
    BLOCKMESH_DICT_NAME: BLOCK_MESH,
    TOPOSET_DICT_NAME: TOPO_SET,
    SNAPPY_HEX_MESH_DICT_NAME: SNAPPY_HEX_MESH,
    SETFIELDS_DICT_NAME: SET_FIELDS,
}


def _declared_object(root: FoamNode | None) -> str:
    """The `object` entry of the file's FoamFile header, or ""."""
    if root is None:
        return ""
    header = find_child(root, "FoamFile")
    if header is None:
        return ""
    obj = find_child(header, "object")
    return "" if obj is None or obj.value is None else str(obj.value).strip().strip('"')


# Every overlay a file can be pinned to, in the order the "Show in 3-D view as" menu
# offers them. "" is the automatic default and is not listed here.
VIEWER_KINDS = (BLOCK_MESH, TOPO_SET, SNAPPY_HEX_MESH, SET_FIELDS, SAMPLING)


def viewer_dict_kind(
    path: str, root: FoamNode | None = None, override: str = ""
) -> str | None:
    """Which overlay *path* feeds, or None if it feeds none.

    *override* is the user's explicit "show this as ..." choice and wins outright: it
    exists for the files neither test below can settle -- a renamed sampling dict, which
    has no header to read -- and for the case where a file's header is simply wrong,
    where the user can see what the file is and the program cannot.

    Otherwise the file name is tried first, so a default-named dictionary costs one dict
    lookup and never depends on having a parsed tree, and only then is the header read.
    """
    if override:
        return override if override in VIEWER_KINDS else None
    name = Path(path).name
    kind = _BY_DICT_NAME.get(name)
    if kind is not None:
        return kind
    if name in SAMPLING_DICT_NAMES:
        return SAMPLING

    declared = _declared_object(root)
    if not declared:
        return SAMPLING if _defines_sampling(root) else None
    kind = _BY_DICT_NAME.get(declared)
    if kind is not None:
        return kind
    # `object topoSetDict.1` -- the variant name rather than the base one. Guarded with a
    # separator test so a longer unrelated name starting with the same letters cannot match.
    for dict_name, overlay in _BY_DICT_NAME.items():
        if declared.startswith(dict_name) and declared[len(dict_name):][:1] in (".", "-", "_"):
            return overlay
    return SAMPLING if _defines_sampling(root) else None


# Function-object types the sampling overlay draws.
_SAMPLING_TYPES = frozenset(
    {"sets", "surfaces", "probes", "patchProbes", "internalProbes", "boundaryProbes"}
)


def _defines_sampling(root: FoamNode | None) -> bool:
    """Whether *root* holds a sampling function object -- the last resort.

    Function-object files go by any name (the OpenCFD tutorials alone use
    ``sampling``, ``cuttingPlane``, ``sampleLines``, ``samplingDebug``…;
    Foundation's ``functions``) and mostly carry no header, so neither test
    above settles them. What they hold does: a ``type sets;`` (``surfaces``,
    ``probes``…) at the top level, in a top-level dictionary, or in
    ``functions``. Only those two levels are looked at, and only sampling
    types count, so a snappyHexMeshDict's ``type triSurfaceMesh`` deep in
    ``geometry`` cannot pass.
    """
    if root is None:
        return False

    def typed(node: FoamNode) -> bool:
        return any(
            c.name == "type" and str(c.value) in _SAMPLING_TYPES for c in node.children
        )

    if typed(root):
        return True
    for child in root.children:
        if child.node_type != "dictionary" or child.name == "FoamFile":
            continue
        if typed(child):
            return True
        if child.name == "functions" and any(
            g.node_type == "dictionary" and typed(g) for g in child.children
        ):
            return True
    return False
