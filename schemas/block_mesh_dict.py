# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Schema for `system/blockMeshDict`.

Keys and values follow `src/mesh/blockMesh/blockMesh/` — in particular the
`mergeStrategy` Enum at `blockMesh.C:46-47` and the `scale` /
`convertToMeters` compatibility entry at `blockMesh.C:196-206`.
"""
from __future__ import annotations

from schemas._base import (
    FOUNDATION_SERIES,
    OPENCFD_SERIES,
    ChoiceItem,
    KeySchema,
)

TARGET_FILE = "blockMeshDict"

_BOTH = (FOUNDATION_SERIES, OPENCFD_SERIES)

_PATCH_TYPE_CHOICES = (
    ChoiceItem("patch", "Generic boundary; the base type for inlets and outlets.", _BOTH),
    ChoiceItem("wall", "Solid wall. Turbulence wall functions require this type.", _BOTH),
    ChoiceItem("empty", "Excluded direction, for 1-D and 2-D cases.", _BOTH),
    ChoiceItem("symmetryPlane", "Planar symmetry.", _BOTH),
    ChoiceItem("symmetry", "Symmetry for a non-planar patch.", _BOTH),
    ChoiceItem("cyclic", "Periodic pair; needs a neighbourPatch entry.", _BOTH),
    ChoiceItem("cyclicAMI", "Periodic pair with non-conforming faces.", _BOTH),
    ChoiceItem("wedge", "Axisymmetric wedge, used with a 5-degree sector.", _BOTH),
    ChoiceItem("processor", "Inter-processor boundary; created by decomposePar.", _BOTH),
)


def _entry(key: str, label: str, description: str,
           choices: tuple[ChoiceItem, ...] = ()) -> KeySchema:
    return KeySchema(
        key=key, label=label, description=description,
        supported_in=_BOTH, choices=choices,
    )


SCHEMAS: dict[str, KeySchema] = {
    # ── scaling ───────────────────────────────────────────────────────────────
    "scale": _entry(
        "scale", "Scale",
        "Factor applied to every vertex coordinate. 0.001 means the vertices are "
        "written in millimetres.",
    ),
    "convertToMeters": KeySchema(
        key="convertToMeters", label="Convert To Meters",
        description="Historical name for 'scale', with the same meaning: a factor "
                    "applied to every vertex coordinate.",
        supported_in=(OPENCFD_SERIES,),
        status="renamed",
        use_instead="scale",
        deprecated_since="v1012",
        note="Renamed in OCT-2008 (blockMesh.C:196). Still accepted as a "
             "compatibility entry, but no tutorial shipped with v2606 uses it.",
    ),

    # ── topology ──────────────────────────────────────────────────────────────
    "vertices": _entry(
        "vertices", "Vertices",
        "The list of points the blocks are built from, indexed from 0 in the "
        "order written here.",
    ),
    "blocks": _entry(
        "blocks", "Blocks",
        "Hexahedral blocks, each written as hex (v0 v1 ... v7), a cell count, "
        "and a grading. Vertex order defines the block's local axes.",
    ),
    "edges": _entry(
        "edges", "Edges",
        "Non-straight edges between vertices — arc, spline, polyLine, line. Any "
        "edge not listed is straight.",
    ),
    "boundary": _entry(
        "boundary", "Boundary",
        "Named boundary patches, each a sub-dictionary with a type and a face "
        "list. Faces not listed fall into defaultFaces.",
    ),
    "patches": KeySchema(
        key="patches", label="Patches",
        description="Older, list-based form of the boundary definition, written "
                    "as type/name/faces triplets rather than named dictionaries.",
        supported_in=_BOTH,
        note="Superseded by 'boundary' in OpenFOAM 2.3. Still read, and still "
             "present in some shipped tutorials.",
    ),
    "boundary.*": _entry(
        "*", "boundary/<patch>",
        "One boundary patch. The entry name becomes the patch name.",
    ),
    "boundary.type": _entry(
        "type", "Patch Type",
        "Geometric type of this patch, which decides what boundary conditions "
        "the fields may use.",
        _PATCH_TYPE_CHOICES,
    ),
    "boundary.faces": _entry(
        "faces", "Faces",
        "Faces making up this patch, each a list of four vertex indices.",
    ),
    "boundary.neighbourPatch": _entry(
        "neighbourPatch", "Neighbour Patch",
        "The other half of a cyclic pair.",
    ),
    "boundary.inGroups": _entry(
        "inGroups", "In Groups",
        "Patch groups this patch joins, so boundary conditions can address them "
        "collectively.",
    ),
    "boundary.transform": _entry(
        "transform", "Transform",
        "How a cyclic pair maps onto its neighbour.",
        (
            ChoiceItem("translational", "Neighbour is a translation of this patch.", _BOTH),
            ChoiceItem("rotational", "Neighbour is a rotation of this patch.", _BOTH),
            ChoiceItem("noOrdering", "No implied ordering.", _BOTH),
            ChoiceItem("unknown", "Determined automatically.", _BOTH),
        ),
    ),
    "boundary.separationVector": _entry("separationVector", "Separation Vector",
        "Offset between the two halves of a translational cyclic pair."),
    "boundary.rotationAxis": _entry("rotationAxis", "Rotation Axis",
        "Axis of a rotational cyclic pair."),
    "boundary.rotationCentre": _entry("rotationCentre", "Rotation Centre",
        "Centre of rotation of a rotational cyclic pair."),

    # ── merging ───────────────────────────────────────────────────────────────
    "mergePatchPairs": _entry(
        "mergePatchPairs", "Merge Patch Pairs",
        "Pairs of patches fused into internal faces, joining blocks whose faces "
        "do not match one-to-one.",
    ),
    "mergeType": _entry(
        "mergeType", "Merge Type",
        "How coincident block faces are connected.",
        (
            ChoiceItem("topology", "Connect using the block topology. The default.", _BOTH),
            ChoiceItem("points", "Connect by matching point geometry, for blocks "
                                 "whose topology does not line up.", _BOTH),
        ),
    ),

    # ── remaining ─────────────────────────────────────────────────────────────
    "defaultPatch": _entry(
        "defaultPatch", "Default Patch",
        "Name and type given to boundary faces not claimed by any patch. Without "
        "it they become a patch called defaultFaces of type empty.",
    ),
    "defaultPatch.name": _entry("name", "Default Patch Name",
        "Name for the unclaimed boundary faces."),
    "defaultPatch.type": _entry("type", "Default Patch Type",
        "Type for the unclaimed boundary faces.", _PATCH_TYPE_CHOICES),
    "geometry": _entry(
        "geometry", "Geometry",
        "Searchable surfaces that projected vertices, edges and faces snap to.",
    ),
    "verbose": _entry(
        "verbose", "Verbose",
        "Prints extra detail while the mesh is generated.",
        (
            ChoiceItem("true", "Enabled.", _BOTH),
            ChoiceItem("false", "Disabled.", _BOTH),
            ChoiceItem("yes", "Enabled.", _BOTH),
            ChoiceItem("no", "Disabled.", _BOTH),
            ChoiceItem("on", "Enabled.", _BOTH),
            ChoiceItem("off", "Disabled.", _BOTH),
        ),
    ),
    "fastMerge": _entry(
        "fastMerge", "Fast Merge",
        "Speeds up point merging on large meshes.",
    ),
}
