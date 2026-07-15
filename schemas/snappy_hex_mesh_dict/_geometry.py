# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from schemas._base import FOUNDATION_V13, OPENCFD_SERIES, ChoiceItem, KeySchema

from ._common import SWITCH_CHOICES

SCHEMAS: dict[str, KeySchema] = {
    # ── top-level ─────────────────────────────────────────────────────────────
    "castellatedMesh": KeySchema(
        key="castellatedMesh",
        label="Castellated Mesh",
        description="Enable or disable the castellated (refinement) meshing phase.",
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        choices=SWITCH_CHOICES,
    ),
    "snap": KeySchema(
        key="snap",
        label="Snap",
        description="Enable or disable the surface snapping phase.",
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        choices=SWITCH_CHOICES,
    ),
    "addLayers": KeySchema(
        key="addLayers",
        label="Add Layers",
        description="Enable or disable the boundary-layer addition phase.",
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        choices=SWITCH_CHOICES,
    ),
    "mergeTolerance": KeySchema(
        key="mergeTolerance",
        label="Merge Tolerance",
        description=(
            "Point-merge tolerance used at the final mesh-assembly step, expressed as a "
            "fraction of the bounding-box diagonal. A value of 1e-6 is a typical default."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "debug": KeySchema(
        key="debug",
        label="Debug",
        description=(
            "Bitmask controlling diagnostic output written during the run. "
            "0 disables all extra output; higher values enable progressively more detail. "
            "Common bits: 1 = write intermediate surfaces, 4 = write refinement levels."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),

    # ── patchInfo sub-dict ────────────────────────────────────────────────────
    # patchInfo appears inside refinementSurfaces entries to assign a patch type.
    "patchInfo.type": KeySchema(
        key="type",
        label="Patch Type",
        description=(
            "OpenFOAM patch type assigned to faces on this refinement surface. "
            "Determines boundary condition behaviour and coupling for the generated patch."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        choices=(
            ChoiceItem(
                "wall",
                "Solid wall patch. Used for no-slip or slip velocity conditions.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "patch",
                "Generic patch with no special geometric or topological constraints.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "symmetry",
                "Symmetry plane patch. Enforces mirror-symmetric flow.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "symmetryPlane",
                "Flat symmetry-plane patch (stricter planarity requirement than symmetry).",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "empty",
                "Used on the front/back faces of 2-D or axisymmetric cases.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "wedge",
                "Wedge patch for axisymmetric cases (paired with empty on front/back).",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "cyclic",
                "Periodic (cyclic) patch matched with an opposite cyclic patch.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "processor",
                "Processor inter-domain boundary created automatically during decomposition.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
        ),
    ),
}
