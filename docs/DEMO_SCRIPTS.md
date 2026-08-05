# FoDE — Demo Movie Scripts

Shot-by-shot scripts for the demo movies, and how to record them. For the still gallery see [SCREENSHOTS.md](SCREENSHOTS.md); for the feature reference see [USER_GUIDE.md](../USER_GUIDE.md).

Every movie below is **scripted in full and runs**: `tools/demo_driver.py` drives the window through each one and records it, from the scenes in `tools/demo_specs.json`. See [Demo recording](../DEVELOPER.md#demo-recording) for how the driver works.

| Movie | Scene | Case | Length | Published |
|---|---|---|---|---|
| 1 — Edit, see, run | `damBreak-end-to-end` | bundled `tutorials/damBreak` | ~74 s | https://youtu.be/kGxfNhAe6xo |
| 2 — It draws your dictionaries | `topoSet-overlay-tour` | bundled `tutorials/topoSetShapes` | ~68 s | https://youtu.be/q5jITY-HIp4 |
| 3 — Working across cases | `cavity-boundary-and-compare` | bundled `tutorials/cavity` | ~43 s | https://youtu.be/FlltvZQrE1k |
| 4 — Meshing around a surface | `motorBike-snappy-overlay` | `{cases}/motorBike` — **not** bundled | ~57 s | https://youtu.be/J06LACn9Njc |
| 5 — Three files, one view | `sampling-three-files-one-view` | bundled `tutorials/samplingShapes` | ~50 s | https://youtu.be/ygXHtzqUZ_A |
| 6 — Five meshes, one case | `multiRegion-five-meshes-one-case` | bundled `tutorials/snappyMultiRegionHeater` | ~31 s | https://youtu.be/exLu67fW-WU |
| 7 — The whole workflow | `cavity-full-workflow` | bundled `tutorials/cavity` | ~3 min 38 s | https://youtu.be/0FZPb92luw8 |

## Choosing what to show

Short movies rather than one long one, because they answer different questions and nobody has all of them. The first three make the general case — *why would I use this*, *what does it look like*, *how does it fit my work* — and are the ones to show someone who has never seen FoDE. The rest each go deeper into one dictionary family, for someone who already knows they have that particular problem: meshing around a surface, sampling, multi-region cases. Someone who bounces off the first minute has still seen the argument.

**Movie 7 is the deliberate exception**, at more than three times the length of any other. It is Appendix A of the SoftwareX paper — the worked icoFoam/cavity example — recorded, so a reader who has just finished the appendix can watch it happen instead of imagining it. The argument for keeping the others short does not apply to it: its audience has already decided to try the tool and is asking what a whole case looks like from one end to the other, which is a question that cannot be answered in a minute. It is the one to link from the paper, and the wrong one to open with.

Each scene prefers a case from the repository's own `tutorials/` over one from an OpenFOAM installation. A bundled case makes the movie **replayable by anyone who clones the repository**, and it makes the recording reproducible: the driver copies the case to a scratch directory before every take, so a movie that runs `blockMesh` starts from a case with no mesh, every time.

## Movie 1 — Edit, see, run (`damBreak`, ~65 s)

**Scene:** `damBreak-end-to-end`. **Case:** bundled `tutorials/damBreak`. **What it argues:** the dictionary, the geometry it describes and the tool that consumes it are one loop, and FoDE closes it.

Layout: side-by-side, so the tree and the 3-D view are on screen together — the whole point of the movie is that an edit in one lands in the other. The detail pane is collapsed to give both the width.

| At | Beat | On screen | Narration |
|---|---|---|---|
| 0:00 | Open | The case is loaded, `blockMeshDict` open, the block mesh drawn beside the tree | This is an OpenFOAM case — the damBreak tutorial — open in FoDE. The dictionary is a tree on the left, the mesh it describes is drawn on the right. |
| 0:04 | Open `setFieldsDict` | Click the file; the orange water column appears inside the mesh, badged `alpha.water=1 (clipped)` | Open setFieldsDict, and the region it initialises is drawn straight onto that mesh. |
| 0:09 | Select the `box` row | The tree row highlights; the editor below scrolls to line 26 and marks it | Select the box that defines it, and the editor below jumps to the line it came from. |
| 0:15 | Edit the value | Double-click the Value cell, type `(0 0 -1) (0.35 0.4 1)` | Change the water column — make it wider and taller. |
| 0:17 | The overlay follows | Enter: the orange box grows, the editor line rewrites, all three views agree | The overlay follows the edit. No re-run, no export, no guessing at coordinates. |
| 0:22 | Save | **Save File** | Save the file. |
| 0:26 | Run blockMesh | **Tools > Run blockMesh…**, then **Run** | The mesh has to exist before the fields can be set, so run blockMesh. |
| 0:31 | It runs | The Terminal tab fills; the file list grows a `constant/polyMesh: 2,268 cells` indicator as it lands | It runs in the Terminal tab, in the case directory, and tees its output to a log. |
| 0:40 | The setFields dialog | The dialog: the compounding-values warning, **Restore 0/ from 0.orig/ first** checked, and the command preview `rm -rf 0 && cp -r 0.orig 0 && setFields 2>&1 \| tee log.setFields` | Now setFields. The dialog offers the flags rather than asking you to remember them, and shows the exact command it will send. setFields rewrites 0/ in place, so it offers to restore 0/ from 0.orig first — checked by default, and visible in the command. |
| 0:48 | It runs | `Selected 1012/2268 cells` — the count follows from the box that was edited at 0:15 | Run it. |
| 0:57 | Log summary | **Tools > View Log Summary…**: utility, build, case, tail, `Result: OK` | And the logs those runs left behind are condensed to a report: what ran, what it produced, and every warning it printed. |

Two beats are the ones worth protecting in any re-cut. **0:17**, because the three-way sync is the thing no other editor does. And **0:48**, because `Selected 1012/2268 cells` is the edit from 0:15 coming back as a number — the loop visibly closing, rather than a claim that it does.

The `then` dwell on each step is sized to its narration, at roughly the speed the line can be read aloud. A step whose caption is three sentences (the setFields dialog) holds for eight seconds; `Save the file.` holds for two.

## Movie 2 — It draws your dictionaries (`topoSetShapes`, ~68 s)

**Scene:** `topoSet-overlay-tour`. **Case:** bundled `tutorials/topoSetShapes`. **What it argues:** you can see what a dictionary says before running anything — and nothing is run here, so the movie plays on a machine with no OpenFOAM at all.

Layout: the **BlockMesh** tab full width, because here the 3-D view is the argument rather than a companion to the tree.

| At | Beat | On screen | Narration |
|---|---|---|---|
| 0:00 | Open | Every shape at once inside the block mesh, each badged, coloured by the action that produced it | This case's topoSetDict exercises every geometry source the viewer can draw — boxes, spheres, cylinders, cones, points, planes. Nothing has been run here. This is the dictionary, drawn. |
| 0:05 | Orbit | Drag in the view; the scene turns | It is a real 3-D scene, so you can look at it from anywhere. |
| 0:11 | The `topoSet ▾` menu | Every source as a row, with the action-colour legend above | Every source in the dictionary is a row in this menu, coloured by the action that produced it — new, add, subtract. |
| 0:15 | Uncheck three | `ball`, `pipe`, `twinBoxes` unchecked; the menu stays open throughout | Uncheck the ones you are not interested in — the menu stays open, so you can work through a list. |
| 0:20 | The rest of the menu | Cursor down the rows to `Non-geometric sources (1)` | Sources with no geometry to draw are not silently dropped either — the last row counts them, so the menu accounts for the whole dictionary. |
| 0:24 | The scene without them | Escape; the three shapes are gone from an otherwise unchanged scene | And the scene is left with what you asked for. |
| 0:31 | Show all | Reopen, **Show all shapes**; they return | Show all brings them back. |
| 0:36 | Clipping | The `midPlane (clipped)` badge | A shape reaching past the block mesh is drawn cut down to it, and its badge says so. That is display only — the dictionary is untouched, and an export writes the whole shape. |
| 0:43 | Tree to editor | Tree tab, select a source; the editor scrolls to its lines | Select a source in the tree and the editor scrolls to the lines that define it — the same two-way link every dictionary has here. |
| 0:53 | Export | **STL ▾ > Export Shapes as STL…**: every shape as a checkable row | Which is what this does. Every shape on screen can be written out as STL — real geometry, not a sketch. |

The beat to protect is **0:15–0:31**: unchecking shapes, closing the menu to see the result, then bringing them back. It is the only part that shows the overlay is a working instrument rather than a picture. Note that the menu is dismissed *before* the reveal — it is tall enough to cover the shapes it is changing, so leaving it open would hide the very thing the beat is about.

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

## Movie 4 — Meshing around a surface (`motorBike`, ~57 s)

**Scene:** `motorBike-snappy-overlay`. **Case:** `motorBike`, from the recording machine's run directory (`{cases}`) — the one movie that is **not** replayable from a bare checkout, because the case is not bundled. **What it argues:** `snappyHexMeshDict` is mostly references to things you cannot see, and FoDE draws them.

| At | Beat | On screen | Narration |
|---|---|---|---|
| 0:00 | Open | The motorBike surface in teal inside the background block mesh, the purple `refinementBox`, the `locationInMesh` marker | snappyHexMesh builds a mesh around a surface, and its dictionary is mostly references to things you cannot see: a geometry file, a refinement region, a point that decides which side is fluid. Open it here and they are drawn — inside the background mesh they will be cut from. |
| 0:06 | Orbit | The scene turns | The bike is the triSurface the dictionary names, resolved from constant/triSurface and loaded for you. |
| 0:12 | Zoom | Scroll in; the bike resolves into an actual motorcycle | Zoom in and it is the real surface, not a bounding box standing in for it. |
| 0:19 | The `snappyHexMesh ▾` menu | Rows grouped by category, with the surface/region/geometry legend and the keep-point row | The rows are classified by how the dictionary uses each one — surfaces to snap to, regions to refine by, and the keep-point — because that is the distinction that matters when a mesh comes out wrong. |
| 0:26 | The box alone | The bike unchecked; the refinement box left in the domain | Hide the bike and the refinement region is left on its own — which is the thing you actually want to check. Does it enclose what it is meant to refine, and is it inside the background mesh at all? |
| 0:35 | Tree to editor | `refinementRegions/refinementBox` selected; the editor scrolls to it | Select the region in the tree and the editor goes to the entry that defines it — the refinement levels, and the mode that says whether inside or outside is the part being refined. |
| 0:44 | The keep-point | The `locationInMesh` marker | And the marker is locationInMesh: the single point that tells snappyHexMesh which side of the surface to keep. Put it on the wrong side and the mesher happily deletes the domain instead of the bike. It is one line in the dictionary, and now it is somewhere you can look at. |

Two things about this scene are worth knowing before re-cutting it.

**The camera pops back out at 0:26.** Hiding a shape re-renders, and every render ends in `reset_camera()` — so the zoom from 0:12 is undone. It is not a glitch to fix in the take; it is what the panel does. Here it happens to serve the line it lands on, which asks whether the box sits inside the *whole* domain, so the wide framing is the right answer to the question being asked.

**The orbit is set to `"ticks": 6`.** Each increment of a drag costs a re-render, and this surface is heavy enough that the default granularity turned a 1.4-second orbit into a 24-second one. Fewer, larger steps stay smooth, because what is slow is the frames rather than the motion.

`motorBike`'s sampling dictionary is `system/cuttingPlane`, which FoDE does not recognise as a sampling dict — `SAMPLING_DICT_NAMES` covers `sample`, `probes`, `surfaces`, `singleGraph` and `controlDict` — so the sampling overlay does not appear in this movie. The sampling counterpart is `tutorials/samplingShapes`, which is bundled and was built for it.

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

## Movie 6 — Five meshes, one case (`snappyMultiRegionHeater`, ~31 s)

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

## Movie 7 — The whole workflow (`cavity`, ~3 min 38 s)

**Scene:** `cavity-full-workflow`. **Case:** bundled `tutorials/cavity/cavity`. **What it argues:** everything the other six show in isolation is one continuous piece of work, and it fits in one window. This is [Appendix A of the SoftwareX paper](https://doi.org/10.1016/j.softx.2026.102852) — the lid-driven cavity solved with icoFoam — shot beat for beat, section A.2 through A.7.

Layout: no 3-D view, and the detail panel given real width instead of being collapsed — the schema drop-down is one of the beats. The window opens with **no case loaded at all**, which no other scene does: the first act is the case arriving.

| At | Beat | On screen | Narration |
|---|---|---|---|
| 0:00 | An empty window | Nothing loaded; the Tools menu correctly disabled | This is the worked example from the FoDE paper: the lid-driven cavity, solved with icoFoam, from nothing to a result — without leaving the editor. |
| 0:08 | The case library | **Case > Duplicate from Case Library…**, the chooser on the tutorials tree | A case starts as a copy of another one. The case library is where the tutorials live, and duplicating from it leaves the original untouched. |
| 0:14 | The Duplicate Case dialog | Source, destination, live preview, the two copy modes | The dialog asks where the copy goes, what to call it, and how much to copy — the whole directory, or only the dictionaries FoDE recognises. |
| 0:19 | Name it | `cavity_copy` → `cavity`, the preview following each keystroke | It proposes the source name with a copy suffix. Drop the suffix: this working case is just cavity. |
| 0:34 | The dictionaries of a case | The file list grouped `system`, `constant`, `0` | Here is the whole case in one pane: controlDict, blockMeshDict, fvSchemes and fvSolution under system, transportProperties under constant, and the velocity and pressure fields under zero. |
| 0:41 | The `[+]` marker | Right-click the `system` header → **Add files from 'system'…** → `PDRblockMeshDict` | A directory marked with a plus holds files the list does not show by default. Ask for them, and here is the one this case has. |
| 0:55 | controlDict in the tree | Tree row selected, the editor below scrolled to line 29 and marked | controlDict, parsed into a tree. The editor holds the same file as text, and follows the tree. |
| 1:00 | The schema-driven detail panel | `writeControl` selected: Key Help, Key Supported In, Key Note, Choices, Choice Help | Select writeControl and the detail panel explains it — what the key does, which distributions support it, and the values it accepts. |
| 1:09 | The documented choices | The drop-down open: `timeStep`, `runTime`, `adjustableRunTime`, `cpuTime`, `clockTime` | The choices are a drop-down rather than something to remember, each with its own note. |
| 1:20 | The tree context menu | On `fvSchemes`' `ddtSchemes`: copy/paste value, add, duplicate, comment out, delete | Entries are edited in the tree itself. |
| 1:28 | The boundary table | `p` and `U` against `fixedWalls` / `frontAndBack` / `movingWall` | Boundary conditions live in a file per field, so reading them as a set means opening every one. The Boundary tab gathers them into a table instead. |
| 1:39 | Lines per cell | The spin box to 3; `value  uniform (1 0 0)` appears under `fixedValue` | Raise the lines per cell and the entries come with it, so the values are there too. |
| 1:45 | A cell, and its file | The `U` / `movingWall` cell selected; `0/U` opens at line 23, status bar *Parsed successfully* | Select a cell and the file it came from opens with that entry highlighted. |
| 1:56 | The terminal | The Terminal tab, already in the case directory | The case is ready to run, and the terminal is already in its directory. |
| 2:03 | blockMesh | Typed by hand, teed to `log.blockMesh`; `constant/polyMesh: 400 cells` lands in the file list | blockMesh builds the mesh from blockMeshDict. It runs in the same window the dictionaries were edited in. |
| 2:13 | icoFoam | Residuals scrolling; `Results: 0.1 0.2 0.3 0.4 0.5` appearing in the file list | Then icoFoam advances the solution to half a second. Four hundred cells, so it is over almost as soon as it starts. |
| 2:24 | The run, condensed | **Tools > View Log Summary…** over `log.blockMesh` and `log.icoFoam` | Those runs left logs behind, and FoDE condenses them. |
| 2:38 | ParaView | **Tools > Open Mesh in ParaView…**; `paraFoam -case` on the open case | And the result goes to ParaView, on the case that is open, from the same menu as everything else. |
| 3:26 | Velocity magnitude | Apply, last time step, coloured by `U` magnitude: the lid red along the top, the vortex under it | Colour it by velocity magnitude, and there is the lid-driven cavity. One case, one window, from an empty editor to that. |

Three beats are the ones to protect in a re-cut. **1:09**, because the schema drop-down is the feature the paper spends the most words on and the hardest to convey in a still. **1:45**, because the boundary table producing the file *and the line* is the aggregation paying for itself. And **2:13**, because the file list growing a time-directory row while the solver is still printing is the whole "one window" claim, unarguable and in passing.

This is the only scene that drives an application other than FoDE. ParaView resolves nothing semantically — it is not our window — so its four clicks are `point` steps, pixel coordinates read off a rehearsal screenshot. They hold because the take runs on a display of a known size with no window manager, so ParaView opens at the origin at 1280×800 every time; they are the first thing to break if that changes, and re-reading them is a rehearsal and a screenshot.

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

**The published copies live on YouTube**, which is what to link from a README, an issue or a release note — GitHub will not play a repository-relative `.mp4` inline in Markdown, so a tracked video would buy nothing a link does not.

The take runs on a **nested display of its own** (Xephyr), not the desktop it was started from — the steps are real mouse and keyboard input, so on a desktop in use another window raises itself into the click and the typing goes wherever focus went. Nothing to configure; it is the default. `--stage` is the exception: it opens the window in the scene's start state and stops, on the display you are looking at, for recording by hand.

Each take writes an `.srt` beside the video with the narration timed against the frames it belongs to — a script to read from, not a subtitle track to ship. Nothing is spoken by the tool.

**A movie must not put the recording user's name on screen.** The same rule as the gallery, and the reason scenes copy their case to `/tmp` rather than opening it in place: the Log Summary dialog prints the case path out of the log file, and this repository lives under a home directory.
