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
│   ├── capture_screenshots.py     # rebuild the docs/SCREENSHOTS.md gallery from tools/screenshot_specs.json: applies a saved window state to a real MainWindow and captures it with ImageMagick's `import -frame`; one process per shot per theme, so a light/dark pair differs only in theme (see "Screenshot capture")
│   ├── screenshot_specs.json      # the gallery's shot list: one ui/window_state.py WindowState per image, plus the output filename per theme
│   ├── capture_dialog.py          # the other half of the gallery: dialogs, which are top-level X windows of their own and so out of capture_screenshots.py's reach. Shots live in a DIALOG_SHOTS dict rather than a JSON spec (a dialog is built from typed Python arguments); same theme/language/import rules (see "Screenshot capture")
│   ├── demo_driver.py             # drive and record the docs/DEMO_SCRIPTS.md movies from tools/demo_specs.json: the same WindowState start state as a screenshot spec, then steps driven with real X input (xdotool) on a nested display of the take's own, recorded with ffmpeg (see "Demo recording")
│   ├── demo_specs.json            # the movies' scene list: a start state per scene, plus the steps, narration and dwell times that drive it
│   ├── generate_foam_keywords.py  # CLI wrapper around app_config/keyword_generator.py; --dir picks an installation root (default: sourced environment)
│   └── roundtrip_corpus.py        # parse+write every dictionary of an installation's tutorials and count the byte-identical ones; the measurement behind the release-note round-trip figure
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
│   ├── foam_env.py          # foam_env_dirs(env) → FoamEnvDirs: single source of truth for reading $WM_PROJECT_DIR/$FOAM_TUTORIALS/$FOAM_ETC/$FOAM_SRC/$FOAM_APP (fields None unless the dir exists; project-dir fallbacks); pure stdlib, no services/ dependency, so it lives here rather than in services/ despite being consumed by services/example_search.py too; shared by example_search, keyword_generator, and AppConfigManager.foam_tutorials_dir
│   └── keyword_generator.py  # scans an OpenFOAM installation (etc/caseDicts templates; TypeName/ClassName + addNamedTo* macros and dictionary-read calls — lookup("…"), get<…>("…"), readEntry("…"), … — in src/ and applications/ sources) to build foam_keywords.json (user-generated, gitignored; overrides the tracked foam_keywords.default.json baseline). Installation root via generate(project_dir=…) or the sourced environment (read through foam_env.foam_env_dirs); the output is written atomically via json_io.atomic_write_text; payload carries provenance metadata (source, version, generated, note — identifier names only, no OpenFOAM source code). Shared by tools/generate_foam_keywords.py and the Settings menu action
├── foam/
│   ├── block_mesh_extractor.py  # extracts vertices/blocks/boundary from blockMeshDict FoamNode tree; _HEX_FACE_VERTICES + _expand_compact_faces convert compact (blockIdx, faceIdx) boundary entries to 4-vertex lists; _compute_default_faces collects exterior block faces unclaimed by any patch (blockMesh's implicit defaultFaces — what quasi-2-D cases leave unlisted) into BlockMeshData.default_faces; parse_vertices() is public; delegates variable resolution to var_resolver
│   ├── var_resolver.py          # shared variable resolution: build_var_map(root, skip_keys) iteratively resolves $vars (including negated-macro word nodes like -$xMax) and #eval{} chains of arbitrary depth; substitute_vars() and eval_foam_expr() are public helpers used by both extractors
│   ├── shapes.py                # SourceShape: the label/kind/geometry base dataclass shared by every extractor shape class (TopoShape, SnappyShape, SetFieldsShape, SamplingShape) — display name + geometry/source keyword + parsed geometry dict; each subclass adds only its own extra fields (action, category/level/mode, source_file). This is what the BlockMesh panel/renderer and Export-STL code consume
│   ├── topo_set_extractor.py    # extracts renderable geometry (box incl. min/max and multi-box `boxes` forms, rotated box, sphere incl. origin alias + innerRadius, cylinder, cone, point sets: nearestTo*/insidePoints/nearPoint, planeToFaceZone plane) from topoSetDict action_entry nodes; resolves $var and #eval inside raw_list / macro geometry values via var_resolver; returns TopoSetData(shapes=[TopoShape(...)]), TopoShape subclassing shapes.SourceShape. The per-source geometry dispatch is exposed as resolve_source_geometry() / is_non_geometric_source(), shared with set_fields_extractor.py
│   ├── set_fields_extractor.py  # extracts renderable region geometry from setFieldsDict's regions ( … ) list (region_block → region_entry nodes; the entry NAME is the source type — boxToCell, sphereToCell, … — there is no `source` child); reuses topo_set_extractor.resolve_source_geometry(); labels each shape with a fieldValues summary (e.g. "alpha.water=1"); returns SetFieldsData(shapes=[SetFieldsShape(...)]), SetFieldsShape subclassing shapes.SourceShape with no extra fields
│   ├── sampling_extractor.py    # extracts renderable sampling geometry — probes probeLocations (point markers), sets-type sample lines (start/end), surfaces-type plane/cuttingPlane discs — from controlDict's functions {} block or a standalone sampling dict (system/sample, probes, surfaces, singleGraph incl. the .org root-level start/end style); both nested member-list syntaxes are structural parser nodes: the dictionary form sets {}/surfaces {} and the classic parenthesised list form sets ( name {…} ) as a named_dict_list; reuses tree_utils.resolve_plane_geometry; returns SamplingData(shapes=[SamplingShape(...)]), SamplingShape subclassing shapes.SourceShape (extra field: source_file)
│   ├── snappy_hex_mesh_extractor.py  # extracts geometry {} primitives (box, sphere incl. ellipsoid via vector radius, cylinder, cone, triSurfaceMesh/distributedTriSurfaceMesh resolved against constant/triSurface/ incl. transparent .gz sibling resolution, and box-based collection members) from snappyHexMeshDict; cross-references castellatedMeshControls.refinementSurfaces/refinementRegions (incl. regex-pattern surface names) to classify each shape surface/region/geometry; extracts locationInMesh/locationsInMesh; returns SnappyHexMeshData(shapes=[SnappyShape(...)]), SnappyShape subclassing shapes.SourceShape (extra fields: category/level/mode)
│   ├── include_resolver.py      # Qt-free, stdlib-only: parse_include_directive() turns a directive_entry's raw text into an IncludeRef (#include/#sinclude/#includeIfPresent/#includeEtc/#includeFunc), rejecting C++ headers pulled in by a #codeStream body; resolve_include() resolves it to a ResolvedInclude, expanding $VARs and a leading <case>/<system>/<constant>/<etc> token. Takes etc_dirs as a parameter so foam/ keeps its no-dependency rule
│   ├── tree_utils.py            # generic FoamNode helpers shared by the topo_set / snappy_hex_mesh / set_fields extractors: find_child, find_child_any, resolve_scalar, resolve_vector, resolve_point_list, expand_evals, and the shared box/sphere/cylinder/cone geometry resolvers (resolve_box_geometry covers the min/max, `box (min) (max)` pair, and multi-box `boxes` forms behind opt-in flags)
│   ├── diff.py                  # diff_trees(a, b) and diff_trees_reverse(b, a) — compare two FoamNode trees by key name; return dict[FoamNode, DiffEntry]
│   ├── boundary_patch.py        # Qt-free FoamNode operations for boundary patches: value_complexity/get_patch_type/patch_inner_text/parse_patch_content (patch content read/parse for the edit dialog) and find_rename_targets (scans a set of parsed roots for boundary_entry / boundaryField-dict nodes matching a name). Moved out of ui/dialogs/boundary_edit_dialog.py and ui/dialogs/rename_boundary_dialog.py — they were Qt-free logic living in QDialog modules, imported across packages as underscore-privates; shared by ui/panels/boundary_view_panel.py and ui/mixins/_boundary_ops.py too
│   ├── lexer.py                 # OpenFoamLexer; _read_directive stops at '{' so #eval{...} braces become LBRACE/RBRACE tokens for correct depth tracking
│   ├── nodes.py
│   ├── parser.py
│   ├── utils.py
│   ├── value_parse.py           # Qt-free text -> typed-value validation backing FoamTreeModel.setData: parse_text_for_node_type(node_type, text) re-parses a string against a node_type (int promoting to scalar on a float-looking string, vector/int_list/scalar_list via parse_parenthesized_numbers, box_pair via foam/utils.parse_box_pair, bool word matching, string types passing through); set_node_value(node, value) is the full contract — mutates node.value/node_type/modified in place and returns whether the edit was accepted, which model/tree_model.py's setData uses verbatim to decide dataChanged vs. edit_rejected
│   └── writer.py
├── model/
│   ├── boundary_model.py   # BoundaryModel (QAbstractTableModel) + extract_boundary()
│   ├── file_list_model.py  # FileListModel (QAbstractListModel)
│   └── tree_model.py       # FoamTreeModel(QAbstractItemModel); setData's Value-column validation is delegated to foam/value_parse.set_node_value, keeping node_type/text parsing Qt-free
├── schemas/
│   ├── __init__.py
│   ├── _base.py
│   ├── builtin.py
│   ├── config_store.py
│   ├── block_mesh_dict.py
│   ├── control_dict.py
│   ├── fv_schemes.py
│   ├── fv_solution.py
│   ├── _turbulence_coeffs.py    # generated, vendored from foamlore: the coefficient facts for all 29 models + build_schemas(target_file)
│   ├── momentum_transport.py    # generated, vendored from foamlore: thin, TARGET_FILE = constant/momentumTransport (Foundation v8-v14)
│   ├── snappy_hex_mesh_dict/    # package: split by subdomain (geometry, castellated mesh, snap, layers, mesh quality)
│   │   ├── __init__.py          # merges submodule SCHEMAS dicts, re-exports TARGET_FILE
│   │   ├── _common.py           # shared SWITCH_CHOICES
│   │   ├── _structure.py        # the four control dictionaries and the sub-dicts inside them
│   │   ├── _geometry.py
│   │   ├── _castellated_mesh.py
│   │   ├── _snap_controls.py
│   │   ├── _add_layers.py
│   │   └── _mesh_quality.py
│   ├── turbulence_properties.py # generated, vendored from foamlore: thin, TARGET_FILE = constant/turbulenceProperties (OpenCFD v2106-v2606, Foundation v7)
│   ├── turbulence_structure.py  # hand-written: simulationType, RAS/LES, model selectors, LES deltas — TARGET_FILES covers both filenames
│   └── registry.py
├── services/
│   ├── case_copier.py
│   ├── foam_monitor.py      # patched_foam_monitor(): copies the installed foamMonitor script to a chmod-755 tempfile with the gnuplot reread-deprecation fix applied (foamMonitor_gnuplot_reread_fix.patch at the repo root); ui/mixins/_foam_monitor_ops.py launches that tempfile
│   ├── backup_files.py      # find_backup_files(case_dir): [(abs_path, rel_path, size_bytes)] for every <name>.bak_YYYYMMDD_HHMMSS file under a case; ui/dialogs/clean_backups_dialog.py's delete-checklist, invoked from ui/mixins/_file_mgmt_ops.py
│   ├── case_files_config.py
│   ├── case_loader.py       # also detect_poly_mesh() -- PolyMeshInfo(n_points, n_cells, n_faces, stale) from constant/polyMesh/owner's FoamFile note field
│   ├── include_scan.py      # the disk half of include support: foam_etc_dirs() builds the OpenFOAM etc search path, scan_includes()/included_files() run foam/include_resolver over a case's already-listed files (a cheap regex line scan, memoised on mtime+size, one level deep and not transitive), copy_destination_for() picks where "Copy into case" puts an out-of-case include
│   ├── example_search.py    # discover_installations()/search_examples(): find OpenFOAM installs (app_config/foam_env env reading → well-known paths) and scan their tutorials/ + etc/caseDicts/ for a keyword, returning SearchHits (matched lines, enclosing tutorial case root)
│   ├── log_summary/         # package: parse_log()/format_summary() condense blockMesh/snappyHexMesh/topoSet and solver run logs (log.* stdout, not FoamNode dict trees; solvers detected by time-loop shape, not name) into a short LogSummary report
│   │   ├── __init__.py          # re-exports LogSummary/LogWarning/PhaseSummary; parse_log() dispatches on utility name/shape, format_summary() renders the report
│   │   ├── _types.py            # LogSummary/LogWarning/PhaseSummary dataclasses + generic header and FOAM Warning/FATAL ERROR parsing shared by every grammar
│   │   ├── _block_mesh.py       # blockMesh grammar: Mesh Information block
│   │   ├── _snappy_hex_mesh.py  # snappyHexMesh grammar: castellation/snapping/layer-addition phases, split on "Wrote mesh in" markers
│   │   ├── _topo_set.py         # topoSet grammar: per-set source/size collapsing
│   │   ├── _solver.py           # solver grammar: time-loop steps, residuals, Courant number, timing
│   │   └── _generic.py          # fallback grammar: tail of an unrecognised log
│   └── tool_options.py      # ToolSpec/ToolOption specs (TOOL_SPECS) + build_args()/build_command() for the Tools-menu "Run *" options dialogs; always tees to log.<tool>
├── i18n/
│   ├── __init__.py             # tr(), set_language(), get_language(), available_languages()
│   └── ja.py                   # Japanese translations (LANGUAGE_NAME + TRANSLATIONS dict)
├── ui/
│   ├── app_state.py            # AppState dataclass: all 16 shared mutable fields (diff is a nested DiffState, undo a nested UndoState holding the global UndoSnapshot undo/redo stacks); MainWindow sets self.state = AppState()
│   ├── theme.py               # Theme mode (system/light/dark), the readable_selection_pair() contrast rule that repairs Qt's desktop-inherited Highlight/HighlightedText pair, and the ThemeColors table every semantic UI colour resolves through via colors()
│   ├── pane_minimize.py       # PaneMinimizer: one-click collapse/restore of one QSplitter pane, plus the handle double-click filter. Two styles: `sizes` (collapse to 0 — file list, Detail pane) and `strip` (pin the widget's maximum, leaving a sliver — the Editor/Terminal row, whose splitter sets setCollapsible(False), under which setSizes clamps to QTabWidget's minimumSizeHint instead of collapsing; the sliver is its tab bar, so the tabs and the sync buttons stay reachable). The whole size row is remembered so a collapse/restore cycle does not lose a pixel per cycle; a size set from outside (a restored session) drops it
│   ├── window_state.py         # WindowState/BlockMeshViewState dataclasses plus capture_window_state()/apply_window_state(): the parts of the layout that are a choice rather than a consequence (geometry, splitters, tabs, open file, tree selection, 3-D toggles and camera, plus `minimized_panes` — which panes are minimized and the size each should come back to, the half a splitter blob cannot carry), JSON-serialisable so a state survives between processes; the strict/lenient split (from_dict + apply_window_state's `strict` flag, load_saved_state) exists because its two consumers disagree: a screenshot spec must fail loudly, a restored session must degrade quietly
│   ├── session_restore.py      # the between-runs wire over window_state.py: save_session() from MainWindow.closeEvent (before the panels are torn down, no auto-save), restore_session() from main.py after show(); layouts stored per feature set via AppConfigManager.session_key(), the 3-D camera re-applied on a timer because the case-load renders end in reset_camera(), skipped parts reported in the status bar
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
│   │   ├── _ui_ops.py              # mixin: label updates, schema manager, help dialogs, language menu, tree column toggles
│   │   └── _protocol.py            # mypy-only MainWindowProtocol every mixin's TYPE_CHECKING base points at, so `self.tree`/`self.state`/cross-mixin calls type-check; see "Typing the ui/mixins/ split" below
│   ├── layout_constants.py
│   ├── main_window.py          # core: __init__, _build_ui and sub-builders, drag-and-drop (dragEnterEvent/dropEvent/eventFilter)
│   ├── dialogs/
│   │   ├── about_dialog.py
│   │   ├── add_files_dialog.py
│   │   ├── boundary_edit_dialog.py
│   │   ├── _case_dest_dialog.py  # _CaseDestDialogBase(QDialog): shared source/destination(parent+name)/preview/copy-mode UI for DuplicateCaseDialog and SaveAsNewCaseDialog; subclasses build their own copy-mode radio group and call _finish_layout
│   │   ├── case_library_dialog.py
│   │   ├── clean_backups_dialog.py
│   │   ├── duplicate_case_dialog.py  # DuplicateCaseDialog(_CaseDestDialogBase): "_copy" name suffix, "Copy all files" checked by default
│   │   ├── export_stl_dialog.py  # ExportStlDialog: modal checklist of loaded topoSetDict/snappyHexMeshDict shapes; writes each checked one to its own .stl via shape_mesh.make_shape_mesh
│   │   ├── find_examples_dialog.py  # FindExamplesDialog: non-modal keyword search over an installation's tutorials/ + etc/caseDicts/ (services/example_search.py in a background QThread, _SearchThread(_worker_thread._CancellableWorkerThread)), syntax-highlighted preview, Copy, "Compare with this case" (emits compare_requested), and "Duplicate this case…" (emits duplicate_requested); installation picker is the shared widgets/installation_selector.InstallationSelector
│   │   ├── foam_monitor_dialog.py  # FoamMonitorDialog: file picker + foamMonitor option controls (log scale, grid, refresh, idle, extra flags)
│   │   ├── generate_keywords_dialog.py  # GenerateKeywordsDialog: runs app_config/keyword_generator.py in a background QThread with progress log (_GeneratorThread(_worker_thread._CancellableWorkerThread)); installation picker is the shared widgets/installation_selector.InstallationSelector (same discovery + persisted openfoam_dir key as FindExamplesDialog)
│   │   ├── keyboard_shortcuts_dialog.py
│   │   ├── log_summary_dialog.py  # LogSummaryDialog: non-modal (like find_examples_dialog, unlike the other dialogs here) file picker + Summary/Raw Log tabs over services/log_summary/
│   │   ├── manage_extra_files_dialog.py
│   │   ├── openfoam_resources_dialog.py
│   │   ├── rename_boundary_dialog.py  # Rename Boundary dialog + find_rename_targets() scanner
│   │   ├── reset_settings_dialog.py
│   │   ├── run_tool_dialog.py  # RunToolDialog: generic Tools-menu "Run *" options dialog built from services/tool_options.TOOL_SPECS — curated flag widgets, free-text extra options, live command preview, optional pre-flight warning and shell-prefix checkbox
│   │   ├── save_as_new_case_dialog.py  # SaveAsNewCaseDialog(_CaseDestDialogBase): "_new" name suffix, "Copy app-visible files only" checked by default, extra italic note about unsaved edits
│   │   ├── schema_manager_dialog.py
│   │   └── _worker_thread.py  # _CancellableWorkerThread(QThread): shared progress/finished_err signals + cancel() flag for _SearchThread (find_examples_dialog) and _GeneratorThread (generate_keywords_dialog); each subclass adds its own finished_ok signal and run()
│   ├── panels/
│   │   ├── block_mesh_panel.py     # 3-D viewer for blockMeshDict (pyVista/VTK, lazy init); also overlays topoSetDict (topoSet ▾ menu), snappyHexMeshDict (snappyHexMesh ▾ menu), setFieldsDict regions (setFields ▾ menu), and sampling definitions (sample ▾ menu; union of controlDict functions {} plus standalone system/sample-style dicts, kept per source basename in _sampling_by_file) geometry, each with per-shape visibility toggles, Show all/Hide all actions, and a "Non-geometric sources (N)" submenu for entries with no drawable geometry; delegates actor setup to block_mesh_renderer.BlockMeshRenderer; STL ▾ menu holds the same per-file rows for loaded STL/OBJ surfaces (block_mesh_renderer.LoadedSurface, one palette colour each, with an Unload submenu) plus "Export Shapes as STL…", which opens dialogs/export_stl_dialog.ExportStlDialog
│   │   ├── block_mesh_renderer.py  # BlockMeshRenderer: VTK render pipeline for blockMeshDict/topoSetDict/snappyHexMeshDict/setFieldsDict geometry via RenderSettings dataclass; colour tables (_PATCH_COLORS, _ACTION_COLORS, _SNAPPY_CATEGORY_COLORS, _SET_FIELDS_REGION_COLOR, _SURFACE_COLORS) and _opacity() (theme-scaled alpha) stay here — they depend on ui.theme; per-shape render methods call shape_mesh.make_shape_mesh()/_clip_to_bounds()/_mark_label() for the Qt-free geometry/clipping/labelling half; _render_boundary_faces also draws BlockMeshData.default_faces in fainter "empty" grey; only imported after the pyvista guard passes
│   │   ├── boundary_view_panel.py
│   │   ├── comparison_tree_panel.py  # read-only reference-case tree; emits use_value_requested(FoamNode)
│   │   ├── detail_panel.py
│   │   ├── editor_panel.py
│   │   ├── file_list_panel.py
│   │   ├── shape_mesh.py           # Qt-free geometry construction split out of block_mesh_renderer.py (no Qt import, no self): make_shape_mesh() dispatches on geometry dict keys (box, boxes, centre+radius incl. list-radius ellipsoid and hollow innerRadius, p1+p2+radius, origin+i+j+k, stl_path, planePoint+planeNormal disc sized via plane_size; points returns None — drawn as markers instead) shared by all overlay sources and by dialogs/export_stl_dialog.py; overlay shapes are clipped (display-only) to the block-mesh AABB expanded 10%/axis via _clip_to_bounds — labels gain "(clipped)" / "(outside block mesh)" marks via _mark_label (ASCII: VTK's label font draws no glyph at all for a pictograph), an enclosing shape falls back to its AABB overlap box; read_surface_mesh() transparently decompresses a gzipped .stl/.obj; imports pyvista unconditionally, same as block_mesh_renderer.py — only pyvistaqt is guarded
│   │   └── terminal_panel.py       # TerminalPanel wrapper: mode_changed signal, xterm/simple toggle logic
│   └── widgets/
│       ├── code_editor.py
│       ├── _checkable_list.py          # checked_items()/set_all_check_states(): shared Select All/Deselect All + "N selected" helpers for the checkable-QListWidget pattern used by clean_backups_dialog.py and manage_extra_files_dialog.py
│       ├── flow_layout.py              # FlowLayout(QLayout): wrapping toolbar layout — min width is the widest single item; used by the BlockMesh panel toolbar
│       ├── installation_selector.py    # InstallationSelector(QWidget): combo + Browse… row over services/example_search.discover_installations() and the persisted openfoam_dir key; installations_available/error signals; shared by find_examples_dialog and generate_keywords_dialog
│       ├── _foam_highlighter.py        # FoamHighlighter(QSyntaxHighlighter): OpenFOAM token colouring; loads app_config/foam_keywords.json (user-generated) or, when absent, app_config/foam_keywords.default.json (shipped baseline) in 1,000-keyword QRegularExpression chunks; the number rule (_NUMBER_RE) and all keyword rules are lookaround-guarded so digits glued to identifiers ("wall0") and keyword prefixes of dotted names ("y0" in "y0.1") are not partially coloured
│       ├── _simple_terminal_widget.py  # SimpleTerminalWidget: QProcess-based terminal (no WebEngine)
│       └── _xterm_widget.py            # PtyBackend, TerminalBridge, XtermTerminalWidget (Unix + QtWebEngine only); exports _XTERM_AVAILABLE
└── tests/
    ├── conftest.py
    ├── test_lint.py             # runs ruff (whole-repo) + mypy (source packages, see "Linting and type-checking") as part of the pytest suite
    ├── test_version.py          # _version.get_version(): git-describe formatting (exact tag, ahead-of-tag, dirty, bare hash, no-git fallback)
    ├── test_i18n.py             # i18n/ja.py's TRANSLATIONS has no duplicate keys; every tr() call under ui/ has a ja.py entry or is in a measured _UNTRANSLATED allowlist (both AST walks)
    ├── foam/
    │   ├── test_block_mesh_extractor.py
    │   ├── test_boundary_patch.py
    │   ├── test_diff.py
    │   ├── test_lexer.py
    │   ├── test_parser_block_mesh_dict.py
    │   ├── test_parser_control_dict.py
    │   ├── test_parser_fv_schemes.py
    │   ├── test_parser_fv_solution.py
    │   ├── test_parser_block_list.py
    │   ├── test_parser_named_dict_list.py
    │   ├── test_parser_region_properties.py
    │   ├── test_parser_set_fields_dict.py
    │   ├── test_parser_topo_set_dict.py
    │   ├── test_include_resolver.py
    │   ├── test_sampling_extractor.py
    │   ├── test_set_fields_extractor.py
    │   ├── test_snappy_hex_mesh_extractor.py
    │   ├── test_sampling_shapes_tutorial.py
    │   ├── test_source_lines.py
    │   ├── test_topo_set_extractor.py
    │   ├── test_topo_set_shapes_tutorial.py
    │   ├── test_tree_utils.py
    │   ├── test_utils.py
    │   ├── test_value_parse.py
    │   ├── test_var_resolver.py
    │   └── test_writer_roundtrip.py
    ├── model/
    │   ├── test_bool_nonuniform.py
    │   ├── test_boundary_model.py
    │   ├── test_file_list_model.py
    │   └── test_tree_model.py
    ├── ui/
    │   ├── test_action_toolbar.py
    │   ├── test_app_state.py
    │   ├── test_apply_comparison_value.py
    │   ├── test_block_mesh_panel_fonts.py
    │   ├── test_block_mesh_panel_load_stl.py
    │   ├── test_block_mesh_panel_sampling_select.py
    │   ├── test_block_mesh_panel_set_fields_select.py
    │   ├── test_block_mesh_panel_snappy_select.py
    │   ├── test_block_mesh_panel_topo_select.py
    │   ├── test_block_mesh_renderer_colors.py
    │   ├── test_block_mesh_selected_block.py
    │   ├── test_bm_side_by_side_multi_dict.py
    │   ├── test_boundary_view_copy.py
    │   ├── test_case_switch_clears_block_mesh_panel.py
    │   ├── test_code_editor.py
    │   ├── test_code_editor_zoom.py
    │   ├── test_comparison_tree_panel.py
    │   ├── test_detail_panel_fit.py
    │   ├── test_dialog_fonts.py
    │   ├── test_dialog_label_fit.py
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
    │   ├── test_fonts.py
    │   ├── test_icons.py
    │   ├── test_included_files.py
    │   ├── test_keyboard_shortcuts_dialog.py
    │   ├── test_log_summary_dialog.py
    │   ├── test_main_window_save_refresh.py
    │   ├── test_main_window_split.py
    │   ├── test_manage_extra_files_dialog.py
    │   ├── test_pane_minimize.py
    │   ├── test_reset_all_settings.py
    │   ├── test_run_tool_dialog.py
    │   ├── test_shape_mesh.py
    │   ├── test_stays_open_menu.py
    │   ├── test_terminal_panel.py
    │   ├── test_theme.py
    │   ├── test_tools_ops_mesh_actions.py
    │   ├── test_translatable_strings.py
    │   ├── test_tree_block_crud.py
    │   ├── test_tree_color_lexer_dispatch.py
    │   ├── test_tree_copy_paste.py
    │   ├── test_tree_inline_edit_dirty.py
    │   ├── test_tree_undo_redo.py
    │   ├── test_tree_text_sync_bar.py
    │   ├── test_update_viewer_panels.py
    │   ├── test_view_log_summary_action.py
    │   ├── test_session_restore.py
    │   └── test_window_state.py
    ├── services/
    │   ├── test_backup.py
    │   ├── test_case_copier.py
    │   ├── test_case_files_config.py
    │   ├── test_include_scan.py
    │   ├── test_case_loader.py
    │   ├── test_example_search.py
    │   ├── test_log_summary.py
    │   └── test_tool_options.py
    ├── app_config/
    │   ├── test_app_config.py
    │   ├── test_foam_env.py
    │   ├── test_json_io.py
    │   └── test_keyword_generator.py
    ├── schemas/
    │   ├── test_schemas.py
    │   └── test_turbulence_schemas.py
    └── tools/
        ├── test_capture_dialog.py
        └── test_demo_specs.py
