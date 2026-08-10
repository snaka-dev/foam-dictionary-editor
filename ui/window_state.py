# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Read back and re-apply the parts of MainWindow's layout that are not derived.

``capture_window_state(window)`` returns a ``WindowState``;
``apply_window_state(window, state)`` puts a freshly built window back into it.
The dataclasses are JSON-serialisable (``to_dict``/``from_dict``), so a state can
be written to a file and applied to a different process. Two things do that:
``tools/capture_screenshots.py``, to make screenshots reproducible, and
``ui/session_restore.py``, to reopen the window where the user left it.

Those two want opposite error handling, which is what the ``strict`` flag on
``from_dict`` and :func:`apply_window_state` is for. A screenshot spec is
hand-written and describes a window that must come out exactly so, and a typo or
a stale tree row in one is a bug that should say so loudly. A saved session is
machine-written and describes a window that *used* to exist, whose case may
since have been renamed and whose fields may have been written by a later
version of the app — so it degrades, part by part, to today's defaults.
:func:`load_saved_state` is the lenient reading entry point.

What is deliberately *not* covered: anything a window re-derives on its own.
Tree expansion beyond the selected row's ancestors, scroll offsets, the editor's
cursor and fold state and the detail panel's contents all follow from the file
that is open and the row that is selected, so they are left to follow. Pinning
the selection pins them; listing them here would only add ways for two runs to
disagree. ``tree_expand`` is the one escape hatch, for rows that have to be open
without being selected.

