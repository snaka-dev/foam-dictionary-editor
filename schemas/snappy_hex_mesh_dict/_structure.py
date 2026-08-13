# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Container keys of `system/snappyHexMeshDict`.

The four control dictionaries and the sub-dictionaries inside them — the rows a
user clicks first — plus wildcards for the entries whose names come from the
case's own surfaces, regions and patches.

Reference: `applications/utilities/mesh/generation/snappyHexMesh/` and
`etc/caseDicts/annotated/snappyHexMeshDict`.
"""
from __future__ import annotations

from schemas._base import (
    BOTH,
    FOUNDATION_V12,
    FOUNDATION_V13,
    OPENCFD_SERIES,
    OPENCFD_V2306,
    OPENCFD_V2606,
    ChoiceItem,
    KeySchema,
    entry,
)

from ._common import SWITCH_CHOICES

SCHEMAS: dict[str, KeySchema] = {
    # ── top-level containers ──────────────────────────────────────────────────
    "geometry": entry(
        "geometry", "Geometry",
        "Surfaces and shapes the mesher works against — STL/OBJ files and "
        "searchable primitives. Everything referenced elsewhere in this "
        "dictionary must be named here first.",
    ),
    "geometry.*": entry(
        "*", "geometry/<name>",
        "One geometry entry. For a triSurfaceMesh the name is normally the file "
        "name; for a primitive it is chosen freely and referenced by that name.",
    ),
    "castellatedMeshControls": entry(
        "castellatedMeshControls", "Castellated Mesh Controls",
        "Settings for the first meshing stage: refining the background mesh and "
        "removing the cells outside the region of interest.",
    ),
    "snapControls": entry(
        "snapControls", "Snap Controls",
        "Settings for the second stage: moving mesh points onto the surface.",
    ),
    "addLayersControls": entry(
        "addLayersControls", "Add Layers Controls",
        "Settings for the third stage: inserting prism layers at the walls.",
    ),
    "meshQualityControls": entry(
        "meshQualityControls", "Mesh Quality Controls",
        "Quality limits every stage must respect. Snapping and layer insertion "
        "are undone wherever they would violate these.",
    ),
    "writeFlags": entry(
        "writeFlags", "Write Flags",
        "Optional intermediate output, as a list — e.g. scalarLevels, layerSets, "
        "layerFields.",
    ),

    # ── castellation sub-dictionaries ─────────────────────────────────────────
    "castellatedMeshControls.features": entry(
        "features", "Features",
        "Edge-feature files (.eMesh from surfaceFeatureExtract) and the level to "
        "refine them to, as a list of dictionaries.",
    ),
    "castellatedMeshControls.refinementSurfaces": entry(
        "refinementSurfaces", "Refinement Surfaces",
        "Per-surface refinement levels. Each entry names a geometry entry.",
    ),
    "castellatedMeshControls.refinementRegions": entry(
        "refinementRegions", "Refinement Regions",
        "Volume refinement relative to a geometry entry — inside, outside, or "
        "within a distance of it.",
    ),
    "refinementSurfaces.*": entry(
        "*", "refinementSurfaces/<surface>",
        "Refinement for one surface. The name must match a geometry entry.",
    ),
    "refinementRegions.*": entry(
        "*", "refinementRegions/<region>",
        "Volume refinement for one region. The name must match a geometry entry.",
    ),
    "features.*": entry(
        "*", "features/<entry>",
        "One feature-edge entry, giving a file and a refinement level.",
    ),
    "refinementRegions.mode": entry(
        "mode", "Refinement Mode",
        "Where the refinement applies relative to the named surface.",
        (
            ChoiceItem("inside", "Cells inside the surface.", BOTH),
            ChoiceItem("outside", "Cells outside the surface.", BOTH),
            ChoiceItem("distance", "Cells within the distances given by 'levels'.", BOTH),
        ),
    ),
    "refinementRegions.levels": entry(
        "levels", "Levels",
        "Distance/level pairs. With mode 'inside' or 'outside' only the level is "
        "used, so the distance is conventionally written as 1e15.",
    ),

    # ── layers ────────────────────────────────────────────────────────────────
    "addLayersControls.layers": entry(
        "layers", "Layers",
        "Per-patch layer specification. Each entry names a patch — or a patch "
        "group, or a regular expression — in the meshed geometry.",
    ),
    "layers.*": entry(
        "*", "layers/<patch>",
        "Layer settings for one patch, at minimum nSurfaceLayers.",
    ),
    "layers.nSurfaceLayers": entry(
        "nSurfaceLayers", "Number of Surface Layers",
        "Layers added at this patch. 0 disables layers there.",
    ),
    "layers.expansionRatio": entry(
        "expansionRatio", "Expansion Ratio",
        "Per-patch expansion ratio, overriding the global value.",
    ),
    "layers.finalLayerThickness": entry(
        "finalLayerThickness", "Final Layer Thickness",
        "Per-patch final-layer thickness, overriding the global value.",
    ),
    "layers.firstLayerThickness": entry(
        "firstLayerThickness", "First Layer Thickness",
        "Per-patch first-layer thickness, overriding the global value.",
    ),
    "layers.thickness": entry(
        "thickness", "Thickness",
        "Per-patch total layer thickness, overriding the global value.",
    ),
    "layers.minThickness": entry(
        "minThickness", "Minimum Thickness",
        "Per-patch minimum thickness below which a layer is dropped.",
    ),

    # ── quality ───────────────────────────────────────────────────────────────
    "meshQualityControls.relaxed": entry(
        "relaxed", "Relaxed Quality Controls",
        "Looser limits used only where the strict ones cannot be met, chiefly "
        "during layer insertion.",
    ),
    "meshQualityControls.minEdgeLength": KeySchema(
        key="minEdgeLength", label="Minimum Edge Length",
        description="Shortest permitted edge. -1 disables the check.",
        supported_in=(OPENCFD_V2306, OPENCFD_V2606),
        note="Not present in any Foundation release checked (v7-v13).",
    ),
    "meshQualityControls.minVolCollapseRatio": entry(
        "minVolCollapseRatio", "Minimum Volume Collapse Ratio",
        "Lowest permitted ratio of cell volume to its bounding-box volume.",
    ),

    # ── geometry sub-entries ──────────────────────────────────────────────────
    "geometry.type": entry(
        "type", "Geometry Type",
        "Which kind of searchable surface this entry is.",
        (
            ChoiceItem("triSurfaceMesh", "An STL or OBJ file in constant/triSurface.", BOTH),
            ChoiceItem("searchableBox", "Axis-aligned box given by min and max.", BOTH),
            ChoiceItem("searchableSphere", "Sphere given by centre and radius.", BOTH),
            ChoiceItem("searchableCylinder", "Cylinder given by two points and a radius.", BOTH),
            ChoiceItem("searchableCone", "Cone given by two points and two radii.", BOTH),
            ChoiceItem("searchablePlane", "Infinite plane.", BOTH),
            ChoiceItem("searchableRotatedBox", "Box with an arbitrary orientation.", BOTH),
            ChoiceItem("searchableSurfaceCollection", "Several surfaces treated as one.", BOTH),
            ChoiceItem("distributedTriSurfaceMesh", "Surface distributed across processors.", BOTH),
        ),
    ),
    "geometry.regions": entry(
        "regions", "Regions",
        "Named regions inside a multi-region surface file, so each can take its "
        "own refinement level.",
    ),
    "regions.*": entry(
        "*", "regions/<region>",
        "One named region of the surface file.",
    ),
    "regions.name": entry(
        "name", "Region Name",
        "Patch name given to this region in the generated mesh.",
    ),
    "regions.level": entry(
        "level", "Region Level",
        "Refinement level for this region, as a min/max pair.",
    ),
    "geometry.file": entry(
        "file", "File",
        "Surface file this entry reads, relative to constant/triSurface.",
    ),
    "geometry.name": entry(
        "name", "Name",
        "Name this surface is referenced by, when it differs from the entry name.",
    ),
    "geometry.mergeTolerance": entry(
        "mergeTolerance", "Merge Tolerance",
        "Point-merge tolerance applied when reading this surface.",
    ),
    "geometry.scale": entry(
        "scale", "Scale",
        "Factor applied to this surface's coordinates on reading.",
    ),
    "geometry.inGroups": entry(
        "inGroups", "In Groups",
        "Patch groups the resulting patches join.",
    ),
    # Shape parameters of the searchable primitives. They sit one level inside
    # a geometry entry, so they resolve through the grandparent form.
    "geometry.min": entry("min", "Minimum", "Lower corner of a searchableBox."),
    "geometry.max": entry("max", "Maximum", "Upper corner of a searchableBox."),
    "geometry.centre": entry("centre", "Centre", "Centre of a searchableSphere."),
    "geometry.origin": entry("origin", "Origin",
        "Origin of a searchableSphere. Current name; 'centre' is the older one."),
    "geometry.radius": entry("radius", "Radius",
        "Radius of a sphere, cylinder or cone. A vector gives an ellipsoid."),
    "geometry.innerRadius": entry("innerRadius", "Inner Radius",
        "Inner radius, making a hollow sphere or an annular cone."),
    "geometry.point1": entry("point1", "Point 1",
        "First axis point of a cylinder or cone."),
    "geometry.point2": entry("point2", "Point 2",
        "Second axis point of a cylinder or cone."),
    # searchableCone reached Foundation in v12; OpenCFD has had it throughout.
    "geometry.radius1": KeySchema(
        key="radius1", label="Radius 1", description="Radius at point1 of a cone.",
        supported_in=(FOUNDATION_V12, FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "geometry.radius2": KeySchema(
        key="radius2", label="Radius 2", description="Radius at point2 of a cone.",
        supported_in=(FOUNDATION_V12, FOUNDATION_V13, OPENCFD_SERIES),
    ),
    "geometry.planeType": entry("planeType", "Plane Type",
        "How a searchablePlane is specified.",
        (
            ChoiceItem("pointAndNormal", "A point on the plane and its normal.", BOTH),
            ChoiceItem("embeddedPoints", "Three points lying in the plane.", BOTH),
            ChoiceItem("planeEquation", "Coefficients of the plane equation.", BOTH),
        )),
    "geometry.span": entry("span", "Span", "Edge lengths of a searchableRotatedBox."),
    "geometry.e1": entry("e1", "e1", "First axis of a searchableRotatedBox."),
    "geometry.e3": entry("e3", "e3", "Third axis of a searchableRotatedBox."),

    # patchInfo may hang off a refinement surface or one of its regions, so it
    # is reachable from either level.
    "patchInfo.*": entry("*", "patchInfo/<entry>",
        "Property of the patch created for this surface or region."),
    "refinementSurfaces.patchInfo": entry("patchInfo", "Patch Info",
        "Type and grouping of the patch created for this surface."),
    "regions.patchInfo": entry("patchInfo", "Patch Info",
        "Type and grouping of the patch created for this region."),
    "refinementSurfaces.regions": entry("regions", "Regions",
        "Per-region overrides for a multi-region surface."),

    # ── remaining layer and top-level keys ────────────────────────────────────
    "addLayersControls.firstLayerThickness": entry(
        "firstLayerThickness", "First Layer Thickness",
        "Thickness of the layer next to the wall, in the units chosen by "
        "relativeSizes.",
    ),
    "addLayersControls.meshShrinker": entry(
        "meshShrinker", "Mesh Shrinker",
        "Algorithm that pulls the mesh back to make room for the layers.",
        (
            ChoiceItem("displacementMotionSolver", "Motion-solver based shrinking.", BOTH),
            ChoiceItem("displacementMedialAxis", "Medial-axis based shrinking. The default.", BOTH),
        ),
    ),
    "addLayersControls.solver": entry(
        "solver", "Motion Solver",
        "Motion solver used when meshShrinker is displacementMotionSolver.",
    ),
    "addLayersControls.thicknessModel": KeySchema(
        key="thicknessModel", label="Thickness Model",
        description="Which pair of thickness parameters defines the layers.",
        supported_in=(OPENCFD_SERIES,),
        note="OpenCFD only; not present in any Foundation release checked (v7-v13).",
        choices=(
            ChoiceItem("firstAndExpansion", "First-layer thickness and expansion ratio.", BOTH),
            ChoiceItem("finalAndExpansion", "Final-layer thickness and expansion ratio.", BOTH),
            ChoiceItem("firstAndTotal", "First-layer and total thickness.", BOTH),
            ChoiceItem("finalAndTotal", "Final-layer and total thickness.", BOTH),
            ChoiceItem("totalAndExpansion", "Total thickness and expansion ratio.", BOTH),
            ChoiceItem("firstAndRelativeFinal", "First-layer and relative final thickness.", BOTH),
        ),
    ),
    "singleRegionName": entry(
        "singleRegionName", "Single Region Name",
        "Suppresses the region-name prefix on patch names when the surface has "
        "only one region.",
        SWITCH_CHOICES,
    ),
}