```

### Documentation map

| File | Role |
|---|---|
| `README.md` | Short introduction: installation, quick-start workflow, and a condensed feature overview whose group headings deep-link into the user guide. |
| `USER_GUIDE.md` | Full feature reference. **When adding a user-visible feature, also add it to the "Where to Find Things" table and the Contents list** — these navigation aids drift silently otherwise. |
| `DEVELOPER.md` | This file: project structure, internals, dev setup, and testing. |
| `RELEASE_NOTES.md` | User-facing change log; new entries accumulate under `## Unreleased` and the heading is renamed to a version number on release. |
| `docs/SCREENSHOTS.md` | Annotated screenshot gallery of the main window, BlockMesh 3-D overlays, and key dialogs/menus. |
| `docs/DEMO_SCRIPTS.md` | Shot-by-shot scripts for the demo movies, and how to record them. Each is a runnable scene in `tools/demo_specs.json`, so a script and the take it produces cannot drift apart. |
| `docs/OPENFOAM_VERSIONS.md` | User-facing: the dictionary-file renames between OpenFOAM releases and between the forks, measured from the tutorial trees. The source of the both-spellings rule in `services/case_loader.py`. |
| `docs/SCHEMA_CANDIDATES.md` | Which dictionary to write a schema for next, ranked by measured frequency and key count, and whether each should be hand-written here or generated by foamlore. |

Every English document has a Japanese counterpart (`*_ja.md`); any edit to one must be mirrored in the other. Japanese docs keep menu labels and other UI strings in English.

### Test coverage notes

One line per test file, grouped by directory. Keep this in sync when adding or removing a test file — it's the thing that drifted silently before.

