# Foam Dictionary Editor (FoDE)

FoDE — Foam Dictionary Editor (pronounced "foh-dee")

A GUI editor for OpenFOAM dictionary files, built with Python and PySide6.

[Demo movie link at YouTube](https://youtu.be/L22fQW3NSUk)

## What is FoDE?

FoDE is a graphical editor for OpenFOAM case dictionary files. It lets you browse, edit, and manage dictionaries through a structured tree view or a plain-text editor — whichever suits the task. It is aimed at engineers and researchers who run OpenFOAM simulations and want a more convenient way to set up and modify case files.

![Main window — Tree and Editor tabs](docs/images/main-window-tree-editor.png)

## Installation

Python 3.10 or newer is required.

```bash
git clone https://github.com/snaka-dev/foam-dictionary-editor
cd foam-dictionary-editor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # installs PySide6 (Qt for Python)
```

An internet connection is recommended on first launch — xterm.js (the terminal emulator) is downloaded automatically to `ui/xterm/`. Without it, the terminal falls back to the simple QProcess-based widget. Restart the app with internet access to retry, or place the files manually:

| File | URL |
|---|---|
| `xterm.js` | `https://cdn.jsdelivr.net/npm/@xterm/xterm@6.0.0/lib/xterm.js` |
| `xterm.css` | `https://cdn.jsdelivr.net/npm/@xterm/xterm@6.0.0/css/xterm.css` |
| `xterm-addon-fit.js` | `https://cdn.jsdelivr.net/npm/@xterm/addon-fit@0.11.0/lib/addon-fit.js` |

**Optional — BlockMesh 3-D viewer** (Linux/macOS): install `pyvista` and `pyvistaqt` to enable the interactive 3-D geometry panel for `blockMeshDict`:

```bash
pip install pyvista pyvistaqt
```

Without these packages the BlockMesh tab shows an install prompt and the 3-D viewer is disabled.

## Basic Workflow

1. **Launch**

   ```bash
   python3 main.py                                   # standard (terminal + BlockMesh)
   python3 main.py --variant no-terminal             # no terminal tab (Windows-friendly)
   python3 main.py --variant no-terminal-blockmesh   # no terminal + BlockMesh 3-D panel
   ```

   The chosen variant is saved to `app_config.json` on exit and used automatically on the next launch.

2. **Open a case** — choose one:
   - *Your own case:* **Case > Open Case** → select your case directory
   - *Start from a tutorial:* **Case > Duplicate from Case Library** → browse `$FOAM_TUTORIALS` → copy to your working directory

3. **Select a file** from the left panel (e.g. `system/controlDict`, `0/U`)

4. **Edit** values in the Tree view or the raw Text editor at the bottom

5. **Check and adjust boundary conditions** in the **Boundary** tab — a table showing all patches and field variables at a glance; click any cell to open its file in the editor and jump to the patch entry

6. **Save** — `Ctrl+S` (current file) or `Ctrl+Shift+S` (all modified files)

7. *(Optional)* **Run your solver** from the **Terminal** tab — the terminal opens in the case directory, so you can run `blockMesh`, `interFoam`, or any other OpenFOAM command directly

## Key Features

**File management**
- Opens common dictionary files automatically (`controlDict`, `fvSchemes`, `fvSolution`, `blockMeshDict`, `snappyHexMeshDict`, and more)
- Detects multiRegion case structures and field directories (`0/`, `0.orig/`) automatically
- Add extra directories to the file list — all files inside are scanned automatically, just like `0/`. Each directory can be scanned flat (direct files only) or recursively (all subdirectories). Useful for custom field directories (`initial/`), restart time steps (`0.5/`), or deep subdirectories (`lagrangian/chemkin/`)
- Add, create, duplicate, backup, or delete files from the file panel
- Reload the current case from disk via **Case > Reload Case** — discards all in-memory edits; prompts if files are unsaved
- Delete the `0/` directory from disk via right-click on the `0` header — available only when `0.orig` exists
- Save the current state as a new case, or duplicate an existing one

**Tree and text editing**
- Structured tree view for browsing and editing dictionary entries
- Raw text editor always available as a fallback
- Sync between tree and text in both directions
- Add, duplicate, comment out, or delete tree entries via right-click

**Boundary condition view**
- See all boundary conditions across all field variables in one table
- Click a cell to open its file in the editor and jump to the patch entry (toggleable with **Auto-scroll editor**)
- Edit, create, delete, copy, and paste patch entries directly in the table
- Add or delete a patch across all field files in one step

**Schema help**
- Built-in descriptions and valid choices for common settings (`controlDict`, `fvSchemes`, `fvSolution`, `blockMeshDict`, `snappyHexMeshDict`)
- Extend with your own schema modules (plain Python files)

**BlockMesh 3-D viewer** *(requires pyvista / pyvistaqt)*
- Interactive 3-D preview of `blockMeshDict` geometry (vertices, block edges, boundary faces)
- Boundary faces colour-coded by patch type (wall, inlet, outlet, symmetry, …)
- Load and overlay STL / OBJ geometry files
- Toggle visibility of vertices, vertex labels, block edges, block labels, boundary faces, axes, grid, and dimension text
- Color blocks: each hex block rendered in a distinct colour from a qualitative palette; Solid blocks: semi-transparent solid block faces (opacity 0.25)
- Adjustable label font size (spin box) shared between vertex labels and block labels
- View direction buttons (+X/−X/+Y/−Y/+Z/−Z/Iso) for quick camera positioning
- Mouse hint bar below the 3-D view (drag = rotate, Shift+drag = pan, scroll = zoom); full reference in **Help > Keyboard Shortcuts…**
- Vertices table (index | X | Y | Z) alongside the 3-D view; click a row to highlight the vertex, double-click a coordinate cell to edit it — change writes back to the FoamNode tree and text editor instantly
- Available as the **BlockMesh** tab when the `blockmesh` feature is enabled (always visible in the `no-terminal-blockmesh` variant; visible in the `standard` variant only when Simple terminal mode is active); can also be toggled via **View > BlockMesh 3-D Panel**

**Integrated terminal**
- Full PTY xterm.js terminal (Linux/macOS with `QtWebEngineWidgets`) — default in `standard` variant
- Simple QProcess-based fallback also available; activating it shows the BlockMesh 3-D panel
- Toggle between the two modes at runtime with the checkbox in the Terminal tab
- Automatically switches to the case directory when a case is opened
- Omitted entirely in the `no-terminal` and `no-terminal-blockmesh` variants (Windows-friendly)

**Case comparison**
- **Case > Compare with Case...** — select a reference case directory to compare against the currently open case
- A diff bar below the action bar shows the reference path, a colour legend, and a **Side by side** toggle; click **Clear** to exit compare mode
- **Side-by-side view**: a reference-case tree panel opens to the right of the main tree; right-click any entry in it to **Use this value** and apply it directly to the current case
- Tree overlay — current case (left pane): light yellow = value changed, light blue = key only in current file; reference pane (right): light yellow = value changed, light green = key only in reference
- Hover a highlighted row in either pane to see the counterpart value in the tooltip
- File list markers: `≠N` (amber) for files with differences, `≠0` (gray) for checked-and-identical, nothing for unvisited; capped at `≠50+`. Markers are computed immediately for all files when comparison starts
- **Changed files only** filter checkbox in the file list: hides files with no differences

**Reference links**
- **Help > Resources...** provides links to official OpenFOAM documentation
- **My Links** tab: add, edit, reorder, and remove personal reference links; double-click to open in browser

## Full Reference

For detailed documentation of every panel, menu, and workflow, see [USER_GUIDE.md](USER_GUIDE.md).
For project structure, dev setup, and testing, see [DEVELOPER.md](DEVELOPER.md).

## License

Copyright (C) 2025-2026 Shinji NAKAGAWA. Released under the [GNU Affero General Public License v3.0 or later](LICENSE) (AGPL-3.0-or-later).

## Disclaimer

This offering is not approved or endorsed by OpenCFD Limited, producer and distributor of the OpenFOAM software via [www.openfoam.com](http://www.openfoam.com/), and owner of the OPENFOAM® and OpenCFD® trade marks.

## Acknowledgements

- [PySide6 (Qt for Python)](https://doc.qt.io/qtforpython/) — GUI framework (LGPL v3)
- [pyVista](https://pyvista.org/) / [VTK](https://vtk.org/) — 3-D viewer for `blockMeshDict` (BSD-3-Clause, optional)
- [xterm.js](https://xtermjs.org/) — Terminal emulator used in the Terminal panel (MIT). Downloaded automatically from jsDelivr on first launch and cached in `ui/xterm/`
- [pytest](https://pytest.org/) / [pytest-qt](https://pytest-qt.readthedocs.io/) — Test framework (development only)

Special thanks to the [OpenFOAM Foundation](https://openfoam.org/) and [OpenCFD / ESI Group](https://www.openfoam.com/) and all contributors for developing and maintaining OpenFOAM as free, open-source CFD software.
