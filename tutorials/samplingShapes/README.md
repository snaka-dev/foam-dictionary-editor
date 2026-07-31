## samplingShapes — sampling geometry demo

A minimal case whose sampling dictionaries exercise every kind of geometry that the
BlockMesh 3-D panel can overlay for sampling, spread across the three places FoDE
reads sampling from. Open the case, open `system/blockMeshDict` (the mesh renders),
then open `system/controlDict`, `system/sample` and `system/surfaces` and use the
**"sample ▾"** menu in the panel toolbar — the **"Show sampling geometry"** toggle
enables the overlay, each definition below has its own checkbox, and **Show all
shapes** / **Hide all shapes** switch every checkbox at once.

This is the sampling counterpart of [`topoSetShapes`](../topoSetShapes/README.md).

### Mesh

`system/blockMeshDict` — a single hex block over a 3×3×3 m domain with six named
patches (`xMin`, `xMax`, `yMin`, `yMax`, `zMin`, `zMax`), the same mesh
`topoSetShapes` uses. `0/U`, `0/p`, `system/{fvSchemes,fvSolution}` and
`constant/transportProperties` are the standard `icoFoam/cavity` dictionaries.

### Where the definitions live

Sampling is unusual among the overlays in having no single dictionary of its own, so
the case covers all three sources at once. The panel merges them and tags each row in
the **"sample ▾"** menu with the file it came from.

| file                | form                                          | definitions                  |
|---------------------|-----------------------------------------------|------------------------------|
| `system/controlDict`| function object inside `functions { }`         | `nearWallProbes`             |
| `system/sample`     | standalone dict, `sets { name { … } }`         | `topSpan`, `riser`, `scatter`|
| `system/surfaces`   | standalone dict, `surfaces ( name { … } );`    | `midCut`, `lowCut`, `outerWall` |

The two standalone files deliberately use the two different member-list syntaxes
OpenFOAM accepts — the dictionary form and the classic parenthesised list — because
they are separate paths through the parser.

### Shapes

Sampling is not actually run; the shapes are drawn for visualisation only.

| name             | type           | drawn as                                        |
|------------------|----------------|-------------------------------------------------|
| `nearWallProbes` | `probes`       | point markers at each `probeLocations` entry     |
| `topSpan`        | `lineUniform`  | a tube from `start` to `end`                     |
| `riser`          | `face`         | a tube from `start` to `end`                     |
| `scatter`        | `cloud`        | point markers, from a `points` list rather than a span |
| `midCut`         | `cuttingPlane` | a disc, from a direct `point`/`normal` pair      |
| `lowCut`         | `plane`        | a disc, from a `pointAndNormalDict { }`          |

### Why the shapes are spread out

Each shape's name badge is drawn at that shape's own centre, so shapes whose centres
project to the same place on screen stack their badges into an unreadable pile. The
positions here are chosen so that all six badges stay legible from the default
isometric view. Note that a plane's badge does **not** follow the `point` it names:
the disc is cut back to the mesh first, so its badge lands near the middle of the
domain whichever point is given. That is why the sets and probes are the ones pushed
out towards the edges.

Both planes are badged **"(clipped)"**, which is correct and worth seeing: a plane is
unbounded, so the disc is display-only and always larger than the mesh it is shown in.

### Non-geometric source

`system/surfaces` also has an `outerWall` entry (`type patch`), which samples an
existing boundary and so carries no geometry of its own. It is not dropped silently —
it is listed greyed-out under the **"Non-geometric sources (1)"** submenu of the
**"sample ▾"** menu.

`system/controlDict` additionally has a `minMaxP` (`fieldMinMax`) function object. That
is not a sampling function object at all, so it is ignored entirely rather than listed
as a source without geometry — the two cases are different and the menu shows the
difference.
