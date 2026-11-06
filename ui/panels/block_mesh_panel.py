# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import dataclasses
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QKeySequence
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

from foam.block_mesh_extractor import BlockMeshData, extract_block_mesh_data
from foam.nodes import FoamNode
from foam.sampling_extractor import SamplingData, extract_sampling_data
from foam.set_fields_extractor import SetFieldsData, SetFieldsShape, extract_set_fields_data
from foam.snappy_hex_mesh_extractor import SnappyHexMeshData, extract_snappy_hex_mesh_data
from foam.topo_set_extractor import TopoSetData, TopoShape, extract_topo_set_data
from i18n import tr
from ui.dialogs.export_stl_dialog import ExportStlDialog
from ui.fonts import button_pixel_width, small_font
from ui.panels._shape_overlay_menu import (
    _color_swatch,
    _exportable,
    _menu_button,
    _ShapeOverlayMenu,
    _StaysOpenMenu,
)
from ui.panels._view_image_export import save_view_image
from ui.panels.block_mesh_renderer import (
    _ACTION_COLORS,
    _SAMPLING_COLOR,
    _SET_FIELDS_REGION_COLOR,
    _SNAPPY_CATEGORY_COLORS,
    _SURFACE_COLORS,
    BlockMeshRenderer,
    LoadedSurface,
    RenderSettings,
)
from ui.panels.shape_mesh import read_surface_mesh
from ui.theme import colors
from ui.widgets.flow_layout import FlowLayout
from ui.window_state import BlockMeshViewState, decode_qt_state, encode_qt_state

try:
    from pyvistaqt import QtInteractor

    _PYVISTA_OK = True
except ImportError:
    _PYVISTA_OK = False

_MAX_VERTEX_TABLE_ROWS = 500

# Floors, not caps: FlowLayout geometries every item at its sizeHint()
# verbatim (ui/widgets/flow_layout.py:85-95), so a control wider than these
# simply takes the room it needs and the row wraps sooner. These are the
# compact figures chosen when the style/font combination left room to spare;
# see ui/fonts.py's button_pixel_width for why they can no longer be a cap.
_LABEL_SPIN_MIN_WIDTH = 52
_VIEW_BUTTON_MIN_WIDTH = 36

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




