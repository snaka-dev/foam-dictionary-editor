# Foam Dictionary Editor (FoDE) — Developer Guide

For user documentation, see [USER_GUIDE.md](USER_GUIDE.md).
For installation and basic usage, see [README.md](README.md).

## Project structure

A typical project layout is as follows.

```text
foam-dictionary-editor/
├── docs/
│   └── images/              # screenshots used in USER_GUIDE.md
├── main.py
├── requirements.txt
├── requirements-dev.txt
├── requirements-packaging.txt
├── README.md
├── README_ja.md
├── USER_GUIDE.md
├── USER_GUIDE_ja.md
├── app_config.json          # application settings (created when a case is first opened; git-ignored)
├── schema_config.json       # schema module list (created when schema settings are changed)
├── presets/
│   ├── standard.json                # features: terminal + blockmesh
│   ├── no-terminal.json             # features: terminal=false, blockmesh=false
│   └── no-terminal-blockmesh.json   # features: terminal=false, blockmesh=true
├── app_config/
│   ├── __init__.py
│   ├── app_config_manager.py
│   ├── constants.py
│   └── defaults.py
├── foam/
│   ├── block_mesh_extractor.py  # extracts vertices/blocks/boundary from blockMeshDict FoamNode tree; parse_vertices() is public
│   ├── diff.py                  # diff_trees(a, b) and diff_trees_reverse(b, a) — compare two FoamNode trees by key name; return dict[FoamNode, DiffEntry]
│   ├── lexer.py
│   ├── nodes.py
│   ├── parser.py
│   ├── utils.py
│   └── writer.py
├── model/
│   └── tree_model.py
├── schemas/
│   ├── __init__.py
│   ├── _base.py
│   ├── builtin.py
│   ├── config_store.py
│   ├── block_mesh_dict.py
│   ├── control_dict.py
│   ├── fv_schemes.py
│   ├── fv_solution.py
│   ├── snappy_hex_mesh_dict.py
│   └── registry.py
├── services/
│   ├── case_copier.py
│   ├── case_files_config.py
│   └── case_loader.py
├── ui/
│   ├── _boundary_ops.py        # mixin: boundary view patch operations
│   ├── _case_ops.py            # mixin: open/reload/duplicate/save-as case, settings
│   ├── _file_ops.py            # mixin: per-file load/save/create/delete
│   ├── _tree_ops.py            # mixin: tree mutations, editor↔tree sync, and _apply_comparison_value
│   ├── block_mesh_panel.py     # 3-D viewer for blockMeshDict (pyVista/VTK, lazy init)
│   ├── add_files_dialog.py
│   ├── case_library_dialog.py
│   ├── clean_backups_dialog.py
│   ├── code_editor.py
│   ├── detail_panel.py
│   ├── duplicate_case_dialog.py
│   ├── editor_panel.py
│   ├── comparison_tree_panel.py  # read-only reference-case tree; emits use_value_requested(FoamNode)
│   ├── file_list_panel.py
│   ├── layout_constants.py
│   ├── keyboard_shortcuts_dialog.py
│   ├── main_window.py          # core: __init__, _build_ui and sub-builders, shared helpers, diff/compare logic
│   ├── manage_extra_files_dialog.py
│   ├── rename_boundary_dialog.py  # Rename Boundary dialog + find_rename_targets() scanner
│   ├── reset_settings_dialog.py
│   ├── save_as_new_case_dialog.py
│   ├── schema_manager_dialog.py
│   └── terminal_panel.py
└── tests/
    ├── conftest.py
    ├── test_app_config.py
    ├── test_backup.py
    ├── test_case_files_config.py
    ├── test_case_loader.py
    ├── test_duplicate_case.py
    ├── test_file_list_panel.py
    ├── test_main_window_split.py
    ├── test_parser_block_mesh_dict.py
    ├── test_parser_control_dict.py
    ├── test_parser_fv_schemes.py
    ├── test_parser_fv_solution.py
    ├── test_parser_set_fields_dict.py
    ├── test_schemas.py
    ├── test_terminal_panel.py
    ├── test_bool_nonuniform.py
    ├── test_source_lines.py
    ├── test_tree_color_lexer_dispatch.py
    ├── test_tree_copy_paste.py
    ├── test_rename_boundary.py
    ├── test_comparison_tree_panel.py
    ├── test_diff.py
    ├── test_tree_model.py
    ├── test_utils.py
    └── test_writer_roundtrip.py
```

