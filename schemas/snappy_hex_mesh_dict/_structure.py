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
    FOUNDATION_SERIES,
    FOUNDATION_V12,
    FOUNDATION_V13,
    OPENCFD_SERIES,
    OPENCFD_V2306,
    OPENCFD_V2606,
    ChoiceItem,
    KeySchema,
)

from ._common import SWITCH_CHOICES

_BOTH = (FOUNDATION_SERIES, OPENCFD_SERIES)


def _entry(key: str, label: str, description: str,
           choices: tuple[ChoiceItem, ...] = ()) -> KeySchema:
    return KeySchema(
        key=key, label=label, description=description,
        supported_in=_BOTH, choices=choices,
    )


SCHEMAS: dict[str, KeySchema] = {
    # ── top-level containers ──────────────────────────────────────────────────
    "geometry": _entry(
        "geometry", "Geometry",
        "Surfaces and shapes the mesher works against — STL/OBJ files and "
        "searchable primitives. Everything referenced elsewhere in this "
        "dictionary must be named here first.",
    ),
    "geometry.*": _entry(
        "*", "geometry/<name>",
        "One geometry entry. For a triSurfaceMesh the name is normally the file "
        "name; for a primitive it is chosen freely and referenced by that name.",
    ),
    "castellatedMeshControls": _entry(
        "castellatedMeshControls", "Castellated Mesh Controls",
        "Settings for the first meshing stage: refining the background mesh and "
        "removing the cells outside the region of interest.",
    ),
    "snapControls": _entry(
        "snapControls", "Snap Controls",
        "Settings for the second stage: moving mesh points onto the surface.",
    ),
    "addLayersControls": _entry(
        "addLayersControls", "Add Layers Controls",
        "Settings for the third stage: inserting prism layers at the walls.",
    ),
    "meshQualityControls": _entry(
        "meshQualityControls", "Mesh Quality Controls",
        "Quality limits every stage must respect. Snapping and layer insertion "
        "are undone wherever they would violate these.",
    ),
    "writeFlags": _entry(
        "writeFlags", "Write Flags",
        "Optional intermediate output, as a list — e.g. scalarLevels, layerSets, "
        "layerFields.",
    ),

    # ── castellation sub-dictionaries ─────────────────────────────────────────
    "castellatedMeshControls.features": _entry(
        "features", "Features",
        "Edge-feature files (.eMesh from surfaceFeatureExtract) and the level to "
        "refine them to, as a list of dictionaries.",
    ),
    "castellatedMeshControls.refinementSurfaces": _entry(
        "refinementSurfaces", "Refinement Surfaces",
        "Per-surface refinement levels. Each entry names a geometry entry.",
    ),
    "castellatedMeshControls.refinementRegions": _entry(
        "refinementRegions", "Refinement Regions",
        "Volume refinement relative to a geometry entry — inside, outside, or "
        "within a distance of it.",
    ),
    "refinementSurfaces.*": _entry(
        "*", "refinementSurfaces/<surface>",
        "Refinement for one surface. The name must match a geometry entry.",
    ),
    "refinementRegions.*": _entry(
        "*", "refinementRegions/<region>",
        "Volume refinement for one region. The name must match a geometry entry.",
    ),
    "features.*": _entry(
        "*", "features/<entry>",
        "One feature-edge entry, giving a file and a refinement level.",
    ),
    "refinementRegions.mode": _entry(
        "mode", "Refinement Mode",
        "Where the refinement applies relative to the named surface.",
        (
            ChoiceItem("inside", "Cells inside the surface.", _BOTH),
            ChoiceItem("outside", "Cells outside the surface.", _BOTH),
            ChoiceItem("distance", "Cells within the distances given by 'levels'.", _BOTH),
        ),
    ),
    "refinementRegions.levels": _entry(
        "levels", "Levels",
        "Distance/level pairs. With mode 'inside' or 'outside' only the level is "
        "used, so the distance is conventionally written as 1e15.",
    ),

    # ── layers ────────────────────────────────────────────────────────────────
    "addLayersControls.layers": _entry(
        "layers", "Layers",
        "Per-patch layer specification. Each entry names a patch — or a patch "
        "group, or a regular expression — in the meshed geometry.",
    ),
    "layers.*": _entry(
        "*", "layers/<patch>",
        "Layer settings for one patch, at minimum nSurfaceLayers.",
    ),
    "layers.nSurfaceLayers": _entry(
        "nSurfaceLayers", "Number of Surface Layers",
        "Layers added at this patch. 0 disables layers there.",
    ),
    "layers.expansionRatio": _entry(
        "expansionRatio", "Expansion Ratio",
        "Per-patch expansion ratio, overriding the global value.",
    ),
    "layers.finalLayerThickness": _entry(
        "finalLayerThickness", "Final Layer Thickness",
        "Per-patch final-layer thickness, overriding the global value.",
    ),
    "layers.firstLayerThickness": _entry(
        "firstLayerThickness", "First Layer Thickness",
        "Per-patch first-layer thickness, overriding the global value.",
    ),
    "layers.thickness": _entry(
        "thickness", "Thickness",
        "Per-patch total layer thickness, overriding the global value.",
    ),
    "layers.minThickness": _entry(
        "minThickness", "Minimum Thickness",
        "Per-patch minimum thickness below which a layer is dropped.",
    ),

    # ── quality ───────────────────────────────────────────────────────────────
    "meshQualityControls.relaxed": _entry(
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
    "meshQualityControls.minVolCollapseRatio": _entry(
        "minVolCollapseRatio", "Minimum Volume Collapse Ratio",
        "Lowest permitted ratio of cell volume to its bounding-box volume.",
    ),

    # ── geometry sub-entries ──────────────────────────────────────────────────
    "geometry.type": _entry(
        "type", "Geometry Type",
        "Which kind of searchable surface this entry is.",
        (
            ChoiceItem("triSurfaceMesh", "An STL or OBJ file in constant/triSurface.", _BOTH),
            ChoiceItem("searchableBox", "Axis-aligned box given by min and max.", _BOTH),
            ChoiceItem("searchableSphere", "Sphere given by centre and radius.", _BOTH),
            ChoiceItem("searchableCylinder", "Cylinder given by two points and a radius.", _BOTH),
            ChoiceItem("searchableCone", "Cone given by two points and two radii.", _BOTH),
            ChoiceItem("searchablePlane", "Infinite plane.", _BOTH),
            ChoiceItem("searchableRotatedBox", "Box with an arbitrary orientation.", _BOTH),
            ChoiceItem("searchableSurfaceCollection", "Several surfaces treated as one.", _BOTH),
            ChoiceItem("distributedTriSurfaceMesh", "Surface distributed across processors.", _BOTH),
        ),
    ),
    "geometry.regions": _entry(
        "regions", "Regions",
        "Named regions inside a multi-region surface file, so each can take its "
        "own refinement level.",
    ),
    "regions.*": _entry(
        "*", "regions/<region>",
        "One named region of the surface file.",
    ),
    "regions.name": _entry(
        "name", "Region Name",
        "Patch name given to this region in the generated mesh.",
    ),
    "regions.level": _entry(
        "level", "Region Level",
        "Refinement level for this region, as a min/max pair.",
    ),
    "geometry.file": _entry(
        "file", "File",
        "Surface file this entry reads, relative to constant/triSurface.",
    ),
    "geometry.name": _entry(
        "name", "Name",
        "Name this surface is referenced by, when it differs from the entry name.",
    ),
    "geometry.mergeTolerance": _entry(
        "mergeTolerance", "Merge Tolerance",
        "Point-merge tolerance applied when reading this surface.",
    ),
    "geometry.scale": _entry(
        "scale", "Scale",
        "Factor applied to this surface's coordinates on reading.",
    ),
    "geometry.inGroups": _entry(
        "inGroups", "In Groups",
        "Patch groups the resulting patches join.",
    ),
    # Shape parameters of the searchable primitives. They sit one level inside
    # a geometry entry, so they resolve through the grandparent form.
    "geometry.min": _entry("min", "Minimum", "Lower corner of a searchableBox."),
    "geometry.max": _entry("max", "Maximum", "Upper corner of a searchableBox."),
    "geometry.centre": _entry("centre", "Centre", "Centre of a searchableSphere."),
    "geometry.origin": _entry("origin", "Origin",
        "Origin of a searchableSphere. Current name; 'centre' is the older one."),
    "geometry.radius": _entry("radius", "Radius",
        "Radius of a sphere, cylinder or cone. A vector gives an ellipsoid."),
    "geometry.innerRadius": _entry("innerRadius", "Inner Radius",
        "Inner radius, making a hollow sphere or an annular cone."),
    "geometry.point1": _entry("point1", "Point 1",
        "First axis point of a cylinder or cone."),
    "geometry.point2": _entry("point2", "Point 2",
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
    "geometry.planeType": _entry("planeType", "Plane Type",
        "How a searchablePlane is specified.",
        (
            ChoiceItem("pointAndNormal", "A point on the plane and its normal.", _BOTH),
            ChoiceItem("embeddedPoints", "Three points lying in the plane.", _BOTH),
            ChoiceItem("planeEquation", "Coefficients of the plane equation.", _BOTH),
        )),
    "geometry.span": _entry("span", "Span", "Edge lengths of a searchableRotatedBox."),
    "geometry.e1": _entry("e1", "e1", "First axis of a searchableRotatedBox."),
    "geometry.e3": _entry("e3", "e3", "Third axis of a searchableRotatedBox."),

    # patchInfo may hang off a refinement surface or one of its regions, so it
    # is reachable from either level.
    "patchInfo.*": _entry("*", "patchInfo/<entry>",
        "Property of the patch created for this surface or region."),
    "refinementSurfaces.patchInfo": _entry("patchInfo", "Patch Info",
        "Type and grouping of the patch created for this surface."),
    "regions.patchInfo": _entry("patchInfo", "Patch Info",
        "Type and grouping of the patch created for this region."),
    "refinementSurfaces.regions": _entry("regions", "Regions",
        "Per-region overrides for a multi-region surface."),

    # ── remaining layer and top-level keys ────────────────────────────────────
    "addLayersControls.firstLayerThickness": _entry(
        "firstLayerThickness", "First Layer Thickness",
        "Thickness of the layer next to the wall, in the units chosen by "
        "relativeSizes.",
    ),
    "addLayersControls.meshShrinker": _entry(
        "meshShrinker", "Mesh Shrinker",
        "Algorithm that pulls the mesh back to make room for the layers.",
        (
            ChoiceItem("displacementMotionSolver", "Motion-solver based shrinking.", _BOTH),
            ChoiceItem("displacementMedialAxis", "Medial-axis based shrinking. The default.", _BOTH),
        ),
    ),
    "addLayersControls.solver": _entry(
        "solver", "Motion Solver",
        "Motion solver used when meshShrinker is displacementMotionSolver.",
    ),
    "addLayersControls.thicknessModel": KeySchema(
        key="thicknessModel", label="Thickness Model",
        description="Which pair of thickness parameters defines the layers.",
        supported_in=(OPENCFD_SERIES,),
        note="OpenCFD only; not present in any Foundation release checked (v7-v13).",
        choices=(
            ChoiceItem("firstAndExpansion", "First-layer thickness and expansion ratio.", _BOTH),
            ChoiceItem("finalAndExpansion", "Final-layer thickness and expansion ratio.", _BOTH),
            ChoiceItem("firstAndTotal", "First-layer and total thickness.", _BOTH),
            ChoiceItem("finalAndTotal", "Final-layer and total thickness.", _BOTH),
            ChoiceItem("totalAndExpansion", "Total thickness and expansion ratio.", _BOTH),
            ChoiceItem("firstAndRelativeFinal", "First-layer and relative final thickness.", _BOTH),
        ),
    ),
    "singleRegionName": _entry(
        "singleRegionName", "Single Region Name",
        "Suppresses the region-name prefix on patch names when the surface has "
        "only one region.",
        SWITCH_CHOICES,
    ),
}