Sizes travel as ``QSplitter.saveState()`` / ``QWidget.saveGeometry()`` blobs
(base64 in JSON) rather than pixel counts: those round-trip exactly and stay
valid across Qt versions, whereas a list of pixel sizes is silently rescaled
when the window it was recorded from was a different size.
"""
from __future__ import annotations

import base64
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QAbstractItemModel, QByteArray, QModelIndex, Qt
from PySide6.QtWidgets import QSplitter, QTabWidget

from foam.utils import is_large_non_foam_file
from model.tree_model import FoamTreeModel

if TYPE_CHECKING:
    from ui.main_window import MainWindow

# Path element: a key as shown in the tree's Key column, or a row number for
# rows that have no key of their own (the anonymous entries of a `topoSetDict`
# `actions ( … )` list, say).
KeyPath = list[str | int]
Vec3 = tuple[float, float, float]


# ── serialisation helpers ─────────────────────────────────────────────────────


def encode_qt_state(data: QByteArray) -> str:
    """Base64-encode a Qt saveState()/saveGeometry() blob for JSON."""
    return base64.b64encode(data.data()).decode("ascii")


def decode_qt_state(text: str) -> QByteArray:
    """Inverse of :func:`encode_qt_state`."""
    return QByteArray(base64.b64decode(text.encode("ascii")))


def _known_fields(cls: type, data: dict[str, Any], strict: bool) -> dict[str, Any]:
    """Return *data* restricted to the keys the dataclass defines.

    Two callers with opposite needs, hence the flag. Hand-written state files —
    the screenshot specs — want ``strict``: a silently ignored typo is exactly
    how a spec drifts out of agreement with what it claims to describe. A saved
    session wants the opposite: a blob written by a newer version of the app,
    naming a field this one has never heard of, must degrade to today's
    defaults rather than stop the application opening.
    """
    known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    unknown = sorted(set(data) - known)
    if unknown and strict:
        raise ValueError(
            f"{cls.__name__}: unknown field(s) {', '.join(unknown)}; "
            f"known fields are {', '.join(sorted(known))}"
        )
    return {name: value for name, value in data.items() if name in known}


def _coerce(value: Any, convert: Callable[[Any], Any], strict: bool) -> Any:
    """Run *convert* over *value*, or return None when lenient and it fails.

    The companion to :func:`_known_fields` at the value level: a newer version
    that changes a field's *shape* (a fourth camera row, say) is as likely as
    one that adds a field name, and neither may take the app down with it.
    """
    if value is None:
        return None
    if strict:
        return convert(value)
    try:
        return convert(value)
    except Exception:
        return None


# ── state ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class BlockMeshViewState:
    """The BlockMesh 3-D panel's own view settings.

    ``toggles`` and ``overlays`` are keyed by the stable names in
    ``BlockMeshPanel.VIEW_TOGGLES`` / ``VIEW_OVERLAYS``; a missing key keeps the
    panel's default, so a state need only name what it changes. ``overlays``
    holds each overlay menu's master switch only — per-shape rows default to
    visible, and re-extraction rebuilds them anyway.
    """

    toggles: dict[str, bool] = field(default_factory=dict)
    overlays: dict[str, bool] = field(default_factory=dict)
    label_font_size: int | None = None
    splitter: str | None = None  # base64 QSplitter.saveState(): plotter vs. vertex table
    camera: tuple[Vec3, Vec3, Vec3] | None = None  # (position, focal point, view up)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if self.toggles:
            data["toggles"] = dict(self.toggles)
        if self.overlays:
            data["overlays"] = dict(self.overlays)
        if self.label_font_size is not None:
            data["label_font_size"] = self.label_font_size
        if self.splitter is not None:
            data["splitter"] = self.splitter
        if self.camera is not None:
            data["camera"] = [list(vec) for vec in self.camera]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any], strict: bool = True) -> BlockMeshViewState:
        data = _known_fields(cls, data, strict)
        return cls(
            toggles=_coerce(data.get("toggles") or None, _as_flags, strict) or {},
            overlays=_coerce(data.get("overlays") or None, _as_flags, strict) or {},
            label_font_size=_coerce(data.get("label_font_size"), int, strict),
            splitter=data.get("splitter"),
            camera=_coerce(data.get("camera"), _as_camera, strict),
        )


def _as_size(value: Any) -> tuple[int, int]:
    """Coerce a two-element sequence to a (width, height) pair.

    The type check is not pedantry: a string is subscriptable, so a spec saying
    ``"window_size": "1200x800"`` would otherwise index its first two characters
    and yield (1, 2) — a window too small to see and no error to explain it.
    """
    if isinstance(value, (str, bytes)) or len(value) != 2:
        raise ValueError("window_size must be a [width, height] pair")
    return int(value[0]), int(value[1])


def _as_flags(value: Any) -> dict[str, bool]:
    """Coerce a mapping to the ``{name: bool}`` shape the toggle menus expect."""
    return {str(name): bool(flag) for name, flag in dict(value).items()}


def _as_camera(value: Any) -> tuple[Vec3, Vec3, Vec3]:
    """Coerce a nested sequence to the three float triples VTK expects."""
    rows = [tuple(float(n) for n in row) for row in value]
    if len(rows) != 3 or any(len(row) != 3 for row in rows):
        raise ValueError("camera must be three [x, y, z] triples: position, focal point, view up")
    position, focal, up = rows
    return position, focal, up  # type: ignore[return-value]


@dataclass(frozen=True)
class WindowState:
    """Everything about a MainWindow's layout that is a choice rather than a consequence."""

    # Geometry. ``geometry`` (saveGeometry: size, position and screen) wins when
    # both are given; ``window_size`` is the readable form for hand-written specs.
    geometry: str | None = None
    window_size: tuple[int, int] | None = None
    # QSplitter.saveState() blobs, keyed by the names in SPLITTERS. Exact, and
    # what capture produces — but not writable by hand, which is what
    # ``splitter_sizes`` (plain pixel widths, applied via setSizes and only as
    # exact as the window size they were chosen for) is for. Both may appear;
    # ``splitters`` is applied first, so a size overrides the blob for that one.
    splitters: dict[str, str] = field(default_factory=dict)
    splitter_sizes: dict[str, list[int]] = field(default_factory=dict)
    # Panes currently minimized, by the ui/pane_minimize.py PANE_* names, mapped
    # to the size a restore should go back to. The splitter blobs above already
    # carry the collapsed geometry, so this exists for the half they cannot: the
    # pane's *former* size, which is gone the moment it collapses, and the fact
    # that the collapse was deliberate rather than a handle dragged to the edge.
    minimized_panes: dict[str, int] = field(default_factory=dict)
    # Tabs are addressed by label, not index: the BlockMesh tab comes and goes
    # with the terminal's mode, so indices are not stable.
    upper_tab: str | None = None
    lower_tab: str | None = None
    side_by_side: bool | None = None
    # View > BlockMesh 3-D Panel. Worth pinning because it does not follow from
    # the terminal's mode: switching out of xterm re-enables the menu item but
    # leaves it unchecked, so the tab stays away until something ticks it.
    block_mesh_visible: bool | None = None
    terminal_mode: str | None = None  # "simple" | "xterm"
    case_dir: str | None = None
    # Files to open before ``current_file``, which stays the one on screen. The
    # 3-D viewer accumulates geometry across the dicts it has seen — a
    # snappyHexMeshDict overlay is drawn inside the block mesh only if
    # blockMeshDict was loaded too — so which files have been opened is part of
    # what the window shows, not just where the cursor happens to be.
    preload_files: list[str] = field(default_factory=list)
    current_file: str | None = None  # relative to case_dir when inside it
    tree_selection: KeyPath | None = None
    tree_expand: list[KeyPath] = field(default_factory=list)
    # The editor's zoom, in points either side of the application font's size —
    # an offset rather than a size, so a state stays meaningful on a machine
    # whose desktop font differs from the one it was captured on.
    editor_zoom: int | None = None
    block_mesh: BlockMeshViewState | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if self.geometry is not None:
            data["geometry"] = self.geometry
        if self.window_size is not None:
            data["window_size"] = list(self.window_size)
        if self.splitters:
            data["splitters"] = dict(self.splitters)
        if self.splitter_sizes:
            data["splitter_sizes"] = {name: list(sizes)
                                      for name, sizes in self.splitter_sizes.items()}
        if self.minimized_panes:
            data["minimized_panes"] = dict(self.minimized_panes)
        for name in ("upper_tab", "lower_tab", "side_by_side", "block_mesh_visible",
                     "terminal_mode", "case_dir", "current_file", "editor_zoom"):
            value = getattr(self, name)
            if value is not None:
                data[name] = value
        if self.preload_files:
            data["preload_files"] = list(self.preload_files)
        if self.tree_selection is not None:
            data["tree_selection"] = list(self.tree_selection)
        if self.tree_expand:
            data["tree_expand"] = [list(path) for path in self.tree_expand]
        if self.block_mesh is not None:
            data["block_mesh"] = self.block_mesh.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any], strict: bool = True) -> WindowState:
        """Build a state from JSON. See :func:`_known_fields` for *strict*.

        Use :func:`load_saved_state` rather than ``strict=False`` directly when
        reading a user's persisted session: it also survives *data* not being a
        usable mapping at all.
        """
        data = _known_fields(cls, data, strict)
        return cls(
            geometry=data.get("geometry"),
            window_size=_coerce(data.get("window_size"), _as_size, strict),
            splitters=_coerce(data.get("splitters") or None,
                              lambda m: {str(k): str(v) for k, v in dict(m).items()}, strict) or {},
            splitter_sizes=_coerce(
                data.get("splitter_sizes") or None,
                lambda m: {str(name): [int(n) for n in sizes] for name, sizes in dict(m).items()},
                strict,
            ) or {},
            minimized_panes=_coerce(
                data.get("minimized_panes") or None,
                lambda m: {str(name): int(size) for name, size in dict(m).items()},
                strict,
            ) or {},
            upper_tab=data.get("upper_tab"),
            lower_tab=data.get("lower_tab"),
            side_by_side=data.get("side_by_side"),
            block_mesh_visible=data.get("block_mesh_visible"),
            terminal_mode=data.get("terminal_mode"),
            case_dir=data.get("case_dir"),
            preload_files=_coerce(data.get("preload_files") or None,
                                  lambda paths: [str(p) for p in paths], strict) or [],
            current_file=data.get("current_file"),
            tree_selection=_coerce(data.get("tree_selection") or None, list, strict),
            tree_expand=_coerce(data.get("tree_expand") or None,
                                lambda paths: [list(path) for path in paths], strict) or [],
            editor_zoom=_coerce(data.get("editor_zoom"), int, strict),
            block_mesh=_coerce(data.get("block_mesh") or None,
                               lambda d: BlockMeshViewState.from_dict(d, strict), strict),
        )

    def merged_with(self, other: WindowState) -> WindowState:
        """Return *other* laid over this state, field by field.

        Used for spec-wide defaults: an unset field (None, or an empty dict/list)
        in *other* leaves this state's value in place. ``block_mesh`` merges one
        level deeper so a shot can set just a camera without restating toggles.
        """
        merged: dict[str, Any] = {}
        for name in self.__dataclass_fields__:
            mine, theirs = getattr(self, name), getattr(other, name)
            if name == "block_mesh" and mine is not None and theirs is not None:
                merged[name] = _merge_block_mesh(mine, theirs)
            elif theirs is None or theirs == {} or theirs == []:
                merged[name] = mine
            else:
                merged[name] = theirs
        return WindowState(**merged)


