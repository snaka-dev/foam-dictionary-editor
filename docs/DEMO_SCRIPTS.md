# FoDE — Demo Movie Scripts

Shot-by-shot scripts for the demo movies, and how to record them. For the still gallery see [SCREENSHOTS.md](SCREENSHOTS.md); for the feature reference see [USER_GUIDE.md](../USER_GUIDE.md).

Every movie below is **scripted in full and runs**: `tools/demo_driver.py` drives the window through each one and records it, from the scenes in `tools/demo_specs.json`. See [Demo recording](../DEVELOPER.md#demo-recording) for how the driver works.

| Movie | Scene | Case | Length | Published |
|---|---|---|---|---|
| 1 — Edit, see, run | `damBreak-end-to-end` | bundled `tutorials/damBreak` | ~94 s | https://vimeo.com/1218332419?texttrack=en |
| 2 — It draws your dictionaries | `topoSet-overlay-tour` | bundled `tutorials/topoSetShapes` | ~68 s | https://vimeo.com/1218336381?texttrack=en |
| 3 — Working across cases | `cavity-boundary-and-compare` | bundled `tutorials/cavity` | ~43 s | https://vimeo.com/1218342697?texttrack=en |
| 4 — Meshing around a surface | `motorBike-snappy-overlay` | `{cases}/motorBike` — **not** bundled | ~73 s | https://vimeo.com/1218350862?texttrack=en |
| 5 — Three files, one view | `sampling-three-files-one-view` | bundled `tutorials/samplingShapes` | ~50 s | https://vimeo.com/1218352171?texttrack=en |
| 6 — Five meshes, one case | `multiRegion-five-meshes-one-case` | bundled `tutorials/snappyMultiRegionHeater` | ~28 s | https://vimeo.com/1218352881?texttrack=en |
| 7 — The whole workflow | `cavity-full-workflow` | bundled `tutorials/cavity` | ~3 min 41 s | https://vimeo.com/1217899060?texttrack=en |
| 8 — What the model is | `pitzDaily-turbulence-notes` | bundled `tutorials/pitzDaily` | ~64 s | https://vimeo.com/1218354126?texttrack=en |
| 9 — Where your cases live | `case-browser-find-and-organise` | bundled `tutorials/cavity` + `damBreak` + `pitzDaily` | ~59 s | https://vimeo.com/1225897573?texttrack=en |
| 10 — Post-processing without the dictionary | `damBreak-function-objects` | bundled `tutorials/damBreak` | ~56 s | https://vimeo.com/1244300225?texttrack=en |
| 11 — A run that outlives FoDE | `damBreak-background-run` | bundled `tutorials/damBreak` | ~85 s | https://vimeo.com/1244300224?texttrack=en |
| 12 — Running in parallel | `damBreak-parallel-run` | bundled `tutorials/damBreak` | ~100 s | https://vimeo.com/1244516337?texttrack=en |

## Choosing what to show

Short movies rather than one long one, because they answer different questions and nobody has all of them. The first three make the general case — *why would I use this*, *what does it look like*, *how does it fit my work* — and are the ones to show someone who has never seen FoDE. The rest each go deeper into one dictionary family, for someone who already knows they have that particular problem: meshing around a surface, sampling, multi-region cases. Someone who bounces off the first minute has still seen the argument.

**Movie 7 is the deliberate exception**, at more than three times the length of any other. It is Appendix A of the SoftwareX paper — the worked icoFoam/cavity example — recorded, so a reader who has just finished the appendix can watch it happen instead of imagining it. The argument for keeping the others short does not apply to it: its audience has already decided to try the tool and is asking what a whole case looks like from one end to the other, which is a question that cannot be answered in a minute. It is the one to link from the paper, and the wrong one to open with.

Each scene prefers a case from the repository's own `tutorials/` over one from an OpenFOAM installation. A bundled case makes the movie **replayable by anyone who clones the repository**, and it makes the recording reproducible: the driver copies the case to a scratch directory before every take, so a movie that runs `blockMesh` starts from a case with no mesh, every time.

## Movie 1 — Edit, see, run (`damBreak`, ~94 s)

**Scene:** `damBreak-end-to-end`. **Case:** bundled `tutorials/damBreak`. **What it argues:** the dictionary, the geometry it describes and the tools that consume it are one loop, and FoDE closes it — from an edit to a finished run without leaving the window.

Layout: side-by-side, so the tree and the 3-D view are on screen together — the whole point of the movie is that an edit in one lands in the other. The detail pane is collapsed to give both the width.

| At | Beat | On screen | Narration |
|---|---|---|---|
| 0:00 | Open | The case is loaded, `blockMeshDict` open, the block mesh drawn beside the tree — and the orange water column already in it, badged `alpha.water=1 (clipped)` | This is an OpenFOAM case — the damBreak tutorial — open in FoDE. The dictionary is a tree on the left; on the right, the mesh it describes, and the water column setFieldsDict will fill — drawn as soon as the case opened. |
| 0:04 | Open `setFieldsDict` | Click the file; its tree replaces blockMeshDict's | Open setFieldsDict: it is the file that puts that water there. |
| 0:09 | Select the `box` row | The tree row highlights; the editor below scrolls to line 26 and marks it | Select the box that defines it, and the editor below jumps to the line it came from. |
| 0:14 | Edit the value | Double-click the Value cell, type `(0 0 -1) (0.35 0.4 1)` | Change the water column — make it wider and taller. |
| 0:18 | The overlay follows | Enter: the orange box grows, the editor line rewrites, all three views agree | The overlay follows the edit. No re-run, no export, no guessing at coordinates. |
| 0:23 | Save | **Save File** | Save the file. |
| 0:28 | Run blockMesh | **Tools > Run blockMesh…**, then **Run** | The mesh has to exist before the fields can be set, so run blockMesh. |
| 0:33 | It runs | The Terminal tab fills; the file list grows a `constant/polyMesh: 2,268 cells` indicator as it lands | It runs in the Terminal tab, in the case directory, and tees its output to a log. |
| 0:44 | The setFields dialog | The dialog: the compounding-values warning, **Restore 0/ from 0.orig/ first** checked, and the command preview `rm -rf 0 && cp -r 0.orig 0 && setFields 2>&1 \| tee log.setFields` | Now setFields. The dialog offers the flags rather than asking you to remember them, and shows the exact command it will send. setFields rewrites 0/ in place, so it offers to restore 0/ from 0.orig first — checked by default, and visible in the command. |
| 0:53 | It runs | `Selected 1012/2268 cells` — the count follows from the box that was edited at 0:14 | Run it. |
| 1:01 | The Run Solver dialog | **Tools > Run Solver…**: `interFoam` read from `controlDict`, the command `interFoam 2>&1 \| tee log.interFoam`, and a note that a parallel run needs a decomposed case | And the solver. Run Solver reads interFoam from controlDict and shows the command; the parallel option waits for a decomposed case. |
| 1:08 | interFoam runs | Residuals in the Terminal; `Results: 0.05 0.1 0.15 …` appearing in the file list; `End` after about four seconds | interFoam runs to the end time, and the time directories it writes land in the file list as they appear. |
| 1:22 | Log summary | **Tools > View Log Summary…** on `log.interFoam`: 401 time steps to `Time = 1`, the last residuals, `Result: OK` | Then the logs the runs left behind are condensed to a report: what ran, how far it got, and every warning it printed. |

Two beats are the ones worth protecting in any re-cut. **0:18**, because the three-way sync is the thing no other editor does. And **0:53**, because `Selected 1012/2268 cells` is the edit from 0:14 coming back as a number — the loop visibly closing, rather than being asserted.

The `then` dwell on each step is sized to its narration, at roughly the speed the line can be read aloud. A step whose caption is three sentences (the setFields dialog) holds for eight seconds; `Save the file.` holds for two. The parallel note in the Run Solver dialog is left in on purpose: it is what [Movie 12](#movie-12--running-in-parallel-dambreak-100-s) picks up.

## Movie 2 — It draws your dictionaries (`topoSetShapes`, ~68 s)

**Scene:** `topoSet-overlay-tour`. **Case:** bundled `tutorials/topoSetShapes`. **What it argues:** you can see what a dictionary says before running anything — and nothing is run here, so the movie plays on a machine with no OpenFOAM at all.

Layout: the **BlockMesh** tab full width, because here the 3-D view is the argument rather than a companion to the tree.

| At | Beat | On screen | Narration |
|---|---|---|---|
| 0:00 | Open | Every shape at once inside the block mesh, each badged, coloured by the action that produced it | This case's topoSetDict exercises every geometry source the viewer can draw — boxes, spheres, cylinders, cones, points, planes. Nothing has been run here. This is the dictionary, drawn. |
| 0:05 | Orbit | Drag in the view; the scene turns | It is a real 3-D scene, so you can look at it from anywhere. |
| 0:11 | The `topoSet ▾` menu | Every source as a row, with the action-colour legend above | Every source in the dictionary is a row in this menu, coloured by the action that produced it — new, add, subtract. |
| 0:15 | Uncheck three | `ball`, `pipe`, `twinBoxes` unchecked; the menu stays open throughout | Uncheck the ones you are not interested in — the menu stays open, so you can work through a list. |
| 0:24 | The rest of the menu | Cursor down the rows to `Non-geometric sources (1)` | Sources with no geometry to draw are not silently dropped either — the last row counts them, so the menu accounts for the whole dictionary. |
| 0:28 | The scene without them | Escape; the three shapes are gone from an otherwise unchanged scene | And the scene is left with what you asked for. |
| 0:34 | Show all | Reopen, **Show all shapes**; they return | Show all brings them back. |
| 0:39 | Clipping | The `midPlane (clipped)` badge | A shape reaching past the block mesh is drawn cut down to it, and its badge says so. That is display only — the dictionary is untouched, and an export writes the whole shape. |
| 0:47 | Tree to editor | Tree tab, select a source; the editor scrolls to its lines | Select a source in the tree and the editor scrolls to the lines that define it — the same two-way link every dictionary has here. |
| 0:58 | Export | **STL ▾ > Export Shapes as STL…**: every shape as a checkable row | Which is what this does. Every shape on screen can be written out as STL — real geometry, not a sketch. |

The beat to protect is **0:15–0:34**: unchecking shapes, closing the menu to see the result, then bringing them back. It is the only part that shows the overlay is a working instrument rather than a picture. Note that the menu is dismissed *before* the reveal — it is tall enough to cover the shapes it is changing, so leaving it open would hide the very thing the beat is about.

## Movie 3 — Working across cases (`cavity`, ~43 s)

**Scene:** `cavity-boundary-and-compare`. **Cases:** bundled `tutorials/cavity/cavity`, compared against `tutorials/cavity/cavityGrade`. **What it argues:** FoDE is for working on a case, not just opening a file.

| At | Beat | On screen | Narration |
|---|---|---|---|
| 0:00 | The boundary table | Boundary tab: fields down, patches across, the type in each cell | Boundary conditions live in a file per field, so reading them as a set means opening every one. The Boundary tab lays them out as a table instead — every patch, every field, and the type each pair is given. This is a two-field case; on a real one the table is what stops you missing a patch. |
| 0:05 | Lines per cell | Raise it twice; the entries under each type appear in the cells | Raise the lines per cell and the entries under each type come with it — so the values are there too, not just the names. |
| 0:11 | Transpose | The table flips orientation | Patches down or fields down, whichever way round you think about them. |
| 0:16 | Pick a reference | **Case > Compare with Case…**, then the reference case | A case rarely exists on its own — it came from a tutorial, or from last week's run. So point FoDE at the other one. |
| 0:23 | The comparison | Two trees side by side, differing entries marked, the file list carrying per-file diff counts | Now both cases are on screen at once. Entries that differ are marked in place, and so are the ones present on only one side — and the file list carries the same information one level up, so you can see which files differ before opening any of them. |
| 0:31 | A differing file | `blockMeshDict`: one block on the left, four graded blocks on the right | A graded mesh against a uniform one, so blockMeshDict is where they part: one block on the left, four graded blocks on the right — found without reading either file. |
| 0:37 | Clear | The comparison ends, the case is as it was | Nothing was modified by comparing. Clear ends it. |

`cavity` is deliberately a small case, and the table beat says so rather than pretending otherwise — two fields and three patches is a table you could have read by hand. The claim being made is about what happens when it is not.

## Movie 4 — Meshing around a surface (`motorBike`, ~73 s)

**Scene:** `motorBike-snappy-overlay`. **Case:** `motorBike`, from the recording machine's run directory (`{cases}`) — the one movie that is **not** replayable from a bare checkout, because the case is not bundled. **What it argues:** `snappyHexMeshDict` is mostly references to things you cannot see, and FoDE draws them.

| At | Beat | On screen | Narration |
|---|---|---|---|
| 0:00 | Open | The motorBike surface in teal inside the background block mesh, the purple `refinementBox`, the `locationInMesh` marker | snappyHexMesh builds a mesh around a surface, and its dictionary is mostly references to things you cannot see: a geometry file, a refinement region, a point that decides which side is fluid. Open the case and they are drawn — inside the background mesh they will be cut from. |
| 0:06 | Orbit | The scene turns | The bike is the triSurface the dictionary names, resolved from constant/triSurface and loaded for you. |
| 0:13 | Zoom | Scroll in, towards the bike; it resolves into an actual motorcycle | Zoom in and it is the real surface, not a bounding box standing in for it. |
| 0:22 | The `snappyHexMesh ▾` menu | Rows grouped by category, with the surface/region/geometry legend and the keep-point row | The rows are classified by how the dictionary uses each one — surfaces to snap to, regions to refine by, and the keep-point — because that is the distinction that matters when a mesh comes out wrong. |
| 0:44 | The box alone | The bike unchecked; the refinement box left in the domain | Hide the bike and the refinement region is left on its own — which is the thing you actually want to check. Does it enclose what it is meant to refine, and is it inside the background mesh at all? |
| 0:58 | Tree to editor | `refinementRegions/refinementBox` selected; the editor scrolls to it | Select the region in the tree and the editor goes to the entry that defines it — the refinement levels, and the mode that says whether inside or outside is the part being refined. |
| 1:05 | The keep-point | The `locationInMesh` marker | And the marker is locationInMesh: the single point that tells snappyHexMesh which side of the surface to keep. Put it on the wrong side and the mesher happily deletes the domain instead of the bike. It is one line in the dictionary, and now it is somewhere you can look at. |

Two things about this scene are worth knowing before re-cutting it.

**The camera pops back out at 0:44.** Hiding a shape re-renders, and every render ends in `reset_camera()` — so the zoom from 0:13 is undone. It is not a glitch to fix in the take; it is what the panel does. Here it happens to serve the line it lands on, which asks whether the box sits inside the *whole* domain, so the wide framing is the right answer to the question being asked.

**The orbit is set to `"ticks": 6`.** Each increment of a drag costs a re-render, and this surface is heavy enough that the default granularity turned a 1.4-second orbit into a 24-second one. Fewer, larger steps stay smooth, because what is slow is the frames rather than the motion.

`motorBike` also has a sampling dictionary, `system/cuttingPlane`, which FoDE draws as a plane through the whole domain. The scene switches the sampling overlay off (`"overlays": {"sampling": false}`) so the plane does not bury the shapes this movie is about; the sampling counterpart is `tutorials/samplingShapes`, which is bundled and was built for it.

## Movie 5 — Three files, one view (`samplingShapes`, ~50 s)

**Scene:** `sampling-three-files-one-view`. **Case:** bundled `tutorials/samplingShapes`. **What it argues:** sampling is the one overlay whose definitions are scattered across files by design, and the panel puts them back together without asking you to remember where you wrote each one.

| At | Beat | On screen | Narration |
|---|---|---|---|
| 0:00 | Open | Probe points, sample tubes and two plane discs in one 3×3×3 block, each badged | Sampling is the odd one out among these dictionaries: it has no file of its own. It can be a function object inside controlDict, or a standalone dictionary, written in either of two list syntaxes. This case spreads its definitions across all three — and the panel draws them as one scene. |
| 0:06 | Orbit | The scene turns | Probe locations are drawn as point markers, sample lines as tubes, sampling planes as discs. |
| 0:10 | The `sample ▾` menu | Every row tagged with its source: `nearWallProbes · probes [controlDict]`, `topSpan · lineUniform [sample]`, `midCut · cuttingPlane [surfaces]`… | And every row says where it came from. nearWallProbes out of controlDict, topSpan and scatter out of sample, midCut and lowCut out of surfaces — three files, one view, and no need to remember which of them you put a thing in. |
| 0:16 | Uncheck two | `topSpan` and `scatter` go; Escape shows the result | They toggle like any other overlay, whichever file they came from. |
| 0:26 | Show all | They return | |
| 0:31 | Clipping | Both planes badged `(clipped)` | Both planes are badged clipped, and always will be: a sampling plane is unbounded, so the disc is a display convenience cut back to the mesh you are looking at rather than a shape with edges of its own. |
| 0:42 | Where the probes came from | Tree tab, `controlDict` open, `functions > nearWallProbes > probeLocations` selected with its three points; the editor highlights them | And this is one of the three: the probes, as a function object in controlDict, with the points that put those markers where they are. Sampling written anywhere the solver accepts it, and still drawn before the solver has run once. |

The beat that carries the movie is **0:10** — the menu, with `[controlDict]`, `[sample]` and `[surfaces]` visible in the same list. Everything before it is setup and everything after is proof; if a re-cut has to lose something, lose the orbit.

The closing beat is deliberately the least visual one in the movie. Ending on the tree and the editor, rather than on the 3-D view it spent forty seconds building up, is the point being made: the picture came from these three files, and here is one of them.

## Movie 6 — Five meshes, one case (`snappyMultiRegionHeater`, ~28 s)

**Scene:** `multiRegion-five-meshes-one-case`. **Case:** bundled `tutorials/snappyMultiRegionHeater`. **What it argues:** on a multi-region case the file list stops being a list and starts being a map. The shortest movie in the set, and the only one with no 3-D view in it at all.

| At | Beat | On screen | Narration |
|---|---|---|---|
| 0:00 | Five meshes | The file list grouped `system/heater`, `system/leftSolid`, `system/topAir`, `constant/bottomAir`, `constant/heater`…; the heater's solid `thermophysicalProperties` open | A conjugate heat transfer case is not one case. This one is five meshes sharing a directory — two fluid regions and three solid ones — each with its own schemes, its own solution settings, its own material properties. On disk that means the same file names repeated under five subdirectories, twice over, in system and in constant. |
| 0:07 | The region groups | Cursor down the grouped list | FoDE recognises the layout and groups the list by region, so the heater's files sit under the heater's own headings — rather than a flat list of identical names you have to read directory prefixes off to tell apart. |
| 0:13 | `changeDictionaryDict` | The heater's, open in the tree | And this is the file that makes multi-region cases what they are — changeDictionaryDict, which patches the boundary conditions per region after the meshes are cut. There is one for every region, and they are the files you actually spend the time in. |
| 0:18 | A fluid region | `system/bottomAir/fvSolution` | The fluid regions sit next to them, solved with entirely different settings in the same case. |
| 0:23 | The case-root scripts | `Allrun` under the **case root** group: shell highlighting, empty tree, and the status bar reading *Script file — text editing only* | And at the bottom, under case root, the scripts that drive the whole thing. They open as text with shell highlighting rather than being forced through a dictionary parser, they keep their executable bit when saved, and they travel with the case when you duplicate it. Reading Allrun is usually how you find out what a case actually does. |

The closing beat pays off twice by accident, and it is worth keeping the framing that lets it: `Allrun`'s visible lines include the `cp` that fetches `geom.stl.gz` out of `$FOAM_TUTORIALS` into `constant/triSurface`. That is exactly the "what does this case actually do" the narration claims, answered on screen — and it is also why this case's `snappyHexMeshDict` geometry cannot be drawn until `Allrun` has been run once, which is why the movie has no 3-D view.

`constant/regionProperties` would have been the natural opening file — it is the entry that literally lists the five regions — and the scene was written around the fact that it did not parse: its list form (`regions ( fluid (…) solid (…) );`) landed as two nameless amber `unknown_raw_entry` rows, because the `regions` key was claimed unconditionally by setFieldsDict's named-dict form. Shooting this movie is what turned that up, and it has since been fixed — the file now parses as a single `regions` row. The scene still opens on the heater's `thermophysicalProperties`, which is what the published take shows and is the better opening for a movie about the *file list* rather than about one file; a future re-cut could open regionProperties instead.

## Movie 7 — The whole workflow (`cavity`, ~3 min 41 s)

**Scene:** `cavity-full-workflow`. **Case:** bundled `tutorials/cavity/cavity`. **What it argues:** everything the other six show in isolation is one continuous piece of work, and it fits in one window. This is [Appendix A of the SoftwareX paper](https://doi.org/10.1016/j.softx.2026.102852) — the lid-driven cavity solved with icoFoam — shot beat for beat, section A.2 through A.7.

It types `blockMesh` and `icoFoam` in the Terminal because the paper's appendix does; the same steps are now on the Tools menu, which [Movie 1](#movie-1--edit-see-run-dambreak-94-s) and [Movie 12](#movie-12--running-in-parallel-dambreak-100-s) show. The movie is kept as the paper describes it rather than updated.

Layout: no 3-D view, and the detail panel given real width instead of being collapsed — the schema drop-down is one of the beats. The window opens with **no case loaded at all**, which no other scene does: the first act is the case arriving.

| At | Beat | On screen | Narration |
|---|---|---|---|
| 0:00 | An empty window | Nothing loaded; the Tools menu correctly disabled | This is the worked example from the FoDE paper: the lid-driven cavity, solved with icoFoam, from nothing to a result — without leaving the editor. |
| 0:08 | The case library | **Case > Duplicate from Case Library…**, the chooser on the tutorials tree | A case starts as a copy of another one. The case library is where the tutorials live, and duplicating from it leaves the original untouched. |
| 0:14 | The Duplicate Case dialog | Source, destination, live preview, the two copy modes | The dialog asks where the copy goes, what to call it, and how much to copy — the whole directory, or only the dictionaries FoDE recognises. |
| 0:19 | Name it | `cavity_copy` → `cavity`, the preview following each keystroke | It proposes the source name with a copy suffix. Drop the suffix: this working case is just cavity. |
| 0:28 | Open it | The copy opens in FoDE; the confirmation answered **Yes** | And open it. |
| 0:34 | The dictionaries of a case | The file list grouped `system`, `constant`, `0` | Here is the whole case in one pane: controlDict, blockMeshDict, fvSchemes and fvSolution under system, transportProperties under constant, and the velocity and pressure fields under zero. No walking three directories to find out what a case contains. |
| 0:41 | The `[+]` marker | Right-click the `system` header → **Add files from 'system'…** → `blockMeshDict.m4` | A directory marked with a plus holds files the list does not show by default. |
| 0:44 | Ask for the files | **Add files from 'system'…** chosen; the picker lists `blockMeshDict.m4` | Ask for them, and here is the one this case has: blockMeshDict.m4, the m4 source the shipped blockMeshDict was generated from. |
| 0:50 | It joins the list | **Select All**, **Add Selected**; `blockMeshDict.m4` appears among the files | Now it is in the list with the rest. |
| 0:55 | controlDict in the tree | Tree row selected, the editor below scrolled to line 29 and marked | controlDict, parsed into a tree. The editor below holds the same file as text, and follows the tree: select an entry and the line it came from is highlighted. |
| 1:00 | The schema-driven detail panel | `writeControl` selected: Key Help, Key Supported In, Key Note, Choices, Choice Help | Select writeControl and the detail panel on the right explains it — what the key does, which distributions support it, and the values it accepts. |
| 1:09 | The documented choices | The drop-down open: `timeStep`, `runTime`, `adjustableRunTime`, `cpuTime`, `clockTime` | The choices are a drop-down rather than something to remember: timeStep, runTime, adjustableRunTime, each with its own note. |
| 1:19 | The tree context menu | On `fvSchemes`' `ddtSchemes`: copy/paste value, add, duplicate, comment out, delete | Entries are edited in the tree itself — copy and paste a value, add or duplicate an entry, comment one out and restore it later, or delete it. |
| 1:27 | The boundary table | `p` and `U` against `fixedWalls` / `frontAndBack` / `movingWall` | Boundary conditions live in a file per field, so reading them as a set means opening every one. The Boundary tab gathers them into a table instead: every patch, every field, and the type each pair is given. The walls are no-slip, and the front and back are empty — this is a two-dimensional case. |
| 1:39 | Lines per cell | The spin box to 3; `value  uniform (1 0 0)` appears under `fixedValue` | Raise the lines per cell and the entries come with it, so the values are there too: the moving wall carries a uniform velocity of one metre per second along the top. |
| 1:45 | A cell, and its file | The `U` / `movingWall` cell selected; `0/U` opens at line 23, status bar *Parsed successfully* | Select a cell and the file it came from opens with that entry highlighted, so a correction is one click from the table that found it. |
| 1:51 | Transpose | **Transpose**; patches and fields swap axes | Patches down or fields down, whichever way round you think about them. |
| 1:55 | The terminal | The Terminal tab, already in the case directory | The case is ready to run, and the terminal is already in its directory. |
| 2:02 | blockMesh | Typed by hand, teed to `log.blockMesh`; `constant/polyMesh: 400 cells` lands in the file list | blockMesh builds the mesh from blockMeshDict. It runs here, in the same window the dictionaries were edited in, and the file list picks up the mesh it wrote. |
| 2:13 | icoFoam | Residuals scrolling; `Results: 0.1 0.2 0.3 0.4 0.5` appearing in the file list | Then icoFoam advances the solution to half a second. Four hundred cells, so it is over almost as soon as it starts — and the time directories it writes appear in the list as they land. |
| 2:24 | The run, condensed | **Tools > View Log Summary…** over `log.blockMesh` and `log.icoFoam` | Those runs left logs behind, and FoDE condenses them: what ran, how far it got, the residuals it ended on, and every warning it printed along the way. |
| 2:38 | ParaView | **Tools > Open Mesh in ParaView…**; `paraFoam -case` on the open case | And the result goes to ParaView, on the case that is open, from the same menu as everything else. It comes up on the case directory, with the mesh and every field already found. |
| 3:07 | Apply | ParaView: **Apply**; the cavity appears in the render view | Apply, and the cavity is there. |
| 3:18 | The last time step | The VCR toolbar's Last Frame button; the view jumps to 0.5 s | Skip to the last time written — half a second, where the run ended. |
| 3:29 | Velocity magnitude | Coloured by `U` magnitude: the lid red along the top, the vortex under it | Colour it by velocity magnitude, and there is the lid-driven cavity: the wall dragging the fluid along the top, the primary vortex turning underneath it. One case, one window, from an empty editor to that. |

Three beats are the ones to protect in a re-cut. **1:09**, because the schema drop-down is the feature the paper spends the most words on and the hardest to convey in a still. **1:45**, because the boundary table producing the file *and the line* is the aggregation paying for itself. And **2:13**, because the file list growing a time-directory row while the solver is still printing is the whole "one window" claim, unarguable and in passing.

This is the only scene that drives an application other than FoDE. ParaView resolves nothing semantically — it is not our window — so its four clicks are `point` steps, pixel coordinates read off a rehearsal screenshot. They hold because the take runs on a display of a known size with no window manager, so ParaView opens at the origin at 1280×800 every time; they are the first thing to break if that changes, and re-reading them is a rehearsal and a screenshot.

## Movie 8 — What the model is, not just its name (`pitzDaily`, ~64 s)

**Scene:** `pitzDaily-turbulence-notes`. **Case:** bundled `tutorials/pitzDaily`. **What it argues:** the detail pane does not merely list the values a key accepts. It says what each one *is*, in OpenFOAM's own words, quoted from that model's source header with the paper that defines it — and it says nothing where upstream says nothing.

Layout: the Tree tab, no 3-D view, and the detail pane at 560 px — wide enough that the longest note in the list wraps without the pane scrolling, which was measured across all seventeen choices rather than eyeballed on one. This is the only movie whose subject is a single form on the right-hand side, so the framing is unusually still: the cursor moves twice in the whole take.

| At | Beat | On screen | Narration |
|---|---|---|---|
| 0:00 | Open | The whole dictionary in six tree rows — `simulationType`, `RAS`, and three entries inside it. No `kEpsilonCoeffs`, because the case overrides no default | A turbulence dictionary is a short file: a simulation type, a model, two switches. Nothing in it says what the model actually is. |
| 0:06 | The model row | `RAS/RASModel` selected; **Key Status** reads *Historical name — OpenFOAM reads 'model' in v2006* | Select the model. RASModel is the old spelling — OpenFOAM reads 'model' now — and the pane says so rather than hiding it, because nearly every tutorial still writes it this way. |
| 0:12 | kEpsilon | Choice Help: the header summary, RDT compression term and all. Choice Note: Launder & Spalding (1972) | And here is what kEpsilon is, in OpenFOAM's own words, quoted from the model's source header — with Launder and Spalding, the paper that defines it. |
| 0:20 | kOmegaSST | One `Down`: the description changes, and **Choice Note is blank** | Step down the list and every value brings its own. Where upstream cites no paper the note is left empty rather than filled with a guess. |
| 0:25 | SpalartAllmaras | A note running to three references | Some are three papers rather than one. |
| 0:30 | realizableKE | | Sixteen models in this list, twenty-nine across RAS and LES. |
| 0:34 | RNGkEpsilon | Yakhot & Orszag (1992) | Every one of them read out of the source of seventeen OpenFOAM releases. |
| 0:38 | LaunderSharmaKE | **Choice Supported In**: `Foundation v7-v14, OpenCFD v2106-v2606` | Which is what the Supported In row is counting: measured, rather than assumed. |
| 0:43 | The sweep | Eleven presses in three seconds; eleven more models' help flickering past | And it is not a handful of them that carry this. |
| 0:50 | laminar | One short line, no note — the only entry in the list written by FoDE rather than quoted | The last row is the exception that proves it: laminar names no model class, so there is nothing upstream to quote — and that one sentence is FoDE's own. |
| 0:56 | Nothing was written | The cursor returns to the tree: the row still reads `kEpsilon`, the file list carries no dirty marker, and the editor below still shows `RASModel kEpsilon;` on line 23 | Nothing has been changed. The tree still reads kEpsilon and the file is not marked dirty: the value moves only when you press Apply Value. Reading the list is free. |

Two beats to protect in a re-cut, and they are the same claim from opposite sides. **0:20**, because a blank note where upstream wrote no reference is the whole credibility of the feature — a pane that always has something to say is a pane that is making things up. And **0:50**, because `laminar` is the one row FoDE speaks in its own voice, and the movie says so out loud rather than letting it pass as quoted.

**The drop-down is deliberately not opened.** Movie 7 opens the same widget with `alt+Down` to show that `writeControl`'s choices are a list; here the popup would cover the Choice Help and Choice Note rows immediately below it, which are the entire subject. A closed combo box moves its index on a plain `Down`, and the help rows follow it live — so the scene clicks the box once for focus and then only presses a key.

The take is also, incidentally, the check that browsing costs nothing: `DetailPanel` updates the help from `currentTextChanged` and writes the node only on **Apply Value**, which no step presses. The closing frame is the evidence, not the assurance.

## Movie 9 — Where your cases live (`cavity`, ~59 s)

**Scene:** `case-browser-find-and-organise`. **Cases:** bundled `tutorials/cavity/{cavity,cavityGrade,cavityClipped}`, `tutorials/damBreak` and `tutorials/pitzDaily`, all copied into one scratch directory so there is a set of cases to browse. **What it argues:** FoDE is where your cases live, not just the one you have open.

| At | Beat | On screen | Narration |
|---|---|---|---|
| 0:00 | One case at a time | The Files tab: `cavity`'s file list, `controlDict` open | The file list shows what is inside the case you have open. That is most of the job — but it says nothing about the case next to it, or where either of them lives. |
| 0:05 | The Cases tab | Five cases listed, each marked `◆`; the open one bold | So there is a second tab, and it lists the cases themselves. A diamond marks a directory that really is an OpenFOAM case, and the one in bold is the case you are in — so the list also answers which of these you are actually looking at. |
| 0:10 | Open by double-click | `cavityGrade` opens; the file list and tree follow | Double-clicking a case opens it. No file chooser, and no typing a path you have to remember — the cases were already on screen. |
| 0:18 | Compare from here | Right-click `cavity` → **Compare with Case…**; the two trees appear | And the case you are not in is the obvious thing to compare against. Pick it from the same list and the comparison starts — a graded mesh against a uniform one, differing entries marked in place. |
| 0:24 | Clear | The comparison ends | Nothing was modified by comparing. |
| 0:27 | The Case Browser | **Browse…** opens the two-pane window | Finding and opening is half of it. The other half is the work you used to leave for a file manager, and Browse opens the window that does it: a folder tree, the cases in the current folder, and what you can do to them. |
| 0:36 | Somewhere to put things | **New Folder…**, typed `archive` | A finished run does not need deleting, it needs moving out of the way. |
| 0:48 | Moved | `damBreak` selected, **Move…**, the destination, then the confirmation | It says where it is going before it goes, and the list updates when it has. Move, rename, copy and delete all work here — and deleting goes to your desktop trash, not to nowhere. |
| 0:53 | Back to the case | **Close**; `cavityGrade` is still open behind it | The case you had open is still open. Browsing your cases never disturbed the one you were working on. |

The scene copies five cases into one scratch directory rather than pointing at an installation's `tutorials/`, for the reason every other scene prefers a bundled case: it replays from a clone. It is also the only scene whose staging has to *remove* something — the `archive` folder a step creates would otherwise still be there on the next take, and **New Folder…** would refuse a name that already exists rather than making one.

## Movie 10 — Post-processing without the dictionary (`damBreak`, ~56 s)

**Scene:** `damBreak-function-objects`. **Case:** bundled `tutorials/damBreak`. **What it argues:** adding probes needs no knowledge of how the dictionary is written, and you see where they are before anything runs.

| At | Beat | On screen | Narration |
|---|---|---|---|
| 0:00 | Everything drawn | `damBreak` just opened, the BlockMesh tab: mesh, water column, two gauge lines | damBreak, just opened. Nothing has been opened yet, and the 3-D view already shows what the case defines: the mesh, the water column from setFieldsDict, and two gauge lines from a file called sampling. |
| 0:12 | The templates | **Tools > Add Function Object…**, placed to the left of the 3-D view | To add probes, you do not need to know how the dictionary is written. This list is not FoDE's own: it is the templates your OpenFOAM installation ships, so the form always matches the version you run. |
| 0:20 | A probe at the centre | Search `probes`; the template's form; a `probes` marker at the domain centre | The form shows only what the template sets. The probe does not start at the template's example, a corner of this case: FoDE put it at the centre of the mesh, read from blockMeshDict — and the 3-D view draws it while the dialog is open. |
| 0:29 | A row along the floor | Five points typed; the markers follow | A row of probes along the floor, where the water will run. The markers follow as the points are typed. |
| 0:37 | Which fields | `fields` set to `alpha.water p_rgh` | And which fields to record — the ▾ beside it lists the case's own. |
| 0:41 | Added | **Add**; `system/probes` joins the file list | Add writes system/probes and adds #includeFunc probes to controlDict, the way the tutorials do it. From now on the probes run with the solver. |
| 0:49 | Under their own name | `controlDict` selected; the probes beside the gauges in 3-D | And they stay in the 3-D view, beside the gauges, under their own name. |

The dialog would open centred over the window and hide the 3-D view, which is what the movie is about; a `place` step puts it over the file list instead, with the main splitter set so the view keeps the right half. The floor probes skip x = 0.25 on purpose: damBreak's obstacle sits there, a hole in the mesh, where a probe would find no cell.

## Movie 11 — A run that outlives FoDE (`damBreak`, ~85 s)

**Scene:** `damBreak-background-run`. **Case:** bundled `tutorials/damBreak`. **What it argues:** a long run does not have to be watched, or lost when the editor closes — and stopping it is safe.

| At | Beat | On screen | Narration |
|---|---|---|---|
| 0:00 | The case | `damBreak`; **Run blockMesh…** and **Run setFields…** in turn | A long run is one you do not want to babysit — or to lose when you close the editor. First, the mesh and the water column. |
| 0:26 | A long run | `controlDict` in the Tree tab; `endTime` set to `100` | Make it a long run: endTime 100 instead of 1. |
| 0:40 | Run Solver | **Tools > Run Solver…** | Run Solver offers to save the edit first, and one more box: keep running after FoDE closes. |
| 0:45 | In the background | **Keep running after FoDE closes** ticked; the command preview changes | Ticked, the run starts detached from the terminal, in a session of its own, writing its log directly — closing FoDE cannot stop it. |
| 0:50 | Running | The terminal follows the log; the **● interFoam running in background** badge; the file-list line | The terminal follows the log. A badge beside the case name says a run is going, the window title says so in the taskbar, and the file list has a line for it. Close FoDE now, and it keeps going; open the case again, and the badge is back. |
| 1:00 | Stop it | The badge's menu → **Stop Background Run** | To stop it, click the badge. |
| 1:04 | Ask the solver | The confirmation, naming the run and its pid | FoDE asks the solver to write the current time and stop, the OpenFOAM way — stopAt writeNow in controlDict. |
| 1:09 | The result | "interFoam has stopped. Last time written: …" and `stopAt` back to `endTime` | The badge turns to Stopping until the run has gone. Then a message says what happened: the last time written, and that stopAt is back as it was — so the next run does not stop at once. |

`endTime` is raised on camera because the bundled case runs to its end in about five seconds, too soon to stop; the edit is also the movie's point that a long run is worth detaching. The scene runs the real solver: its terminal prelude sources OpenFOAM v2606, and the take stops the run itself, so nothing is left running afterwards. The pid in the confirmation differs on every take.

## Movie 12 — Running in parallel (`damBreak`, ~100 s)

**Scene:** `damBreak-parallel-run`. **Case:** bundled `tutorials/damBreak`. **What it argues:** a parallel run is four steps that are easy to get wrong by hand — decompose, run on the right number of processors, reconstruct, and clean up without losing results — and the Tools menu does each one, checking as it goes.

Layout: the **BlockMesh** tab with a wider file list than the other scenes, because the file list's **Decomposed** line is how the movie shows where the results are.

| At | Beat | On screen | Narration |
|---|---|---|---|
| 0:00 | The case | `damBreak`; **Run blockMesh…** and **Run setFields…** in turn | A parallel run takes four steps that are easy to get wrong by hand. First, the mesh and the water column. |
| 0:27 | decomposePar | **Tools > Run decomposePar…**, then **Run** | decomposePar splits the case into the four pieces decomposeParDict asks for. |
| 0:32 | Decomposed | The file list's **Decomposed: 4 processors — times 0** line appears | The file list now says so: decomposed into four processors, and which times they hold. |
| 0:42 | Run Solver | **Tools > Run Solver…**: **Run in parallel** ticked, the command `mpirun -np 4 interFoam -parallel 2>&1 \| tee log.interFoam` | Run Solver sees the decomposition and ticks Run in parallel, with the processor count the case really has — mpirun, minus parallel. |
| 0:48 | Running in parallel | Four processes, one log; the Decomposed line turns orange as times land only in the processors | Four processes, one log. Their results are written into the processor directories, not the case — so the file list's processor line turns orange: those times exist nowhere else yet. |
| 1:05 | reconstructPar | **Tools > Run reconstructPar…**, `-newTimes` ticked | reconstructPar puts them back together — only the new times, by default. |
| 1:09 | Reconstructed | `Results: 0.05 0.1 …` appears at the case root; the Decomposed line is grey again | Now every time is at the case root too: the results line is back, and the processor line is no longer orange. |
| 1:21 | Delete processor* | **Tools > Delete processor\* Directories…**: *Permanently delete 5.5 MB…*, everything checked file by file, **Keep the latest time (1) and the decomposed mesh** ticked | The processor directories can go — but only once FoDE has checked, file by file, that the copy at the case root is complete. By default it keeps each processor's latest time, so the run can carry on in parallel without decomposing again. |
| 1:31 | Deleted | Status bar *Deleted the processor\* time directories except 1 (5.5 MB)*; the line reads **times 1** | Deleted — the status bar says what was kept, and the file list shows the one time left in the processors. |

The beat to protect is **1:21**: the confirmation is the one place the movie shows FoDE refusing to take the user's word for it, and its text — what will be deleted, what is kept, and that every file was checked — is the argument. The run itself takes about three seconds on four processors, so the 0:48 dwell is the narration's, not the solver's.

## Recording

```bash
DISPLAY=:1 python3 tools/demo_driver.py --list
```

Rehearse first — same take, no recording, so timings can be fixed cheaply:

```bash
DISPLAY=:1 python3 tools/demo_driver.py damBreak-end-to-end
```

Then record. With no filename the take lands in `docs/demo/<scene>.mp4`; `.gif` runs the same take through a two-pass palette encode for a README loop:

```bash
DISPLAY=:1 python3 tools/demo_driver.py damBreak-end-to-end --record
```

`cavity-full-workflow` needs two things the others do not. The shell it is started from must have OpenFOAM **sourced**, because the ParaView beat looks for `paraFoam` on `PATH` and silently falls back to a bare `paraview` with no case loaded if it is not there. And the take is longer than the watchdog's default, so raise it:

```bash
source /usr/lib/openfoam/openfoam2512/etc/bashrc
LIBGL_ALWAYS_SOFTWARE=1 DISPLAY=:1 python3 tools/demo_driver.py cavity-full-workflow \
    --record --max-seconds 420
```

`LIBGL_ALWAYS_SOFTWARE=1` is for ParaView, which renders through the nested display where there is no hardware GL to have. FoDE's own 3-D panel is not in this scene, so nothing else pays for it.

### Where the files live

**The videos are not tracked.** `docs/demo/*.mp4` is gitignored, and so are `.gif` and `.webm` beside it. A movie is a derived artifact — regenerate it from the scene — and video does not delta-compress, so every retake tracked would be a whole new multi-megabyte blob in history forever. The tooling exists to make retakes cheap, which is exactly what makes storing their output expensive. One set of seven is already several times the size of the entire screenshot gallery.

**The `.srt` files beside them are tracked.** A couple of kilobytes of plain text each, they diff cleanly, and they are the caption track to upload alongside the video. Each one pairs with the take it was recorded from, so re-record and re-upload together.

**Beside each is `<scene>.ja.srt`, the Japanese track.** It keeps the English cue timings and takes each line from the matching row of [DEMO_SCRIPTS_ja.md](DEMO_SCRIPTS_ja.md): `tools/make_ja_srt.py` finds every English cue, word for word, in this document's table and uses the Japanese row in the same position. Re-run it after a retake or a narration edit; `tests/tools/test_demo_specs.py` fails while a Japanese track is out of date, and the tool refuses a cue that matches no row rather than guessing.

**The published copies live on Vimeo**, which is what to link from a README, an issue or a release note — GitHub will not play a repository-relative `.mp4` inline in Markdown, so a tracked video would buy nothing a link does not.

The take runs on a **nested display of its own** (Xephyr), not the desktop it was started from — the steps are real mouse and keyboard input, so on a desktop in use another window raises itself into the click and the typing goes wherever focus went. Nothing to configure; it is the default. `--stage` is the exception: it opens the window in the scene's start state and stops, on the display you are looking at, for recording by hand.

Each take writes an `.srt` beside the video with the narration timed against the frames it belongs to — a script to read from, not a subtitle track to ship. Nothing is spoken by the tool.

**A movie must not put the recording user's name on screen.** The same rule as the gallery, and the reason scenes copy their case to `/tmp` rather than opening it in place: the Log Summary dialog prints the case path out of the log file, and this repository lives under a home directory.

That rule needed a second mitigation. A take also opens **file choosers**, and Qt's own chooser offers a **Home** shortcut in its sidebar — so the name went into the frame from there instead. A take now redirects `XDG_CONFIG_HOME` into its own scratch directory and seeds the sidebar with that directory, which fixes every chooser in every scene at once. It also means recording no longer edits your real `~/.config/QtProject.conf`, which it previously left its own `history` in. See [Demo recording](../DEVELOPER.md#demo-recording) for why `$HOME` is deliberately left alone.

**Check the frames where a chooser is open** before publishing a retake, not an evenly spaced sample — those are the windows this rule is about.
