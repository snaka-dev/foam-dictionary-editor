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
│   ├── block_mesh_extractor.py  # extracts vertices/blocks/boundary from blockMeshDict FoamNode tree; _build_var_map iteratively resolves $vars (including negated-macro word nodes like -$xMax) and #eval{} chains of arbitrary depth; _HEX_FACE_VERTICES + _expand_compact_faces convert compact (blockIdx, faceIdx) boundary entries to 4-vertex lists; parse_vertices() is public
│   ├── diff.py                  # diff_trees(a, b) and diff_trees_reverse(b, a) — compare two FoamNode trees by key name; return dict[FoamNode, DiffEntry]
│   ├── lexer.py                 # OpenFoamLexer; _read_directive stops at '{' so #eval{...} braces become LBRACE/RBRACE tokens for correct depth tracking
│   ├── nodes.py
│   ├── parser.py
│   ├── utils.py
│   └── writer.py
├── model/
│   ├── boundary_model.py   # BoundaryModel (QAbstractTableModel) + extract_boundary()
│   ├── file_list_model.py  # FileListModel (QAbstractListModel)
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
├── i18n/
│   ├── __init__.py             # tr(), set_language(), get_language(), available_languages()
│   └── ja.py                   # Japanese translations (LANGUAGE_NAME + TRANSLATIONS dict)
├── ui/
│   ├── app_state.py            # AppState dataclass: all 18 shared mutable fields; MainWindow sets self.state = AppState()
│   ├── mixins/
│   │   ├── _boundary_ops.py        # mixin: boundary view patch operations
│   │   ├── _case_ops.py            # mixin: open/reload/duplicate/save-as case, settings
│   │   ├── _diff_ops.py            # mixin: side-by-side comparison, diff compute/clear
│   │   ├── _file_mgmt_ops.py       # mixin: create/add/backup/delete/duplicate/clean file operations
│   │   ├── _file_ops.py            # mixin: per-file load/save, directory scan helpers
│   │   ├── _foam_monitor_ops.py    # mixin: foamMonitor launch/stop/poll, gnuplot reread patch
│   │   ├── _panel_ops.py           # mixin: BlockMesh panel and terminal mode toggle handlers
│   │   └── _tree_ops.py            # mixin: tree mutations, editor↔tree sync, and _apply_comparison_value
│   ├── layout_constants.py
│   ├── main_window.py          # core: __init__, _build_ui and sub-builders, shared helpers, drag-and-drop (dragEnterEvent/dropEvent/eventFilter)
│   ├── dialogs/
│   │   ├── about_dialog.py
│   │   ├── add_files_dialog.py
│   │   ├── boundary_edit_dialog.py
│   │   ├── case_library_dialog.py
│   │   ├── clean_backups_dialog.py
│   │   ├── duplicate_case_dialog.py
│   │   ├── foam_monitor_dialog.py  # FoamMonitorDialog: file picker + foamMonitor option controls (log scale, grid, refresh, idle, extra flags)
│   │   ├── keyboard_shortcuts_dialog.py
│   │   ├── manage_extra_files_dialog.py
│   │   ├── openfoam_resources_dialog.py
│   │   ├── rename_boundary_dialog.py  # Rename Boundary dialog + find_rename_targets() scanner
│   │   ├── reset_settings_dialog.py
│   │   ├── save_as_new_case_dialog.py
│   │   └── schema_manager_dialog.py
│   ├── panels/
│   │   ├── block_mesh_panel.py     # 3-D viewer for blockMeshDict (pyVista/VTK, lazy init)
│   │   ├── boundary_view_panel.py
│   │   ├── comparison_tree_panel.py  # read-only reference-case tree; emits use_value_requested(FoamNode)
│   │   ├── detail_panel.py
│   │   ├── editor_panel.py
│   │   ├── file_list_panel.py
│   │   └── terminal_panel.py       # TerminalPanel wrapper: mode_changed signal, xterm/simple toggle logic
│   └── widgets/
│       ├── code_editor.py
│       ├── _simple_terminal_widget.py  # SimpleTerminalWidget: QProcess-based terminal (no WebEngine)
│       └── _xterm_widget.py            # PtyBackend, TerminalBridge, XtermTerminalWidget (Unix + QtWebEngine only); exports _XTERM_AVAILABLE
└── tests/
    ├── conftest.py
    ├── foam/
    │   ├── test_diff.py
    │   ├── test_parser_block_mesh_dict.py
    │   ├── test_parser_control_dict.py
    │   ├── test_parser_fv_schemes.py
    │   ├── test_parser_fv_solution.py
    │   ├── test_parser_set_fields_dict.py
    │   ├── test_source_lines.py
    │   ├── test_utils.py
    │   └── test_writer_roundtrip.py
    ├── model/
    │   ├── test_bool_nonuniform.py
    │   ├── test_boundary_model.py
    │   ├── test_file_list_model.py
    │   └── test_tree_model.py
    ├── ui/
    │   ├── test_boundary_view_copy.py
    │   ├── test_comparison_tree_panel.py
    │   ├── test_drag_drop_open_case.py
    │   ├── test_duplicate_case.py
    │   ├── test_file_list_panel.py
    │   ├── test_main_window_split.py
    │   ├── test_manage_extra_files_dialog.py
    │   ├── test_rename_boundary.py
    │   ├── test_terminal_panel.py
    │   ├── test_tree_color_lexer_dispatch.py
    │   └── test_tree_copy_paste.py
    ├── services/
    │   ├── test_backup.py
    │   ├── test_case_files_config.py
    │   └── test_case_loader.py
    ├── app_config/
    │   └── test_app_config.py
    └── schemas/
        └── test_schemas.py