def load_saved_state(data: Any) -> WindowState | None:
    """Parse a persisted session blob, or return None if it is unusable.

    The lenient counterpart to ``WindowState.from_dict``, and the only one that
    should ever be pointed at ``app_config.json``. Restoring a layout is a
    convenience; failing to restore one must cost the user nothing worse than a
    default window, so every way this can go wrong ends in None.
    """
    if not isinstance(data, dict):
        return None
    try:
        return WindowState.from_dict(data, strict=False)
    except Exception:
        return None


def _merge_block_mesh(base: BlockMeshViewState, over: BlockMeshViewState) -> BlockMeshViewState:
    return BlockMeshViewState(
        toggles={**base.toggles, **over.toggles},
        overlays={**base.overlays, **over.overlays},
        label_font_size=(over.label_font_size if over.label_font_size is not None
                         else base.label_font_size),
        splitter=over.splitter if over.splitter is not None else base.splitter,
        camera=over.camera if over.camera is not None else base.camera,
    )


# ── splitter registry ─────────────────────────────────────────────────────────

# Stable names for the splitters that make up the main window's layout, in the
# order they nest. The BlockMesh panel's internal splitter is not here: it is
# part of that panel's own view state.
SPLITTERS = ("main", "right", "right_upper", "tree_bm")


