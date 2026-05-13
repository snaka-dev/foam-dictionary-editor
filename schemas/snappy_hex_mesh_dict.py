# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from schemas._base import (
    ChoiceItem, KeySchema,
    FOUNDATION_V13, OPENCFD_SERIES,
)

TARGET_FILE = "snappyHexMeshDict"

_SWITCH_CHOICES = (
    ChoiceItem("true", "Enable.", supported_in=(FOUNDATION_V13, OPENCFD_SERIES)),
    ChoiceItem("false", "Disable.", supported_in=(FOUNDATION_V13, OPENCFD_SERIES)),
    ChoiceItem("yes", "Alternative enabled switch form.", supported_in=(FOUNDATION_V13,)),
    ChoiceItem("no", "Alternative disabled switch form.", supported_in=(FOUNDATION_V13,)),
)

SCHEMAS: dict[str, KeySchema] = {
    # ── top-level phase toggles ───────────────────────────────────────────────
    "castellatedMesh": KeySchema(
        key="castellatedMesh",
        label="Castellated Mesh",
        description="Enable or disable the castellated (refinement) meshing phase.",
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        choices=_SWITCH_CHOICES,
    ),
    "snap": KeySchema(
        key="snap",
        label="Snap",
        description="Enable or disable the surface snapping phase.",
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        choices=_SWITCH_CHOICES,
    ),
    "addLayers": KeySchema(
        key="addLayers",
        label="Add Layers",
        description="Enable or disable the boundary-layer addition phase.",
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        choices=_SWITCH_CHOICES,
    ),

    # ── castellatedMeshControls ───────────────────────────────────────────────
    "maxLocalCells": KeySchema(
        key="maxLocalCells",
        label="Max Local Cells",
        description=(
            "Maximum number of cells per MPI process during refinement. "
            "Controls memory usage on each core."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "maxGlobalCells": KeySchema(
        key="maxGlobalCells",
        label="Max Global Cells",
        description=(
            "Maximum total number of cells across all MPI processes during refinement. "
            "The run stops refining when this limit is reached."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "minRefinementCells": KeySchema(
        key="minRefinementCells",
        label="Min Refinement Cells",
        description=(
            "Minimum number of cells that must be refined in a given iteration "
            "before snappyHexMesh continues to the next refinement level. "
            "Set to 0 to disable this threshold."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "maxLoadUnbalance": KeySchema(
        key="maxLoadUnbalance",
        label="Max Load Unbalance",
        description=(
            "Maximum allowable imbalance in cell count between MPI processes (fraction, 0–1). "
            "A value of 0.10 allows up to 10 % imbalance before rebalancing."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "nCellsBetweenLevels": KeySchema(
        key="nCellsBetweenLevels",
        label="Cells Between Levels",
        description=(
            "Number of buffer cells between consecutive refinement levels. "
            "Larger values produce smoother level transitions but increase cell count."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "resolveFeatureAngle": KeySchema(
        key="resolveFeatureAngle",
        label="Resolve Feature Angle",
        description=(
            "Surface feature angle (degrees) below which adjacent faces are considered "
            "part of the same feature. Cells near sharper features are automatically refined."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "allowFreeStandingZoneFaces": KeySchema(
        key="allowFreeStandingZoneFaces",
        label="Allow Free-Standing Zone Faces",
        description=(
            "When true, face zones may include faces that do not lie on a cell-zone boundary. "
            "Required for some baffle or interface configurations."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        choices=_SWITCH_CHOICES,
    ),

    # ── snapControls ─────────────────────────────────────────────────────────
    "nSmoothPatch": KeySchema(
        key="nSmoothPatch",
        label="Smooth Patch Iterations",
        description=(
            "Number of patch-normal smoothing iterations applied to boundary points "
            "before the main snapping step."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "nSmoothInternal": KeySchema(
        key="nSmoothInternal",
        label="Smooth Internal Iterations",
        description=(
            "Number of internal smoothing iterations used to move internal points "
            "after boundary points have been snapped."
        ),
        supported_in=(OPENCFD_SERIES,),
        note="Available in OpenCFD releases. May not be present in Foundation v13.",
    ),
    "tolerance": KeySchema(
        key="tolerance",
        label="Snap Tolerance",
        description=(
            "Distance tolerance used during snapping, expressed as a fraction of the local "
            "cell size. A higher value allows points to snap from further away."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "nSolveIter": KeySchema(
        key="nSolveIter",
        label="Solve Iterations",
        description="Number of relaxation (mesh-displacement solver) iterations per snapping step.",
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "nRelaxIter": KeySchema(
        key="nRelaxIter",
        label="Relax Iterations",
        description=(
            "Maximum number of relaxation iterations for the mesh-displacement solver. "
            "Each iteration reduces the displacement to avoid inverted cells."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "nFeatureSnapIter": KeySchema(
        key="nFeatureSnapIter",
        label="Feature Snap Iterations",
        description="Number of iterations used to snap points onto explicit feature edges/points.",
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "implicitFeatureSnap": KeySchema(
        key="implicitFeatureSnap",
        label="Implicit Feature Snap",
        description=(
            "When enabled, snappyHexMesh automatically detects and snaps to surface features "
            "without requiring an explicit eMesh file."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        choices=_SWITCH_CHOICES,
    ),
    "explicitFeatureSnap": KeySchema(
        key="explicitFeatureSnap",
        label="Explicit Feature Snap",
        description=(
            "When enabled, snappyHexMesh snaps to features defined in the eMesh files "
            "listed under geometry."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        choices=_SWITCH_CHOICES,
    ),
    "multiRegionFeatureSnap": KeySchema(
        key="multiRegionFeatureSnap",
        label="Multi-Region Feature Snap",
        description=(
            "When enabled, features at boundaries between multiple geometry regions "
            "are also snapped. Useful for multi-material or coupled-region cases."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        choices=_SWITCH_CHOICES,
    ),

    # ── addLayersControls ─────────────────────────────────────────────────────
    "relativeSizes": KeySchema(
        key="relativeSizes",
        label="Relative Sizes",
        description=(
            "When true, layer thickness parameters (finalLayerThickness, minThickness) are "
            "interpreted as fractions of the adjacent cell size. "
            "When false, they are absolute distances."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        choices=_SWITCH_CHOICES,
    ),
    "expansionRatio": KeySchema(
        key="expansionRatio",
        label="Expansion Ratio",
        description=(
            "Growth ratio between successive layers away from the wall. "
            "Values greater than 1 make outer layers thicker."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "finalLayerThickness": KeySchema(
        key="finalLayerThickness",
        label="Final Layer Thickness",
        description=(
            "Thickness of the layer farthest from the wall, as either a fraction of the "
            "adjacent cell size (relativeSizes true) or an absolute distance."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "minThickness": KeySchema(
        key="minThickness",
        label="Min Thickness",
        description=(
            "Minimum allowable layer thickness. Layers thinner than this are removed. "
            "Interpreted relative or absolute depending on relativeSizes."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "featureAngle": KeySchema(
        key="featureAngle",
        label="Feature Angle",
        description=(
            "Surface angle (degrees) used to identify sharp edges where layer extrusion "
            "should be reduced or stopped to avoid cell quality issues."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "nGrow": KeySchema(
        key="nGrow",
        label="Grow Iterations",
        description=(
            "Number of cell layers of growth applied outward from the layer region "
            "before the final layer extrusion. Can improve stability near complex geometry."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "nLayerIter": KeySchema(
        key="nLayerIter",
        label="Layer Iterations",
        description="Overall number of iterations for the layer-addition algorithm.",
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),

    # ── meshQualityControls ───────────────────────────────────────────────────
    "maxNonOrtho": KeySchema(
        key="maxNonOrtho",
        label="Max Non-Orthogonality",
        description=(
            "Maximum allowable non-orthogonality angle (degrees) for internal faces. "
            "Cells with higher non-orthogonality are removed or not generated."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "maxBoundarySkewness": KeySchema(
        key="maxBoundarySkewness",
        label="Max Boundary Skewness",
        description="Maximum skewness allowed for boundary faces.",
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "maxInternalSkewness": KeySchema(
        key="maxInternalSkewness",
        label="Max Internal Skewness",
        description="Maximum skewness allowed for internal faces.",
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "maxConcave": KeySchema(
        key="maxConcave",
        label="Max Concave",
        description=(
            "Maximum concavity angle (degrees) for cell vertices. "
            "High values indicate strongly concave cells."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "minFlatness": KeySchema(
        key="minFlatness",
        label="Min Flatness",
        description=(
            "Minimum flatness ratio for faces (area of face divided by area of its bounding box). "
            "Faces below this threshold indicate degenerate geometry."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "minVol": KeySchema(
        key="minVol",
        label="Min Volume",
        description=(
            "Minimum allowable cell volume. Cells smaller than this are considered invalid. "
            "A value of 1e-13 is a common default."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "minTetQuality": KeySchema(
        key="minTetQuality",
        label="Min Tet Quality",
        description=(
            "Minimum quality of the tet decomposition used internally for cell checks. "
            "Very negative values (e.g. -1e30) disable the check."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "minArea": KeySchema(
        key="minArea",
        label="Min Area",
        description=(
            "Minimum allowable face area. Faces smaller than this are treated as degenerate. "
            "Set to -1 to disable."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "minTwist": KeySchema(
        key="minTwist",
        label="Min Twist",
        description=(
            "Minimum face twist (cosine of the angle between adjacent face-normal vectors). "
            "A value of 0.02 is a common threshold."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "minDeterminant": KeySchema(
        key="minDeterminant",
        label="Min Determinant",
        description=(
            "Minimum value of the cell determinant (0 to 1). "
            "Values close to 0 indicate severely distorted cells."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "minFaceWeight": KeySchema(
        key="minFaceWeight",
        label="Min Face Weight",
        description=(
            "Minimum face interpolation weight (0 to 0.5). "
            "Low values indicate faces where owner and neighbour cell centres are far from the face."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "minVolRatio": KeySchema(
        key="minVolRatio",
        label="Min Volume Ratio",
        description=(
            "Minimum ratio of volumes between adjacent cells. "
            "A value of 0.01 is a common lower bound."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "minTriangleTwist": KeySchema(
        key="minTriangleTwist",
        label="Min Triangle Twist",
        description=(
            "Minimum twist for triangular faces. "
            "A value of -1 disables the check."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "nSmoothScale": KeySchema(
        key="nSmoothScale",
        label="Smooth Scale Iterations",
        description=(
            "Number of error-scaling smoothing iterations applied to improve mesh quality "
            "after each refinement step."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "errorReduction": KeySchema(
        key="errorReduction",
        label="Error Reduction",
        description=(
            "Fraction by which the displacement of low-quality cells is reduced "
            "during each smoothing iteration (0–1)."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
}