```

`test_utils.py` covers `is_large_non_foam_file` — small files are never flagged regardless of header, large files with a `FoamFile` token in the first 512 bytes are not flagged, large files without it are flagged, missing files return `(False, 0)`, and a header preceded by a comment is still detected. `test_diff.py` covers `diff_trees` and `diff_trees_reverse` — identical trees, changed values, keys only in one tree, nested dictionaries, anonymous node skipping, `field_value_block` entries, and symmetry between the two functions. `FoamNode` carries `__hash__ = object.__hash__` so instances can be used as dict keys in the diff map. `test_comparison_tree_panel.py` covers `ComparisonTreePanel` — `load` sets the header label, populates the proxy, collapses the FoamFile node, and re-applies the Type column visibility; `clear` resets model and header; `set_type_column_visible` hides/shows the Type column and persists across `load` calls; `use_value_requested` signal is connectable. `test_tree_model.py` covers `set_diff(reverse=True)` — remaps `"only_here"` to `"only_in_ref"`, leaves `"changed"` unchanged, returns the light-green `BackgroundRole` colour, and includes `"only in reference case"` in the tooltip. `test_file_list_panel.py` covers the diff filter: `set_diff_filter_enabled` shows/hides and unchecks the checkbox; the filter hides zero-diff file items while always showing headers; `mark_diff` updates item visibility immediately when the filter is active. `test_case_loader.py` covers `detect_time_dirs` and `TestExtraDirs` — flat and recursive extra-directory scanning, missing-directory tolerance, and duplicate suppression. `test_case_files_config.py` covers `TestCaseFilesConfigDirs` — `DirEntry` add/remove/update-in-place, backward-compatible loading of plain-string JSON, and config reset. `test_main_window_split.py` verifies the mixin structure — that each mixin owns the right methods (including `_on_patch_selected` in `_BoundaryOpsMixin`, `_apply_comparison_value` in `_TreeOpsMixin`, and the foamMonitor methods in `_FoamMonitorOpsMixin`), there are no cross-mixin duplicates, and `MainWindow` inherits from all mixins; `test_bool_nonuniform.py` covers bool/nonuniform_list parsing and parser error collection; `test_tree_color_lexer_dispatch.py` covers `unknown_raw_entry` amber colouring, lexer `//` behaviour, and the parser `_PAREN_DISPATCH` table; `test_source_lines.py` covers `source_line` and `source_end_line` population for all node types; `test_parser_block_mesh_dict.py` covers `boundary_block`/`boundary_entry` structured parsing, round-trip writing, and `extract_block_mesh_data` output for `blockMeshDict`; variable resolution (`$varName`, `${varName}`, macro references, negated-macro word nodes like `-$xMax`, `#eval{ expr }` arithmetic, and multi-level dependency chains); compact `(blockIndex, faceIndex)` boundary face notation (expansion to 4-vertex lists, including combined with negated-macro vertex variables); `test_rename_boundary.py` covers `find_rename_targets()` — detection of `boundary_entry` nodes in `blockMeshDict`, `dictionary` patch nodes in `boundaryField` blocks, absence of false positives for unrelated dictionaries, and the empty-input edge cases.