def _splitters(window: MainWindow) -> dict[str, QSplitter]:
    found = {
        "main": window.main_splitter,
        "right": window.right_splitter,
        "right_upper": window.right_upper_splitter,
        "tree_bm": window._tree_bm_splitter,
    }
    return {name: splitter for name, splitter in found.items() if splitter is not None}


# ── tree addressing ───────────────────────────────────────────────────────────


def index_for_key_path(model: QAbstractItemModel, path: KeyPath) -> QModelIndex:
    """Resolve a key path against a FoamTreeModel; invalid index if it misses.

    Each element is matched against the Key column's displayed text, except an
    integer, which selects that child row directly — the way to address the
    anonymous entries of a list-of-dicts.
    """
    index = QModelIndex()
    for element in path:
        if isinstance(element, int):
            if element >= model.rowCount(index):
                return QModelIndex()
            index = model.index(element, FoamTreeModel.COL_KEY, index)
            continue
        for row in range(model.rowCount(index)):
            child = model.index(row, FoamTreeModel.COL_KEY, index)
            if model.data(child, Qt.ItemDataRole.DisplayRole) == element:
                index = child
                break
        else:
            return QModelIndex()
    return index


def key_path_for_index(index: QModelIndex) -> KeyPath:
    """Inverse of :func:`index_for_key_path` for an index in the source model."""
    path: KeyPath = []
    while index.isValid():
        key = index.model().data(index.siblingAtColumn(FoamTreeModel.COL_KEY),
                                 Qt.ItemDataRole.DisplayRole)
        path.append(index.row() if not key else str(key))
        index = index.parent()
    return list(reversed(path))