`test_diff.py` covers `diff_trees` and `diff_trees_reverse` — identical trees, changed values, keys only in one tree, nested dictionaries, anonymous node skipping, `field_value_block` entries, and symmetry between the two functions. `FoamNode` carries `__hash__ = object.__hash__` so instances can be used as dict keys in the diff map. `test_comparison_tree_panel.py` covers `ComparisonTreePanel` — `load` sets the header label, populates the proxy, collapses the FoamFile node, and re-applies the Type column visibility; `clear` resets model and header; `set_type_column_visible` hides/shows the Type column and persists across `load` calls; `use_value_requested` signal is connectable. `test_tree_model.py` covers `set_diff(reverse=True)` — remaps `"only_here"` to `"only_in_ref"`, leaves `"changed"` unchanged, returns the light-green `BackgroundRole` colour, and includes `"only in reference case"` in the tooltip. `test_file_list_panel.py` covers the diff filter: `set_diff_filter_enabled` shows/hides and unchecks the checkbox; the filter hides zero-diff file items while always showing headers; `mark_diff` updates item visibility immediately when the filter is active. `test_case_loader.py` covers `detect_time_dirs` and `TestExtraDirs` — flat and recursive extra-directory scanning, missing-directory tolerance, and duplicate suppression. `test_case_files_config.py` covers `TestCaseFilesConfigDirs` — `DirEntry` add/remove/update-in-place, backward-compatible loading of plain-string JSON, and config reset. `test_main_window_split.py` verifies the mixin structure — that each mixin owns the right methods (including `_on_patch_selected` in `_BoundaryOpsMixin` and `_apply_comparison_value` in `_TreeOpsMixin`), there are no cross-mixin duplicates, and `MainWindow` inherits from all four mixins; `test_bool_nonuniform.py` covers bool/nonuniform_list parsing and parser error collection; `test_tree_color_lexer_dispatch.py` covers `unknown_raw_entry` amber colouring, lexer `//` behaviour, and the parser `_PAREN_DISPATCH` table; `test_source_lines.py` covers `source_line` and `source_end_line` population for all node types; `test_parser_block_mesh_dict.py` covers `boundary_block`/`boundary_entry` structured parsing, round-trip writing, and `extract_block_mesh_data` output for `blockMeshDict`; `test_rename_boundary.py` covers `find_rename_targets()` — detection of `boundary_entry` nodes in `blockMeshDict`, `dictionary` patch nodes in `boundaryField` blocks, absence of false positives for unrelated dictionaries, and the empty-input edge cases.

## Extra directories

`case_files_config.py` stores the per-case list of extra directories as `list[DirEntry]`, where `DirEntry = tuple[str, bool]` is `(rel_path, recursive)`. The flag controls whether the directory is scanned flat (`Path.iterdir()`) or recursively (`Path.rglob("*")`).

- `add_dir(rel_path, recursive=False)` appends a new entry or updates the recursive flag in-place if the path already exists.
- `remove_dir(rel_path)` filters the entry out by path.
- JSON is saved as `[{"path": "...", "recursive": true/false}]`. Old files that stored plain strings are loaded as non-recursive for backward compatibility.

