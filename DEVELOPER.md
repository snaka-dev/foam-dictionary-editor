# Foam Dictionary Editor (FoDE) — Developer Guide

For user documentation, see [USER_GUIDE.md](USER_GUIDE.md).
For installation and basic usage, see [README.md](README.md).

## Project structure

A typical project layout is as follows.

```text
foam-dictionary-editor/
├── docs/
│   └── images/              # screenshots used in USER_GUIDE.md
├── tools/
│   └── generate_foam_keywords.py  # CLI wrapper around app_config/keyword_generator.py; --dir picks an installation root (default: sourced environment)
├── tutorials/               # bundled example cases (GPL-3.0, see tutorials/README.md)
├── main.py
├── _version.py              # single source of truth for the app version; get_version() adds a git dev-build suffix when run from a checkout
├── requirements.txt
├── requirements-dev.txt
├── requirements-packaging.txt
├── README.md
├── README_ja.md
├── USER_GUIDE.md
├── USER_GUIDE_ja.md
├── DEVELOPER.md
├── DEVELOPER_ja.md
├── RELEASE_NOTES.md
├── RELEASE_NOTES_ja.md
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
│   ├── defaults.py
│   └── keyword_generator.py  # scans an OpenFOAM installation (etc/caseDicts templates; TypeName/ClassName + addNamedTo* macros and dictionary-read calls — lookup("…"), get<…>("…"), readEntry("…"), … — in src/ and applications/ sources) to build foam_keywords.json (user-generated, gitignored; overrides the tracked foam_keywords.default.json baseline). Installation root via generate(project_dir=…) or the sourced environment (read through services/foam_env.foam_env_dirs, imported lazily); the output is written atomically via json_io.atomic_write_text; payload carries provenance metadata (source, version, generated, note — identifier names only, no OpenFOAM source code). Shared by tools/generate_foam_keywords.py and the Settings menu action
├── foam/
│   ├── block_mesh_extractor.py  # extracts vertices/blocks/boundary from blockMeshDict FoamNode tree; _HEX_FACE_VERTICES + _expand_compact_faces convert compact (blockIdx, faceIdx) boundary entries to 4-vertex lists; _compute_default_faces collects exterior block faces unclaimed by any patch (blockMesh's implicit defaultFaces — what quasi-2-D cases leave unlisted) into BlockMeshData.default_faces; parse_vertices() is public; delegates variable resolution to var_resolver
│   ├── var_resolver.py          # shared variable resolution: build_var_map(root, skip_keys) iteratively resolves $vars (including negated-macro word nodes like -$xMax) and #eval{} chains of arbitrary depth; substitute_vars() and eval_foam_expr() are public helpers used by both extractors
│   ├── topo_set_extractor.py    # extracts renderable geometry (box incl. min/max and multi-box `boxes` forms, rotated box, sphere incl. origin alias + innerRadius, cylinder, cone, point sets: nearestTo*/insidePoints/nearPoint, planeToFaceZone plane) from topoSetDict action_entry nodes; resolves $var and #eval inside raw_list / macro geometry values via var_resolver; returns TopoSetData(shapes=[TopoShape(...)]). All extractor shape classes (TopoShape/SnappyShape/SetFieldsShape) share the label/kind field scheme: display name + geometry/source keyword. The per-source geometry dispatch is exposed as resolve_source_geometry() / is_non_geometric_source(), shared with set_fields_extractor.py
│   ├── set_fields_extractor.py  # extracts renderable region geometry from setFieldsDict's regions ( … ) list (region_block → region_entry nodes; the entry NAME is the source type — boxToCell, sphereToCell, … — there is no `source` child); reuses topo_set_extractor.resolve_source_geometry(); labels each shape with a fieldValues summary (e.g. "alpha.water=1"); returns SetFieldsData(shapes=[SetFieldsShape(...)])
│   ├── sampling_extractor.py    # extracts renderable sampling geometry — probes probeLocations (point markers), sets-type sample lines (start/end), surfaces-type plane/cuttingPlane discs — from controlDict's functions {} block or a standalone sampling dict (system/sample, probes, surfaces, singleGraph incl. the .org root-level start/end style); both nested member-list syntaxes are structural parser nodes: the dictionary form sets {}/surfaces {} and the classic parenthesised list form sets ( name {…} ) as a named_dict_list; reuses tree_utils.resolve_plane_geometry; returns SamplingData(shapes=[SamplingShape(...)])
│   ├── snappy_hex_mesh_extractor.py  # extracts geometry {} primitives (box, sphere incl. ellipsoid via vector radius, cylinder, cone, triSurfaceMesh/distributedTriSurfaceMesh resolved against constant/triSurface/ incl. transparent .gz sibling resolution, and box-based collection members) from snappyHexMeshDict; cross-references castellatedMeshControls.refinementSurfaces/refinementRegions (incl. regex-pattern surface names) to classify each shape surface/region/geometry; extracts locationInMesh/locationsInMesh; returns SnappyHexMeshData(shapes=[SnappyShape(...)])
│   ├── tree_utils.py            # generic FoamNode helpers shared by the topo_set / snappy_hex_mesh / set_fields extractors: find_child, find_child_any, resolve_scalar, resolve_vector, resolve_point_list, expand_evals, and the shared box/sphere/cylinder/cone geometry resolvers (resolve_box_geometry covers the min/max, `box (min) (max)` pair, and multi-box `boxes` forms behind opt-in flags)
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
│   ├── snappy_hex_mesh_dict/    # package: split by subdomain (geometry, castellated mesh, snap, layers, mesh quality)
│   │   ├── __init__.py          # merges submodule SCHEMAS dicts, re-exports TARGET_FILE
│   │   ├── _common.py           # shared SWITCH_CHOICES
│   │   ├── _geometry.py
│   │   ├── _castellated_mesh.py
│   │   ├── _snap_controls.py
│   │   ├── _add_layers.py
│   │   └── _mesh_quality.py
│   └── registry.py
├── services/
│   ├── case_copier.py
│   ├── case_files_config.py
│   ├── case_loader.py       # also detect_poly_mesh() -- PolyMeshInfo(n_points, n_cells, n_faces, stale) from constant/polyMesh/owner's FoamFile note field
│   ├── example_search.py    # discover_installations()/search_examples(): find OpenFOAM installs (foam_env env reading → well-known paths) and scan their tutorials/ + etc/caseDicts/ for a keyword, returning SearchHits (matched lines, enclosing tutorial case root)
│   ├── foam_env.py          # foam_env_dirs(env) → FoamEnvDirs: single source of truth for reading $WM_PROJECT_DIR/$FOAM_TUTORIALS/$FOAM_ETC/$FOAM_SRC/$FOAM_APP (fields None unless the dir exists; project-dir fallbacks); shared by example_search, keyword_generator, and AppConfigManager.foam_tutorials_dir (the latter two import it lazily — app_config is a lower layer than services)
│   ├── log_summary.py       # parse_log()/format_summary(): condense blockMesh/snappyHexMesh/topoSet and solver run logs (log.* stdout, not FoamNode dict trees; solvers detected by time-loop shape, not name) into a short LogSummary report
│   └── tool_options.py      # ToolSpec/ToolOption specs (TOOL_SPECS) + build_args()/build_command() for the Tools-menu "Run *" options dialogs; always tees to log.<tool>
├── i18n/
│   ├── __init__.py             # tr(), set_language(), get_language(), available_languages()
│   └── ja.py                   # Japanese translations (LANGUAGE_NAME + TRANSLATIONS dict)
├── ui/
│   ├── app_state.py            # AppState dataclass: all 16 shared mutable fields (diff is a nested DiffState, undo a nested UndoState holding the global UndoSnapshot undo/redo stacks); MainWindow sets self.state = AppState()
│   ├── mixins/
│   │   ├── _boundary_ops.py        # mixin: boundary view patch operations
│   │   ├── _case_ops.py            # mixin: open/reload/duplicate/save-as case, settings
│   │   ├── _diff_ops.py            # mixin: side-by-side comparison, diff compute/clear; _reset_diff_for_case_dir reconciles an active comparison after _load_case_dir (clear on a case switch, re-arm on a same-dir reload); reference-file parse failures are reported in the status bar (per-file in _recompute_diff, a skipped-count summary at the end of the precompute scan)
│   │   ├── _file_mgmt_ops.py       # mixin: create/add/backup/delete/duplicate/clean file operations
│   │   ├── _file_ops.py            # mixin: per-file load/save, directory scan helpers
│   │   ├── _foam_monitor_ops.py    # mixin: foamMonitor launch/stop/poll, gnuplot reread patch
│   │   ├── _model_ops.py           # mixin: buffer/tree state, dirty tracking, parse cache
│   │   ├── _panel_ops.py           # mixin: BlockMesh panel and terminal mode toggle handlers
│   │   ├── _tools_ops.py           # mixin: Tools-menu actions — restore 0/ from 0.orig, run blockMesh/snappyHexMesh/topoSet/setFields/checkMesh via _run_tool_with_options (RunToolDialog per tool; pre-flight warnings embedded — time-dir results for the mesh tools via _rerun_over_results_warning, a default-checked "Restore 0/ from 0.orig/ first" prefix checkbox for setFields since it rewrites 0/ in place and re-runs compound; checkMesh is read-only so gets no warning; last-used option values kept in state.run_tool_options), run Allrun/Allclean scripts, clean case via foamCleanTutorials (Allrun offers "clean, then run" when log.* files exist, since runApplication skips already-logged steps), open ParaView, view log summary (non-modal LogSummaryDialog, kept alive via self._log_summary_dialog), find OpenFOAM examples (non-modal FindExamplesDialog, kept alive via self._find_examples_dialog; its compare_requested feeds _diff_ops._start_comparison_with, its duplicate_requested feeds _case_ops._duplicate_case_from with the home dir as the fallback destination)
│   │   ├── _tree_crud_ops.py       # mixin: tree entry CRUD (copy/paste, add, duplicate, comment out, delete, restore) and _apply_comparison_value
│   │   ├── _tree_sync_ops.py       # mixin: editor↔tree sync (apply text to tree, reload from tree)
│   │   ├── _undo_ops.py            # mixin: snapshot-based tree undo/redo (Ctrl+Z / Ctrl+Shift+Z scoped to the tree; one global timeline of serialized-text snapshots)
│   │   └── _ui_ops.py              # mixin: label updates, schema manager, help dialogs, language menu, tree column toggles
│   ├── layout_constants.py
│   ├── main_window.py          # core: __init__, _build_ui and sub-builders, drag-and-drop (dragEnterEvent/dropEvent/eventFilter)
│   ├── dialogs/
│   │   ├── about_dialog.py
│   │   ├── add_files_dialog.py
│   │   ├── boundary_edit_dialog.py
│   │   ├── case_library_dialog.py
│   │   ├── clean_backups_dialog.py
│   │   ├── duplicate_case_dialog.py
│   │   ├── export_stl_dialog.py  # ExportStlDialog: modal checklist of loaded topoSetDict/snappyHexMeshDict shapes; writes each checked one to its own .stl via BlockMeshRenderer._make_shape_mesh
│   │   ├── find_examples_dialog.py  # FindExamplesDialog: non-modal keyword search over an installation's tutorials/ + etc/caseDicts/ (services/example_search.py in a background QThread), syntax-highlighted preview, Copy, "Compare with this case" (emits compare_requested), and "Duplicate this case…" (emits duplicate_requested); installation picker is the shared widgets/installation_selector.InstallationSelector
│   │   ├── foam_monitor_dialog.py  # FoamMonitorDialog: file picker + foamMonitor option controls (log scale, grid, refresh, idle, extra flags)
│   │   ├── generate_keywords_dialog.py  # GenerateKeywordsDialog: runs app_config/keyword_generator.py in a background QThread with progress log; installation picker is the shared widgets/installation_selector.InstallationSelector (same discovery + persisted openfoam_dir key as FindExamplesDialog)
│   │   ├── keyboard_shortcuts_dialog.py
│   │   ├── log_summary_dialog.py  # LogSummaryDialog: non-modal (like find_examples_dialog, unlike the other dialogs here) file picker + Summary/Raw Log tabs over services/log_summary.py
│   │   ├── manage_extra_files_dialog.py
│   │   ├── openfoam_resources_dialog.py
│   │   ├── rename_boundary_dialog.py  # Rename Boundary dialog + find_rename_targets() scanner
│   │   ├── reset_settings_dialog.py
│   │   ├── run_tool_dialog.py  # RunToolDialog: generic Tools-menu "Run *" options dialog built from services/tool_options.TOOL_SPECS — curated flag widgets, free-text extra options, live command preview, optional pre-flight warning and shell-prefix checkbox
│   │   ├── save_as_new_case_dialog.py
│   │   └── schema_manager_dialog.py
│   ├── panels/
│   │   ├── block_mesh_panel.py     # 3-D viewer for blockMeshDict (pyVista/VTK, lazy init); also overlays topoSetDict (topoSet ▾ menu), snappyHexMeshDict (snappyHexMesh ▾ menu), setFieldsDict regions (setFields ▾ menu), and sampling definitions (sample ▾ menu; union of controlDict functions {} plus standalone system/sample-style dicts, kept per source basename in _sampling_by_file) geometry, each with per-shape visibility toggles, Show all/Hide all actions, and a "Non-geometric sources (N)" submenu for entries with no drawable geometry; delegates actor setup to block_mesh_renderer.BlockMeshRenderer; STL ▾ menu's "Export Shapes as STL…" opens dialogs/export_stl_dialog.ExportStlDialog
│   │   ├── block_mesh_renderer.py  # BlockMeshRenderer: VTK render pipeline for blockMeshDict/topoSetDict/snappyHexMeshDict/setFieldsDict geometry via RenderSettings dataclass; _make_shape_mesh dispatches on geometry dict keys (box, boxes, centre+radius incl. list-radius ellipsoid and hollow innerRadius, p1+p2+radius, origin+i+j+k, stl_path, planePoint+planeNormal disc sized via plane_size; points returns None — drawn as markers instead) shared by all overlay sources; overlay shapes are clipped (display-only) to the block-mesh AABB expanded 10%/axis via _clip_to_bounds — labels gain "✂ clipped" / "⚠ outside block mesh" marks, an enclosing shape falls back to its AABB overlap box, and STL export stays unclipped; _render_boundary_faces also draws BlockMeshData.default_faces in fainter "empty" grey; only imported after the pyvista guard passes
│   │   ├── boundary_view_panel.py
│   │   ├── comparison_tree_panel.py  # read-only reference-case tree; emits use_value_requested(FoamNode)
│   │   ├── detail_panel.py
│   │   ├── editor_panel.py
│   │   ├── file_list_panel.py
│   │   └── terminal_panel.py       # TerminalPanel wrapper: mode_changed signal, xterm/simple toggle logic
│   └── widgets/
│       ├── code_editor.py
│       ├── flow_layout.py              # FlowLayout(QLayout): wrapping toolbar layout — min width is the widest single item; used by the BlockMesh panel toolbar
│       ├── installation_selector.py    # InstallationSelector(QWidget): combo + Browse… row over services/example_search.discover_installations() and the persisted openfoam_dir key; installations_available/error signals; shared by find_examples_dialog and generate_keywords_dialog
│       ├── _foam_highlighter.py        # FoamHighlighter(QSyntaxHighlighter): OpenFOAM token colouring; loads app_config/foam_keywords.json (user-generated) or, when absent, app_config/foam_keywords.default.json (shipped baseline) in 1,000-keyword QRegularExpression chunks; the number rule (_NUMBER_RE) and all keyword rules are lookaround-guarded so digits glued to identifiers ("wall0") and keyword prefixes of dotted names ("y0" in "y0.1") are not partially coloured
│       ├── _simple_terminal_widget.py  # SimpleTerminalWidget: QProcess-based terminal (no WebEngine)
│       └── _xterm_widget.py            # PtyBackend, TerminalBridge, XtermTerminalWidget (Unix + QtWebEngine only); exports _XTERM_AVAILABLE
└── tests/
    ├── conftest.py
    ├── test_lint.py             # runs ruff + mypy as part of the pytest suite (scoped to foam/, model/, app_config/, schemas/, services/, ui/app_state.py)
    ├── test_version.py          # _version.get_version(): git-describe formatting (exact tag, ahead-of-tag, dirty, bare hash, no-git fallback)
    ├── foam/
    │   ├── test_diff.py
    │   ├── test_parser_block_mesh_dict.py
    │   ├── test_parser_control_dict.py
    │   ├── test_parser_fv_schemes.py
    │   ├── test_parser_fv_solution.py
    │   ├── test_parser_named_dict_list.py
    │   ├── test_parser_set_fields_dict.py
    │   ├── test_parser_topo_set_dict.py
    │   ├── test_sampling_extractor.py
    │   ├── test_set_fields_extractor.py
    │   ├── test_snappy_hex_mesh_extractor.py
    │   ├── test_source_lines.py
    │   ├── test_topo_set_extractor.py
    │   ├── test_topo_set_shapes_tutorial.py
    │   ├── test_tree_utils.py
    │   ├── test_utils.py
    │   ├── test_var_resolver.py
    │   └── test_writer_roundtrip.py
    ├── model/
    │   ├── test_bool_nonuniform.py
    │   ├── test_boundary_model.py
    │   ├── test_file_list_model.py
    │   └── test_tree_model.py
    ├── ui/
    │   ├── test_apply_comparison_value.py
    │   ├── test_block_mesh_panel_sampling_select.py
    │   ├── test_block_mesh_panel_set_fields_select.py
    │   ├── test_block_mesh_panel_snappy_select.py
    │   ├── test_block_mesh_panel_topo_select.py
    │   ├── test_block_mesh_renderer_topo.py
    │   ├── test_bm_side_by_side_multi_dict.py
    │   ├── test_boundary_view_copy.py
    │   ├── test_case_switch_clears_block_mesh_panel.py
    │   ├── test_code_editor.py
    │   ├── test_comparison_tree_panel.py
    │   ├── test_diff_state_reset_on_case_change.py
    │   ├── test_drag_drop_open_case.py
    │   ├── test_duplicate_case.py
    │   ├── test_editor_panel.py
    │   ├── test_export_stl_action_state.py
    │   ├── test_export_stl_dialog.py
    │   ├── test_file_list_panel.py
    │   ├── test_find_examples_dialog.py
    │   ├── test_flow_layout.py
    │   ├── test_foam_highlighter.py
    │   ├── test_log_summary_dialog.py
    │   ├── test_main_window_save_refresh.py
    │   ├── test_main_window_split.py
    │   ├── test_manage_extra_files_dialog.py
    │   ├── test_rename_boundary.py
    │   ├── test_run_tool_dialog.py
    │   ├── test_stays_open_menu.py
    │   ├── test_terminal_panel.py
    │   ├── test_tools_ops_mesh_actions.py
    │   ├── test_tree_color_lexer_dispatch.py
    │   ├── test_tree_copy_paste.py
    │   ├── test_tree_inline_edit_dirty.py
    │   ├── test_tree_undo_redo.py
    │   └── test_view_log_summary_action.py
    ├── services/
    │   ├── test_backup.py
    │   ├── test_case_copier.py
    │   ├── test_case_files_config.py
    │   ├── test_case_loader.py
    │   ├── test_example_search.py
    │   ├── test_foam_env.py
    │   ├── test_log_summary.py
    │   └── test_tool_options.py
    ├── app_config/
    │   ├── test_app_config.py
    │   ├── test_json_io.py
    │   └── test_keyword_generator.py
    └── schemas/
        └── test_schemas.py
```