# ── capture ───────────────────────────────────────────────────────────────────


def capture_window_state(window: MainWindow) -> WindowState:
    """Read the current window layout back into a WindowState."""
    tabs = _tab_label(window.upper_tabs), _tab_label(window.bottom_tabs)
    selection = window.tree.currentIndex()
    tree_selection: KeyPath | None = None
    if selection.isValid():
        tree_selection = key_path_for_index(window.proxy_model.mapToSource(selection))

    block_mesh = None
    if window.block_mesh_panel is not None:
        block_mesh = window.block_mesh_panel.view_state()

    terminal_mode = None
    if window.terminal_panel is not None:
        terminal_mode = "xterm" if window.terminal_panel.use_xterm else "simple"

    return WindowState(
        geometry=encode_qt_state(window.saveGeometry()),
        window_size=(window.width(), window.height()),
        splitters={
            name: encode_qt_state(splitter.saveState())
            for name, splitter in _splitters(window).items()
        },
        minimized_panes={
            name: minimizer.restore_size
            for name, minimizer in window._pane_minimizers.items()
            if minimizer.minimized
        },
        upper_tab=tabs[0],
        lower_tab=tabs[1],
        side_by_side=window.state.bm_side_by_side,
        block_mesh_visible=(window._blockmesh_action.isChecked()
                            if window._blockmesh_action is not None else None),
        terminal_mode=terminal_mode,
        case_dir=window.state.current_case_dir,
        # Insertion order is load order, which is what a replay needs; the file
        # on screen is named separately, so it is left out here.
        preload_files=[
            relative
            for path in window.state.file_buffers
            if path != window.state.current_file
            and (relative := _relative_file(path, window.state.current_case_dir))
        ],
        current_file=_relative_file(window.state.current_file, window.state.current_case_dir),
        tree_selection=tree_selection,
        editor_zoom=window.editor_panel.editor.zoom_steps(),
        block_mesh=block_mesh,
    )


def _tab_label(tabs: QTabWidget) -> str | None:
    index = tabs.currentIndex()
    return tabs.tabText(index) if index >= 0 else None


def _relative_file(path: str | None, case_dir: str | None) -> str | None:
    if not path:
        return None
    if case_dir:
        try:
            return str(Path(path).relative_to(case_dir))
        except ValueError:
            pass  # an #include target outside the case: keep it absolute
    return path


# ── apply ─────────────────────────────────────────────────────────────────────


