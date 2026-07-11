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
    ) -> None:
        self._plotter.clear()
        topo_shapes = topo_shapes or []
        has_mesh = data is not None and bool(data.vertices)

        if has_mesh:
            pts = np.array(data.vertices, dtype=float)
            self._render_points(pts, data, settings)
            self._render_blocks(pts, data, settings)
            self._render_boundary_faces(pts, data, settings)

        for stl in stl_meshes:
            self._plotter.add_mesh(stl, color="lightgray", opacity=0.4)

        if topo_shapes:
            self._render_topo_shapes(topo_shapes, settings.label_font_size)

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

    def _render_topo_shapes(self, shapes: list[TopoShape], label_font_size: int = 10) -> None:
        for shape in shapes:
            color = _ACTION_COLORS.get(shape.action, "gray")
            geo = shape.geometry
            mesh = self._make_topo_mesh(shape.source, geo)
            if mesh is None:
                continue
            self._plotter.add_mesh(mesh, color=color, opacity=0.35, style="surface")
            self._plotter.add_mesh(mesh, color=color, opacity=0.8, style="wireframe")
            if shape.label:
                self._plotter.add_point_labels(
                    [mesh.center],
                    [shape.label],
                    font_size=label_font_size,
                    bold=True,
                    text_color="black",
                    background_color="white",
                    background_opacity=0.7,
                    always_visible=True,
                    show_points=False,
                )

    @staticmethod
    def _make_topo_mesh(source: str, geo: dict):
        try:
            if "box" in geo:
                p1, p2 = geo["box"]
                bounds = [p1[0], p2[0], p1[1], p2[1], p1[2], p2[2]]
                return pv.Box(bounds=bounds)
            if "origin" in geo:
                return _make_rotated_box_mesh(
                    geo["origin"], geo["i"], geo["j"], geo["k"]
                )
            if "centre" in geo:
                return pv.Sphere(radius=geo["radius"], center=geo["centre"])
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