`case_loader.py`'s `list_case_files` accepts `extra_dirs: list[tuple[str, bool]] | None`. Each entry is iterated independently — flat entries use `sorted(d.iterdir(), key=...)`, recursive entries use `sorted(d.rglob("*"), key=lambda p: (str(p.parent), p.name.lower()))` so files appear in directory-then-name order. The deduplication set shared with the fixed `TARGET_FILES` prevents any path from appearing twice.

`manage_extra_files_dialog.py` exposes a **Toggle Recursive** button that flips the recursive flag on all selected directory items. The raw path is stored in `Qt.UserRole` on each item; the display text appends `[recursive]` when the flag is set. The `result_dirs` property returns the full `list[DirEntry]` final state, which `_file_ops.py` uses to compute the status-bar summary (added, removed, toggled counts).

## Tree-to-editor sync

Selecting a tree node highlights its source span in the text editor (amber background) and optionally scrolls the editor to that line. The mechanism works as follows.

**Parser side** — `FoamNode` carries two 1-based line fields: `source_line` (first line of the entry in the original source) and `source_end_line` (last line). The parser populates these in `_finalize_node` and in `_parse_dictionary_entry` using `_token_line(token_index)`, which counts newlines in the source text up to the token's character offset.

**UI side** — `CodeEditor` holds `_span_start_line` / `_span_end_line`. `set_span_highlight(start, end)` stores the range and triggers `highlight_current_line`, which renders the amber span first (behind) and the blue current-line highlight on top via `setExtraSelections`. `EditorPanel` exposes `jump_to_node(start, end, scroll=True)` (highlight + optional scroll) and `clear_node_highlight()`.

**State guard** — `MainWindow._source_lines_valid` is `True` after any `_load_tree` call (file load or Apply Text to Tree) and `False` as soon as the user edits the editor text (`_on_user_text_changed`). `on_tree_selection` skips jump and highlight when this flag is `False`, preventing jumps to stale line numbers. `_update_sync_checkbox` reflects the valid/stale state in the checkbox label, style, and tooltip.

**Editor → tree** — `_sync_tree_to_editor_line` reads the current editor cursor line and calls `_find_deepest(root, line)` to find the innermost node whose `source_line ≤ line ≤ source_end_line`. The tree is scrolled to the result. If the matched node is filtered out by the proxy model, the code walks up to the nearest visible ancestor. This method is triggered by the **Find in Tree** button in the Editor toolbar and by the `Ctrl+Shift+T` shortcut.

## Boundary-to-editor navigation

Clicking a cell in the Boundary panel emits `patch_selected(path, patch_name)`, handled by `_on_patch_selected` in `_BoundaryOpsMixin`. Unlike tree navigation (which uses `source_line`), boundary navigation uses text search because `write_root()` regenerates text after any boundary edit, making source-line numbers immediately stale.

`EditorPanel.jump_to_text(text)` calls `QTextDocument.find(text, 0, FindWholeWords)` from the top of the document. When a match is found it calls `set_span_highlight(line, line)` and `goto_line(line)` on the matched block number. Patch names in `boundaryField` are unique per file, so the first hit is always the correct one.

If the clicked cell's file differs from `current_file`, `_on_patch_selected` calls `load_selected_file(path)` first (which sets `current_file`), then `file_list_panel.select_file(path)` to sync the file-list highlight. The re-entrant `load_selected_file` triggered by the resulting `file_selected` signal is a no-op because `current_file` is already set.

The **Auto-scroll editor** checkbox in the Boundary panel toolbar gates the `patch_selected` emission in `_on_cell_clicked`; when unchecked, single-click has no editor effect.

`BoundaryViewPanel._table_data()` extracts `(col_headers, row_headers, rows)` from the current `QTableWidget` state. `_copy_as_markdown()` builds a GitHub-Flavored Markdown pipe table from this data and writes it to the system clipboard; `\n` in cell text becomes `<br>`. `_copy_as_csv()` writes RFC 4180 CSV; multiline cell content is preserved inside quoted fields. Both methods respect the current transposed orientation because they read from the already-rendered table.