## Parser and data model

### Node types

**Leaf value types** — set by `_classify_value` in `foam/parser.py:387` and `classify_parenthesized_value` in `foam/utils.py:113`:

| `node_type` | `value` Python type | Condition |
|---|---|---|
| `int` | `int` | bare integer token (`"."` and `"e"` absent) |
| `scalar` | `float` | bare float token |
| `bool` | `str` | single token in `BOOL_WORDS`: `true` / `false` / `on` / `off` / `yes` / `no` |
| `word` | `str` | any other single token (fallback) |
| `string` | `str` | double-quoted token (`"…"`) |
| `macro` | `str` | token starting with `$` |
| `compound` | `str` | multiple space-separated tokens (no parens) |
| `nonuniform_list` | `str` | `nonuniform List<T> N (…)` — a special case detected before `compound` |
| `vector` | `list[float]` (len 3) | `(x y z)` — exactly 3 numeric tokens in parens |
| `int_list` | `list[int]` | `(a b …)` — all integer tokens in parens |
| `scalar_list` | `list[float]` | `(a b …)` — all numeric tokens in parens, not exactly 3 |
| `raw_list` | `str` (inner text) | `(…)` with mixed or nested content |
| `box_pair` | `list[list[float]]` (2×3) | `(x y z) (x y z)` — only for the `box` key |

**Structural types** — set by `_parse_entry` / `_parse_dictionary_entry` / `_parse_named_dict_block`:

| `node_type` | Description |
|---|---|
| `dictionary` | `key { … }` block; `value=None`, children populated |
| `field_value_block` | `defaultFieldValues / fieldValues ( … );` |
| `field_value` | item inside a `field_value_block` |
| `region_block` | `regions ( … );` |
| `region_entry` | named `{ … }` entry inside a `region_block` |
| `boundary_block` | `boundary ( … );` in `blockMeshDict` |
| `boundary_entry` | named `{ … }` entry inside a `boundary_block` |
| `directive_entry` | `#include`, `#inputMode`, etc.; `name=""` |
| `macro_entry` | standalone `$macro;`; `name=""` |
| `unknown_raw_entry` | fallback when a parse attempt fails; raw text stored verbatim in `value` |

### Classification logic

`_classify_value(key, text)` (`foam/parser.py:387`) is called for every non-brace, non-special-paren entry. Priority order:

1. **`box_pair`** — only when `key == "box"` and `parse_box_pair(text)` in `foam/utils.py` succeeds.
2. **Parenthesised** — delegates to `classify_parenthesized_value` (`foam/utils.py:113`): returns `vector` (exactly 3 floats), `int_list` (all integers), `scalar_list` (all floats, not 3), or `raw_list` (anything else).
3. **`string`** — starts and ends with `"`.
4. **`macro`** — starts with `$`.
5. **Space-containing** — `nonuniform_list` if it begins `nonuniform List…`, otherwise `compound`.
6. Single token: `int` → `scalar` → `bool` (token in `BOOL_WORDS`) → `word` (fallback).

### Re-parse triggers

The parser runs (and the tree is rebuilt) at exactly two moments:

- **File open** — when a file is selected in the file list or loaded programmatically.
- **Apply Text to Tree** — the manual button in the action bar.

There is no automatic re-parse on keystroke or on file save. After a manual edit in the text editor the tree and source-line numbers become stale; this is indicated by the "Auto-scroll editor (stale)" label until the next parse.

### Error recovery

