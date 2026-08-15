# Schema coverage fixtures

Real OpenFOAM dictionaries, copied unmodified from the tutorials shipped with
OpenCFD v2606 (`/usr/lib/openfoam/openfoam2606/tutorials`), except where the
fork column says otherwise:

| fixture | fork | source |
|---|---|---|
| `fvSchemes`, `fvSolution`, `controlDict`, `blockMeshDict`, `turbulenceProperties` | OpenCFD v2606 | `incompressible/simpleFoam/pitzDaily` |
| `snappyHexMeshDict` | OpenCFD v2606 | `incompressible/pisoFoam/LES/motorBike/motorBike` |
| `transportProperties` | OpenCFD v2606 | `incompressible/nonNewtonianIcoFoam/offsetCylinder` |
| `physicalProperties` | **Foundation 14** | `incompressibleFluid/moodyChart` |

`physicalProperties` has to come from Foundation, because OpenCFD has no such
file: Foundation renamed `constant/transportProperties` to
`constant/physicalProperties` at v10 and moved the non-Newtonian viscosity
models into the momentum-transport tree at the same time, so the two files are
not the same dictionary under two names. The pair is what makes that visible —
`transportProperties` selects `CrossPowerLaw` and carries its coefficients,
while `physicalProperties` carries `viscosityModel constant;` and `nu`.

They are here so `test_schema_coverage.py` can measure schema coverage against
genuine dictionaries without assuming an OpenFOAM installation is present. Keep
them byte-identical to upstream — the point is that they are not curated to fit
the schema. `snappyHexMeshDict` in particular still contains `minFlatness`,
the key OpenFOAM silently ignores, which is exactly what one of the tests
asserts we warn about.

These are verbatim OpenFOAM tutorial dictionaries, licensed GPL-3.0-or-later.
All but one were taken from the OpenCFD (openfoam.com) distribution, so OpenCFD
Ltd holds the copyright in those; `physicalProperties` comes from the OpenFOAM
Foundation (openfoam.org) distribution and is held by the OpenFOAM Foundation.
Note that this is specific to *these* files.
Upstream material elsewhere in this repository is held by several parties;
`THIRD-PARTY.md` records who holds what, generated from the sources rather
than assumed.
