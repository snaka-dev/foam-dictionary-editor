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
    # ── top-level ─────────────────────────────────────────────────────────────
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

    # ── castellatedMeshControls ───────────────────────────────────────────────
    "castellatedMeshControls.maxLocalCells": KeySchema(
        key="maxLocalCells",
        label="Max Local Cells",
        description=(
            "Maximum number of cells per MPI process during refinement. "
            "Controls memory usage on each core."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "castellatedMeshControls.maxGlobalCells": KeySchema(
        key="maxGlobalCells",
        label="Max Global Cells",
        description=(
            "Maximum total number of cells across all MPI processes during refinement. "
            "The run stops refining when this limit is reached."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "castellatedMeshControls.minRefinementCells": KeySchema(
        key="minRefinementCells",
        label="Min Refinement Cells",
        description=(
            "Minimum number of cells that must be refined in a given iteration "
            "before snappyHexMesh continues to the next refinement level. "
            "Set to 0 to disable this threshold."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "castellatedMeshControls.maxLoadUnbalance": KeySchema(
        key="maxLoadUnbalance",
        label="Max Load Unbalance",
        description=(
            "Maximum allowable imbalance in cell count between MPI processes (fraction, 0–1). "
            "A value of 0.10 allows up to 10 % imbalance before rebalancing."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "castellatedMeshControls.nCellsBetweenLevels": KeySchema(
        key="nCellsBetweenLevels",
        label="Cells Between Levels",
        description=(
            "Number of buffer cells between consecutive refinement levels. "
            "Larger values produce smoother level transitions but increase cell count."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "castellatedMeshControls.resolveFeatureAngle": KeySchema(
        key="resolveFeatureAngle",
        label="Resolve Feature Angle",
        description=(
            "Surface feature angle (degrees) below which adjacent faces are considered "
            "part of the same feature. Cells near sharper features are automatically refined."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "castellatedMeshControls.planarAngle": KeySchema(
        key="planarAngle",
        label="Planar Angle",
        description=(
            "Angle (degrees) below which two surface triangles are considered coplanar "
            "and their shared edge is not treated as a feature edge. "
            "Reducing this value preserves more sharp edges."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "castellatedMeshControls.allowFreeStandingZoneFaces": KeySchema(
        key="allowFreeStandingZoneFaces",
        label="Allow Free-Standing Zone Faces",
        description=(
            "When true, face zones may include faces that do not lie on a cell-zone boundary. "
            "Required for some baffle or interface configurations."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        choices=_SWITCH_CHOICES,
    ),
    "castellatedMeshControls.locationInMesh": KeySchema(
        key="locationInMesh",
        label="Location In Mesh",
        description=(
            "A point (x y z) that lies inside the region to be kept after castellated meshing. "
            "snappyHexMesh retains the connected cell region containing this point."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),

    # ── snapControls ─────────────────────────────────────────────────────────
    "snapControls.nSmoothPatch": KeySchema(
        key="nSmoothPatch",
        label="Smooth Patch Iterations",
        description=(
            "Number of patch-normal smoothing iterations applied to boundary points "
            "before the main snapping step."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
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
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "snapControls.nSolveIter": KeySchema(
        key="nSolveIter",
        label="Solve Iterations",
        description="Number of relaxation (mesh-displacement solver) iterations per snapping step.",
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "snapControls.nRelaxIter": KeySchema(
        key="nRelaxIter",
        label="Relax Iterations (Snap)",
        description=(
            "Maximum number of relaxation iterations for the mesh-displacement solver "
            "during the snapping phase. Each iteration reduces the displacement to avoid "
            "inverted cells."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "snapControls.nFeatureSnapIter": KeySchema(
        key="nFeatureSnapIter",
        label="Feature Snap Iterations",
        description="Number of iterations used to snap points onto explicit feature edges/points.",
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "snapControls.implicitFeatureSnap": KeySchema(
        key="implicitFeatureSnap",
        label="Implicit Feature Snap",
        description=(
            "When enabled, snappyHexMesh automatically detects and snaps to surface features "
            "without requiring an explicit eMesh file."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        choices=_SWITCH_CHOICES,
    ),
    "snapControls.explicitFeatureSnap": KeySchema(
        key="explicitFeatureSnap",
        label="Explicit Feature Snap",
        description=(
            "When enabled, snappyHexMesh snaps to features defined in the eMesh files "
            "listed under geometry."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        choices=_SWITCH_CHOICES,
    ),
    "snapControls.multiRegionFeatureSnap": KeySchema(
        key="multiRegionFeatureSnap",
        label="Multi-Region Feature Snap",
        description=(
            "When enabled, features at boundaries between multiple geometry regions "
            "are also snapped. Useful for multi-material or coupled-region cases."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        choices=_SWITCH_CHOICES,
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
        choices=_SWITCH_CHOICES,
    ),

    # ── addLayersControls ─────────────────────────────────────────────────────
    "addLayersControls.relativeSizes": KeySchema(
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
    "addLayersControls.expansionRatio": KeySchema(
        key="expansionRatio",
        label="Expansion Ratio",
        description=(
            "Growth ratio between successive layers away from the wall. "
            "Values greater than 1 make outer layers thicker."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "addLayersControls.finalLayerThickness": KeySchema(
        key="finalLayerThickness",
        label="Final Layer Thickness",
        description=(
            "Thickness of the layer farthest from the wall, as either a fraction of the "
            "adjacent cell size (relativeSizes true) or an absolute distance."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "addLayersControls.minThickness": KeySchema(
        key="minThickness",
        label="Min Thickness",
        description=(
            "Minimum allowable layer thickness. Layers thinner than this are removed. "
            "Interpreted relative or absolute depending on relativeSizes."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "addLayersControls.featureAngle": KeySchema(
        key="featureAngle",
        label="Feature Angle (Layers)",
        description=(
            "Surface angle (degrees) used to identify sharp edges where layer extrusion "
            "should be reduced or stopped to avoid cell quality issues."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "addLayersControls.slipFeatureAngle": KeySchema(
        key="slipFeatureAngle",
        label="Slip Feature Angle",
        description=(
            "Angle (degrees) below which layer points near feature edges are allowed to "
            "slip along the edge rather than being fully constrained. "
            "Helps avoid collapsed layers on convex edges."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "addLayersControls.nGrow": KeySchema(
        key="nGrow",
        label="Grow Iterations",
        description=(
            "Number of cell layers of growth applied outward from the layer region "
            "before the final layer extrusion. Can improve stability near complex geometry."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "addLayersControls.nSmoothSurfaceNormals": KeySchema(
        key="nSmoothSurfaceNormals",
        label="Smooth Surface Normals",
        description=(
            "Number of smoothing iterations for the surface normals used to determine "
            "the layer extrusion direction. More iterations produce a smoother normal field."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "addLayersControls.nSmoothNormals": KeySchema(
        key="nSmoothNormals",
        label="Smooth Internal Normals",
        description=(
            "Number of smoothing iterations applied to the internal point-displacement "
            "normals during layer addition. Helps avoid kinks in the layer field."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "addLayersControls.nSmoothThickness": KeySchema(
        key="nSmoothThickness",
        label="Smooth Thickness",
        description=(
            "Number of smoothing iterations applied to the layer-thickness field. "
            "Smoothing reduces abrupt thickness changes near patch boundaries."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "addLayersControls.maxFaceThicknessRatio": KeySchema(
        key="maxFaceThicknessRatio",
        label="Max Face Thickness Ratio",
        description=(
            "Maximum ratio of the face thickness to the median cell size (0–1). "
            "Faces with a higher ratio are collapsed to avoid thin slivers. "
            "A value of 0.5 is a typical default."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "addLayersControls.maxThicknessToMedialRatio": KeySchema(
        key="maxThicknessToMedialRatio",
        label="Max Thickness to Medial Ratio",
        description=(
            "Maximum ratio of the requested layer thickness to the local medial-axis "
            "distance (0–1). Prevents layers from being extruded into narrow gaps. "
            "A value of 0.3 is a typical default."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "addLayersControls.minMedianAxisAngle": KeySchema(
        key="minMedianAxisAngle",
        label="Min Median Axis Angle",
        description=(
            "Minimum angle (degrees) used in the medial-axis analysis. Points near "
            "concave regions with a smaller angle have their layer thickness reduced. "
            "A value of 90 degrees is a typical default."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "addLayersControls.nMedialAxisIter": KeySchema(
        key="nMedialAxisIter",
        label="Medial Axis Iterations",
        description=(
            "Number of iterations used to compute the medial axis. More iterations "
            "improve accuracy near complex surfaces but increase run time."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "addLayersControls.nBufferCellsNoExtrude": KeySchema(
        key="nBufferCellsNoExtrude",
        label="Buffer Cells No Extrude",
        description=(
            "Number of cell layers around patches where extrusion is disabled "
            "that are also excluded from extrusion. Acts as a buffer zone to "
            "prevent layer quality issues at no-extrude boundaries."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "addLayersControls.nRelaxIter": KeySchema(
        key="nRelaxIter",
        label="Relax Iterations (Layers)",
        description=(
            "Maximum number of relaxation iterations for the layer-addition mesh-displacement "
            "solver. Each iteration reduces displacement to avoid inverted cells near walls."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "addLayersControls.nRelaxedIter": KeySchema(
        key="nRelaxedIter",
        label="Relaxed Iterations (Layers)",
        description=(
            "Number of outer layer-addition iterations after which the relaxed mesh-quality "
            "criteria (defined in meshQualityControls.relaxed) are applied instead of the "
            "standard ones. Allows the solver to escape local quality minima."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "addLayersControls.nLayerIter": KeySchema(
        key="nLayerIter",
        label="Layer Iterations",
        description="Overall number of iterations for the layer-addition algorithm.",
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),

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
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "refinementSurfaces.faceZone": KeySchema(
        key="faceZone",
        label="Face Zone",
        description=(
            "Name of the face zone created from faces on this surface. "
            "Required when the surface is used as an internal baffle or interface."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "refinementSurfaces.cellZone": KeySchema(
        key="cellZone",
        label="Cell Zone",
        description=(
            "Name of the cell zone created from cells on the inside of this surface. "
            "Used together with faceZone to define multi-region or porous-zone boundaries."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "refinementSurfaces.cellZoneInside": KeySchema(
        key="cellZoneInside",
        label="Cell Zone Inside",
        description=(
            "Controls which side of the surface is marked as belonging to the cell zone."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        choices=(
            ChoiceItem(
                "inside",
                "Cells geometrically inside the closed surface are added to the cell zone.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "outside",
                "Cells geometrically outside the closed surface are added to the cell zone.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "insidePoint",
                "Cells in the connected region containing the insidePoint are added.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
        ),
    ),
    "refinementSurfaces.faceType": KeySchema(
        key="faceType",
        label="Face Type",
        description=(
            "Topology of the faces placed on this surface in the final mesh."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        choices=(
            ChoiceItem(
                "internal",
                "Faces are internal mesh faces shared by two cells. "
                "Used for internal interfaces without a physical gap.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "baffle",
                "Faces form a zero-thickness baffle: two boundary faces occupying the same "
                "geometric position, each owned by a different cell.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "boundary",
                "Faces become ordinary boundary faces on a single patch.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
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
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        choices=(
            ChoiceItem(
                "inside",
                "Cells whose centres lie inside the region are refined to the specified level.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "outside",
                "Cells whose centres lie outside the region are refined to the specified level.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "distance",
                "Cells within a given distance from the surface are refined; "
                "levels is a list of (distance level) pairs applied from closest to furthest.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
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
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
    ),

    # ── addLayersControls.layers entries (grandparent = "layers") ────────────
    # layers { "patch_.*" { nSurfaceLayers 3; } }
    # grandparent_key = "layers"
    "layers.nSurfaceLayers": KeySchema(
        key="nSurfaceLayers",
        label="Surface Layers",
        description=(
            "Number of boundary layers to extrude on this patch (or patch group). "
            "Set to 0 to suppress layer addition on this patch entirely."
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