When `_parse_entry` raises a `ParseError`, the parser backtracks to `start_index`, records the error in `self.errors`, and calls `_parse_unknown_raw_entry`. That method consumes tokens up to the next `;` or line boundary, wraps the raw text in an `unknown_raw_entry` node, and continues parsing. The file remains usable; the verbatim text is written back on save. After parsing, `OpenFoamParser.errors` contains all recovery events; the caller reports the count in the status bar as "N unrecognized entries."

### FoamNode field semantics

`FoamNode` (`foam/nodes.py`) carries several fields beyond `name`, `node_type`, and `value` that the parser and writer use together:

| Field | Type | Purpose |
|---|---|---|
| `modified` | `bool` | Set to `True` by `FoamTreeModel.setData` when a key or value changes. Drives the writer's regeneration decision. |
| `raw_text` | `str` | The original source text for the node, captured by `_finalize_node` and `_parse_dictionary_entry`. Used verbatim by the writer for unmodified nodes. |
| `leading_trivia` | `list[str]` | Whitespace and comments that appear before the node in the source. Restored by `_with_leading_trivia` in the writer to preserve blank lines between entries. |
| `inline_comment` | `str` | The `// …` or `/* … */` comment immediately following the value on the same line. Collected by `_collect_inline_comment` and reproduced by the writer. |
| `source_line` / `source_end_line` | `int` | 1-based line numbers in the original source, set by `_token_line`. Used for editor-sync highlighting. `0` means the node was added in the tree and has no source location. |

### Writer raw_text passthrough

`_write_node` (`foam/writer.py:29`) skips regeneration entirely when three conditions hold:

```python
if not node.modified and node.raw_text and not _has_modified_descendant(node):
    return _with_leading_trivia(node, node.raw_text)
```

When all three are true the original source text is emitted verbatim, preserving formatting, inline comments, and exact whitespace. Only nodes where `modified=True` (or containing a modified descendant) are regenerated. A "Reload from Tree" on an unedited file therefore produces byte-identical output for every entry captured with `raw_text`.

`_has_modified_descendant` recurses through `node.children` for most types. For `field_value_block` it also checks `node.value` directly (see below).

### `field_value_block` children in `value`

`field_value_block` is the only structural type that stores its child nodes in `node.value` (a `list[FoamNode]`) rather than `node.children`. `FoamTreeModel._child_list` (`model/tree_model.py:159`) handles this special case:

```python
if node.node_type == "field_value_block":
    return node.value if isinstance(node.value, list) else []
return node.children
```

`node.children` is always an empty list for `field_value_block` nodes. Code that recurses over a tree generically must iterate `node.value` for this type. The writer (`foam/writer.py:72`) and `_has_modified_descendant` both do this explicitly.

### Legacy `"list"` type

The `"list"` node type name is a compatibility artifact from before `int_list` was introduced. The parser has never produced `"list"` nodes; the dead dispatch branches in `foam/writer.py` and `model/tree_model.py` that checked for it have been removed. New code should produce and expect `"int_list"` exclusively.

## Schema system

Schema modules supply the Detail pane with key descriptions, supported-version text, and value choices. The runtime registry and the base dataclasses live in `schemas/`.

### KeySchema and ChoiceItem

`schemas/_base.py` defines two frozen dataclasses that schema modules import:

```python
@dataclass(frozen=True)
class ChoiceItem:
    value: str
    description: str
    supported_in: tuple[str, ...] = ()
    note: str = ""

@dataclass(frozen=True)
class KeySchema:
    key: str
    label: str
    description: str
    supported_in: tuple[str, ...] = ()
    note: str = ""
    choices: tuple[ChoiceItem, ...] = ()
```

`_base.py` also exports three pre-built version strings: `FOUNDATION_V13`, `OPENCFD_V2312`, `OPENCFD_V2512`, and `OPENCFD_SERIES`. Schema modules import these for `supported_in` tuples to keep version strings consistent across modules.

### SchemaRegistry

`SchemaRegistry` (`schemas/registry.py`) is a singleton loaded at import time via `schemas/__init__.py`. It builds a two-level dict `_file_key_schemas[filename][dotted_key] → KeySchema` from the list of module names in `schema_config.json` (or the built-in default when the file does not exist).

