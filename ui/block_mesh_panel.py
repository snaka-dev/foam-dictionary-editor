# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from foam.nodes import FoamNode

try:
    import numpy as np
    import pyvista as pv
    from pyvistaqt import QtInteractor

    _PYVISTA_OK = True
except ImportError:
    _PYVISTA_OK = False

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
_MAX_VERTEX_TABLE_ROWS = 500

_MOUSE_HINT = (
    "Mouse:  drag = rotate  |  Shift+drag = pan  "
    "|  scroll / right-drag = zoom  |  R = reset camera  |  F = fly to point"
)
_MOUSE_HINT_TOOLTIP = (
    "Rotate:        Left drag\n"
    "Pan:           Shift + left drag\n"
    "Zoom:          Scroll wheel  or  right drag\n"
    "Reset camera:  R\n"
    "Fly to point:  F"
)


def _make_hex_grid(pts: "np.ndarray", hex_blocks: list[list[int]]) -> "pv.UnstructuredGrid":
    n_verts = len(pts)
    valid = [b for b in hex_blocks if b and max(b) < n_verts]
    cells = []
    for block in valid:
        cells.extend([8] + block)
    cells_np = np.array(cells, dtype=np.int_)
    cell_types = np.full(len(valid), pv.CellType.HEXAHEDRON, dtype=np.uint8)
    return pv.UnstructuredGrid(cells_np, cell_types, pts)