@dataclasses.dataclass
class GeometryToolbar:
    """Return value of BlockMeshPanel._build_geometry_toolbar()."""

    toolbar: FlowLayout
    refresh_btn: QPushButton
    load_stl_act: QAction


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
    image_saved = Signal(str)  # absolute path of a saved 3-D view image

    # Stable names for the view toggles and overlay menus, so a saved view state
    # is readable and survives renaming the widgets behind them.
    VIEW_TOGGLES = {
        "vertices": "_show_vertices",
        "vertex_labels": "_show_labels",
        "vertex_table": "_act_vtx_table",
        "block_edges": "_show_edges",
        "block_labels": "_show_block_labels",
        "color_blocks": "_color_blocks",
        "solid_blocks": "_solid_blocks",
        "boundary_faces": "_show_boundary",
        "axes": "_act_axes",
        "grid": "_act_grid",
        "dimensions": "_act_bounds",
    }
    VIEW_OVERLAYS = {
        "topo_set": "_topo",
        "snappy_hex_mesh": "_snappy",
        "set_fields": "_set_fields",
        "sampling": "_sampling",
        "loaded_surfaces": "_loaded_surfaces",
    }

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._data: BlockMeshData | None = None
        self._surfaces: list[LoadedSurface] = []
        # Whether the last render drew anything; lets _render() tell "nothing to
        # draw, nothing drawn" from "nothing to draw, stale actors to clear".
        self._scene_drawn: bool = False
        self._plotter: QtInteractor | None = None
        self._renderer: BlockMeshRenderer | None = None
        self._plotter_layout: QVBoxLayout | None = None
        self._vtx_table: QTableWidget | None = None
        self._selected_vertex: int | None = None
        self._selected_block: int | None = None
        self._root: FoamNode | None = None
        self._has_variables: bool = False
        self._preview_mode: bool = False
        self._preview_btn: QPushButton | None = None
        self._preview_banner: QLabel | None = None
        self._vtx_info_bar: QWidget | None = None
        self._topo: _ShapeOverlayMenu | None = None
        self._snappy: _ShapeOverlayMenu | None = None
        self._set_fields: _ShapeOverlayMenu | None = None
        self._sampling: _ShapeOverlayMenu | None = None
        self._loaded_surfaces: _ShapeOverlayMenu | None = None
        # Every overlay's shapes are kept per source file and the menu shows their union.
        # Sampling needed this first -- controlDict's functions{} plus a standalone
        # system/sample are two files feeding one overlay -- but the other three need it
        # too: a case can hold `topoSetDict-slices` and `topoSetDict-background` side by side,
        # and rebuilding from just the file being viewed made whichever was opened last
        # erase the other. Keyed by full path, not basename, so two files sharing a
        # basename in different directories do not overwrite each other.
        self._sampling_by_file: dict[str, SamplingData] = {}
        self._topo_by_file: dict[str, TopoSetData] = {}
        self._snappy_by_file: dict[str, SnappyHexMeshData] = {}
        self._set_fields_by_file: dict[str, SetFieldsData] = {}
        self._export_stl_act: QAction | None = None
        self._clear_stl_act: QAction | None = None
        self._view_splitter: QSplitter | None = None
        self._vtx_group: QGroupBox | None = None
        self._case_dir: str | None = None
        # Public: MainWindow adds this same QAction to the View menu, so the
        # toolbar button and the menu item can never drift apart. Stays None
        # when pyvista is missing, since _build_controls() never runs then.
        self.save_image_action: QAction | None = None

        if not _PYVISTA_OK:
            lbl = QLabel(
                tr("pyvista / pyvistaqt is not installed.\nRun:  pip install pyvista pyvistaqt")
            )
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            QVBoxLayout(self).addWidget(lbl)
            return

        self._build_controls()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_controls(self) -> None:
        geometry_toolbar = self._build_geometry_toolbar()
        toolbar = geometry_toolbar.toolbar
        refresh_btn = geometry_toolbar.refresh_btn
        load_stl_act = geometry_toolbar.load_stl_act
        vtx_group = self._build_vertex_table()

        plotter_container = QWidget()
        self._plotter_layout = QVBoxLayout(plotter_container)
        self._plotter_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(plotter_container)
        splitter.addWidget(vtx_group)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([600, 280])
        self._view_splitter = splitter
        self._vtx_group = vtx_group

        # _MOUSE_HINT/_MOUSE_HINT_TOOLTIP are module constants (their own English
        # translation key), so tr() is applied here rather than at definition —
        # the module is imported before main.py's set_language() call, and a
        # module-level tr() would freeze the text as English forever.
        hint_label = QLabel(tr(_MOUSE_HINT))
        hint_label.setFont(small_font(italic=True))
        hint_label.setStyleSheet(f"color: {colors().hint_text};")
        hint_label.setToolTip(tr(_MOUSE_HINT_TOOLTIP))
        hint_label.setWordWrap(True)

        self._preview_banner = QLabel(
            tr(
                "Preview mode — changes shown in 3-D view only. "
                "Tree and file are not modified. Click Refresh to reset."
            )
        )
        self._preview_banner.setStyleSheet(
            f"background: {colors().banner_bg}; color: {colors().banner_fg}; "
            f"padding: 3px 8px; border: 1px solid {colors().banner_border}; border-radius: 3px;"
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

        # Built above by _build_geometry_toolbar()/_build_vertex_table(), just called.
        assert self._preview_btn is not None
        assert self._export_stl_act is not None
        assert self._clear_stl_act is not None
        assert self._vtx_table is not None
        assert self.save_image_action is not None

        refresh_btn.clicked.connect(self._on_refresh)
        self._preview_btn.clicked.connect(self._on_preview_toggled)
        load_stl_act.triggered.connect(self._load_stl)
        self._clear_stl_act.triggered.connect(self._clear_stl)
        self._export_stl_act.triggered.connect(self._export_shapes_stl)
        self.save_image_action.triggered.connect(self._save_view_image)
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

    def _build_geometry_toolbar(self) -> GeometryToolbar:
        """Build the wrapping toolbar; set geometry-visibility action attrs.

        All controls live in a single FlowLayout that reflows onto more
        lines as the panel narrows, so the toolbar never dictates a large
        minimum panel width. Split by section below: vertex/block menus,
        the per-source overlay menus, the STL menu, the scale/label
        controls, and finally the view buttons.
        """
        vtx_btn, blk_btn = self._build_vertex_and_block_menus()
        topo_btn, snappy_btn, set_fields_btn, sampling_btn = self._build_overlay_menus()
        refresh_btn = QPushButton(tr("Refresh"))
        stl_btn, load_stl_act = self._build_stl_menu()
        save_image_btn = self._build_save_image_button()
        scale_btn, label_size_group = self._build_scale_and_label_controls()

        toolbar = FlowLayout()
        toolbar.addWidget(vtx_btn)
        toolbar.addWidget(blk_btn)
        toolbar.addWidget(self._show_boundary)
        toolbar.addWidget(topo_btn)
        toolbar.addWidget(snappy_btn)
        toolbar.addWidget(set_fields_btn)
        toolbar.addWidget(sampling_btn)
        toolbar.addWidget(refresh_btn)
        toolbar.addWidget(stl_btn)
        toolbar.addWidget(save_image_btn)
        toolbar.addWidget(scale_btn)
        toolbar.addWidget(label_size_group)
        toolbar.addWidget(QLabel(tr("View:")))
        self._build_view_buttons(toolbar)

        return GeometryToolbar(toolbar=toolbar, refresh_btn=refresh_btn, load_stl_act=load_stl_act)

    def _build_vertex_and_block_menus(self) -> tuple[QToolButton, QToolButton]:
        """Build the Vertices ▾ / Blocks ▾ menus and the boundary-faces checkbox."""
        vtx_menu = _StaysOpenMenu(self)
        self._show_vertices  = QAction(tr("Vertices"),       vtx_menu, checkable=True, checked=True)
        self._show_labels    = QAction(tr("Vertex labels"),  vtx_menu, checkable=True, checked=False)
        self._act_vtx_table  = QAction(tr("Vertices table"), vtx_menu, checkable=True, checked=True)
        vtx_menu.addAction(self._show_vertices)
        vtx_menu.addAction(self._show_labels)
        vtx_menu.addAction(self._act_vtx_table)

        vtx_btn = _menu_button(tr("Vertices"), vtx_menu)

        blk_menu = _StaysOpenMenu(self)
        self._show_edges        = QAction(tr("Block edges"),  blk_menu, checkable=True, checked=True)
        self._show_block_labels = QAction(tr("Block labels"), blk_menu, checkable=True, checked=False)
        self._color_blocks      = QAction(tr("Color blocks"), blk_menu, checkable=True, checked=False)
        self._solid_blocks      = QAction(tr("Solid blocks"), blk_menu, checkable=True, checked=False)
        blk_menu.addAction(self._show_edges)
        blk_menu.addAction(self._show_block_labels)
        blk_menu.addAction(self._color_blocks)
        blk_menu.addAction(self._solid_blocks)

        blk_btn = _menu_button(tr("Blocks"), blk_menu)

        self._show_boundary = QCheckBox(tr("Boundary faces"))
        self._show_boundary.setChecked(True)

        return vtx_btn, blk_btn

    def _build_overlay_menus(self) -> tuple[QToolButton, QToolButton, QToolButton, QToolButton]:
        """Build the topoSet ▾ / snappyHexMesh ▾ / setFields ▾ / sample ▾ menus.

        One _ShapeOverlayMenu construction per source, kept as five
        straight-line blocks rather than a data table: they share only the
        constructor, not enough fields in common to be worth one (see
        DEVELOPER.md's "Update candidates").
        """
        # shape_row/info_row lambdas mix static prose ("(unnamed)", "(no geometry)")
        # with data straight out of the user's dictionary (s.label, s.kind); only
        # the static parts are translated. The action/category words themselves
        # ("new"/"add"/…, "surface"/"region"/"geometry") are OpenFOAM vocabulary —
        # the literal keywords in the dictionary file being viewed — and are
        # deliberately left untranslated so the legend still matches the file.
        self._topo = _ShapeOverlayMenu(
            self,
            master_label=tr("Show topoSet geometry"),
            legend_title=tr("Action colours"),
            legend={a: _ACTION_COLORS[a] for a in ("new", "add", "subtract", "subset", "invert")},
            shape_row=lambda s: (
                _color_swatch(_ACTION_COLORS.get(s.action, "gray")),
                f"{s.label or tr('(unnamed)')}  ·  {s.kind}",
            ),
            info_row=lambda s: f"{s.label or tr('(unnamed)')}  ·  {s.kind}  {tr('(no geometry)')}",
            on_changed=self._render,
        )

        topo_btn = _menu_button(
            tr("topoSet"),
            self._topo.menu,
            tr(
                "Show geometry sources from topoSetDict, or toggle individual shapes\n"
                "(load topoSetDict to populate)"
            ),
        )

        self._snappy = _ShapeOverlayMenu(
            self,
            master_label=tr("Show snappyHexMesh geometry"),
            legend_title=tr("Category colours"),
            legend={
                c: _SNAPPY_CATEGORY_COLORS[c] for c in ("surface", "region", "geometry")
            },
            shape_row=lambda s: (
                _color_swatch(_SNAPPY_CATEGORY_COLORS.get(s.category, "gray")),
                f"{s.label}  ·  {s.kind}  {s.level or s.mode or ''}".strip(),
            ),
            info_row=lambda s: f"{s.label}  ·  {s.kind}  {tr('(no geometry)')}",
            location_row=lambda location: f"📍 {location[1]}",
            on_changed=self._render,
        )

        snappy_btn = _menu_button(
            tr("snappyHexMesh"),
            self._snappy.menu,
            tr(
                "Show geometry/refinementSurfaces/refinementRegions from\n"
                "snappyHexMeshDict, or toggle individual shapes\n"
                "(load snappyHexMeshDict to populate)"
            ),
        )

        self._set_fields = _ShapeOverlayMenu(
            self,
            master_label=tr("Show setFields regions"),
            legend_title=tr("Region colour"),
            legend={"region": _SET_FIELDS_REGION_COLOR},
            shape_row=lambda s: (
                _color_swatch(_SET_FIELDS_REGION_COLOR),
                f"{s.label or tr('(no fieldValues)')}  ·  {s.kind}",
            ),
            info_row=lambda s: f"{s.label or tr('(no fieldValues)')}  ·  {s.kind}  {tr('(no geometry)')}",
            on_changed=self._render,
        )

        set_fields_btn = _menu_button(
            tr("setFields"),
            self._set_fields.menu,
            tr(
                "Show region sources from setFieldsDict, or toggle individual shapes\n"
                "(load setFieldsDict to populate). Regions larger than the block mesh\n"
                "are clipped in the view and marked '(clipped)'."
            ),
        )

        self._sampling = _ShapeOverlayMenu(
            self,
            master_label=tr("Show sampling geometry"),
            legend_title=tr("Sampling colour"),
            legend={tr("probes / lines / planes"): _SAMPLING_COLOR},
            shape_row=lambda s: (
                _color_swatch(_SAMPLING_COLOR),
                f"{s.label or tr('(unnamed)')}  ·  {s.kind}",
            ),
            info_row=lambda s: (
                f"{s.label or tr('(unnamed)')}  ·  {s.kind}"
                f"  {tr('(no geometry)')}"
            ),
            on_changed=self._render,
        )

        sampling_btn = _menu_button(
            tr("sample"),
            self._sampling.menu,
            tr(
                "Show sampling geometry — probes, sample lines, sample planes — from\n"
                "controlDict's functions {} block or a standalone sampling dict\n"
                "(sample / probes / surfaces / singleGraph), or toggle individual\n"
                "shapes (load one of those files to populate)"
            ),
        )

        return topo_btn, snappy_btn, set_fields_btn, sampling_btn

    def _build_stl_menu(self) -> tuple[QToolButton, QAction]:
        """Build the STL ▾ menu: load/unload/clear/export plus loaded-surface rows."""
        stl_menu = _StaysOpenMenu(self)
        load_stl_act = stl_menu.addAction(tr("Load STL / OBJ…"))
        self._unload_stl_menu = QMenu(tr("Unload"), stl_menu)
        self._unload_stl_menu.setEnabled(False)
        stl_menu.addMenu(self._unload_stl_menu)
        self._clear_stl_act = stl_menu.addAction(tr("Clear STL"))
        self._clear_stl_act.setEnabled(False)
        stl_menu.addSeparator()
        self._export_stl_act = stl_menu.addAction(tr("Export Shapes as STL…"))
        self._export_stl_act.setEnabled(False)
        self._export_stl_act.setToolTip(
            tr(
                "Save topoSetDict / snappyHexMeshDict / setFieldsDict shapes as\n"
                "individual STL files (load one of those dicts to populate)"
            )
        )
        stl_menu.addSeparator()

        # Adopts the menu built above so Load/Unload/Clear/Export stay at the
        # top and the per-file rows are appended underneath. Each row carries
        # its own colour swatch, so there is no static legend to show.
        self._loaded_surfaces = _ShapeOverlayMenu(
            self,
            master_label=tr("Show loaded surfaces"),
            legend_title="",
            legend={},
            shape_row=lambda s: (_color_swatch(s.color), f"{s.label}  ·  {s.kind}"),
            info_row=lambda s: s.label,
            on_changed=self._render,
            menu=stl_menu,
            item_noun="surfaces",
        )

        stl_btn = _menu_button(
            tr("STL"),
            stl_menu,
            tr(
                "Load STL/OBJ surfaces as a reference overlay, toggle or unload\n"
                "individual ones, or export dictionary shapes as STL files"
            ),
        )

        return stl_btn, load_stl_act

    def _build_save_image_button(self) -> QToolButton:
        """Build the Save Image button; set self.save_image_action.

        One QAction drives both this button and the View-menu item MainWindow
        adds, so their label, tooltip, shortcut and enabled state stay in sync
        (setDefaultAction, rather than two objects kept aligned by hand).

        It starts disabled: the plotter is created lazily on the first
        showEvent, and there is no view to save before that happens.

        The label is short because it has to sit in the wrapping toolbar
        beside Refresh and STL ▾; the tooltip carries the full sentence, and
        in the View menu the item follows the BlockMesh 3-D Panel toggle,
        which supplies the context the label leaves out.
        """
        self.save_image_action = QAction(tr("Save Image…"), self)
        self.save_image_action.setToolTip(
            tr("Save the 3-D view as an image file, exactly as shown")
        )
        self.save_image_action.setShortcut(QKeySequence("Ctrl+Shift+I"))
        self.save_image_action.setEnabled(False)
        btn = QToolButton(self)
        btn.setDefaultAction(self.save_image_action)
        return btn

    def _build_scale_and_label_controls(self) -> tuple[QToolButton, QWidget]:
        """Build the Scale ▾ menu (axes/grid/dimensions) and the label-size spinbox."""
        scale_menu = _StaysOpenMenu(self)
        self._act_axes   = QAction(tr("Axes"),       scale_menu, checkable=True, checked=True)
        self._act_grid   = QAction(tr("Grid"),       scale_menu, checkable=True, checked=True)
        self._act_bounds = QAction(tr("Dimensions"), scale_menu, checkable=True, checked=True)
        scale_menu.addAction(self._act_axes)
        scale_menu.addAction(self._act_grid)
        scale_menu.addAction(self._act_bounds)

        scale_btn = _menu_button(tr("Scale"), scale_menu)

        self._label_font_size = QSpinBox()
        self._label_font_size.setRange(6, 32)
        self._label_font_size.setValue(10)
        self._label_font_size.setToolTip(tr("Font size for vertex and block labels"))
        # The spin box asks the style for its own hint (CT_SpinBox includes
        # the up/down button metrics), so it needs no helper of its own.
        self._label_font_size.setFixedWidth(
            max(_LABEL_SPIN_MIN_WIDTH, self._label_font_size.sizeHint().width())
        )

        # "Label size:" and its spinbox wrap as one unit.
        label_size_group = QWidget()
        label_size_layout = QHBoxLayout(label_size_group)
        label_size_layout.setContentsMargins(0, 0, 0, 0)
        label_size_layout.setSpacing(4)
        label_size_layout.addWidget(QLabel(tr("Label size:")))
        label_size_layout.addWidget(self._label_font_size)

        return scale_btn, label_size_group

    def _build_view_buttons(self, toolbar: FlowLayout) -> None:
        """Append the +X/-X/…/Iso camera-view buttons to *toolbar*.

        Axis symbols and "Iso" are identical in Japanese, so these are
        deliberately not tr()-wrapped (see the axis-label entries in
        tests/ui/test_translatable_strings.py's _ALLOWED).
        """
        views = [
            ("+X", "view_yz",        {"negative": False}),
            ("-X", "view_yz",        {"negative": True}),
            ("+Y", "view_xz",        {"negative": False}),
            ("-Y", "view_xz",        {"negative": True}),
            ("+Z", "view_xy",        {"negative": False}),
            ("-Z", "view_xy",        {"negative": True}),
            ("Iso", "view_isometric", {}),
        ]
        # One width for the whole row, not per button: per-button sizing goes
        # ragged as the font grows ("+X" wants less room than "Iso" does).
        width = max(_VIEW_BUTTON_MIN_WIDTH, max(button_pixel_width(lbl) for lbl, _, _ in views))
        for _label, _fn, _kw in views:
            _btn = QPushButton(_label)
            _btn.setFixedWidth(width)
            _btn.clicked.connect(
                lambda _=False, f=_fn, k=_kw: self._set_view(f, **k)
            )
            toolbar.addWidget(_btn)

    def _build_vertex_table(self) -> QGroupBox:
        """Build the vertex table with the variable-preview info bar; return the group box."""
        self._vtx_table = QTableWidget(0, 4)
        # "#"/"X"/"Y"/"Z" are coordinate/index headers, identical in Japanese.
        self._vtx_table.setHorizontalHeaderLabels(["#", "X", "Y", "Z"])
        self._vtx_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._vtx_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._vtx_table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
        self._vtx_table.verticalHeader().hide()
        hdr = self._vtx_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        for col in (1, 2, 3):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)

        self._preview_btn = QPushButton(tr("Preview"))
        self._preview_btn.setCheckable(True)
        self._preview_btn.setToolTip(
            tr(
                "Enable Preview mode: edit vertex coordinates in the table.\n"
                "Changes are shown in the 3-D view only — tree and file are not modified.\n"
                "Click Refresh to reset to the tree values."
            )
        )

        vtx_vars_label = QLabel(tr("⚙ Variable-based"))
        vtx_vars_label.setFont(small_font())
        vtx_vars_label.setStyleSheet(
            f"color: {colors().banner_fg}; background: {colors().banner_bg}; "
            "padding: 1px 6px; border-radius: 3px;"
        )

        self._vtx_info_bar = QWidget()
        info_row = QHBoxLayout(self._vtx_info_bar)
        info_row.setContentsMargins(0, 0, 0, 2)
        info_row.setSpacing(6)
        info_row.addWidget(vtx_vars_label)
        info_row.addWidget(self._preview_btn)
        info_row.addStretch()
        self._vtx_info_bar.setVisible(False)

        vtx_group = QGroupBox(tr("Vertices"))
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
        self._plotter.set_background(colors().viewport_bg)
        self._plotter.setMinimumSize(0, 0)
        self._plotter_layout.addWidget(self._plotter)
        # ``color`` is the label colour only; the x/y/z arrows keep their
        # conventional red/green/blue. Without it the letters stay PyVista's
        # default black and vanish against the dark theme's viewport.
        self._plotter.add_axes(
            xlabel="X",
            ylabel="Y",
            zlabel="Z",
            line_width=3,
            color=colors().viewport_text,
        )
        self._renderer = BlockMeshRenderer(self._plotter)
        if self.save_image_action is not None:
            self.save_image_action.setEnabled(True)
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
        self._selected_block = None
        self._populate_vertex_table()
        if self._plotter is not None:
            self._render()

    def set_selected_block(self, index: int | None) -> None:
        """Highlight one block, by its index in `blocks ( … )`.

        The tree's "block N" rows are numbered by position and so are the
        viewer's centroid labels, both straight off the parsed order, so the
        caller's row index needs no translation. Out-of-range values are the
        renderer's problem, not this method's -- the panel may be holding a
        different file's mesh than the tree is showing.
        """
        if index == self._selected_block:
            return
        self._selected_block = index
        if self._plotter is not None:
            self._render()

    def view_state(self) -> BlockMeshViewState | None:
        """Read the current view settings back (see ui/window_state.py).

        None when pyVista is missing: there is no viewer whose state to report.
        """
        if not _PYVISTA_OK:
            return None
        camera = None
        if self._plotter is not None:
            camera = tuple(
                tuple(round(float(n), 6) for n in vec) for vec in self._plotter.camera_position
            )
        return BlockMeshViewState(
            toggles={
                name: self._view_toggle(attr).isChecked()
                for name, attr in self.VIEW_TOGGLES.items()
            },
            overlays={
                name: self._view_overlay(attr).master.isChecked()
                for name, attr in self.VIEW_OVERLAYS.items()
            },
            label_font_size=self._label_font_size.value(),
            splitter=(encode_qt_state(self._view_splitter.saveState())
                      if self._view_splitter is not None else None),
            camera=camera,  # type: ignore[arg-type]
        )

    def apply_view_state(self, state: BlockMeshViewState) -> None:
        """Apply view settings read by :meth:`view_state`.

        Unnamed toggles keep their current value, so a state need only say what
        it changes. The camera goes on last because rendering resets it.
        """
        if not _PYVISTA_OK:
            return
        for name, checked in state.toggles.items():
            action = self._view_toggle(self.VIEW_TOGGLES[name])
            action.blockSignals(True)
            action.setChecked(checked)
            action.blockSignals(False)
        if self._vtx_group is not None:
            # Normally driven by the action's `triggered` signal, which a
            # programmatic setChecked() does not emit.
            self._vtx_group.setVisible(self._view_toggle("_act_vtx_table").isChecked())
        for name, on in state.overlays.items():
            # Left unblocked: the master toggle also enables/disables the rows
            # under it, and its render is superseded by the one below.
            self._view_overlay(self.VIEW_OVERLAYS[name]).master.setChecked(on)
        if state.label_font_size is not None:
            self._label_font_size.blockSignals(True)
            self._label_font_size.setValue(state.label_font_size)
            self._label_font_size.blockSignals(False)
        if state.splitter is not None and self._view_splitter is not None:
            self._view_splitter.restoreState(decode_qt_state(state.splitter))

        self._render()
        if state.camera is not None and self._plotter is not None:
            self._plotter.camera_position = [list(vec) for vec in state.camera]
            self._plotter.render()

    def _view_toggle(self, attr: str) -> QAction | QCheckBox:
        """Resolve a VIEW_TOGGLES attribute name; both kinds are checkable."""
        widget = getattr(self, attr)
        assert widget is not None  # built in _build_controls() when _PYVISTA_OK
        return widget

    def _view_overlay(self, attr: str) -> _ShapeOverlayMenu:
        menu = getattr(self, attr)
        assert menu is not None  # built in _build_controls() when _PYVISTA_OK
        return menu

    @staticmethod
    def _merge_by_file(store, path, data, shapes, non_geometric, extra=None):
        """Record one file's shapes in *store* and return the union across all files.

        Stamps each shape with the file's basename, which is what lets a merged menu say
        which of several `topoSetDict-*` a row came from. A file that yields nothing is
        dropped from the store rather than kept as an empty entry, so closing or emptying
        one dictionary removes its rows instead of leaving a dead source behind.

        `extra` is for an overlay with a second per-file list to keep alive alongside the
        shapes -- snappyHexMesh's keep-points -- so that a file contributing only those is
        still stored.
        """
        for shape in list(shapes) + list(non_geometric):
            shape.source_file = Path(path).name
        if shapes or non_geometric or extra:
            store[path] = data
        else:
            store.pop(path, None)
        merged = [s for d in store.values() for s in d.shapes]
        merged_info = [s for d in store.values() for s in d.non_geometric]
        return merged, merged_info

    def forget_file(self, path: str) -> None:
        """Drop *path*'s contribution from every overlay and redraw.

        Needed when a file stops feeding the overlay it used to. Re-dispatching alone
        cannot do it: changing a "show as" override from topoSet to setFields calls
        update_set_fields, which has no reason to touch the topoSet store, so the old
        rows would sit there forever. Clearing the override entirely is worse -- nothing
        is dispatched at all, so nothing would remove them.
        """
        if not _PYVISTA_OK:
            return
        removed = False
        for store in (
            self._topo_by_file, self._snappy_by_file,
            self._set_fields_by_file, self._sampling_by_file,
        ):
            removed |= store.pop(path, None) is not None
        if not removed:
            return
        if self._topo is not None:
            self._topo.rebuild(
                [s for d in self._topo_by_file.values() for s in d.shapes],
                [s for d in self._topo_by_file.values() for s in d.non_geometric],
            )
        if self._snappy is not None:
            self._snappy.rebuild(
                [s for d in self._snappy_by_file.values() for s in d.shapes],
                [s for d in self._snappy_by_file.values() for s in d.non_geometric],
                [p for d in self._snappy_by_file.values() for p in d.location_points],
            )
        if self._set_fields is not None:
            self._set_fields.rebuild(
                [s for d in self._set_fields_by_file.values() for s in d.shapes],
                [s for d in self._set_fields_by_file.values() for s in d.non_geometric],
            )
        if self._sampling is not None:
            self._sampling.rebuild(
                [s for d in self._sampling_by_file.values() for s in d.shapes],
                [s for d in self._sampling_by_file.values() for s in d.non_geometric],
            )
        self._update_export_stl_enabled()
        if self._plotter is not None:
            self._render()

    def update_topo_set(self, path: str, root: FoamNode) -> None:
        if not _PYVISTA_OK:
            return
        assert self._topo is not None  # built in _build_controls() when _PYVISTA_OK
        data = extract_topo_set_data(root)
        shapes, non_geometric = self._merge_by_file(
            self._topo_by_file, path, data, data.shapes, data.non_geometric
        )
        self._topo.rebuild(shapes, non_geometric)
        self._update_export_stl_enabled()
        if self._plotter is not None:
            self._render()

    def update_snappy_hex_mesh(self, path: str, root: FoamNode) -> None:
        if not _PYVISTA_OK:
            return
        assert self._snappy is not None  # built in _build_controls() when _PYVISTA_OK
        case_dir = str(Path(path).parent.parent)
        data = extract_snappy_hex_mesh_data(root, case_dir)
        shapes, non_geometric = self._merge_by_file(
            self._snappy_by_file, path, data, data.shapes, data.non_geometric,
            extra=data.location_points,
        )
        points = [
            pt for d in self._snappy_by_file.values() for pt in d.location_points
        ]
        self._snappy.rebuild(shapes, non_geometric, points)
        self._update_export_stl_enabled()
        if self._plotter is not None:
            self._render()

    def update_set_fields(self, path: str, root: FoamNode) -> None:
        if not _PYVISTA_OK:
            return
        assert self._set_fields is not None  # built in _build_controls() when _PYVISTA_OK
        data = extract_set_fields_data(root)
        shapes, non_geometric = self._merge_by_file(
            self._set_fields_by_file, path, data, data.shapes, data.non_geometric
        )
        self._set_fields.rebuild(shapes, non_geometric)
        self._update_export_stl_enabled()
        if self._plotter is not None:
            self._render()

    def update_sampling(self, path: str, root: FoamNode) -> None:
        if not _PYVISTA_OK:
            return
        assert self._sampling is not None  # built in _build_controls() when _PYVISTA_OK
        data = extract_sampling_data(root)
        shapes, non_geometric = self._merge_by_file(
            self._sampling_by_file, path, data, data.shapes, data.non_geometric
        )
        self._sampling.rebuild(shapes, non_geometric)
        if self._plotter is not None:
            self._render()

    def set_case_dir(self, directory: str | None) -> None:
        """Remember the case directory, for the Save Image dialog's default path.

        Poked by _load_case_dir whenever the case changes, the same way
        LogSummaryDialog is kept pointed at the current case.
        """
        self._case_dir = directory

    def clear(self) -> None:
        self._data = None
        self._case_dir = None
        # Surfaces were loaded for the case being left behind, so they must not
        # stay drawn over the next one.
        self._surfaces.clear()
        self._rebuild_surface_menu()
        if self._topo is not None:
            self._topo.rebuild([], [])
        if self._snappy is not None:
            self._snappy.rebuild([], [], [])
        if self._set_fields is not None:
            self._set_fields.rebuild([], [])
        self._sampling_by_file.clear()
        self._topo_by_file.clear()
        self._snappy_by_file.clear()
        self._set_fields_by_file.clear()
        if self._sampling is not None:
            self._sampling.rebuild([], [])
        self._update_export_stl_enabled()
        self._selected_vertex = None
        self._selected_block = None
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
        # There is no render window left to capture; init_plotter() re-enables
        # this when one is built again (the xterm/VTK switch does exactly that).
        if self.save_image_action is not None:
            self.save_image_action.setEnabled(False)

    # ── vertices table ────────────────────────────────────────────────────────

    def _populate_vertex_table(self) -> None:
        if self._vtx_table is None:
            return
        verts = self._data.vertices if self._data else []
        n = len(verts)
        shown = min(n, _MAX_VERTEX_TABLE_ROWS)
        truncated = n > shown

        right = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        ro_flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        editable = not self._has_variables or self._preview_mode
        rw_flags = (ro_flags | Qt.ItemFlag.ItemIsEditable) if editable else ro_flags

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
                tr("… {n} vertices total (table limited to {shown})").format(
                    n=n, shown=shown
                )
            )
            msg.setFlags(Qt.ItemFlag.ItemIsEnabled)
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
        assert self._vtx_table is not None  # slot is only connected once built
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
        assert self._vtx_info_bar is not None  # built alongside _preview_btn
        self._vtx_info_bar.setVisible(self._has_variables)
        self._preview_btn.setChecked(self._preview_mode)
        if self._preview_banner is not None:
            self._preview_banner.setVisible(self._preview_mode)

    def _on_preview_toggled(self) -> None:
        assert self._preview_btn is not None  # slot is only connected once built
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
            selected_block=self._selected_block,
        )

    def _set_view(self, fn: str, **kw) -> None:
        if self._renderer is None:
            return
        self._renderer.set_view(fn, **kw)

    def _render(self) -> None:
        if self._renderer is None:
            return
        # Built together in _build_controls() whenever _PYVISTA_OK, same as _renderer.
        assert self._topo is not None
        assert self._snappy is not None
        assert self._set_fields is not None
        assert self._sampling is not None
        assert self._loaded_surfaces is not None
        has_overlay = (
            self._topo.shapes or self._snappy.shapes or self._snappy.locations
            or self._set_fields.shapes or self._sampling.shapes
        )
        has_content = (
            self._data is not None or bool(has_overlay) or bool(self._surfaces)
        )
        # Nothing to draw: skip, unless the previous frame drew something that
        # now has to be cleared (e.g. the last loaded surface was unloaded).
        # Keyed on loaded, not visible, surfaces so unchecking every row still
        # re-renders — to an empty scene — instead of leaving the last frame up.
        if not has_content and not self._scene_drawn:
            return
        self._scene_drawn = has_content
        self._renderer.render(
            self._data,
            self._make_settings(),
            self._loaded_surfaces.visible_shapes(),
            self._topo.visible_shapes(),
            self._snappy.visible_shapes(),
            self._snappy.visible_locations(),
            self._set_fields.visible_shapes(),
            self._sampling.visible_shapes(),
        )

    # ── STL loading ───────────────────────────────────────────────────────────

    def _load_stl(self) -> None:
        if not _PYVISTA_OK:
            return
        paths, _ = QFileDialog.getOpenFileNames(
            self, tr("Load STL / OBJ"), "",
            f"{tr('STL / OBJ files')} (*.stl *.STL *.stlb *.obj *.OBJ "
            f"*.stl.gz *.STL.gz *.obj.gz *.OBJ.gz *.stlb.gz);;{tr('All files')} (*)",
        )
        if not paths:
            return
        # One unreadable file must not discard the ones that did load.
        loaded = 0
        failures: list[str] = []
        for path in paths:
            try:
                mesh = read_surface_mesh(path)
            except Exception as e:
                failures.append(f"{Path(path).name}: {e}")
                continue
            loaded += 1
            existing = self._surface_index(path)
            if existing is None:
                self._surfaces.append(
                    LoadedSurface(
                        label=Path(path).name,
                        kind=Path(path).suffix.lstrip(".").lower(),
                        source_file=path,
                        color=self._next_surface_color(),
                        mesh=mesh,
                    )
                )
            else:
                # Re-loading a path already on screen re-reads it in place —
                # a refresh for an externally edited file, not a second row.
                # Keeping the entry's identity also keeps its menu row checked
                # or unchecked as the user left it.
                self._surfaces[existing] = dataclasses.replace(
                    self._surfaces[existing], mesh=mesh
                )
        if loaded:
            self._rebuild_surface_menu()
            self._render()
        if failures:
            QMessageBox.warning(
                self, tr("STL Load Error"),
                tr("Could not load:\n{files}").format(files="\n".join(failures)),
            )

    def _surface_index(self, path: str) -> int | None:
        for i, surface in enumerate(self._surfaces):
            if surface.source_file == path:
                return i
        return None

    def _next_surface_color(self) -> str:
        """First palette colour not already in use, else cycle by count.

        Assigned once at load time, so unloading a surface never recolours the
        others — but the colour it frees is handed to the next file loaded.
        """
        used = {s.color for s in self._surfaces}
        for color in _SURFACE_COLORS:
            if color not in used:
                return color
        return _SURFACE_COLORS[len(self._surfaces) % len(_SURFACE_COLORS)]

    def _unload_surface(self, path: str) -> None:
        index = self._surface_index(path)
        if index is None:
            return
        del self._surfaces[index]
        self._rebuild_surface_menu()
        self._render()

    def _clear_stl(self) -> None:
        self._surfaces.clear()
        self._rebuild_surface_menu()
        self._render()

    def _rebuild_surface_menu(self) -> None:
        """Repopulate the per-file rows, the Unload submenu, and Clear STL."""
        if self._loaded_surfaces is None:
            return
        self._loaded_surfaces.rebuild(self._surfaces, [])
        self._unload_stl_menu.clear()
        for surface in self._surfaces:
            act = self._unload_stl_menu.addAction(surface.label)
            act.setToolTip(surface.source_file)
            act.triggered.connect(
                lambda _=False, p=surface.source_file: self._unload_surface(p)
            )
        self._unload_stl_menu.setEnabled(bool(self._surfaces))
        self._update_clear_stl_enabled()

    def _update_clear_stl_enabled(self) -> None:
        if self._clear_stl_act is not None:
            self._clear_stl_act.setEnabled(bool(self._surfaces))

    # ── STL export ────────────────────────────────────────────────────────────

    def _exportable_topo_shapes(self) -> list[TopoShape]:
        """topoSet shapes that produce a meaningful STL surface (see _exportable())."""
        return _exportable(self._topo.shapes if self._topo is not None else [])

    def _exportable_set_fields_shapes(self) -> list[SetFieldsShape]:
        """setFields regions that produce a meaningful STL surface (unclipped)."""
        return _exportable(self._set_fields.shapes if self._set_fields is not None else [])

    def _update_export_stl_enabled(self) -> None:
        if self._export_stl_act is not None:
            snappy_shapes = self._snappy.shapes if self._snappy is not None else []
            self._export_stl_act.setEnabled(
                bool(
                    self._exportable_topo_shapes()
                    or snappy_shapes
                    or self._exportable_set_fields_shapes()
                )
            )

    def _export_shapes_stl(self) -> None:
        exportable = self._exportable_topo_shapes()
        set_fields_exportable = self._exportable_set_fields_shapes()
        if not _PYVISTA_OK:
            return
        # Built together in _build_controls(), which only runs when _PYVISTA_OK.
        assert self._topo is not None
        assert self._snappy is not None
        assert self._set_fields is not None
        if not (exportable or self._snappy.shapes or set_fields_exportable):
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

    # ── image export ──────────────────────────────────────────────────────────

    def _default_image_path(self) -> str:
        """Where the Save Image dialog opens, named after the case when known."""
        if self._case_dir:
            case = Path(self._case_dir)
            return str(case / f"{case.name}-3Dview.png")
        return "3Dview.png"

    def _save_view_image(self) -> None:
        """Write the 3-D view to an image file. The dialog and the writing live in
        ui/panels/_view_image_export.py; what stays here is the panel's own state."""
        if not _PYVISTA_OK or self._plotter is None:
            return
        path = save_view_image(self, self._plotter, self._default_image_path())
        if path:
            self.image_saved.emit(path)
