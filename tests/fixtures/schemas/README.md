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

OpenFOAM is distributed under the GPL; these files are Copyright OpenCFD Ltd.
