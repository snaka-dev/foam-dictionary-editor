# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from schemas._base import FOUNDATION_SERIES, OPENCFD_SERIES, ChoiceItem, KeySchema

from ._common import SWITCH_CHOICES

SCHEMAS: dict[str, KeySchema] = {
    # ── castellatedMeshControls ───────────────────────────────────────────────
    "castellatedMeshControls.maxLocalCells": KeySchema(
        key="maxLocalCells",
        label="Max Local Cells",
        description=(
            "Maximum number of cells per MPI process during refinement. "
            "Controls memory usage on each core."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),
    "castellatedMeshControls.maxGlobalCells": KeySchema(
        key="maxGlobalCells",
        label="Max Global Cells",
        description=(
            "Maximum total number of cells across all MPI processes during refinement. "
            "The run stops refining when this limit is reached."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),
    "castellatedMeshControls.minRefinementCells": KeySchema(
        key="minRefinementCells",
        label="Min Refinement Cells",
        description=(
            "Minimum number of cells that must be refined in a given iteration "
            "before snappyHexMesh continues to the next refinement level. "
            "Set to 0 to disable this threshold."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),
    "castellatedMeshControls.maxLoadUnbalance": KeySchema(
        key="maxLoadUnbalance",
        label="Max Load Unbalance",
        description=(
            "Maximum allowable imbalance in cell count between MPI processes (fraction, 0–1). "
            "A value of 0.10 allows up to 10 % imbalance before rebalancing."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),
    "castellatedMeshControls.nCellsBetweenLevels": KeySchema(
        key="nCellsBetweenLevels",
        label="Cells Between Levels",
        description=(
            "Number of buffer cells between consecutive refinement levels. "
            "Larger values produce smoother level transitions but increase cell count."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),
    "castellatedMeshControls.resolveFeatureAngle": KeySchema(
        key="resolveFeatureAngle",
        label="Resolve Feature Angle",
        description=(
            "Surface feature angle (degrees) below which adjacent faces are considered "
            "part of the same feature. Cells near sharper features are automatically refined."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),
    "castellatedMeshControls.planarAngle": KeySchema(
        key="planarAngle",
        label="Planar Angle",
        description=(
            "Angle (degrees) below which two surface triangles are considered coplanar "
            "and their shared edge is not treated as a feature edge. "
            "Reducing this value preserves more sharp edges."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),
    "castellatedMeshControls.allowFreeStandingZoneFaces": KeySchema(
        key="allowFreeStandingZoneFaces",
        label="Allow Free-Standing Zone Faces",
        description=(
            "When true, face zones may include faces that do not lie on a cell-zone boundary. "
            "Required for some baffle or interface configurations."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
        choices=SWITCH_CHOICES,
    ),
    "castellatedMeshControls.locationInMesh": KeySchema(
        key="locationInMesh",
        label="Location In Mesh",
        description=(
            "A point (x y z) that lies inside the region to be kept after castellated meshing. "
            "snappyHexMesh retains the connected cell region containing this point."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),

    # ── refinementSurfaces entries (grandparent = "refinementSurfaces") ────────
    # These keys live inside a named surface entry, e.g.:
    #   refinementSurfaces { motorBike { level (5 6); ... } }
    # parent_key = user-defined surface name → no fixed match
    # grandparent_key = "refinementSurfaces"  → matched here
    "refinementSurfaces.level": KeySchema(
        key="level",
        label="Refinement Level (Surface)",
        description=(
            "Minimum and maximum refinement levels applied to cells near this surface, "
            "given as (min max). Cells cut by the surface are refined to at least the "
            "minimum level; those near features may reach the maximum level."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),
    "refinementSurfaces.faceZone": KeySchema(
        key="faceZone",
        label="Face Zone",
        description=(
            "Name of the face zone created from faces on this surface. "
            "Required when the surface is used as an internal baffle or interface."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),
    "refinementSurfaces.cellZone": KeySchema(
        key="cellZone",
        label="Cell Zone",
        description=(
            "Name of the cell zone created from cells on the inside of this surface. "
            "Used together with faceZone to define multi-region or porous-zone boundaries."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),
    "refinementSurfaces.cellZoneInside": KeySchema(
        key="cellZoneInside",
        label="Cell Zone Inside",
        description=(
            "Controls which side of the surface is marked as belonging to the cell zone."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
        choices=(
            ChoiceItem(
                "inside",
                "Cells geometrically inside the closed surface are added to the cell zone.",
                supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "outside",
                "Cells geometrically outside the closed surface are added to the cell zone.",
                supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "insidePoint",
                "Cells in the connected region containing the insidePoint are added.",
                supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
            ),
        ),
    ),
    "refinementSurfaces.faceType": KeySchema(
        key="faceType",
        label="Face Type",
        description=(
            "Topology of the faces placed on this surface in the final mesh."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
        choices=(
            ChoiceItem(
                "internal",
                "Faces are internal mesh faces shared by two cells. "
                "Used for internal interfaces without a physical gap.",
                supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "baffle",
                "Faces form a zero-thickness baffle: two boundary faces occupying the same "
                "geometric position, each owned by a different cell.",
                supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "boundary",
                "Faces become ordinary boundary faces on a single patch.",
                supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
            ),
        ),
    ),

    # ── refinementRegions entries (grandparent = "refinementRegions") ──────────
    # These keys live inside a named region entry, e.g.:
    #   refinementRegions { sphere1 { mode inside; levels ((1e15 4)); } }
    # grandparent_key = "refinementRegions"
    "refinementRegions.mode": KeySchema(
        key="mode",
        label="Refinement Mode",
        description=(
            "Determines how refinement levels are applied relative to this region."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
        choices=(
            ChoiceItem(
                "inside",
                "Cells whose centres lie inside the region are refined to the specified level.",
                supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "outside",
                "Cells whose centres lie outside the region are refined to the specified level.",
                supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "distance",
                "Cells within a given distance from the surface are refined; "
                "levels is a list of (distance level) pairs applied from closest to furthest.",
                supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
            ),
        ),
    ),
    "refinementRegions.levels": KeySchema(
        key="levels",
        label="Refinement Levels",
        description=(
            "List of (distance level) pairs used when mode is 'distance'. "
            "Each pair specifies that cells within 'distance' of the surface are refined "
            "to at least 'level'. Pairs are evaluated from smallest distance outward, "
            "e.g. ((1e-3 5)(5e-3 3))."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),

}
