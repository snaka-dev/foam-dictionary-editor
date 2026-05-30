# Release Notes

## v1.2.0 — 2026-05-30

### New features

**Boundary view — Copy Table**

- New **Copy Table** button in the Boundary panel toolbar. A drop-down menu offers two clipboard formats:
  - **Copy as Markdown** — GitHub-Flavored Markdown pipe table; multi-line cells (Lines per cell > 1) use `<br>` tags so they render as real line breaks on GitHub.
  - **Copy as CSV** — RFC 4180-compliant CSV; multi-line cell content is preserved inside quoted fields for correct display in Excel and LibreOffice Calc.
- Both formats include the row-header column and respect the current transposed orientation.

**Case comparison — Side-by-side view**

- **Side by side** toggle in the diff bar splits the centre panel horizontally: the left pane shows the editable current-case tree and a new **Reference** pane opens on the right with the corresponding file in read-only form.
- Reference tree uses **light green** for keys that exist only in the reference case.
- Right-click any leaf node in the reference pane and select **Use this value** to apply that value to the matching node in the current case instantly. Diff highlighting updates automatically after the change.
- **Changed files only** checkbox in the file list: hides files with zero differences, leaving only files that differ from the reference case.
- Diff markers (`≠N` / `≠0`) are now computed immediately for all files when comparison starts, rather than lazily as each file is opened.

### Improvements

**BlockMesh panel**

- Toolbar compacted into a single row.
- Load and overlay OBJ geometry files in addition to STL (`Load STL / OBJ…` / `Clear STL`).

**File list**

- Extra-files button is now always visible (shows the count of registered extras when any are active).

**Case comparison**

- The diff bar now shows a **Side by side** toggle and a colour legend alongside the reference path.

---

## v1.1.0 — 2026-05-23

This release adds several major features: an interactive BlockMesh 3-D viewer, case comparison with a diff overlay, case-wide boundary rename, Boundary-to-editor navigation, and tree ↔ editor source synchronisation. It also adds application variants for Windows-friendly use (no-terminal), recursive directory scanning for extra directories, expanded snappyHexMeshDict schema coverage, and various editor and usability improvements.

### New features

**BlockMesh 3-D viewer** *(requires `pyvista` and `pyvistaqt`)*

- New **BlockMesh** tab showing an interactive 3-D preview of `blockMeshDict` geometry: vertices (red spheres), hex block edges (wireframe), and boundary patch faces (colour-coded by type: wall, inlet, outlet, symmetry, …).
- Visibility toggles for vertices, vertex labels, block edges, block labels, boundary faces, axes, grid, and dimension text.
- **Block labels** — hex block index displayed at each block centroid (dark blue text), analogous to vertex labels.
- **Color blocks** — each hex block rendered in a distinct colour from a qualitative palette (tab10). Applies to wireframe edges and solid faces.
- **Solid blocks** — semi-transparent solid hex block faces (opacity 0.25) rendered alongside the wireframe, sharing the Color blocks palette.
- **Label size** — shared spin box (range 6–32, default 10) in the second toolbar row controls font size for both vertex labels and block labels.
- View direction buttons (+X / −X / +Y / −Y / +Z / −Z / Iso) for quick camera positioning.
- Mouse hint bar at the bottom of the panel showing abbreviated controls (drag = rotate, Shift+drag = pan, scroll = zoom); full reference on hover tooltip and in **Help > Keyboard Shortcuts…**.
- Vertices table (index | X | Y | Z) alongside the 3-D view; click a row to highlight the vertex, double-click a coordinate cell to edit the value — the change writes back to the FoamNode tree and text editor instantly.
- Load and overlay STL geometry files (`Load STL…` / `Clear STL`).
- **View > BlockMesh 3-D Panel** (checkable) shows or hides the tab independently of the terminal mode. When xterm is active the action is grayed out and its label changes to explain the GPU conflict reason.
- Available in the `no-terminal-blockmesh` variant at all times; available in the `standard` variant while the terminal is in Simple mode.

**Case comparison**

- **Case > Compare with Case…** — select a reference case directory and compare it against the currently open case.
- A diff bar below the action bar shows the reference path and a colour legend; click **Clear** to exit compare mode.
- Tree overlay: light yellow = value changed, light blue = key exists only in this file. Hover a highlighted row to see the reference value in a tooltip.
- File list markers: `≠N` (amber) for files with N differences, `≠0` (gray) for checked-and-identical files, no marker for unvisited files. Capped at `≠50+`. Markers are updated lazily as each file is opened.

**Rename Boundary**

- Right-click a cell, a patch column/row header in the **Boundary** panel, or a patch node in the tree view and choose **Rename Boundary…**.
- A dialog lists every loaded file in which the patch name appears (`blockMeshDict` boundary entries and `boundaryField` patch keys). Select the files to update, enter the new name, and click **Rename**. All selected files are updated in memory and marked dirty in one step.

