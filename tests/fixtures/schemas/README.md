# Schema coverage fixtures

Real OpenFOAM dictionaries, copied unmodified from the tutorials shipped with
OpenCFD v2606 (`/usr/lib/openfoam/openfoam2606/tutorials`):

| fixture | source |
|---|---|
| `fvSchemes`, `fvSolution`, `controlDict`, `blockMeshDict`, `turbulenceProperties` | `incompressible/simpleFoam/pitzDaily` |
| `snappyHexMeshDict` | `incompressible/pisoFoam/LES/motorBike/motorBike` |

They are here so `test_schema_coverage.py` can measure schema coverage against
genuine dictionaries without assuming an OpenFOAM installation is present. Keep
them byte-identical to upstream — the point is that they are not curated to fit
the schema. `snappyHexMeshDict` in particular still contains `minFlatness`,
the key OpenFOAM silently ignores, which is exactly what one of the tests
asserts we warn about.

These are verbatim OpenFOAM tutorial dictionaries, licensed GPL-3.0-or-later.
They were taken from the OpenCFD (openfoam.com) distribution, so OpenCFD Ltd
holds the copyright in them — but note that is specific to *these* files.
Upstream material elsewhere in this repository is held by several parties;
`THIRD-PARTY.md` records who holds what, generated from the sources rather
than assumed.