### Documentation map

| File | Role |
|---|---|
| `README.md` | Short introduction: installation, quick-start workflow, and a condensed feature overview whose group headings deep-link into the user guide. |
| `USER_GUIDE.md` | Full feature reference. **When adding a user-visible feature, also add it to the "Where to Find Things" table and the Contents list** — these navigation aids drift silently otherwise. |
| `DEVELOPER.md` | This file: project structure, internals, dev setup, and testing. |
| `RELEASE_NOTES.md` | User-facing change log; new entries accumulate under `## Unreleased` and the heading is renamed to a version number on release. |
| `docs/SCREENSHOTS.md` | Annotated screenshot gallery of the main window, BlockMesh 3-D overlays, and key dialogs/menus. |

Every English document has a Japanese counterpart (`*_ja.md`); any edit to one must be mirrored in the other. Japanese docs keep menu labels and other UI strings in English.

### Test coverage notes

One line per test file, grouped by directory. Keep this in sync when adding or removing a test file — it's the thing that drifted silently before.

**`tests/foam/`**
- `test_diff.py` — `diff_trees`/`diff_trees_reverse`: identical trees, changed values, keys only in one tree, nested dictionaries, anonymous node skipping, `field_value_block` entries, symmetry between the two functions.
- `test_parser_block_mesh_dict.py` — `boundary_block`/`boundary_entry` structured parsing, round-trip writing, `extract_block_mesh_data` output; variable resolution (`$varName`, `${varName}`, macros, negated-macro word nodes like `-$xMax`, `#eval{ expr }`, multi-level chains); compact `(blockIndex, faceIndex)` boundary face notation, including combined with negated-macro vertex variables; `default_faces` extraction (fully-claimed boundary → empty, unassigned exterior faces collected, claim matching in any vertex rotation, shared inter-block faces excluded).
- `test_parser_control_dict.py` — `controlDict` parsing: FoamFile header, int/scalar/word values, `#directives`, `functions` sub-dicts, and parser-failure fallback to an empty root.
- `test_parser_fv_schemes.py` — `fvSchemes` parsing: compound values, `ddtSchemes`/`divSchemes`/`interpolationSchemes`/`snGradSchemes` blocks, presence of all top-level blocks, round-trip writing.
- `test_parser_fv_solution.py` — `fvSolution` parsing: macro and regex-pattern solver keys, the `PIMPLE` block, solver `tolerance`/`smoother` entries, round-trip writing.
- `test_parser_named_dict_list.py` — the optional named-dict-list syntax: `sets`/`surfaces` parenthesised lists of named dicts parse to `named_dict_list`/`named_dict_entry` (top-level and nested in a function-object dict), the lookahead keeps plain word/string lists (`sets (setA setB);`) and empty lists on the ordinary value path, unmodified round-trip is byte-identical, and a modified entry's siblings keep their names.
- `test_parser_set_fields_dict.py` — `setFieldsDict` parsing: `defaultFieldValues`/`regions` field-value entries (including vector values), `box_pair` parsing, round-trip writing after an edit.
- `test_parser_topo_set_dict.py` — `action_list`/`action_entry` structured parsing: node type, entry count, named child values, `box_pair` coordinates, source-less entries, round-trip writing, positional diff detection via `_diff_action_list`.
- `test_snappy_hex_mesh_extractor.py` — `extract_snappy_hex_mesh_data`: `geometry` box/sphere (scalar and vector/ellipsoid radius)/cylinder/cone extraction; `name` override resolution (`geom.stl { name geom; }`); `triSurfaceMesh`/`distributedTriSurfaceMesh` file resolution against `constant/triSurface/` (explicit `file` child, implicit filename-as-key, missing file), including transparent `.gz` resolution (a plain-name entry resolving to a `.gz`-only file on disk, a `.gz`-suffixed entry key/file resolving directly, and a `.gz`-suffixed reference falling back to an uncompressed file on disk); `collection` (searchableSurfaceCollection) box members via `rotation none` and `e1`/`e3` axes (including a case that actually rotates), skipped for a non-box base or a missing/unsupported transform; `refinementSurfaces`/`refinementRegions` cross-referencing by exact name and by regex-pattern key (e.g. `"iglo.*"`); `locationInMesh` (singular) and `locationsInMesh` (plural) point extraction; `$var`/`#eval{}` resolution.
- `test_source_lines.py` — `source_line`/`source_end_line` population for all node types.
- `test_topo_set_extractor.py` — `extract_topo_set_data`: plain typed values for all three geometry types (box, sphere, cylinder), `$var` resolution in vectors and scalars, `#eval{...}` inside `raw_list`, chained var/eval resolution, unresolvable-variable skipping, all face/point source variants.
- `test_sampling_extractor.py` — `extract_sampling_data`: probes in a `functions {}` block, dict-form `sets {}` line/cloud members and the parenthesised list form (in a functions {} block and at file root, sampleDict-style), `plane`/`cuttingPlane`/`patch` surface members, root-level `singleGraph`-style `start`/`end`, standalone `sample`/`probes` files, `$var` resolution, and non-sampling function objects being ignored.
- `test_set_fields_extractor.py` — `extract_set_fields_data`: box/sphere/cylinder region extraction (entry name as source type), the `fieldValues` label summary (scalar and vector values), non-geometric source classification (`zoneToCell`), `$var` resolution, and the unresolvable-geometric-source case.
- `test_topo_set_shapes_tutorial.py` — `extract_topo_set_data` against the bundled `tutorials/topoSetShapes` case: every geometry source is extracted and all shapes lie within the domain.
- `test_tree_utils.py` — direct `tree_utils` resolver contracts (the extractor tests only exercise them indirectly): `find_child`/`find_child_any` alias precedence, `expand_evals`, `resolve_scalar` (scalar/int/macro/`${…}`/`#eval`), `resolve_vector` arity/numeric guards, `resolve_point_list`, the sphere/cylinder/cone resolvers with their opt-in flags, and `resolve_box_geometry` (min/max vs `box` pair vs multi-`boxes` precedence and flag gating).
- `test_utils.py` — `is_large_non_foam_file`: small files never flagged regardless of header, large files with a `FoamFile` token in the first 512 bytes not flagged, large files without it flagged, missing files return `(False, 0)`, a header preceded by a comment is still detected.
- `test_var_resolver.py` — `build_var_map`, `substitute_vars`, `eval_foam_expr`: scalar/int seeding, macro chains, `#eval` expressions, negated-macro word nodes, unresolvable vars staying absent, `skip_keys` exclusion, dictionary node non-collection.
- `test_writer_roundtrip.py` — `write_root`/`write_node` broadly: unmodified nodes reproduced via `raw_text`, modified word/int/scalar/vector nodes regenerated, directive/unknown-raw/macro entries preserved, nested dictionaries, excess-blank-line suppression, `field_value_block`/`region_block` round-tripping (including a field value edited inside a region), and the regression where regenerating one region entry dropped unmodified siblings' names (entry `raw_text` now starts at the name token).