def apply_window_state(
    window: MainWindow,
    state: WindowState,
    settle: Callable[[], None] = lambda: None,
    strict: bool = True,
) -> list[str]:
    """Put an already-shown window into *state*; return notes on what was skipped.

    Order matters: the terminal's mode decides whether there is a BlockMesh tab
    to select, loading a case resets the tree, and side-by-side mode reparents
    the BlockMesh panel into a splitter — so sizes are restored last of all.

    Some of what this triggers only completes on a later turn of the event loop
    (switching the terminal *to* xterm, and side-by-side's deferred setSizes and
    VTK init). ``settle`` is called at those points to let the caller decide how
    to wait — spin a nested loop, as tools/capture_screenshots.py does, or leave
    it as the no-op default and accept that those steps land shortly after this
    returns. Either way they end in a re-render that resets the 3-D camera, so a
    caller that pinned one should call :func:`apply_block_mesh_view` again once
    the window has settled.

    ``strict`` matches ``WindowState.from_dict``'s flag and matters for the same
    reason. A screenshot spec naming a tab, splitter or tree row that is not
    there is a broken spec and says so; a restored session is describing a
    window the user had *last time*, whose case may since have been renamed or
    whose selected row may since have been deleted, so each such part is skipped
    and named in the returned notes instead. The returned list is always empty
    when ``strict`` is true, because anything worth noting has raised by then.
    """
    notes: list[str] = []
    _apply_geometry(window, state)

    # Independent of everything below — it survives the file loads and the tab
    # switches — so it is applied first and left alone.
    if state.editor_zoom is not None:
        window.editor_panel.editor.set_zoom_steps(state.editor_zoom)

    # Only on a real change, like side-by-side below: set_use_xterm already
    # no-ops when the mode matches, but settling costs the caller an event-loop
    # turn it does not owe — and at startup that turn is a visible stall.
    if state.terminal_mode is not None and window.terminal_panel is not None:
        use_xterm = state.terminal_mode == "xterm"
        if use_xterm != window.terminal_panel.use_xterm:
            window.terminal_panel.set_use_xterm(use_xterm)
            settle()

    if state.block_mesh_visible is not None and window._blockmesh_action is not None:
        window._blockmesh_action.setChecked(state.block_mesh_visible)

    # The file half hangs off the case directory — the file list, the buffers
    # and the tree all come from it — so a case that has been moved or deleted
    # takes the files with it and leaves only the layout to restore.
    case_dir = state.case_dir
    if case_dir and not strict and not Path(case_dir).is_dir():
        notes.append(f"case directory is gone: {case_dir}")
        case_dir = None
    elif case_dir:
        window._load_case_dir(case_dir)

    if case_dir or not state.case_dir:
        for relative in state.preload_files:
            _load_file(window, relative, case_dir, strict, notes)
        if state.current_file:
            path = _load_file(window, state.current_file, case_dir, strict, notes)
            if path is not None:
                window.file_list_panel.select_file(path)

    _apply_tree(window, state, strict, notes)

    # Only on a real change: toggling side-by-side *off* adds a BlockMesh tab,
    # which is wrong when there was never one to begin with (xterm mode).
    if (state.side_by_side is not None and window.block_mesh_panel is not None
            and state.side_by_side != window.state.bm_side_by_side):
        window._on_toggle_bm_side_by_side(state.side_by_side)
        settle()

    _select_tab(window.upper_tabs, state.upper_tab, strict, notes)
    _select_tab(window.bottom_tabs, state.lower_tab, strict, notes)

    for name, blob in state.splitters.items():
        splitter = _splitter(window, name, strict, notes)
        if splitter is not None:
            splitter.restoreState(decode_qt_state(blob))
    for name, sizes in state.splitter_sizes.items():
        splitter = _splitter(window, name, strict, notes)
        if splitter is not None:
            splitter.setSizes(sizes)
    _apply_minimized_panes(window, state, strict, notes)

    apply_block_mesh_view(window, state)
    return notes


def _absolute(path: str, case_dir: str | None) -> str:
    if Path(path).is_absolute() or not case_dir:
        return path
    return str(Path(case_dir) / path)


def _load_file(
    window: MainWindow, relative: str, case_dir: str | None, strict: bool, notes: list[str]
) -> str | None:
    """Open one of the state's files; return the path opened, or None if skipped.

    The two checks are what keep a lenient restore quiet, because
    ``load_selected_file`` has two ways of stopping to ask: a modal error for a
    file it cannot read, and a modal confirmation for a large non-dictionary
    file (a ``log.*`` run log is exactly that shape). Neither is a way to greet
    someone at startup. The large-file prompt in particular warns that loading
    will freeze the window, and answering that question on the user's behalf is
    no better than asking it — so the file is left for them to click, which
    puts the prompt back where they asked for it.
    """
    path = _absolute(relative, case_dir)
    if strict:
        window.load_selected_file(path)
        return path
    if not Path(path).is_file():
        notes.append(f"file is gone: {relative}")
        return None
    if is_large_non_foam_file(path)[0]:
        notes.append(f"large file not reopened: {relative}")
        return None
    window.load_selected_file(path)
    return path


