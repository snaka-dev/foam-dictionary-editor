## Changes from upstream

Derived from the upstream `icoFoam/cavity` tutorial.

- `system/controlDict`, `system/fvSchemes`, `system/fvSolution`,
  `system/decomposeParDict`, and `constant/transportProperties` are taken
  unchanged from the standard `cavity` case.
- `system/blockMeshDict` is custom-authored: a 3-D 3×3 multi-block mesh (9
  blocks) over a 3×3×3 m domain with six named patches (`xMin`, `xMax`,
  `yMin`, `yMax`, `zMin`, `zMax`).
- `0/U` and `0/p` are custom-authored to match the new patch names, using
  regex patterns (`"(xMin|xMax)"`, `"x.*"`, `"(yMin|yMax|zMin|zMax)"`,
  `"z.*"`) in `boundaryField`.
