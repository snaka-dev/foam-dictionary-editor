# FoDE example cases — provenance and license

This directory contains example OpenFOAM cases used in the Foam Dictionary
Editor (FoDE) documentation and in the article "Foam Dictionary Editor: A
GUI-based open-source tool for OpenFOAM case configuration." They are provided
so that users can try FoDE on real cases and reproduce the worked tutorials.

## Cases included

| Directory                  | Source tutorial                                   | Solver               | Purpose in FoDE docs                                  |
|----------------------------|---------------------------------------------------|----------------------|-------------------------------------------------------|
| `cavity/`                  | `incompressible/icoFoam/cavity/cavity`            | `icoFoam`            | Single-region, end-to-end workflow walkthrough        |
| `snappyMultiRegionHeater/` | `heatTransfer/chtMultiRegionFoam/snappyMultiRegionHeater` | `chtMultiRegionFoam` | Multi-region overview, boundary view, symbolic links  |

Both cases are taken from the standard tutorial set distributed with OpenFOAM
(OpenCFD/ESI, OpenFOAM v2512). Any modifications made for the FoDE tutorials
(e.g. duplication into a working copy, minor edits to dictionary entries shown
in the walkthroughs) are limited to the dictionary files and are described in
the per-case README in each subdirectory.

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