**`tests/foam/`**
- `test_block_mesh_extractor.py` — `extract_block_mesh_data` output: boundary face extraction (including the regression where a `#include` among the patches cost `outlet` its name and faces), hex extraction from a `blocks` list holding an `#include` and from a list the lookahead rejects into `raw_list`, `default_faces` (fully-claimed boundary → empty, unassigned exterior faces collected, claim matching in any vertex rotation, shared inter-block faces excluded); `parse_vertices` public API (well-formed and non-triplet-tolerant); vertices/blocks extraction with inline comments and patch comments; variable resolution (`$varName`, `${varName}`, macros, negated-macro word nodes like `-$xMax`, `#eval{ expr }`, multi-level chains); compact `(blockIndex, faceIndex)` boundary face notation, including combined with negated-macro vertex variables.
- `test_boundary_patch.py` — `find_rename_targets()`: detection of `boundary_entry` nodes in `blockMeshDict`, `dictionary` patch nodes in `boundaryField` blocks, absence of false positives for unrelated dictionaries, empty-input edge cases.
- `test_diff.py` — `diff_trees`/`diff_trees_reverse`: identical trees, changed values, keys only in one tree, nested dictionaries, anonymous node skipping, `field_value_block` entries, symmetry between the two functions.
- `test_lexer.py` — `foam.lexer.OpenFoamLexer`'s `//` handling: a double-slash inside a quoted string is not a comment, one after whitespace starts `LINE_COMMENT` without swallowing the preceding word, and a standalone `//` line is a comment from its first token. Also `${…}` braced macro references: the whole reference is one WORD (with a scope path, and with nested braces balanced), the tokens after it are unaffected, a plain `$macro` and a lone `{` are unchanged, an unterminated `${` runs to end of text instead of looping, and `#eval{…}` still splits into DIRECTIVE + LBRACE + body + RBRACE, which its own parsing depends on.
- `test_parser_block_mesh_dict.py` — `boundary_block`/`boundary_entry` structured parsing (patch count/names/types/faces), round-trip writing; inline `//` and `/* */` comments between a patch name and its brace and inside `vertices` not corrupting node types; a `#include` standing among the patches becoming a `directive_entry` child instead of failing the whole block (no parse errors, patch names intact, byte-identical round-trip); `_read_parenthesized_text` skipping inline comments inside an embedded parenthesised value.
- `test_parser_control_dict.py` — `controlDict` parsing: FoamFile header, int/scalar/word values, `#directives`, `functions` sub-dicts, and parser-failure fallback to an empty root.
- `test_parser_fv_schemes.py` — `fvSchemes` parsing: compound values, `ddtSchemes`/`divSchemes`/`interpolationSchemes`/`snGradSchemes` blocks, presence of all top-level blocks, round-trip writing, and a stray `;` closing a dictionary (`divSchemes { … };`) becoming its own node without being counted as a parse error.
- `test_parser_fv_solution.py` — `fvSolution` parsing: macro and regex-pattern solver keys, the `PIMPLE` block, solver `tolerance`/`smoother` entries, round-trip writing.
- `test_parser_block_list.py` — `blockMeshDict`'s `blocks ( … );` explosion: a pure `hex` list parses to `block_list`/`block_entry` with anonymous, one-line entries; the lookahead keeps an empty list, a plain macro word list, a directive-only list, and a non-`hex` leading shape (`hex2D`, `prism`) on the ordinary `raw_list` path; an `#include` *beside* hex blocks instead explodes with a `directive_entry` child — leading or in the middle of the list — and still round-trips byte-identically; variant forms parse as one entry each (zone name with `grading`, bare `$blockInfo` tail, 12-value `edgeGrading`, a block split over three lines, and blockMesh's `name <blockName> hex …` prefix — with a bare `name` word *not* splitting an entry); comment placement (inline vs. next entry's `leading_trivia`); unmodified round-trip is byte-identical and a modified entry leaves its siblings verbatim.
- `test_parser_named_dict_list.py` — the optional named-dict-list syntax: `sets`/`surfaces` parenthesised lists of named dicts parse to `named_dict_list`/`named_dict_entry` (top-level and nested in a function-object dict), the lookahead keeps plain word/string lists (`sets (setA setB);`) and empty lists on the ordinary value path, unmodified round-trip is byte-identical, and a modified entry's siblings keep their names.
- `test_parser_region_properties.py` — the `regions` key, which two unrelated dictionaries both claim: `setFieldsDict`'s named dicts still parse to `region_block`/`region_entry`, while `constant/regionProperties`'s list of name/word-list pairs falls through to `raw_list` instead of the two nameless `unknown_raw_entry` nodes it used to produce, with no parse errors and a byte-identical round trip both ways. Both bundled tutorial files are checked directly, a plain `regions ( a b c );` and an empty list are covered, and one test pins the rule the fix restores by asserting the entry parses identically to the same content under a different key.
- `test_parser_set_fields_dict.py` — `setFieldsDict` parsing: `defaultFieldValues`/`regions` field-value entries (including vector values), `box_pair` parsing, round-trip writing after an edit.
- `test_parser_topo_set_dict.py` — `action_list`/`action_entry` structured parsing: node type, entry count, named child values, `box_pair` coordinates, source-less entries, round-trip writing, positional diff detection via `_diff_action_list`.
- `test_snappy_hex_mesh_extractor.py` — `extract_snappy_hex_mesh_data`: `geometry` box/sphere (scalar and vector/ellipsoid radius)/cylinder/cone extraction; `name` override resolution (`geom.stl { name geom; }`); `triSurfaceMesh`/`distributedTriSurfaceMesh` file resolution against `constant/triSurface/` (explicit `file` child, implicit filename-as-key, missing file), including transparent `.gz` resolution (a plain-name entry resolving to a `.gz`-only file on disk, a `.gz`-suffixed entry key/file resolving directly, and a `.gz`-suffixed reference falling back to an uncompressed file on disk); `collection` (searchableSurfaceCollection) box members via `rotation none` and `e1`/`e3` axes (including a case that actually rotates), skipped for a non-box base or a missing/unsupported transform; `refinementSurfaces`/`refinementRegions` cross-referencing by exact name and by regex-pattern key (e.g. `"iglo.*"`); `locationInMesh` (singular) and `locationsInMesh` (plural) point extraction; `$var`/`#eval{}` resolution.
- `test_source_lines.py` — `source_line`/`source_end_line` population for all node types.
- `test_topo_set_extractor.py` — `extract_topo_set_data`: plain typed values for all three geometry types (box, sphere, cylinder), `$var` resolution in vectors and scalars, `#eval{...}` inside `raw_list`, chained var/eval resolution, unresolvable-variable skipping, all face/point source variants.
- `test_include_resolver.py` — `parse_include_directive`/`resolve_include`: the five directive kinds, optional (`#sinclude`/`#includeIfPresent`) marking, trailing `;`/comment/quote stripping, `#includeFunc mag(U)` reducing to the base name, C++-header rejection by suffix and by whole-token angle bracket (with `<constant>/…` deliberately surviving), `<case>`/`<system>`/`<constant>`/`<etc>` and `$VAR` expansion, including-file-dir-before-case-dir ordering, `.gz` siblings, per-root `#includeEtc` search order, `#includeFunc` preferring `system/`, and each of the four statuses.
- `test_sampling_extractor.py` — `extract_sampling_data`: probes in a `functions {}` block, dict-form `sets {}` line/cloud members and the parenthesised list form (in a functions {} block and at file root, sampleDict-style), `plane`/`cuttingPlane`/`patch` surface members, root-level `singleGraph`-style `start`/`end`, standalone `sample`/`probes` files, `$var` resolution, and non-sampling function objects being ignored.
- `test_set_fields_extractor.py` — `extract_set_fields_data`: box/sphere/cylinder region extraction (entry name as source type), the `fieldValues` label summary (scalar and vector values), non-geometric source classification (`zoneToCell`), `$var` resolution, and the unresolvable-geometric-source case.
- `test_topo_set_shapes_tutorial.py` — `extract_topo_set_data` against the bundled `tutorials/topoSetShapes` case: every geometry source is extracted and all shapes lie within the domain.
- `test_sampling_shapes_tutorial.py` — the same for `tutorials/samplingShapes` and `extract_sampling_data`: probes read out of a `controlDict` `functions {}` block with a non-sampling function object beside them ignored entirely, both member-list syntaxes (`sets { … }` and `surfaces ( … );`), a cloud carrying points rather than a span, both plane spellings, a `patch` surface listed as non-geometric, and every named point inside the domain. Plus the one thing a coverage check would miss: each shape's badge is projected through the gallery camera and asserted to stay clear of the others, because a shape moved in the case can hide another's badge behind it — two of the six were invisible while the case was being built.
- `test_tree_utils.py` — direct `tree_utils` resolver contracts (the extractor tests only exercise them indirectly): `find_child`/`find_child_any` alias precedence, `expand_evals`, `resolve_scalar` (scalar/int/macro/`${…}`/`#eval`), `resolve_vector` arity/numeric guards, `resolve_point_list`, the sphere/cylinder/cone resolvers with their opt-in flags, and `resolve_box_geometry` (min/max vs `box` pair vs multi-`boxes` precedence and flag gating).
- `test_utils.py` — `is_large_non_foam_file`: small files never flagged regardless of header, large files with a `FoamFile` token in the first 512 bytes not flagged, large files without it flagged, missing files return `(False, 0)`, a header preceded by a comment is still detected.
- `test_value_parse.py` — `parse_parenthesized_numbers`/`parse_text_for_node_type`/`set_node_value` directly (no Qt): int accept/reject and its promotion to scalar on a float-looking string, scalar accept/reject, vector/int_list/scalar_list/box_pair accept/reject, raw_list paren-stripping, bool case-insensitive accept/reject, word/string/macro/compound pass-through, an unsupported node_type rejected, and `set_node_value`'s field_value/directive_entry/unknown_raw_entry special cases plus its in-place mutation contract (rejected edits leave the node completely unchanged).
- `test_var_resolver.py` — `build_var_map`, `substitute_vars`, `eval_foam_expr`: scalar/int seeding, macro chains, `#eval` expressions, negated-macro word nodes, unresolvable vars staying absent, `skip_keys` exclusion, dictionary node non-collection.
- `test_writer_roundtrip.py` — `write_root`/`write_node` broadly: unmodified nodes reproduced via `raw_text`, modified word/int/scalar/vector nodes regenerated, directive/unknown-raw/macro entries preserved, nested dictionaries, blank-line runs preserved verbatim, `field_value_block`/`region_block` round-tripping (including a field value edited inside a region), and the regression where regenerating one region entry dropped unmodified siblings' names (entry `raw_text` now starts at the name token). Also the byte-identical round-trip group over `_CORPUS_SHAPED_DICT`, a fixture shaped like a real tutorial `blockMeshDict`: the `// * * *` banner keeps its following blank line, multi-blank gaps between entries survive, the trailing `// ****` footer banner is re-emitted from `root.trailing_trivia`, a missing final newline is not invented, `x1 14; x2 6;` stays on one line, editing one entry changes only that entry's line, a node added without trivia still gets its own line, a stray `;` after a `}` stays on the brace's line rather than being broken onto its own (indented) one, and regenerating a nested node of any type reproduces its source indentation instead of doubling it (parametrized over dictionary/simple/directive/macro/region/action/field-value/deeply-nested), with a left-margin case pinning that the writer still supplies an indent when the trivia does not. A `macro_entry` group covers the two spellings that used to be parse failures: a braced `${../_bladeForces}` and a bare `$minX` with no `;` both become `macro_entry` nodes, a bare macro is not a parse error and does not swallow the trivia belonging to the entry after it, all five spellings round-trip byte-identical, `_macro_suffix` reproduces whichever terminator the source had when the node is regenerated (including alongside an inline comment), and a node the app builds with no `raw_text` still gets a `;`.

**`tests/model/`**
- `test_bool_nonuniform.py` — `bool`/`nonuniform_list` parsing and round-tripping, `FoamTreeModel` bool editing (case-insensitive, rejection signal), `nonuniform_list` display/non-editability, parser error collection for bad entries.
- `test_boundary_model.py` — `extract_boundary()` and `BoundaryModel`: loading, field updates, per-directory boundary sets, `_is_in_dir` multi-level matching, model clearing.
- `test_file_list_model.py` — `FileListModel`: loading, sorted groups, dirty-state and diff-state per item, extra-files handling, clearing.
- `test_tree_model.py` — `set_diff(reverse=True)`: remaps `"only_here"` to `"only_in_ref"`, leaves `"changed"` unchanged, returns the light-green `BackgroundRole` colour, includes `"only in reference case"` in the tooltip. `FoamNode` carries `__hash__ = object.__hash__` so instances can be used as dict keys in the diff map. Block numbering: `block N` keys step over a `directive_entry` row so the first block below an `#include` still reads `block 0`, and the per-list cache behind that is dropped on an insert.

**`tests/ui/`**
- `test_app_state.py` — `ui/app_state.py`'s `AppState` defaults: `diff` is a `DiffState`, the scalar fields start empty, the mutable fields are writable, and two instances do not share a `parsed_roots` — the mistake a plain class attribute would make.
- `test_apply_comparison_value.py` — `_apply_comparison_value` ("Use this value"): creating missing parent dictionaries when adopting a nested entry (e.g. `functions/forces1/rhoInf` into a case without `functions {}`), appending unnamed `#includeFunc` directives by content into an existing block without overwriting it, skipping an identical directive instead of duplicating it, the plain named-value overwrite path, and refusing when the enclosing key exists but is not a dictionary.
- `test_block_mesh_panel_fonts.py` — the panel's two secondary labels (the hint line and the `⚙ Variable-based` badge) sizing from the desktop font at 9, 11 and 16 pt. Both used to pin `font-size: 11px` in their stylesheet, which stayed 11 px however large the desktop font was set — see "Font sizes and display scaling" below.
- `test_block_mesh_panel_load_stl.py` — the `STL ▾` menu's loaded surfaces: multi-file selection in one `getOpenFileNames` invocation, an unreadable file leaving the readable ones loaded (one warning naming the failures), a cancelled dialog as a no-op; then the per-file rows — one row and one palette colour per file (first is `lightgray`), individual hide vs. unload, per-row checked state surviving an unload or a re-load of the same path (which refreshes in place rather than duplicating), and a surface loaded with no `blockMeshDict` reaching the renderer (via a stub renderer) including the clearing render when the last one is unloaded.
- `test_block_mesh_panel_sampling_select.py` — the `sample ▾` per-shape visibility menu: population from a controlDict `functions {}` block (rows tagged with the source basename), individual/master toggling, greyed-out non-geometric entries, the multi-file union (controlDict + system/sample) with per-file replacement on reload, two dicts sharing a basename in different directories staying separate (`_sampling_by_file` is keyed by full path, labelled by basename), and `clear()` resetting `_sampling_by_file`.
- `test_block_mesh_panel_set_fields_select.py` — the `setFields ▾` per-shape visibility menu: population from the bundled damBreak tutorial's `setFieldsDict` (rows labelled with the `fieldValues` summary), individual/master toggling, greyed-out non-geometric sources, inclusion in STL export, and clearing on reload.
- `test_block_mesh_panel_snappy_select.py` — the `snappyHexMesh ▾` per-shape visibility menu: population, individual/master toggling, the surface/region/geometry category-colour legend, greyed-out non-geometric sources, `locationInMesh`/`locationsInMesh` keep-point toggles.
- `test_block_mesh_panel_topo_select.py` — the `topoSet ▾` per-shape visibility menu: population, individual/master toggling, Show all/Hide all, the action-colour legend, the "Non-geometric sources (N)" submenu of greyed-out entries, and the exclusion of point/plane shapes from STL export.
- `test_shape_mesh.py` — `ui/panels/shape_mesh.py`'s Qt-free geometry: `make_shape_mesh` generation for cones (true and frustum), hollow annuli, `rotatedBoxToCell`, sphere (scalar radius and vector-radius ellipsoid), and `stl_path` mesh loading (present and missing file, plus a gzip-compressed `.stl.gz` file via `read_surface_mesh`); `read_surface_mesh` plain-file passthrough; the overlay clip helpers (`_expanded_bounds` per-axis padding incl. degenerate 2-D axes; `_clip_to_bounds` fits-inside/clipped/outside/enclosing-stand-in cases, and that a clip seals what it cuts — a box cut through both ends and a cylinder both come back with no open edges, a box's side faces stay whole quads rather than triangle pairs, and a plane declines the capped path and falls back); and the scene text VTK draws — `_mark_label`'s suffixing, and an AST walk asserting every non-docstring string literal in `shape_mesh.py` is ASCII, since that font drew the previous `✂`/`⚠` clip marks as nothing at all.
- `test_block_mesh_renderer_colors.py` — what stayed behind in `block_mesh_renderer.py` when its Qt-free geometry moved to `shape_mesh.py`: `_ACTION_COLORS`'s `subtract`/`delete` alias and `remove`'s deliberate absence, plus the same AST-walk ASCII check applied to `block_mesh_renderer.py` itself, since that font drew the Dimensions bounds readout's `→` as nothing at all.
- `test_translatable_strings.py` — an AST walk over `ui/**/*.py` (excluding `block_mesh_renderer.py`/`shape_mesh.py`, see "Internationalisation (i18n)" below) asserting every string literal reaching a fixed set of Qt display sinks (`QLabel`/`QPushButton`/.../`setText`/`setToolTip`/.../`QMessageBox.warning`/`QInputDialog.getText`, ...) goes through `tr()`; an f-string counts too, unless its non-interpolated text is empty once HTML tag syntax is stripped. `_LOCAL_SINKS` extends the same check into this codebase's own helpers (`_menu_button`, `_ShapeOverlayMenu`'s `master_label`/`legend_title`), and `_ALLOWED` exempts specific literals (camera-view axis symbols, topoSet/snappyHexMesh keywords the dict file itself uses) with a one-line reason each; a trailing `# i18n: skip` comment covers a one-off case `_ALLOWED` isn't worth growing for. Both `_LOCAL_SINKS` and `_ALLOWED` are asserted to still match real code under `ui/`, in both directions, so a renamed helper or a deleted call site cannot leave a stale, unverifiable exemption in place.
- `test_block_mesh_selected_block.py` — the tree → 3-D block highlight: no block highlighted initially, `set_selected_block` reaching `RenderSettings.selected_block`, clearing it, a new mesh dropping it; `_highlight_selected_block` forwarding a `block_entry` row index and clearing on any other row; and `_render_selected_block` drawing nothing for `None` or an out-of-range index (proved by passing a `None` plotter, which any `add_mesh` call would blow up on).
- `test_bm_side_by_side_multi_dict.py` — the `⊞` side-by-side corner button (`_update_bm_side_by_side_btn`): enabled for `blockMeshDict`, `topoSetDict`, `snappyHexMeshDict`, and `controlDict` (sampling overlay); disabled for an unrelated dict (e.g. `fvSchemes`). Also asserts the tree/BlockMesh splitter panes are non-collapsible and the panel keeps its 150-px minimum width.
- `test_flow_layout.py` — `FlowLayout` (ui/widgets/flow_layout.py): minimum width equals the widest single item, `heightForWidth` wrapping when narrowed, item order/positions after a wrap, and `takeAt` bookkeeping.
- `test_boundary_view_copy.py` — `BoundaryViewPanel._table_data()` and Copy Table: Markdown and CSV export in both orientations.
- `test_case_switch_clears_block_mesh_panel.py` — `_load_case_dir()` fully resets `BlockMeshPanel` state via `clear()` (not just the `_topo_shapes`/`_snappy_shapes` lists) when switching to a different case: per-shape menu actions, `non_geometric` lists, `locationInMesh`/`locationsInMesh` markers, and the `Export Shapes as STL…` action's enabled state all clear.
- `test_code_editor.py` — `CodeEditor` fold-map computation, collapse/expand toggling, automatic folding of the `FoamFile { … }` header and the top-of-file comment banner on load.
- `test_code_editor_zoom.py` — the editor's zoom half of `ui/widgets/code_editor.py`: `Ctrl` `+`/`-`/`0` and `Ctrl+wheel`, the offset-in-points model (so a persisted zoom keeps its meaning on a machine with a different application font), and the `ZOOM_MAX_POINT_SIZE` clamp.
- `test_comparison_tree_panel.py` — `ComparisonTreePanel`: `load` sets the header label, populates the proxy, collapses the FoamFile node, re-applies Type column visibility; `clear` resets model and header; `set_type_column_visible` hides/shows the Type column and persists across `load` calls; `use_value_requested` signal is connectable.
- `test_detail_panel_fit.py` — the Detail pane's own wrapped-label clipping fix (see "Repeated fitting: the Detail pane" under "Font sizes and display scaling" below): `_choice_hint_label` reaching the bottom of the scroll area's reachable range at three font sizes, every wrapped label on the normal page getting the height it needs, and narrowing after populate (exercising `resizeEvent`'s own re-fit, not just the populate-time one).
- `test_dialog_fonts.py` — the About and Resources dialogs' labels sizing from the desktop font at 9, 11 and 16 pt. Six of them used to pin a `font-size` in pixels (16, 12, 12, 12, 13, 13), which ignored the desktop font entirely — the same fault as `test_block_mesh_panel_fonts.py` above.
- `test_dialog_label_fit.py` — `ui/label_fit.py`: both dialogs built at 9, 11 and 16 pt, asserting no wrapped label is allocated less than its text needs. Both are a fixed width full of wrapped labels, and a wrapped `QLabel`'s `sizeHint` is measured at a width Qt guesses rather than the one it gets — optimistically enough to cut the last lines off the About dialog's acknowledgements and the second paragraph off both disclaimer boxes, at a desktop font as ordinary as 11 pt. Compare `test_detail_panel_fit.py` above, which covers the same helper applied to a panel that is re-fitted rather than fitted once.
- `test_diff_state_reset_on_case_change.py` — `_reset_diff_for_case_dir` regression: opening a different case clears the active comparison (diff state, bar, panel, parse cache); reloading the same case keeps it armed; no-op without an active comparison.
- `test_drag_drop_open_case.py` — `MainWindow` drag-and-drop case opening: `dragEnterEvent`, `dropEvent`, and the `eventFilter` that makes every child widget a valid drop target.
- `test_duplicate_case.py` — case duplication: what gets copied in "all files" vs. "app-visible files only" mode, destination creation, extra files configured for the case are copied too.
- `test_editor_panel.py` — `EditorPanel`'s `user_text_changed` gating: not emitted by the programmatic paths (`set_text()`, `reload_highlighting()` — `QSyntaxHighlighter.rehighlight()` fires `textChanged` even though only formatting changed, which used to mark the file dirty after Generate OpenFOAM Keywords), emitted by direct document edits.
- `test_export_stl_action_state.py` — the `STL ▾` menu's "Export Shapes as STL…" action (`_export_stl_act`): disabled by default, enabled after `update_topo_set`/`update_snappy_hex_mesh` loads geometric shapes, disabled again after `clear()` or reloading an empty dict.
- `test_export_stl_dialog.py` — `ExportStlDialog`: row count and labelling for combined topoSet+snappyHexMesh shapes, default checked state mirrors the passed-in visibility sets, Select All/Deselect All, writing one `.stl` per checked shape (round-tripped via `pyvista.read()`), filename de-duplication on label collision, skipping (not raising on) degenerate geometry, and `_safe_filename` sanitization.
- `test_file_list_panel.py` — the diff filter: `set_diff_filter_enabled` shows/hides and unchecks the checkbox; the filter hides zero-diff file items while always showing headers; `mark_diff` updates item visibility immediately when the filter is active.
- `test_find_examples_dialog.py` — `FindExamplesDialog`: non-modal window modality, installation-combo population (with `discover_installations` monkeypatched to a fake install), grouped Tutorials/caseDicts results after a threaded search, preview + Compare/Duplicate-button enablement for tutorial hits vs. caseDicts hits, Copy-to-clipboard, `compare_requested`/`duplicate_requested` emitting the tutorial case root, the no-match/blank-query/no-source status messages, and the file-name filter.
- `test_included_files.py` — `#include` support end to end in `MainWindow`, against a fake OpenFOAM `etc` tree on `tmp_path` (so it never depends on a real installation): out-of-case includes landing in the `<included>` group while in-case ones join their natural group, an already-listed target staying unmarked, the read-only contract (editor, `flags()`, `_mark_dirty`, `save_file`, `save_all_files`, backup, `apply_text_to_tree`, and the flag clearing on the next file), **Open Included File** for both in- and out-of-case targets plus the missing/optional/non-include cases, tooltip notes, and **Copy into case…** including its refusal of an existing name and of a `../` escape.
- `test_foam_highlighter.py` — `FoamHighlighter`: comments, strings, `#directives`, `$macro` references, reserved keywords, numbers (including the lookaround guards keeping digits inside identifiers like `wall0`/`inlet-1` uncoloured), keyword rules sharing the same guards so dotted identifiers like `y0.1` (or `off.1`, shell `config.fi`) are not split, dictionary-key colouring sourced from the schema registry and the keyword JSON (user `foam_keywords.json` preferred, shipped `foam_keywords.default.json` fallback, empty set when both absent), the 1,000-keyword `QRegularExpression` chunking, the enable/disable toggle.
- `test_keyboard_shortcuts_dialog.py` — **Help > Keyboard Shortcuts** stays honest and stays on screen. The list is a hand-written table, so nothing stopped it drifting from the shortcuts the window actually installs — `Ctrl+S` was bound with no menu item and no entry here for several releases. `TestCoverage` walks every live `QShortcut` and `QAction` shortcut under a built `MainWindow` and fails naming any key sequence the dialog omits, which is why a new shortcut must be added to `_SECTIONS_DATA` or the suite breaks. The rest guards the layout (the table had grown taller than a small display could show, and a `QDialog` with no scroll area cannot be resized below its content) and that no section or row label is left untranslated.
- `test_log_summary_dialog.py` — `LogSummaryDialog`: non-modal window modality, defaulting to the most-recently-modified `log.*` file in the case directory and showing its summary, re-parsing when the file field changes, and the empty-case-directory fallback message.
- `test_main_window_save_refresh.py` — first behavior-level `MainWindow` test (vs. `test_main_window_split.py`'s structural checks only): editing without saving leaves the `constant/polyMesh` mesh indicator unchanged; `save_file()`/`save_all_files()` both refresh the file list immediately so the staleness indicator updates without a full "Reload Case".
- `test_main_window_split.py` — the mixin structure: each mixin owns the right methods (including `_on_patch_selected` in `_BoundaryOpsMixin`, `_apply_comparison_value` in `_TreeCrudOpsMixin`, and the foamMonitor methods in `_FoamMonitorOpsMixin`), no cross-mixin duplicates, `MainWindow` inherits from all mixins.
- `test_manage_extra_files_dialog.py` — `ManageExtraFilesDialog`: display of registered extra files/directories and removal actions.
- `test_reset_all_settings.py` — what `app_config.json` looks like after **Reset All Settings**, where deleting the file is only half the job: the application keeps running, and `closeEvent` used to capture the session layout and window size on the way out, recreating the file and handing back the settings the user had just asked to be rid of. Pins the close writing nothing once the config has been deleted, and writing as before when it has not.
- `test_run_tool_dialog.py` — `RunToolDialog`: the live preview matching `get_command()` from a pristine dialog, checkbox/value edits updating the command, `last_values` restoration and `get_values()` round-tripping into a new dialog, the Run button disabling on unparseable extra text, the prefix checkbox prepending its shell prefix, and Browse inserting case-relative paths (absolute when outside the case).
- `test_stays_open_menu.py` — the toolbar dropdown menus (`Vertices ▾`, `Blocks ▾`, `Scale ▾`, `topoSet ▾`, `snappyHexMesh ▾`) staying open on checkable-item clicks while still closing for non-checkable actions.
- `test_terminal_panel.py` — `SimpleTerminalWidget` and `TerminalPanel`: initial state, working-directory switching, cleanup, command history, the tab label, `run_command()` (including queuing before the shell is ready).
- `test_theme.py` — `ui/theme.py`'s colour tables as data: the contrast maths, the convention rule for the selected-row pair (with a regression test naming the Windows accent `#0078d4` explicitly, since picking the higher-contrast of black/white reproduces the bug), a sweep asserting no accent can produce an illegible pair, a 3:1 floor for every foreground in both tables against that theme's `Base`, the diff-swatch versus legend-fill separation, and a 3:1 floor for the viewport's text against `viewport_bg`. Table-level checks: they catch a colour that cannot work, not one that merely looks wrong. See "Theming and colours".
- `test_fonts.py` — `ui/fonts.py`: the monospace sizes the editor and both terminals derive from the application font, including `ui_point_size`'s fall back to `QFontInfo` only for a pixel-specified platform font (`QFontInfo` quantises to whole pixels, so 13 pt at 96 dpi comes back as 12.75) and `css_pixel_size`'s fixed 96/72 conversion for the xterm page.
- `test_icons.py` — `ui/icons.py`: `ICON_NAMES` matches the asset directory both directions, every declared name loads a non-null icon with non-empty pixels, an unknown name degrades to a null icon rather than raising, every SVG asset parses and carries the SPDX header, `icon_pixel_size()` growing with the application font, and the dark-mode guard — an icon's mean luminance over its alpha-masked opaque pixels is high under `apply_theme(app, "dark")` and low under `"light"`, which is the one check that actually catches a regression back to a string-substitution tint rather than the alpha-mask composite. See "Icon tinting" below.
- `test_tools_ops_mesh_actions.py` — the Tools-menu "Run *" actions and Run Allrun/Run Allclean/Clean Case: the exact command string sent to a fake terminal panel after accepting the (real, exec-patched) `RunToolDialog` for blockMesh/snappyHexMesh/topoSet/setFields/checkMesh, nothing sent on cancel, the rerun warning text passed to the dialog when time dirs exist, last-used options restored from `state.run_tool_options`, the setFields restore-0/ prefix checkbox (present + checked by default with `0.orig/`, absent without, uncheckable to "run anyway"); missing-script warnings for Allrun/Allclean; the three-way Allrun pre-flight when `log.*` files exist — clean-then-run, run-anyway, cancel; the Clean Case dialog mentioning Allclean delegation or `-auto` 0/ removal; and `_update_tools_actions()`'s enablement for all these actions plus View Log Summary (which needs a case but not a terminal).
- `test_tree_block_crud.py` — Add/Duplicate/Delete on `block_entry` rows: `_new_sibling_for` producing a `block_entry` whose default value reparses as a real block (and a `word` entry for a dictionary parent), `_delete_label` naming a block by position, the written file after a block is deleted or added (siblings verbatim, list still closing on its own line, remaining blocks renumbered by position), and the end-to-end delete → editor text → Ctrl+Z round trip through a MainWindow.
- `test_tree_color_lexer_dispatch.py` — `unknown_raw_entry` amber colouring, the parser `_PAREN_DISPATCH` table.
- `test_tree_copy_paste.py` — tree Copy/Paste Value: round-tripping a copied value, pasting across differently-typed nodes, guards that reject unsupported node types.
- `test_tree_undo_redo.py` — snapshot-based tree undo/redo: an inline edit undone restores the value, editor text, and clean dirty flag (and redo re-applies it); multi-step undo; a new edit clearing the redo branch; rejected edits' stray snapshots being skipped; delete/add-entry round-trips; one CRUD operation producing exactly one snapshot (no signal double-checkpoint); a multi-file snapshot restoring every file; stacks cleared on case reload; and the depth cap.
- `test_update_viewer_panels.py` — `MainWindow._update_viewer_panels`: the file-name → 3-D viewer dispatch, parametrised over each dictionary that drives an overlay, an unrelated dictionary dispatching to nothing, and Apply Text to Tree refreshing the snappyHexMesh overlay. That last one is why the helper exists: the dispatch was copy-pasted into the load, save and tree-edit paths, and the apply copy had no snappyHexMeshDict case, so applying edited snappy text never refreshed the 3-D view.
- `test_tree_inline_edit_dirty.py` — inline Tree-panel cell edits marking the file dirty and regenerating the editor text; confirms a rejected edit leaves the file clean.
- `test_view_log_summary_action.py` — `_on_view_log_summary_clicked`: reopening after the dialog was closed (it's only hidden, not destroyed, so the cached instance must be re-shown, not just raised), the no-case-dir no-op, and following a case switch (`_load_case_dir` pushes the new directory into the already-open dialog immediately via `set_case_dir()`, not just on the next menu click).
- `test_pane_minimize.py` — `ui/pane_minimize.py` and the three panes it is wired to: the collapse/restore round trip, minimizing twice not forgetting the size to go back to, the `strip` style pinning *and releasing* the widget maximum, freed space going to the other panes proportionally, the View-menu items tracking the panes without the two toggling each other in a loop, the bottom row stopping at its tab bar (with the tabs and corner widget still there), the handle double-click — including a handle with no minimizable pane beside it doing nothing —, side-by-side parking the Detail pane but not un-parking one the user had parked first, and the `minimized_panes` capture/apply round trip, whose restore size has to be written *after* minimizing or the collapsed size overwrites it. One test pins the no-drift property rather than exact pixels: Qt's own distribution loses a pixel from the row on the first cycle and there is no arguing with that, but the second cycle and the tenth must land where the first did.
- `test_tree_text_sync_bar.py` — where **Apply Text to Tree** / **Reload from Tree** live: on the bottom tab bar's corner rather than inside a tab page (which would hide them on a tab switch, and `apply_text_to_tree` is what refreshes the 3-D overlays), gone from the top action bar, wired to the real methods (patched on the class *before* the window is built, so the click tests the wiring and not a re-connection made by the test), and duplicated in the Case menu with `Ctrl+Shift+A` on Apply and deliberately nothing on Reload, which overwrites the editor text.
- `test_action_toolbar.py` — the main action toolbar: it is a real `QToolBar` docked via `addToolBar` (not a child of `centralWidget()`), its icon size follows `icon_pixel_size()`, `createPopupMenu()` returns `None` (Qt's built-in hide-this-toolbar menu would have no way back), the current-case/current-file labels still update after moving onto the toolbar, `"Save All Files"` survives nowhere (not a `QAction` text, an `QAbstractButton` text, a `QLabel` text, or a tooltip), and — the identity check that buys the label/enabled-state sync for free — the toolbar's `Open Case…`/`Save File`/`Save Case`/`Reload Case` actions are the *same objects*, not merely equal, as the Case menu's.
- `test_window_state.py` — `ui/window_state.py` and the screenshot spec it feeds: JSON round-trip of every field, unknown keys and malformed cameras rejected, the defaults merge (including `False` overriding a `True` default, which is what `side_by_side` needs), key-path addressing by name and by row number for anonymous entries, capture from a live `MainWindow`, the lenient counterparts of all of that (unknown fields dropped, malformed cameras/sizes/splitter sizes dropped, an unusable blob giving `None`; a missing case dir, missing file, large non-dictionary file, unknown tab, unknown splitter and vanished tree row each skipped and named in the returned notes instead of raising), and structural checks on `tools/screenshot_specs.json` (valid states, no two shots writing the same file, known path placeholders, and a compare shot naming both its cases outside `$HOME` — the diff bar prints the reference's full path into the image). The capture tool itself is not covered — it needs a real X display.
- `test_session_restore.py` — `ui/session_restore.py`: that a close stores a layout under the right key and stores nothing when the setting is off, that restore reports honestly when there is nothing to apply, that a damaged blob (a renamed field, a changed field shape, a truncated camera, a moved case, a tab label from another language) never raises, and a full round-trip of the case, the open file and the selected tree row from one real `MainWindow` into a second one.

**`tests/services/`**
- `test_backup.py` — backup-file naming (`.bak_<timestamp>`) and content (captures the in-memory buffer when the file is open, the on-disk version otherwise).
- `test_case_copier.py` — `copy_visible_files`: visible files copied with layout preserved, hidden entries (root `log.*`, time dirs, unlisted files) skipped, registered extra files and `.foam-editor-files.json` itself carried over, no-config tolerance, nested destination creation.
- `test_include_scan.py` — `scan_includes`/`included_files`/`copy_destination_for`/`foam_etc_dirs`: hits carrying the raw directive text that the parser also stores (the tooltip lookup key), `#codeStream` C++ headers skipped, non-transitivity, the size/log/script guards, the mtime memo re-reading nothing on an unchanged file and re-reading on change, in-case vs out-of-case splitting, symlink-aware dedupe against already-listed files, the `+N more` origin label, `.gz` targets excluded, and the etc-root chain preferring the user override and degrading to `()`.
- `test_case_files_config.py` — `TestCaseFilesConfigDirs`: `DirEntry` add/remove/update-in-place, backward-compatible loading of plain-string JSON, config reset.
- `test_case_loader.py` — `detect_time_dirs` and `TestExtraDirs`: flat and recursive extra-directory scanning, missing-directory tolerance, duplicate suppression.
- `test_example_search.py` — `example_search`: `installation_from_dir` on an install root / bare tutorials dir / non-install dir; `discover_installations` env-mapping injection, `extra_roots` precedence, and de-duplication; `case_root_for` ancestor walking with the `stop` boundary; `search_examples` hits in both sources (source/case_root/line_numbers/snippet fields), case-insensitivity, `file_name` and `sources` filters, `max_hits` cap, `cancelled` early exit, binary/oversized-file skipping, the 50-line-number cap, blank-query `ValueError`, and the `progress` callback.
- `test_log_summary.py` — `parse_log`/`format_summary`: `blockMesh` Mesh Information/Patches extraction and fatal-error detection; `snappyHexMesh` phase splitting on `Wrote mesh in` markers, per-category refinement iteration counts, the final per-patch layer table, and warning de-duplication with a repeat count; `topoSet` multi-source set collapsing (a `Read set` checkpoint continuing the same set rather than starting a new one); solver logs — steady converged (Run/Residuals phases, converged line, total time), transient with per-name Courant lines and the ESI `Time = 0.005s` unit suffix, fatal-error and no-`End` runs marked FAILED, and a `checkMesh`-style log with `Time =` lines but no residuals staying on the generic path; the generic tail fallback for an unrecognized utility.
- `test_tool_options.py` — `tool_options`: the expected `TOOL_SPECS` set and default commands (snappyHexMesh's default-on `-overwrite`), `build_args` bool/value/file handling in spec order, empty-value omission, shlex splitting of the extra text (unbalanced quote → `ValueError`), stale unknown flags ignored, and `build_command`'s quoting, raw prefix, and `tee log.<tool>` suffix.

**`tests/app_config/`**
- `test_app_config.py` — `AppConfigManager`: window size, default case dir, Case Library dirs (incl. the `$WM_PROJECT_DIR/tutorials` fallback), `save()`/`reset()` semantics, fallbacks when `app_config.json` is absent, combined settings, JSON structure, feature-flag handling (`set_feature`/`set_features`).
- `test_foam_env.py` — `foam_env_dirs`: explicit `FOAM_*` variables winning over `WM_PROJECT_DIR` fallbacks, per-subdirectory fallback only when the dir exists, invalid/blank variables treated as unset, version resolution.
- `test_json_io.py` — `load_json` missing/corrupt/valid handling; `save_json` round-trips and parent creation; `atomic_write_text` leaves no `.tmp` sibling on success and keeps the original file intact (temp cleaned up) when the final rename or serialization fails.
- `test_keyword_generator.py` — `keyword_generator`: `scan_src_lookup_keywords()` collecting dictionary-read calls (`lookup`/`get<…>`/`readEntry`/`found`/…) from `*.C`/`*.H` with non-keyword forms rejected; `generate(project_dir=…)` over a fixture install tree — environment ignored, `version` from the dir name, provenance metadata in the payload, `RuntimeError` when nothing is collected.

**`tests/schemas/`**
- `test_schemas.py` — `ChoiceItem`/`KeySchema`, `schema_config.json` load/save/reset/delete, `SchemaRegistry` plain/parent-qualified/grandparent-qualified lookup, the closed-namespace rule that withholds the flat fallback inside a foreign namespace (over a synthetic two-model module, plus the check that a real `snappyHexMeshDict` namespace does not over-suppress), the `snappyHexMeshDict` schema module, the configured module list.
- `test_schema_coverage.py` — the test that would have caught a whole module going dark. Parses the real dictionaries in `tests/fixtures/schemas/` (copied unmodified from the v2606 tutorials, so they are not curated to fit the schema) and walks them exactly as `DetailPanel` does — `node.name`, `node.parent.name`, `node.parent.parent.name` — asserting a per-dictionary coverage floor. `fv_schemes.py` once spelled its keys `"<key>.<parent>"` while the registry looked up `"<parent>.<key>"`, so every entry was unreachable and 0% of a real fvSchemes resolved, yet the unit tests passed because they asserted the internal table shape rather than the call the UI makes. Also checks two table invariants — a dotted key's suffix must equal its `KeySchema.key` (the exact rule that module broke), and every `use_instead`/`renamed_from` target must itself be a documented key — plus the provenance cases end to end: motorBike's `minFlatness` reports as `ineffective`, `minMedianAxisAngle` as `renamed` with a successor and version, and `mergeType` never offers the invalid `merge`.
- `test_turbulence_schemas.py` — the foamlore-generated `turbulence_properties`/`momentum_transport` modules: `TARGET_FILE` and `SCHEMAS` shape (every value a `KeySchema`, every choice a `ChoiceItem`), both registered by default in `schemas/builtin.py`'s module list, `SchemaRegistry` lookup through the parent-qualified form (`kOmegaSSTCoeffs.beta1`) and the plain `RAS`-dict fallback, per-version `supported_in` tags and source-default choices (including `decayControl`'s OpenCFD-only note), and that the `GENERATED` banner survives intact — these files must be regenerated in foamlore, never hand-edited. Plus the seam with the hand-written module: the `RAS`/`LES` model selectors are looked up the way `DetailPanel` does — real file path, real parent key, no `<Model>Coeffs` dictionary anywhere — and their choices must carry `MODEL_DOCS`' description and citation, which is the check the change itself was written against, since the registry API alone had been reporting the prose as reachable while a normal case showed nothing.

**`tests/tools/`**
- `test_capture_dialog.py` — `tools/capture_dialog.py`'s shot list as plain data, the counterpart of `test_window_state.py`'s screenshot-spec checks: names matching their keys, no two shots writing the same file, every shot referenced by both gallery pages and its image present, and `requires()` naming what is missing rather than raising a traceback. Shots are split by where their inputs come from — the capture machine, or the repository — and a third test asserts every shot is classified as one or the other, so adding one forces the choice. It also pins the private `FindExamplesDialog` attributes the `find-examples` shot drives, and asserts the run-tool shot's warning and prefix text still appear in `ui/mixins/_tools_ops.py`, so the gallery cannot end up showing a dialog the app never produces. The capture itself is not covered — it needs a real X display.
- `test_demo_specs.py` — `tools/demo_specs.json`'s scenes as plain data, and the check that earns its keep most: a take needs a real X display, an OpenFOAM installation and about a minute of wall clock, so a scene naming a renamed menu item would otherwise fail halfway through a recording. Covers the spec loading through the strict `WindowState` path, every step's kind and required payload, a targeted step naming exactly one target (and an untargeted one naming none), path and typed-text placeholders being ones `_expand` knows, scratch workdirs living outside the repository, and — for bundled cases only, since a `{cases}` scene depends on the recording machine — the case existing and holding every file the scene opens. Labels are checked against the UI source in the same spirit as the run-tool shot above: menu-bar titles, ellipsis-carrying menu items (the convention for an action that opens a dialog, and so a literal in the source, unlike a shape row read out of a case), button labels and widget attribute names. One test exists purely for a bug that happened: a step's mouse button is `with`, because `button` is already a target, and `"button": "left"` parses as a target named "left" and fails only at record time. The step vocabulary is read off `Runner`'s `_step_*` methods rather than listed, so a new step kind cannot be added to the driver and leave this stale. Driving and recording are not covered — they need a display.

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
| `region_block` | `regions ( … );` whose content is named dicts — decided by a lookahead, since `constant/regionProperties` uses the same key for a plain list and falls through to `raw_list` |
| `region_entry` | named `{ … }` entry inside a `region_block` |
| `boundary_block` | `boundary ( … );` in `blockMeshDict` |
| `boundary_entry` | named `{ … }` entry inside a `boundary_block`. A `boundary_block` may also hold `directive_entry` children: a `#include` standing in for patches (`boundary ( #include "…caseBoundary" outlet { … } );`) is parsed as its own child rather than failing the block, so the patches around it keep their structured parse |
| `action_list` | `actions ( … );` in `topoSetDict`; `value=None`, children are `action_entry` nodes |
| `named_dict_list` | optional parenthesised list of named dicts — `sets ( y0.1 { … } … );` / `surfaces ( … );` (classic sampleDict style); produced only when a lookahead sees `name {` after the `(`, so plain word lists (`sets (setA setB);`) keep parsing as `raw_list` |
| `named_dict_entry` | named `{ … }` entry inside a `named_dict_list` |
| `action_entry` | anonymous `{ … }` block inside an `action_list`; `name=""`, children are the dict entries |
| `block_list` | `blocks ( … );` in `blockMeshDict`; `value=None`, children are `block_entry` nodes. Produced only when a lookahead sees a list whose entries all start with a word in `BLOCK_SHAPE_WORDS` (currently just `hex`, optionally behind a `name <blockName>` prefix); anything else — an empty list, a plain word list, a non-`hex` shape — keeps parsing as `raw_list`. May also hold `directive_entry` children: an `#include` contributing blocks from another file is kept as its own child so the blocks around it still get rows (a list of nothing but directives has no blocks to explode and stays `raw_list`) |
| `block_entry` | one block inside a `block_list`; `name=""`, `value` is the whole normalised block text (`hex (…) (…) simpleGrading (…)`). Cell counts and grading stay in the value string rather than becoming children — nothing consumes them yet and the grading grammar varies too much to model. Row order matches the 3-D viewer's block index, which is why only `hex` explodes; where a `directive_entry` shares the list, `foam/utils.py`'s `block_number` subtracts it so both sides still agree (see "Block numbering with an `#include`" below) |
| `directive_entry` | `#include`, `#inputMode`, etc.; `name=""` |
| `macro_entry` | a macro reference standing alone as a statement; `name=""`, `value` is the reference without its terminator. Four spellings, all one node type: `$p;`, a bare `$p` (OpenFOAM accepts a macro as a complete statement inside a dictionary, as in `maxX { $minX }`), and either of those braced with an optional scope path (`${../_bladeForces}`). The trailing `;` is optional at parse time and is *not* stored in `value`, so the writer reads it back off `raw_text` (`_macro_suffix`) rather than always appending one — otherwise editing a bare `$p` would silently add a `;` the file never had |
| `unknown_raw_entry` | fallback when a parse attempt fails; raw text stored verbatim in `value` |

### Classification logic

`_classify_value(key, text)` (`foam/parser.py:387`) is called for every non-brace, non-special-paren entry. Priority order:

1. **`box_pair`** — only when `key == "box"` and `parse_box_pair(text)` in `foam/utils.py` succeeds.
2. **Parenthesised** — delegates to `classify_parenthesized_value` (`foam/utils.py:113`): returns `vector` (exactly 3 floats), `int_list` (all integers), `scalar_list` (all floats, not 3), or `raw_list` (anything else).
3. **`string`** — starts and ends with `"`.
4. **`macro`** — starts with `$`.
5. **Space-containing** — `nonuniform_list` if it begins `nonuniform List…`, otherwise `compound`.
6. Single token: `int` → `scalar` → `bool` (token in `BOOL_WORDS`) → `word` (fallback).

Before `_classify_value` runs, `_try_parse_special_parenthesized_entry` gets first refusal on
any `key ( … );` entry. It consults four tables in order, each with its own entry shape:

| Table | Entry shape | Lookahead? |
|---|---|---|
| `_NAMED_BLOCK_PARAMS` | `name { … }` | no — the key alone decides |
| `_ANONYMOUS_BLOCK_PARAMS` | `{ … }` | no |
| `_OPTIONAL_NAMED_BLOCK_PARAMS` | `name { … }` | yes — `_looks_like_named_dict_list` |
| `_POSITIONAL_BLOCK_PARAMS` | `hex ( … ) ( … ) simpleGrading ( … )` | yes — `_looks_like_block_list` |

The two lookaheads are non-consuming (they restore `self.index` in a `finally`), so a rejected
entry falls through to the ordinary value path having consumed nothing — which is what lets
`sets`/`blocks` be a structured block in one file and a plain `raw_list` in another.

### Re-parse triggers

The parser runs (and the tree is rebuilt) at exactly two moments:

- **File open** — when a file is selected in the file list or loaded programmatically.
- **Apply Text to Tree** — the manual button in the bottom tab bar's top-right corner.

There is no automatic re-parse on keystroke or on file save. After a manual edit in the text editor the tree and source-line numbers become stale; this is indicated by the "Auto-scroll editor (stale)" label until the next parse.

### Error recovery

When `_parse_entry` raises a `ParseError`, the parser backtracks to `start_index`, records the error in `self.errors`, and calls `_parse_unknown_raw_entry`. That method consumes tokens up to the next `;` or line boundary, wraps the raw text in an `unknown_raw_entry` node, and continues parsing. The file remains usable; the verbatim text is written back on save. After parsing, `OpenFoamParser.errors` contains all recovery events; the caller reports the count in the status bar as "N unrecognized entries."

### FoamNode field semantics

`FoamNode` (`foam/nodes.py`) carries several fields beyond `name`, `node_type`, and `value` that the parser and writer use together:

| Field | Type | Purpose |
|---|---|---|
| `modified` | `bool` | Set to `True` by `FoamTreeModel.setData` when a key or value changes. Drives the writer's regeneration decision. |
| `raw_text` | `str` | The original source text for the node, captured by `_finalize_node` and `_parse_dictionary_entry`. Used verbatim by the writer for unmodified nodes. |
| `leading_trivia` | `list[str]` | Whitespace and comments that appear before the node in the source, including the newline that ended the *previous* entry's line. Restored by `_with_leading_trivia` in the writer to preserve blank lines between entries. See "Trivia ownership" below. |
| `trailing_trivia` | `list[str]` | Root node only: the trivia after the last entry, i.e. the closing `// ****` footer banner and the blank lines before it. Re-emitted by `write_root`. |
| `inline_comment` | `str` | The `// …` or `/* … */` comment immediately following the value on the same line. Collected by `_collect_inline_comment` and reproduced by the writer. |
| `source_line` / `source_end_line` | `int` | 1-based line numbers in the original source, set by `_token_line`. Used for editor-sync highlighting. `0` means the node was added in the tree and has no source location. |

### Writer raw_text passthrough

`_write_node` (`foam/writer.py:61`) skips regeneration entirely when three conditions hold:

```python
if not node.modified and node.raw_text and not _has_modified_descendant(node):
    return _with_leading_trivia(node, node.raw_text)
```

When all three are true the original source text is emitted verbatim, preserving formatting, inline comments, and exact whitespace. Only nodes where `modified=True` (or containing a modified descendant) are regenerated. A "Reload from Tree" on an unedited file therefore produces byte-identical output for every entry captured with `raw_text`.

`_has_modified_descendant` recurses through `node.children` for most types. For `field_value_block` it also checks `node.value` directly (see below).

### Trivia ownership

The passthrough above only reproduces the source verbatim because parser and writer agree on who owns the whitespace *between* entries:

> **A node's text ends at its last content character.** The newline that terminates that line is not part of the node — it belongs to whatever comes next: the following sibling's `leading_trivia`, or the enclosing block's closing brace.

So `raw_text` for `scale 0.001;` ends at the `;`, and the `\n\n` separating it from the next entry is that next entry's `leading_trivia`. The consequence is that `"".join(node.leading_trivia) + node.raw_text`, concatenated over `root.children`, reconstructs the source byte for byte.

Two pieces follow from this:

- **`root.trailing_trivia`** (`foam/nodes.py`) holds the trivia left after the last entry — for a normal OpenFOAM dictionary, the blank lines and the closing `// ****` footer banner. It attaches to no node, so `parse()` parks it on the root and `write_root` re-emits it last. It is the only place this field is used; every other node's trailing whitespace is the next node's `leading_trivia`.
- **`_join`** (`foam/writer.py`) concatenates rendered parts and inserts a line break only for parts that cannot space themselves — nodes added in the tree, and the writer's own synthetic braces and headers. It must not decide this by inspecting the string: the separator between two entries can legitimately be a single space (`x1 14; x2 6;`), which is indistinguishable from generated indentation. Hence `_part` passes the flag explicitly.

  A node with no `leading_trivia` is *not* automatically one that needs a break. It can equally be a parsed node that abutted its predecessor with nothing between them at all — the stray `;` some dictionaries close with (`divSchemes { … };`) is its own entry and has to stay on the `}` line. `_continues_previous_line` tells the two apart by `source_line`, which only a parsed node has, and `_write_inline_entry` consults it again to suppress the indent it would otherwise prepend (`}    ;`).

- **`_own_indent`** (`foam/writer.py`) decides the indentation of a node's *own first line*, and is the counterpart to the rule above. `_with_leading_trivia` already re-emits the source's indentation verbatim, so a renderer that also prepends `_indent(indent)` indents the line twice — which is exactly what regenerating a nested entry used to do: editing `nCorrectors` inside `PIMPLE { … }` moved it from four spaces to eight. Every helper that starts a line goes through `_own_indent` now (`_write_block`'s name/opener, `_write_field_value_block`, `_write_simple_entry`, `_write_inline_entry`, `_write_block_entry`); the openers and closers the writer generates *below* that first line keep the plain `_indent(indent)`, because they have no trivia of their own.

  The rule is: no indent when the trivia already ends in a space or tab, or when the node continues the previous line; otherwise the generated indent — which is what a node added in the tree needs, and what an entry the source wrote at column 0 gets.

`write_root` appends nothing of its own — a source file that ends without a final newline round-trips without one. **The writer has no "tidy the file on save" policy, and must not acquire one:** saving an unedited tutorial case has to leave the file byte-identical, and saving an edited one has to rewrite only the edited entries.

Until this was fixed, it did neither. `write_root` force-appended `\n` to every chunk, double-counting the newline the next node's trivia already carried; two `re.sub` band-aids (`MAX_CONSECUTIVE_NEWLINES` and `re.sub(r'\n{2,}$', '\n', leading)`) papered over the doubling but were lossy — they collapsed real blank-line runs, shifted the blank line around the `// * * *` banner, and, together with `parse()` discarding the EOF trivia, dropped the footer banner outright. Every one of the 439 parseable `system/blockMeshDict` files in the OpenFOAM v2512 tutorials was rewritten on save. `tests/foam/test_writer_roundtrip.py`'s `_CORPUS_SHAPED_DICT` pins the shape the older fixtures lacked (banner, multi-blank gaps, footer), which is why the tests passed throughout.

`tools/roundtrip_corpus.py` measures this over a whole OpenFOAM installation, so the figure in the release notes can be re-derived rather than taken on trust:

```bash
python3 tools/roundtrip_corpus.py --dir /usr/lib/openfoam/openfoam2512
```

It walks every file under a tutorial case's `system/`, `constant/`, `0/` and `0.orig/` and reports how many parse and how many write back identical; `--list-differing` names the ones that do not. On v2512 it reads 9620 files, parses all 9620, and round-trips all 9620. Before the trivia-ownership fix the same corpus round-tripped 286; the parseable count was 9501 until the macro-entry fix (braced `${…}` references and the optional `;`) closed the last 119.

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
    status: KeyStatus = "valid"
    use_instead: str = ""
    deprecated_since: str = ""

@dataclass(frozen=True)
class KeySchema:
    key: str
    label: str
    description: str
    supported_in: tuple[str, ...] = ()
    note: str = ""
    choices: tuple[ChoiceItem, ...] = ()
    status: KeyStatus = "valid"
    use_instead: str = ""
    renamed_from: tuple[str, ...] = ()
    deprecated_since: str = ""
```

`_base.py` exports pre-built version strings — `FOUNDATION_V7` … `FOUNDATION_V14`, `OPENCFD_V2106` … `OPENCFD_V2606`, plus the collective `FOUNDATION_SERIES`, `OPENCFD_SERIES` and `BOTH`. Prefer a collective label for anything in the shared `finiteVolume`/`lduMatrix` libraries: tagging such a key with one release reads in the Detail pane as "only available there", which is how 61 entries once came to tell OpenCFD users that core keys were Foundation-only. Note what a collective label does **not** buy you: the span in it is a verification record, earned by auditing those entries across Foundation 7-13 and OpenCFD v2106-v2606, so a new release does not extend it for free. "Collective" exempts a key from naming one release, not from being measured. `FOUNDATION_SERIES` reaches v14 because `tools/scan_foundation14_keys.py` measured it there; the ~21 keys whose readers that scan never reached carry `FOUNDATION_V7_V13` instead, and that narrower label is the one `OPEN_ENDED_SERIES` marks so the Detail pane qualifies it (the generator's spec item 9). A key measured and found *absent* is a third case again — a closed span plus `deprecated_since`, which says we looked.

### Recording what a key *is*: the `status` field

Real dictionaries are full of names that are no longer current, or that never worked. `KeyStatus` is one of three values, and the Detail pane words its provenance line from it (`DetailPanel._apply_provenance`):

| status | meaning | example |
|---|---|---|
| `valid` | a current key | `scale` |
| `renamed` | a historical spelling; `use_instead` names the successor and `deprecated_since` the version | `convertToMeters` → `scale` (v1012) |
| `ineffective` | appears in official tutorials but no reader consumes it, so writing it does nothing | `minFlatness` → `minFaceFlatness` |

A renamed or ineffective key is **kept**, not deleted — a user whose case contains the old name needs to be told what it is. `renamed_from` goes on the *current* key and lists its historical spellings.

### What happens when a key is omitted: `default` and `required`

Two more fields, answering one question, so the Detail pane gives them a single **If Omitted** row (`_if_omitted_text`). `default` is what OpenFOAM falls back to, spelled as the source spells it. `required` says there is no fallback at all: omitting the key is an error. They are **mutually exclusive**, and `tests/schemas/test_default_and_required.py` fails if any schema sets both.

The rule that keeps them honest: **a fact goes in `default`/`required` or in `description`, never both.** `description` says what the key *means*; these say what happens if you leave it out. An empty `default` is therefore *silence*, not a claim — the generated turbulence modules carry their defaults in prose and leave the field empty, so reading `""` as "no default exists" would mark every one of them required. Only `required=True` asserts absence.

`required` is the field that earns its place, and `CrossPowerLaw.C:71-78` is why: it reads `nu0`, `nuInf`, `m` and `n` with no fallback, and before this the only way to say so was a sentence no code could act on. Being machine-readable, `required` can back a future "your case omits a key OpenFOAM needs" check; a prose default cannot. `default` is the weaker of the two — it mainly lets the generated prose stop duplicating a fact the schema already holds. Neither field goes on `ChoiceItem`: a default belongs to a key, not to one of its values.

Where the rename data comes from: OpenCFD declares renames machine-readably as `getCompat("newName", {{"oldName", apiVersion}})`, and Foundation as `lookupBackwardsCompatible<T>({"newName", "oldName"})`. The extraction is **generated, not hand-transcribed**: foamlore's `facts/tools/scan_renames.py` scans both call families across all nineteen checkouts into `facts/derived/renames.json`, and `render_renames.py` turns that into the table spliced into [docs/OPENFOAM_VERSIONS.md](docs/OPENFOAM_VERSIONS.md)'s generated `renames-table` region. Measured over the current scope it finds **21 pairs with none unresolved** — not the ~100 an early estimate guessed, which counted call sites rather than distinct pairs. Some survive only in older trees because the compatibility entry was later dropped: `minMedianAxisAngle` is accepted by OpenCFD up to v2206 and by Foundation to this day.

The scan reads `sources/*/`, i.e. **whatever is checked out**, which is why for most of its life it saw only the turbulence subtree and reached `controlDict`, `fvSolution` and `snappyHexMeshDict` for the first time in August 2026 — finding a three-release-old defect in `turbOnFinalIterOnly` the moment it did (the generator's spec item 10). What is *not* generated is the per-key consequence: `renamed_from`, `use_instead`, `deprecated_since` and `status` on an individual `KeySchema` are still set by hand from the derived table, because whether a pair is a global rename or a fork disagreement is a judgement the table does not make. `turbOnFinalIterOnly` is the type case — Foundation renamed it, OpenCFD reads it as current, so marking it `renamed` outright would tell OpenCFD users to write a key their fork ignores.

### Generated modules (vendored from foamlore)

`schemas/_turbulence_coeffs.py`, `schemas/turbulence_properties.py` and `schemas/momentum_transport.py` are **generated files**, vendored from the sibling foamlore repository (`facts/tools/generate_fode_schemas.py`). They carry turbulence-model coefficients for **29 models** — 16 RAS and 13 LES/DES, every model either fork ships — extracted mechanically from the OpenFOAM `.C` constructors of all nineteen releases (Foundation 7–14, OpenCFD v2106–v2606), with `supported_in` tags measured across those releases and source defaults as `ChoiceItem`s. Coefficient keys are emitted parent-qualified (`kOmegaSSTCoeffs.beta1`) plus a flat fallback matching OpenFOAM's `optionalSubDict` read idiom; where several models read the same name, the flat entry names every owner and offers each model's default. Never edit them here — regenerate in foamlore and re-copy (a test asserts the `GENERATED` banner is intact).

The split is three files rather than two because foundation renamed `constant/turbulenceProperties` to `constant/momentumTransport` in OpenFOAM 8: `_turbulence_coeffs.py` holds the coefficient facts once and exposes `build_schemas(target_file)`, and each of the other two is ~25 lines declaring its `TARGET_FILE` and calling it. `_turbulence_coeffs` is imported, never registered — it has no `TARGET_FILE`, so `SchemaRegistry` would skip it anyway.

**Do not collapse the two into one module declaring `TARGET_FILES`.** `_build_file_key_schemas` merges a multi-file module's table into every file it names *identically*, so OpenCFD-only keys (`decayControl`, all of `GEKOCoeffs`) would resolve inside `constant/momentumTransport` — a file no OpenCFD release reads. Only the facts are shared between the two; every version tag, note and default list is target-dependent. Making the literal merge safe would need a per-key target filter in the registry.

`_turbulence_coeffs` also exports `MODEL_DOCS` — `model → (description, note)`, the summary from the model's own header and the paper it cites — which `turbulence_structure.py` imports to build the choices of the `RAS`/`LES` model selectors. That crosses the hand-written/generated boundary on purpose, and the direction matters: the choice *list* and its `supported_in` tags are structural facts about the dictionary, which the hand-written module owns, while the prose for each name is extracted. Without it the model's description would only ever be reachable through `<Model>Coeffs`, a key that exists only in a case that overrides a default. It is a plain import of a module that declares no `TARGET_FILE` and is never registered, so the load order in `schemas/builtin.py` does not come into it — unlike the selector keys themselves, which the generator deliberately does not emit (generated modules load *after* `turbulence_structure` and would silently override rather than collide).

### SchemaRegistry

`SchemaRegistry` (`schemas/registry.py`) is a singleton loaded at import time via `schemas/__init__.py`. It builds a two-level dict `_file_key_schemas[filename][dotted_key] → KeySchema` from the list of module names in `schema_config.json` (or the built-in default when the file does not exist).

A module declares its target as `TARGET_FILES` (a tuple) or the original single `TARGET_FILE`. Tables are **merged** per file rather than replaced, so several modules can contribute to one dictionary and later modules win on a collision. That is what lets the hand-written `turbulence_structure` module sit alongside the generated coefficient modules for the same file, and what lets one module serve both `turbulenceProperties` and `momentumTransport`.

`schema_for_file_key(file_path, key_name, parent_key, grandparent_key)` implements the lookup:

1. `f"{parent_key}.{key_name}"` — direct parent context.
2. `f"{grandparent_key}.{key_name}"` — grandparent context (for blocks whose immediate parent is user-defined, such as a named `refinementSurfaces` entry).
3. `f"{parent_key}.*"` — wildcard, for dictionaries whose children are named after the case and so cannot be enumerated: `divSchemes { div(phi,U) … }`, `relaxationFactors { equations { U 0.7; } }`, `residualControl { p 1e-3; }`. Deliberately the **direct parent only** — matching a wildcard from the grandparent would reach a level too far, making `functions.*` (which describes one function object) answer for every key *inside* that object. A `*` suffix registers its prefix as a namespace but is excluded from the owned-key set, or it would arm the guard in step 5 against the whole file.
4. Plain `key_name` — flat fallback, unless step 5 withholds it.
5. A dotted prefix is a **closed namespace**: once a module qualifies any key under `kOmegaSSTCoeffs`, a key it does *not* qualify there is not that dictionary's key, and step 3 must not answer for it. The flat fallback is therefore withheld when the parent (or grandparent) is a declared prefix for that file *and* the key is qualified under some other prefix. Keys that no prefix claims are unaffected and still fall back from any context, which is why the nine namespaces in `snappyHexMeshDict` — none of whose keys has a flat twin — resolve exactly as before. The rule exists because coefficients are read through OpenFOAM's `optionalSubDict`, so each one is registered twice, qualified and flat (`kOmegaSSTCoeffs.beta1` and `beta1`, for the `RAS { beta1 …; }` spelling); without it a stray `kOmegaSSTCoeffs { C1 1.44; }` — a coefficient that model never reads — resolved through the flat `C1` and reported kEpsilon's coefficient inside a kOmegaSST dictionary.

`_build_qualified_index` derives both sets (the prefixes a file declares, and the suffixes qualified under any of them) from the key table itself, so a module opts into the rule simply by using dotted keys.

Some dictionaries are namespaces and still legitimately hold arbitrary keys. `RAS` has structural entries of its own (`model`, `turbulence`) while OpenFOAM's `optionalSubDict` idiom also allows a model's coefficients to be written straight into it — `RAS { Cmu 0.09; }`. Structure alone cannot tell that apart from `kOmegaSSTCoeffs`, so a module lists such prefixes in **`OPEN_NAMESPACES`** and they keep the flat fallback. `schemas/turbulence_structure.py` declares `RAS`, `LES` and `laminar`; the `<model>Coeffs` dictionaries stay closed.

### Config: defaults are merged, not replaced

`load_schema_config()` returns the saved file as-is; `SchemaRegistry._effective_config` then computes `union(builtin_defaults, saved) - disabled_modules`. A saved list used to be authoritative, which meant a module added to `schemas/builtin.py` in a later release never reached anyone who had opened **Manage Schema Modules…** even once — their config pinned the old list forever. Only modules the user explicitly removed (recorded in `disabled_modules` by `set_schema_modules`) stay out. A config written before `disabled_modules` existed carries no record of intent, so a module removed back then reappears once; that is the conservative direction, since a schema too many is visible and one click to remove, while a missing schema is invisible.

`reload()` re-reads `schema_config.json` from disk and rebuilds the tables. `apply_and_reload()` rebuilds from the current in-memory config without touching disk (used after **Settings > Manage Schema Modules…** applies changes within the same session).

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

All user-visible strings in `ui/` are wrapped with `tr()` from `i18n/__init__.py`, with two deliberate exceptions (below). English strings serve as their own keys; translations fall back to the key when a mapping is absent. `tests/ui/test_translatable_strings.py` is the regression guard that keeps this true — an AST walk over `ui/**/*.py` that fails on a string literal (or an f-string with fixed, non-interpolated text) reaching a Qt display sink without going through `tr()`. See that test's module docstring for its sink list, its `_LOCAL_SINKS`/`_ALLOWED` exemption tables, and the `# i18n: skip` comment escape hatch for one-off cases.

**Runtime flow**
1. `main.py` calls `set_language(get_app_config().get_language())` before the window is created.
2. Every widget constructor calls `tr("some string")` at instantiation time, so the selected language is applied to the whole UI on startup.
3. Language changes take effect after a restart (no live retranslation).

Step 1 runs *after* `ui.main_window` (and everything it imports) is already loaded — `from ui.main_window import MainWindow` sits above `set_language(...)` in `main.py`. A module-level string constant wrapped in `tr()` at *definition* time would therefore freeze to English forever, regardless of the language the user picks. `ui/panels/block_mesh_panel.py`'s `_MOUSE_HINT`/`_MOUSE_HINT_TOOLTIP` are plain English constants for exactly this reason — `tr()` is applied where they are *used* (inside `__init__`, which only runs once a window is actually being built), not where they are defined.

**Two exclusions: text VTK draws**

`ui/panels/block_mesh_renderer.py` and `ui/panels/shape_mesh.py` are permanently excluded from `tr()` coverage. Their strings end up drawn by VTK's own built-in label font (see "Text drawn by VTK, not Qt" above), which silently draws **nothing** for a character it lacks a glyph for — a Japanese label there would not show mistranslated, it would not show at all. `tests/ui/test_shape_mesh.py` and `tests/ui/test_block_mesh_renderer_colors.py` already AST-assert both modules are ASCII-only, so translating them is not just unhelpful but actively forbidden by an existing test; `test_translatable_strings.py` excludes both files from its own scan for the same reason.

**Interpolation: `.format()`, never an f-string**

`tr()` looks a string up in `TRANSLATIONS` by its exact English text, so the text passed to `tr()` must be the same for every call — an f-string bakes the *rendered* value into what would be the lookup key, so `tr(f"Line: {n}")` can never match a `i18n/ja.py` entry. Interpolate after translating instead: `tr("Line: {n}").format(n=n)`, with `"Line: {n}"` as the literal key in both `tr()` calls and `i18n/ja.py`. `ui/panels/file_list_panel.py`'s `tr("included from {origin}").format(origin=origin)` is the original precedent for this.

**The `▾` menu-button marker stays outside the key**

`ui/panels/block_mesh_panel.py`'s dropdown buttons (`topoSet ▾`, `STL ▾`, ...) append `" ▾"` to an already-translated label inside `_menu_button()` itself, rather than folding the glyph into the translation key (`tr("topoSet ▾")`). The marker is chrome, not prose — translating `"topoSet ▾"` and `"snappyHexMesh ▾"` as two unrelated strings would be seven near-duplicate keys differing only by a trailing symbol that never changes between languages. Call sites pass the caller `tr("topoSet")`; `_menu_button` appends the glyph after.

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

## Include resolution

A dictionary can pull in another file with an `#include`-family directive, and roughly half of those in the OpenFOAM tutorials point *outside* the case, into the installation's `etc/caseDicts/`. `foam/parser.py` still stores every directive as an opaque `directive_entry` (`name=""`, `value` = the raw source line) — the included content is never inlined into the including file's tree. Instead the target is resolved to a real file and listed as a **separate file**, the same way a symlinked file is.

**Two layers.** `foam/include_resolver.py` is pure text→path logic, Qt-free and stdlib-only; it takes `etc_dirs` as a *parameter* so `foam/` keeps its no-dependency rule. `services/include_scan.py` is the disk half: it supplies the `etc` search path, runs the resolver over a case, and caches.

`parse_include_directive(text) -> IncludeRef | None` strips a trailing comment, `;`, whitespace and one layer of quotes, then rejects anything that is not a followable include. `resolve_include(ref, source_file=…, case_dir=…, etc_dirs=…) -> ResolvedInclude` always returns a value; `path is None` means unresolved and `status` says why:

| status | meaning |
|---|---|
| `resolved` | `path` is the on-disk file |
| `missing_optional` | `#sinclude`/`#includeIfPresent` target absent — legal OpenFOAM, never a warning, never listed |
| `no_installation` | an `etc`-based kind with no `etc_dirs` at all, so the UI can point at the installation picker instead of claiming the file is missing |
| `missing` | everything else |

**Resolution order** — first existing candidate wins, each passed through `foam/utils.py`'s `resolve_optionally_gzipped`:

| kind | candidates, in order |
|---|---|
| `include` / `sinclude` / `includeIfPresent` | leading-token expansion → `<including file's dir>/target` → `<case>/target` |
| `includeEtc` | `<root>/target` for each etc root |
| `includeFunc` | `<case>/system/<name>` → a recursive name→path index of `<root>/caseDicts/postProcessing` per etc root |

"Including file's directory first, then the case" is one rule covering every real form: `0/U` + `"include/initialConditions"` finds `0/include/…`, and `system/snappyHexMeshDict` + `"meshQualityDict"` finds `system/meshQualityDict`. Case-local `system/<name>` winning for `includeFunc` is what makes **Copy into case…** an override that needs no edit to the directive.

Before that, `os.path.expandvars` runs (`$FOAM_CASE`, `${WM_PROJECT_DIR}`; an unset variable stays literal and simply misses — running without a sourced environment is not an error), then a *leading* path token is expanded, matching OpenFOAM's `fileName::expand`: `<case>`, `<system>`, `<constant>`, and `<etc>` (which yields one candidate per etc root).

**The etc search path** comes from `include_scan.foam_etc_dirs()`, cached and deduped, keeping only directories that exist: `~/.OpenFOAM/<version>/` (OpenFOAM's own first location) → the user's `openfoam_dir` config key + `/etc` (set by the shared `InstallationSelector`) → `foam_env_dirs().etc_dir` → each `discover_installations()` root + `/etc`. With no installation at all it returns `()` and the two etc-based kinds report `no_installation`. Note it cannot know which OpenFOAM *version* a case targets, so a case from an older release resolves against the newest installed `etc` unless the user picks one explicitly.

**Why a regex line scan, not a parse.** `scan_includes` runs on every file-list refresh, and refresh is driven by a 400 ms-debounced `QFileSystemWatcher`, so it never walks directories (it only reads the paths `list_case_files` already returned), rejects most files with a substring test (`"#include"`/`"#sinclude"`) before any regex, skips files over 512 KB plus scripts and `log.*`, and memoises per file on `(mtime, size)`. `_dedupe_key`'s `Path.resolve()` is memoised too — it walks every path component for symlinks and dominated the refresh cost before that (a 54-file case measured 4.4 ms warm, 1.5 ms after). Resolution is deduped within a scan, since a reference like `setConstraintTypes` recurs in every field file.

**C++ header rejection.** A `#codeStream` body contains real `#include` lines for C++ sources, which must never reach the file list. Two rules, applied at both entry points: a whole-token angle bracket (`^<.*>$`, which `<constant>/caseSettings` escapes because it does not *end* in `>`), and a suffix in `.H/.h/.C/.cc/.cpp/.hpp/.hxx`. Measured against the v2512 tutorials this is exactly effective: every false positive there (`createTime.H`, `argList.H`, `fvCFD.H`, `setRootCase.H`, …) ends in `.H`, and no dictionary include does. It remains a heuristic rather than a proof — see "Update candidates".

Across the whole v2512 tutorial corpus, 1072 of 1081 directives resolve; the nine that do not are files `Allrun` generates (`blockMeshDict.caseBlocks`, `constant/ignitionPoint`) or ones under a `0/` that only exists after `0.orig/` is copied — correctly reported missing in a pristine case.

**Resolution is one level deep and not transitive**: an included file is not itself scanned.

**Listing.** `services/case_loader.list_case_files` is deliberately untouched — it is the case allow-list, and `services/case_copier.copy_visible_files` relies on it (duplicating a case must not copy `/usr/lib/openfoam/…` into it), as does the Add-files dialog's `loaded_set`. Includes are appended after it by `_case_file_paths` (`ui/mixins/_file_ops.py`), which both `_load_case_dir` and `_reload_file_list` call. A target already in the list keeps its normal appearance: only rows the scan *added* get `_INCLUDED_ROLE` and the `↳` marker. Dedupe is on the resolved real path (so a symlink alias matches), while the *displayed* path stays the include's own spelling. A `.gz` resolution is reported `resolved` but excluded from the list, because `foam/utils.py`'s `read_foam_file` cannot decompress it.

`model/file_list_model.py`'s `_group_name` needed one change: its `except ValueError` branch (a path not under the case dir) now returns the new `INCLUDED_GROUP` sentinel (`"<included>"`, ordered 2000 so it sorts below even `ROOT_GROUP`). An include *inside* the case succeeds at `relative_to` and lands in its natural `constant`/`system`/`0/heater` group for free — that is the whole of the grouping rule. The old `p.parent.name` fallback is kept for the `case_dir is None` path.

**Read-only contract.** An out-of-case include is shown but never written to: editing one would change a file shared by every case. One predicate, `_is_read_only(path)` (`ui/mixins/_model_ops.py`), reads `state.read_only_files`, which `_case_file_paths` rebuilds on every list load. It gates nine places: `_mark_dirty`/`_mark_path_dirty` (**the real lock** — with dirty never set, the `*` marker, Save All and the unsaved-changes prompts are all dead by construction), `save_file`, `save_all_files`, `EditorPanel.set_read_only`, `FoamTreeModel.flags` (withholding `ItemIsEditable` disables inline edit *and* Paste Value), `DetailPanel._populate_normal`, the tree context menu's mutating entries, `apply_text_to_tree`, and `_create_backup`/`_on_delete_file_requested`/`_on_duplicate_file_requested` (each writes to the file or beside it). `ui/mixins/_diff_ops.py` needs no change — `_recompute_diff` and `_precompute_diff_step` already wrap `relative_to(case_path)` in `try/except ValueError`, so out-of-case files are skipped for free; that pre-existing guard is now load-bearing.

**Copy into case…** (`_on_copy_into_case_requested`, `ui/mixins/_file_mgmt_ops.py`) is the escape hatch, offered only on a read-only row. `include_scan.copy_destination_for` picks the destination: `includeFunc`/`includeEtc` flatten to `system/<name>`; a plain `#include` with a relative target keeps that relative path, so it re-resolves to the copy with no edit at all. The containment check normalises the path first — `Path.relative_to` is purely lexical, so `<case>/../escaped` would otherwise pass it. Afterwards it calls `_reload_file_list()`, **not** `_load_case_dir`, which would discard every unsaved buffer.

**Tree affordance.** A `directive_entry` row offers **Open Included File** in its context menu and responds to double-click on the Key/Type columns (the Value column keeps starting an inline edit, since a directive *is* value-editable). Both route to `_open_included_target`. Resolution notes reach the tooltip and the Detail panel's note line via `FoamTreeModel.set_include_notes`, populated after `_load_tree` from the already-cached scan — the model never touches the disk to paint a tooltip. Notes are keyed on the directive's exact source text, which is why `IncludeHit` carries the raw matched line rather than reconstructing it.

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

## Block selection and CRUD

`blocks ( … )` in a `blockMeshDict` reaches the tree as a `block_list` of anonymous `block_entry` rows. Two things follow from those rows being *positional*, and both are load-bearing:

- The row's `block N` key is synthesised from `index.row()` (`model/tree_model.py`'s `_display_key`), not stored. Insert or delete a row and every key after it renumbers itself.
- That same number is what `BlockMeshRenderer._render_blocks` draws at each block's centroid, because both come from the parsed order of `data.hex_blocks`. **A tree row index is a viewer block index**, with no lookup in between.

### Block numbering with an `#include`

The one thing that breaks "row index *is* block index" is a `block_list` that also holds a `directive_entry` — `boundary`-style, an `#include` pulling in blocks defined in another file:

```
blocks
(
    #include "blockMeshDict.caseBlocks"
    hex ( 48  52  53  49  64  68  69  65) ($yc $zc $x4) simpleGrading (1 1 1)
    …
);
```

The directive takes a row without being a block, while `block_mesh_extractor` counts `hex` entries only — so the raw row would label the first real block `block 1` where the viewer draws a `0`. `foam/utils.py`'s `block_number(parent, row, skipped=None)` is the single correction, used by all three consumers: the model's key column and tooltip (via `_block_number`, which memoises `non_block_rows` per list and clears the cache in `insert_node`/`remove_node`, keeping the common directive-free case O(1) rather than reintroducing the O(N²) sweep the key column has to avoid), `_delete_label`, and `_highlight_selected_block`.

Both sides are then numbering the blocks written *in this file* only. What the `#include` pulls in is invisible to FoDE — in `compressible/rhoPimpleFoam/laminar/helmholtzResonance`, the only tutorial written this way, `blockMeshDict.caseBlocks` is a symlink `Allrun` creates at run time, pointing at either `blockMeshDict.resolvedBlocks` (23 blocks) or `blockMeshDict.modelledBlocks` (0), and it does not exist in a pristine case. So these indices can differ from blockMesh's own once it resolves the include; what they cannot do is differ from each other, which is the invariant the tree/viewer pairing rests on.

**CRUD.** Add Entry After, Duplicate and Delete are enabled on `block_entry` rows even though their parent is not a `dictionary` (`ui/mixins/_tree_crud_ops.py`'s `parent_is_block_list`). Two details are specific to blocks:

- `_new_sibling_for` supplies a real `hex ( … ) ( … ) simpleGrading ( … )` rather than the `newKey / newValue` placeholder used everywhere else — a placeholder would not reparse as a block, so the row would disappear on the next Apply Text to Tree.
- `_delete_label` names the node by position for the confirmation dialog, since `node.name` is `""`.

**Comment Out stays disabled.** A `// hex …` line inside the parentheses is valid OpenFOAM but reparses as *trivia*, so the row would vanish rather than become a commented-out row the user can restore.

**Highlight.** `on_tree_selection` (`ui/mixins/_tree_sync_ops.py`) forwards the selected row to `BlockMeshPanel.set_selected_block`, which stores it and re-renders; `RenderSettings.selected_block` carries it to `BlockMeshRenderer._render_selected_block`. The highlight is its own actor (a thick wireframe plus a translucent surface in `viewport_selected_block`) rather than a scalar on the shared block grid, because the blocks are drawn as a single `UnstructuredGrid` and the highlight has to show even when both **Block edges** and **Solid blocks** are off. Selecting any other row clears it, and loading another mesh drops it — the index would otherwise point into a different file's blocks. The renderer bounds-checks regardless, since the panel can be holding a different file's mesh than the tree is showing.

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
python3 main.py --theme dark                      # this run only; the saved setting is untouched
python3 main.py --ui-scale 150                    # this run only; overrides QT_SCALE_FACTOR too
```

The `--theme` flag (`system`/`light`/`dark`) overrides the stored **Settings > Appearance** value for one process without writing it back, so two windows in different themes can run side by side and neither changes what the next launch uses. `tools/capture_screenshots.py` relies on this.

The `--ui-scale` flag (50-400, percent) overrides both the stored **Settings > UI Scale** value and any `QT_SCALE_FACTOR` in the environment, for one process, without writing anything back. See "Font sizes and display scaling" below for what it actually does.

The `--variant` flag loads `presets/<name>.json`, overwrites the `features` dict in the config singleton, and saves the result to `app_config.json` on exit. Subsequent launches without `--variant` use the saved flags. Feature flags default to `true` when absent, so a developer's personal `app_config.json` (which is git-ignored and typically has no `features` key) always starts in standard mode.

After startup, use **Case > Open Case…** to select an OpenFOAM case directory, or drag a directory from your file manager onto any part of the window. Then choose a file from the file list. `app_config.json` is created automatically the first time a case is opened. `schema_config.json` is created only when schema settings are explicitly changed via the Settings menu.

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

## Theming and colours

`ui/theme.py` is the single source of every colour the UI draws, and the only module that touches `QPalette`. It is applied once in `main.py` before `MainWindow` is constructed:

```python
apply_theme(app, get_app_config().get_theme())   # "system" | "light" | "dark"
```

**Modes.** `system` keeps the platform style and the desktop palette (so a Windows accent colour or a Linux desktop theme still shows through) and only normalises the selection pair. `light`/`dark` call `app.setStyle("Fusion")` and install FoDE's own palette, so the result does not depend on the platform style. The mode is persisted as the `theme` key in `app_config.json` (`AppConfigManager.get_theme`/`set_theme`, same no-auto-save contract as the other setters) and, like the language setting, takes effect on restart — panel stylesheets are baked in at widget construction, so a live switch would leave the window half-themed.

**Why the selection pair is recomputed.** Qt reads `QPalette.Highlight` and `QPalette.HighlightedText` from the desktop independently and never checks them against each other. On Windows the fill follows the user's accent colour while the text does not, giving dark text on a saturated fill.

Note that the naive repair — pick whichever of black/white has the higher WCAG contrast — *reproduces* the bug: the default Windows 11 accent `#0078d4` scores 4.64:1 against black and only 4.53:1 against white, so black wins on the numbers. Around mid luminance the numeric winner flips on noise. `readable_selection_pair` therefore encodes the desktop convention instead:

1. white text whenever it clears `_MIN_CONTRAST` (4.5:1) on the fill;
2. black text on a fill whose relative luminance exceeds `_LIGHT_FILL_LUMINANCE` (0.45) — a yellow or pastel accent, where dark text is the natural read;
3. otherwise keep white text and darken the fill in HSV value steps, preserving hue and saturation, until it clears.

`_normalise_selection` applies this to the Active, Inactive, and Disabled colour groups *unconditionally* — not only when a threshold fails — precisely because the Windows default passes the naive threshold while still being the reported problem.

Because styles differ in how they paint `CE_ItemViewItem` (the Windows 11 style does not simply fill with `Highlight`), setting the palette alone does not guarantee the pair actually gets used. `item_view_qss` additionally pins both the fill and the text in an application stylesheet covering `QTreeView`/`QListWidget`/`QListView`/`QTableView`, in both the `:active` and `:!active` states.

**Semantic colours.** `ThemeColors` is a frozen dataclass whose field names describe the *role* (`file_dirty_fg`, `diff_changed`, `syntax_keyword`, `banner_bg`, …), with a `_LIGHT` and a `_DARK` instance. Consumers call `colors()` at paint or populate time rather than caching at import time, which is what allows the table to be swapped. Two consequences worth knowing:

- The diff legend swatches in `_build_diff_bar` and `FoamTreeModel`'s diff row backgrounds read the *same* fields, so they cannot drift apart.
- `model/tree_model.py` and `ui/widgets/_foam_highlighter.py` both import `ui.theme`. That is a deliberate exception to the layering (`ui/theme.py` depends on nothing but PySide6, so there is no cycle) rather than duplicating the table.

**Why the legend bar has its own fill.** The diff legend is styled with `legend_bg`/`legend_fg`/`legend_border`, not the `banner_*` notice colours it looks like it should share. The bar *carries* the three diff swatches, so its fill has to stay clear of every `diff_*` value: while it used `banner_bg`, the dark table had `banner_bg == diff_changed == #4A4526` and the "changed" swatch was invisible against the bar it sat on. Anything drawn behind a swatch is subject to the same constraint, which `test_diff_swatches_are_visible_on_the_legend_bar` now enforces in both tables.

**The 3-D viewer.** VTK has no palette and draws its own text, so every colour it needs is named explicitly (`viewport_bg`, `viewport_text`, `viewport_grid`, `viewport_label_fg`/`_bg`, `viewport_vertex_label_fg`, `viewport_block_label_fg`) and read through `colors()` in `block_mesh_panel.init_plotter` and `block_mesh_renderer`. The dark `viewport_bg` is a mid-dark blue-grey (`#2E3238`) rather than the panel's near-black: the mesh and its overlays are drawn in saturated mid-tones that lose their hue against a very dark scene. `viewport_geometry_opacity` is a *scale factor*, not a colour — translucent faces blend toward the background, so an alpha tuned against white goes muddy on dark; `_opacity()` applies it and clamps to 1.0. Patch and overlay hues themselves (`_PATCH_COLORS`, `_ACTION_COLORS`, …) are deliberately theme-independent, since they encode meaning rather than styling.

A `ForegroundRole` returned by a model is *not* a way to colour a selected row: `QStyledItemDelegate.initStyleOption` copies it into `palette.Text`, but `QCommonStyle` paints selected rows with `HighlightedText` and the override never reaches the screen.

`tests/ui/test_theme.py` covers the contrast maths, the convention rule (including a regression test naming `#0078d4` explicitly), a sweep asserting no accent can produce an illegible pair, a floor of 3:1 for every foreground in both tables against that theme's `Base`, the swatch-versus-legend-fill separation described above, and a 3:1 floor for the viewport's text colours against `viewport_bg`. Note these are table-level checks: they catch a colour that cannot work, not one that merely looks wrong in place, so a change to the 3-D viewer still wants a look at the real scene (see below).

Rendering the VTK panel for a visual check needs a real X display — `QT_QPA_PLATFORM=offscreen` makes `QtInteractor` abort with `BadWindow`, and `QWidget.grab()` returns black for it because it is a native child window. Use `plotter.screenshot(path)` to capture the scene itself.

**Icon tinting.** `ui/icons.py`'s `icon(name) -> QIcon` loads the hand-authored SVGs under `ui/assets/icons/` and tints them for the active theme. Every SVG is authored black (`fill="#000"`/`stroke="#000"`) with no `currentColor` anywhere in it — Qt's SVG Tiny 1.2 renderer has no CSS cascade, so `currentColor` simply would not resolve, unlike in a browser. Tinting therefore does not touch the SVG source at all: the glyph is rendered to a transparent `QImage`, then `QPainter.CompositionMode_SourceIn` fills the whole image with the tint colour and erases everything outside the glyph's own alpha. That is an alpha mask, not a colour substitution — there is no hex string inside the icon to get wrong, so "black icon invisible in dark mode" is structurally impossible rather than a rule someone has to remember while adding the tenth icon.

The tint colour itself is `theme.icon_tint()` — `QApplication.palette().color(QPalette.ColorRole.ButtonText)`, read live, every call. It is deliberately *not* a `ThemeColors` field: in `system` mode `apply_theme` leaves the desktop's own palette in place, so a hardcoded `_LIGHT`/`_DARK` hex would be correct only by accident against a desktop theme whose button text is not near-black or near-white. Reading the palette is the only source that is right in all three modes, and it keeps `ui/theme.py` the sole module touching `QPalette` — `ui/icons.py` never imports it.

`icon()`'s `size`/`tint` parameters default to `fonts.icon_pixel_size()`/`theme.icon_tint()` and are resolved at call time, not at import — the same rule `ui/theme.py` and `ui/fonts.py` already follow, since the desktop font and the active theme both settle after this module is first imported. The module-level `(name, size, tint)` cache underneath is not the import-time caching that rule warns against: the font and theme are *inputs to the cache key*, so a theme switch or a font change simply misses the cache and renders again — a stale entry is unreachable, not stale. Every failure mode — the SVG file is missing, `PySide6.QtSvg` fails to import, `QSvgRenderer.isValid()` is false — returns a null `QIcon` rather than raising, because a broken icon asset must never be able to stop the app from starting; a null icon just draws nothing.

`tests/ui/test_icons.py` checks `ICON_NAMES` against the asset directory in both directions (a name with no file, and a file with no name, both fail), that every icon renders non-null with non-empty pixels, and — the one that actually catches a regression to the string-substitution version of this bug — that an icon's mean luminance over its *opaque* pixels (alpha masked, so the transparent background cannot dilute the average) is high under `apply_theme(app, "dark")` and low under `apply_theme(app, "light")`.

## Font sizes and display scaling

Two separate mechanisms, often confused because both surface as "the text is too small".

### Sizes come from the application font

`ui/fonts.py` derives every monospace size from `QApplication.font()`; nothing in the UI names a point size of its own. Before it existed, three places did — the editor at 10 pt, the simple terminal at 10 pt, and the xterm.js page at 13 CSS px — which on a desktop whose font is 11 pt made the two panels holding the actual text the smallest thing in the window, and left them unmoved when the user raised the desktop font size.

- `ui_point_size()` reads the size as *set* on the application font, falling back to `QFontInfo` only for a font specified in pixels (some platform themes do that, and such a font reports `-1` for its point size). The order matters: `QFontInfo` reports the size of the font fontconfig actually *matched*, quantised to whole pixels — 13 pt at 96 dpi comes back as 12.75 — and rounding a size the user chose, on every widget that asks, is not this layer's job.
- `monospace_font()` is the family list plus that size; `css_pixel_size()` converts to CSS pixels (a fixed 96/72) for the xterm.js page, which is fed through the `<!--XTERM_FONT_SIZE-->` placeholder in `ui/xterm_terminal.html` alongside the existing CSS/JS ones. Under Qt 6 the logical DPI is pinned at 96 and scaling rides on the device pixel ratio, which WebEngine applies to CSS pixels too, so the ratio between the two sides is constant.

- `icon_pixel_size()` sizes `ui/icons.py`'s toolbar/menu icons the same way: `ICON_TO_TEXT_RATIO` (1.30) of `css_pixel_size()`, floored at `ICON_MIN_PIXEL_SIZE` (12). At the 9 pt default that comes to 16 px — the conventional small-icon size — without pinning 16 outright, so an icon grows the same way the text beside it does when the desktop font is raised. Going through `css_pixel_size()` rather than `ui_point_size()` directly is deliberate: an icon is measured in pixels the way xterm.js's font is, not in points.
- `small_point_size()` / `small_font()` cover secondary text — the BlockMesh panel's mouse-hint line and "⚙ Variable-based" badge, the About dialog's version, licence and acknowledgements lines — as a ratio of the application font (`SMALL_TEXT_RATIO`, with `SMALL_TEXT_MIN_POINT_SIZE` as a floor so an already-small desktop font does not take the hints with it).
- `heading_point_size()` / `heading_font()` are the step up (`HEADING_TEXT_RATIO`), used by the About dialog's app-name line. The bold that goes with it stays in the stylesheet — a weight is a style, not a size.

Between them those replaced eight pinned pixel sizes (11, 11, 16, 12, 12, 12, 13, 13). The two disclaimer boxes got no helper at all: their `font-size: 13px` was simply dropped, because a disclaimer should read as easily as the body text around it, which is what the application font already is.

Note the rule that follows: **size through the font, style through the stylesheet.** A `font-size` in a stylesheet overrides the widget's own font, so a `setFont` above it has no effect; a stylesheet that names only colour, padding and italics leaves the size alone. `tests/ui/test_block_mesh_panel_fonts.py` and `tests/ui/test_dialog_fonts.py` pin both halves, the second including a sweep asserting no label in either dialog pins a size again.

Nothing is cached at import: the platform theme settles the application font before the first widget is built, the same reason `ui/theme.py` reads `colors()` at construction time.

**The editor's zoom** (`CodeEditor.set_zoom_steps`) is stored as an offset in points from the application font, not an absolute size, so a saved zoom keeps its meaning on a machine whose desktop font differs — which is what makes it safe to persist as `WindowState.editor_zoom`. Clamping happens in the setter rather than at the call sites, so holding the key down cannot bank steps the editor never showed. `Ctrl+wheel` needs an explicit `wheelEvent`: `QPlainTextEdit` implements it, but only while read-only.

### Wrapped labels and the height they claim to need

A related trap, and the reason the About and Resources dialogs used to cut their text off: `QLabel.sizeHint()` for a word-wrapped label is measured at a width Qt guesses, not the width the label is given. In a fixed-width dialog that guess is always optimistic — the About dialog's acknowledgements label reported 102 px while needing 176 px at its real 458 px width — so the layout allocated the smaller number and the remaining lines were never drawn. It bit at a desktop font as ordinary as 11 pt, and got worse as the font grew.

`ui/label_fit.py`'s `fit_wrapped_labels(root)` raises each wrapped label's *minimum* height to `heightForWidth(width())`. Three things about how it is called matter:

- **After the first layout pass**, from `showEvent` — a label does not know its width before then, and a minimum pinned from a default width is pinned wrong for good.
- **`layout().activate()` before resizing**, so the new minimums have travelled back up before the dialog's own size hint is read.
- **`resize(width(), sizeHint().height())`, not `adjustSize()`** — the latter clamps a window to two thirds of the screen height, which on a small display is exactly where the text would be cut off again.

Note what is *not* the fix: turning on `QSizePolicy.setHeightForWidth`. `hasHeightForWidth()` is already true for these labels. The layout is not ignoring height-for-width; it is being handed a `sizeHint` that disagrees with it.

`tests/ui/test_dialog_label_fit.py` builds both dialogs at 9, 11 and 16 pt and asserts no wrapped label is allocated less than its text needs.

**Repeated fitting: the Detail pane.** `ui/panels/detail_panel.py` hit the same clipped-last-line bug (the `_choice_hint_label` under a key with schema choices), but it is not another `showEvent`-once dialog: it repopulates on every tree selection, and its width changes on every drag of the `right_upper` splitter, independent of any repopulation. A one-shot fit would leave a stale minimum from whatever width happened to be current the last time it ran.

`ui/label_fit.py` itself is untouched — deliberately. `fit_wrapped_labels` only ever *raises* a minimum, which is exactly right for a dialog fitted once: a label that was already given room keeps it. Lowering minimums back down would be wrong for the About and Resources dialogs, which never need to shrink once shown. The Detail pane needs the opposite habit — a minimum raised for a wide splitter position must *not* survive a later narrow one, or a label that no longer needs the room leaves a gap below it — so that behaviour lives in the pane's own `_refit_labels()`, not in the shared helper: it zeroes every wrapped label's minimum height before calling `fit_wrapped_labels`, so each call starts clean rather than compounding against whatever the previous width left behind.

`_refit_labels()` runs from three places: the tail of `_populate_normal`/`_populate_field_value` (after `_stack.setCurrentIndex`, not before — a `QStackedWidget` only gives a page real geometry once it is current, so fitting first would measure the previous page's stale width, 0 on the very first selection), and from a `resizeEvent` override the panel adds for the splitter-drag case `showEvent` alone cannot cover. Two `layout().activate()` calls bracket the `fit_wrapped_labels` call for reasons parallel to the dialogs' own two-step (`activate()`, then measure) but doubled: the first activate is needed *before* measuring, because a label made visible for the first time by this populate (a schema note that was previously hidden) still carries whatever stale width it last had — 0 for one that has never been shown, and `fit_wrapped_labels` silently skips a label whose `width()` is `<= 0`. The second activate applies the minimums `fit_wrapped_labels` just set, the same as the dialogs' single post-fit activate. A final `self._stack.resize(...)` to the stack's own `sizeHint().height()` is the one step the dialogs do not need: `activate()` only redistributes space inside the page's *current* rect, so a page that now needs more room would otherwise leave that extra height outside the scroll area's tracked range until some later, unrelated resize happened to pick it up.

`tests/ui/test_detail_panel_fit.py` builds the panel at three font sizes, narrow enough that the normal page's wrapped labels need several lines, and checks the scroll area's scrollbar range reaches the bottom of `_choice_hint_label` (not `sizeHint()` — see the repo's "measuring Qt pane overflow" lesson, which reports the same wrong number regardless of what was actually clipped on screen); a separate case populates at a wide width and then narrows, to exercise `resizeEvent`'s own re-fit rather than the populate-time one.

### Qt's scale factor, and why the setting needs a restart

Qt fixes its scale factor when the `QApplication` is constructed and offers no way to change it afterwards, so **Settings > UI Scale** is a `QT_SCALE_FACTOR` written into the environment from inside the process — `main._apply_ui_scale`, called between `parse_known_args` and the `QApplication`, the same before-Qt-starts trick as the `QTWEBENGINE_CHROMIUM_FLAGS` block at the top of the module. The value persists as the `ui_scale` key (percent; `AppConfigManager.get_ui_scale`/`set_ui_scale`, no-auto-save like the rest, clamped to `MIN_UI_SCALE`/`MAX_UI_SCALE` on the way in *and* on load, since a hand-edited 5000 would open a window with no way to reach the setting that did it).

A value from the config file uses `setdefault`, so an existing `QT_SCALE_FACTOR` wins — the environment was chosen for the machine the user is sitting at. `--ui-scale` assigns instead, because overriding is what passing it means.

The setting exists because Qt's own high-DPI handling is only as good as what the session tells it. On X11 the scale factor comes from `Xft.dpi` alone, so a desktop that scales through `GDK_SCALE`, or a fractionally scaled XWayland session, leaves Qt at 1× while GTK applications beside it look right. USER_GUIDE.md's "Text size and display scaling" is the user-facing version of this, including the `QT_FONT_DPI` and `QT_SCALE_FACTOR_ROUNDING_POLICY` escape hatches.

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

**Text drawn by VTK, not Qt** — the 3-D scene's own text (shape name badges, vertex and block numbers, the bounds readout, the orientation triad's letters, the grid's tick labels) goes through VTK's built-in label font, which is not the desktop font stack Qt draws with. That font silently draws **nothing** for a character it has no glyph for — no placeholder box — so a symbol that looks right in a Qt menu can vanish inside a 3-D label while still taking up its width. Two shipped that way until 2026-07-30: `✂`/`⚠` in `_CLIP_MARK_SUFFIX` (now `ui/panels/shape_mesh.py`), and the `→` separating the two numbers of each axis in the **Dimensions** bounds readout (`block_mesh_renderer.py`), which reached the screen as `X  0   3  (3 m)`. Square brackets are no better — they render as parentheses. Keep every string in `shape_mesh.py` and `block_mesh_renderer.py` to ASCII; `tests/ui/test_shape_mesh.py` and `tests/ui/test_block_mesh_renderer_colors.py` each walk their module's AST and assert exactly that, docstrings excepted, because the bounds readout was an inline f-string that a per-constant check walked straight past. The test catches a character that *cannot* be drawn, not one that merely looks wrong, so new scene text still wants a look on screen — a missing glyph is invisible to `assert`. `block_mesh_panel.py`'s `▾`, `·`, `📍` and `…` are unaffected: those are Qt widget text.

**Side-by-side mode** — A `⊞` toggle button (`_bm_side_by_side_btn`) is added as a `QTabWidget` corner widget. When enabled, `_on_toggle_bm_side_by_side` reparents `block_mesh_panel` from the `upper_tabs` `QTabWidget` into `_tree_bm_splitter` (a `QSplitter(Qt.Horizontal)` that wraps `right_upper_splitter` and is itself the content of the Tree tab). The Tree tab is switched to first so the splitter is visible before reparenting; `setSizes([1,1])` and `_init_plotter()` are deferred to the next event-loop tick via `QTimer.singleShot(0, ...)`. When side-by-side mode is turned off, `block_mesh_panel` is moved back into `upper_tabs` as a normal tab. `_update_bm_side_by_side_btn` (`ui/mixins/_panel_ops.py`) enables the button when the current file's name is `blockMeshDict`, `topoSetDict`, `snappyHexMeshDict`, `setFieldsDict`, or one of the sampling names (`SAMPLING_DICT_NAMES`: `controlDict`, `sample`, `probes`, `surfaces`, `singleGraph`) — all render into the same 3-D view (see `block_mesh_extractor.py`, `topo_set_extractor.py`, `snappy_hex_mesh_extractor.py`, `set_fields_extractor.py`, `sampling_extractor.py`), the BlockMesh tab itself is on, and xterm is not active; it is disabled (and side-by-side mode force-exited) otherwise.

**Comparison panel visibility** — `comparison_panel` is added to `right_upper_splitter` at startup but immediately hidden (`comparison_panel.hide()`). Qt `QSplitter` ignores hidden children, so no handle or gap appears. `_on_side_by_side_toggled(True)` calls `comparison_panel.show()` before `setSizes`; `_on_side_by_side_toggled(False)` and `_clear_diff` call `comparison_panel.hide()` after.

**Preview mode** — `BlockMeshPanel` carries two extra flags set on every `update_block_mesh()` call: `_has_variables` (True when the `vertices` raw_list value contains a `$` character) and `_preview_mode` (False by default, toggled by the **Preview** button). When `_has_variables` is True a `_vtx_info_bar` widget (amber **⚙ Variable-based** chip + **Preview** toggle) appears inside the Vertices group box above the table, and the X/Y/Z cells are made read-only (`rw_flags = ro_flags`). When `_preview_mode` is True the cells are editable and `_on_cell_changed` calls `_render()` directly instead of emitting `vertices_changed` — keeping the tree and file untouched. `_on_refresh()` re-extracts from `self._root` before calling `_render()` when in preview mode, which both resets the vertex data and exits preview.

## Screenshot capture

`docs/SCREENSHOTS.md`'s gallery is captured by `tools/capture_screenshots.py` from the shot list in `tools/screenshot_specs.json`. It exists because hand-captured images go stale: the main-window shot sat un-retaken from May 2026 until 2026-07-30, by which point it predated the Tools menu, the key filter box and the case-root and included-files groups. Running the tool twice with different `--theme` values on one spec yields a light/dark pair that differs in nothing but colour.

```bash
DISPLAY=:1 python3 tools/capture_screenshots.py --all                    # whole gallery, both themes
DISPLAY=:1 python3 tools/capture_screenshots.py main-window-tree-editor --theme dark --out /tmp/shots
python3 tools/capture_screenshots.py --list                              # what the spec defines
DISPLAY=:1 python3 tools/capture_screenshots.py <shot> --interactive     # adjust by hand, print the resulting state
```

**A real X display is required.** Offscreen Qt aborts VTK, so there is no headless mode. `--out` defaults to `docs/images/`, so aim a first run somewhere else.

**Capture goes through ImageMagick, not Qt.** `QWidget.grab()` returns black for the BlockMesh panel's native child window (same root cause as the GPU notes above), so the window is captured with `import -frame -window <winId()>`. `-frame` also keeps the title bar and borders that every existing gallery image has, and yields the same 1228×866 for a 1200×800 window. The window id comes from `QWidget.winId()`, so no window-manager query or title matching is involved — but `import` reads the *screen*, so the window is moved to (0, 0) and raised, and anything overlapping it would be captured instead.

**Nothing is written back to `app_config.json`.** The theme comes from `--theme` rather than the saved setting (`main.py`'s `--theme` flag does the same for a normal run), the language is forced to English, and the window is never closed — `MainWindow.closeEvent` is what saves the window size, so not calling it is what keeps a capture from changing the user's settings.

**One process per shot per theme.** The script re-executes itself (`--_worker`), so no shot can inherit state from the one before it. Each worker ends in `os._exit` because VTK's teardown at interpreter exit can abort even after a clean `shutdown()`, which would report a good capture as a failure.

### What a spec pins, and what it does not

A shot's `state` is a `WindowState` (`ui/window_state.py`) — see that module's docstring for the field list. Specs read and apply through the **strict** path, and should keep doing so: an unknown field, a tab label that does not exist or a tree row that has been renamed out from under a spec is a broken spec, and a shot that quietly captures the wrong window is worse than one that fails. The lenient path next to it (`load_saved_state`, `apply_window_state(..., strict=False)`) belongs to `ui/session_restore.py` and is easy to reach for by accident. `defaults` in the spec is laid under every shot. `case_dir` may use `{repo}` for the repository root and `{cases}` for the capture machine's OpenFOAM run directory (`--cases-dir`, or `$FODE_CASES_DIR`), since the tutorial cases the gallery uses live outside the repository.

Only choices are pinned. Tree expansion beyond the selected row's ancestors, scroll offsets, the editor's cursor and fold state and the detail panel's contents all follow from the file that is open and the row that is selected, so the specs pin the selection and let the rest follow — the shots were chosen so that this is enough. `tree_expand` is the one escape hatch, for rows that must be open without being selected.

Two things about a spec are easy to get wrong and worth knowing:

- **`preload_files`** — the 3-D viewer accumulates geometry across the dicts it has seen, so a `snappyHexMeshDict` overlay is drawn inside the block mesh only if `blockMeshDict` was opened too. Every 3-D shot preloads it.
- **`block_mesh_visible`** — switching the terminal out of xterm mode re-enables the **View > BlockMesh 3-D Panel** menu item but leaves it unchecked, so the tab does not come back on its own. A shot wanting the 3-D panel says so explicitly.

### Compare mode

A shot may carry a `compare_with` key beside its `state`, naming the reference case for compare mode. It is deliberately **not** a `WindowState` field: that dataclass is shared with `ui/session_restore.py`, so a field there would change what a saved session restores — a product decision rather than a screenshot one — and compare mode is a consequence rather than the sort of choice `WindowState` holds, since starting one forces side-by-side on. The tool instead calls `MainWindow._start_comparison_with`, the same entry point **Case > Compare with Case…** and the Find Examples dialog use, so the shot shows the real thing.

Two things follow from doing it after `apply_window_state` rather than inside it. The per-file diff counts are precomputed on a zero-timer, so the file-list marks need an event-loop turn before they appear; and starting a comparison un-hides the reference pane, which makes Qt share the splitter space out afresh — so pinned sizes are applied again afterwards, splitter-only.

**A compare shot needs both cases outside `$HOME`**, and so names absolute paths rather than `{repo}`: the diff bar prints the reference case's full path into the image, and this repository lives under a home directory. Same rule and same reason as `capture_dialog.py`'s log-summary case:

```bash
mkdir -p /tmp/OpenFOAM/run && cp -r tutorials/cavity/cavity tutorials/cavity/cavityGrade /tmp/OpenFOAM/run/
```

Sizes travel as `QSplitter.saveState()` / `QWidget.saveGeometry()` blobs (base64 in JSON), which round-trip exactly and stay valid across Qt versions, unlike a list of pixel sizes. Those blobs are not writable by hand, so `splitter_sizes` (plain pixel widths, applied via `setSizes`) is the authoring form; it is only as exact as the `window_size` it was chosen for, which is why both are pinned together.

The camera is `plotter.camera_position` — `(position, focal point, view up)`, which round-trips as three 3-tuples. It has to be applied *after* the last render, because `BlockMeshRenderer.render` ends in `reset_camera()`; hence `apply_block_mesh_view` being callable on its own, and the tool calling it again after the settle delay (the deferred VTK re-initialisation after a terminal-mode switch lands inside that window).

### Dialogs

A dialog is a top-level X window of its own rather than part of the main window's frame, so `capture_screenshots.py` — which applies a `WindowState` to one `MainWindow` and captures that — cannot reach one. `tools/capture_dialog.py` is the other half:

```bash
DISPLAY=:1 python3 tools/capture_dialog.py --all
DISPLAY=:1 python3 tools/capture_dialog.py log-summary --out /tmp/shots
python3 tools/capture_dialog.py --list
```

Its shots live in a `DIALOG_SHOTS` dict in the module rather than in a JSON spec, because a dialog is built from typed Python arguments and a schema to express those buys nothing at this scale. Everything else follows the rules above and for the same reasons: `--theme` and a forced English language rather than the saved settings, `import -frame` rather than `QWidget.grab()`, and nothing written back to `app_config.json`.

**A shot must not put the capturing user's name in the gallery.** The log summary reproduces the `Case:` line out of the log file itself, so a case run from a home directory prints that path into the image. Hence `DEFAULT_CASE` of `/tmp/OpenFOAM/run/pitzDaily`, and this recipe to produce it — the tutorial is deterministic, so any machine gets the same numbers:

```bash
mkdir -p /tmp/OpenFOAM/run && cp -r "$FOAM_TUTORIALS/incompressible/simpleFoam/pitzDaily" /tmp/OpenFOAM/run/ && cd /tmp/OpenFOAM/run/pitzDaily && blockMesh > log.blockMesh 2>&1 && simpleFoam > log.simpleFoam 2>&1
```

The same rule applies to any shot added later: check the image for `/home/<name>` before committing it. `find_foam_example.png` predates the rule and happens to satisfy it, having been taken on a machine whose user was called `user`, and showing only the installation path `/usr/lib/openfoam/openfoam2606/...`.

Each shot pairs a `requires` with its `build`. `requires` answers "does this machine have what the shot reads?" and raises naming what is missing; keeping it out of `build` means the question can be asked without a `QApplication`, which is what lets the tests cover it. Two shots read something the capture machine has to supply (a run case, an installation); `run-tool` reads the bundled `tutorials/damBreak`, since the restore-`0/` prefix it exists to show only appears for a case with a `0.orig/` — so its inputs travel with a checkout.

The `run-tool` shot hands `RunToolDialog` the warning and prefix text that `ui/mixins/_tools_ops.py` would hand it, copied rather than imported because they are inline literals in a mixin and reaching for them would mean standing up a `MainWindow`. The test suite asserts those strings still appear in that file, so the gallery cannot end up showing a dialog the app never produces.

A shot whose content is not ready when the dialog is constructed gets a `prepare` hook, run after `show()` and handed a `pump(ms)` to turn the event loop with. `find-examples` is the case that needed it: its search runs in a `QThread`, so the shot types the query, starts the search, waits for the results tree to fill (capped — a capture must not hang), then selects one result to populate the preview. That hook drives `FindExamplesDialog` through its private widgets, which is the trade for not adding capture-only accessors to a production dialog; `tests/tools/test_capture_dialog.py` pins the names it reaches for, so a rename fails in the suite rather than halfway through a capture run that needs an X display.

Like `capture_screenshots.py`, this one re-executes itself once per shot (`--_worker`). The reason there is that no shot should inherit stray state from the one before it; here there is a harder one too, since `QApplication` is a singleton and a second shot in the same process cannot have one.

### Not covered

`tools-menu.png` has no spec and no shot. An open menu is neither a window of its own nor part of the main window's frame — it is a popup that closes as soon as focus moves — so it is still the one image taken by hand.

The specs capture in `light`, never `system`: a system-themed window inherits the capture machine's desktop palette, which is the one thing about a shot that cannot be reproduced elsewhere. The gallery's light images were hand-captured in `system` mode until 2026-07-30, which is why the current ones show FoDE's own blue selected-row fill rather than the desktop accent, and Fusion widgets rather than the desktop style.

## Demo recording

`docs/DEMO_SCRIPTS.md`'s movies are driven and recorded by `tools/demo_driver.py` from the scenes in `tools/demo_specs.json`. It is `capture_screenshots.py`'s sibling and starts where that one does — a scene's `state` is the same `WindowState`, laid over the same kind of `defaults` — and then adds a list of `steps` that drive the window while `ffmpeg` records it.

```bash
python3 tools/demo_driver.py --list                                            # what the spec defines
DISPLAY=:1 python3 tools/demo_driver.py damBreak-end-to-end                    # rehearse: drive it, record nothing
DISPLAY=:1 python3 tools/demo_driver.py damBreak-end-to-end --record out.mp4   # a take
DISPLAY=:1 python3 tools/demo_driver.py damBreak-end-to-end --stage            # start state, then hand it over
```

`ffmpeg`, `xdotool` and `Xephyr` (`xserver-xephyr`) are required, alongside the X display the screenshot tools need.

**The steps are real X input.** `xdotool` moves the pointer and clicks it, so the app sees ordinary mouse and keyboard events and the recording shows a real cursor moving over real hover states — nothing reaches into the app to fake a click, and the cursor glides between targets on an ease-in-out curve rather than teleporting. A step names a target semantically (a menu item, a tree row by key path, a file row, a button by its label) and it is resolved to a screen point *when the step runs*: a menu item does not exist until the click before it has opened the menu.

**A take runs on a nested display of its own.** Real input goes to whichever window the window manager put on top and wherever focus drifted to; on a desktop in use that is someone's editor, and the take is both unreliable and rude — the failure mode found in testing was a chat window raising itself into the click, and the next step then typing a dictionary value into it. So the driver starts an Xephyr server, runs there, and stops it afterwards. `--on-this-display` opts out for a machine nobody is sitting at. `--stage` never nests, because its whole purpose is to hand the window to a person. A bonus: a nested display has no window manager, so there are no decorations and the recording is the application and nothing else.

**Steps run on a `QTimer` chain, not a nested event loop.** A modal dialog runs an event loop of its own, so a driver that waited by spinning `QEventLoop` would block on the dialog it had just opened, waiting for the step that closes it. Timers fire inside the dialog's loop, so the chain keeps stepping. The same fact bites once more on the way out: `app.quit()` only ends the outermost loop, so a take that stopped with a dialog still up closes it before quitting, or it would hang.

The chain is a queue of *atoms* — resolve, glide, click — and `push` puts them at the **front**, which is what lets an atom schedule work before whatever follows it. That ordering is worth stating because getting it backwards is silent: a click step that pushes its glide and then its click runs the click *first*, at wherever the pointer happened to be, and the take proceeds looking almost right.

**Every take starts from a fresh copy of its case.** A scene names `case_source` and a `workdir`, and the case is copied there unconditionally before the window opens. A take that began from the leftovers of the one before it — a mesh already built, `0/` already set — records something other than what the script says, and a scene that runs `blockMesh` would otherwise litter the repository's `tutorials/`. `terminal_prelude` sources the OpenFOAM environment into the Terminal tab during staging, before recording starts: watching someone set up their shell is not the demo. `clean` is the counterpart for what a *step* creates rather than what the staging copies — a scene that duplicates a case writes a directory neither `case_source` nor `copy_also` names, and finding it there from the last take turns the next step into an "Overwrite?" box. `prepare_case` refuses to clean a path inside the repository.

**And from a fresh `app_config.json`.** `seed_app_config` writes a scratch config into the workdir and points the singleton at it before `MainWindow` is built. Two reasons, and the second is why it runs for every scene. A take must not *write* the recording user's settings: answering "open the duplicated case now?" with Yes saves a new default case directory on the way through, and never closing the window is not enough to prevent it. And a take must not *read* them either — the feature flags, the default case directory and the case library all come from that file, so a movie recorded on one machine would otherwise open somewhere else on the next.

`case_library` builds on it: the named directory becomes the one entry the Case Library offers. It is also assigned to `$FOAM_TUTORIALS`, because `get_case_library_dirs` prepends that variable to the registered list and two entries make the app ask *which* library to browse before it opens the chooser — a dialog whose contents would depend on the recording shell. Pointing the variable at the same directory collapses the pair into one, which is the reason for doing it that way round rather than unsetting the variable: `paraFoam` needs the rest of the OpenFOAM environment intact.

**The nested display costs two things, both handled in the driver.** A dismissed menu leaves its pixels on screen, over anything that does not redraw itself — the 3-D view is immune because VTK repaints it, so what is left is a menu-shaped hole over the editor for as long as it takes something else to draw there. Neither `repaint()` nor `xrefresh` shifts it; a one-pixel resize does, because it invalidates every widget's geometry rather than just its contents, so that is what runs after a step that closed a popup. Separately, takes force Qt's own file dialog (`AA_DontUseNativeDialogs`): the desktop's portal chooser is another process, so none of its widgets are reachable and its keyboard shortcuts vary by desktop — and it opens on the home directory with the user's account name across the top, which a published movie must not show.

**A take cannot hang.** Anything a step raises ends it — with the message, and a screenshot of what was on screen, which is what a target lost to a renamed menu item looks like from the outside. A watchdog ends one that has stopped for any other reason, because a stuck take holds the display and reports nothing.

Two smaller things, both found the hard way. `xdotool mousemove --sync` waits for a motion event that a move to the pointer's *current* position never generates, and blocks for seconds — easing rounds several ticks of a slow stretch to the same pixel, so a glide must skip the moves that would not move anything. And a step's mouse button is `with`, not `button`, because `button` is already a target: the name of the push button to click.

Everything the screenshot tools do to stay out of the user's way applies here unchanged — the theme comes from the spec rather than the saved setting, the language is forced to English, the window is never closed so `closeEvent` never writes `app_config.json`, and the process ends in `os._exit` because VTK's teardown can abort after a clean `shutdown()`.

**One scene drives an application that is not ours.** `cavity-full-workflow` ends in ParaView, which resolves nothing semantically, so its clicks are `point` steps — pixel coordinates read off a rehearsal screenshot. They hold only because a take runs on a display of a known size with no window manager, so ParaView opens at the origin at 1280×800 every time. That scene also needs the driver started from an OpenFOAM-sourced shell, because `_on_open_paraview_clicked` looks for `paraFoam` on `PATH` and falls back to a bare `paraview` with no case loaded rather than failing; `LIBGL_ALWAYS_SOFTWARE=1` is what gets ParaView rendering through the nested display. Both are in `docs/DEMO_SCRIPTS.md`'s Recording section, where whoever records it will be looking.

## Testing

```bash
python3 -m pytest -q
```

If `pytest -q` causes import issues, running it as `python3 -m pytest -q` is safer because the project root is handled more reliably.

`tests/test_lint.py` runs `ruff` and `mypy` as part of the suite (see below), so a plain `pytest -q` also catches lint/type regressions.

### The test run cannot write your settings

`tests/conftest.py`'s autouse `temp_config` fixture points the config singleton — and `$FODE_CONFIG` — at a `tmp_path` file for **every** test. It is unconditional because the ways a test can write `app_config.json` are not visible from the test itself: closing a window saves, anything calling `save()` saves, and a test that turns a feature flag off to stay light leaves it off for the developer whose checkout it ran in. That last one happened, which is why this is no longer left to individual tests to remember. `tests/test_config_isolation.py` fails if the fixture stops being applied.

`AppConfigManager` reads **`$FODE_CONFIG`** when no path is passed, which is the same protection for anything outside pytest — a scratch script that builds a `MainWindow` against a real checkout should set it:

```bash
FODE_CONFIG=/tmp/throwaway.json python3 some_scratch_script.py
```

An explicit `config_path=` still wins over the variable, and the variable is read per call rather than at import, so a test may set it and build a manager in the same process.

Two things to know if you touch that fixture. It is written with plain save/restore rather than `monkeypatch`: an autouse fixture that requests `monkeypatch` makes it the earliest-created fixture in every test, which moves its undo to the very end of teardown — and `tests/ui/test_included_files.py` patches `include_scan.foam_etc_dirs` (an `lru_cache`) and clears that cache in its own teardown, so it needs its patches undone first. And `main_window` requests `temp_config` explicitly rather than trusting autouse ordering, because the window it builds is one of the things that saves.

## Linting and type-checking

Configuration lives in `pyproject.toml`. `ruff` covers the whole repository (no `include`/`exclude` restriction beyond its own default excludes, e.g. `.venv/`) and the whole tree is clean, so it runs unscoped:

```bash
ruff check
```

`i18n/ja.py`'s translation string literals (the English `tr()` keys and their Japanese values) are exempted from `E501` (line-too-long) via `[tool.ruff.lint.per-file-ignores]` in `pyproject.toml` — wrapping either one risks silently breaking the key lookup or corrupting the translated text.

`mypy`'s `[tool.mypy] files` in `pyproject.toml` lists `foam/`, `model/`, `app_config/`, `schemas/`, `services/`, `ui/` (all of it), plus `main.py` and `i18n/` — every top-level source package except `tools/`, which is deliberately left out. Every PySide6 attribute access in `ui/` uses the fully-qualified enum form the stubs require (e.g. `Qt.Orientation.Horizontal`, not the flattened `Qt.Horizontal`) — mixing the two styles is otherwise the single largest source of `mypy` noise in a PySide6 codebase.

```bash
mypy
```

A `[[tool.mypy.overrides]]` entry relaxes `numpy.*`/`numpy` to `follow_imports = "skip"` (plus `follow_imports_for_stubs = true`): numpy's bundled stubs use PEP 695 `type` statements that only parse under `python_version >= 3.12`, which conflicts with this project's `python_version = "3.10"` target (the minimum supported runtime). `ui/panels/block_mesh_*.py`'s and `ui/panels/shape_mesh.py`'s `vtk`/`pyvista`/`pyvistaqt` imports have no stubs at all and fall back to `ignore_missing_imports = true`, so those objects type as `Any`.

### Typing the `ui/mixins/` split

`ui/main_window.py`'s `MainWindow` is built from thirteen mixins plus `QMainWindow` (see the `ui/mixins/` entries in "Project structure" above); each mixin is a plain class with no common base at runtime; the composition only happens once `MainWindow` inherits from all of them. That is a problem for `mypy`, which type-checks each mixin module on its own — a bare `class _FileOpsMixin:` has no way to know that `self` will ever have a `.tree`, a `.state`, or a `._load_tree()`.

`ui/mixins/_protocol.py`'s `MainWindowProtocol` (a plain class inheriting `QMainWindow`, not `typing.Protocol` — mypy rejects a protocol with a non-protocol base) declares that whole combined surface: every widget/state attribute `MainWindow.__init__`/`_build_ui()` sets, and every method any mixin defines, with a signature matching the real one. Each mixin does:

```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ui.mixins._protocol import MainWindowProtocol as _Base
else:
    _Base = object

class _FileOpsMixin(_Base):
    ...
```

so `_Base` is `MainWindowProtocol` while mypy is looking (giving every method in the file the full attribute/method surface) and plain `object` at runtime — an inert base that leaves the mixin's real MRO, and therefore `MainWindow`'s own MRO, unchanged. `ui/mixins/_protocol.py` must never import `ui.main_window` or any `ui.mixins.*` module: that would make the mixins' `TYPE_CHECKING` base inherit from a class that, at runtime, inherits from the mixins themselves — a genuine inheritance cycle, not just a circular *import*, which mypy rejects outright. When adding a method to a mixin that other mixins will call, add its signature to `MainWindowProtocol` too (a mismatched stub signature there surfaces as a spurious "incompatible with supertype" error on the mixin's real method).

`foam/nodes.py`'s `NodeType` `Literal` is the definitive list of valid `node_type` values; `mypy` flags any assignment or comparison against a value outside that set. See the "Node types" section above for what each value means.

## Update candidates

Ideas noted for a later release, not currently scheduled:

- **Glob the suffixed variants of every listed dictionary** — `services/case_loader.py` lists exact names, so `topoSetDict.1`, `decomposeParDict.4`, `controlDict.orig` and the rest are invisible; they are ~9% of the `system/`+`constant/` files in the tutorial trees, the largest single group still unlisted. A `<name>.*` glob per `TARGET_FILES` entry, like `PHASE_FILE_BASES` already does for `constant/`, would sweep up nearly all of them in a few lines. It was consciously not done because the same glob catches `blockMeshDict.m4` (25 cases), an m4 template that is not a dictionary and will not parse — so the change needs a rule for what to exclude, or the text-only treatment scripts and logs already get, rather than being a one-line widening.

- **Schema modules for the uncovered dictionaries** — six of the 105 listed names have one. `docs/SCHEMA_CANDIDATES.md` ranks the rest by measured tutorial frequency and key count and splits them into hand-write-here and generate-with-foamlore, with the reasoning; the cheapest is `meshQualityDict`, where `schemas/snappy_hex_mesh_dict/_mesh_quality.py` already describes the keys and needs only a `TARGET_FILES` tuple to answer for the standalone file too.

- **Detect the case's fork and release, and act on it** — the banner at the top of every dictionary names both (`Version: v2606` / `www.openfoam.com`), and `docs/OPENFOAM_VERSIONS.md` now records what changes between them. Two things could use that: the Detail pane could grey out a `supported_in` that excludes the case's own release instead of leaving the user to compare strings, and `include_scan.foam_etc_dirs()` could resolve `#includeEtc` against the matching installation rather than the newest (which is the "Version-aware `etc` selection" item below, from the other end).

- **Fetch the missing OpenCFD v2112 checkout in foamlore** — the generator's checkout set jumps v2106 → v2206, so a coefficient present across that span renders as the explicit pair "OpenCFD v2106, OpenCFD v2206", which reads as a gap that does not exist. Requested as item 6 in the generator's spec. FoDE's side is done: `schemas/_base.py` exports `OPENCFD_V2112` and the one hand-written tag spanning the gap lists it, by inference from the releases either side rather than measurement.

- **Side-by-side reference *text* editor in compare mode** — compare mode currently shows the reference case as a read-only *tree*; a read-only text editor of the reference file beside the main Editor tab would allow free-form copy/paste of keys and values (today the non-modal Find OpenFOAM Examples preview + "Copy Selection" covers this for example cases, but not for an arbitrary reference case). Revisit as part of a compare-mode update.
- **Consolidate `foam/parser.py`'s four parenthesized-block dispatch tables** — `_NAMED_BLOCK_PARAMS`, `_ANONYMOUS_BLOCK_PARAMS`, `_OPTIONAL_NAMED_BLOCK_PARAMS`, and `_POSITIONAL_BLOCK_PARAMS` each drive a different lookahead/dispatch path for `(...)`-delimited blocks; they could become one table keyed by entry name with a lookahead flag distinguishing the four behaviors, instead of four separately-consulted dicts.
- **3-D picking → tree** — the tree → 3-D direction is done (see "Block selection and CRUD" below); the reverse, clicking a block in the viewer to select its tree row, would be the first use of VTK picking in the codebase.
- **CRUD on the other positional lists** — Add/Duplicate/Delete are now enabled for `block_entry` rows, but `region_entry`, `boundary_entry`, and `action_entry` are still gated on a `dictionary` parent (`ui/mixins/_tree_crud_ops.py`). Those three are *named*, so each needs a way to supply the name of a newly added entry — a prompt, or an inline edit on a placeholder — which is why they were not swept in with blocks.
- **Cells/grading as `block_entry` children** — currently kept in the value string (see the node-type table). If something ever consumes them (e.g. showing cells-per-block in the 3-D panel), the additive shape is named children alongside a regenerated `value`.
- **Decide the fate of `block_mesh_extractor.py`'s legacy raw-text boundary-block fallback** (~lines 164-250) — reachability has now been measured rather than guessed. Of the 489 `blockMeshDict` files in the v2512 tutorials, exactly one reached this path (`compressible/rhoPimpleFoam/laminar/helmholtzResonance`), and it produced *wrong* output there: the regex walker read the leading `#include` as a patch name and gave it the following patch's faces, losing `outlet`. That trigger was fixed upstream in the parser (a directive inside `boundary ( … )` is now a `directive_entry` child instead of a `ParseError`), so the fallback is at 0 hits across the corpus. It is still not provably dead — it remains a net for `boundary` blocks that fail structured parsing for other reasons — so the open question is whether to keep an untested net or delete it and let such files degrade visibly.
- **Transitive include resolution** — `services/include_scan.py` follows includes exactly one level, from the files `list_case_files` already returns. Bounded-depth recursion with a visited set is the additive shape, and this is not hypothetical: in `compressible/rhoPimpleFoam/RAS/annularThermalMixer`, `constant/caseSettings` is itself an include target and its own `#include "<constant>/boundaryConditions"` is therefore not followed, so `constant/boundaryConditions` stays unlisted (the `constant` header shows `[+]` instead). The `etc/caseDicts/*.cfg` files also include each other.
- **Transparent gzip reading for dictionaries** — `foam/include_resolver.py` resolves a candidate through `resolve_optionally_gzipped`, so an include *can* land on a `.stl.gz`-style compressed dictionary, but `foam/utils.py`'s `read_foam_file` cannot decompress one; such targets are therefore reported `resolved` yet deliberately excluded from the file list. A gzip branch in `read_foam_file` would close the asymmetry and also help compressed `0/` fields.
- **`#codeStream` body awareness in the include scan** — the C++-header rejection in `parse_include_directive` (angle brackets, `.H`-family suffixes) is a heuristic that happens to be exactly effective on the v2512 tutorials, where every such include ends in `.H`. A `#{ … #}` depth tracker would be exact, but needs real lexing inside what has to stay a cheap line scan; the current failure mode is benign (an unrecognised target simply never resolves).
- **A general directive registry** — `foam/lexer.py` still collapses every `#word` into one `DIRECTIVE` token, and `foam/include_resolver.py` is the codebase's *first* per-directive knowledge. `#remove`, `#calc`, `#codeStream`, `#eval` and the include family could grow into one table instead of the current split between the lexer's blanket token and one module that re-reads the text.
- **Version-aware `etc` selection for includes** — `include_scan.foam_etc_dirs()` cannot know which OpenFOAM version a case targets, so a case written for an older release resolves `#includeEtc` against the newest installed `etc` unless the user picks an installation explicitly. Reading the case's `FoamFile` header version, or remembering a per-case choice, would remove the surprise.
- **The four remaining parser failure modes** — three parser defects were fixed by walking the v2606 tutorials rather than reasoning about the grammar (a dictionary inside an entry's value, an entry with no value, a comment between a key and its opening brace), taking the corpus from 288 failing files to 38. The 217 errors left in those 38 files are not a long tail: they are four causes, each with a clear shape, and each deliberately left alone because the fix involves a real trade-off rather than a missing case. Measured over the 4435 dictionary files in `/usr/lib/openfoam/openfoam2606/tutorials`:

  | root cause | errors | files | mainly in |
  |---|---|---|---|
  | `#{ … #}` verbatim code blocks | 153 | 27 | blockMeshDict, controlDict |
  | a comment inside a multi-line value | 49 | 11 | fvSchemes |
  | `actions ( name { … } )` with *named* entries | 10 | 6 | setFieldsDict, topoSetDict |
  | a comment or bare word in a field-value list | 5 | 3 | setFieldsDict |

  **`#{ … #}`** is the big one, and it is a *lexer* gap rather than a parser one: `foam/lexer.py` has no notion of a verbatim block, so the C++ inside a `codeExecute #{ … #};` is tokenised as ordinary dictionary text — its braces close dictionaries, its `;` end entries, and the damage cascades to the end of the file (hence 110 of the 153 surfacing as "unexpected EOF"). The fix is a lexer state that emits `#{ … #}` as one opaque token, which is additive; the reason it is not done here is that it belongs with "a general directive registry" above, since `#{` is a directive form and the lexer currently collapses every `#word` into one token.

  **A comment inside a multi-line value** is the one with a genuine trade-off. `_read_value_text_until_semicolon` ends the value at a depth-0 comment, which is right when the entry ends there and wrong when the value continues on the next line — as in fvSchemes' DEShybrid entry, where every line of a ten-line value carries a trailing comment. Making comments non-terminating would fix those 49, but a file genuinely missing a `;` would then be consumed to EOF instead of failing locally, so the change trades a precise error for a broad one and needs lookahead to do properly. Note 30 of the 49 are *cascade*: six real sites, each resyncing badly and mis-parsing the following lines as entries.

  **Named `actions ( … )`** is a dispatch-table question, not a parsing one: `actions` is registered in `_ANONYMOUS_BLOCK_PARAMS` and so expects `( { … } { … } )`, but `topoSetDict` also permits `( heater { … } )` with a name before each block — the same optional-name lookahead `_OPTIONAL_NAMED_BLOCK_PARAMS` already performs for `sets`/`surfaces`. It is listed here rather than fixed because it lands squarely on the "consolidate the four parenthesized-block dispatch tables" item above, and doing it separately would add a fifth path to the four that item wants to remove.

  Round-trip fidelity is unaffected by any of this: all 4435 files write back byte-identical, before and after the three fixes, because an entry that fails to parse is preserved verbatim as `unknown_raw_entry`. The cost is in the tree view and schema help, which are wrong or absent for the affected entries, not in the file on disk.

- **Retype `shape_mesh.make_shape_mesh`'s geometry dispatch** (moved from `block_mesh_renderer._make_shape_mesh` when the Qt-free geometry split into `ui/panels/shape_mesh.py`) — it currently dispatches on dict keys (`box`, `boxes`, `centre`+`radius`, `p1`+`p2`+`radius`, `origin`+`i`+`j`+`k`, `stl_path`, `planePoint`+`planeNormal`, ...) duck-typed at the call site; this was deliberately left as-is in both refactors. A typed geometry union (e.g. per-kind dataclasses) would let mypy check the dispatch instead of relying on key presence at runtime.

### Deferred review findings (undo/redo, sampling)

Low-severity items surfaced by a code review of the undo/redo and sampling work and left unfixed at the time (each was judged *plausible* rather than confirmed — narrow trigger, latent, or design-hardening). Worth folding into the next change that touches these areas:

- **`_restored_dirty` re-reads disk to settle dirtiness** (`ui/mixins/_undo_ops.py`) — originally filed as a live defect on the theory that a root cached in `state.parsed_roots` has no `raw_text` and so re-serializes to text differing from disk. That theory does not hold: every writer of `parsed_roots` populates it from `OpenFoamParser.parse()`, which sets `raw_text`, and `tools/roundtrip_corpus.py` measures 9620/9620 v2512 tutorial files re-serializing byte-identical. `_undo_text_for` also prefers `file_buffers`, so the serialize-vs-disk comparison is only reached for files parsed straight from disk. Downgraded to a design note: comparing against the in-memory buffer would remove the I/O and the dependence on a 100% round-trip, but there is no known input that makes the current code wrong.
- **`UndoState.op_active` reset timing is fragile** (`ui/mixins/_undo_ops.py`) — the double-checkpoint guard is cleared by `QTimer.singleShot(0, ...)`, which fires inside a nested event loop (`QMessageBox`/`QDialog.exec`). No current call site opens a dialog between its `_checkpoint_for_undo` and the mutation, so this is latent; a future op that does would let the model's `about_to_change` push a second, mid-mutation snapshot (one edit then needing two undos). Bounding the guard to the synchronous op scope (e.g. a context manager) would remove the timing coupling.
- **No enforcement that a mutation path checkpoints for undo** (`ui/mixins/_tree_crud_ops.py`, `_tree_sync_ops.py`, `_boundary_ops.py`) — undo coverage rests on ~18 hand-placed `_checkpoint_for_undo` calls plus the `about_to_change` signal for `setData`-driven edits. A future direct-mutation path that forgets its explicit call is silently non-undoable (a later Ctrl+Z jumps past it). A single post-mutation choke point that diffs the prior serialized text, or a coverage test, would make this robust.

## Acknowledgements

- [PyInstaller](https://pyinstaller.org/) — Used to build standalone executables.
- [pyVista](https://pyvista.org/) / [VTK](https://vtk.org/) — 3-D viewer for `blockMeshDict` (BSD-3-Clause, optional).
- [pytest](https://pytest.org/) / [pytest-qt](https://pytest-qt.readthedocs.io/) — Test framework.

Special thanks to the [OpenFOAM Foundation](https://openfoam.org/) and [OpenCFD / ESI Group](https://www.openfoam.com/) and all contributors for developing and maintaining OpenFOAM as free, open-source CFD software.
