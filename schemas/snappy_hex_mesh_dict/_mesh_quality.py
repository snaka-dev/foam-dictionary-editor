# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from schemas._base import FOUNDATION_V13, OPENCFD_SERIES, KeySchema

SCHEMAS: dict[str, KeySchema] = {
    # ── meshQualityControls ───────────────────────────────────────────────────
    "meshQualityControls.maxNonOrtho": KeySchema(
        key="maxNonOrtho",
        label="Max Non-Orthogonality",
        description=(
            "Maximum allowable non-orthogonality angle (degrees) for internal faces. "
            "Cells with higher non-orthogonality are removed or not generated."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "meshQualityControls.maxBoundarySkewness": KeySchema(
        key="maxBoundarySkewness",
        label="Max Boundary Skewness",
        description="Maximum skewness allowed for boundary faces.",
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "meshQualityControls.maxInternalSkewness": KeySchema(
        key="maxInternalSkewness",
        label="Max Internal Skewness",
        description="Maximum skewness allowed for internal faces.",
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "meshQualityControls.maxConcave": KeySchema(
        key="maxConcave",
        label="Max Concave",
        description=(
            "Maximum concavity angle (degrees) for cell vertices. "
            "High values indicate strongly concave cells."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "meshQualityControls.minFlatness": KeySchema(
        key="minFlatness",
        label="Min Flatness",
        description=(
            "Minimum flatness ratio for faces (area of face divided by area of its bounding box). "
            "Faces below this threshold indicate degenerate geometry."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "meshQualityControls.minVol": KeySchema(
        key="minVol",
        label="Min Volume",
        description=(
            "Minimum allowable cell volume. Cells smaller than this are considered invalid. "
            "A value of 1e-13 is a common default."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "meshQualityControls.minTetQuality": KeySchema(
        key="minTetQuality",
        label="Min Tet Quality",
        description=(
            "Minimum quality of the tet decomposition used internally for cell checks. "
            "Very negative values (e.g. -1e30) disable the check."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "meshQualityControls.minArea": KeySchema(
        key="minArea",
        label="Min Area",
        description=(
            "Minimum allowable face area. Faces smaller than this are treated as degenerate. "
            "Set to -1 to disable."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "meshQualityControls.minTwist": KeySchema(
        key="minTwist",
        label="Min Twist",
        description=(
            "Minimum face twist (cosine of the angle between adjacent face-normal vectors). "
            "A value of 0.02 is a common threshold."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "meshQualityControls.minDeterminant": KeySchema(
        key="minDeterminant",
        label="Min Determinant",
        description=(
            "Minimum value of the cell determinant (0 to 1). "
            "Values close to 0 indicate severely distorted cells."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "meshQualityControls.minFaceWeight": KeySchema(
        key="minFaceWeight",
        label="Min Face Weight",
        description=(
            "Minimum face interpolation weight (0 to 0.5). "
            "Low values indicate faces where owner and neighbour cell centres are far from the face."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "meshQualityControls.minVolRatio": KeySchema(
        key="minVolRatio",
        label="Min Volume Ratio",
        description=(
            "Minimum ratio of volumes between adjacent cells. "
            "A value of 0.01 is a common lower bound."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "meshQualityControls.minTriangleTwist": KeySchema(
        key="minTriangleTwist",
        label="Min Triangle Twist",
        description=(
            "Minimum twist for triangular faces. "
            "A value of -1 disables the check."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "meshQualityControls.nSmoothScale": KeySchema(
        key="nSmoothScale",
        label="Smooth Scale Iterations",
        description=(
            "Number of error-scaling smoothing iterations applied to improve mesh quality "
            "after each refinement step."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "meshQualityControls.errorReduction": KeySchema(
        key="errorReduction",
        label="Error Reduction",
        description=(
            "Fraction by which the displacement of low-quality cells is reduced "
            "during each smoothing iteration (0–1)."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),

    # ── meshQualityControls.relaxed ───────────────────────────────────────────
    # These mirror the meshQualityControls keys but with looser thresholds
    # applied once addLayersControls.nRelaxedIter is reached.
    "relaxed.maxNonOrtho": KeySchema(
        key="maxNonOrtho",
        label="Max Non-Orthogonality (Relaxed)",
        description=(
            "Relaxed non-orthogonality limit (degrees) used during the final layer-addition "
            "iterations (see addLayersControls.nRelaxedIter). Typically set higher than the "
            "standard meshQualityControls value to allow the solver to escape local minima."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "relaxed.maxBoundarySkewness": KeySchema(
        key="maxBoundarySkewness",
        label="Max Boundary Skewness (Relaxed)",
        description=(
            "Relaxed boundary-face skewness limit used during the final layer-addition "
            "iterations. Typically set higher than the standard limit."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "relaxed.maxInternalSkewness": KeySchema(
        key="maxInternalSkewness",
        label="Max Internal Skewness (Relaxed)",
        description=(
            "Relaxed internal-face skewness limit used during the final layer-addition "
            "iterations. Typically set higher than the standard limit."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "relaxed.minTwist": KeySchema(
        key="minTwist",
        label="Min Twist (Relaxed)",
        description=(
            "Relaxed minimum face-twist threshold used during the final layer-addition "
            "iterations. Typically set lower (more permissive) than the standard value."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),

}
