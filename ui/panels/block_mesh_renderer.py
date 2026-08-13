# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""VTK render pipeline for blockMeshDict geometry.

This module is only ever instantiated after the _PYVISTA_OK guard in
block_mesh_panel.py passes, so top-level numpy/pyvista imports are safe.
"""
from __future__ import annotations

import dataclasses
from collections.abc import Callable, Sequence
from typing import Any

import numpy as np
import pyvista as pv

from foam.block_mesh_extractor import BlockMeshData
from foam.sampling_extractor import SamplingShape
from foam.set_fields_extractor import SetFieldsShape
from foam.shapes import SourceShape
from foam.snappy_hex_mesh_extractor import SnappyShape
from foam.topo_set_extractor import TopoShape
from ui.panels.shape_mesh import (
    _clip_to_bounds,
    _expanded_bounds,
    _make_hex_grid,
    _mark_label,
    make_shape_mesh,
)
from ui.theme import colors


def _opacity(base: float) -> float:
    """Scale a face opacity for the active theme, clamped to a valid alpha.

    Translucent faces blend toward the scene background, so an alpha tuned
    against white reads as muddy against the dark viewport.
    """
    return min(1.0, base * colors().viewport_geometry_opacity)


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
# Keep-point markers use the viewport foreground so they stay visible in
# both themes (a fixed black dot vanishes against the dark scene).

# setFieldsDict regions have no topoSet action or snappy category, so they all
# share one colour, chosen to clash with neither palette above.
_SET_FIELDS_REGION_COLOR = "darkorange"

# Loaded reference surfaces cycle a pale palette so several files stay
# distinguishable, deliberately washed-out next to the saturated dict-overlay
# colours above. "lightgray" comes first so a single loaded file looks exactly
# as it did when every surface was grey.
_SURFACE_COLORS: tuple[str, ...] = (
    "lightgray", "lightsteelblue", "wheat", "thistle",
    "darkseagreen", "lightsalmon", "paleturquoise", "khaki",
)


@dataclasses.dataclass
class LoadedSurface:
    """One STL/OBJ file loaded into the viewer as a reference overlay.

    The label/kind/source_file names deliberately mirror foam/shapes.py's
    SourceShape scheme so instances drop straight into the panel's
    _ShapeOverlayMenu, whose row identity is (source_file, label, kind). It is
    not a SourceShape subclass: that class's third field is a parsed geometry
    dict, and a loaded surface carries a mesh instead, so inheriting would mean
    dragging a permanently empty `geometry` along.
    """

    label: str        # basename, shown in the STL ▾ row
    kind: str         # file suffix without the dot ("stl", "obj")
    source_file: str  # full path — stable identity across menu rebuilds
    color: str
    mesh: Any         # pyvista mesh from read_surface_mesh()

# All sampling shapes (probes / sample lines / sample planes) share one colour.
_SAMPLING_COLOR = "teal"


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
    selected_block: int | None = None


class BlockMeshRenderer:
    """VTK actor setup for blockMeshDict geometry. Requires an active QtInteractor."""

    def __init__(self, plotter) -> None:
        self._plotter = plotter

    def render(
        self,
        data: BlockMeshData | None,
        settings: RenderSettings,
        surfaces: list[LoadedSurface],
        topo_shapes: list[TopoShape] | None = None,
        snappy_shapes: list[SnappyShape] | None = None,
        location_points: list[tuple[list, str]] | None = None,
        set_fields_shapes: list[SetFieldsShape] | None = None,
        sampling_shapes: list[SamplingShape] | None = None,
    ) -> None:
        self._plotter.clear()
        topo_shapes = topo_shapes or []
        snappy_shapes = snappy_shapes or []
        location_points = location_points or []
        set_fields_shapes = set_fields_shapes or []
        sampling_shapes = sampling_shapes or []
        has_mesh = data is not None and bool(data.vertices)

        clip_bounds: list[float] | None = None
        if has_mesh:
            assert data is not None  # has_mesh implies data is not None
            pts = np.array(data.vertices, dtype=float)
            clip_bounds = _expanded_bounds(pts)
            self._render_points(pts, data, settings)
            self._render_blocks(pts, data, settings)
            self._render_boundary_faces(pts, data, settings)

        for surface in surfaces:
            self._plotter.add_mesh(
                surface.mesh, color=surface.color, opacity=_opacity(0.4)
            )

        # Scene size for display-only extents (plane discs, sample-line tubes).
        if has_mesh:
            assert data is not None  # has_mesh implies data is not None
            pts_arr = np.array(data.vertices, dtype=float)
            scene_size = float(
                np.linalg.norm(pts_arr.max(axis=0) - pts_arr.min(axis=0))
            ) or 1.0
        else:
            scene_size = 1.0

        if topo_shapes:
            self._render_source_shapes(
                topo_shapes,
                lambda s: _ACTION_COLORS.get(s.action, "gray"),
                settings.label_font_size,
                clip_bounds,
                plane_size=0.75 * scene_size,
            )

        if snappy_shapes:
            self._render_snappy_shapes(
                snappy_shapes, settings.label_font_size, clip_bounds
            )

        if set_fields_shapes:
            self._render_source_shapes(
                set_fields_shapes,
                lambda s: _SET_FIELDS_REGION_COLOR,
                settings.label_font_size,
                clip_bounds,
            )

        if sampling_shapes:
            self._render_source_shapes(
                sampling_shapes,
                lambda s: _SAMPLING_COLOR,
                settings.label_font_size,
                clip_bounds,
                plane_size=0.75 * scene_size,
            )

        if location_points:
            self._render_location_points(location_points, settings.label_font_size)

        if has_mesh:
            assert data is not None  # has_mesh implies data is not None
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
                text_color=colors().viewport_vertex_label_fg,
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
                text_color=colors().viewport_block_label_fg,
                shape=None,
                show_points=False,
                always_visible=True,
            )
        self._render_selected_block(pts, data, settings)
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
            self._plotter.add_mesh(grid, style="surface", opacity=_opacity(0.25), **color_kw)

    def _render_selected_block(
        self, pts: np.ndarray, data: BlockMeshData, settings: RenderSettings,
    ) -> None:
        """Outline the block whose tree row is selected.

        Its own actor rather than a scalar on the shared grid: the blocks are
        drawn as one UnstructuredGrid, and the highlight has to stay visible
        whether or not block edges and solid faces are switched on at all.
        """
        index = settings.selected_block
        if index is None or not (0 <= index < len(data.hex_blocks)):
            return
        block = data.hex_blocks[index]
        if not block or max(block) >= len(pts):
            return

        highlight = colors().viewport_selected_block
        grid = _make_hex_grid(pts, [block])
        self._plotter.add_mesh(grid, style="wireframe", line_width=5, color=highlight)
        self._plotter.add_mesh(grid, style="surface", opacity=_opacity(0.35), color=highlight)

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
            self._plotter.add_mesh(poly, color=color, opacity=_opacity(0.6))
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
            self._plotter.add_mesh(poly, color=_PATCH_COLORS["empty"], opacity=_opacity(0.25))

    def _add_shape_label(self, position, text: str, label_font_size: int) -> None:
        self._plotter.add_point_labels(
            [position],
            [text],
            font_size=label_font_size,
            bold=True,
            text_color=colors().viewport_label_fg,
            background_color=colors().viewport_label_bg,
            background_opacity=0.85,
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
        self._plotter.add_mesh(mesh, color=color, opacity=_opacity(0.35), style="surface")
        self._plotter.add_mesh(mesh, color=color, opacity=0.8, style="wireframe")
        text = _mark_label(label, mark)
        if text:
            self._add_shape_label(mesh.center, text, label_font_size)

    def _render_source_shapes(
        self,
        shapes: Sequence[SourceShape],
        color_for: Callable[[Any], str],
        label_font_size: int = 10,
        clip_bounds: list[float] | None = None,
        plane_size: float = 1.0,
    ) -> None:
        """Render shapes carrying the shared label/kind field scheme."""
        for shape in shapes:
            color = color_for(shape)
            geo = shape.geometry
            if "points" in geo:
                self._render_point_shape(shape, color, label_font_size)
                continue
            mesh = make_shape_mesh(shape.kind, geo, plane_size=plane_size)
            if mesh is None:
                continue
            self._add_shape_mesh(
                mesh, color, shape.label, label_font_size, clip_bounds
            )

    def _render_point_shape(
        self,
        shape: SourceShape,
        color: str,
        label_font_size: int,
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
            mesh = make_shape_mesh(shape.kind, shape.geometry)
            if mesh is None:
                continue
            detail = shape.level or shape.mode or ""
            label = f"{shape.label}  {detail}".strip()
            self._add_shape_mesh(mesh, color, label, label_font_size, clip_bounds)

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
            color=colors().viewport_text,
        )
        self._plotter.add_point_labels(
            pts,
            [label for _p, label in points],
            font_size=label_font_size,
            bold=True,
            text_color=colors().viewport_label_fg,
            background_color=colors().viewport_label_bg,
            background_opacity=0.85,
            always_visible=True,
            show_points=False,
        )

    def _render_scale_indicators(
        self, pts: np.ndarray, data: BlockMeshData, settings: RenderSettings
    ) -> None:
        if settings.show_axes:
            self._plotter.show_axes()
        else:
            self._plotter.hide_axes()
        if settings.show_grid:
            axes = self._plotter.show_grid(color=colors().viewport_grid, font_size=8)
            # show_grid's ``color`` paints the lines and their text alike, which
            # leaves the tick numbers as faint as the gridlines. Repaint just
            # the text afterwards; VTK keeps a property per axis, so all three
            # need setting.
            grid_text = pv.Color(colors().viewport_grid_text).float_rgb
            for axis in range(3):
                axes.GetLabelTextProperty(axis).SetColor(*grid_text)
                axes.GetTitleTextProperty(axis).SetColor(*grid_text)
        if settings.show_bounds:
            self._plotter.add_bounding_box(color=colors().viewport_grid, line_width=1)
            mins = pts.min(axis=0)
            maxs = pts.max(axis=0)
            dims = maxs - mins
            # ".." and not an arrow or a dash: VTK draws no glyph at all for →
            # (see shape_mesh.py's _CLIP_MARK_SUFFIX), and a hyphen would read
            # as a minus sign in a range that starts negative — "X  -5 - 15".
            lines = [
                f"X  {mins[0]:.4g} .. {maxs[0]:.4g}  ({dims[0]:.4g} m)",
                f"Y  {mins[1]:.4g} .. {maxs[1]:.4g}  ({dims[1]:.4g} m)",
                f"Z  {mins[2]:.4g} .. {maxs[2]:.4g}  ({dims[2]:.4g} m)",
            ]
            if data.scale != 1.0:
                lines.append(f"scale  {data.scale}")
            self._plotter.add_text(
                "\n".join(lines),
                position="upper_left",
                font_size=9,
                color=colors().viewport_text,
                font="courier",
            )