## Setup

Python 3.10 or newer is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Run

```bash
python3 main.py                                   # standard (terminal + BlockMesh)
python3 main.py --variant no-terminal             # no terminal tab
python3 main.py --variant no-terminal-blockmesh   # no terminal + BlockMesh always visible
```

The `--variant` flag loads `presets/<name>.json`, overwrites the `features` dict in the config singleton, and saves the result to `app_config.json` on exit. Subsequent launches without `--variant` use the saved flags. Feature flags default to `true` when absent, so a developer's personal `app_config.json` (which is git-ignored and typically has no `features` key) always starts in standard mode.

After startup, use **Case > Open Case** to select an OpenFOAM case directory, and then choose a file from the file list. `app_config.json` is created automatically the first time a case is opened. `schema_config.json` is created only when schema settings are explicitly changed via the Settings menu.

If the selected directory does not contain a `system/` or `constant/` subdirectory, a warning dialog is shown before the case is loaded. You can open the directory anyway or cancel and select a different one.

## GPU / OpenGL notes

The application uses two subsystems that both access the GPU on Linux:

- **VTK / pyVista** (`block_mesh_panel.py`) — uses OpenGL for 3-D rendering via `QtInteractor`. Present only when `features.blockmesh=true`.
- **Qt WebEngine** (`terminal_panel.py`, xterm mode) — uses its own GPU process. Present only when `features.terminal=true`.

These two cannot safely coexist on the same GPU context. The workarounds applied in `main.py` are:

1. `QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu --disable-vulkan --log-level=2` forces WebEngine to use SwiftShader (CPU software rendering), leaving the GPU free for VTK. `--log-level=2` suppresses the "GPUInfo not initialized on GpuInfoUpdate" Chromium warning that appears as a side-effect of `--disable-gpu`.
2. At startup, if `block_mesh_panel` is not `None` and the terminal is absent or in Simple mode, `QTimer.singleShot(0, block_mesh_panel._init_plotter)` eagerly initialises VTK so it claims the OpenGL context before any user interaction.

The terminal mode toggle (`TerminalPanel.mode_changed` signal) shuts down VTK before xterm starts, and re-initialises it (after a 300 ms delay) when switching back to Simple mode. This signal is connected only when both `terminal` and `blockmesh` features are enabled.

**View menu action** — `_blockmesh_action` (`QAction`, checkable) in `_build_menu_bar` provides a second way to show/hide the BlockMesh tab independently of the terminal mode. When xterm is active the action is disabled and its text changes to `"BlockMesh 3-D Panel  (unavailable: xterm active)"` so the reason is visible without hovering. `_on_terminal_mode_changed` keeps the action's enabled state and label in sync with the terminal mode. `_on_toggle_blockmesh_panel` handles the actual tab add/remove when the user clicks the action.

**Axes widget** — `add_axes()` creates a `vtkOrientationMarkerWidget` that persists across `plotter.clear()` calls (it is a widget, not an actor). It is therefore called once in `_init_plotter()`. `_render()` calls `show_axes()` / `hide_axes()` to toggle it, rather than re-adding it each frame.

## Testing

```bash
python3 -m pytest -q
```

If `pytest -q` causes import issues, running it as `python3 -m pytest -q` is safer because the project root is handled more reliably.

## Acknowledgements

- [PyInstaller](https://pyinstaller.org/) — Used to build standalone executables.
- [pyVista](https://pyvista.org/) / [VTK](https://vtk.org/) — 3-D viewer for `blockMeshDict` (BSD-3-Clause, optional).
- [pytest](https://pytest.org/) / [pytest-qt](https://pytest-qt.readthedocs.io/) — Test framework.

Special thanks to the [OpenFOAM Foundation](https://openfoam.org/) and [OpenCFD / ESI Group](https://www.openfoam.com/) and all contributors for developing and maintaining OpenFOAM as free, open-source CFD software.
