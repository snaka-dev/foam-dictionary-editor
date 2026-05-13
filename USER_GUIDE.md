# Foam Dictionary Editor (FoDE)

FoDE — Foam Dictionary Editor (pronounced "foh-dee")

## What is FoDE?

FoDE is a graphical editor for OpenFOAM case dictionary files. It lets you browse, edit, and manage dictionaries through a structured tree view or a plain-text editor — whichever suits the task. It is aimed at engineers and researchers who run OpenFOAM simulations and want a more convenient way to set up and modify case files.

## About This Guide

This is the full feature reference for FoDE. It covers every panel, menu, dialog, and workflow in detail. For installation and a quick-start walkthrough, see [README.md](README.md). For project structure, dev setup, and testing, see [DEVELOPER.md](DEVELOPER.md).

## Where to Find Things

| I want to… | Section |
|---|---|
| Browse and manage case files | [File list behavior](#file-list-behavior) |
| Edit boundary conditions in bulk | [Boundary view](#boundary-view) |
| Edit values in the tree | [Tree view context menu](#tree-view-context-menu) |
| Get help on a dictionary setting | [Detail pane](#detail-pane) |
| Add schema help for custom keys | [Schema module configuration](#schema-module-configuration) |
| Save or duplicate a case | [Duplicating a case](#duplicating-a-case) / [Saving as a new case](#saving-as-a-new-case) |
| Run OpenFOAM commands from FoDE | [Terminal tab](#terminal-tab) |
| Use tutorial or template cases | [Case Library](#case-library) |
| Understand tree ↔ text sync | [Tree and text workflow](#tree-and-text-workflow) |
| Configure application settings | [Application settings](#application-settings) |
| Open help links or reference sites | [Resources dialog](#resources-dialog) |

## Contents

- [Features](#features)
- [UI layout](#current-ui-layout)
- [Current case and file display](#current-case-and-file-display)
- [File list behavior](#file-list-behavior)
  - [Directory header markers](#directory-header-markers)
  - [Default target files](#default-target-files)
  - [MultiRegion cases](#multiregion-cases)
  - [Symbolic links](#symbolic-links)
  - [Adding files at runtime](#adding-files-at-runtime)
  - [Adding extra directories](#adding-extra-directories)
  - [Extra files and directories indicator](#extra-files-and-directories-indicator)
  - [Removing extra files and directories](#removing-extra-files-and-directories)
  - [Numeric time directory indicator](#numeric-time-directory-indicator)
  - [Creating a backup](#creating-a-backup)
  - [Creating a new file](#creating-a-new-file)
  - [Cleaning up backup files](#cleaning-up-backup-files)
  - [Deleting a file](#deleting-a-file)
  - [Duplicating a file](#duplicating-a-file)
  - [Duplicating a field directory](#duplicating-a-field-directory)
  - [Resetting the file list](#resetting-the-file-list)
- [Boundary view](#boundary-view)
  - [Table layout](#table-layout)
  - [Directory selector](#directory-selector)
  - [Transpose](#transpose)
  - [Editing a boundary condition](#editing-a-boundary-condition)
  - [Creating a patch entry](#creating-a-patch-entry)
  - [Deleting a patch entry](#deleting-a-patch-entry)
  - [Copy and paste](#copy-and-paste)
  - [Deleting a boundary condition across all field files](#deleting-a-boundary-condition-across-all-field-files)
  - [Adding a boundary condition across all field files](#adding-a-boundary-condition-across-all-field-files)
- [Schema module configuration](#schema-module-configuration)
- [Application settings](#application-settings)
- [Resetting settings](#resetting-settings)
- [Terminal tab](#terminal-tab)
- [Tree view context menu](#tree-view-context-menu)
- [Case Library](#case-library)
- [Resources dialog](#resources-dialog)
- [Saving as a new case](#saving-as-a-new-case)
- [Duplicating a case](#duplicating-a-case)
- [Tree and text workflow](#tree-and-text-workflow)
- [Detail pane](#detail-pane)
- [Behavior on parse failure](#behavior-on-parse-failure)
- [Editor behavior](#editor-behavior)
- [Supported syntax and node types](#supported-syntax-and-node-types)
- [Limitations](#limitations)
- [Disclaimer](#disclaimer)
- [Acknowledgements](#acknowledgements)

---

## Features

- Open an OpenFOAM case directory and list common dictionary files from the case.
- Load and edit a wide range of common dictionary files including `controlDict`, `fvSchemes`, `fvSolution`, `blockMeshDict`, `snappyHexMeshDict`, `transportProperties`, and many more when present.
- Automatically list all files found under the `0` and `0.orig` field directories.
- Automatically detect multiRegion case structures (e.g. `chtMultiRegionFoam`, `chtMultiRegionSimpleFoam`) and list per-region files under separate group headers such as `system/fluid` and `constant/heater`.
- Automatically collect phase-variant files such as `thermophysicalProperties.air` and `turbulenceProperties.water` that are present in `constant/` or per-region constant directories.
- Display symbolic links in the file list with a `⇢` marker and italic text; hovering shows the link target in the tooltip.
- Add files not in the default list to the file panel at runtime via right-click on a directory header.
- Add entire directories to the file list so that all files inside are scanned automatically, just like `0/` and `0.orig/`. Useful for custom field directories (`initial/`), restart time steps (`0.5/`), or deep subdirectories (`lagrangian/chemkin/`). Extra directories are shown with a distinct (purple) header. Right-click the **Results** indicator to add a numeric time directory directly; use **Settings > Manage Extra Files & Directories…** or the indicator button for arbitrary directories.
- Create a new file from a FoamFile template in any directory group via right-click on the directory header.
- Save per-case extra file and directory selections to `.foam-editor-files.json` inside the case directory.
- Show an indicator at the top of the file list when extra files or directories are registered for the current case, with a link to the management dialog.
- Remove extra files individually via right-click, or manage files and directories in bulk via the management dialog.
- Create a timestamped backup of any file via right-click on a file in the file list.
- Delete any file from disk via right-click on a file in the file list. A confirmation dialog offers three choices: create a backup and delete, delete without a backup, or cancel. The deletion cannot be undone.
- Clean up accumulated backup files for the current case via **Case > Clean Backup Files...**. A dialog lists all `.bak_*` files found in the case directory with checkboxes (all selected by default) and **Select All** / **Deselect All** buttons for quick bulk selection.
- Duplicate any file in the file list via right-click; a dialog prompts for a new name and the `object` field in the FoamFile header is updated automatically to the new name. If the source file has unsaved changes, the application asks whether to save first or duplicate with the unsaved state.
- Duplicate the `0/` or `0.orig/` directory to create the missing counterpart via right-click on the group header (shown only when exactly one of the two directories exists).
- View all boundary conditions across field variables at a glance in the **Boundary** tab. Rows are field files and columns are patches by default; a **Transpose** checkbox swaps the orientation. Double-click a cell to edit its content, or to create a new entry for a `–` cell. Right-click any cell to edit, create, delete, copy, or paste a boundary condition. Right-click a patch column/row header to delete that boundary condition from all field files, or to add a new patch entry across all field files.
- Show the parsed dictionary structure in a tree view.
- Indicate the presence of numeric time directories (OpenFOAM calculation results such as `0.5`, `1`, `10`) with a bold **Results: …** row at the bottom of the file list. The indicator shows up to six directory names and notes the total count when more exist. Hovering shows the full count and range. Right-clicking the indicator offers a submenu to add any listed directory to the file list as an extra directory.
- Hide the **Type** column in the tree by default; re-enable it with **View > Show Type Column**.
- View rich schema information for each setting in the right-side detail pane:
  description, available choices, applicable solver versions, and notes.
  Schema annotations are provided for a subset of common settings; not all keys are covered.
- Edit node values directly from the detail pane. When a fractional value is entered for an `int` node, the node type is automatically promoted to `scalar`.
- Customize or extend schema information by writing your own schema modules.
- Edit raw file text directly in the lower text editor.
- Show line numbers and the current line position in the editor.
- Rebuild raw text from the parsed tree with **Reload from Tree**.
- Rebuild the tree from edited text with **Apply Text to Tree**.
- Save the current file from the raw text editor with **Save File**.
- Save all modified files at once with **Save Case**.
- Duplicate the open case to a new directory with **Case > Duplicate Case**, choosing between a full directory copy or a copy of only the app-visible files.
- Save the currently open case as a new case with **Case > Save as New Case...**, which copies files from disk (all files or app-visible files only, selectable) and then writes any unsaved in-memory edits on top, then switches to the new case.
- Register reference case directories in the **Case Library** for quick access. The `$FOAM_TUTORIALS` directory is included automatically whenever the environment variable is set.
- Open a case directly from any Case Library directory with **Case > Open from Case Library...**.
- Duplicate a case from the Case Library into the working directory with **Case > Duplicate from Case Library...**, with the Default Case Directory pre-filled as the destination parent.
- Show a warning when the selected directory contains neither `system/` nor `constant/`, suggesting it may not be a valid OpenFOAM case, with an option to open it anyway.
- Add, duplicate, comment out, restore, or delete tree nodes via the right-click context menu in the tree view.
- Copy and paste node values in the tree view via right-click context menu or Ctrl+C / Ctrl+V.
- Run shell commands in the integrated **Terminal** tab at the bottom of the window. The terminal automatically changes to the case directory when a case is opened.
- Undo, redo, cut, copy, paste, select all, and find text via the edit toolbar.
- Keep the text editor usable even if parsing fails.
- Configure schema modules and application settings at runtime via the **Settings** menu.
- Open **Help > Resources...** to access official OpenFOAM documentation links and manage personal reference links. The **My Links** tab lets you add, edit, reorder, and remove links; double-click any entry to open it in your browser. Links are saved to `app_config.json`.

## Current UI layout

![Main window — Tree and Editor tabs](docs/images/main-window-tree-editor.png)

The main window is divided into two top-level columns separated by a horizontal splitter.

- **Left column** — file list for the selected OpenFOAM case (full window height).
- **Right column** — a vertical splitter with two rows:
  - **Upper row** — a tab widget with two tabs:
    - **Tree** tab — parsed dictionary tree (center) and detail editor (right).
    - **Boundary** tab — boundary condition table for all field variables (see [Boundary view](#boundary-view)).
  - **Lower row** — tabbed panel with two tabs:
    - **Editor** — plain-text editor with line numbers.
    - **Terminal** — integrated terminal (see [Terminal tab](#terminal-tab) below).

The top action bar contains the frequently used commands and the current case and file display.

- Save File.
- Save Case.
- Apply Text to Tree.
- Reload from Tree.
- Case: current case name display.
- File: current file name display.

A second edit toolbar provides text editing operations.

- Undo, Redo.
- Cut, Copy, Paste, Select All.
- Find, Find Next.

The menu bar provides a **Case** menu, a **View** menu, a **Settings** menu, and a **Help** menu.

**Case menu:**

- Case > Open Case `Ctrl+O`.
- Case > Open from Case Library...
- Case > Duplicate Case...
- Case > Duplicate from Case Library...
- Case > Save as New Case...
- Case > Clean Backup Files...
- Case > Save File `Ctrl+S`.
- Case > Save Case `Ctrl+Shift+S`.
- Case > Exit `Ctrl+Q`.

**View menu:**

- View > Show Type Column (checkable; hidden by default).

**Settings menu:**

- Settings > Set Default Case Directory.
- Settings > Manage Case Library…
- Settings > Manage Extra Files & Directories…
- Settings > Reset File List.
- Settings > Manage Schema Modules.
- Settings > Reset Window Size.
- Settings > Reset All Settings…

**Help menu:**

- Help > About Foam Dictionary Editor (FoDE)...
- Help > Resources...

## Current case and file display

The top bar shows the current case as its directory name and the current file as `parent-directory/file-name`. For example, `system/controlDict` and `constant/transportProperties` are shown in that form.

If no case or file is loaded, the labels show `-`.

## File list behavior

The file list is populated by `services/case_loader.py`. The implementation combines a fixed list of common dictionary files, per-case user-added files, and automatic enumeration of field files.

### Directory header markers

Each directory group in the file list is shown as a bold header. A `[+]` suffix is added to a header when files exist in that directory on disk but are not currently in the file list. No marker is shown when all files in the directory are already listed.

### Default target files

**system/**

- `blockMeshDict`
- `changeDictionaryDict`
- `controlDict`
- `createBafflesDict`
- `createPatchDict`
- `decomposeParDict`
- `extrudeMeshDict`
- `fvOptions`
- `fvSchemes`
- `fvSolution`
- `meshQualityDict`
- `mirrorMeshDict`
- `refineMeshDict`
- `setFieldsDict`
- `snappyHexMeshDict`
- `surfaceFeatureExtractDict`
- `topoSetDict`

**constant/**

- `boundaryRadiationProperties`
- `dynamicMeshDict`
- `fvOptions`
- `g`
- `kinematicCloudProperties`
- `radiationProperties`
- `regionProperties`
- `thermophysicalProperties`
- `transportProperties`
- `turbulenceProperties`

In addition, all files found directly inside the `0` and `0.orig` directories of the case are listed automatically when those directories exist.

Phase-variant files matching `thermophysicalProperties.*` and `turbulenceProperties.*` (for example `thermophysicalProperties.air`) are collected automatically via glob from `constant/` and from each per-region constant directory.

### MultiRegion cases

When subdirectories are found inside `system/`, the editor treats them as region names and builds additional file groups. The following files are listed per region when present:

**system/\<region\>/**

- `changeDictionaryDict`
- `decomposeParDict`
- `fvOptions`
- `fvSchemes`
- `fvSolution`
- `meshQualityDict`

**constant/\<region\>/**

- `boundaryRadiationProperties`
- `dynamicMeshDict`
- `fvOptions`
- `radiationProperties`
- `thermophysicalProperties`
- `turbulenceProperties`

Each region directory appears as its own group header in the file list (for example `system/fluid`, `constant/heater`). Region groups are sorted after the top-level `system` and `constant` groups.

### Symbolic links

Symbolic links in the file list are shown with a `⇢` marker appended to the file name and the item text is rendered in italic. Hovering over the item shows a tooltip containing the path and the link target. Editing a symlink writes through to the target file, exactly as the operating system resolves the link.

### Adding files at runtime

Right-click any directory header in the file list to open a context menu with the following actions.

- **New file in '\<dir\>'...** — create a new file from a FoamFile template (see [Creating a new file](#creating-a-new-file)).
- **Add files from '\<dir\>'...** — add existing files to the file list. A dialog lists all files in that directory that are not yet shown. Select one or more and click **OK** to add them.
- **Remove '\<dir\>' from file list** — removes an extra directory from the file list. Shown only on extra-directory headers (see [Adding extra directories](#adding-extra-directories)).
- **Duplicate '\<dir\>' → '\<counterpart\>'...** — copy a `0/` or `0.orig/` directory to create the missing counterpart (see [Duplicating a field directory](#duplicating-a-field-directory)). This action is shown only for `0` and `0.orig` headers, and only when exactly one of the two directories is present.

Added files are saved to `.foam-editor-files.json` in the case directory and are restored the next time the case is opened. The config file is also copied when **Duplicate Case** uses the app-visible files only mode.

Extra files are displayed in a distinct colour in the file list so they can be told apart from the default target files at a glance.

### Adding extra directories

Any directory inside the case root can be added to the file list so that all files directly inside it are scanned and listed automatically, in the same way as `0/` and `0.orig/`. This is useful for:

- Custom field directories used by non-standard solvers (e.g. `initial/` for `laserBeamFoam`).
- Restart time steps you want to browse and edit (e.g. `0.5/`, `1/`).
- Deep subdirectories with supplementary dictionaries (e.g. `lagrangian/sprayFoam/aachenBomb/chemkin/`).

Extra directory group headers are shown in **purple** to distinguish them from built-in groups. The `[+]` unlisted-files marker is never shown for extra directories because all files are already loaded.

**Adding a time directory via the Results indicator:**  
Right-click the **Results: …** row at the bottom of the file list. A submenu lists each time directory; click one to add it. Directories already added are greyed out.

**Adding an arbitrary directory via the management dialog:**  
Open **Settings > Manage Extra Files & Directories…** (or click the indicator button at the top of the file list). In the **Extra Directories** tab, click **Add Directory…**. A folder picker opens rooted at the case directory; select any subdirectory and click **OK**. The selected directory is added immediately and the file list refreshes.

**Removing an extra directory:**  
Right-click the (purple) directory header in the file list and select **Remove '\<dir\>' from file list**, or use the **Extra Directories** tab in the management dialog (check the entry, then click **Remove Selected**).

Files created or duplicated inside an extra directory are not added to the extra-files list — they are already visible because the whole directory is scanned.

### Extra files and directories indicator

When extra files or directories are registered for the current case, a button appears at the top of the file list panel showing the count (e.g. **Extra files: 2, directories: 1 — Manage…**). Clicking it opens the **Manage Extra Files & Directories** dialog, which has two tabs.

- **Extra Files** — lists all individually registered extra files. Select one or more and click **Remove Selected** to remove them.
- **Extra Directories** — lists all registered extra directories. Click **Add Directory…** to add a new one via a folder picker. Select one or more and click **Remove Selected** to remove them.

Changes take effect immediately when the dialog is closed. When neither extra files nor extra directories are registered the indicator is hidden.

### Removing extra files and directories

**Extra files:**
- **Right-click** an extra file (shown in blue) in the file list and select **Remove from extra files**. The file is removed immediately.
- Open the management dialog and use the **Extra Files** tab to remove one or more files at once.

**Extra directories:**
- **Right-click** the purple directory header and select **Remove '\<dir\>' from file list**. All files from that directory disappear from the list immediately.
- Open the management dialog and use the **Extra Directories** tab to remove one or more directories at once.

Removing an extra file or directory from the list does not delete anything from disk. It only removes it from the per-case configuration so it no longer appears in the file list.

### Numeric time directory indicator

When numeric directories (OpenFOAM calculation results such as `0.5`, `1`, `10`) are found at the case root — excluding `0`, `0.orig`, and any directories already added as extra directories — a non-selectable **Results: …** row is appended at the bottom of the file list. The indicator is rendered in bold gray text and lists up to six directory names. When more than six exist, a `(+N more)` suffix is added. Hovering shows the total count and, for multiple directories, the first and last in the sorted range.

Right-click the indicator to add any of the listed directories to the file list as an extra directory (see [Adding extra directories](#adding-extra-directories)). Once a directory is added, it no longer appears in the Results indicator and instead shows as a full group header.

### Creating a backup

Right-click any file in the file list and select **Create Backup**. A copy of the file is saved in the same directory with a timestamp suffix, for example `controlDict.bak_20260502_143022`.

The backup captures the current in-memory buffer if the file has been loaded, so unsaved edits are included. If the file has not been loaded yet, the on-disk version is copied. A confirmation message is shown in the status bar, and if the backup includes unsaved edits that note is appended to the message.

### Creating a new file

Right-click a directory header in the file list and select **New file in '\<dir\>'...**. An input dialog prompts for a file name. The file is created at `<case_dir>/<dir>/<name>` with a minimal FoamFile dictionary header. The file is opened automatically in the editor after creation.

Files created in directories other than `0/` and `0.orig/` are registered in `.foam-editor-files.json` so they persist across sessions.

### Cleaning up backup files

Select **Case > Clean Backup Files...** to remove accumulated `.bak_*` files from the current case. The dialog scans the entire case directory recursively and lists every file whose name matches the `.bak_YYYYMMDD_HHMMSS` pattern, showing each relative path and file size.

All files are checked by default. Use the checkboxes to select individual files, or use **Select All** / **Deselect All** to change the entire selection at once. The **Delete Selected (N)** button shows the current count of checked files and is disabled when nothing is selected.

Clicking **Delete Selected** deletes the checked files from disk immediately, with no further confirmation. If any deleted file was open in the editor, the editor and tree view are cleared. If any error occurs (e.g. a permission problem), a summary is shown after the operation.

If no backup files are found, the dialog shows a message and offers only a **Close** button.

### Deleting a file

Right-click any file in the file list and select **Delete file...**. A confirmation dialog shows the file name and three choices.

- **Backup && Delete** — creates a timestamped backup in the same directory (for example `controlDict.bak_20260506_143022`) and then deletes the original. The backup captures the current in-memory buffer, so unsaved edits are included. If the backup write fails, the deletion is aborted.
- **Delete** — deletes the file immediately without creating a backup.
- **Cancel** (default) — aborts the operation.

If the file has unsaved changes, the dialog shows an additional warning. The deleted file is removed from the in-memory buffers, the dirty-state tracking, and the per-case extra files configuration. If the deleted file was open in the editor, the editor and tree view are cleared. The file list is refreshed after deletion.

This action deletes the file from disk and cannot be undone.

### Duplicating a file

Right-click any file in the file list and select **Duplicate...**. An input dialog pre-fills the current file name and prompts for a new name. The duplicate is written to the same directory and the `object` field inside the FoamFile header is updated to match the new file name.

If the source file has unsaved changes, the application presents three choices.

- **Save and Duplicate** — save the file first, then duplicate the saved content.
- **Duplicate with Unsaved Changes** — duplicate the current in-memory buffer as-is.
- **Cancel** — abort the operation.

Files duplicated outside `0/` and `0.orig/` are registered in `.foam-editor-files.json`.

### Duplicating a field directory

Right-click the `0` or `0.orig` header in the file list and select **Duplicate '\<dir\>' → '\<counterpart\>'...**. This action copies the entire directory to create the missing counterpart (`0/` → `0.orig/` or `0.orig/` → `0/`). The action is shown only when exactly one of the two directories is present. A confirmation dialog is displayed before the copy begins.

### Resetting the file list

Select **Settings > Reset File List** to remove all user-added files and directories for the current case. This deletes `.foam-editor-files.json` from the case directory and reloads the file list with the default target files only.

## Boundary view

![Main window — Boundary and Editor tabs](docs/images/main-window-boundary-editor.png)

The **Boundary** tab in the upper right panel shows a table of boundary conditions for all field variable files in the current field directory.

### Table layout

**Default orientation:**
- **Rows** — one per field variable file, sorted by file name (`epsilon`, `k`, `nut`, `p`, `U`, etc.).
- **Columns** — one per boundary patch name, sorted alphabetically.

**Transposed orientation** (enable with the **Transpose** checkbox): rows become patches and columns become field files.

In both orientations:
- The column set is the union of all patch names across all field files; cells show `–` when a patch is not defined in a given file.
- **Cell text** — the `type` value for that patch (e.g. `fixedValue`, `zeroGradient`, `noSlip`). A `†` marker is appended when the patch contains large or binary data that cannot be shown in the edit dialog.
- **Tooltip** — hovering over a cell shows the full patch sub-dictionary text. For `†`-marked cells, the tooltip shows the type and a brief data description (`large data` or `binary data`) instead.
- **Lines per cell** — a spin box at the top right of the panel controls how many lines are shown per cell (1–10, default 1). When set above 1, additional key-value entries from the patch sub-dictionary are shown below the `type` line. Entries with large or complex values display as `key  …`.

### Directory selector

A drop-down at the top of the panel selects which field directory to display. It shows `0` and `0.orig` when they exist, plus any extra directories that contain at least one parseable field file (i.e. a file with a `boundaryField` dictionary). When only one qualifying directory exists, the selector is disabled. The table is rebuilt automatically when the selection changes.

### Transpose

Check the **Transpose** checkbox at the top of the panel to swap rows and columns. The table is rebuilt immediately. All other operations (edit, create, copy, paste) work the same in both orientations.

### Editing a boundary condition

Double-click a cell (or right-click → **Edit**) to open the **Edit boundary** dialog. The dialog header shows the variable name and patch name in read-only form.

**Normal mode** (no `†` marker) — the full content of the patch sub-dictionary is shown in an editable text area. Edit any lines, including `type`, and click **OK** to apply. If the content is unchanged, **OK** has no effect and the file is not marked as modified.

**Complex mode** (`†` marker) — the patch contains a large nonuniform field or binary data. Only the `type` field is editable here; use the **Text Editor** tab to modify the full value.

### Creating a patch entry

When a cell shows `–`, the patch is not yet defined in that field file. Double-click the cell (or right-click → **Create Entry**) to open an empty **Edit boundary** dialog. Enter the patch content and click **OK** to create the entry. The new entry is appended to `boundaryField` in that file, and the cell updates immediately.

### Deleting a patch entry

Right-click a cell with a defined patch and select **Delete Entry** to remove that patch from the specific field file. The row or column for that patch is removed from the table if the patch no longer exists in any file.

### Copy and paste

Right-click any cell with a defined patch and select **Copy** to store that patch's full content in an internal clipboard. Then right-click any other cell (including `–` cells) and select **Paste** to apply the copied content. Pasting into a `–` cell creates the entry; pasting into an existing cell replaces its content. The clipboard persists within the application session.

### Deleting a boundary condition across all field files

Right-click a patch column header (non-transposed view) or a patch row header (transposed view) and select **Delete BoundaryField '\<patch\>'**. A confirmation dialog lists the affected field files. Clicking **Yes** removes that patch entry from every field file in the current directory in one step.

### Adding a boundary condition across all field files

Right-click a patch column header or patch row header and select **Add BoundaryField...**. Enter the new patch name. A confirmation dialog states how many field files will receive an empty entry. Clicking **Yes** appends an empty `<patch> {}` block to each file that has a `boundaryField` dictionary but does not yet contain that patch. Edit individual cells afterwards to fill in the boundary condition content.

### No-type cells

Cells whose patch sub-dictionary has no `type` key are displayed in italic text. All other interactions (edit, delete, copy, paste) work identically.

Changes from all boundary view operations are immediately reflected in the tree view and text editor. Files modified through the boundary view are marked dirty (`*`) in the title bar and file list, the same as any other edit.

## Schema module configuration

Schema definitions for each dictionary type are managed in the `schemas/` directory. The runtime schema registry is handled by `schemas/registry.py`, and the default built-in configuration is defined in `schemas/builtin.py`.

Built-in schema modules:

- `schemas/control_dict.py` — schema for `controlDict`. Covers `startFrom`, `stopAt`, `writeControl`, `writeFormat`, `writeCompression`, `timeFormat`, `graphFormat`, `runTimeModifiable`, `adjustTimeStep`, and `purgeWrite`.
- `schemas/fv_schemes.py` — schema for `fvSchemes`.
- `schemas/fv_solution.py` — schema for `fvSolution`.
- `schemas/block_mesh_dict.py` — schema for `blockMeshDict`. Covers the top-level scaling keys (`convertToMeters`, `scale`), `mergeType`, and `verbose`.
- `schemas/snappy_hex_mesh_dict.py` — schema for `snappyHexMeshDict`. Covers the three phase-toggle keys (`castellatedMesh`, `snap`, `addLayers`) and the most common settings inside `castellatedMeshControls`, `snapControls`, `addLayersControls`, and `meshQualityControls`.

Which schema modules to load is controlled at runtime via `schema_config.json`. You can add or remove schema modules without modifying the source code.

### Writing a custom schema module

Each schema module must define two module-level names.

- `TARGET_FILE` — the dictionary filename the module applies to (e.g. `"controlDict"`).
- `SCHEMAS` — a `dict[str, KeySchema]` mapping entry keys to their schema definitions.

The registry imports each configured module and reads these two names. Any module that follows this convention can be added through **Settings > Manage Schema Modules** without further configuration.

### schema_config.json

`schema_config.json` is created the first time the user modifies schema settings via **Settings > Manage Schema Modules** or triggers a settings reset. If the file does not exist, the built-in default modules are used in memory without writing to disk. The file records the list of schema modules to load.

```json
{
  "schema_modules": [
    "schemas.control_dict",
    "schemas.fv_schemes",
    "schemas.fv_solution",
    "schemas.block_mesh_dict",
    "schemas.snappy_hex_mesh_dict"
  ]
}
```

To add a custom schema module, select **Settings > Manage Schema Modules** in the application, then use the **Add Module from File** button to select a Python file. The change is saved to `schema_config.json` and takes effect immediately.

## Application settings

General application settings are stored in `app_config.json`, which is separate from `schema_config.json`. This file is created the first time a case is opened (which triggers an automatic save of the case directory). If the file does not exist, built-in defaults are used. Settings are managed internally by the `app_config` package (`app_config/app_config_manager.py`).

### app_config.json

```json
{
  "window_size": [1200, 800],
  "default_case_dir": "/path/to/cases",
  "case_library_dirs": ["/home/user/my_templates"],
  "user_links": [{"label": "My reference", "url": "https://example.com"}]
}
```

| Key | Description |
|---|---|
| `window_size` | Main window size on startup. Saved automatically when the application is closed. |
| `default_case_dir` | Initial directory shown when **Case > Open Case** is used. Updated automatically to the parent of the last opened case. Also used as the default destination parent in **Case > Duplicate from Case Library...** and **Case > Save as New Case...**. |
| `case_library_dirs` | User-added Case Library directories. The `$FOAM_TUTORIALS` directory is not stored here; it is included dynamically from the environment variable. |
| `user_links` | User-defined reference links shown in **Help > Resources... > My Links**. Each entry is `{"label": "…", "url": "…"}`. |

### Setting the default case directory

Select **Settings > Set Default Case Directory** to set the directory that opens when **Case > Open Case** is used. The directory is also updated automatically to the parent of the last opened case, so the next session starts from the same location.

### Window size

The main window opens at the size recorded in `app_config.json`. If the file does not exist, the default size of 1200×800 is used. The size is saved automatically on exit. To restore the default size, select **Settings > Reset Window Size**.

## Resetting settings

Select **Settings > Reset All Settings** to reset `app_config.json`, `schema_config.json`, or both to their default values. A confirmation dialog is shown before any changes are made.

## Terminal tab

The bottom panel contains an **Editor** tab and a **Terminal** tab. The terminal implementation is selected automatically at startup.

- **Linux / macOS with `PySide6.QtWebEngineWidgets` available** — A full PTY-based terminal powered by [xterm.js](https://xtermjs.org/) v6 rendered in a `QWebEngineView`. It provides full VT100/xterm emulation with colour output, cursor control, and support for interactive programs such as `vim` and `htop`. The tab is labelled **Terminal**.
- **Windows or when `QtWebEngineWidgets` is absent** — `SimpleTerminalWidget` is used, a `QProcess`-based fallback that runs a persistent shell (`bash` on Linux/macOS, `cmd.exe` on Windows) and displays output in a plain-text area. ANSI escape codes are stripped from the output. The tab is labelled **Terminal (Simple)**.

When a case is opened, the terminal automatically changes its working directory to the case root so that OpenFOAM commands such as `blockMesh` or `interFoam` can be run directly.

### xterm.js assets

The xterm.js library files are downloaded automatically from jsDelivr on first use and cached in `ui/xterm/`. No manual installation is required. If the download fails (e.g. no internet access), a message is displayed instead; place the following files in `ui/xterm/` manually:

| File | Source |
|---|---|
| `xterm.js` | `https://cdn.jsdelivr.net/npm/@xterm/xterm@6.0.0/lib/xterm.js` |
| `xterm.css` | `https://cdn.jsdelivr.net/npm/@xterm/xterm@6.0.0/css/xterm.css` |
| `xterm-addon-fit.js` | `https://cdn.jsdelivr.net/npm/@xterm/addon-fit@0.11.0/lib/addon-fit.js` |

### SimpleTerminalWidget

`SimpleTerminalWidget` supports basic command-line interaction:

- Type a command in the input field at the bottom and press **Enter** to run it.
- Use the **↑** and **↓** arrow keys to navigate command history.
- Click **Clear** to clear the output area.
- If the shell process exits unexpectedly, it is restarted automatically.
- The shell process is terminated cleanly when the application closes.

## Tree view context menu

Right-click any row in the center tree view to open a context menu. Items are grouped by function.

### Value copy and paste

- **Copy Value** — copies the display text from the Value column of the selected row to the system clipboard. Ctrl+C when the tree has keyboard focus does the same.
- **Paste Value** — applies the clipboard text to the Value column of the selected row using the same parsing path as direct cell editing. Ctrl+V when the tree has focus does the same.

**Paste Value** is disabled when the selected node type does not support value editing (for example, `dictionary` nodes that show an entry count). If the pasted text cannot be parsed for the node type (for example, a non-numeric string pasted into a `scalar` node), the paste is silently rejected and a status-bar message is shown.

Ctrl+C and Ctrl+V are scoped to the tree widget and do not interfere with the text editor at the bottom. When a tree cell is in inline-edit mode, the shortcuts go to the inline editor as usual.

### Adding and duplicating entries

- **Add Entry After** — inserts a new `word`-typed entry (`newKey / newValue`) as a sibling immediately after the selected node and opens the key cell for inline editing. Enabled when the parent is a dictionary or the root.
- **Add Child Entry** — inserts a new entry as the last child of the selected node. Enabled only when the selected node is a `dictionary`.
- **Duplicate** — deep-copies the selected node and its subtree, inserting the copy immediately after the original.

### Commenting and deleting

- **Comment Out** — converts the selected entry into a commented-out `unknown_raw_entry` by prepending `// ` to every non-blank line of its rendered text. The result is written back into the file as a block comment. Disabled when the entry is already commented out.
- **Restore from Comment** — reverses **Comment Out**: strips the `// ` prefix from each line, re-parses the result, and replaces the `unknown_raw_entry` with the recovered node(s). Enabled only when every non-blank line of the entry starts with `//`.
- **Delete** — removes the selected node after a Yes/No confirmation dialog. This cannot be undone.

## Case Library

The Case Library is a set of directories used as sources for browsing and duplicating reference cases. It is intended to provide quick access to `$FOAM_TUTORIALS` and other template case collections without navigating the filesystem from scratch each time.

### Automatic inclusion of $FOAM_TUTORIALS

When the `FOAM_TUTORIALS` environment variable is set and points to an existing directory, that directory is automatically included at the top of the Case Library list on every application start. It does not need to be added manually and is not stored in `app_config.json`. If the variable is unset or the directory does not exist, it is simply absent from the list.

### Managing user-added directories

Select **Settings > Manage Case Library...** to open the library management dialog. The dialog shows two sections.

- **Auto-detected (read-only)** — shows the `$FOAM_TUTORIALS` path if the environment variable is active. This entry cannot be removed here; it disappears automatically when the variable is unset.
- **User-added directories** — directories you have added manually. Use **Add Directory...** to browse for a directory to register. Check one or more entries and click **Remove Selected (N)** to remove them. Changes are saved to `app_config.json`.

### Opening a case from the library

Select **Case > Open from Case Library...** to browse within a library directory and open a case from it. If multiple library directories are registered (including the auto-detected one), the application first asks which library to start from via a drop-down prompt, then opens a directory picker rooted at the chosen library.

### Duplicating a case from the library

Select **Case > Duplicate from Case Library...** to copy a case from the library into your working directory. The workflow is as follows.

1. Choose a library directory (if more than one is available).
2. Navigate to and select the source case inside that library.
3. A duplicate dialog opens with the **Default Case Directory** pre-filled as the destination parent.
4. Adjust the destination and name if needed, then click **OK** to copy.
5. After a successful copy, the application offers to open the new case immediately.

The copy mode options (full copy vs. app-visible files only) are the same as for **Case > Duplicate Case**.

## Resources dialog

Select **Help > Resources...** to open the Resources dialog. It has two tabs.

### OpenFOAM tab

Displays links to official OpenFOAM documentation for the two main distributions — OpenCFD/ESI Group (openfoam.com) and the OpenFOAM Foundation (openfoam.org). These links are fixed and read-only. This application is not affiliated with either organisation.

### My Links tab

Lets you manage a personal list of reference links.

- **Add** — opens a dialog to enter a label and a URL. The label is optional; if left blank, the URL is used as the display text.
- **Edit** — opens the same dialog pre-filled with the selected entry's label and URL.
- **Remove** — deletes the selected entry from the list.
- **Move Up / Move Down** — reorders the selected entry.
- **Double-click** an entry to open its URL in the default browser.

Changes are saved to `app_config.json` when the dialog is closed.

## Saving as a new case

Select **Case > Save as New Case...** to write the current editor state to a new case directory and immediately switch to it. Unlike **Duplicate Case** (which copies files from disk), this operation captures whatever is in the in-memory buffers — including unsaved edits — so the new case reflects the exact state visible in the editor at the moment the command is used. The original case is not modified.

A dialog shows the following fields.

- **Save in** — the parent directory for the new case (defaults to the parent of the current case).
- **New case name** — the name for the new case directory (defaults to the current name with `_new` appended).
- **Destination** — a live preview of the full destination path.
- **Copy mode** — controls which files are copied from disk before unsaved edits are applied:
  - **Copy app-visible files only** (default) — copies only the files shown in the file panel. Lightweight; excludes mesh data, processor directories, and result time steps.
  - **Copy all files** — full directory copy using `shutil.copytree`. Includes everything: mesh data, processor directories, existing result time steps, logs, etc.

In both modes, any unsaved in-memory edits are written into the new case on top of the copied files. The original case is not modified.

After the copy, the application opens the new case automatically.

## Duplicating a case

Select **Case > Duplicate Case** to save a copy of the current case under a new name. A dialog is shown with the following fields.

- **Save in** — the parent directory for the new case (defaults to the parent of the current case).
- **New case name** — the name for the new case directory (defaults to the current name with `_copy` appended).
- **Destination** — a live preview of the full destination path.
- **Copy mode** — choose how files are copied:
  - **Copy all files** (default) — performs a full directory copy using `shutil.copytree`. Every file and subdirectory under the case root is included, such as mesh data, time-step directories, and log files.
  - **Copy app-visible files only** — copies only the files listed in the file panel (`system/controlDict`, `fvSchemes`, `fvSolution`, etc., and all files under `0/` and `0.orig/`). Files not shown by the application, such as `constant/polyMesh`, `processor*/`, and arbitrary time-step directories, are not copied.

If the destination already exists, a confirmation prompt is shown before overwriting. After a successful copy, the application offers to open the new case immediately.

If there are unsaved changes when **Duplicate Case** is pressed, the application asks whether to save all modified files before copying so that the duplicated case reflects the latest edits.

To duplicate a case from a reference directory rather than the currently open case, use **Case > Duplicate from Case Library...** (see [Case Library](#case-library)).

## Tree and text workflow

The editor is designed so that raw text editing remains available even when the parser cannot fully interpret a file. The intended workflow is:

1. Open a case and select a file from the file list.
2. Load the raw text into the bottom editor immediately.
3. Parse the text and update the tree when parsing succeeds.
4. Use the tree for structure browsing and simple value editing.
5. Use the lower text editor for direct manual editing.
6. Press **Apply Text to Tree** when you want to parse the edited text back into the tree.
7. Press **Reload from Tree** when you want to regenerate the text from the current parsed tree.
8. Press **Save File** to save the current raw text to disk, or **Save Case** to save all modified files at once.

## Detail pane

The right-side detail pane shows contextual information for the selected node and lets you edit its value.

When a schema is defined for the selected key, the pane displays:

- **Key Help** — a description of what the setting controls.
- **Key Supported In** — the solver types or configurations where the setting applies.
- **Key Note** — additional remarks or caveats.
- **Choices** — a drop-down list of valid or common values. Selecting a choice updates the help fields below to show the description, supported-in information, and notes specific to that value.

These help fields are populated from schema modules. Because OpenFOAM is highly flexible and supports a large number of settings and solvers, the built-in schemas cover only a selection of common keys — not every possible entry. For keys without a schema annotation, the detail pane still shows the key name, type, and value, but the help fields are left blank. You can fill in the gaps by writing your own schema modules, which are plain Python files you can load at runtime via **Settings > Manage Schema Modules**.

For ordinary nodes, the pane also shows Key, Type, and an editable Value field. For `field_value` nodes, the pane shows Field Type, Field Name, and Value.

### Numeric type promotion

OpenFOAM does not strictly distinguish between integer and floating-point values in most contexts. When you enter a fractional value (for example `0.5`) for a node whose current type is `int`, the editor automatically promotes the node to `scalar` without an error or confirmation prompt. The Type column updates immediately to reflect the new type. Entering an integer value in a `scalar` node keeps the type as `scalar`.

## Behavior on parse failure

If parsing fails after loading or after editing, the application shows a warning and keeps the raw text editor usable. In this state, the last successfully parsed tree remains available until a later parse succeeds.

## Editor behavior

The bottom editor is based on the custom `CodeEditor` widget and is used for direct plain-text editing of OpenFOAM dictionary files. It shows the current line number in the lower area of the editor panel.

The window title shows a `*` suffix when the editor content has unsaved changes, and clears it after save, reload from tree, or a successful apply-to-tree.

## Supported syntax and node types

FoDE targets common OpenFOAM dictionary syntax with practical, tolerant handling rather than full specification coverage. The parser recognises the following node types:

| Type | Description |
|---|---|
| `word` | A plain keyword–value pair |
| `scalar` | A floating-point value |
| `int` | An integer value (auto-promoted to `scalar` when a fractional value is entered) |
| `bool` | A boolean value (`true`/`false`/`yes`/`no`/`on`/`off`) |
| `vector` | A parenthesised three-component value, e.g. `(0 0 9.81)` |
| `list` | A parenthesised list of values |
| `dictionary` | A sub-dictionary block |
| `field_value_block` | A block with `internalField`/`boundaryField` structure (field files such as `0/U`) |
| `field_value` | An individual field value entry within a `field_value_block` |
| `region_block` | A named region block (used in `setFieldsDict`) |
| `region_entry` | An entry within a `region_block` |
| `directive_entry` | A `#include`, `#inputMode`, or other pre-processor directive |
| `macro_entry` | A `$variable` macro expansion |
| `unknown_raw_entry` | Any entry the parser could not fully interpret; stored and written back as raw text |

Unrecognised syntax is preserved as `unknown_raw_entry` nodes and written back verbatim, so partially-parsed files are not corrupted.

## Limitations

This project is a practical editor template, not a complete OpenFOAM parser. Known limitations at this stage include these points:

- Full lossless round-trip behavior is not guaranteed for every possible OpenFOAM syntax variant.
- Formatting and comment placement can change for modified nodes when text is regenerated from the tree.

## Disclaimer

This offering is not approved or endorsed by OpenCFD Limited, producer and distributor of the OpenFOAM software via [www.openfoam.com](http://www.openfoam.com/), and owner of the OPENFOAM® and OpenCFD® trade marks.


## Acknowledgements

- [PySide6 (Qt for Python)](https://doc.qt.io/qtforpython/) — GUI framework (LGPL v3).
- [xterm.js](https://xtermjs.org/) — Terminal emulator used in the Terminal panel (MIT).
  Files are downloaded automatically from jsDelivr on first launch and cached in `ui/xterm/`.
- [pytest](https://pytest.org/) / [pytest-qt](https://pytest-qt.readthedocs.io/) — Test framework (development only).
- [PyInstaller](https://pyinstaller.org/) — Used to build standalone executables.

---

Copyright (C) 2025-2026 Shinji NAKAGAWA — [AGPL-3.0-or-later](LICENSE)
