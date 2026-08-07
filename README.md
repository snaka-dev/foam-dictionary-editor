# Foam Dictionary Editor (FoDE)

FoDE — Foam Dictionary Editor (pronounced "foh-dee")

A GUI editor for OpenFOAM dictionary files, built with Python and PySide6.

🎬 **Demo movies on YouTube** — eight short walkthroughs, listed with shot-by-shot scripts in [docs/DEMO_SCRIPTS.md](docs/DEMO_SCRIPTS.md). Start with [Edit, see, run](https://youtu.be/kGxfNhAe6xo) (~74 s), or watch [the whole workflow](https://youtu.be/0FZPb92luw8) end to end (~3 min 38 s).

> 📄 **Now published in [*SoftwareX*](https://doi.org/10.1016/j.softx.2026.102852)** (Elsevier) — see [Citation](#citation).

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

**Optional — BlockMesh 3-D viewer** (Linux/macOS): install `pyvista` and `pyvistaqt` to enable the interactive 3-D geometry panel for `blockMeshDict` (also overlays `topoSetDict`, `snappyHexMeshDict`, and `setFieldsDict` geometry when those files are open):

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
   - *Drag and drop:* drag a case directory from your file manager onto any part of the application window
   - *Start from a tutorial:* **Case > Duplicate from Case Library** → browse `$FOAM_TUTORIALS` → copy to your working directory
   - *Use a bundled example:* open any case from the `tutorials/` directory in the repository root (see [Example Cases](#example-cases))

3. **Select a file** from the left panel (e.g. `system/controlDict`, `0/U`)

4. **Edit** values in the Tree view or the raw Text editor at the bottom

5. **Check and adjust boundary conditions** in the **Boundary** tab — a table showing all patches and field variables at a glance; click any cell to open its file in the editor and jump to the patch entry

6. **Save** — `Ctrl+S` (current file) or `Ctrl+Shift+S` (all modified files)

7. *(Optional)* **Run your solver** from the **Terminal** tab — the terminal opens in the case directory, so you can run `blockMesh`, `interFoam`, or any other OpenFOAM command directly

## Key Features

Each heading links to the full documentation in [USER_GUIDE.md](USER_GUIDE.md).

**[File management](USER_GUIDE.md#file-list-behavior)**
- Lists common dictionary files automatically (`controlDict`, `fvSchemes`, `fvSolution`, `blockMeshDict`, `snappyHexMeshDict`, and more) plus everything under `0/` and `0.orig/` and the case-root `All*` scripts (`Allrun`, `Allclean`, … — editable as plain text); detects multiRegion case structures
- Add extra files or whole directories (scanned flat or recursively) to the file list — useful for custom field directories, restart time steps, or deep subdirectories
- [Follows `#include` directives](USER_GUIDE.md#included-files) and lists the files they pull in — an include inside the case joins its own directory group, one resolving into your OpenFOAM installation (`#includeEtc`, `#includeFunc`) is grouped separately and opened read-only, with **Copy into case...** to make an editable local copy
- Create, duplicate, back up, or delete files from the file panel; reload the case from disk at any time
- File list auto-refreshes after changes made outside the app (e.g. via the Terminal); a `constant/polyMesh` indicator shows the cell count, marked stale when `blockMeshDict` has changed since the mesh was generated
- Save the current state as a new case, or duplicate an existing one

**[Tree and text editing](USER_GUIDE.md#tree-and-text-workflow)**
- Structured tree view and a raw text editor, synced in both directions
- OpenFOAM syntax highlighting (toggleable; the keyword list can be regenerated from your own installation) and code folding
- Add, duplicate, comment out, or delete tree entries via right-click
- `blockMeshDict`'s `blocks ( … );` expands to one `block 0`, `block 1`, … row per block, numbered to match the BlockMesh 3-D viewer — each row editable, addable, duplicable and deletable on its own, and selecting one outlines that block in 3-D

**[Boundary condition view](USER_GUIDE.md#boundary-view)**
- All boundary conditions across all field variables in one table — no switching between field files
- Edit, create, delete, copy, and paste patch entries directly in the table; add, delete, or rename a patch across all field files in one step
- Click a cell to jump to the patch entry in the editor; copy the whole table as Markdown or CSV

**[Schema help](USER_GUIDE.md#detail-pane)**
- Built-in descriptions and valid choices for common settings (`controlDict`, `fvSchemes`, `fvSolution`, `blockMeshDict`, `snappyHexMeshDict`)
- Turbulence models in `turbulenceProperties`/`momentumTransport`: what each of the 29 models is, quoted from its own OpenFOAM header with the paper that defines it, and every coefficient's source-extracted default per fork and version
- Extend with your own schema modules (plain Python files)

**[BlockMesh 3-D viewer](USER_GUIDE.md#blockmesh-panel)** *(requires pyvista / pyvistaqt)*
- Interactive 3-D preview of `blockMeshDict` geometry — vertices, blocks, and boundary faces colour-coded by patch type — with `$variable` and `#eval` references resolved automatically
- Overlays `topoSetDict` action geometry, `snappyHexMeshDict` `geometry {}` shapes (classified as surface / region / geometry-only), and `setFieldsDict` regions (labelled with their `fieldValues`), each with per-shape visibility toggles; shapes larger than the block mesh are clipped in the view and marked "(clipped)"
- Vertices table beside the 3-D view: edit a coordinate and see the change instantly; a Preview mode explores variable-based vertices without touching the file
- Load STL/OBJ overlays — several at once, each with its own row and colour in the `STL ▾` menu — and export topoSet/snappyHexMesh/setFields shapes as STL files
- **⊞** side-by-side mode shows the 3-D view next to the tree while editing `blockMeshDict`, `topoSetDict`, `snappyHexMeshDict`, or `setFieldsDict`

**[Integrated terminal](USER_GUIDE.md#terminal-tab)**
- Full PTY xterm.js terminal (Linux/macOS) with a simple QProcess-based fallback, switchable at runtime; automatically changes to the case directory when a case is opened
- Omitted entirely in the `no-terminal` variants (Windows-friendly)

**[Tools menu](USER_GUIDE.md#foammonitor-launcher)**
- Run `blockMesh`, `snappyHexMesh`, `topoSet`, `setFields`, or `checkMesh` in the terminal with one click (output saved to `log.*`), or restore `0/` from `0.orig`
- Run the case's `Allrun`/`Allclean` scripts, or clean the case back to a pristine state with `foamCleanTutorials`
- Launch `foamMonitor` to plot residuals with gnuplot while the solver runs
- Open the generated mesh in ParaView
- View a condensed summary of a `log.*` file instead of scrolling through thousands of raw lines
- Find OpenFOAM examples: search an installation's `tutorials/` and `etc/caseDicts/` templates for real usage of a keyword, preview hits, load one into the compare view, or duplicate a tutorial case as the starting point for your own

**[Case comparison](USER_GUIDE.md#case-comparison)**
- Compare the open case against any reference case: colour-coded diff overlay in the tree, `≠N` markers in the file list, and a changed-files-only filter
- Side-by-side reference tree with right-click **Use this value** to adopt individual settings

**[Appearance](USER_GUIDE.md#appearance-and-colours)**
- **Settings > Appearance** — **Follow System** (default), **Light**, or **Dark** (takes effect after restart); the theme covers the whole UI, including the editor's syntax highlighting, diff row colours, and the BlockMesh 3-D viewer's scene, rather than leaving the 3-D view a fixed white rectangle in a dark window

**UI language**
- **Settings > Language** — switch between English and 日本語 (takes effect after restart); add more languages by dropping a translation file into `i18n/`

**[Reference links](USER_GUIDE.md#resources-dialog)**
- **Help > Resources...** — official OpenFOAM documentation links, plus a personal **My Links** list

## Full Reference

For detailed documentation of every panel, menu, and workflow, see [USER_GUIDE.md](USER_GUIDE.md).
For project structure, dev setup, and testing, see [DEVELOPER.md](DEVELOPER.md).
For annotated screenshots of the app, see [docs/SCREENSHOTS.md](docs/SCREENSHOTS.md).

## Example Cases

The `tutorials/` directory in the repository root contains ready-to-open OpenFOAM cases:

| Directory | Solver | Purpose |
|---|---|---|
| `tutorials/cavity/cavity/` | `icoFoam` | Single-region end-to-end workflow walkthrough |
| `tutorials/cavity/cavityGrade/` | `icoFoam` | Non-uniform grading (`simpleGrading`) |
| `tutorials/cavity/cavityClipped/` | `icoFoam` | Clipped geometry; `mapFieldsDict` |
| `tutorials/snappyMultiRegionHeater/` | `chtMultiRegionFoam` | Multi-region case for the boundary view and region file listing |
| `tutorials/damBreak/` | `interFoam` | Two-phase flow; tests `setFieldsDict` and `0.orig/` |
| `tutorials/pitzDaily/` | `simpleFoam` | The canonical RAS case; the only bundled case that is not laminar, so it is where the turbulence-model help is visible |
| `tutorials/oneBlocks/` | `icoFoam` | 3-D single-block; `blockMeshDict` editing and 3-D mesh viewer |
| `tutorials/oneBlocks-vars/` | `icoFoam` | As `oneBlocks` with variable substitution and compact face notation |
| `tutorials/nineBlocks/` | `icoFoam` | 3×3 multi-block; regex boundary patches |
| `tutorials/nineBlocks-vars/` | `icoFoam` | As `nineBlocks` with variable substitution and compact face notation |
| `tutorials/topoSetShapes/` | `icoFoam` | Every `topoSetDict` geometry source the 3-D viewer can overlay, in one 3×3×3 block |
| `tutorials/samplingShapes/` | `icoFoam` | The same for the sampling overlay: probe points, lines, a point cloud and both plane spellings |

The `cavity/` cases, `snappyMultiRegionHeater`, `damBreak`, and `pitzDaily` are from the OpenFOAM v2512 standard tutorial set. The `oneBlocks*` and `nineBlocks*` cases are custom `blockMeshDict` cases derived from cavity for FoDE testing.

**License:** these case files are licensed under the **GPL-3.0** (not the AGPL-3.0 that covers FoDE source code). See `tutorials/README.md` for full provenance and license details.

## Citation

Citation is not required, but if FoDE has been useful in your research, a citation is welcome and helps support continued development:

> Shinji Nakagawa,
> Foam Dictionary Editor: A GUI-based open-source tool for OpenFOAM case configuration,
> *SoftwareX*, Volume 35, 2026, 102852, ISSN 2352-7110,
> [https://doi.org/10.1016/j.softx.2026.102852](https://doi.org/10.1016/j.softx.2026.102852)
> ([ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2352711026003444))

## License

Copyright (C) 2025-2026 Shinji NAKAGAWA. Released under the [GNU Affero General Public License v3.0 or later](LICENSE) (AGPL-3.0-or-later).

Some material here comes from OpenFOAM and is **not** covered by that licence: the bundled tutorial cases, the extracted keyword list, and the documentation quoted in the generated turbulence schema modules. That material is GPL-3.0-or-later and is held by several parties — the OpenFOAM Foundation, OpenCFD Ltd, Upstream CFD GmbH and Keysight Technologies. See [THIRD-PARTY.md](THIRD-PARTY.md) for per-file credits, generated from the sources rather than maintained by hand.

## Disclaimer

This offering is not approved or endorsed by OpenCFD Limited, producer and distributor of the OpenFOAM software via [www.openfoam.com](http://www.openfoam.com/), and owner of the OPENFOAM® and OpenCFD® trade marks.

## Acknowledgements

- [PySide6 (Qt for Python)](https://doc.qt.io/qtforpython/) — GUI framework (LGPL v3)
- [pyVista](https://pyvista.org/) / [VTK](https://vtk.org/) — 3-D viewer for `blockMeshDict`, `topoSetDict`, and `snappyHexMeshDict` geometry (BSD-3-Clause, optional)
- [xterm.js](https://xtermjs.org/) — Terminal emulator used in the Terminal panel (MIT). Downloaded automatically from jsDelivr on first launch and cached in `ui/xterm/`
- [pytest](https://pytest.org/) / [pytest-qt](https://pytest-qt.readthedocs.io/) — Test framework (development only)

Special thanks to the [OpenFOAM Foundation](https://openfoam.org/) and [OpenCFD / ESI Group](https://www.openfoam.com/) and all contributors for developing and maintaining OpenFOAM as free, open-source CFD software.
