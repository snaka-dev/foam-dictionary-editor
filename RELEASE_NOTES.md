# Release Notes

## v1.9.0 — 2026-07-22

### New features

- **Undo/redo for tree edits** — every tree-side change is now undoable with **Ctrl+Z** / **Ctrl+Shift+Z** while the tree has focus (also in the tree context menu as **Undo Tree Edit** / **Redo Tree Edit**): inline cell edits, Detail-panel applies, Paste Value, Add/Duplicate/Delete/Comment Out/Restore from Comment, "Use this value" from compare mode, **Apply Text to Tree**, BlockMesh vertex drags, and the Boundary tab's patch operations. Multi-file boundary operations (e.g. renaming a patch across all `0/` fields) undo as a single step that restores every touched file. Undo is one global history for the session (up to 50 steps, cleared on a case switch): Ctrl+Z reverses the most recent change wherever it happened and switches to the affected file if needed; the text editor keeps its own native undo for free-form typing, and the delete confirmation no longer claims deletion "cannot be undone" — it can.
- **Sampling overlay in the 3-D viewer (`sample ▾`)** — the BlockMesh panel gained a fourth overlay source: sampling definitions are drawn in teal on the block mesh, so probe positions and sample lines/planes can be checked against the geometry before running. Probe points (`probes`/`patchProbes`/`boundaryProbes` `probeLocations`) render as markers, `sets`-type sample lines (`lineUniform`, `lineCell`, `uniform`, `face`, … — anything with a `start`/`end` pair, plus `cloud` point lists) as thin tubes, and `surfaces`-type `plane`/`cuttingPlane` members as display-extent discs. Definitions are read from `controlDict`'s `functions {}` block **and** from standalone sampling dicts — `system/sample`, `system/probes`, `system/surfaces`, `system/singleGraph` (including the `.org` style with top-level `start`/`end`) — which now also appear in the file list; several files contribute at once and each menu row is tagged with its source file. Both member-list syntaxes are supported — the dictionary form `sets { … }` and the classic parenthesised list form `sets ( y0.1 { … } … );`, which the parser now also turns into a real editable tree (named entries instead of an opaque raw block), diffable in compare mode like `regions ( … )`. Non-drawable entries (e.g. `patch` surfaces) are listed under **Non-geometric sources (N)**, and the usual overlay clipping ("✂ clipped") applies. Like the other overlay dicts, these files enable the `⊞` side-by-side view.
- **View Log Summary now condenses solver logs** — a `log.simpleFoam`, `log.interFoam`, … written by an `Allrun` run (or any hand-run solver tee'd to a `log.*` file) no longer falls back to the generic last-20-lines tail: the Summary tab now reports the number of time steps and the simulated time range, the final `ExecutionTime`/`ClockTime`, a convergence line when the run converged, and the last step's residuals (initial/final residual and iteration count per field, Courant number(s), cumulative continuity error). Solver logs are recognised by their time-loop shape (`Time = …` steps plus `Solving for …` residual lines) rather than by executable name, so any solver from either OpenFOAM fork works. A run that neither converged nor reached `End` is reported as FAILED, so an aborted run is visible at a glance.
- **Options dialog for the Tools-menu "Run *" actions** — **Run blockMesh… / Run snappyHexMesh… / Run topoSet… / Run setFields… / Run checkMesh…** no longer fire immediately: each now opens a small options dialog with the tool's most common flags as checkboxes and fields (blockMesh/topoSet/setFields: `-dict` with a case-relative **Browse…** and `-region`; snappyHexMesh: additionally `-overwrite`, checked by default; checkMesh: `-allGeometry`, `-allTopology`, `-writeSets` format, `-region`), a free-text **Extra options** field for everything else, and a live **Command** preview showing the exact command line — including the automatic `2>&1 | tee log.<tool>` redirection, which stays out of the user's hands so **View Log Summary** and the Allrun pre-flight keep finding the logs. **Run** is the default button, so Enter runs with the defaults and the flow costs no extra clicks compared to the old confirmation boxes — those pre-flights moved into the dialog: the "case already has results in …" warning appears at the top for the mesh tools, and setFields' three-way "restore 0/, then run" choice became a **Restore 0/ from 0.orig/ first** checkbox (checked by default when `0.orig/` exists) whose `rm -rf 0 && cp -r 0.orig 0 && ` prefix shows up in the preview. Option values are remembered per tool for the rest of the session, and a malformed Extra field (an unbalanced quote) disables Run instead of sending a broken command.
- **Duplicate a tutorial case from Find OpenFOAM Examples** — the Find OpenFOAM Examples dialog gained a **Duplicate this case…** button (enabled, like **Compare with this case**, when the hit lies inside a tutorial case). It opens the familiar Duplicate Case dialog with the tutorial as the source, completing the "search a keyword → find a tutorial that uses it → start my own case from it" workflow without a manual `cp -r` from the installation. The suggested destination is the default case directory (falling back to the home directory — never the read-only installation), the default copy mode is a full directory copy so `Allrun` scripts, `0.orig/`, and `constant/triSurface/` geometry come along, and after copying FoDE offers to open the new case immediately. The **Find OpenFOAM Examples…** action itself is now also listed in the **Case** menu, next to the other Duplicate actions (the same action in both places), since it doubles as a way to start a new case.

### Bug fixes

- **Regenerating one entry of a named parenthesised block no longer drops its siblings' names**: in `regions ( … )` (setFieldsDict), `boundary ( … )` (blockMeshDict), and the new `sets`/`surfaces` lists, an entry's stored raw text began at its `{` — so editing one entry in the tree made every *unmodified* sibling lose its name when the file text was regenerated, corrupting the dictionary. An entry's raw span now starts at its name token (tree-to-editor line highlighting now covers the name line too).
- Fixed a **stale comparison surviving a case switch**: opening a different case while a Compare-with-Case comparison was active left the diff bar, the reference-case parse cache, and the file-list diff marks pointing at the previous case's reference. Opening a different case now clears the comparison; **Reload Case** (same directory) keeps it armed and recomputes the diff marks instead.
- Compare mode no longer **fails silently when a reference file cannot be parsed**: the comparison view used to just go blank, indistinguishable from "no differences". A status-bar warning now names the unparseable reference file, and the background scan that computes per-file diff counts reports how many reference files it had to skip.
- **Configuration files are now written atomically** (temp file + rename): a crash or full disk mid-save can no longer truncate `app_config.json`, a case's `.foam-editor-files.json`, or the generated `foam_keywords.json` to an empty/partial file that would previously have been silently discarded on the next start.
- **Dotted identifiers no longer split by the syntax highlighter** — a set name such as `y0.1` used to render its `y0` prefix in keyword colour with the trailing `.1` plain, because keyword rules matched on a `\b` boundary that falls between a digit and a dot. Keyword rules are now lookaround-guarded like the number rule; the same fix covers structural keywords (`off.1`) and shell keywords (`config.fi`).

### Improvements

- **Transparent gzip support for triSurface files in the BlockMesh 3-D viewer** — `snappyHexMeshDict` `triSurfaceMesh`/`distributedTriSurfaceMesh` geometry now resolves `.gz`-compressed surface files automatically, matching how OpenFOAM tutorials ship them (e.g. `constant/triSurface/motorBike.obj.gz`): a dict entry naming the plain file resolves to a `.gz` sibling when that's the only one on disk, and a `.gz`-named reference falls back to an uncompressed file when present. The manual **Load STL / OBJ…** file dialog now also opens `.stl.gz`/`.obj.gz`/`.stlb.gz` files directly.
- The **Case Library now also finds the tutorials of a sourced OpenFOAM environment via `$WM_PROJECT_DIR`** when `$FOAM_TUTORIALS` itself is not exported, matching how Find OpenFOAM Examples already discovered installations.

### Documentation

- **New screenshot gallery** (`docs/SCREENSHOTS.md` / `docs/SCREENSHOTS_ja.md`) — an annotated tour of the main window, the BlockMesh 3-D viewer's `topoSetDict`/`snappyHexMeshDict` overlays (topoSetShapes, floatingObject, and motorBike cases), and the Find OpenFOAM Examples dialog and Tools menu, linked from `README.md`, `USER_GUIDE.md`'s "Where to Find Things" table, and `DEVELOPER.md`'s documentation map.

### Internal

- The three extractor shape dataclasses now share one field-naming scheme: `label` (display name) + `kind` (geometry/source keyword) replace `TopoShape.source`, `SnappyShape.name`/`geo_type`, and `SetFieldsShape.source`. This let the near-duplicate topoSet/setFields renderer methods collapse into one shared `_render_source_shapes` and removed the Export-STL dialog's `source_or_geo_type` bridging field. No user-visible change.
- Single source of truth for reading the sourced OpenFOAM environment: the three separate `WM_PROJECT_DIR`/`FOAM_*` readers in `example_search`, `keyword_generator`, and `AppConfigManager.foam_tutorials_dir` now share `services/foam_env.py`.
- The topoSet/snappyHexMesh box-geometry resolution was unified into `foam/tree_utils.resolve_box_geometry`, and topoSet/sampling point-and-normal plane resolution into `foam/tree_utils.resolve_plane_geometry` (joining the existing shared sphere/cylinder/cone resolvers), and the duplicated installation-combo + Browse… code of Find OpenFOAM Examples and Generate OpenFOAM Keywords became a shared `InstallationSelector` widget.
- `--variant` presets now go through a proper `AppConfigManager.set_features()` API instead of poking a private attribute.
- New unit tests: direct coverage for `foam/tree_utils.py`'s resolvers, service-level tests for `services/case_copier.py`, env-discovery tests for `services/foam_env.py`, atomic-write tests for `app_config/json_io.py`, and a regression test for the comparison-state reset on case change.

## v1.8.0 — 2026-07-15

### New features

- **Case-root `All*` scripts in the file list** — `Allrun`, `Allrun.pre`, `Allclean`, and any other `All*` script at the case root now appear automatically under a new **case root** group at the bottom of the file list, so the scripts the Tools menu executes can be inspected and edited without leaving the app. Only `All*` files are listed — logs, `*.foam` files, and results stay hidden as before. Scripts open as shell scripts, not dictionaries: the editor switches to a shell-highlighting mode (`#` comments, strings, `$variables`, OpenFOAM helpers like `runApplication`/`runParallel`, and utility/solver names from the regular keyword list), the tree view stays empty, **Apply Text to Tree** has no effect, and compare mode skips them; editing and saving preserve the executable permission. As a side effect, **Duplicate Case** / **Save As New Case** now include the scripts, so copies remain runnable via **Tools > Run Allrun Script** — previously they were silently dropped. Two related refinements: hidden files (dotfiles such as the app's own `.foam-editor-files.json`) are now always excluded from extra-directory scans and the Add-files dialog, and `log.*` run logs — when listed via an extra directory — are shown dimmed and open as plain text at any size instead of being fed to the dictionary parser (the >100 KB warning dialog's "tree view will not be available" promise is now actually kept). The **case root** header offers the same right-click menu as other directory headers (**New file in 'case root'...** / **Add files from 'case root'...**), so specific root files such as a run log or a `README` can be listed opt-in without registering the whole root directory.
- **BlockMesh 3-D panel: wrapping toolbar and free side-by-side resize** — the panel's top controls (Vertices ▾, Blocks ▾, the overlay menus, Refresh, STL ▾, Scale ▾, label size, view buttons) now live in a single wrapping toolbar: when the panel is wide they fit on one line, and when it is narrow they flow onto additional lines instead of dictating a ~700 px minimum panel width. In side-by-side mode the splitter no longer snaps the 3-D pane closed when dragged past that minimum — both panes are non-collapsible and the 3-D view can be narrowed smoothly down to a small usable width (150 px), with the mouse-hint line and the Preview banner word-wrapping instead of blocking the resize.
- **setFieldsDict regions in the BlockMesh 3-D panel** — loading or editing `setFieldsDict` now overlays its `regions ( … )` list on the 3-D panel, alongside the existing `topoSetDict`/`snappyHexMeshDict` overlays. Region sources reuse topoSet's geometry keywords, so the same shapes render (box, multi-box, rotated box, sphere, cylinder, cone — with the same `$variable`/`#eval{ expr }` resolution); each shape is drawn in orange and labelled with the entry's `fieldValues` summary (e.g. `alpha.water=1`). A new **setFields ▾** menu mirrors the topoSet/snappyHexMesh ones (master toggle, Show/Hide all, per-shape checkboxes, and a Non-geometric sources submenu for entries like `zoneToCell`), the shapes join **Export Shapes as STL…** as a third group, and the panel's ⊞ side-by-side toggle now also enables when `setFieldsDict` is the active file.
- **Oversized overlay shapes are clipped to the block mesh** — a `setFieldsDict` region such as damBreak's `box (0 0 -1) (0.1461 0.292 1)` extends far beyond the block mesh and used to dwarf it in the 3-D view. All overlay shapes (topoSet, snappyHexMesh, and setFields) are now clipped — for display only — to the block-mesh bounding box expanded by 10% per axis, and a clipped shape's scene label carries a "✂ clipped" mark so the cut is not mistaken for its real extent. A shape lying entirely outside the block mesh is kept unclipped and labelled "⚠ outside block mesh"; one whose volume encloses the whole scene (so no part of its surface is visible inside) is drawn as its bounding-box overlap instead of disappearing. **Export Shapes as STL…** always writes the full, unclipped geometry.
- **Run setFields / Run checkMesh** — two more Tools-menu actions running in the Terminal tab. **Run setFields** runs `setFields`, teeing to `log.setFields`; because setFields overwrites the `0/` field files in place (re-running it on already-set fields compounds the values), on a case with `0.orig/` it offers **Restore 0/, then run** (`rm -rf 0 && cp -r 0.orig 0 && setFields …`), **Run anyway**, or **Cancel** — and a plain confirmation on a case without `0.orig/`. **Run checkMesh** validates the mesh and tees to `log.checkMesh` with no confirmation (it only reads the mesh). Both logs show up in **View Log Summary** via its generic log parser.
- **Version number in Help > About** — the About dialog now shows the application version under the title. The number comes from a single source of truth (`_version.py`); in a git checkout it is enriched with a short dev suffix (commits past the last tag + commit hash, `*` if the tree is dirty, e.g. `1.7.0 (dev+12, ge75192d*)`) so bug reports can pinpoint the exact build, while installed copies show the plain release number.
- **`constant/polyMesh` presence/staleness indicator** — the file list now shows a `constant/polyMesh: N cells` row (cell count read from the `owner` file's `FoamFile` header note, no mesh parsing needed) whenever a mesh is present. The indicator turns amber and reads "stale (blockMeshDict changed since last run)" when `blockMeshDict` has been modified more recently than the mesh was generated.
- **snappyHexMeshDict geometry in the BlockMesh 3-D panel** — loading or editing `snappyHexMeshDict` now overlays its `geometry {}` block on the 3-D panel, independent of `blockMeshDict`/`topoSetDict`. Supported entry types: `box`, `sphere` (including an ellipsoid when `radius` is given as a per-axis vector, e.g. an igloo-shaped dome), `cylinder`, `cone`, `triSurfaceMesh`/`distributedTriSurfaceMesh` (the referenced STL/OBJ file is loaded automatically from `constant/triSurface/`), and box-based `collection`/searchableSurfaceCollection members (each placed instance is drawn as its own scaled/rotated/translated box). Each shape is classified as a **surface**, **region**, or plain **geometry** by cross-referencing `castellatedMeshControls.refinementSurfaces`/`refinementRegions` — including regex-pattern surface-name keys such as `"iglo.*"` — and colour-coded accordingly (teal / purple / grey). `locationInMesh` and the multi-region `locationsInMesh` are drawn as labelled keep-point markers. A **"snappyHexMesh ▾"** menu toggles the whole overlay and lets you show or hide each shape individually, with a category-colour legend and greyed-out entries for geometry that couldn't be resolved (e.g. a missing STL file, or a `collection` with no resolvable box member). Top-level `$variable` definitions and `#eval{ expr }` expressions are resolved the same way as in `blockMeshDict`/`topoSetDict`.
- **More topoSetDict sources rendered in the BlockMesh 3-D panel, and a scalable topoSet ▾ menu** — the `topoSetDict` overlay now understands far more of the real-world source syntax (on OpenFOAM v2606's kitchen-sink `pisoFoam/RAS/cavity` tutorial dictionary, 21 of 67 actions now render, up from 6, and none are silently dropped any more). Newly recognised: the `min`/`max` and multi-box `boxes ( … )` forms of `boxToCell/Face/Point`; spheres declared with `origin` (OpenFOAM's primary keyword — previously only the `centre` compat alias was found) and hollow spheres via `innerRadius`; point-carrying sources drawn as labelled markers (`nearestToCell`/`nearestToPoint` `points`, `regionToCell` `insidePoints`/`insidePoint`, `regionToFace` `nearPoint`); and `planeToFaceZone`, drawn as a disc sized to the scene bounds. To keep the **topoSet ▾** menu usable with 60+ actions, it gained **Show all shapes** / **Hide all shapes** actions and now collects the entries with no drawable geometry under a **Non-geometric sources (N)** submenu instead of a long greyed-out list; the **snappyHexMesh ▾** menu got the same two improvements for consistency. Point-marker and plane shapes are excluded from **Export Shapes as STL…** (they have no meaningful STL surface). The bundled `tutorials/topoSetShapes` demo case showcases all the new forms.
- **Run snappyHexMesh / Run topoSet** — Tools menu actions mirroring the existing "Run blockMesh": each sends the command to the Terminal tab and tees its output to `log.snappyHexMesh` / `log.topoSet` in the case directory, warning first if the case already has numeric result directories that re-running may invalidate.
- **Run Allrun Script / Run Allclean Script / Clean Case (foamCleanTutorials)** — three more Tools-menu actions running in the Terminal tab. **Run Allrun Script** runs the case's `./Allrun` (the full workflow, solver included); since OpenFOAM's `runApplication`/`runParallel` helpers skip any step whose `log.*` file already exists, on an already-run case the action offers **Clean, then run** (`foamCleanTutorials && ./Allrun`, the standard `./Allclean && ./Allrun` idiom), **Run anyway**, or **Cancel** instead of appearing to do nothing. **Clean Case** runs `foamCleanTutorials`, which uses the case's own `Allclean`/`Allwclean` script when present and otherwise removes the mesh, time directories, `processor*/`, `postProcessing/`, and `log.*` files — plus `0/` when `0.orig/` exists (the standard `-auto` tutorial convention); the confirmation dialog states exactly which of these will happen. **Run Allclean Script** runs `./Allclean` directly for when the script itself is wanted explicitly. All three warn before doing anything destructive and are disabled without a case or terminal panel.
- **Export Shapes as STL** — a new **STL ▾ → Export Shapes as STL…** action in the BlockMesh 3-D panel opens a dialog listing every renderable `topoSetDict`/`snappyHexMeshDict` shape currently loaded (parametric box/sphere/cylinder/cone/rotated-box shapes as well as `triSurfaceMesh`/collection-derived ones), each with a checkbox defaulting to its current 3-D-view visibility. Pick an output folder and each checked shape is written as its own `.stl` file, named after its label/name (de-duplicated on collision); shapes with no drawable geometry are reported as skipped rather than failing the export.
- **Find OpenFOAM Examples** — a new, non-modal Tools-menu dialog for finding real usage examples of a keyword or setting without `find`/`grep`. It searches both the tutorial cases (`tutorials/`) and the curated templates under `etc/caseDicts/` (including the `postProcessing/` function-object templates usable via `#includeFunc`) of a local OpenFOAM installation. Installations are taken from the environment (`WM_PROJECT_DIR`/`FOAM_TUTORIALS`/`FOAM_ETC`) when sourced, and otherwise auto-discovered in the usual install locations (`/usr/lib/openfoam/`, `/opt/`, `~/OpenFOAM/`) with a version selector; a custom directory can be browsed to and is remembered across sessions. Results are grouped by tutorial case / template folder, filterable by file name (`controlDict`, `fvSchemes`, …), and shown in a syntax-highlighted, read-only preview scrolled to the first matching line. From there you can copy the file or just the selected snippet to the clipboard (separate **Copy File** / **Copy Selection** buttons) — or, when the hit lies inside a tutorial case, click **Compare with this case** to load that case straight into the existing Compare-with-Case view, where the right-click **Use this value** action lets you adopt individual settings into your own case.
- **View Log Summary** — a new, non-modal Tools-menu dialog that condenses a `log.*` file (blockMesh, snappyHexMesh, topoSet) into a short report instead of the raw text: final mesh stats and iteration counts per phase, the final per-patch layer-thickness table, one line per topoSet cell/face/point set, and de-duplicated warnings with a repeat count (fatal errors are always shown in full). A "Raw Log" tab keeps the untouched text a click away. Being non-modal, it can stay open beside the tree/editor while you cross-reference dictionary settings against the log's results. Closing it (rather than leaving it open) no longer leaves it stuck invisible when reopened, and opening a different case re-points it at that case's most-recent log automatically, just like the rest of the app's panels.
- **Deeper syntax-highlighter keyword extraction, with a selectable installation** — the keyword scanner behind **Settings > Generate OpenFOAM Keywords…** now also greps the `src/` and `applications/` sources for dictionary-read calls (`lookup("…")`, `get<…>("…")`, `readEntry("…")`, …), which is where free-form dictionary keys such as `controlDict`'s `application`, `writePrecision`, or `timePrecision` are actually named — none of these appeared in the caseDicts templates or `TypeName` macros scanned before. The bundled keyword list was regenerated with the new scan (≈3,100 → ≈5,200 keywords), so those keys now highlight out of the box. The dialog also gained the same auto-discovering **Installation** selector as Find OpenFOAM Examples (shared remembered directory), so a keyword list can be built from any installed version without sourcing an OpenFOAM environment first — the CLI equivalent is `tools/generate_foam_keywords.py --dir <install-root>`. The generated JSON now records provenance (`source`, `version`, `generated`, and a license `note` — the file contains keyword identifier names only).
- **Bundled default keyword list split from the user-generated one** — the shipped baseline now lives in `app_config/foam_keywords.default.json` (tracked in git, currently built from OpenFOAM v2512), while **Generate OpenFOAM Keywords…** keeps writing to `app_config/foam_keywords.json`, which is now gitignored and simply overrides the default when present. Regenerating the list no longer dirties a git checkout, and deleting the user file reverts to the bundled default.

### Bug fixes

- Fixed **Boundary faces** appearing to do nothing on quasi-2-D cases (e.g. damBreak): such cases list only their thin side walls under `boundary`, while the large front/back faces belong to blockMesh's implicit `defaultFaces` patch and were never drawn. Unassigned exterior block faces are now extracted as `defaultFaces` and rendered as fainter grey faces whenever **Boundary faces** is checked, so the checkbox has a visible effect on 2-D cases too.
- **View Log Summary…** is now listed in the **View** menu as well as **Tools** (the same action in both places) — users reasonably look for anything starting with "View" under the View menu.
- Added the missing Japanese translations for the Tools menu (the menu title, every action label and tooltip, and the confirmation/warning dialogs of Restore 0/, Run blockMesh/snappyHexMesh/topoSet, and Open Mesh in ParaView), plus **Settings > Generate OpenFOAM Keywords…** and the BlockMesh side-by-side toggle's tooltip — these previously appeared in English in Japanese mode.
- Fixed **Use this value** (compare mode) mishandling unnamed entries such as `#includeFunc …` directives: because directives have no key name, the action used to target the enclosing block itself and could overwrite an entire `functions {}` dictionary with the single directive line. Unnamed entries are now appended into the correct block by content, with an identical entry detected and skipped instead of duplicated. The action also no longer refuses when the entry's enclosing block is missing from the current case — missing parent dictionaries (e.g. `functions {}`) are created automatically, so a setting found in a reference/example case can be adopted even by a case that never had that block.
- Fixed `save_file()` / `save_all_files()` not refreshing disk-derived file-list indicators (including the new mesh staleness flag) after rewriting a file in place. `QFileSystemWatcher.directoryChanged` only fires on directory-entry add/remove, not in-place rewrites, so both save paths now call `_reload_file_list()` directly.
- Fixed the BlockMesh 3-D panel's **⊞** side-by-side toggle only enabling when `blockMeshDict` was the active file, even though the panel already overlays `topoSetDict`/`snappyHexMeshDict` geometry onto the same view. It now also enables for those two file types.
- Fixed `topoSetDict`/`snappyHexMeshDict` overlay state (shapes, per-shape menu checkboxes, keep-point markers, and the **Export Shapes as STL…** action's enabled state) not being cleared when opening a different case. Opening a new case directory was resetting only the panel's internal shape lists directly instead of calling its own `clear()`, so the previous case's per-shape menu entries, `locationInMesh`/`locationsInMesh` markers, and 3-D overlay kept showing until a `topoSetDict`/`snappyHexMeshDict` from the new case happened to be loaded.
- Fixed the Editor's number highlighting bleeding into identifiers: digits glued to a word — the `0` in a patch name like `wall0`, the `1` in `inlet-1`, or the leading `0` in `0wall` — were coloured teal as if they were standalone numbers. The number rule is now boundary-guarded on both sides; real numbers (`0.05`, `-1e-05`, vector components) are unaffected.
- Fixed **Settings > Generate OpenFOAM Keywords…** spuriously marking the current file dirty (`*` in the title) just by opening and closing the dialog. The rehighlight that runs afterwards fires Qt's `textChanged` even though only formatting changed; it now goes through the editor panel's programmatic-update guard (the same one the Highlight toolbar toggle already used), so only real edits mark the file dirty.
- Fixed the Simple terminal starting in the application's own directory instead of the case directory after switching back from xterm mode. The replacement terminal widget was told the case directory while its shell process was still starting up, and the `cd` command was silently skipped because the process was not yet in the `Running` state. The command is now issued whenever the process is not `NotRunning` — `QProcess` buffers writes made during startup and flushes them once the shell is up.
- Fixed **Apply Text to Tree** not refreshing the `snappyHexMeshDict` 3-D overlay: the apply path carried its own copy of the file-name → viewer dispatch and it was missing the snappyHexMesh case, so geometry edited in the text editor only appeared in the 3-D view after saving the file or editing via the tree. All load/save/tree-edit/apply paths now share a single dispatch helper.

### Documentation

- **Easier feature discovery in the manuals** — `USER_GUIDE.md`'s "Where to Find Things" table grew from 27 to 41 task-oriented rows (e.g. viewing `topoSetDict` geometry in 3-D, checking all boundary conditions at a glance without opening each field file, exporting shapes as STL, renaming a patch everywhere, plotting residuals with foamMonitor), and its Contents list now includes the previously missing Tools sections, **Generate OpenFOAM Keywords**, **Bundled example cases**, and the BlockMesh-panel subsections. `README.md`'s Key Features section was condensed into a compact overview whose group headings deep-link into the corresponding user-guide sections; the Tools actions that don't require the terminal moved out of "Integrated terminal" into their own **Tools menu** group, and the missing Allrun/Allclean/Clean Case actions were added. `DEVELOPER.md` gained a documentation-map subsection (which document covers what, plus the rule that new user-visible features must also be added to the guide's "Where to Find Things" table and Contents list) and now lists `tutorials/` and the developer/release-notes files in the project-structure tree.
- **Published SoftwareX citation** — the README's Citation section and top banner now carry the full reference for the published article — *SoftwareX*, Volume 35, 2026, 102852, [doi:10.1016/j.softx.2026.102852](https://doi.org/10.1016/j.softx.2026.102852) — replacing the "accepted, details coming soon" placeholder.

### Internal

**Refactor: shared JSON config helper**

- Added `app_config/json_io.py` (`load_json`/`save_json`) and switched `AppConfigManager` and `CaseFilesConfig` to use it instead of each hand-rolling the same read/tolerate-corruption/write logic. No functional change.

**Refactor: split `snappyHexMeshDict` schema into a package**

- `schemas/snappy_hex_mesh_dict.py` (776 lines, 70 keys) is now `schemas/snappy_hex_mesh_dict/`, a package with one submodule per subdomain (geometry, castellated mesh, snap controls, layers, mesh quality) merged in `__init__.py`. The `schemas.snappy_hex_mesh_dict` import path used by the schema registry is unchanged. No functional change.

**Refactor: `AppState` diff fields → `DiffState` sub-dataclass**

- `AppState.diff_case_dir` and `diff_parsed_roots` are now nested under a `DiffState` sub-dataclass (`AppState.diff`), matching the existing `FoamMonitorState` pattern. No functional change.

**Widened `ruff`/`mypy` scope**

- `ruff` and `mypy` now also cover `app_config/`, `schemas/`, `services/`, and `ui/app_state.py`, in addition to the existing `foam/` and `model/` scope. Fixed the pre-existing lint/type issues in those directories needed to pass cleanly (line-length wrapping in a few schema description strings, two missing type annotations). The rest of `ui/` remains excluded.

**Refactor: deduplicate UI plumbing and share extractor/formatting helpers**

- BlockMeshPanel's `topoSet ▾` / `snappyHexMesh ▾` menus — previously two parallel families of ~25 attributes with mirrored rebuild/visibility methods — are now two instances of a single `_ShapeOverlayMenu` helper class. Only behavioural difference: the snappy location-point toggles now follow the master toggle's enabled state immediately instead of on the next rebuild.
- The Tools-menu run actions share `_run_in_terminal()` / `_confirm_rerun_over_results()` helpers, the menu construction is loop-driven, and a shared `_confirm()` yes/no helper replaces the repeated `QMessageBox.question` blocks.
- `ui/mixins/_boundary_ops.py` gained `_find_boundary_field` / `_append_new_patch` / `_set_patch_children` helpers, replacing five copies of the boundaryField lookup and the repeated patch-creation/replacement blocks.
- Leaf-value formatting is shared: `foam/utils.py`'s new `format_leaf_value()` is used by both the writer and the tree model's Value column, so display and serialisation can no longer drift.
- The sphere/cylinder/cone geometry resolution duplicated between `foam/topo_set_extractor.py` and `foam/snappy_hex_mesh_extractor.py` moved into shared resolvers in `foam/tree_utils.py` (`resolve_sphere_geometry`, `resolve_cylinder_geometry`, `resolve_cone_geometry`).
- Encapsulation: `FoamTreeModel.index_of_node`/`attach_parents` and `BlockMeshPanel.init_plotter` are public now that other modules call them; `FileListPanel` gained a `file_paths()` accessor so the diff precompute no longer reaches into its private list widget.
- `i18n.tr()` now looks translations up in a table cached at `set_language()` time instead of re-importing the language module on every call.

## v1.7.0 — 2026-07-04

### New features

- **topoSetDict `actions` block** is now parsed as a structured tree instead of opaque raw text. Each anonymous `{ … }` entry becomes an `action_entry` node whose children (`name`, `type`, `action`, `source`, `box`, `set`, etc.) are individually visible and editable in the tree view. Diff comparison uses positional matching across action entries.
- **Syntax highlighting in the text editor** — the plain-text editor now colours OpenFOAM dictionary tokens: `//` and `/* */` comments (grey italic), string literals (green), `#directives` (purple bold), `$macro` references (orange), reserved keywords such as `FoamFile`, `true`/`false`, `uniform`, `nonuniform` (blue bold), and numbers (teal). No new dependency — implemented with PySide6's built-in `QSyntaxHighlighter`.
- **Code folding in the text editor** — the line-number gutter now shows a clickable ▾/▶ triangle for every `{ … }` block that spans more than one line, as well as for every run of two or more continuous comment lines (a multi-line `/* … */` block or consecutive `//` lines). Click the triangle to collapse or expand the region. The `FoamFile { … }` header and the top-of-file comment banner are both collapsed automatically when a file is loaded. Folding is visual only; the underlying text is unchanged.
- **topoSetDict geometry in the BlockMesh 3-D panel** — loading or editing `topoSetDict` now overlays the geometry sources of each action on the 3-D panel. Supported source types: `boxToCell/Face/Point` (box), `sphereToCell/Face/Point` (sphere), `cylinderToCell/Face/Point/AnnulusToCell` (cylinder), and `coneToCell/Face/Point` + `coneAnnulusToCell` (truncated cone — a true cone when `radius2` is 0). Both the modern `point1`/`point2` and the legacy `p1`/`p2` axis-point key names are accepted for cylinders and cones. Shapes are colour-coded by action type (`new` = steel-blue, `add` = green, `subtract`/`delete` = red, `subset` = purple, `invert` = gold) and rendered semi-transparently so the underlying mesh remains visible. A **"topoSet ▾"** menu in the panel toolbar toggles the whole overlay and lets you show or hide each shape individually (one entry per action, listed by `name · source`). Top-level `$variable` definitions and `#eval{ expr }` expressions inside `topoSetDict` are resolved before extraction (the same mechanism as in `blockMeshDict`).

### Bug fixes

- Fixed syntax-highlighting failing silently (invalid `QRegularExpression` — "regular expression is too large") after regenerating the keyword list with the extended scanner. The highlighter now splits the value-keyword alternation into 1,000-keyword chunks compiled as separate `QRegularExpression` objects, making it immune to PCRE2's compiled-code size limit regardless of how large the keyword list grows.
- Fixed `_on_patch_edit_requested`, `_on_patch_paste_requested`, `_on_patch_delete_all_requested`, and `_on_patch_add_all_requested` in `ui/mixins/_boundary_ops.py` importing a non-existent `_extract_boundary` from `ui.panels.boundary_view_panel`; corrected to import `extract_boundary` from `model.boundary_model`.
- Fixed the **Side by side** checkbox in the Compare Cases diff bar having no effect when opening a comparison. The checkbox was initialised as checked before its signal was connected, leaving it stuck at `True`; `_compare_with_case` calling `setChecked(True)` on an already-checked box was a no-op so the comparison panel never appeared.
- Fixed **Generate OpenFOAM Keywords** producing an invalid `QRegularExpression` pattern when the scanned keyword list contained tokens with regex-special characters (e.g. `CoProcessor()`, `Pipeline:`). The generator now requires a full identifier match (`^[A-Za-z]\w+$`); the highlighter loader applies the same filter so an already-generated file is cleaned on the next startup without regeneration.
- Fixed the **"Vertices ▾"**, **"Blocks ▾"**, **"Scale ▾"**, and **"topoSet ▾"** dropdown menus in the BlockMesh 3-D panel closing after every single click, making it tedious to toggle more than one checkbox at a time (e.g. isolating several topoSet shapes). These menus now stay open when a checkable item is clicked; they still close on an outside click, Escape, or re-clicking the toolbar button.
- Fixed editing a value directly in the **Tree panel** (inline cell editing) not marking the file as unsaved and not updating the text editor, even after **Reload from Tree**. Editing the same value through the Detail panel worked correctly. The tree model's `dataChanged` signal is now connected to the same follow-up used elsewhere (regenerate editor text, mark dirty), so inline tree edits behave the same as Detail-panel edits.

### Improvements

- **Per-shape topoSet visibility** — the topoSet overlay control in the BlockMesh 3-D panel is now a **"topoSet ▾"** menu: alongside the master **Show topoSet geometry** toggle it lists every shape from the loaded `topoSetDict` (by `name · source`) with an individual checkbox, so you can isolate or hide individual box/sphere/cylinder/cone sources. The list resets to all-visible when a new `topoSetDict` is loaded. The menu also carries an **action-colour legend** (`new`, `add`, `subtract`, `subset`, `invert`) and each shape row shows a colour swatch matching its action, so the menu maps directly onto the colours drawn in the 3-D view.
- **Hollow topoSet annuli, `rotatedBox`, and non-geometric source listing** — in the BlockMesh 3-D panel, `cylinderAnnulusToCell` and `coneAnnulusToCell` are now drawn as genuinely hollow tubes (their `innerRadius` / `innerRadius1` / `innerRadius2` are honoured) instead of solid shapes. `rotatedBoxToCell/Face/Point` (an oriented parallelepiped defined by `origin` + `i`/`j`/`k` span vectors) is now overlaid as a box. Sources that carry no drawable geometry (`cellToFace`, `zoneToCell`, `fieldToCell`, `surfaceToCell`, …) are listed greyed-out in the **"topoSet ▾"** menu as *"(no geometry)"* so their presence in the dict is still visible.
- **Syntax-highlighting toggle** — a **Highlight** button in the Editor toolbar lets you turn syntax colouring on or off with one click. The setting persists to `app_config.json` and is restored on the next launch.
- **Richer syntax-highlighting keyword list** — the **Generate OpenFOAM Keywords** scanner now also extracts `ClassName("…")` macros from C++ headers and `addNamedToRunTimeSelectionTable` / `addNamedToMemberFunctionSelectionTable` lookup names from implementation files, raising the baseline count from ~2,200 to ~3,100 keywords. Dictionary key names (`vertices`, `blocks`, `edges`, `boundary`, `dimensions`, `internalField`, `boundaryField`, `solvers`, etc.) are now highlighted dark-cyan: the caseDicts scan collects node names in addition to node values, and the highlighter extracts key segments from the schema registry at startup so common keys are covered even without regenerating the keyword file.
- **Type-safety hardening in the parser/model layer** — `FoamNode.node_type` (`foam/nodes.py`) is now a `Literal` of every value the parser/writer/tree-model actually produce, instead of a bare `str`; `mypy` (added as a dev dependency, scoped to `foam/` and `model/`) enforces it and is now checked by `tests/test_lint.py` as part of the normal test run, alongside `ruff` for linting. No functional or behavioural change.

**Extended bundled tutorial set in `tutorials/`**

- `tutorials/cavity/` is now a container for three icoFoam sub-cases taken from the OpenFOAM v2512 standard tutorial: `cavity/` (single-region walkthrough), `cavityGrade/` (non-uniform `simpleGrading`), and `cavityClipped/` (clipped geometry, `mapFieldsDict`). `Allclean`/`Allrun` scripts are included at the container level.
- Added `tutorials/damBreak/` (interFoam, laminar) from the OpenFOAM v2512 standard tutorial. Exercises `setFieldsDict` with `defaultFieldValues`/`regions` blocks, `0.orig/`, and a `sampling` function-object dictionary.
- Added four custom icoFoam `blockMeshDict` cases derived from cavity: `oneBlocks` (3-D single-block), `oneBlocks-vars` (variable substitution and compact `(blockId faceId)` face notation), `nineBlocks` (3×3 multi-block, regex boundary patches), and `nineBlocks-vars` (variables + compact notation).
- Added `tutorials/topoSetShapes/` — a `topoSetDict` demo over a single 3×3×3 block that exercises every geometry source the BlockMesh 3-D panel can overlay (`boxToCell`, `rotatedBoxToCell`, `sphereToCell`, `cylinderToCell`, a hollow `cylinderAnnulusToCell`, a truncated `coneToCell` frustum, a true `coneToCell` cone with `radius2 0`, and a hollow `coneAnnulusToCell`), plus a non-geometric `cellToFace` action, including `$variable` and `#eval` resolution. Open `system/topoSetDict` and tick **"topoSet geometry"** to see the shapes colour-coded by action.

---

## v1.6.1 — 2026-06-19

### Bug fixes

READMEs in tutorials/ is fixed and GPL license is added.

## v1.6.0 — 2026-06-19

### Improvements

**Bundled example cases in `tutorials/`**

- Two ready-to-open OpenFOAM cases are now included in the `tutorials/` directory: `cavity` (icoFoam, single-region walkthrough) and `snappyMultiRegionHeater` (chtMultiRegionFoam, multi-region).
- Cases are sourced from the OpenFOAM v2512 standard tutorial set and licensed under GPL-3.0 (separate from the AGPL-3.0 that covers FoDE source code). See `tutorials/tutorials_README.md` for provenance and license details.

**MultiRegion: field files under `0/<region>/` now listed and shown in Boundary panel**

- Field files inside `0/<region>/` and `0.orig/<region>/` (e.g. `0/heater/T`, `0/bottomWater/p`) are now included in the file list automatically, grouped under `0/<region>` headers such as `0/heater` and `0/bottomWater`.
- The **Boundary** panel Directory selector now shows one entry per region subdirectory (e.g. `0/bottomWater`, `0/heater`, `0/topAir`) in addition to `0` and `0.orig`. Selecting a region entry filters the boundary table to that region's field files.
- Previously only direct files inside `0/` and `0.orig/` were scanned; region subdirectories were silently ignored.

**BlockMesh viewer: compact `(blockIndex, faceIndex)` boundary face notation**

- The newer OpenFOAM compact boundary face notation — `(blockIndex faceIndex)` — is now supported alongside the traditional 4-vertex notation `(v0 v1 v2 v3)`.
- The compact form is expanded to a 4-vertex list using the standard hex block face table (face 0 = −x, 1 = +x, 2 = −y, 3 = +y, 4 = −z, 5 = +z). Both notations can coexist in the same file.
- Previously, compact face entries were silently dropped (the `len < 3` guard rejected 2-integer tuples), so boundary patches using the new notation were invisible in the 3-D view.

**GUI: top-bar reorganisation and Tools menu**

- Added a **Reload Case** button to the top bar, placed between **Save All Files** and the separator. The button is equivalent to **Case > Reload Case** and provides one-click access to the most common case-reload operation.
- Moved the **foamMonitor…** launcher from the top bar to a new **Tools** menu (between **Settings** and **Help**). foamMonitor is a runtime monitoring tool rather than a file-editing operation; separating it from the editing buttons makes the distinction clearer. The running-state indicator (menu item text changes to **■ foamMonitor**) and stop-by-click behaviour are unchanged.

### Bug fixes

- **BlockMesh viewer: negated-macro vertex variables now resolved** — Variable definitions of the form `xMin -$xMax;` (a leading minus sign before a `$reference`) were silently ignored by `_build_var_map` because the parser classifies them as `word` nodes rather than `macro` nodes, and the macro-resolution pass only handled `macro`-typed nodes. As a result, vertices such as `($xMin $yMin $zMin)` were missing from the 3-D view. A new word/compound arithmetic pass evaluates the substituted value as a numeric expression, so `-$xMax` resolves correctly once `xMax` is known.

- **Compare Cases: side-by-side panel now appears immediately** — The "Side by side" checkbox is checked by default. When a comparison was started, Qt's `toggled` signal was not emitted because the checkbox value was already `True`, so the comparison panel stayed hidden until the user manually unchecked and rechecked the box. Fixed by calling the toggle handler directly after `setChecked`.

### Internal

**Refactor: reorganise `ui/` into subdirectories**

- Moved 14 dialog files to `ui/dialogs/`, 7 panel files to `ui/panels/`, 3 low-level widget files to `ui/widgets/`, and the 8 `_*_ops.py` mixin files to `ui/mixins/`. The orchestrator core (`main_window.py`, `app_state.py`, `layout_constants.py`) stays at `ui/` top level. No functional change.

**Refactor: mirror source structure in `tests/`**

- Moved all test files from the flat `tests/` directory into subdirectories that match the source layout: `tests/foam/`, `tests/model/`, `tests/ui/`, `tests/services/`, `tests/app_config/`, and `tests/schemas/`. `conftest.py` stays at the `tests/` root. No functional change.

**Refactor: centralise shared state in `AppState` dataclass**

- Added `ui/app_state.py` with an `AppState` dataclass holding all 18 shared mutable fields that were previously bare `self.X` attributes on `MainWindow` (current file/tree, file buffers, dirty tracking, flags, case config, diff state, foamMonitor state, panel state). `MainWindow.__init__` now does `self.state = AppState()` and all eight mixins access shared data as `self.state.<field>`, making every cross-mixin dependency explicit and grep-able. No functional change.

## v1.5.0 — 2026-06-10

### Improvements

**BlockMesh viewer: side-by-side mode**

- A **⊞** toggle button appears in the top-right corner of the upper tab widget when `blockMeshDict` is the active file and the BlockMesh panel is available.
- Clicking it places the 3-D viewer in a horizontal splitter to the right of the Tree, so tree edits and the 3-D view are visible simultaneously. The separate **BlockMesh** tab is removed while side-by-side mode is on, and restored when it is turned off.
- The 3-D view is not updated automatically; click **Refresh** in the BlockMesh panel after making tree edits.
- The button is disabled while the xterm terminal is active (GPU/OpenGL conflict).

**Comparison panel: hidden when not in comparison mode**

- The reference-case tree pane is now hidden entirely when no reference case is loaded. Previously it occupied an invisible splitter slot, leaving a hairline splitter handle gap between the main tree and the detail pane.
- The pane appears when **Side by side** is checked in the diff bar and disappears when it is unchecked or **Clear** is clicked.

**BlockMesh viewer: Preview mode for variable-based meshes**

- When the `vertices` block contains variable references (`$varName`), the X/Y/Z cells in the vertices table are now read-only by default (direct writes would silently fail and were confusing).
- A **⚙ Variable-based** chip and a **Preview** toggle button appear at the top of the Vertices panel (inside the group box, not in the main toolbar). Clicking **Preview** enters Preview mode: table cells become editable and each change immediately updates the 3-D view, but the tree and file are not modified. A yellow banner is shown while Preview mode is active.
- Click **Refresh** to exit Preview mode and restore vertex coordinates from the tree.
- For meshes without variable references the table behaves as before: edits write through to the tree and editor immediately.

**BlockMesh viewer: multi-level variable chain resolution**

- Variable chains of arbitrary depth in `blockMeshDict` are now fully resolved. Previously, a macro reference like `z001 $z1;` would fail when `z1` itself was defined via `#eval{$z0+$dz0}` — the macro pass ran before `#eval` was evaluated, leaving the raw expression string instead of a number.
- The fix replaces the fixed three-pass approach with an iterative loop that alternates macro-reference resolution and `#eval` expression evaluation until stable. The iteration cap is the number of top-level variable definitions, which is the theoretical maximum depth of any non-circular dependency graph.
- Circular references (`a $b; b $a;`) are silently left unresolved without causing an infinite loop or crash.

---

## v1.4.0 — 2026-06-09

### New features

**foamMonitor launcher**

- A **foamMonitor…** button in the top bar opens a dialog to launch `foamMonitor` and plot residuals or other data with gnuplot.
- The dialog lets you pick any file (solver log or `postProcessing/` output), set options (log scale, grid, refresh interval, idle timeout), and add free-form extra flags.
- While foamMonitor is running the button changes to **■ foamMonitor**; clicking it stops the process (kills both the foamMonitor shell and the gnuplot window). Opening a new case also stops a running instance.
- A compatibility patch is applied at launch so that the `reread` command deprecated in newer gnuplot versions is replaced by the modern `load ARG0` equivalent — the gnuplot window refreshes correctly regardless of gnuplot version.
- If the selected file does not exist, or foamMonitor exits with an error, a warning dialog is shown.

**BlockMesh viewer: variable and `#eval` expression support**

- Variable definitions at the top of `blockMeshDict` (e.g. `xMax 0.5;`, `nCell 20;`) are now substituted in `vertices` and `blocks` before the 3-D geometry is extracted. Both `$varName` and `${varName}` reference styles are recognised.
- Macro variables that reference other variables (`nx $nCell;`) are resolved one level deep.
- Arithmetic expressions (`zMax #eval{ $length / $nCell };`) are evaluated after variable substitution. Supported operators: `+`, `−`, `*`, `/`, parentheses.
- Previously, unresolved `$variable` references caused `float()` conversion to fail, producing missing vertices and, in the worst case, an out-of-bounds vertex index that triggered a VTK crash.
- **Lexer fix:** `#eval{expr};` written without internal spaces was tokenised as a single directive token that included the semicolon, causing the parser to consume the entire `vertices` block as the value of the preceding variable. The lexer now stops directive token reading at `{`, so depth tracking works correctly.

**Drag-and-drop to open a case**

- Drag a case directory from the file manager and drop it anywhere on the application window to open it — the tree view, editor, file list, and all other panels are valid drop targets.
- If there are unsaved changes in the currently open file, a confirmation dialog is shown before loading the new case.

---

## v1.3.0 — 2026-06-01

### Improvements

**Faster, non-blocking case comparison**

- Diff counts for the file list are now computed incrementally — one file per event-loop tick — so the UI stays responsive and `≠` markers appear progressively instead of blocking until all files are parsed.
- Large files without a `FoamFile` header (e.g. `log.simpleFoam`, residual outputs) are automatically skipped during diff computation and boundary panel loading. Files under 100 KB are always attempted so small custom solver dictionaries without a `FoamFile` block continue to work.
- Opening a large non-dictionary file now shows a confirmation dialog warning that the tree view will be unavailable and the application may not respond during loading. A status bar message appears immediately after confirmation.

### New features

**UI language selection (English / Japanese)**

- New **Settings > Language** submenu. Select **English** or **日本語**; the application restarts in the chosen language.
- Language is stored in `app_config.json` and applied at startup. English remains the default.
- New `i18n/` module: `tr()` looks up the active language dict; missing keys fall back to the English string automatically.
- Adding further languages (e.g. Italian) requires only a single `i18n/<code>.py` translation file — no other code changes.

---

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
