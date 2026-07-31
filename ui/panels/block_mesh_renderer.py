# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""VTK render pipeline for blockMeshDict geometry.

This module is only ever instantiated after the _PYVISTA_OK guard in
block_mesh_panel.py passes, so top-level numpy/pyvista imports are safe.
"""
from __future__ import annotations

import dataclasses
import gzip
import os
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pyvista as pv

from foam.block_mesh_extractor import BlockMeshData
from foam.sampling_extractor import SamplingShape
from foam.set_fields_extractor import SetFieldsShape
from foam.shapes import SourceShape
from foam.snappy_hex_mesh_extractor import SnappyShape
from foam.topo_set_extractor import TopoShape
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

# Overlay shapes larger than the block mesh are clipped (display only) to keep
# the mesh visible; the scene label carries a mark so the cut is not mistaken
# for the shape's real extent.
#
# Plain ASCII, and parenthesised rather than bracketed, because these are drawn
# by VTK and not by Qt. VTK's built-in label font has no glyph for ✂ or ⚠ (nor
# for →) and draws *nothing* at all for them — not even a .notdef box — so the
# marks these once used reached the screen as a blank gap inside the badge.
# Square brackets are no good either: they come out as parentheses. Parentheses
# render as themselves, and match the "(no geometry)" suffix the overlay menus
# already use. Anything added here wants checking on screen, not just in a test.
_CLIP_MARGIN = 0.1
_CLIP_MARK_SUFFIX = {
    "clipped": "(clipped)",
    "outside": "(outside block mesh)",
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


def _bounds_within(inner, outer, rel_eps: float = 1e-4) -> bool:
    """True if AABB ``inner`` lies inside AABB ``outer`` (scaled slack).

    VTK stores clipped points as float32, so allow a small tolerance scaled
    to the clip box so genuine clips at the planes still count as inside.
    """
    span = max(outer[1] - outer[0], outer[3] - outer[2], outer[5] - outer[4], 1.0)
    eps = span * rel_eps
    return (
        inner[0] >= outer[0] - eps and inner[1] <= outer[1] + eps
        and inner[2] >= outer[2] - eps and inner[3] <= outer[3] + eps
        and inner[4] >= outer[4] - eps and inner[5] <= outer[5] + eps
    )


# (normal, index into a bounds list) per clip-box face, each normal pointing
# into the box so vtkClipClosedSurface keeps the inside.
_CLIP_PLANES = (
    ((1.0, 0.0, 0.0), 0), ((-1.0, 0.0, 0.0), 1),
    ((0.0, 1.0, 0.0), 2), ((0.0, -1.0, 0.0), 3),
    ((0.0, 0.0, 1.0), 4), ((0.0, 0.0, -1.0), 5),
)


def _clip_capped(mesh, clip_bounds: list[float]):
    """Clip a closed shape to the box, sealing each cut face. None if it can't.

    ``clip_box`` leaves the cut open, and a shape mesh is a hollow surface, so
    a shape whose end caps both fall outside the box comes back a tube. That
    is not an edge case: a ``setFieldsDict`` box spanning ``z -1 1`` against a
    quasi-2-D mesh is see-through from the front, which is the one angle such
    a case is ever viewed from. Clipping plane by plane seals each cut, but
    only accepts a closed manifold surface — a plane disc is not one, and
    neither is whatever a preceding plane may have left — so failure is
    expected and the caller falls back to ``clip_box``.

    ``clean`` is what makes a cylinder pass at all: its seam carries duplicate
    points that read as non-manifold until they are merged. It is deliberately
    ``clean`` rather than ``triangulate``, which satisfies the same check but
    splits the box's quad faces — and the wireframe pass drawn over the result
    would then show a diagonal across every one of them.
    """
    try:
        surface = mesh if isinstance(mesh, pv.PolyData) else mesh.extract_surface()
        surface = surface.clean()
        for normal, idx in _CLIP_PLANES:
            origin = [0.0, 0.0, 0.0]
            origin[idx // 2] = clip_bounds[idx]
            surface = surface.clip_closed_surface(normal=normal, origin=origin)
            if surface.n_cells == 0:
                return None
    except Exception:
        return None
    # Same honesty check as the clip_box path: a result claiming to be clipped
    # but still spanning the unclipped extent is degenerate, not a clip.
    if not _bounds_within(surface.bounds, clip_bounds):
        return None
    return surface


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
    capped = _clip_capped(mesh, clip_bounds)
    if capped is not None:
        return capped, "clipped"
    try:
        clipped = mesh.clip_box(clip_bounds, invert=False)  # keep the inside
    except Exception:
        return mesh, ""
    if (
        clipped is None
        or clipped.n_cells == 0
        or not _bounds_within(clipped.bounds, clip_bounds)
    ):
        # The shape's volume encloses the clip box but its surface lies wholly
        # outside it (e.g. a huge boxToCell around the whole mesh): stand in
        # with the AABB overlap so something meaningful is drawn. VTK's box
        # clip can also return a non-empty *degenerate* result for a hollow
        # shell that straddles a clip plane (e.g. a box enclosing the mesh in
        # x/y but cut by a z face inside the clip range) whose bounds still
        # span the huge unclipped extent — the _bounds_within test above
        # catches that case too, since a genuinely clipped result is always
        # honestly bounded by the clip box.
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


def read_surface_mesh(path: str):
    """Read an STL/OBJ surface, transparently decompressing gzip.

    pyvista/VTK dispatch on the file extension and cannot read a gzip stream,
    so a ``.stl.gz`` / ``.obj.gz`` file is decompressed to a temporary file
    that carries the inner extension and read from there. A binary-STL inner
    extension (``.stlb``) is written as ``.stl`` because VTK's STL reader,
    which auto-detects ASCII vs binary, is not registered for ``.stlb``.
    The temp file is removed after reading; the ``fode-surface-`` prefix
    makes any file orphaned by a hard kill attributable to this app.
    """
    if path.lower().endswith(".gz"):
        inner_suffix = Path(path[:-3]).suffix.lower()
        if inner_suffix == ".stlb":
            inner_suffix = ".stl"
        with gzip.open(path, "rb") as src:
            data = src.read()
        fd, tmp_path = tempfile.mkstemp(prefix="fode-surface-", suffix=inner_suffix)
        try:
            with os.fdopen(fd, "wb") as tmp:
                tmp.write(data)
            return pv.read(tmp_path)
        finally:
            os.unlink(tmp_path)
    return pv.read(path)


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
            mesh = self._make_shape_mesh(shape.kind, geo, plane_size=plane_size)
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
            mesh = self._make_shape_mesh(shape.kind, shape.geometry)
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
                return read_surface_mesh(geo["stl_path"])
            if "start" in geo:
                # A sample line; drawn as a thin tube whose radius (derived
                # from plane_size, i.e. the scene bounds) is display-only.
                return pv.Line(geo["start"], geo["end"]).tube(
                    radius=0.008 * plane_size
                )
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
            # (see _CLIP_MARK_SUFFIX above), and a hyphen would read as a minus
            # sign in a range that starts negative — "X  -5 - 15".
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
