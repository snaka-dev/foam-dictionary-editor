## Changes from upstream

This case is redistributed **unmodified** from the upstream tutorial
(`incompressible/simpleFoam/pitzDaily`, OpenFOAM v2512); no dictionary entries
have been changed.

Upstream ships no `Allrun` script for this case, so none is included here: it
is run as `blockMesh` then `simpleFoam`, both available from FoDE's Tools menu
or from the terminal panel.

## Why it is bundled

It is the only bundled case with a turbulence model — every other one is
laminar — so it is where `constant/turbulenceProperties` and the schema help
for the model selector and its coefficients can be seen on a real case.

`system/controlDict` also ends in `#includeFunc streamlines`, and
`system/streamlines` in `#includeEtc`, which makes the case a working example
of the include resolution in the file list.
