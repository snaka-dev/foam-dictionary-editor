# FoDE example cases — provenance and license

This directory contains example OpenFOAM cases used in the Foam Dictionary
Editor (FoDE) documentation and in the article "Foam Dictionary Editor: A
GUI-based open-source tool for OpenFOAM case configuration." They are provided
so that users can try FoDE on real cases and reproduce the worked tutorials.

## Cases included

| Directory                         | Origin                                                           | Solver               | Purpose in FoDE docs                                                                  |
|-----------------------------------|------------------------------------------------------------------|----------------------|---------------------------------------------------------------------------------------|
| `cavity/cavity/`                  | `incompressible/icoFoam/cavity/cavity`                           | `icoFoam`            | Single-region, end-to-end workflow walkthrough                                        |
| `cavity/cavityGrade/`             | `incompressible/icoFoam/cavity/cavityGrade`                      | `icoFoam`            | Non-uniform grading; tests `simpleGrading` in `blockMeshDict`                         |
| `cavity/cavityClipped/`           | `incompressible/icoFoam/cavity/cavityClipped`                    | `icoFoam`            | Clipped geometry; tests `mapFieldsDict` and non-rectangular block topology            |
| `snappyMultiRegionHeater/`        | `heatTransfer/chtMultiRegionFoam/snappyMultiRegionHeater`        | `chtMultiRegionFoam` | Multi-region overview, boundary view, symbolic links                                  |
| `damBreak/`                       | `multiphase/interFoam/laminar/damBreak/damBreak`                 | `interFoam`          | Tests `setFieldsDict` (`defaultFieldValues`/`regions`), `0.orig/`, `sampling`         |
| `oneBlocks/`                      | Derived from `cavity` (custom `blockMeshDict`)                   | `icoFoam`            | 3-D single-block case; tests basic `blockMeshDict` editing and 3-D mesh viewer        |
| `oneBlocks-vars/`                 | Derived from `cavity` (custom `blockMeshDict`)                   | `icoFoam`            | As `oneBlocks` but uses variable definitions and compact face notation `(block face)` |
| `nineBlocks/`                     | Derived from `cavity` (custom `blockMeshDict`)                   | `icoFoam`            | 3×3 multi-block case; tests multi-block `blockMeshDict` and regex boundary patches    |
| `nineBlocks-vars/`                | Derived from `cavity` (custom `blockMeshDict`)                   | `icoFoam`            | As `nineBlocks` but uses variable definitions and compact face notation                |
| `topoSetShapes/`                  | Custom (single 3×3×3 block + `topoSetDict`)                      | `icoFoam`            | Tests `topoSetDict` geometry overlay in the 3-D viewer (box incl. `min`/`max` and `boxes` forms, sphere incl. hollow `origin`+`innerRadius`, cylinder/cone family, point markers, `planeToFaceZone`, `$var`/`#eval`) |

The `cavity/` subdirectories, `snappyMultiRegionHeater`, and `damBreak` are
taken unchanged from the standard tutorial set distributed with OpenFOAM
(OpenCFD/ESI, OpenFOAM v2512).

`snappyMultiRegionHeater/0/` is not present in the
original source (it is generated at run time by `./Allrun`); the
copy here was produced from a completed run of that tutorial.

The `oneBlocks`, `oneBlocks-vars`, `nineBlocks`, `nineBlocks-vars`, and
`topoSetShapes` cases are custom cases created for FoDE testing. Their
`system/controlDict`, `system/fvSchemes`, `system/fvSolution`,
`system/decomposeParDict`, and `constant/transportProperties` files are taken
from or closely follow the standard `cavity` tutorial; the
`system/blockMeshDict` files are custom-authored.  The two `-vars` variants
exercise two features not present in the plain variants: variable substitution
(`$var`) and the compact block-face notation `(blockId faceId)` in the
`boundary` section.  `topoSetShapes` adds a custom `system/topoSetDict` that
demonstrates every geometry source rendered by the BlockMesh 3-D panel.

Any modifications made for the FoDE tutorials (e.g. duplication into a working
copy, minor edits to dictionary entries shown in the walkthroughs) are limited
to the dictionary files and are described in the per-case README in each
subdirectory where applicable.

## License of these cases

> **These example cases are NOT covered by the license of the FoDE source code.**

OpenFOAM, and the tutorial cases distributed with it, are licensed under the
**GNU General Public License, version 3 (GPL-3.0)**. The case files in this
directory are redistributed under that same license. A copy of the GPL-3.0 text
is provided in [`COPYING.GPL-3.0`](./COPYING.GPL-3.0); the canonical text is also
available at <https://www.gnu.org/licenses/gpl-3.0.html>.

Copyright for the original tutorial cases is held by their respective OpenFOAM
copyright holders (OpenCFD Ltd. / ESI Group and/or the OpenFOAM Foundation).
This redistribution does not transfer or alter that copyright.

## Relationship to the FoDE license

The Foam Dictionary Editor application itself (all source code outside this
`tutorials/` directory) is licensed under the **GNU Affero General Public
License, version 3 or later (AGPL-3.0-or-later)**. See the top-level
[`LICENSE`](../LICENSE).

These example cases are independent data files that FoDE operates on; they are
not linked into, or incorporated by, the application. They are included here as
an aggregate of separately licensed works. The AGPL-3.0 terms that govern the
FoDE source code do **not** extend to these GPL-3.0 case files, and the GPL-3.0
terms that govern the case files do **not** extend to the FoDE source code.
GPL-3.0 and AGPL-3.0 are mutually compatible (see section 13 of each license),
so the two may be distributed together in this repository.

## Trademark and affiliation

OpenFOAM® is a registered trademark of OpenCFD Ltd. Foam Dictionary Editor
(FoDE) is an independent project and is **not** affiliated with, endorsed by, or
certified by OpenCFD Ltd., ESI Group, or the OpenFOAM Foundation. The OpenFOAM
name is used here only to identify the cases and the software with which FoDE is
designed to interoperate.

## If you redistribute these cases

Under the GPL-3.0 you are free to use, modify, and redistribute these case
files, provided you:

- keep this notice and the `COPYING.GPL-3.0` license text with them;
- preserve the existing file headers/notices in the case files; and
- if you modify a case file, state that you changed it and when.