**Boundary-panel single-click navigation**

- Clicking a cell in the Boundary panel now opens its field file in the editor and scrolls to the corresponding patch entry (amber highlight). The **Auto-scroll editor** checkbox toggles this behaviour.
- When the clicked cell belongs to a different file than the currently open one, the file list and editor both update automatically.

**Tree ↔ editor source synchronisation**

- Clicking a tree node highlights the node's source span in the text editor with an amber background and scrolls to it.
- **Find in Tree** button (or `Ctrl+Shift+T`) finds the deepest tree node whose source span covers the current editor cursor line and selects it in the tree.
- A state guard disables jumps while the editor text is unsaved (stale line numbers), shown via the checkbox label and tooltip.

**Tree key filter**

- A filter bar above the tree allows case-insensitive keyword filtering. Parent nodes remain visible when a descendant matches.

**Case Reload**

- **Case > Reload Case** — discards all in-memory edits and reloads the case from disk. A confirmation dialog shows the number of unsaved files before proceeding.

**Delete `0/` directory**

- Right-click the `0` group header in the file list and choose **Delete '0' directory…** to permanently delete the `0/` directory from disk. Shown only when `0.orig` exists. A confirmation dialog displays the full path before deletion.

**Recursive subdirectory scan for extra directories**

- Each extra directory can now be scanned flat (direct files only, default) or recursively (all subdirectories via `rglob`).
- In **Settings > Manage Extra Files & Directories…** > **Extra Directories**, check one or more entries and click **Toggle Recursive** to enable or disable recursive scanning. The entry label shows `[recursive]` when active.
- Useful for result or validation trees (e.g. `validation/`) that contain files in subdirectories.

**Application variants**

- `--variant` flag selects a startup configuration: `standard` (terminal + BlockMesh), `no-terminal` (Windows-friendly), or `no-terminal-blockmesh` (BlockMesh always visible, no terminal). The selected variant is saved to `app_config.json` and applied automatically on the next launch.
- The terminal mode toggle (xterm ↔ Simple) is now in the Terminal tab; switching to Simple mode shows the BlockMesh tab.

**Tree copy/paste**

- `Ctrl+C` / `Ctrl+V` in the tree panel copies and pastes tree entries. Shortcuts are scoped to the tree widget so they do not conflict with the text editor below.

### Improvements

**View menu**

- **View > Show Type Column** — show or hide the Type column in the tree view.
- **View > BlockMesh 3-D Panel** — toggleable panel visibility (see above).

**Editor toolbar**

- Separate **Find Prev** (Shift+F3) and **Find Next** (F3) buttons.
- **Find in Tree** button (`Ctrl+Shift+T`) — jump from the current editor line to the corresponding tree node.
- **Line: N** indicator on the right side of the toolbar shows the current cursor line.

**Keyboard Shortcuts dialog**

- **Help > Keyboard Shortcuts…** lists all keyboard shortcuts in one place.
- New **BlockMesh 3-D viewer (mouse)** section covers rotate, pan, zoom, reset camera, and fly-to-point bindings.

**snappyHexMeshDict schema**

- Expanded schema coverage for `snappyHexMeshDict`: additional `snapControls`, `addLayersControls`, and `meshQualityControls` keys.
- Context-aware schema lookup now handles user-named sub-dicts (geometry entries, refinement surfaces/regions, layer patch groups) using grandparent-key context, so the correct schema is shown regardless of user-defined names.

**Parser**

- Fixed a bug where inline `//` comments inside parenthesised blocks (e.g. vertex lists) were silently dropped. Comments are now preserved as `unknown_raw_entry` nodes inside the block.

**Boundary panel**

- Right-click context menu now includes **Rename Boundary…** for cells and column/row headers.
- **Add or delete a patch across all field files** — right-click a patch column/row header.

**File management**

- `unknown_raw_entry` nodes (entries the parser could not fully interpret) are highlighted in amber in the tree so they stand out from normal entries.

---

## v1.0.0 — initial public release

First public release. Core features:

- Structured tree view and raw text editor for OpenFOAM dictionary files.
- File list with automatic scanning of `TARGET_FILES`, `0/`, and `0.orig/`; extra directories can be added.
- Boundary condition table (view, edit, create, delete, copy, paste, add/delete across all files).
- Built-in schema help for `controlDict`, `fvSchemes`, `fvSolution`, `blockMeshDict`, `snappyHexMeshDict`.
- Full PTY xterm.js terminal (Linux/macOS) with automatic case-directory switching.
- Case Library (`Case > Duplicate from Case Library`) to copy tutorials into a working directory.
- Save as new case / Duplicate case.
- Personal reference links (**Help > Resources…** > **My Links** tab).
- AGPL-3.0-or-later license.
