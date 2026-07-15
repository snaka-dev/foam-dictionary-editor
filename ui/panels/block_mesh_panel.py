# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPixmap
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

from foam.block_mesh_extractor import extract_block_mesh_data
from foam.nodes import FoamNode
from foam.set_fields_extractor import SetFieldsShape, extract_set_fields_data
from foam.snappy_hex_mesh_extractor import extract_snappy_hex_mesh_data
from foam.topo_set_extractor import TopoShape, extract_topo_set_data
from ui.dialogs.export_stl_dialog import ExportStlDialog
from ui.widgets.flow_layout import FlowLayout

try:
    import pyvista as pv
    from pyvistaqt import QtInteractor

    _PYVISTA_OK = True
except ImportError:
    _PYVISTA_OK = False

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


from ui.panels.block_mesh_renderer import (
    _ACTION_COLORS,
    _SET_FIELDS_REGION_COLOR,
    _SNAPPY_CATEGORY_COLORS,
    BlockMeshRenderer,
    RenderSettings,
)


def _color_swatch(color_name: str, size: int = 12) -> QIcon:
    """A small filled square icon; stays vivid on disabled (greyed) menu rows."""
    pm = QPixmap(size, size)
    pm.fill(QColor(color_name))
    icon = QIcon(pm)
    icon.addPixmap(pm, QIcon.Disabled)
    return icon


class _StaysOpenMenu(QMenu):
    """A QMenu whose checkable items toggle without closing the popup.

    Qt closes a menu on any mouse-click activation, checkable or not, which
    makes multi-selecting a checklist-style menu tedious. Clicking a checkable,
    enabled item here toggles it and keeps the menu open; everything else
    (clicking outside, Escape, disabled rows) behaves like a stock QMenu.
    """

    def mouseReleaseEvent(self, event) -> None:
        action = self.activeAction()
        if action is not None and action.isCheckable() and action.isEnabled():
            action.trigger()
            return
        super().mouseReleaseEvent(event)