def _splitter(
    window: MainWindow, name: str, strict: bool, notes: list[str]
) -> QSplitter | None:
    splitter = _splitters(window).get(name)
    if splitter is None:
        if strict:
            raise ValueError(f"unknown splitter {name!r}; known: {', '.join(SPLITTERS)}")
        notes.append(f"no {name!r} splitter in this layout")
    return splitter


def _apply_minimized_panes(
    window: MainWindow, state: WindowState, strict: bool, notes: list[str]
) -> None:
    """Re-minimize the panes the state names, and restore the ones it does not.

    Runs after the splitter blobs, which is the whole point: restoring a blob
    puts the pane back at whatever size it had when the state was captured, and
    for a minimized pane that is the collapsed size with no memory of what it
    collapsed *from*.

    The remembered size is written *after* minimizing, not before. Minimizing
    records the size it collapsed from — which here is the collapsed size the
    blob just restored — so setting it first would only have it overwritten, and
    the next restore would fall back to the pane's build-time default.
    """
    for name, minimizer in window._pane_minimizers.items():
        remembered = state.minimized_panes.get(name)
        window.set_pane_minimized(name, remembered is not None)
        if remembered is not None:
            minimizer.restore_size = remembered
    unknown = sorted(set(state.minimized_panes) - set(window._pane_minimizers))
    for name in unknown:
        if strict:
            raise ValueError(
                f"unknown pane {name!r}; known: {', '.join(sorted(window._pane_minimizers))}"
            )
        notes.append(f"no {name!r} pane in this layout")


def apply_block_mesh_view(window: MainWindow, state: WindowState) -> None:
    """Apply just the BlockMesh panel's view settings, camera last.

    Separate from :func:`apply_window_state` because it is the one step worth
    repeating: every render resets the camera, so whoever waited for the scene
    to settle has to set it again afterwards.
    """
    if state.block_mesh is None or window.block_mesh_panel is None:
        return
    window.block_mesh_panel.apply_view_state(state.block_mesh)


def _apply_geometry(window: MainWindow, state: WindowState) -> None:
    if state.geometry is not None:
        window.restoreGeometry(decode_qt_state(state.geometry))
    elif state.window_size is not None:
        window.resize(*state.window_size)


def _apply_tree(
    window: MainWindow, state: WindowState, strict: bool = True, notes: list[str] | None = None
) -> None:
    source = window.proxy_model.sourceModel()
    if source is None:
        return

    for path in state.tree_expand:
        index = index_for_key_path(source, path)
        if index.isValid():
            window.tree.expand(window.proxy_model.mapFromSource(index))

    if state.tree_selection is None:
        return
    index = index_for_key_path(source, state.tree_selection)
    if not index.isValid():
        if strict:
            raise ValueError(f"no tree row at {state.tree_selection}")
        # The file is open, just edited since: leave the selection where
        # loading put it rather than guessing at a nearby row.
        if notes is not None:
            notes.append(f"tree row is gone: {state.tree_selection}")
        return
    proxy_index = window.proxy_model.mapFromSource(index)
    # Ancestors have to be open for the row to be reachable; QTreeView expands
    # them itself on setCurrentIndex, but not before scrollTo needs them.
    parent = proxy_index.parent()
    while parent.isValid():
        window.tree.expand(parent)
        parent = parent.parent()
    window.tree.setCurrentIndex(proxy_index)
    window.tree.scrollTo(proxy_index, window.tree.ScrollHint.PositionAtCenter)


def _select_tab(
    tabs: QTabWidget, label: str | None, strict: bool = True, notes: list[str] | None = None
) -> None:
    if label is None:
        return
    for index in range(tabs.count()):
        if tabs.tabText(index) == label:
            tabs.setCurrentIndex(index)
            return
    available = ", ".join(tabs.tabText(i) for i in range(tabs.count()))
    if strict:
        raise ValueError(f"no tab labelled {label!r}; available: {available}")
    # Reached by a session saved in a different language, or one whose tab
    # belongs to a feature this run does not have.
    if notes is not None:
        notes.append(f"no {label!r} tab in this layout")