class BlockMeshPanel(QWidget):
    """3-D viewer for blockMeshDict geometry (pyVista / VTK).

    The QtInteractor is created lazily on the first showEvent so VTK's native
    window is only initialised after the widget is embedded in the Qt hierarchy.

    WebEngine's GPU process (terminal) is forced to SwiftShader via the
    QTWEBENGINE_CHROMIUM_FLAGS env-var set in main.py, leaving the GPU free
    for VTK and preventing context conflicts.

    Emits ``vertices_changed(vertex_index, [x, y, z])`` when the user edits
    a coordinate cell in the vertices table.
    """

    vertices_changed = Signal(int, list)  # (vertex_index, [x, y, z])

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._data = None
        self._stl_meshes: list = []
        self._plotter: "QtInteractor | None" = None
        self._plotter_layout: QVBoxLayout | None = None
        self._vtx_table: QTableWidget | None = None
        self._selected_vertex: int | None = None
        self._root: FoamNode | None = None
        self._has_variables: bool = False
        self._preview_mode: bool = False
        self._preview_btn: "QPushButton | None" = None
        self._preview_banner: "QLabel | None" = None
        self._vtx_info_bar: "QWidget | None" = None

        if not _PYVISTA_OK:
            lbl = QLabel(
                "pyvista / pyvistaqt is not installed.\n"
                "Run:  pip install pyvista pyvistaqt"
            )
            lbl.setAlignment(Qt.AlignCenter)
            QVBoxLayout(self).addWidget(lbl)
            return

        self._build_controls()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_controls(self) -> None:
        row1, row2, refresh_btn, load_stl_act = self._build_geometry_toolbar()
        vtx_group = self._build_vertex_table()

        plotter_container = QWidget()
        self._plotter_layout = QVBoxLayout(plotter_container)
        self._plotter_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(plotter_container)
        splitter.addWidget(vtx_group)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([600, 280])

        hint_label = QLabel(_MOUSE_HINT)
        hint_label.setStyleSheet("color: #888888; font-size: 11px; font-style: italic;")
        hint_label.setToolTip(_MOUSE_HINT_TOOLTIP)

        self._preview_banner = QLabel(
            "Preview mode — changes shown in 3-D view only. "
            "Tree and file are not modified. Click Refresh to reset."
        )
        self._preview_banner.setStyleSheet(
            "background: #FFF3CD; color: #856404; "
            "padding: 3px 8px; border: 1px solid #FFEEBA; border-radius: 3px;"
        )
        self._preview_banner.setVisible(False)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(2)
        main_layout.addLayout(row1)
        main_layout.addLayout(row2)
        main_layout.addWidget(self._preview_banner)
        main_layout.addWidget(splitter, 1)
        main_layout.addWidget(hint_label)

        refresh_btn.clicked.connect(self._on_refresh)
        self._preview_btn.clicked.connect(self._on_preview_toggled)
        load_stl_act.triggered.connect(self._load_stl)
        self._clear_stl_act.triggered.connect(self._clear_stl)
        self._act_vtx_table.triggered.connect(lambda checked: vtx_group.setVisible(checked))
        self._vtx_table.itemSelectionChanged.connect(self._on_vertex_selected)
        self._vtx_table.cellChanged.connect(self._on_cell_changed)
        self._show_boundary.toggled.connect(self._render)
        for act in (self._show_vertices, self._show_labels,
                    self._show_edges, self._show_block_labels,
                    self._color_blocks, self._solid_blocks,
                    self._act_axes, self._act_grid, self._act_bounds):
            act.triggered.connect(self._render)
        self._label_font_size.valueChanged.connect(self._render)

    def _build_geometry_toolbar(self) -> tuple:
        """Build the two toolbar rows; set geometry-visibility action attrs."""
        vtx_menu = QMenu(self)
        self._show_vertices  = QAction("Vertices",       vtx_menu, checkable=True, checked=True)
        self._show_labels    = QAction("Vertex labels",  vtx_menu, checkable=True, checked=False)
        self._act_vtx_table  = QAction("Vertices table", vtx_menu, checkable=True, checked=True)
        vtx_menu.addAction(self._show_vertices)
        vtx_menu.addAction(self._show_labels)
        vtx_menu.addAction(self._act_vtx_table)

        vtx_btn = QToolButton()
        vtx_btn.setText("Vertices ▾")
        vtx_btn.setPopupMode(QToolButton.InstantPopup)
        vtx_btn.setMenu(vtx_menu)

        blk_menu = QMenu(self)
        self._show_edges        = QAction("Block edges",  blk_menu, checkable=True, checked=True)
        self._show_block_labels = QAction("Block labels", blk_menu, checkable=True, checked=False)
        self._color_blocks      = QAction("Color blocks", blk_menu, checkable=True, checked=False)
        self._solid_blocks      = QAction("Solid blocks", blk_menu, checkable=True, checked=False)
        blk_menu.addAction(self._show_edges)
        blk_menu.addAction(self._show_block_labels)
        blk_menu.addAction(self._color_blocks)
        blk_menu.addAction(self._solid_blocks)

        blk_btn = QToolButton()
        blk_btn.setText("Blocks ▾")
        blk_btn.setPopupMode(QToolButton.InstantPopup)
        blk_btn.setMenu(blk_menu)

        self._show_boundary = QCheckBox("Boundary faces")
        self._show_boundary.setChecked(True)

        scale_menu = QMenu(self)
        self._act_axes   = QAction("Axes",       scale_menu, checkable=True, checked=True)
        self._act_grid   = QAction("Grid",       scale_menu, checkable=True, checked=True)
        self._act_bounds = QAction("Dimensions", scale_menu, checkable=True, checked=True)
        scale_menu.addAction(self._act_axes)
        scale_menu.addAction(self._act_grid)
        scale_menu.addAction(self._act_bounds)

        scale_btn = QToolButton()
        scale_btn.setText("Scale ▾")
        scale_btn.setPopupMode(QToolButton.InstantPopup)
        scale_btn.setMenu(scale_menu)

        stl_menu = QMenu(self)
        load_stl_act = stl_menu.addAction("Load STL / OBJ…")
        self._clear_stl_act = stl_menu.addAction("Clear STL")
        self._clear_stl_act.setEnabled(False)

        stl_btn = QToolButton()
        stl_btn.setText("STL ▾")
        stl_btn.setPopupMode(QToolButton.InstantPopup)
        stl_btn.setMenu(stl_menu)

        refresh_btn = QPushButton("Refresh")

        row1 = QHBoxLayout()
        row1.addWidget(vtx_btn)
        row1.addWidget(blk_btn)
        row1.addWidget(self._show_boundary)
        row1.addSpacing(12)
        row1.addWidget(refresh_btn)
        row1.addWidget(stl_btn)
        row1.addStretch()

        self._label_font_size = QSpinBox()
        self._label_font_size.setRange(6, 32)
        self._label_font_size.setValue(10)
        self._label_font_size.setToolTip("Font size for vertex and block labels")
        self._label_font_size.setFixedWidth(52)

        row2 = QHBoxLayout()
        row2.addWidget(scale_btn)
        row2.addSpacing(16)
        row2.addWidget(QLabel("Label size:"))
        row2.addWidget(self._label_font_size)
        row2.addSpacing(16)
        row2.addWidget(QLabel("View:"))
        for _label, _fn, _kw in [
            ("+X", "view_yz",        {"negative": False}),
            ("-X", "view_yz",        {"negative": True}),
            ("+Y", "view_xz",        {"negative": False}),
            ("-Y", "view_xz",        {"negative": True}),
            ("+Z", "view_xy",        {"negative": False}),
            ("-Z", "view_xy",        {"negative": True}),
            ("Iso", "view_isometric", {}),
        ]:
            _btn = QPushButton(_label)
            _btn.setFixedWidth(36)
            _btn.clicked.connect(
                lambda _=False, f=_fn, k=_kw: self._set_view(f, **k)
            )
            row2.addWidget(_btn)
        row2.addStretch()

        return row1, row2, refresh_btn, load_stl_act

    def _build_vertex_table(self) -> "QGroupBox":
        """Build the vertex table with the variable-preview info bar; return the group box."""
        self._vtx_table = QTableWidget(0, 4)
        self._vtx_table.setHorizontalHeaderLabels(["#", "X", "Y", "Z"])
        self._vtx_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._vtx_table.setSelectionMode(QTableWidget.SingleSelection)
        self._vtx_table.setEditTriggers(QTableWidget.DoubleClicked)
        self._vtx_table.verticalHeader().hide()
        hdr = self._vtx_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        for col in (1, 2, 3):
            hdr.setSectionResizeMode(col, QHeaderView.Stretch)

        self._preview_btn = QPushButton("Preview")
        self._preview_btn.setCheckable(True)
        self._preview_btn.setToolTip(
            "Enable Preview mode: edit vertex coordinates in the table.\n"
            "Changes are shown in the 3-D view only — tree and file are not modified.\n"
            "Click Refresh to reset to the tree values."
        )

        vtx_vars_label = QLabel("⚙ Variable-based")
        vtx_vars_label.setStyleSheet(
            "color: #6B4F00; background: #FFF0B3; "
            "padding: 1px 6px; border-radius: 3px; font-size: 11px;"
        )

        self._vtx_info_bar = QWidget()
        info_row = QHBoxLayout(self._vtx_info_bar)
        info_row.setContentsMargins(0, 0, 0, 2)
        info_row.setSpacing(6)
        info_row.addWidget(vtx_vars_label)
        info_row.addWidget(self._preview_btn)
        info_row.addStretch()
        self._vtx_info_bar.setVisible(False)

        vtx_group = QGroupBox("Vertices")
        vtx_inner = QVBoxLayout(vtx_group)
        vtx_inner.setContentsMargins(2, 4, 2, 2)
        vtx_inner.setSpacing(2)
        vtx_inner.addWidget(self._vtx_info_bar)
        vtx_inner.addWidget(self._vtx_table)
        return vtx_group

    def _init_plotter(self) -> None:
        if self._plotter is not None or self._plotter_layout is None:
            return
        self._plotter = QtInteractor(self)
        self._plotter.set_background("white")
        self._plotter.setMinimumSize(0, 0)
        self._plotter_layout.addWidget(self._plotter)
        self._plotter.add_axes(xlabel="X", ylabel="Y", zlabel="Z", line_width=3)
        if self._data is not None:
            self._render()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not _PYVISTA_OK:
            return
        if self._plotter is None:
            self._init_plotter()
        else:
            self._plotter.render()

    # ── public API ────────────────────────────────────────────────────────────

    def update_block_mesh(self, path: str, root: FoamNode) -> None:
        if not _PYVISTA_OK:
            return
        from foam.block_mesh_extractor import extract_block_mesh_data
        self._root = root
        self._data = extract_block_mesh_data(root)
        self._preview_mode = False
        self._has_variables = self._vertices_have_variables()
        self._update_preview_ui()
        self._selected_vertex = None
        self._populate_vertex_table()
        if self._plotter is not None:
            self._render()

    def clear(self) -> None:
        self._data = None
        self._selected_vertex = None
        if self._vtx_table is not None:
            self._vtx_table.setRowCount(0)
        if self._plotter is not None:
            self._plotter.clear()
            self._plotter.render()

    def shutdown(self) -> None:
        """Close VTK render window before Qt tears down OpenGL contexts."""
        if self._plotter is not None:
            if self._plotter_layout is not None:
                self._plotter_layout.removeWidget(self._plotter)
            try:
                self._plotter.close()
            except Exception:
                pass
            self._plotter = None

    # ── vertices table ────────────────────────────────────────────────────────

    def _populate_vertex_table(self) -> None:
        if self._vtx_table is None:
            return
        verts = self._data.vertices if self._data else []
        n = len(verts)
        shown = min(n, _MAX_VERTEX_TABLE_ROWS)
        truncated = n > shown

        right = Qt.AlignRight | Qt.AlignVCenter
        ro_flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        editable = not self._has_variables or self._preview_mode
        rw_flags = (ro_flags | Qt.ItemIsEditable) if editable else ro_flags

        self._vtx_table.blockSignals(True)
        self._vtx_table.setRowCount(shown + (1 if truncated else 0))

        for i in range(shown):
            x, y, z = verts[i]
            for col, (text, flags) in enumerate((
                (str(i),      ro_flags),
                (f"{x:.6g}",  rw_flags),
                (f"{y:.6g}",  rw_flags),
                (f"{z:.6g}",  rw_flags),
            )):
                item = QTableWidgetItem(text)
                item.setTextAlignment(right)
                item.setFlags(flags)
                self._vtx_table.setItem(i, col, item)

        if truncated:
            msg = QTableWidgetItem(
                f"… {n} vertices total (table limited to {shown})"
            )
            msg.setFlags(Qt.ItemIsEnabled)
            self._vtx_table.setItem(shown, 0, msg)
            self._vtx_table.setSpan(shown, 0, 1, 4)

        self._vtx_table.blockSignals(False)

    def _on_vertex_selected(self) -> None:
        if self._vtx_table is None or self._data is None:
            return
        sel = self._vtx_table.selectedItems()
        if not sel:
            self._selected_vertex = None
        else:
            row = self._vtx_table.row(sel[0])
            n = len(self._data.vertices)
            self._selected_vertex = row if row < n else None
        if self._plotter is not None:
            self._render()

    def _on_cell_changed(self, row: int, col: int) -> None:
        if self._data is None or col == 0:
            return
        n = len(self._data.vertices)
        if row >= n:
            return
        item = self._vtx_table.item(row, col)
        if item is None:
            return
        try:
            new_val = float(item.text().strip())
        except ValueError:
            old_val = self._data.vertices[row][col - 1]
            self._vtx_table.blockSignals(True)
            item.setText(f"{old_val:.6g}")
            self._vtx_table.blockSignals(False)
            return
        self._data.vertices[row][col - 1] = new_val
        if self._preview_mode:
            if self._plotter is not None:
                self._render()
        else:
            self.vertices_changed.emit(row, list(self._data.vertices[row]))

    # ── preview mode ─────────────────────────────────────────────────────────

    def _vertices_have_variables(self) -> bool:
        if self._root is None:
            return False
        vtx_node = next(
            (c for c in self._root.children
             if c.name == "vertices" and c.node_type == "raw_list"),
            None,
        )
        return vtx_node is not None and "$" in str(vtx_node.value)

    def _update_preview_ui(self) -> None:
        if self._preview_btn is None:
            return
        self._vtx_info_bar.setVisible(self._has_variables)
        self._preview_btn.setChecked(self._preview_mode)
        if self._preview_banner is not None:
            self._preview_banner.setVisible(self._preview_mode)

    def _on_preview_toggled(self) -> None:
        self._preview_mode = self._preview_btn.isChecked()
        self._update_preview_ui()
        self._populate_vertex_table()

    def _on_refresh(self) -> None:
        if self._preview_mode and self._root is not None:
            from foam.block_mesh_extractor import extract_block_mesh_data
            self._data = extract_block_mesh_data(self._root)
            self._preview_mode = False
            self._update_preview_ui()
            self._selected_vertex = None
            self._populate_vertex_table()
        self._render()

    # ── rendering ─────────────────────────────────────────────────────────────

    def _set_view(self, fn: str, **kw) -> None:
        if self._plotter is None:
            return
        getattr(self._plotter, fn)(**kw)

    def _render(self) -> None:
        if self._plotter is None or self._data is None:
            return

        self._plotter.clear()
        verts = self._data.vertices
        if not verts:
            self._plotter.render()
            return

        pts = np.array(verts, dtype=float)

        if self._show_vertices.isChecked():
            self._plotter.add_mesh(
                pv.PolyData(pts),
                render_points_as_spheres=True,
                point_size=10,
                color="red",
            )

        # Selected vertex — always rendered when a table row is active
        if self._selected_vertex is not None and self._selected_vertex < len(verts):
            sel_pt = np.array([verts[self._selected_vertex]], dtype=float)
            self._plotter.add_mesh(
                pv.PolyData(sel_pt),
                render_points_as_spheres=True,
                point_size=18,
                color="cyan",
            )

        if self._show_labels.isChecked():
            self._plotter.add_point_labels(
                pts,
                [str(i) for i in range(len(verts))],
                font_size=self._label_font_size.value(),
                text_color="black",
                shape=None,
                show_points=False,
                always_visible=True,
            )

        if self._show_block_labels.isChecked() and self._data.hex_blocks:
            centroids = np.array(
                [pts[block].mean(axis=0) for block in self._data.hex_blocks]
            )
            self._plotter.add_point_labels(
                centroids,
                [str(i) for i in range(len(self._data.hex_blocks))],
                font_size=self._label_font_size.value(),
                text_color="darkblue",
                shape=None,
                show_points=False,
                always_visible=True,
            )

        if (self._show_edges.isChecked() or self._solid_blocks.isChecked()) and self._data.hex_blocks:
            grid = _make_hex_grid(pts, self._data.hex_blocks)
            if self._color_blocks.isChecked():
                grid.cell_data["block_id"] = np.arange(len(self._data.hex_blocks))
                color_kw: dict = {
                    "scalars": "block_id",
                    "cmap": "tab10",
                    "n_colors": len(self._data.hex_blocks),
                    "show_scalar_bar": False,
                }
            else:
                color_kw = {"color": "steelblue"}

            if self._show_edges.isChecked():
                self._plotter.add_mesh(grid, style="wireframe", line_width=2, **color_kw)
            if self._solid_blocks.isChecked():
                self._plotter.add_mesh(grid, style="surface", opacity=0.25, **color_kw)

        if self._show_boundary.isChecked():
            for _name, (patch_type, faces) in self._data.boundary_faces.items():
                if not faces:
                    continue
                conn: list[int] = []
                for face in faces:
                    conn += [len(face)] + face
                poly = pv.PolyData(pts, np.array(conn, dtype=np.int_))
                color = _PATCH_COLORS.get(patch_type, _DEFAULT_PATCH_COLOR)
                self._plotter.add_mesh(poly, color=color, opacity=0.6)

        for stl in self._stl_meshes:
            self._plotter.add_mesh(stl, color="lightgray", opacity=0.4)

        # ── scale / orientation indicators ───────────────────────────────────
        if self._act_axes.isChecked():
            self._plotter.show_axes()
        else:
            self._plotter.hide_axes()

        if self._act_grid.isChecked():
            self._plotter.show_grid(color="gray", font_size=8)

        if self._act_bounds.isChecked():
            self._plotter.add_bounding_box(color="gray", line_width=1)
            mins = pts.min(axis=0)
            maxs = pts.max(axis=0)
            dims = maxs - mins

            def _fmt(v: float) -> str:
                return f"{v:.4g}"

            lines = [
                f"X  {_fmt(mins[0])} → {_fmt(maxs[0])}  ({_fmt(dims[0])} m)",
                f"Y  {_fmt(mins[1])} → {_fmt(maxs[1])}  ({_fmt(dims[1])} m)",
                f"Z  {_fmt(mins[2])} → {_fmt(maxs[2])}  ({_fmt(dims[2])} m)",
            ]
            if self._data.scale != 1.0:
                lines.append(f"scale  {self._data.scale}")
            self._plotter.add_text(
                "\n".join(lines),
                position="upper_left",
                font_size=9,
                color="black",
                font="courier",
            )

        self._plotter.reset_camera()
        self._plotter.render()

    # ── STL loading ───────────────────────────────────────────────────────────

    def _load_stl(self) -> None:
        if not _PYVISTA_OK:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Load STL / OBJ", "",
            "STL / OBJ files (*.stl *.STL *.obj *.OBJ);;All files (*)",
        )
        if not path:
            return
        try:
            self._stl_meshes.append(pv.read(path))
            self._clear_stl_act.setEnabled(True)
            self._render()
        except Exception as e:
            QMessageBox.warning(self, "STL Load Error", str(e))

    def _clear_stl(self) -> None:
        self._stl_meshes.clear()
        self._clear_stl_act.setEnabled(False)
        self._render()
