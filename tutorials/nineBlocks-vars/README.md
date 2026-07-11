## Changes from upstream

Derived from the upstream `icoFoam/cavity` tutorial. Same modifications as
`nineBlocks/` with two additional features in `system/blockMeshDict`:

- `system/controlDict`, `system/fvSchemes`, `system/fvSolution`,
  `system/decomposeParDict`, and `constant/transportProperties` are taken
  unchanged from the standard `cavity` case.
- `system/blockMeshDict` is custom-authored (3-D 3×3 multi-block), and
  additionally uses variable definitions (`$var`) for coordinates and cell
  counts, and compact `(blockId faceId)` notation in the `boundary` section.
- `0/U` and `0/p` are custom-authored (same as `nineBlocks/`).
