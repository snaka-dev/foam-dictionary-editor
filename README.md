# Foam Dictionary Editor (FoDE)

FoDE — Foam Dictionary Editor (pronounced "foh-dee")

A GUI editor for OpenFOAM dictionary files, built with Python and PySide6.

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

An internet connection is recommended on first launch — xterm.js (the terminal emulator) is downloaded automatically to `ui/xterm/`. Without it, a simple fallback terminal is used instead. Restart the app with internet access to retry, or place the files manually:

| File | URL |
|---|---|
| `xterm.js` | `https://cdn.jsdelivr.net/npm/@xterm/xterm@6.0.0/lib/xterm.js` |
| `xterm.css` | `https://cdn.jsdelivr.net/npm/@xterm/xterm@6.0.0/css/xterm.css` |
| `xterm-addon-fit.js` | `https://cdn.jsdelivr.net/npm/@xterm/addon-fit@0.11.0/lib/addon-fit.js` |

## Basic Workflow

1. **Launch**

   ```bash
   python3 main.py
   ```

2. **Open a case** — choose one:
   - *Your own case:* **Case > Open Case** → select your case directory
   - *Start from a tutorial:* **Case > Duplicate from Case Library** → browse `$FOAM_TUTORIALS` → copy to your working directory

3. **Select a file** from the left panel (e.g. `system/controlDict`, `0/U`)

4. **Edit** values in the Tree view or the raw Text editor at the bottom

5. **Check and adjust boundary conditions** in the **Boundary** tab — a table showing all patches and field variables at a glance

6. **Save** — `Ctrl+S` (current file) or `Ctrl+Shift+S` (all modified files)

7. *(Optional)* **Run your solver** from the **Terminal** tab — the terminal opens in the case directory, so you can run `blockMesh`, `interFoam`, or any other OpenFOAM command directly

## Key Features

**File management**
- Opens common dictionary files automatically (`controlDict`, `fvSchemes`, `fvSolution`, `blockMeshDict`, `snappyHexMeshDict`, and more)
- Detects multiRegion case structures and field directories (`0/`, `0.orig/`) automatically
- Add extra directories to the file list — all files inside are scanned automatically, just like `0/`. Useful for custom field directories (`initial/`), restart time steps (`0.5/`), or deep subdirectories (`lagrangian/chemkin/`)
- Add, create, duplicate, backup, or delete files from the file panel
- Save the current state as a new case, or duplicate an existing one

**Tree and text editing**
- Structured tree view for browsing and editing dictionary entries
- Raw text editor always available as a fallback
- Sync between tree and text in both directions
- Add, duplicate, comment out, or delete tree entries via right-click

**Boundary condition view**
- See all boundary conditions across all field variables in one table
- Edit, create, delete, copy, and paste patch entries directly in the table
- Add or delete a patch across all field files in one step

**Schema help**
- Built-in descriptions and valid choices for common settings (`controlDict`, `fvSchemes`, `fvSolution`, `blockMeshDict`, `snappyHexMeshDict`)
- Extend with your own schema modules (plain Python files)

**Integrated terminal**
- Full PTY terminal (Linux/macOS with `QtWebEngineWidgets`) or simple fallback
- Automatically switches to the case directory when a case is opened

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
- [xterm.js](https://xtermjs.org/) — Terminal emulator used in the Terminal panel (MIT). Downloaded automatically from jsDelivr on first launch and cached in `ui/xterm/`
- [pytest](https://pytest.org/) / [pytest-qt](https://pytest-qt.readthedocs.io/) — Test framework (development only)