class _ShapeOverlayMenu:
    """One checkable shape-overlay menu (`topoSet ▾` / `snappyHexMesh ▾`).

    Owns the master toggle, the Show/Hide-all actions, a static colour legend,
    and the rebuildable per-shape (and optional location-point) toggles plus
    the "Non-geometric sources" submenu. ``on_changed`` runs after every
    visibility change so the owner can re-render.
    """

    def __init__(
        self,
        parent: QWidget,
        *,
        master_label: str,
        legend_title: str,
        legend: dict[str, str],
        shape_row: Callable[[Any], tuple[QIcon, str]],
        info_row: Callable[[Any], str],
        on_changed: Callable[[], None],
        location_row: Callable[[tuple], str] | None = None,
    ) -> None:
        self._shape_row = shape_row
        self._info_row = info_row
        self._location_row = location_row
        self._on_changed = on_changed

        self.shapes: list = []
        self.non_geometric: list = []
        self.locations: list = []
        self.shape_actions: list[QAction] = []
        self.location_actions: list[QAction] = []
        self.info_actions: list[QAction] = []
        self.info_menu: QMenu | None = None

        self.menu = _StaysOpenMenu(parent)
        self.master = QAction(master_label, self.menu, checkable=True, checked=True)
        self.menu.addAction(self.master)
        self.show_all = QAction("Show all shapes", self.menu)
        self.hide_all = QAction("Hide all shapes", self.menu)
        self.menu.addAction(self.show_all)
        self.menu.addAction(self.hide_all)
        self.menu.addSeparator()

        # Static legend mapping each row label to its overlay colour.
        legend_header = QAction(legend_title, self.menu)
        legend_header.setEnabled(False)
        self.menu.addAction(legend_header)
        self.legend_actions: list[QAction] = []
        for label, color in legend.items():
            act = QAction(_color_swatch(color), label, self.menu)
            act.setEnabled(False)
            self.menu.addAction(act)
            self.legend_actions.append(act)
        self.menu.addSeparator()

        self.master.toggled.connect(self._on_master_toggled)
        self.show_all.triggered.connect(lambda: self.set_all(True))
        self.hide_all.triggered.connect(lambda: self.set_all(False))

    def _on_master_toggled(self, on: bool) -> None:
        for act in (
            self.shape_actions + self.location_actions + [self.show_all, self.hide_all]
        ):
            act.setEnabled(on)
        self._on_changed()

    def set_all(self, checked: bool) -> None:
        """Check/uncheck every per-shape toggle with a single change callback."""
        for act in self.shape_actions + self.location_actions:
            act.blockSignals(True)
            act.setChecked(checked)
            act.blockSignals(False)
        self._on_changed()

    def rebuild(
        self, shapes: list, non_geometric: list, locations: list | None = None
    ) -> None:
        """Repopulate the per-shape toggles from freshly extracted data.

        The master action, Show/Hide all, legend, and separator persist; the
        per-shape/location toggles and the "Non-geometric sources" submenu are
        rebuilt so each renderable entry can be shown or hidden individually.
        Non-geometric sources are listed for awareness but never rendered;
        they are collapsed into a submenu so a source-rich dict (60+ actions)
        keeps the renderable toggles readable at the top level.
        """
        for act in self.shape_actions + self.location_actions:
            self.menu.removeAction(act)
            act.deleteLater()
        self.shape_actions = []
        self.location_actions = []
        self.info_actions = []
        if self.info_menu is not None:
            self.menu.removeAction(self.info_menu.menuAction())
            self.info_menu.deleteLater()
            self.info_menu = None

        self.shapes = list(shapes)
        self.non_geometric = list(non_geometric)
        self.locations = list(locations or [])

        master_on = self.master.isChecked()
        for shape in self.shapes:
            icon, text = self._shape_row(shape)
            act = QAction(icon, text, self.menu, checkable=True, checked=True)
            act.setEnabled(master_on)
            act.toggled.connect(self._on_changed)
            self.menu.addAction(act)
            self.shape_actions.append(act)

        if self._location_row is not None:
            for location in self.locations:
                act = QAction(
                    self._location_row(location), self.menu, checkable=True, checked=True
                )
                act.setEnabled(master_on)
                act.toggled.connect(self._on_changed)
                self.menu.addAction(act)
                self.location_actions.append(act)

        if self.non_geometric:
            self.info_menu = QMenu(
                f"Non-geometric sources ({len(self.non_geometric)})", self.menu
            )
            for shape in self.non_geometric:
                act = QAction(self._info_row(shape), self.info_menu)
                act.setEnabled(False)
                self.info_menu.addAction(act)
                self.info_actions.append(act)
            self.menu.addMenu(self.info_menu)

    def visible_shapes(self) -> list:
        """Return the shapes currently selected for display."""
        if not self.master.isChecked():
            return []
        return [s for s, a in zip(self.shapes, self.shape_actions) if a.isChecked()]

    def visible_locations(self) -> list:
        """Return the location points currently selected for display."""
        if not self.master.isChecked():
            return []
        return [p for p, a in zip(self.locations, self.location_actions) if a.isChecked()]


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
        self._renderer: "BlockMeshRenderer | None" = None
        self._plotter_layout: QVBoxLayout | None = None
        self._vtx_table: QTableWidget | None = None
        self._selected_vertex: int | None = None
        self._root: FoamNode | None = None
        self._has_variables: bool = False
        self._preview_mode: bool = False
        self._preview_btn: "QPushButton | None" = None
        self._preview_banner: "QLabel | None" = None
        self._vtx_info_bar: "QWidget | None" = None
        self._topo: "_ShapeOverlayMenu | None" = None
        self._snappy: "_ShapeOverlayMenu | None" = None
        self._set_fields: "_ShapeOverlayMenu | None" = None
        self._export_stl_act: "QAction | None" = None

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
        toolbar, refresh_btn, load_stl_act = self._build_geometry_toolbar()
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
        hint_label.setWordWrap(True)

        self._preview_banner = QLabel(
            "Preview mode — changes shown in 3-D view only. "
            "Tree and file are not modified. Click Refresh to reset."
        )
        self._preview_banner.setStyleSheet(
            "background: #FFF3CD; color: #856404; "
            "padding: 3px 8px; border: 1px solid #FFEEBA; border-radius: 3px;"
        )
        self._preview_banner.setWordWrap(True)
        self._preview_banner.setVisible(False)

        # Explicit floor so the side-by-side splitter handle stops at a
        # still-usable width instead of snapping the pane closed.
        self.setMinimumWidth(150)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(2)
        main_layout.addLayout(toolbar)
        main_layout.addWidget(self._preview_banner)
        main_layout.addWidget(splitter, 1)
        main_layout.addWidget(hint_label)

        refresh_btn.clicked.connect(self._on_refresh)
        self._preview_btn.clicked.connect(self._on_preview_toggled)
        load_stl_act.triggered.connect(self._load_stl)
        self._clear_stl_act.triggered.connect(self._clear_stl)
        self._export_stl_act.triggered.connect(self._export_shapes_stl)
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
        """Build the wrapping toolbar; set geometry-visibility action attrs.

        All controls live in a single FlowLayout that reflows onto more
        lines as the panel narrows, so the toolbar never dictates a large
        minimum panel width.
        """
        vtx_menu = _StaysOpenMenu(self)
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

        blk_menu = _StaysOpenMenu(self)
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

        self._topo = _ShapeOverlayMenu(
            self,
            master_label="Show topoSet geometry",
            legend_title="Action colours",
            legend={a: _ACTION_COLORS[a] for a in ("new", "add", "subtract", "subset", "invert")},
            shape_row=lambda s: (
                _color_swatch(_ACTION_COLORS.get(s.action, "gray")),
                f"{s.label or '(unnamed)'}  ·  {s.source}",
            ),
            info_row=lambda s: f"{s.label or '(unnamed)'}  ·  {s.source}  (no geometry)",
            on_changed=self._render,
        )

        topo_btn = QToolButton()
        topo_btn.setText("topoSet ▾")
        topo_btn.setPopupMode(QToolButton.InstantPopup)
        topo_btn.setMenu(self._topo.menu)
        topo_btn.setToolTip(
            "Show geometry sources from topoSetDict, or toggle individual shapes\n"
            "(load topoSetDict to populate)"
        )

        self._snappy = _ShapeOverlayMenu(
            self,
            master_label="Show snappyHexMesh geometry",
            legend_title="Category colours",
            legend={
                c: _SNAPPY_CATEGORY_COLORS[c] for c in ("surface", "region", "geometry")
            },
            shape_row=lambda s: (
                _color_swatch(_SNAPPY_CATEGORY_COLORS.get(s.category, "gray")),
                f"{s.name}  ·  {s.geo_type}  {s.level or s.mode or ''}".strip(),
            ),
            info_row=lambda s: f"{s.name}  ·  {s.geo_type}  (no geometry)",
            location_row=lambda location: f"📍 {location[1]}",
            on_changed=self._render,
        )

        snappy_btn = QToolButton()
        snappy_btn.setText("snappyHexMesh ▾")
        snappy_btn.setPopupMode(QToolButton.InstantPopup)
        snappy_btn.setMenu(self._snappy.menu)
        snappy_btn.setToolTip(
            "Show geometry/refinementSurfaces/refinementRegions from\n"
            "snappyHexMeshDict, or toggle individual shapes\n"
            "(load snappyHexMeshDict to populate)"
        )

        self._set_fields = _ShapeOverlayMenu(
            self,
            master_label="Show setFields regions",
            legend_title="Region colour",
            legend={"region": _SET_FIELDS_REGION_COLOR},
            shape_row=lambda s: (
                _color_swatch(_SET_FIELDS_REGION_COLOR),
                f"{s.label or '(no fieldValues)'}  ·  {s.source}",
            ),
            info_row=lambda s: f"{s.label or '(no fieldValues)'}  ·  {s.source}  (no geometry)",
            on_changed=self._render,
        )

        set_fields_btn = QToolButton()
        set_fields_btn.setText("setFields ▾")
        set_fields_btn.setPopupMode(QToolButton.InstantPopup)
        set_fields_btn.setMenu(self._set_fields.menu)
        set_fields_btn.setToolTip(
            "Show region sources from setFieldsDict, or toggle individual shapes\n"
            "(load setFieldsDict to populate). Regions larger than the block mesh\n"
            "are clipped in the view and marked '✂ clipped'."
        )

        scale_menu = _StaysOpenMenu(self)
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
        stl_menu.addSeparator()
        self._export_stl_act = stl_menu.addAction("Export Shapes as STL…")
        self._export_stl_act.setEnabled(False)
        self._export_stl_act.setToolTip(
            "Save topoSetDict / snappyHexMeshDict / setFieldsDict shapes as\n"
            "individual STL files (load one of those dicts to populate)"
        )

        stl_btn = QToolButton()
        stl_btn.setText("STL ▾")
        stl_btn.setPopupMode(QToolButton.InstantPopup)
        stl_btn.setMenu(stl_menu)

        refresh_btn = QPushButton("Refresh")

        self._label_font_size = QSpinBox()
        self._label_font_size.setRange(6, 32)
        self._label_font_size.setValue(10)
        self._label_font_size.setToolTip("Font size for vertex and block labels")
        self._label_font_size.setFixedWidth(52)

        # "Label size:" and its spinbox wrap as one unit.
        label_size_group = QWidget()
        label_size_layout = QHBoxLayout(label_size_group)
        label_size_layout.setContentsMargins(0, 0, 0, 0)
        label_size_layout.setSpacing(4)
        label_size_layout.addWidget(QLabel("Label size:"))
        label_size_layout.addWidget(self._label_font_size)

        toolbar = FlowLayout()
        toolbar.addWidget(vtx_btn)
        toolbar.addWidget(blk_btn)
        toolbar.addWidget(self._show_boundary)
        toolbar.addWidget(topo_btn)
        toolbar.addWidget(snappy_btn)
        toolbar.addWidget(set_fields_btn)
        toolbar.addWidget(refresh_btn)
        toolbar.addWidget(stl_btn)
        toolbar.addWidget(scale_btn)
        toolbar.addWidget(label_size_group)
        toolbar.addWidget(QLabel("View:"))
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
            toolbar.addWidget(_btn)

        return toolbar, refresh_btn, load_stl_act

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

    def init_plotter(self) -> None:
        if self._plotter is not None or self._plotter_layout is None:
            return
        self._plotter = QtInteractor(self)
        self._plotter.set_background("white")
        self._plotter.setMinimumSize(0, 0)
        self._plotter_layout.addWidget(self._plotter)
        self._plotter.add_axes(xlabel="X", ylabel="Y", zlabel="Z", line_width=3)
        self._renderer = BlockMeshRenderer(self._plotter)
        if self._data is not None:
            self._render()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not _PYVISTA_OK:
            return
        if self._plotter is None:
            self.init_plotter()
        else:
            self._plotter.render()

    # ── public API ────────────────────────────────────────────────────────────

    def update_block_mesh(self, path: str, root: FoamNode) -> None:
        if not _PYVISTA_OK:
            return
        self._root = root
        self._data = extract_block_mesh_data(root)
        self._preview_mode = False
        self._has_variables = self._vertices_have_variables()
        self._update_preview_ui()
        self._selected_vertex = None
        self._populate_vertex_table()
        if self._plotter is not None:
            self._render()

    def update_topo_set(self, path: str, root: FoamNode) -> None:
        if not _PYVISTA_OK:
            return
        data = extract_topo_set_data(root)
        self._topo.rebuild(data.shapes, data.non_geometric)
        self._update_export_stl_enabled()
        if self._plotter is not None:
            self._render()

    def update_snappy_hex_mesh(self, path: str, root: FoamNode) -> None:
        if not _PYVISTA_OK:
            return
        case_dir = str(Path(path).parent.parent)
        data = extract_snappy_hex_mesh_data(root, case_dir)
        self._snappy.rebuild(data.shapes, data.non_geometric, data.location_points)
        self._update_export_stl_enabled()
        if self._plotter is not None:
            self._render()

    def update_set_fields(self, path: str, root: FoamNode) -> None:
        if not _PYVISTA_OK:
            return
        data = extract_set_fields_data(root)
        self._set_fields.rebuild(data.shapes, data.non_geometric)
        self._update_export_stl_enabled()
        if self._plotter is not None:
            self._render()

    def clear(self) -> None:
        self._data = None
        if self._topo is not None:
            self._topo.rebuild([], [])
        if self._snappy is not None:
            self._snappy.rebuild([], [], [])
        if self._set_fields is not None:
            self._set_fields.rebuild([], [])
        self._update_export_stl_enabled()
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
            self._data = extract_block_mesh_data(self._root)
            self._preview_mode = False
            self._update_preview_ui()
            self._selected_vertex = None
            self._populate_vertex_table()
        self._render()

    # ── rendering ─────────────────────────────────────────────────────────────

    def _make_settings(self) -> RenderSettings:
        return RenderSettings(
            show_vertices=self._show_vertices.isChecked(),
            show_labels=self._show_labels.isChecked(),
            show_edges=self._show_edges.isChecked(),
            show_block_labels=self._show_block_labels.isChecked(),
            color_blocks=self._color_blocks.isChecked(),
            solid_blocks=self._solid_blocks.isChecked(),
            show_boundary=self._show_boundary.isChecked(),
            show_axes=self._act_axes.isChecked(),
            show_grid=self._act_grid.isChecked(),
            show_bounds=self._act_bounds.isChecked(),
            label_font_size=self._label_font_size.value(),
            selected_vertex=self._selected_vertex,
        )

    def _set_view(self, fn: str, **kw) -> None:
        if self._renderer is None:
            return
        self._renderer.set_view(fn, **kw)

    def _render(self) -> None:
        if self._renderer is None:
            return
        has_overlay = (
            self._topo.shapes or self._snappy.shapes or self._snappy.locations
            or self._set_fields.shapes
        )
        if self._data is None and not has_overlay:
            return
        self._renderer.render(
            self._data,
            self._make_settings(),
            self._stl_meshes,
            self._topo.visible_shapes(),
            self._snappy.visible_shapes(),
            self._snappy.visible_locations(),
            self._set_fields.visible_shapes(),
        )

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

    # ── STL export ────────────────────────────────────────────────────────────

    def _exportable_topo_shapes(self) -> list[TopoShape]:
        """topoSet shapes that produce a meaningful STL surface.

        Point markers have no surface and a planeToFaceZone disc's extent is
        display-only, so neither is offered for export.
        """
        return [
            s for s in self._topo.shapes
            if not ({"points", "planePoint"} & s.geometry.keys())
        ]

    def _exportable_set_fields_shapes(self) -> list[SetFieldsShape]:
        """setFields regions that produce a meaningful STL surface (unclipped)."""
        return [
            s for s in self._set_fields.shapes
            if not ({"points", "planePoint"} & s.geometry.keys())
        ]

    def _update_export_stl_enabled(self) -> None:
        if self._export_stl_act is not None:
            self._export_stl_act.setEnabled(
                bool(
                    self._exportable_topo_shapes()
                    or self._snappy.shapes
                    or self._exportable_set_fields_shapes()
                )
            )

    def _export_shapes_stl(self) -> None:
        exportable = self._exportable_topo_shapes()
        set_fields_exportable = self._exportable_set_fields_shapes()
        if not _PYVISTA_OK or not (
            exportable or self._snappy.shapes or set_fields_exportable
        ):
            return
        topo_visible = {id(s) for s in self._topo.visible_shapes()}
        snappy_visible = {id(s) for s in self._snappy.visible_shapes()}
        set_fields_visible = {id(s) for s in self._set_fields.visible_shapes()}
        dlg = ExportStlDialog(
            exportable, topo_visible,
            self._snappy.shapes, snappy_visible,
            self,
            set_fields_shapes=set_fields_exportable,
            set_fields_visible=set_fields_visible,
        )
        dlg.exec()