`schema_for_file_key(file_path, key_name, parent_key, grandparent_key)` implements the three-level lookup:

1. `f"{parent_key}.{key_name}"` — direct parent context.
2. `f"{grandparent_key}.{key_name}"` — grandparent context (for blocks whose immediate parent is user-defined, such as a named `refinementSurfaces` entry).
3. Plain `key_name` — flat fallback.

`reload()` re-reads `schema_config.json` from disk and rebuilds the tables. `apply_and_reload()` rebuilds from the current in-memory config without touching disk (used after **Settings > Manage Schema Modules** applies changes within the same session).

## Diff algorithm

`foam/diff.py` compares two `FoamNode` trees and produces an annotation map used to colour the comparison panel.

### API

```python
DiffEntry = tuple[str, FoamNode | None]

def diff_trees(a: FoamNode, b: FoamNode) -> dict[FoamNode, DiffEntry]: ...
def diff_trees_reverse(b: FoamNode, a: FoamNode) -> dict[FoamNode, DiffEntry]: ...
```

Both functions return a `dict` mapping nodes in the **first argument** to a `(status, ref_node)` pair. `diff_trees_reverse` is a thin alias that calls `diff_trees(b, a)` so the annotation map is keyed on `b`-tree nodes; the UI uses this when rendering the reference-case pane.

### Status values

| Status | Meaning |
|---|---|
| `"changed"` | Key exists in both trees; `node_type` or `value` differs. `ref_node` is the matching node from `b`. |
| `"only_here"` | Key exists in `a` but not in `b`. `ref_node` is `None`. |

Nodes absent from `a` but present in `b` are not annotated in the `diff_trees` result. `FoamTreeModel.set_diff(diff, reverse=True)` remaps `"only_here"` to `"only_in_ref"` when attaching the map to the reference-case model.

### Recursion and skipping

`_diff_node` recurses into structural types listed in `_RECURSE_TYPES`:

```python
_RECURSE_TYPES = frozenset({
    "dictionary",
    "boundary_block", "boundary_entry",
    "region_block", "region_entry",
    "field_value_block",
})
```

