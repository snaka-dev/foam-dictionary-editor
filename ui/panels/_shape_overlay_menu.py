# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""The checkable per-shape overlay menu used by the BlockMesh 3-D viewer.

Split out of ui/panels/block_mesh_panel.py, which was 1512 lines. Nothing here refers to
BlockMeshPanel: `_ShapeOverlayMenu` is driven entirely by the shapes it is handed and the
callbacks it is constructed with, which is what made the move mechanical.

The panel builds five of these -- topoSet, snappyHexMesh, setFields, sampling, and the STL
overlay menu -- plus the small helpers they share.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from PySide6.QtGui import QAction, QColor, QIcon, QPixmap
from PySide6.QtWidgets import QMenu, QToolButton, QWidget

from foam.shapes import SourceShape
from i18n import tr


def _shape_key(shape) -> tuple[str, str, str]:
    """Stable identity for an overlay shape across re-extraction.

    Uses the shared label/kind fields plus the sampling-only source_file (blank
    for the other overlays) so per-shape visibility toggles can be preserved
    when the menu is rebuilt.
    """
    return (
        getattr(shape, "source_file", ""),
        getattr(shape, "label", ""),
        getattr(shape, "kind", ""),
    )


def _color_swatch(color_name: str, size: int = 12) -> QIcon:
    """A small filled square icon; stays vivid on disabled (greyed) menu rows."""
    pm = QPixmap(size, size)
    pm.fill(QColor(color_name))
    icon = QIcon(pm)
    icon.addPixmap(pm, QIcon.Mode.Disabled)
    return icon


def _menu_button(text: str, menu: QMenu, tooltip: str | None = None) -> QToolButton:
    """Build a QToolButton that instant-pops *menu*; used by the geometry toolbar.

    *text* is expected to already be translated (via ``tr()``) by the caller;
    the trailing " ▾" marker is appended here rather than baked into a
    translation key, since it is chrome, not prose (see DEVELOPER.md's i18n
    section). The composed labels — "Vertices ▾", "Blocks ▾", "topoSet ▾",
    "snappyHexMesh ▾", "setFields ▾", "sample ▾", "Scale ▾", "STL ▾" — are
    each named here in full so tools/demo_specs.json's button-label targets
    still resolve to a literal in ui/ (tests/tools/test_demo_specs.py scans
    for a quoted string, not the rendered widget text).
    """
    btn = QToolButton()
    btn.setText(text + " ▾")
    btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    btn.setMenu(menu)
    if tooltip is not None:
        btn.setToolTip(tooltip)
    return btn


_T = TypeVar("_T", bound=SourceShape)


def _exportable(shapes: list[_T]) -> list[_T]:
    """Shapes from *shapes* that produce a meaningful STL surface.

    Point markers have no surface and a planeToFaceZone disc's extent is
    display-only, so neither is offered for export. Generic over the concrete
    SourceShape subclass so callers keep their specific return type.
    """
    return [s for s in shapes if not ({"points", "planePoint"} & s.geometry.keys())]


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
        menu: QMenu | None = None,
        item_noun: str = "shapes",
    ) -> None:
        self._shape_row = shape_row
        self._info_row = info_row
        self._location_row = location_row
        self._on_changed = on_changed

        self.shapes: list = []
        self.non_geometric: list = []
        self._multi_source = False
        self.locations: list = []
        self.shape_actions: list[QAction] = []
        self.location_actions: list[QAction] = []
        self.info_actions: list[QAction] = []
        self.info_menu: QMenu | None = None

        # An existing menu can be adopted so the owner's own actions sit above
        # the toggles; rebuild() only ever appends and only removes rows it
        # created, so foreign actions in the same menu are left alone.
        self.menu = menu if menu is not None else _StaysOpenMenu(parent)
        self.master = QAction(master_label, self.menu, checkable=True, checked=True)
        self.menu.addAction(self.master)
        # item_noun ("shapes" / "surfaces") is itself tr()'d here rather than at
        # the call site, since it is folded into the sentence below.
        self.show_all = QAction(tr("Show all {noun}").format(noun=tr(item_noun)), self.menu)
        self.hide_all = QAction(tr("Hide all {noun}").format(noun=tr(item_noun)), self.menu)
        self.menu.addAction(self.show_all)
        self.menu.addAction(self.hide_all)
        self.menu.addSeparator()

        # Static legend mapping each row label to its overlay colour. Menus
        # whose rows carry their own colour pass no legend, making it redundant.
        self.legend_actions: list[QAction] = []
        if legend:
            legend_header = QAction(legend_title, self.menu)
            legend_header.setEnabled(False)
            self.menu.addAction(legend_header)
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

    def _attribution(self, shape) -> str:
        """`  [file]` when several files feed this menu, otherwise "".

        Every overlay is now the union of however many files define that dictionary -- a
        case can hold `topoSetDict-slices` and `topoSetDict-background` at once -- so a row has
        to be able to say which file it came from. Only when there is more than one,
        though: almost every case has a single `topoSetDict`, and stamping its name onto
        every row there would be noise rather than information.

        Applied here rather than in each overlay's row lambda because this is the only
        place that knows how many files contributed.
        """
        return f"  [{shape.source_file}]" if self._multi_source else ""

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
        # Remember which shapes/locations the user had hidden so a rebuild
        # (fired on every edit of a contributing dict) does not silently
        # re-show them. Keyed by a stable identity that survives re-extraction;
        # this matters most for the sampling overlay, whose menu is the union
        # of several files, so editing one must not reset another's toggles.
        prior_shape_checked = {
            _shape_key(s): a.isChecked()
            for s, a in zip(self.shapes, self.shape_actions)
        }
        prior_loc_checked = {
            self._location_row(loc): a.isChecked()
            for loc, a in zip(self.locations, self.location_actions)
        } if self._location_row is not None else {}

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
        self._multi_source = len({
            s.source_file for s in self.shapes + self.non_geometric if s.source_file
        }) > 1

        master_on = self.master.isChecked()
        for shape in self.shapes:
            icon, text = self._shape_row(shape)
            text += self._attribution(shape)
            checked = prior_shape_checked.get(_shape_key(shape), True)
            act = QAction(icon, text, self.menu, checkable=True, checked=checked)
            act.setEnabled(master_on)
            act.toggled.connect(self._on_changed)
            self.menu.addAction(act)
            self.shape_actions.append(act)

        if self._location_row is not None:
            for location in self.locations:
                row = self._location_row(location)
                act = QAction(
                    row, self.menu, checkable=True,
                    checked=prior_loc_checked.get(row, True),
                )
                act.setEnabled(master_on)
                act.toggled.connect(self._on_changed)
                self.menu.addAction(act)
                self.location_actions.append(act)

        if self.non_geometric:
            self.info_menu = QMenu(
                tr("Non-geometric sources ({n})").format(n=len(self.non_geometric)),
                self.menu,
            )
            for shape in self.non_geometric:
                act = QAction(self._info_row(shape) + self._attribution(shape), self.info_menu)
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
