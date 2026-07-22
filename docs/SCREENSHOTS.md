# FoDE — Screenshot Gallery

A visual tour of FoDE's panels, overlays, and dialogs. For the full feature reference see [USER_GUIDE.md](../USER_GUIDE.md); for installation and a quick start see [README.md](../README.md).

## Main window

![Main window — Tree and Editor tabs](images/main-window-tree-editor.png)

Tree view and plain-text editor side by side, kept in sync in both directions — edit a value in the tree and the corresponding line highlights in the editor, or edit the text and apply it back to the tree. See [Current UI layout](../USER_GUIDE.md#current-ui-layout).

![Main window — Boundary and Editor tabs](images/main-window-boundary-editor.png)

The Boundary view tab: every boundary patch across every field file laid out as a table (patches × fields), so the whole boundary condition set can be reviewed and edited at a glance instead of opening each field file in turn. See [Boundary view](../USER_GUIDE.md#boundary-view).

## BlockMesh 3-D viewer

The 3-D panel renders `blockMeshDict` geometry and overlays matching geometry from `topoSetDict`, `snappyHexMeshDict`, `setFieldsDict`, and sampling dicts when those files are loaded or being edited. See [BlockMesh panel](../USER_GUIDE.md#blockmesh-panel).

### topoSetDict overlay — topoSetShapes case

![topoSetDict overlay — topoSetShapes case](images/blockMesh3Dview-topoSet-topoSetShapes.png)

The bundled `tutorials/topoSetShapes` case, showing nine labelled `topoSetDict` shapes — `box0`, `ball`, `spike`, `ring`, `pipe`, a tilted cylinder, a rotated box (`core`), a frustum, and `coneRing` — overlaid inside the block-mesh wireframe. The editor pane shows a `coneToCell` entry using an `#eval` expression. See [topoSetDict overlay](../USER_GUIDE.md#toposetdict-overlay).

### topoSetDict overlay — floatingObject case

![topoSetDict overlay — floatingObject case](images/blockMesh3Dview-topoSet-floatingObject.png)

The OpenFOAM `floatingObject` tutorial, showing a blue `boxToCell` cellSet (`c0`) rendered inside the unit block. See [topoSetDict overlay](../USER_GUIDE.md#toposetdict-overlay).

### snappyHexMeshDict overlay — motorBike case (side-by-side)

![snappyHexMeshDict overlay — motorBike case](images/blockMesh3Dview-snappyHex-motorBike.png)

The OpenFOAM `motorBike` tutorial in side-by-side mode: tree and 3-D view shown together. The motorBike `triSurfaceMesh` geometry is rendered alongside a purple `refinementBox` region (classified "inside"), plus a `locationInMesh` marker; the tree and editor are focused on the `refinementRegions` entry. See [snappyHexMeshDict overlay](../USER_GUIDE.md#snappyhexmeshdict-overlay) and [Side-by-side mode](../USER_GUIDE.md#side-by-side-mode).

## Dialogs and menus

### Find OpenFOAM Examples

![Find OpenFOAM Examples dialog](images/find_foam_example.png)

The non-modal Find OpenFOAM Examples dialog: an installation picker, a query (`topoSetDict` here), matching tutorial files listed as a tree, a syntax-highlighted preview of the matched file, and **Copy File** / **Compare with this case** actions. See [Find OpenFOAM Examples](../USER_GUIDE.md#find-openfoam-examples).

### Tools menu

![Tools menu](images/Tools_menu.png)

The Tools menu: launch `foamMonitor…`, restore `0/` from `0.orig`, run `blockMesh`/`snappyHexMesh`/`topoSet`/`setFields`/`checkMesh`, run the case's Allrun/Allclean scripts, open the mesh in ParaView, clean the case, view a log summary, and find OpenFOAM examples. See [Run blockMesh](../USER_GUIDE.md#run-blockmesh) and [foamMonitor launcher](../USER_GUIDE.md#foammonitor-launcher).