Children are matched by `node.name`; anonymous nodes (empty `name`) are skipped. For `field_value_block`, `_diff_field_value_block` matches items by `field_name` from `node.value` (the same `value`-as-list layout described in [`field_value_block` children in `value`](#field_value_block-children-in-value)).

Equality is tested by `_equal(a, b)`: `True` when `a.node_type == b.node_type and a.value == b.value`.

## Internationalisation (i18n)

All user-visible strings in `ui/` are wrapped with `tr()` from `i18n/__init__.py`. English strings serve as their own keys; translations fall back to the key when a mapping is absent.

**Runtime flow**
1. `main.py` calls `set_language(get_app_config().get_language())` before the window is created.
2. Every widget constructor calls `tr("some string")` at instantiation time, so the selected language is applied to the whole UI on startup.
3. Language changes take effect after a restart (no live retranslation).

**Adding a new language**

Create `i18n/<code>.py` — no other files need changing:

```python
LANGUAGE_NAME = "Italiano"          # shown in Settings > Language menu

TRANSLATIONS: dict[str, str] = {
    "Open Case": "Apri caso",
    "Save File": "Salva file",
    # ... add as many as needed; missing keys fall back to English
}
```

`available_languages()` in `i18n/__init__.py` auto-discovers all `.py` files in the `i18n/` directory, so the new language appears in the Settings menu without any further changes.

**Storage** — the selected language code is stored in `app_config.json` under the key `"language"`. The key is omitted entirely when the language is `"en"` (the default), keeping the config file clean.

## Extra directories

`case_files_config.py` stores the per-case list of extra directories as `list[DirEntry]`, where `DirEntry = tuple[str, bool]` is `(rel_path, recursive)`. The flag controls whether the directory is scanned flat (`Path.iterdir()`) or recursively (`Path.rglob("*")`).

- `add_dir(rel_path, recursive=False)` appends a new entry or updates the recursive flag in-place if the path already exists.
- `remove_dir(rel_path)` filters the entry out by path.
- JSON is saved as `[{"path": "...", "recursive": true/false}]`. Old files that stored plain strings are loaded as non-recursive for backward compatibility.

`case_loader.py`'s `list_case_files` accepts `extra_dirs: list[tuple[str, bool]] | None`. Each entry is iterated independently — flat entries use `sorted(d.iterdir(), key=...)`, recursive entries use `sorted(d.rglob("*"), key=lambda p: (str(p.parent), p.name.lower()))` so files appear in directory-then-name order. The deduplication set shared with the fixed `TARGET_FILES` prevents any path from appearing twice.

The `FIELD_DIRS` scan (`0/`, `0.orig/`) collects direct files first and then descends one level into any subdirectory that exists — this picks up per-region field files such as `0/heater/T` and `0/bottomWater/p` that are common in `chtMultiRegionFoam` cases. `_group_name` already returns `"0/heater"` for these paths, so they automatically appear under their own group header in the file list. The boundary panel's `_available_field_dirs` mirrors this detection and populates the Directory selector with `"0/heater"` etc.; `_is_in_dir` uses `Path.is_relative_to` to match multi-level dir names correctly.

`manage_extra_files_dialog.py` exposes a **Toggle Recursive** button that flips the recursive flag on all selected directory items. The raw path is stored in `Qt.UserRole` on each item; the display text appends `[recursive]` when the flag is set. The `result_dirs` property returns the full `list[DirEntry]` final state, which `_file_mgmt_ops.py` uses to compute the status-bar summary (added, removed, toggled counts).

## Tree-to-editor sync

Selecting a tree node highlights its source span in the text editor (amber background) and optionally scrolls the editor to that line. The mechanism works as follows.

**Parser side** — `FoamNode` carries two 1-based line fields: `source_line` (first line of the entry in the original source) and `source_end_line` (last line). The parser populates these in `_finalize_node` and in `_parse_dictionary_entry` using `_token_line(token_index)`, which counts newlines in the source text up to the token's character offset.

**UI side** — `CodeEditor` holds `_span_start_line` / `_span_end_line`. `set_span_highlight(start, end)` stores the range and triggers `highlight_current_line`, which renders the amber span first (behind) and the blue current-line highlight on top via `setExtraSelections`. `EditorPanel` exposes `jump_to_node(start, end, scroll=True)` (highlight + optional scroll) and `clear_node_highlight()`.

**State guard** — `MainWindow._source_lines_valid` is `True` after any `_load_tree` call (file load or Apply Text to Tree) and `False` as soon as the user edits the editor text (`_on_user_text_changed`). `on_tree_selection` skips jump and highlight when this flag is `False`, preventing jumps to stale line numbers. `_update_sync_checkbox` reflects the valid/stale state in the checkbox label, style, and tooltip.

**Editor → tree** — `_sync_tree_to_editor_line` reads the current editor cursor line and calls `_find_deepest(root, line)` to find the innermost node whose `source_line ≤ line ≤ source_end_line`. The tree is scrolled to the result. If the matched node is filtered out by the proxy model, the code walks up to the nearest visible ancestor. This method is triggered by the **Find in Tree** button in the Editor toolbar and by the `Ctrl+Shift+T` shortcut.

## Boundary-to-editor navigation

Clicking a cell in the Boundary panel emits `patch_selected(path, patch_name)`, handled by `_on_patch_selected` in `_BoundaryOpsMixin`. Unlike tree navigation (which uses `source_line`), boundary navigation uses text search because `write_root()` regenerates text after any boundary edit, making source-line numbers immediately stale.

`EditorPanel.jump_to_text(text)` calls `QTextDocument.find(text, 0, FindWholeWords)` from the top of the document. When a match is found it calls `set_span_highlight(line, line)` and `goto_line(line)` on the matched block number. Patch names in `boundaryField` are unique per file, so the first hit is always the correct one.

If the clicked cell's file differs from `state.current_file`, `_on_patch_selected` calls `load_selected_file(path)` first (which sets `state.current_file`), then `file_list_panel.select_file(path)` to sync the file-list highlight. The re-entrant `load_selected_file` triggered by the resulting `file_selected` signal is a no-op because `state.current_file` is already set.

The **Auto-scroll editor** checkbox in the Boundary panel toolbar gates the `patch_selected` emission in `_on_cell_clicked`; when unchecked, single-click has no editor effect.

`BoundaryViewPanel._table_data()` extracts `(col_headers, row_headers, rows)` from the current `QTableWidget` state. `_copy_as_markdown()` builds a GitHub-Flavored Markdown pipe table from this data and writes it to the system clipboard; `\n` in cell text becomes `<br>`. `_copy_as_csv()` writes RFC 4180 CSV; multiline cell content is preserved inside quoted fields. Both methods respect the current transposed orientation because they read from the already-rendered table.

## Dirty-state tracking

`MainWindow` maintains two parallel dirty-state variables:

- `state.text_dirty: bool` — whether the currently open file's in-memory editor content differs from what is on disk. Set by `_mark_dirty()` and cleared by `save_file()`, Apply Text to Tree, and Reload from Disk.
- `state.file_dirty: dict[str, bool]` — per-file dirty state for every file that has been loaded in the current session. Persists across file switches so unsaved edits are not lost when the user selects a different file.

`_mark_dirty()` (`ui/main_window.py:566`) sets both values to `True`, adds the `*` suffix to the window title, and calls `file_list_panel.mark_dirty()` to show the indicator in the file list. It is called from `_after_model_edit()` (after any tree edit that regenerates text via `write_root()`) and from `_on_user_text_changed()` (on any human keystroke in the editor).

`_save_current_buffer()` (`ui/main_window.py:520`) flushes `editor_panel.get_text()` to `state.file_buffers[state.current_file]` and writes `state.text_dirty` back into `state.file_dirty[state.current_file]` before a file switch. This preserves unsaved edits in memory across switches.

`_mark_path_dirty(path)` marks a specific path dirty regardless of which file is currently open. Used by operations that modify non-current files (e.g. renaming a boundary patch across multiple field files).

## Tree copy/paste shortcuts

`_setup_tree_copy_paste()` (`ui/mixins/_tree_ops.py:29`) attaches Ctrl+C and Ctrl+V `QShortcut` instances directly to the `tree` widget using `Qt.WidgetShortcut` scope:

```python
copy_sc = QShortcut(QKeySequence.Copy, self.tree)
copy_sc.setContext(Qt.WidgetShortcut)

paste_sc = QShortcut(QKeySequence.Paste, self.tree)
paste_sc.setContext(Qt.WidgetShortcut)
```

`Qt.WidgetShortcut` fires only when `self.tree` has keyboard focus, so Ctrl+C in the text editor is unaffected. It also does not fire while a tree cell is in inline-edit mode: Qt routes Ctrl+C to the cell editor's own selection-copy mechanism in that state.

The same two actions appear in the context menu (**Copy Value** / **Paste Value**). Paste is disabled in the menu and silently rejected when the selected node type does not support value editing.

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

After startup, use **Case > Open Case** to select an OpenFOAM case directory, or drag a directory from your file manager onto any part of the window. Then choose a file from the file list. `app_config.json` is created automatically the first time a case is opened. `schema_config.json` is created only when schema settings are explicitly changed via the Settings menu.

If the selected directory does not contain a `system/` or `constant/` subdirectory, a warning dialog is shown before the case is loaded. You can open the directory anyway or cancel and select a different one.

## Application configuration

`AppConfigManager` (`app_config/app_config_manager.py`) manages persistent application settings. A single instance is obtained via `get_app_config()` and reused throughout the session.

### save() semantics

`set_window_size()`, `set_default_case_dir()`, `set_language()`, and the other setters only update in-memory state. They do **not** write to disk. The caller must explicitly call `cfg.save()` afterwards.

Two callers in `main_window.py` do this:

- `closeEvent` — calls `cfg.set_window_size(w, h)` then `cfg.save()` to persist the final window geometry.
- `reset_window_size` — resets the stored size and saves immediately.

Any other caller that modifies config (e.g. updating the default case dir on open) must also call `cfg.save()` explicitly. An unsaved `set_*` call is silently discarded if `save()` is never called before exit.

### app_config.json location

`app_config.json` is written to the project root (the directory containing `main.py`). It is git-ignored. If the file does not exist, `_load()` returns without error and all properties return their defaults.

## GPU / OpenGL notes

The application uses two subsystems that both access the GPU on Linux:

- **VTK / pyVista** (`block_mesh_panel.py`) — uses OpenGL for 3-D rendering via `QtInteractor`. Present only when `features.blockmesh=true`.
- **Qt WebEngine** (`_xterm_widget.py`, `XtermTerminalWidget`) — uses its own GPU process. Present only when `features.terminal=true`.

These two cannot safely coexist on the same GPU context. The workarounds applied in `main.py` are:

1. `QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu --disable-vulkan --log-level=2` forces WebEngine to use SwiftShader (CPU software rendering), leaving the GPU free for VTK. `--log-level=2` suppresses the "GPUInfo not initialized on GpuInfoUpdate" Chromium warning that appears as a side-effect of `--disable-gpu`.
2. At startup, if `block_mesh_panel` is not `None` and the terminal is absent or in Simple mode, `QTimer.singleShot(0, block_mesh_panel._init_plotter)` eagerly initialises VTK so it claims the OpenGL context before any user interaction.

The terminal mode toggle (`TerminalPanel.mode_changed` signal) shuts down VTK before xterm starts, and re-initialises it (after a 300 ms delay) when switching back to Simple mode. This signal is connected only when both `terminal` and `blockmesh` features are enabled.

**View menu action** — `_blockmesh_action` (`QAction`, checkable) in `_build_menu_bar` provides a second way to show/hide the BlockMesh tab independently of the terminal mode. When xterm is active the action is disabled and its text changes to `"BlockMesh 3-D Panel  (unavailable: xterm active)"` so the reason is visible without hovering. `_on_terminal_mode_changed` keeps the action's enabled state and label in sync with the terminal mode. `_on_toggle_blockmesh_panel` handles the actual tab add/remove when the user clicks the action.

**Axes widget** — `add_axes()` creates a `vtkOrientationMarkerWidget` that persists across `plotter.clear()` calls (it is a widget, not an actor). It is therefore called once in `_init_plotter()`. `_render()` calls `show_axes()` / `hide_axes()` to toggle it, rather than re-adding it each frame.

**Side-by-side mode** — A `⊞` toggle button (`_bm_side_by_side_btn`) is added as a `QTabWidget` corner widget. When enabled, `_on_toggle_bm_side_by_side` reparents `block_mesh_panel` from the `upper_tabs` `QTabWidget` into `_tree_bm_splitter` (a `QSplitter(Qt.Horizontal)` that wraps `right_upper_splitter` and is itself the content of the Tree tab). The Tree tab is switched to first so the splitter is visible before reparenting; `setSizes([1,1])` and `_init_plotter()` are deferred to the next event-loop tick via `QTimer.singleShot(0, ...)`. When side-by-side mode is turned off, `block_mesh_panel` is moved back into `upper_tabs` as a normal tab.

**Comparison panel visibility** — `comparison_panel` is added to `right_upper_splitter` at startup but immediately hidden (`comparison_panel.hide()`). Qt `QSplitter` ignores hidden children, so no handle or gap appears. `_on_side_by_side_toggled(True)` calls `comparison_panel.show()` before `setSizes`; `_on_side_by_side_toggled(False)` and `_clear_diff` call `comparison_panel.hide()` after.

**Preview mode** — `BlockMeshPanel` carries two extra flags set on every `update_block_mesh()` call: `_has_variables` (True when the `vertices` raw_list value contains a `$` character) and `_preview_mode` (False by default, toggled by the **Preview** button). When `_has_variables` is True a `_vtx_info_bar` widget (amber **⚙ Variable-based** chip + **Preview** toggle) appears inside the Vertices group box above the table, and the X/Y/Z cells are made read-only (`rw_flags = ro_flags`). When `_preview_mode` is True the cells are editable and `_on_cell_changed` calls `_render()` directly instead of emitting `vertices_changed` — keeping the tree and file untouched. `_on_refresh()` re-extracts from `self._root` before calling `_render()` when in preview mode, which both resets the vertex data and exits preview.

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
