# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from schemas._base import (
    FOUNDATION_SERIES,
    OPENCFD_SERIES,
    OPENCFD_V2106,
    OPENCFD_V2112,
    OPENCFD_V2206,
    KeySchema,
)

from ._common import SWITCH_CHOICES

SCHEMAS: dict[str, KeySchema] = {
    # ── addLayersControls ─────────────────────────────────────────────────────
    "addLayersControls.relativeSizes": KeySchema(
        key="relativeSizes",
        label="Relative Sizes",
        description=(
            "When true, layer thickness parameters (finalLayerThickness, minThickness) are "
            "interpreted as fractions of the adjacent cell size. "
            "When false, they are absolute distances."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
        choices=SWITCH_CHOICES,
    ),
    "addLayersControls.expansionRatio": KeySchema(
        key="expansionRatio",
        label="Expansion Ratio",
        description=(
            "Growth ratio between successive layers away from the wall. "
            "Values greater than 1 make outer layers thicker."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),
    "addLayersControls.finalLayerThickness": KeySchema(
        key="finalLayerThickness",
        label="Final Layer Thickness",
        description=(
            "Thickness of the layer farthest from the wall, as either a fraction of the "
            "adjacent cell size (relativeSizes true) or an absolute distance."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),
    "addLayersControls.minThickness": KeySchema(
        key="minThickness",
        label="Min Thickness",
        description=(
            "Minimum allowable layer thickness. Layers thinner than this are removed. "
            "Interpreted relative or absolute depending on relativeSizes."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),
    "addLayersControls.featureAngle": KeySchema(
        key="featureAngle",
        label="Feature Angle (Layers)",
        description=(
            "Surface angle (degrees) used to identify sharp edges where layer extrusion "
            "should be reduced or stopped to avoid cell quality issues."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),
    "addLayersControls.slipFeatureAngle": KeySchema(
        key="slipFeatureAngle",
        label="Slip Feature Angle",
        description=(
            "Angle (degrees) below which layer points near feature edges are allowed to "
            "slip along the edge rather than being fully constrained. "
            "Helps avoid collapsed layers on convex edges."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),
    "addLayersControls.nGrow": KeySchema(
        key="nGrow",
        label="Grow Iterations",
        description=(
            "Number of cell layers of growth applied outward from the layer region "
            "before the final layer extrusion. Can improve stability near complex geometry."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),
    "addLayersControls.nSmoothSurfaceNormals": KeySchema(
        key="nSmoothSurfaceNormals",
        label="Smooth Surface Normals",
        description=(
            "Number of smoothing iterations for the surface normals used to determine "
            "the layer extrusion direction. More iterations produce a smoother normal field."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),
    "addLayersControls.nSmoothNormals": KeySchema(
        key="nSmoothNormals",
        label="Smooth Internal Normals",
        description=(
            "Number of smoothing iterations applied to the internal point-displacement "
            "normals during layer addition. Helps avoid kinks in the layer field."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),
    "addLayersControls.nSmoothThickness": KeySchema(
        key="nSmoothThickness",
        label="Smooth Thickness",
        description=(
            "Number of smoothing iterations applied to the layer-thickness field. "
            "Smoothing reduces abrupt thickness changes near patch boundaries."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),
    "addLayersControls.maxFaceThicknessRatio": KeySchema(
        key="maxFaceThicknessRatio",
        label="Max Face Thickness Ratio",
        description=(
            "Maximum ratio of the face thickness to the median cell size (0–1). "
            "Faces with a higher ratio are collapsed to avoid thin slivers. "
            "A value of 0.5 is a typical default."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),
    "addLayersControls.maxThicknessToMedialRatio": KeySchema(
        key="maxThicknessToMedialRatio",
        label="Max Thickness to Medial Ratio",
        description=(
            "Maximum ratio of the requested layer thickness to the local medial-axis "
            "distance (0–1). Prevents layers from being extruded into narrow gaps. "
            "A value of 0.3 is a typical default."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),
    "addLayersControls.minMedialAxisAngle": KeySchema(
        key="minMedialAxisAngle",
        label="Min Medial Axis Angle",
        description=(
            "Minimum angle (degrees) used in the medial-axis analysis. Points near "
            "concave regions with a smaller angle have their layer thickness reduced. "
            "A value of 90 degrees is a typical default."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
        renamed_from=("minMedianAxisAngle",),
    ),
    "addLayersControls.minMedianAxisAngle": KeySchema(
        key="minMedianAxisAngle",
        label="Min Median Axis Angle",
        description=(
            "Historical spelling of minMedialAxisAngle — 'median' rather than "
            "'medial'. Same meaning: the minimum angle used in the medial-axis "
            "analysis."
        ),
        # Verified per tree: every Foundation release from v7 to dev still
        # declares the compatibility entry, while OpenCFD carries it up to
        # v2206 and drops it in v2212 (medialAxisMeshMover.C). v2112 sits
        # between two releases that both declare it and is listed on that
        # basis — it is the one release in the v2106-v2606 span with no local
        # source tree to check.
        supported_in=(FOUNDATION_SERIES, OPENCFD_V2106, OPENCFD_V2112, OPENCFD_V2206),
        status="renamed",
        use_instead="minMedialAxisAngle",
        deprecated_since="v1712",
        note=(
            "The code was renamed in DEC-2013. OpenCFD kept the old name as a "
            "compatibility entry through v2206 and removed it in v2212, so an "
            "OpenCFD case using this spelling is silently ignored today. "
            "Foundation still accepts both."
        ),
    ),
    "addLayersControls.nMedialAxisIter": KeySchema(
        key="nMedialAxisIter",
        label="Medial Axis Iterations",
        description=(
            "Number of iterations used to compute the medial axis. More iterations "
            "improve accuracy near complex surfaces but increase run time."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),
    "addLayersControls.nBufferCellsNoExtrude": KeySchema(
        key="nBufferCellsNoExtrude",
        label="Buffer Cells No Extrude",
        description=(
            "Number of cell layers around patches where extrusion is disabled "
            "that are also excluded from extrusion. Acts as a buffer zone to "
            "prevent layer quality issues at no-extrude boundaries."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),
    "addLayersControls.nRelaxIter": KeySchema(
        key="nRelaxIter",
        label="Relax Iterations (Layers)",
        description=(
            "Maximum number of relaxation iterations for the layer-addition mesh-displacement "
            "solver. Each iteration reduces displacement to avoid inverted cells near walls."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),
    "addLayersControls.nRelaxedIter": KeySchema(
        key="nRelaxedIter",
        label="Relaxed Iterations (Layers)",
        description=(
            "Number of outer layer-addition iterations after which the relaxed mesh-quality "
            "criteria (defined in meshQualityControls.relaxed) are applied instead of the "
            "standard ones. Allows the solver to escape local quality minima."
        ),
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),
    "addLayersControls.nLayerIter": KeySchema(
        key="nLayerIter",
        label="Layer Iterations",
        description="Overall number of iterations for the layer-addition algorithm.",
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
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
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
    ),

}
