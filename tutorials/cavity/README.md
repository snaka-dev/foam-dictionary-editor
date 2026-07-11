## Changes from upstream

All three sub-cases and the `Allrun`/`Allclean` scripts are redistributed
**unmodified** from the upstream tutorial; no dictionary entries have been
changed.

| Sub-case        | Upstream path                                      | Notes                                              |
|-----------------|----------------------------------------------------|----------------------------------------------------|
| `cavity/`       | `incompressible/icoFoam/cavity/cavity`             | Base single-region case                            |
| `cavityGrade/`  | `incompressible/icoFoam/cavity/cavityGrade`        | Non-uniform `simpleGrading`                        |
| `cavityClipped/`| `incompressible/icoFoam/cavity/cavityClipped`      | Clipped geometry; requires `mapFields` from cavity |

The upstream `Allrun` script also creates `cavityFine` and `cavityHighRe` on
the fly by cloning `cavity`; those cases are not distributed here but are
generated at run time and then removed by `Allclean`.
