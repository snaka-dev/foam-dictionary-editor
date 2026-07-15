# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""VTK render pipeline for blockMeshDict geometry.

This module is only ever instantiated after the _PYVISTA_OK guard in
block_mesh_panel.py passes, so top-level numpy/pyvista imports are safe.
"""
from __future__ import annotations

import dataclasses

import numpy as np
import pyvista as pv

from foam.block_mesh_extractor import BlockMeshData
from foam.set_fields_extractor import SetFieldsShape
from foam.snappy_hex_mesh_extractor import SnappyShape
from foam.topo_set_extractor import TopoShape

_PATCH_COLORS: dict[str, str] = {
    "wall":          "#E87722",
    "patch":         "#0055A2",
    "empty":         "#AAAAAA",
    "symmetry":      "#00A050",
    "symmetryPlane": "#00A050",
    "wedge":         "#9040C0",
    "cyclic":        "#C0A000",
    "cyclicAMI":     "#C0A000",
    "inlet":         "#0077CC",
    "outlet":        "#CC2200",
}
_DEFAULT_PATCH_COLOR = "#4080FF"

# topoSet action → overlay colour. Only actions that carry source geometry can
# render a shape; `remove`/`clear`/`list` have none and are intentionally absent.
# `subtract` is the canonical element-removal action; `delete` is its legacy alias.
_ACTION_COLORS: dict[str, str] = {
    "new":      "steelblue",
    "add":      "forestgreen",
    "subtract": "crimson",
    "delete":   "crimson",
    "subset":   "mediumpurple",
    "invert":   "goldenrod",
}

# snappyHexMeshDict geometry-entry category → overlay colour. Distinct from
# _ACTION_COLORS so topoSet and snappyHexMesh overlays stay visually
# distinguishable when both are loaded in the same session.
_SNAPPY_CATEGORY_COLORS: dict[str, str] = {
    "surface":  "teal",
    "region":   "mediumpurple",
    "geometry": "gray",
}
_LOCATION_POINT_COLOR = "black"

# setFieldsDict regions have no topoSet action or snappy category, so they all
# share one colour, chosen to clash with neither palette above.
_SET_FIELDS_REGION_COLOR = "darkorange"

# Overlay shapes larger than the block mesh are clipped (display only) to keep
# the mesh visible; the scene label carries a mark so the cut is not mistaken
# for the shape's real extent.
_CLIP_MARGIN = 0.1
_CLIP_MARK_SUFFIX = {
    "clipped": "✂ clipped",
    "outside": "⚠ outside block mesh",
}


def _mark_label(label: str, mark: str) -> str:
    """Combine a shape label with its clip-mark suffix (either may be "")."""
    suffix = _CLIP_MARK_SUFFIX.get(mark, "")
    return f"{label}  {suffix}".strip() if suffix else label


def _make_hex_grid(pts: np.ndarray, hex_blocks: list[list[int]]) -> pv.UnstructuredGrid:
    n_verts = len(pts)
    valid = [b for b in hex_blocks if b and max(b) < n_verts]
    cells = []
    for block in valid:
        cells.extend([8] + block)
    cells_np = np.array(cells, dtype=np.int_)
    cell_types = np.full(len(valid), pv.CellType.HEXAHEDRON, dtype=np.uint8)
    return pv.UnstructuredGrid(cells_np, cell_types, pts)


def _axis_basis(p1, p2):
    """Return ``(p1, p2, d, u, v, height)`` for the axis p1 → p2.

    ``d`` is the unit axis direction and ``(u, v)`` an orthonormal basis of the
    plane perpendicular to it. Returns ``None`` for a degenerate (zero-length)
    axis.
    """
    p1 = np.asarray(p1, dtype=float)
    p2 = np.asarray(p2, dtype=float)
    axis = p2 - p1
    height = float(np.linalg.norm(axis))
    if height == 0.0:
        return None
    d = axis / height
    ref = np.array([1.0, 0.0, 0.0])
    if abs(float(np.dot(ref, d))) > 0.9:
        ref = np.array([0.0, 1.0, 0.0])
    u = np.cross(d, ref)
    u /= np.linalg.norm(u)
    v = np.cross(d, u)
    return p1, p2, d, u, v, height


def _make_frustum_mesh(
    p1, p2, r1: float, r2: float, resolution: int = 48
) -> pv.PolyData | None:
    """Build a truncated cone (frustum) spanning point1 → point2.

    A true cone is the special case ``r2 == 0``. ``pv.CylinderStructured`` cannot
    be used for this: passing an array of radii creates concentric shells of
    constant height, not a taper along the axis, so it renders as a cylinder.
    """
    basis = _axis_basis(p1, p2)
    if basis is None:
        return None
    p1, p2, _d, u, v, _height = basis

    ang = np.linspace(0.0, 2.0 * np.pi, resolution, endpoint=False)
    circ = np.cos(ang)[:, None] * u[None, :] + np.sin(ang)[:, None] * v[None, :]
    bottom = p1 + r1 * circ
    top = p2 + r2 * circ
    pts = np.vstack([bottom, top, p1[None, :], p2[None, :]])

    n = resolution
    cb, ct = 2 * n, 2 * n + 1        # bottom/top centre point indices
    faces: list[int] = []
    for i in range(n):
        j = (i + 1) % n
        faces += [4, i, j, n + j, n + i]   # lateral quad (collapses to a triangle when r2 == 0)
        faces += [3, cb, j, i]             # bottom cap
        faces += [3, ct, n + i, n + j]     # top cap
    return pv.PolyData(pts, np.array(faces, dtype=np.int_))


def _make_annular_frustum_mesh(
    p1, p2, r1o: float, r2o: float, r1i: float, r2i: float, resolution: int = 48
) -> pv.PolyData | None:
    """Build a hollow (annular) frustum spanning point1 → point2.

    ``r1o/r2o`` are the outer bottom/top radii and ``r1i/r2i`` the inner ones. A
    hollow cylinder is the special case ``r1o == r2o`` and ``r1i == r2i``. The end
    caps are annular rings (quads between the outer and inner rims), so the hole is
    visible through the ends.
    """
    basis = _axis_basis(p1, p2)
    if basis is None:
        return None
    p1, p2, _d, u, v, _height = basis

    ang = np.linspace(0.0, 2.0 * np.pi, resolution, endpoint=False)
    circ = np.cos(ang)[:, None] * u[None, :] + np.sin(ang)[:, None] * v[None, :]
    n = resolution
    outer_bottom = p1 + r1o * circ   # [0, n)
    outer_top = p2 + r2o * circ      # [n, 2n)
    inner_bottom = p1 + r1i * circ   # [2n, 3n)
    inner_top = p2 + r2i * circ      # [3n, 4n)
    pts = np.vstack([outer_bottom, outer_top, inner_bottom, inner_top])

    ob, ot, ib, it = 0, n, 2 * n, 3 * n
    faces: list[int] = []
    for a in range(n):
        b = (a + 1) % n
        # Outer wall, inner wall (reversed winding), and the two annular end caps.
        faces += [4, ob + a, ob + b, ot + b, ot + a]
        faces += [4, ib + b, ib + a, it + a, it + b]
        faces += [4, ib + a, ib + b, ob + b, ob + a]   # bottom ring
        faces += [4, ot + a, ot + b, it + b, it + a]   # top ring
    return pv.PolyData(pts, np.array(faces, dtype=np.int_))


def _expanded_bounds(pts: np.ndarray, margin: float = _CLIP_MARGIN) -> list[float]:
    """Block-mesh AABB expanded by ``margin`` per axis — the overlay clip box.

    Degenerate axes (2-D meshes) are padded from the largest span so the clip
    box always has volume.
    """
    mins = pts.min(axis=0)
    maxs = pts.max(axis=0)
    spans = maxs - mins
    fallback = float(spans.max()) or 1.0
    pad = np.where(spans > 0, spans, fallback) * margin
    return [
        float(mins[0] - pad[0]), float(maxs[0] + pad[0]),
        float(mins[1] - pad[1]), float(maxs[1] + pad[1]),
        float(mins[2] - pad[2]), float(maxs[2] + pad[2]),
    ]


def _clip_to_bounds(mesh, clip_bounds: list[float] | None):
    """Limit an overlay shape mesh to the clip box (display only).

    Returns ``(mesh, mark)`` where mark is "" (fits inside, unchanged),
    "clipped" (cut down to the box), or "outside" (no overlap at all — the
    original is kept so the shape stays visible, just labelled).
    """
    if clip_bounds is None:
        return mesh, ""
    b = mesh.bounds
    if (
        b[0] >= clip_bounds[0] and b[1] <= clip_bounds[1]
        and b[2] >= clip_bounds[2] and b[3] <= clip_bounds[3]
        and b[4] >= clip_bounds[4] and b[5] <= clip_bounds[5]
    ):
        return mesh, ""
    if (
        b[1] < clip_bounds[0] or b[0] > clip_bounds[1]
        or b[3] < clip_bounds[2] or b[2] > clip_bounds[3]
        or b[5] < clip_bounds[4] or b[4] > clip_bounds[5]
    ):
        return mesh, "outside"
    try:
        clipped = mesh.clip_box(clip_bounds, invert=False)  # keep the inside
    except Exception:
        return mesh, ""
    if clipped is None or clipped.n_cells == 0:
        # The shape's volume encloses the clip box but its surface lies wholly
        # outside it (e.g. a huge boxToCell around the whole mesh): stand in
        # with the AABB overlap so something meaningful is drawn.
        overlap = [
            max(b[0], clip_bounds[0]), min(b[1], clip_bounds[1]),
            max(b[2], clip_bounds[2]), min(b[3], clip_bounds[3]),
            max(b[4], clip_bounds[4]), min(b[5], clip_bounds[5]),
        ]
        clipped = pv.Box(bounds=overlap)
    return clipped, "clipped"


def _make_rotated_box_mesh(origin, i, j, k) -> pv.UnstructuredGrid | None:
    """Build an oriented parallelepiped from an origin and three span vectors."""
    o = np.asarray(origin, dtype=float)
    vi = np.asarray(i, dtype=float)
    vj = np.asarray(j, dtype=float)
    vk = np.asarray(k, dtype=float)
    # VTK hex ordering: bottom face 0-3, top face 4-7 (offset by +k).
    pts = np.array([
        o, o + vi, o + vi + vj, o + vj,
        o + vk, o + vi + vk, o + vi + vj + vk, o + vj + vk,
    ], dtype=float)
    return _make_hex_grid(pts, [[0, 1, 2, 3, 4, 5, 6, 7]])


@dataclasses.dataclass
class RenderSettings:
    show_vertices: bool
    show_labels: bool
    show_edges: bool
    show_block_labels: bool
    color_blocks: bool
    solid_blocks: bool
    show_boundary: bool
    show_axes: bool
    show_grid: bool
    show_bounds: bool
    label_font_size: int
    selected_vertex: int | None


class BlockMeshRenderer:
    """VTK actor setup for blockMeshDict geometry. Requires an active QtInteractor."""

    def __init__(self, plotter) -> None:
        self._plotter = plotter

    def render(
        self,
        data: BlockMeshData | None,
        settings: RenderSettings,
        stl_meshes: list,
        topo_shapes: list[TopoShape] | None = None,
        snappy_shapes: list[SnappyShape] | None = None,
        location_points: list[tuple[list, str]] | None = None,
        set_fields_shapes: list[SetFieldsShape] | None = None,
    ) -> None:
        self._plotter.clear()
        topo_shapes = topo_shapes or []
        snappy_shapes = snappy_shapes or []
        location_points = location_points or []
        set_fields_shapes = set_fields_shapes or []
        has_mesh = data is not None and bool(data.vertices)

        clip_bounds: list[float] | None = None
        if has_mesh:
            pts = np.array(data.vertices, dtype=float)
            clip_bounds = _expanded_bounds(pts)
            self._render_points(pts, data, settings)
            self._render_blocks(pts, data, settings)
            self._render_boundary_faces(pts, data, settings)

        for stl in stl_meshes:
            self._plotter.add_mesh(stl, color="lightgray", opacity=0.4)

        if topo_shapes:
            # Scene size for display-only extents (e.g. the planeToFaceZone disc).
            if has_mesh:
                pts_arr = np.array(data.vertices, dtype=float)
                scene_size = float(
                    np.linalg.norm(pts_arr.max(axis=0) - pts_arr.min(axis=0))
                ) or 1.0
            else:
                scene_size = 1.0
            self._render_topo_shapes(
                topo_shapes, settings.label_font_size, scene_size, clip_bounds
            )

        if snappy_shapes:
            self._render_snappy_shapes(
                snappy_shapes, settings.label_font_size, clip_bounds
            )

        if set_fields_shapes:
            self._render_set_fields_shapes(
                set_fields_shapes, settings.label_font_size, clip_bounds
            )

        if location_points:
            self._render_location_points(location_points, settings.label_font_size)

        if has_mesh:
            self._render_scale_indicators(pts, data, settings)

        self._plotter.reset_camera()
        self._plotter.render()

    def set_view(self, fn: str, **kw) -> None:
        getattr(self._plotter, fn)(**kw)

    def _render_points(self, pts: np.ndarray, data: BlockMeshData, settings: RenderSettings) -> None:
        verts = data.vertices
        if settings.show_vertices:
            self._plotter.add_mesh(
                pv.PolyData(pts),
                render_points_as_spheres=True,
                point_size=10,
                color="red",
            )
        if settings.selected_vertex is not None and settings.selected_vertex < len(verts):
            sel_pt = np.array([verts[settings.selected_vertex]], dtype=float)
            self._plotter.add_mesh(
                pv.PolyData(sel_pt),
                render_points_as_spheres=True,
                point_size=18,
                color="cyan",
            )
        if settings.show_labels:
            self._plotter.add_point_labels(
                pts,
                [str(i) for i in range(len(verts))],
                font_size=settings.label_font_size,
                text_color="black",
                shape=None,
                show_points=False,
                always_visible=True,
            )

    def _render_blocks(self, pts: np.ndarray, data: BlockMeshData, settings: RenderSettings) -> None:
        if not data.hex_blocks:
            return
        if settings.show_block_labels:
            centroids = np.array(
                [pts[block].mean(axis=0) for block in data.hex_blocks]
            )
            self._plotter.add_point_labels(
                centroids,
                [str(i) for i in range(len(data.hex_blocks))],
                font_size=settings.label_font_size,
                text_color="darkblue",
                shape=None,
                show_points=False,
                always_visible=True,
            )
        if not (settings.show_edges or settings.solid_blocks):
            return
        grid = _make_hex_grid(pts, data.hex_blocks)
        if settings.color_blocks:
            grid.cell_data["block_id"] = np.arange(len(data.hex_blocks))
            color_kw: dict = {
                "scalars": "block_id",
                "cmap": "tab10",
                "n_colors": len(data.hex_blocks),
                "show_scalar_bar": False,
            }
        else:
            color_kw = {"color": "steelblue"}
        if settings.show_edges:
            self._plotter.add_mesh(grid, style="wireframe", line_width=2, **color_kw)
        if settings.solid_blocks:
            self._plotter.add_mesh(grid, style="surface", opacity=0.25, **color_kw)

    def _render_boundary_faces(self, pts: np.ndarray, data: BlockMeshData, settings: RenderSettings) -> None:
        if not settings.show_boundary:
            return
        for _name, (patch_type, faces) in data.boundary_faces.items():
            if not faces:
                continue
            conn: list[int] = []
            for face in faces:
                conn += [len(face)] + face
            poly = pv.PolyData(pts, np.array(conn, dtype=np.int_))
            color = _PATCH_COLORS.get(patch_type, _DEFAULT_PATCH_COLOR)
            self._plotter.add_mesh(poly, color=color, opacity=0.6)
        # blockMesh's implicit defaultFaces (unassigned exterior faces): drawn
        # fainter than named patches — essential for quasi-2-D cases whose big
        # front/back faces are never listed under boundary.
        n_pts = len(pts)
        default_faces = [f for f in data.default_faces if f and max(f) < n_pts]
        if default_faces:
            conn = []
            for face in default_faces:
                conn += [len(face)] + face
            poly = pv.PolyData(pts, np.array(conn, dtype=np.int_))
            self._plotter.add_mesh(poly, color=_PATCH_COLORS["empty"], opacity=0.25)

    def _add_shape_label(self, position, text: str, label_font_size: int) -> None:
        self._plotter.add_point_labels(
            [position],
            [text],
            font_size=label_font_size,
            bold=True,
            text_color="black",
            background_color="white",
            background_opacity=0.7,
            always_visible=True,
            show_points=False,
        )

    def _add_shape_mesh(
        self,
        mesh,
        color: str,
        label: str,
        label_font_size: int,
        clip_bounds: list[float] | None,
    ) -> None:
        """Add one overlay shape (clipped to the scene) plus its label."""
        mesh, mark = _clip_to_bounds(mesh, clip_bounds)
        self._plotter.add_mesh(mesh, color=color, opacity=0.35, style="surface")
        self._plotter.add_mesh(mesh, color=color, opacity=0.8, style="wireframe")
        text = _mark_label(label, mark)
        if text:
            self._add_shape_label(mesh.center, text, label_font_size)

    def _render_topo_shapes(
        self,
        shapes: list[TopoShape],
        label_font_size: int = 10,
        scene_size: float = 1.0,
        clip_bounds: list[float] | None = None,
    ) -> None:
        for shape in shapes:
            color = _ACTION_COLORS.get(shape.action, "gray")
            geo = shape.geometry
            if "points" in geo:
                self._render_topo_points(shape, color, label_font_size)
                continue
            mesh = self._make_shape_mesh(
                shape.source, geo, plane_size=0.75 * scene_size
            )
            if mesh is None:
                continue
            self._add_shape_mesh(
                mesh, color, shape.label, label_font_size, clip_bounds
            )

    def _render_topo_points(
        self, shape: TopoShape | SetFieldsShape, color: str, label_font_size: int
    ) -> None:
        """Draw a point-carrying source (nearestTo*, insidePoints, nearPoint)."""
        pts = np.array(shape.geometry["points"], dtype=float)
        self._plotter.add_mesh(
            pv.PolyData(pts),
            render_points_as_spheres=True,
            point_size=14,
            color=color,
        )
        if shape.label:
            self._add_shape_label(pts.mean(axis=0), shape.label, label_font_size)

    def _render_snappy_shapes(
        self,
        shapes: list[SnappyShape],
        label_font_size: int = 10,
        clip_bounds: list[float] | None = None,
    ) -> None:
        for shape in shapes:
            color = _SNAPPY_CATEGORY_COLORS.get(shape.category, "gray")
            mesh = self._make_shape_mesh(shape.geo_type, shape.geometry)
            if mesh is None:
                continue
            detail = shape.level or shape.mode or ""
            label = f"{shape.name}  {detail}".strip()
            self._add_shape_mesh(mesh, color, label, label_font_size, clip_bounds)

    def _render_set_fields_shapes(
        self,
        shapes: list[SetFieldsShape],
        label_font_size: int = 10,
        clip_bounds: list[float] | None = None,
    ) -> None:
        color = _SET_FIELDS_REGION_COLOR
        for shape in shapes:
            if "points" in shape.geometry:
                self._render_topo_points(shape, color, label_font_size)
                continue
            mesh = self._make_shape_mesh(shape.source, shape.geometry)
            if mesh is None:
                continue
            self._add_shape_mesh(
                mesh, color, shape.label, label_font_size, clip_bounds
            )

    def _render_location_points(
        self, points: list[tuple[list, str]], label_font_size: int = 10
    ) -> None:
        if not points:
            return
        pts = np.array([p for p, _label in points], dtype=float)
        self._plotter.add_mesh(
            pv.PolyData(pts),
            render_points_as_spheres=True,
            point_size=16,
            color=_LOCATION_POINT_COLOR,
        )
        self._plotter.add_point_labels(
            pts,
            [label for _p, label in points],
            font_size=label_font_size,
            bold=True,
            text_color="black",
            background_color="white",
            background_opacity=0.7,
            always_visible=True,
            show_points=False,
        )

    @staticmethod
    def _make_shape_mesh(source: str, geo: dict, plane_size: float = 1.0):
        try:
            if "box" in geo:
                p1, p2 = geo["box"]
                bounds = [p1[0], p2[0], p1[1], p2[1], p1[2], p2[2]]
                return pv.Box(bounds=bounds)
            if "boxes" in geo:
                # Multi-box form (`boxes ( (min) (max) … );`): one merged mesh.
                meshes = [
                    pv.Box(bounds=[p1[0], p2[0], p1[1], p2[1], p1[2], p2[2]])
                    for p1, p2 in geo["boxes"]
                ]
                return pv.merge(meshes) if len(meshes) > 1 else meshes[0]
            if "origin" in geo:
                return _make_rotated_box_mesh(
                    geo["origin"], geo["i"], geo["j"], geo["k"]
                )
            if "stl_path" in geo:
                return pv.read(geo["stl_path"])
            if "planePoint" in geo:
                # An infinite plane; drawn as a disc whose extent (plane_size)
                # is display-only, sized by the caller from the scene bounds.
                return pv.Disc(
                    center=geo["planePoint"],
                    inner=0.0,
                    outer=plane_size,
                    normal=geo["planeNormal"],
                    c_res=48,
                )
            if "points" in geo:
                # Loose points carry no surface; rendered as markers instead.
                return None
            if "centre" in geo:
                radius = geo["radius"]
                if isinstance(radius, list):
                    # Ellipsoid: a per-axis radius (snappyHexMesh's `sphere` type
                    # supports this, e.g. igloo-shaped domes) — build a unit
                    # sphere and scale each axis, then translate to centre.
                    mesh = pv.Sphere(radius=1.0)
                    mesh.points *= np.asarray(radius, dtype=float)
                    mesh.points += np.asarray(geo["centre"], dtype=float)
                    return mesh
                outer = pv.Sphere(radius=radius, center=geo["centre"])
                if "innerRadius" in geo:
                    # Hollow sphere: the inner shell shows through the
                    # semi-transparent outer surface.
                    inner = pv.Sphere(radius=geo["innerRadius"], center=geo["centre"])
                    return pv.merge([outer, inner])
                return outer
            if "radius1" in geo:
                # Truncated cone (frustum); a true cone when radius2 == 0.
                # It spans the full point1 → point2 distance.
                if "innerRadius1" in geo:
                    return _make_annular_frustum_mesh(
                        geo["p1"], geo["p2"], geo["radius1"], geo["radius2"],
                        geo["innerRadius1"], geo["innerRadius2"],
                    )
                return _make_frustum_mesh(
                    geo["p1"], geo["p2"], geo["radius1"], geo["radius2"]
                )
            if "p1" in geo:
                if "innerRadius" in geo:
                    # Hollow cylinder = annular frustum with equal end radii.
                    r = geo["radius"]
                    ri = geo["innerRadius"]
                    return _make_annular_frustum_mesh(
                        geo["p1"], geo["p2"], r, r, ri, ri
                    )
                p1 = np.array(geo["p1"], dtype=float)
                p2 = np.array(geo["p2"], dtype=float)
                axis = p2 - p1
                height = float(np.linalg.norm(axis))
                if height == 0.0:
                    return None
                center = ((p1 + p2) / 2).tolist()
                direction = (axis / height).tolist()
                return pv.Cylinder(
                    center=center,
                    direction=direction,
                    radius=geo["radius"],
                    height=height,
                )
        except Exception:
            return None
        return None

    def _render_scale_indicators(self, pts: np.ndarray, data: BlockMeshData, settings: RenderSettings) -> None:
        if settings.show_axes:
            self._plotter.show_axes()
        else:
            self._plotter.hide_axes()
        if settings.show_grid:
            self._plotter.show_grid(color="gray", font_size=8)
        if settings.show_bounds:
            self._plotter.add_bounding_box(color="gray", line_width=1)
            mins = pts.min(axis=0)
            maxs = pts.max(axis=0)
            dims = maxs - mins
            lines = [
                f"X  {mins[0]:.4g} → {maxs[0]:.4g}  ({dims[0]:.4g} m)",
                f"Y  {mins[1]:.4g} → {maxs[1]:.4g}  ({dims[1]:.4g} m)",
                f"Z  {mins[2]:.4g} → {maxs[2]:.4g}  ({dims[2]:.4g} m)",
            ]
            if data.scale != 1.0:
                lines.append(f"scale  {data.scale}")
            self._plotter.add_text(
                "\n".join(lines),
                position="upper_left",
                font_size=9,
                color="black",
                font="courier",
            )
