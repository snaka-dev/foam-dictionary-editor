## topoSetShapes — topoSetDict geometry demo

A minimal case whose `system/topoSetDict` exercises every geometry source that the
BlockMesh 3-D panel can overlay. Open the case, open `system/blockMeshDict` (the mesh
renders), then open `system/topoSetDict` and use the **"topoSet ▾"** menu in the panel
toolbar — the **"Show topoSet geometry"** toggle enables the overlay, each shape
below has its own checkbox so you can isolate or hide it individually, and
**Show all shapes** / **Hide all shapes** switch every checkbox at once — to see all
fourteen shapes drawn inside the 3×3×3 domain.

### Mesh

`system/blockMeshDict` — a single hex block over a 3×3×3 m domain with six named patches
(`xMin`, `xMax`, `yMin`, `yMax`, `zMin`, `zMax`). `0/U`, `0/p` use regex `boundaryField`
patterns matching those patches; `system/{controlDict,fvSchemes,fvSolution}` and
`constant/transportProperties` are the standard `icoFoam/cavity` dictionaries.

### topoSetDict shapes

Shapes are drawn as overlays for visualisation — `topoSet` is not actually run. The panel
colours each shape by its `action`: **new** = steel-blue, **add** = green,
**subtract**/**delete** = red, **subset** = purple, **invert** = gold.

| name       | source                  | action   | notes                          |
|------------|-------------------------|----------|--------------------------------|
| `box0`     | `boxToCell`             | new      | axis-aligned box               |
| `ball`     | `sphereToCell`          | add      | centre/radius via `$variables` |
| `pipe`     | `cylinderToCell`        | add      | vertical cylinder              |
| `ring`     | `cylinderAnnulusToCell` | new      | hollow cylinder                |
| `frustum`  | `coneToCell`            | invert   | truncated cone (`radius2` > 0) |
| `spike`    | `coneToCell`            | subtract | true cone (`radius2 0`) + `#eval` on the apex height |
| `coneRing` | `coneAnnulusToCell`     | new      | hollow cone                    |
| `core`     | `boxToCell`             | subset   | box, intersection with the set |
| `tilted`   | `rotatedBoxToCell`      | add      | oriented box (`origin` + `i`/`j`/`k`) |
| `slab`     | `boxToCell`             | add      | box via the `min`/`max` key pair |
| `twinBoxes`| `boxToCell`             | new      | two boxes from one `boxes ( … )` list |
| `shell`    | `sphereToCell`          | new      | hollow sphere via `origin` + `innerRadius` |
| `probes`   | `nearestToCell`         | new      | three points drawn as labelled markers |
| `midPlane` | `planeToFaceZone`       | new      | plane drawn as a disc sized to the scene bounds |

The `ball` entry demonstrates top-level `$variable` resolution (`ballX`/`ballY`/`ballZ`,
`ballR`) and `spike` demonstrates inline `#eval{ }` resolution; both are evaluated before
extraction.

### Non-geometric source

The dict also has a `coreFaces` entry (`cellToFace`, promoting `core`'s cells to their
boundary faces). It carries no drawable geometry, so it isn't overlaid in the 3-D view —
it's listed greyed-out under the **"Non-geometric sources (1)"** submenu of the
**"topoSet ▾"** menu as *"coreFaces · cellToFace (no geometry)"* so its presence in
the dict is still visible.
