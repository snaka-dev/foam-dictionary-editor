# FoDE — Screenshot Gallery

A visual tour of FoDE's panels, overlays, and dialogs. For the full feature reference see [USER_GUIDE.md](../USER_GUIDE.md); for installation and a quick start see [README.md](../README.md).

Every image in the **Main window** and **BlockMesh 3-D viewer** sections below is captured by `tools/capture_screenshots.py` from the window states in `tools/screenshot_specs.json`, so a shot can be retaken with one command and a light/dark pair differs in nothing but the theme. See [Screenshot capture](../DEVELOPER.md#screenshot-capture). The **Dialogs and menus** shots are taken separately: an open menu and a dialog are separate X windows rather than part of the main window's frame.

## Main window

![Main window — Tree and Editor tabs](images/main-window-tree-editor.png)

Tree view and plain-text editor side by side, kept in sync in both directions — edit a value in the tree and the corresponding line highlights in the editor, or edit the text and apply it back to the tree. See [Current UI layout](../USER_GUIDE.md#current-ui-layout).

![Main window — dark theme](images/main-window-tree-editor-dark.png)

The same view with **Settings > Appearance** set to **Dark**. The theme reaches everything the window draws, including the editor's syntax highlighting, the line-number gutter, and the selected-row fill and text — the last recomputed by FoDE rather than inherited from the desktop, so a selected row stays legible whatever accent colour is set. See [Appearance and colours](../USER_GUIDE.md#appearance-and-colours).

![Main window — Boundary and Editor tabs](images/main-window-boundary-editor.png)

The Boundary view tab: every boundary patch across every field file laid out as a table (patches × fields), so the whole boundary condition set can be reviewed and edited at a glance instead of opening each field file in turn. Each cell shows the patch's `type`; raising **Lines per cell** shows the entries under it (`value uniform (10 0 0)` and so on) as well. See [Boundary view](../USER_GUIDE.md#boundary-view).

![Main window — comparing two cases](images/main-window-compare.png)

Compare mode, with the `cavity` tutorial open and `cavityGrade` set as the reference. The two trees sit side by side and the differences are marked in place rather than left to be spotted: entries that differ are highlighted, as are those present on only one side — `grad(p)` here exists in the open case and not in the reference. The file list carries the same information one level up, so a case can be scanned before any file is opened: each file is marked with how many entries differ, and files missing from one side are greyed. Nothing is modified by comparing; **Clear** ends it. See [Case comparison](../USER_GUIDE.md#case-comparison).

## BlockMesh 3-D viewer

The 3-D panel renders `blockMeshDict` geometry and overlays matching geometry from `topoSetDict`, `snappyHexMeshDict`, `setFieldsDict`, and sampling dicts when those files are loaded or being edited. See [BlockMesh panel](../USER_GUIDE.md#blockmesh-panel).

### topoSetDict overlay — topoSetShapes case

![topoSetDict overlay — topoSetShapes case](images/blockMesh3Dview-topoSet-topoSetShapes.png)

The bundled `tutorials/topoSetShapes` case, whose `topoSetDict` exercises every geometry source the overlay can draw: boxes (plain, `min`/`max` and multi-box `boxes`), a rotated box, solid and hollow spheres, the cylinder and cone family, point markers, and a `planeToFaceZone` plane — all overlaid inside the block-mesh wireframe and named by a badge at the shape's centre. Each shape takes its colour from the action that produced it, so `new`, `add` and `subtract` sets are told apart at a glance; where shapes sit inside one another their badges overlap, and any shape reaching past the block mesh is drawn clipped and its badge is marked `(clipped)` (`midPlane`, here). The editor pane shows a `coneToCell` entry using an `#eval` expression. See [topoSetDict overlay](../USER_GUIDE.md#toposetdict-overlay).

### topoSetDict overlay — floatingObject case

![topoSetDict overlay — floatingObject case](images/blockMesh3Dview-topoSet-floatingObject.png)

The OpenFOAM `floatingObject` tutorial, showing a blue `boxToCell` cellSet (`c0`) rendered inside the unit block. See [topoSetDict overlay](../USER_GUIDE.md#toposetdict-overlay).

### setFieldsDict overlay — damBreak case

![setFieldsDict overlay — damBreak case](images/blockMesh3Dview-setFields-damBreak.png)

The bundled `tutorials/damBreak` case, with `setFieldsDict`'s `regions` list drawn in orange over the block mesh and each region badged with a summary of the field values it sets — so the initial water column can be checked against the mesh before `setFields` is ever run. The region here is written to span the full depth of what is a quasi-2-D case, well past the mesh, so it is drawn cut down to the mesh and its badge marked `(clipped)`; the dictionary itself is untouched, and an STL export would write the full shape. Selecting the `box` row in the tree scrolls the editor to the line that defines it. See [setFieldsDict overlay](../USER_GUIDE.md#setfieldsdict-overlay) and [Overlay clipping](../USER_GUIDE.md#overlay-clipping).

### Sampling overlay — samplingShapes case

![Sampling overlay — samplingShapes case](images/blockMesh3Dview-sampling-samplingShapes.png)

The bundled `tutorials/samplingShapes` case, the sampling counterpart of `topoSetShapes`: every kind of sampling geometry the viewer draws, in one 3×3×3 block. Probe and cloud definitions are drawn as point markers, span-based sets as tubes, and sampling planes as discs. Sampling is unusual among the overlays in having no dictionary of its own — it can be written as a function object inside `controlDict`, or in a standalone dictionary, in either of two member-list syntaxes — so this case spreads its definitions across all three and the panel merges them, tagging each row of the **sample ▾** menu with the file it came from. Both planes are badged `(clipped)`: a plane is unbounded, so the disc is display-only and is always cut back to the mesh it is shown in. See [Sampling overlay](../USER_GUIDE.md#sampling-overlay) and [Overlay clipping](../USER_GUIDE.md#overlay-clipping).

### snappyHexMeshDict overlay — motorBike case (side-by-side)

![snappyHexMeshDict overlay — motorBike case](images/blockMesh3Dview-snappyHex-motorBike.png)

The OpenFOAM `motorBike` tutorial in side-by-side mode: tree and 3-D view shown together. The motorBike `triSurfaceMesh` geometry is rendered alongside a purple `refinementBox` region (classified "inside"), plus a `locationInMesh` marker; the tree and editor are focused on the `refinementRegions` entry. See [snappyHexMeshDict overlay](../USER_GUIDE.md#snappyhexmeshdict-overlay) and [Side-by-side mode](../USER_GUIDE.md#side-by-side-mode).

![snappyHexMeshDict overlay — motorBike case, dark theme](images/blockMesh3Dview-snappyHex-motorBike-dark.png)

The same overlay from the same camera in the dark theme — the same spec captured twice, so nothing but the theme differs. The 3-D scene has no palette of its own, so it is themed explicitly: the scene background, the bounds readout above it, the grid's tick numbers and axis titles, the orientation triad's X/Y/Z letters, and the vertex and block numbers all switch with the theme. The patch and overlay colours do not — the motorBike surface stays teal and `refinementBox` stays purple, because those identify what you are looking at. Shape name badges stay a light sticker in both themes for the same reason: they have to read against whatever colour the geometry underneath them is. See [Appearance and colours](../USER_GUIDE.md#appearance-and-colours).

## Dialogs and menus

### Find OpenFOAM Examples

![Find OpenFOAM Examples dialog](images/find_foam_example.png)

The non-modal Find OpenFOAM Examples dialog, searching an installation's `tutorials/` and `etc/caseDicts/` for a keyword — `topoSetDict` here, matching 200 files. Hits are grouped under the case they belong to, and selecting one previews the file with syntax highlighting. The buttons along the bottom are what turns a search result into work you can do: take a copy of the file, open the tutorial as the reference side of a case comparison, or duplicate the whole case as a new editable one. See [Find OpenFOAM Examples](../USER_GUIDE.md#find-openfoam-examples).

### Run a meshing or field tool

![Run setFields options dialog](images/run-tool-dialog.png)

The options dialog behind the Tools menu's **Run …** actions, here for `setFields` on the bundled `damBreak` case. Rather than asking you to remember an executable's flags, each tool offers a curated set of them as fields, with anything uncurated going in **Extra options** — and the box at the bottom shows the exact command that will be sent to the Terminal tab, updating as you change your mind. The composed command always ends by teeing to `log.<tool>`, which is what leaves a log for [View Log Summary](#view-log-summary) to read afterwards. The dialog is also where a tool's foot-guns are headed off: `setFields` rewrites `0/` in place, so re-running it compounds the values it has already set, and the offer to restore `0/` from `0.orig/` first is checked by default and visible in the command as the prefix it will actually run. See [Run setFields](../USER_GUIDE.md#run-setfields).

### View Log Summary

![View Log Summary dialog](images/log-summary-dialog.png)

The non-modal View Log Summary dialog, reading the `log.simpleFoam` a `pitzDaily` run left behind — 2,898 lines of solver output condensed to what is on screen: how far the run got, whether it converged, where the residuals ended up, and whether it finished cleanly. The most recently written `log.*` in the case is picked automatically; **Browse…** chooses another, and the **Raw Log** tab holds the untouched text for when the summary is not enough. `blockMesh`, `snappyHexMesh` and `topoSet` logs each have their own grammar and report what matters for that utility instead — mesh sizes, refinement phases, per-set counts — and repeated warnings are grouped rather than listed one by one. Being non-modal, the dialog can sit beside the main window while you keep editing. See [View Log Summary](../USER_GUIDE.md#view-log-summary).

### Tools menu

![Tools menu](images/tools-menu.png)

The Tools menu is where FoDE stops editing dictionaries and hands work to OpenFOAM itself. Its entries are grouped by what they act on: the meshing and field utilities, each of which opens the [options dialog above](#run-a-meshing-or-field-tool) before sending its command to the Terminal tab; the whole-case scripts and clean-up; handing the mesh to ParaView; and the two non-modal dialogs, [View Log Summary](#view-log-summary) and [Find OpenFOAM Examples](#find-openfoam-examples). Everything acts on the open case — `pitzDaily`, here. See [Run blockMesh](../USER_GUIDE.md#run-blockmesh) and [foamMonitor launcher](../USER_GUIDE.md#foammonitor-launcher).