**`tests/model/`**
- `test_bool_nonuniform.py` — `bool`/`nonuniform_list` parsing and round-tripping, `FoamTreeModel` bool editing (case-insensitive, rejection signal), `nonuniform_list` display/non-editability, parser error collection for bad entries.
- `test_boundary_model.py` — `extract_boundary()` and `BoundaryModel`: loading, field updates, per-directory boundary sets, `_is_in_dir` multi-level matching, model clearing.
- `test_file_list_model.py` — `FileListModel`: loading, sorted groups, dirty-state and diff-state per item, extra-files handling, clearing.
- `test_tree_model.py` — `set_diff(reverse=True)`: remaps `"only_here"` to `"only_in_ref"`, leaves `"changed"` unchanged, returns the light-green `BackgroundRole` colour, includes `"only in reference case"` in the tooltip. `FoamNode` carries `__hash__ = object.__hash__` so instances can be used as dict keys in the diff map.

**`tests/ui/`**
- `test_apply_comparison_value.py` — `_apply_comparison_value` ("Use this value"): creating missing parent dictionaries when adopting a nested entry (e.g. `functions/forces1/rhoInf` into a case without `functions {}`), appending unnamed `#includeFunc` directives by content into an existing block without overwriting it, skipping an identical directive instead of duplicating it, the plain named-value overwrite path, and refusing when the enclosing key exists but is not a dictionary.
- `test_block_mesh_panel_sampling_select.py` — the `sample ▾` per-shape visibility menu: population from a controlDict `functions {}` block (rows tagged with the source basename), individual/master toggling, greyed-out non-geometric entries, the multi-file union (controlDict + system/sample) with per-file replacement on reload, and `clear()` resetting `_sampling_by_file`.
- `test_block_mesh_panel_set_fields_select.py` — the `setFields ▾` per-shape visibility menu: population from the bundled damBreak tutorial's `setFieldsDict` (rows labelled with the `fieldValues` summary), individual/master toggling, greyed-out non-geometric sources, inclusion in STL export, and clearing on reload.
- `test_block_mesh_panel_snappy_select.py` — the `snappyHexMesh ▾` per-shape visibility menu: population, individual/master toggling, the surface/region/geometry category-colour legend, greyed-out non-geometric sources, `locationInMesh`/`locationsInMesh` keep-point toggles.
- `test_block_mesh_panel_topo_select.py` — the `topoSet ▾` per-shape visibility menu: population, individual/master toggling, Show all/Hide all, the action-colour legend, the "Non-geometric sources (N)" submenu of greyed-out entries, and the exclusion of point/plane shapes from STL export.
- `test_block_mesh_renderer_topo.py` — `_make_shape_mesh` geometry generation for cones (true and frustum), hollow annuli, `rotatedBoxToCell`, sphere (scalar radius and vector-radius ellipsoid), and `stl_path` mesh loading (present and missing file, plus a gzip-compressed `.stl.gz` file via `read_surface_mesh`); `read_surface_mesh` plain-file passthrough; the overlay clip helpers (`_expanded_bounds` per-axis padding incl. degenerate 2-D axes; `_clip_to_bounds` fits-inside/clipped/outside/enclosing-stand-in cases).
- `test_bm_side_by_side_multi_dict.py` — the `⊞` side-by-side corner button (`_update_bm_side_by_side_btn`): enabled for `blockMeshDict`, `topoSetDict`, `snappyHexMeshDict`, and `controlDict` (sampling overlay); disabled for an unrelated dict (e.g. `fvSchemes`). Also asserts the tree/BlockMesh splitter panes are non-collapsible and the panel keeps its 150-px minimum width.
- `test_flow_layout.py` — `FlowLayout` (ui/widgets/flow_layout.py): minimum width equals the widest single item, `heightForWidth` wrapping when narrowed, item order/positions after a wrap, and `takeAt` bookkeeping.
- `test_boundary_view_copy.py` — `BoundaryViewPanel._table_data()` and Copy Table: Markdown and CSV export in both orientations.
- `test_case_switch_clears_block_mesh_panel.py` — `_load_case_dir()` fully resets `BlockMeshPanel` state via `clear()` (not just the `_topo_shapes`/`_snappy_shapes` lists) when switching to a different case: per-shape menu actions, `non_geometric` lists, `locationInMesh`/`locationsInMesh` markers, and the `Export Shapes as STL…` action's enabled state all clear.
- `test_code_editor.py` — `CodeEditor` fold-map computation, collapse/expand toggling, automatic folding of the `FoamFile { … }` header and the top-of-file comment banner on load.
- `test_comparison_tree_panel.py` — `ComparisonTreePanel`: `load` sets the header label, populates the proxy, collapses the FoamFile node, re-applies Type column visibility; `clear` resets model and header; `set_type_column_visible` hides/shows the Type column and persists across `load` calls; `use_value_requested` signal is connectable.
- `test_diff_state_reset_on_case_change.py` — `_reset_diff_for_case_dir` regression: opening a different case clears the active comparison (diff state, bar, panel, parse cache); reloading the same case keeps it armed; no-op without an active comparison.
- `test_drag_drop_open_case.py` — `MainWindow` drag-and-drop case opening: `dragEnterEvent`, `dropEvent`, and the `eventFilter` that makes every child widget a valid drop target.
- `test_duplicate_case.py` — case duplication: what gets copied in "all files" vs. "app-visible files only" mode, destination creation, extra files configured for the case are copied too.
- `test_editor_panel.py` — `EditorPanel`'s `user_text_changed` gating: not emitted by the programmatic paths (`set_text()`, `reload_highlighting()` — `QSyntaxHighlighter.rehighlight()` fires `textChanged` even though only formatting changed, which used to mark the file dirty after Generate OpenFOAM Keywords), emitted by direct document edits.
- `test_export_stl_action_state.py` — the `STL ▾` menu's "Export Shapes as STL…" action (`_export_stl_act`): disabled by default, enabled after `update_topo_set`/`update_snappy_hex_mesh` loads geometric shapes, disabled again after `clear()` or reloading an empty dict.
- `test_export_stl_dialog.py` — `ExportStlDialog`: row count and labelling for combined topoSet+snappyHexMesh shapes, default checked state mirrors the passed-in visibility sets, Select All/Deselect All, writing one `.stl` per checked shape (round-tripped via `pyvista.read()`), filename de-duplication on label collision, skipping (not raising on) degenerate geometry, and `_safe_filename` sanitization.
- `test_file_list_panel.py` — the diff filter: `set_diff_filter_enabled` shows/hides and unchecks the checkbox; the filter hides zero-diff file items while always showing headers; `mark_diff` updates item visibility immediately when the filter is active.
- `test_find_examples_dialog.py` — `FindExamplesDialog`: non-modal window modality, installation-combo population (with `discover_installations` monkeypatched to a fake install), grouped Tutorials/caseDicts results after a threaded search, preview + Compare/Duplicate-button enablement for tutorial hits vs. caseDicts hits, Copy-to-clipboard, `compare_requested`/`duplicate_requested` emitting the tutorial case root, the no-match/blank-query/no-source status messages, and the file-name filter.
- `test_foam_highlighter.py` — `FoamHighlighter`: comments, strings, `#directives`, `$macro` references, reserved keywords, numbers (including the lookaround guards keeping digits inside identifiers like `wall0`/`inlet-1` uncoloured), keyword rules sharing the same guards so dotted identifiers like `y0.1` (or `off.1`, shell `config.fi`) are not split, dictionary-key colouring sourced from the schema registry and the keyword JSON (user `foam_keywords.json` preferred, shipped `foam_keywords.default.json` fallback, empty set when both absent), the 1,000-keyword `QRegularExpression` chunking, the enable/disable toggle.
- `test_log_summary_dialog.py` — `LogSummaryDialog`: non-modal window modality, defaulting to the most-recently-modified `log.*` file in the case directory and showing its summary, re-parsing when the file field changes, and the empty-case-directory fallback message.
- `test_main_window_save_refresh.py` — first behavior-level `MainWindow` test (vs. `test_main_window_split.py`'s structural checks only): editing without saving leaves the `constant/polyMesh` mesh indicator unchanged; `save_file()`/`save_all_files()` both refresh the file list immediately so the staleness indicator updates without a full "Reload Case".
- `test_main_window_split.py` — the mixin structure: each mixin owns the right methods (including `_on_patch_selected` in `_BoundaryOpsMixin`, `_apply_comparison_value` in `_TreeCrudOpsMixin`, and the foamMonitor methods in `_FoamMonitorOpsMixin`), no cross-mixin duplicates, `MainWindow` inherits from all mixins.
- `test_manage_extra_files_dialog.py` — `ManageExtraFilesDialog`: display of registered extra files/directories and removal actions.
- `test_rename_boundary.py` — `find_rename_targets()`: detection of `boundary_entry` nodes in `blockMeshDict`, `dictionary` patch nodes in `boundaryField` blocks, absence of false positives for unrelated dictionaries, empty-input edge cases.
- `test_run_tool_dialog.py` — `RunToolDialog`: the live preview matching `get_command()` from a pristine dialog, checkbox/value edits updating the command, `last_values` restoration and `get_values()` round-tripping into a new dialog, the Run button disabling on unparseable extra text, the prefix checkbox prepending its shell prefix, and Browse inserting case-relative paths (absolute when outside the case).
- `test_stays_open_menu.py` — the toolbar dropdown menus (`Vertices ▾`, `Blocks ▾`, `Scale ▾`, `topoSet ▾`, `snappyHexMesh ▾`) staying open on checkable-item clicks while still closing for non-checkable actions.
- `test_terminal_panel.py` — `SimpleTerminalWidget` and `TerminalPanel`: initial state, working-directory switching, cleanup, command history, the tab label, `run_command()` (including queuing before the shell is ready).
- `test_tools_ops_mesh_actions.py` — the Tools-menu "Run *" actions and Run Allrun/Run Allclean/Clean Case: the exact command string sent to a fake terminal panel after accepting the (real, exec-patched) `RunToolDialog` for blockMesh/snappyHexMesh/topoSet/setFields/checkMesh, nothing sent on cancel, the rerun warning text passed to the dialog when time dirs exist, last-used options restored from `state.run_tool_options`, the setFields restore-0/ prefix checkbox (present + checked by default with `0.orig/`, absent without, uncheckable to "run anyway"); missing-script warnings for Allrun/Allclean; the three-way Allrun pre-flight when `log.*` files exist — clean-then-run, run-anyway, cancel; the Clean Case dialog mentioning Allclean delegation or `-auto` 0/ removal; and `_update_tools_actions()`'s enablement for all these actions plus View Log Summary (which needs a case but not a terminal).
- `test_tree_color_lexer_dispatch.py` — `unknown_raw_entry` amber colouring, lexer `//` behaviour, the parser `_PAREN_DISPATCH` table.
- `test_tree_copy_paste.py` — tree Copy/Paste Value: round-tripping a copied value, pasting across differently-typed nodes, guards that reject unsupported node types.
- `test_tree_undo_redo.py` — snapshot-based tree undo/redo: an inline edit undone restores the value, editor text, and clean dirty flag (and redo re-applies it); multi-step undo; a new edit clearing the redo branch; rejected edits' stray snapshots being skipped; delete/add-entry round-trips; one CRUD operation producing exactly one snapshot (no signal double-checkpoint); a multi-file snapshot restoring every file; stacks cleared on case reload; and the depth cap.
- `test_tree_inline_edit_dirty.py` — inline Tree-panel cell edits marking the file dirty and regenerating the editor text; confirms a rejected edit leaves the file clean.
- `test_view_log_summary_action.py` — `_on_view_log_summary_clicked`: reopening after the dialog was closed (it's only hidden, not destroyed, so the cached instance must be re-shown, not just raised), the no-case-dir no-op, and following a case switch (`_load_case_dir` pushes the new directory into the already-open dialog immediately via `set_case_dir()`, not just on the next menu click).

**`tests/services/`**
- `test_backup.py` — backup-file naming (`.bak_<timestamp>`) and content (captures the in-memory buffer when the file is open, the on-disk version otherwise).
- `test_case_copier.py` — `copy_visible_files`: visible files copied with layout preserved, hidden entries (root `log.*`, time dirs, unlisted files) skipped, registered extra files and `.foam-editor-files.json` itself carried over, no-config tolerance, nested destination creation.
- `test_case_files_config.py` — `TestCaseFilesConfigDirs`: `DirEntry` add/remove/update-in-place, backward-compatible loading of plain-string JSON, config reset.
- `test_case_loader.py` — `detect_time_dirs` and `TestExtraDirs`: flat and recursive extra-directory scanning, missing-directory tolerance, duplicate suppression.
- `test_example_search.py` — `example_search`: `installation_from_dir` on an install root / bare tutorials dir / non-install dir; `discover_installations` env-mapping injection, `extra_roots` precedence, and de-duplication; `case_root_for` ancestor walking with the `stop` boundary; `search_examples` hits in both sources (source/case_root/line_numbers/snippet fields), case-insensitivity, `file_name` and `sources` filters, `max_hits` cap, `cancelled` early exit, binary/oversized-file skipping, the 50-line-number cap, blank-query `ValueError`, and the `progress` callback.
- `test_foam_env.py` — `foam_env_dirs`: explicit `FOAM_*` variables winning over `WM_PROJECT_DIR` fallbacks, per-subdirectory fallback only when the dir exists, invalid/blank variables treated as unset, version resolution.
- `test_log_summary.py` — `parse_log`/`format_summary`: `blockMesh` Mesh Information/Patches extraction and fatal-error detection; `snappyHexMesh` phase splitting on `Wrote mesh in` markers, per-category refinement iteration counts, the final per-patch layer table, and warning de-duplication with a repeat count; `topoSet` multi-source set collapsing (a `Read set` checkpoint continuing the same set rather than starting a new one); solver logs — steady converged (Run/Residuals phases, converged line, total time), transient with per-name Courant lines and the ESI `Time = 0.005s` unit suffix, fatal-error and no-`End` runs marked FAILED, and a `checkMesh`-style log with `Time =` lines but no residuals staying on the generic path; the generic tail fallback for an unrecognized utility.
- `test_tool_options.py` — `tool_options`: the expected `TOOL_SPECS` set and default commands (snappyHexMesh's default-on `-overwrite`), `build_args` bool/value/file handling in spec order, empty-value omission, shlex splitting of the extra text (unbalanced quote → `ValueError`), stale unknown flags ignored, and `build_command`'s quoting, raw prefix, and `tee log.<tool>` suffix.

**`tests/app_config/`**
- `test_app_config.py` — `AppConfigManager`: window size, default case dir, Case Library dirs (incl. the `$WM_PROJECT_DIR/tutorials` fallback), `save()`/`reset()` semantics, fallbacks when `app_config.json` is absent, combined settings, JSON structure, feature-flag handling (`set_feature`/`set_features`).
- `test_json_io.py` — `load_json` missing/corrupt/valid handling; `save_json` round-trips and parent creation; `atomic_write_text` leaves no `.tmp` sibling on success and keeps the original file intact (temp cleaned up) when the final rename or serialization fails.
- `test_keyword_generator.py` — `keyword_generator`: `scan_src_lookup_keywords()` collecting dictionary-read calls (`lookup`/`get<…>`/`readEntry`/`found`/…) from `*.C`/`*.H` with non-keyword forms rejected; `generate(project_dir=…)` over a fixture install tree — environment ignored, `version` from the dir name, provenance metadata in the payload, `RuntimeError` when nothing is collected.

**`tests/schemas/`**
- `test_schemas.py` — `ChoiceItem`/`KeySchema`, `schema_config.json` load/save/reset/delete, `SchemaRegistry` plain/parent-qualified/grandparent-qualified lookup, the `snappyHexMeshDict` schema module, the configured module list.

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
| `action_list` | `actions ( … );` in `topoSetDict`; `value=None`, children are `action_entry` nodes |
| `named_dict_list` | optional parenthesised list of named dicts — `sets ( y0.1 { … } … );` / `surfaces ( … );` (classic sampleDict style); produced only when a lookahead sees `name {` after the `(`, so plain word lists (`sets (setA setB);`) keep parsing as `raw_list` |
| `named_dict_entry` | named `{ … }` entry inside a `named_dict_list` |
| `action_entry` | anonymous `{ … }` block inside an `action_list`; `name=""`, children are the dict entries |
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
    "named_dict_list", "named_dict_entry",
    "field_value_block",
    "action_list",
})
```

Children are matched by `node.name`; anonymous nodes (empty `name`) are skipped. For `field_value_block`, `_diff_field_value_block` matches items by `field_name` from `node.value` (the same `value`-as-list layout described in [`field_value_block` children in `value`](#field_value_block-children-in-value)). For `action_list`, `_diff_action_list` matches `action_entry` children **positionally** (by index), then compares their named sub-entries by key; `action_entry` nodes themselves are anonymous (`name=""`) so they cannot be matched by name.

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

## Case-root scripts

`list_case_files` also globs `ROOT_SCRIPT_GLOB` (`All*`) at the case root, so `Allrun`, `Allrun.pre`, `Allclean`, etc. are auto-listed — these are the scripts the Tools menu executes, and listing them also makes `copy_visible_files` carry them into duplicated cases (`shutil.copy2` preserves the exec bit). Other root files (logs, `*.foam`, results) remain hidden. `model/file_list_model.py` groups root files under the `ROOT_GROUP` (`"."`) key, sorted last; `file_list_panel.py` displays that header as "case root" (via `group_display_name`, also used in header context-menu and Add-files-dialog labels) and never adds a `[+]` marker to it (unlisted logs almost always exist at the root, so the marker would be permanently on). The header offers the same New file / Add files context-menu actions as other groups — both handlers work with `"."` because pathlib normalizes it — and `list_directory_files` filters dotfiles, so the Add dialog never offers `.foam-editor-files.json`.

Because scripts are shell files, not dictionaries, they get a text-only path: `is_script_text` / `is_script_path` (`foam/utils.py`) detect the `#!` shebang, and `is_log_filename` extends the same path to `log.*` run logs (which can enter the list via a user extra directory). `load_selected_file` and `save_file` skip parsing for both (the tree is loaded with an empty root, mirroring `_clear_current_file`), `apply_text_to_tree` refuses with a status message, and both diff code paths (`_recompute_diff`, `_precompute_diff_step`) skip them so no junk tree diff is shown. `log.*` rows are additionally rendered dimmed grey via `_TEXT_ONLY_ROLE` in `file_list_panel.py` (colour priority: dirty > diff > text-only > extra). Saving uses the ordinary `Path.write_text`, which rewrites an existing file in place and therefore preserves its executable permission.

The editor highlights scripts as shell code: `EditorPanel.set_text` sniffs the shebang and calls `CodeEditor.set_shell_mode`, which switches `FoamHighlighter` (`ui/widgets/_foam_highlighter.py`) into its `"shell"` mode — `#` comments, quoted strings, `$variables`, OpenFOAM RunFunctions (`_SHELL_KEYWORD_RE`), plus the regular `_build_value_kw_rules()` keyword chunks so utility/solver names colour too. The `/* */` block-comment state machine is bypassed in shell mode.

Extra-directory scans in `list_case_files` always skip hidden entries (any path component starting with `.`), so the app's own `.foam-editor-files.json` never becomes editable in-app even when the case root (`"."`) is added as an extra directory.

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

`_mark_dirty()` (`ui/mixins/_model_ops.py:102`) sets both values to `True`, adds the `*` suffix to the window title, and calls `file_list_panel.mark_dirty()` to show the indicator in the file list. It is called from `_after_model_edit()` (after any tree edit that regenerates text via `write_root()`) and from `_on_user_text_changed()` (on any human keystroke in the editor).

`_after_model_edit()` itself is reached two ways: explicitly, by the Detail-panel "Apply" handlers and the tree CRUD operations (`_tree_crud_ops.py`) right after they call `FoamTreeModel.setData()` / `insert_node()` / `remove_node()`; and via `_load_tree()`, which connects `FoamTreeModel.dataChanged` to `_on_tree_data_changed()` (`ui/mixins/_model_ops.py`), filtered to emissions carrying `Qt.EditRole`. The signal connection is what catches edits made directly in the Tree panel's inline cell editor — Qt's item delegate calls `setData()` straight from the view, with no explicit `_after_model_edit()` call anywhere in that path. Without the `dataChanged` hook, inline tree edits change the node but never regenerate the editor text or mark the file dirty. The `Qt.EditRole` filter excludes the diff-highlight refresh (`set_diff()` / `clear_diff()`), which emits `dataChanged` with `BackgroundRole` only.

`_save_current_buffer()` (`ui/mixins/_model_ops.py:29`) flushes `editor_panel.get_text()` to `state.file_buffers[state.current_file]` and writes `state.text_dirty` back into `state.file_dirty[state.current_file]` before a file switch. This preserves unsaved edits in memory across switches.

`_mark_path_dirty(path)` marks a specific path dirty regardless of which file is currently open. Used by operations that modify non-current files (e.g. renaming a boundary patch across multiple field files).

## Tree copy/paste shortcuts

`_setup_tree_copy_paste()` (`ui/mixins/_tree_crud_ops.py:27`) attaches Ctrl+C and Ctrl+V `QShortcut` instances directly to the `tree` widget using `Qt.WidgetShortcut` scope:

```python
copy_sc = QShortcut(QKeySequence.Copy, self.tree)
copy_sc.setContext(Qt.WidgetShortcut)

paste_sc = QShortcut(QKeySequence.Paste, self.tree)
paste_sc.setContext(Qt.WidgetShortcut)
```

`Qt.WidgetShortcut` fires only when `self.tree` has keyboard focus, so Ctrl+C in the text editor is unaffected. It also does not fire while a tree cell is in inline-edit mode: Qt routes Ctrl+C to the cell editor's own selection-copy mechanism in that state.

The same two actions appear in the context menu (**Copy Value** / **Paste Value**). Paste is disabled in the menu and silently rejected when the selected node type does not support value editing.

## Tree undo/redo

`ui/mixins/_undo_ops.py` implements snapshot-based undo/redo for tree edits. Every tree mutation already ends in a full `write_root()` re-serialization, so the pre-mutation state is checkpointed as serialized *text* — one `UndoSnapshot` (`ui/app_state.py`) holding `{path: text}` and the dirty flags of every file the operation touches. Undo re-parses the snapshot and reloads the tree through the existing `_load_tree()` full-rebuild path; tree expansion/selection state is not preserved. The history is a **single global timeline** (`UndoState.undo_stack` / `redo_stack`), not per file: Ctrl+Z reverses the most recent tree operation regardless of which file is on screen — `_restore_undo_snapshot` switches the view to an affected file when the current one is not in the snapshot — and *any* new edit clears the redo branch. A boundary operation that spans several field files stores them all in one snapshot, so a single undo restores every file it touched. The stack is bounded by both a count cap (`_UNDO_DEPTH` = 50) and a total-bytes cap (`_UNDO_MAX_BYTES`), and cleared on a case change.

Checkpoints reach the stack two ways, mirroring how `_after_model_edit()` is reached:

- **`FoamTreeModel.about_to_change`** — emitted at the top of `setData()` *before* the edit is validated, so it only *stashes* a `pending` snapshot rather than committing it. `_on_tree_data_changed` (which fires only on a successful `setData`) then calls `_commit_pending_undo`, which pushes the pending snapshot and clears redo — or discards it when the resulting state is identical (a value-unchanged edit). A rejected edit never emits `dataChanged`, so its stashed snapshot is silently dropped and the stacks are untouched. This covers the inline delegate, Paste Value, and the Detail-panel Apply handlers.
- **Explicit `_checkpoint_for_undo(paths)` calls** — first line of every operation that mutates nodes directly (CRUD in `_tree_crud_ops.py`, `apply_text_to_tree` / `_on_blockmesh_vertices_changed` in `_tree_sync_ops.py`, all boundary operations in `_boundary_ops.py`). These commit immediately because the caller guarantees a real mutation follows; `UndoState.op_active` (reset on the next event-loop tick) then suppresses the redundant `about_to_change` stash from any `setData` the operation performs internally.

For the current file the snapshot text is always the editor text: in sync it is byte-faithful to the loaded file (so a fully-undone file compares clean against disk), and when the user has typed unapplied free-text it is what is on screen — either way the state undo must be able to restore. A restored file whose snapshot claims "clean" is verified against disk before the dirty flag is cleared (the file may have been saved between the mutation and the undo).

Like copy/paste, the Ctrl+Z / Ctrl+Shift+Z shortcuts are `Qt.WidgetShortcut`-scoped to the tree, so the bottom text editor keeps its native undo, and both actions appear in the tree context menu (**Undo Tree Edit** / **Redo Tree Edit**).

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

`AppConfigManager` (`app_config/app_config_manager.py`) manages persistent application settings. A single instance is obtained via `get_app_config()` and reused throughout the session. Its load/save methods delegate the actual JSON I/O to `app_config/json_io.py` (`load_json`/`save_json`), the same helper used by `services/case_files_config.py`. `save_json` writes atomically (`atomic_write_text`: sibling `.tmp` file + `os.replace`, so a failed write never truncates the existing config; a named temp file rather than `tempfile.mkstemp` keeps umask-default permissions).

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

**Side-by-side mode** — A `⊞` toggle button (`_bm_side_by_side_btn`) is added as a `QTabWidget` corner widget. When enabled, `_on_toggle_bm_side_by_side` reparents `block_mesh_panel` from the `upper_tabs` `QTabWidget` into `_tree_bm_splitter` (a `QSplitter(Qt.Horizontal)` that wraps `right_upper_splitter` and is itself the content of the Tree tab). The Tree tab is switched to first so the splitter is visible before reparenting; `setSizes([1,1])` and `_init_plotter()` are deferred to the next event-loop tick via `QTimer.singleShot(0, ...)`. When side-by-side mode is turned off, `block_mesh_panel` is moved back into `upper_tabs` as a normal tab. `_update_bm_side_by_side_btn` (`ui/mixins/_panel_ops.py`) enables the button when the current file's name is `blockMeshDict`, `topoSetDict`, `snappyHexMeshDict`, `setFieldsDict`, or one of the sampling names (`SAMPLING_DICT_NAMES`: `controlDict`, `sample`, `probes`, `surfaces`, `singleGraph`) — all render into the same 3-D view (see `block_mesh_extractor.py`, `topo_set_extractor.py`, `snappy_hex_mesh_extractor.py`, `set_fields_extractor.py`, `sampling_extractor.py`), the BlockMesh tab itself is on, and xterm is not active; it is disabled (and side-by-side mode force-exited) otherwise.

**Comparison panel visibility** — `comparison_panel` is added to `right_upper_splitter` at startup but immediately hidden (`comparison_panel.hide()`). Qt `QSplitter` ignores hidden children, so no handle or gap appears. `_on_side_by_side_toggled(True)` calls `comparison_panel.show()` before `setSizes`; `_on_side_by_side_toggled(False)` and `_clear_diff` call `comparison_panel.hide()` after.

**Preview mode** — `BlockMeshPanel` carries two extra flags set on every `update_block_mesh()` call: `_has_variables` (True when the `vertices` raw_list value contains a `$` character) and `_preview_mode` (False by default, toggled by the **Preview** button). When `_has_variables` is True a `_vtx_info_bar` widget (amber **⚙ Variable-based** chip + **Preview** toggle) appears inside the Vertices group box above the table, and the X/Y/Z cells are made read-only (`rw_flags = ro_flags`). When `_preview_mode` is True the cells are editable and `_on_cell_changed` calls `_render()` directly instead of emitting `vertices_changed` — keeping the tree and file untouched. `_on_refresh()` re-extracts from `self._root` before calling `_render()` when in preview mode, which both resets the vertex data and exits preview.

## Testing

```bash
python3 -m pytest -q
```

If `pytest -q` causes import issues, running it as `python3 -m pytest -q` is safer because the project root is handled more reliably.

`tests/test_lint.py` runs `ruff` and `mypy` as part of the suite (see below), so a plain `pytest -q` also catches lint/type regressions.

## Linting and type-checking

Configuration lives in `pyproject.toml`. `ruff` has no repo-wide `include`/`exclude` restriction, but only `foam/`, `model/`, `app_config/`, `schemas/`, `services/`, and `ui/app_state.py` are currently clean — the rest of `ui/` has pre-existing violations not yet cleaned up, so run it scoped:

```bash
ruff check foam model app_config schemas services ui/app_state.py
```

`mypy` is explicitly scoped to `foam/`, `model/`, `app_config/`, `schemas/`, `services/`, and `ui/app_state.py` via `[tool.mypy] files` in `pyproject.toml` — these are the pure-Python (or near-pure-Python) layers where static typing pays off most, plus the one `ui/` file this scope has been extended to cover; the rest of `ui/` is excluded because PySide6's stubs don't recognise the flattened enum-access style (`Qt.Horizontal` vs. the fully-qualified `Qt.Orientation.Horizontal`) used throughout the UI layer, which would otherwise produce hundreds of false positives.

```bash
mypy
```

`foam/nodes.py`'s `NodeType` `Literal` is the definitive list of valid `node_type` values; `mypy` flags any assignment or comparison against a value outside that set. See the "Node types" section above for what each value means.

## Update candidates

Ideas noted for a later release, not currently scheduled:

- **Side-by-side reference *text* editor in compare mode** — compare mode currently shows the reference case as a read-only *tree*; a read-only text editor of the reference file beside the main Editor tab would allow free-form copy/paste of keys and values (today the non-modal Find OpenFOAM Examples preview + "Copy Selection" covers this for example cases, but not for an arbitrary reference case). Revisit as part of a compare-mode update.

### Deferred review findings (undo/redo, sampling)

Low-severity items surfaced by a code review of the undo/redo and sampling work and left unfixed at the time (each was judged *plausible* rather than confirmed — narrow trigger, latent, or design-hardening). Worth folding into the next change that touches these areas:

- **`_restored_dirty` can spuriously mark a restored file dirty** (`ui/mixins/_undo_ops.py`) — it compares a `write_root`-serialized snapshot against the raw disk file, but a clean file cached only in `state.parsed_roots` (whose nodes have no `raw_text`) serializes to reformatted text that differs from disk, so undoing a multi-file operation can flag it dirty and stage a formatting-only rewrite on the next Save All. Compare against the in-memory buffer, or trust the snapshot's recorded flag, instead of re-reading disk.
- **`UndoState.op_active` reset timing is fragile** (`ui/mixins/_undo_ops.py`) — the double-checkpoint guard is cleared by `QTimer.singleShot(0, ...)`, which fires inside a nested event loop (`QMessageBox`/`QDialog.exec`). No current call site opens a dialog between its `_checkpoint_for_undo` and the mutation, so this is latent; a future op that does would let the model's `about_to_change` push a second, mid-mutation snapshot (one edit then needing two undos). Bounding the guard to the synchronous op scope (e.g. a context manager) would remove the timing coupling.
- **No enforcement that a mutation path checkpoints for undo** (`ui/mixins/_tree_crud_ops.py`, `_tree_sync_ops.py`, `_boundary_ops.py`) — undo coverage rests on ~18 hand-placed `_checkpoint_for_undo` calls plus the `about_to_change` signal for `setData`-driven edits. A future direct-mutation path that forgets its explicit call is silently non-undoable (a later Ctrl+Z jumps past it). A single post-mutation choke point that diffs the prior serialized text, or a coverage test, would make this robust.
- **Sampling overlay keys files by basename** (`ui/panels/block_mesh_panel.py`) — `_sampling_by_file` is keyed by `Path(path).name`, so two loaded sampling dicts sharing a basename (only reachable when the user adds an extra directory containing e.g. a second `sample`) overwrite each other's shapes and mislabel `source_file`. Key by the full path (display the basename).

## Acknowledgements

- [PyInstaller](https://pyinstaller.org/) — Used to build standalone executables.
- [pyVista](https://pyvista.org/) / [VTK](https://vtk.org/) — 3-D viewer for `blockMeshDict` (BSD-3-Clause, optional).
- [pytest](https://pytest.org/) / [pytest-qt](https://pytest-qt.readthedocs.io/) — Test framework.

Special thanks to the [OpenFOAM Foundation](https://openfoam.org/) and [OpenCFD / ESI Group](https://www.openfoam.com/) and all contributors for developing and maintaining OpenFOAM as free, open-source CFD software.
