# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from schemas._base import FOUNDATION_SERIES, OPENCFD_SERIES, KeySchema

from ._common import SWITCH_CHOICES

SCHEMAS: dict[str, KeySchema] = {
    # ── snapControls ─────────────────────────────────────────────────────────
    "snapControls.nSmoothPatch": KeySchema(
        key="nSmoothPatch",
        label="Smooth Patch Iterations",
        description=(
            "Number of patch-normal smoothing iterations applied to boundary points "
            "before the main snapping step."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),
    "snapControls.nSmoothInternal": KeySchema(
        key="nSmoothInternal",
        label="Smooth Internal Iterations",
        description=(
            "Number of internal smoothing iterations used to move internal points "
            "after boundary points have been snapped."
        ),
        supported_in=(OPENCFD_SERIES,),
        note="Available in OpenCFD releases. May not be present in Foundation v13.",
    ),
    "snapControls.tolerance": KeySchema(
        key="tolerance",
        label="Snap Tolerance",
        description=(
            "Distance tolerance used during snapping, expressed as a fraction of the local "
            "cell size. A higher value allows points to snap from further away."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),
    "snapControls.nSolveIter": KeySchema(
        key="nSolveIter",
        label="Solve Iterations",
        description="Number of relaxation (mesh-displacement solver) iterations per snapping step.",
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),
    "snapControls.nRelaxIter": KeySchema(
        key="nRelaxIter",
        label="Relax Iterations (Snap)",
        description=(
            "Maximum number of relaxation iterations for the mesh-displacement solver "
            "during the snapping phase. Each iteration reduces the displacement to avoid "
            "inverted cells."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),
    "snapControls.nFeatureSnapIter": KeySchema(
        key="nFeatureSnapIter",
        label="Feature Snap Iterations",
        description="Number of iterations used to snap points onto explicit feature edges/points.",
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),
    "snapControls.implicitFeatureSnap": KeySchema(
        key="implicitFeatureSnap",
        label="Implicit Feature Snap",
        description=(
            "When enabled, snappyHexMesh automatically detects and snaps to surface features "
            "without requiring an explicit eMesh file."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
        choices=SWITCH_CHOICES,
    ),
    "snapControls.explicitFeatureSnap": KeySchema(
        key="explicitFeatureSnap",
        label="Explicit Feature Snap",
        description=(
            "When enabled, snappyHexMesh snaps to features defined in the eMesh files "
            "listed under geometry."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
        choices=SWITCH_CHOICES,
    ),
    "snapControls.multiRegionFeatureSnap": KeySchema(
        key="multiRegionFeatureSnap",
        label="Multi-Region Feature Snap",
        description=(
            "When enabled, features at boundaries between multiple geometry regions "
            "are also snapped. Useful for multi-material or coupled-region cases."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
        choices=SWITCH_CHOICES,
    ),
    "snapControls.detectNearSurfacesSnap": KeySchema(
        key="detectNearSurfacesSnap",
        label="Detect Near Surfaces Snap",
        description=(
            "When enabled, snapping avoids moving points through nearby surfaces, "
            "reducing the risk of inverted cells in thin-feature regions."
        ),
        supported_in=(OPENCFD_SERIES,),
        note="Available in OpenCFD releases. Not present in Foundation v13.",
        choices=SWITCH_CHOICES,
    ),

}
