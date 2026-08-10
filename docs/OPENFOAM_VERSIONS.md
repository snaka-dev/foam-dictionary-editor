# OpenFOAM version differences that change your case files

[日本語版](OPENFOAM_VERSIONS_ja.md)

A case is not portable between OpenFOAM releases in the way people expect. Solver
names change, keys are renamed, and — the part that surprises most — **whole
dictionary files are renamed**. A `constant/transportProperties` copied from an
OpenFOAM 7 tutorial is simply not read by OpenFOAM 12, which looks for
`constant/physicalProperties` instead. Nothing warns you; the file sits there and
the run uses defaults or stops with a lookup error.

This page records the renames that FoDE has measured, so you can tell at a glance
whether a case you have been handed matches the OpenFOAM you are running.

## First: which OpenFOAM is this?

Both forks write their identity into the banner at the top of every dictionary.
Open any file in the Editor tab and read the fourth line:

```
|  \\    /   O peration     | Version:  v2606                                 |
|   \\  /    A nd           | Website:  www.openfoam.com                      |
```

- **`www.openfoam.com`** with a `vYYMM` version — the **OpenCFD** fork
  (openfoam.com), released twice a year: `v2506`, `v2512`, `v2606`, …
- **`openfoam.org`** with a plain number — the **Foundation** fork
  (openfoam.org), released roughly yearly: `9`, `10`, `11`, `12`, …

The two are separate lineages, not versions of one thing. Which fork you are on
matters more than which release, because almost every rename below is
Foundation's.

## The Foundation renames

Measured by counting the files each release actually ships in its `tutorials/`
tree. A `0` means no tutorial in that release uses the name at all.

| file | 7 | 8 | 9 | 10 | 11 | 12 | dev |
|---|---:|---:|---:|---:|---:|---:|---:|
| `constant/turbulenceProperties` | 166 | 0 | 0 | 0 | 0 | 0 | 0 |
| `constant/momentumTransport` | 0 | 166 | 169 | 176 | 183 | 187 | 203 |
| `constant/transportProperties` | 110 | 111 | 112 | 0 | 0 | 0 | 0 |
| `constant/thermophysicalProperties` | 86 | 85 | 94 | 0 | 0 | 0 | 0 |
| `constant/physicalProperties` | 1 | 1 | 1 | 157 | 159 | 165 | 184 |
| `constant/fvOptions` | 23 | 22 | 0 | 0 | 0 | 0 | 0 |
| `system/fvOptions` | 6 | 6 | 0 | 0 | 0 | 0 | 0 |
| `constant/fvModels` | 0 | 0 | 42 | 46 | 66 | 72 | 91 |
| `system/fvConstraints` | 0 | 0 | 43 | 44 | 50 | 52 | 58 |
| `constant/thermophysicalTransport` | 0 | 2 | 6 | 6 | 6 | 6 | 10 |
| `constant/regionProperties` | 4 | 4 | 5 | 5 | 0 | 0 | 0 |
| `system/functions` | 0 | 0 | 0 | 0 | 0 | 115 | 137 |
| `constant/momentumTransfer` | 0 | 0 | 0 | 0 | 0 | 0 | 31 |

Read down the columns and four clean switch-overs stand out:

**OpenFOAM 8 — turbulence.** `constant/turbulenceProperties` becomes
`constant/momentumTransport`, the same 166 files under a new name, in one
release. The contents keep their shape: `simulationType`, the `RAS`/`LES` block,
`model`, `turbulence`, `printCoeffs`. `constant/thermophysicalTransport` appears
at the same time for the thermal half that was split out.

**OpenFOAM 9 — `fvOptions` splits in two.** The single `fvOptions` file becomes
`constant/fvModels` (sources and sinks — what *adds* to an equation) and
`system/fvConstraints` (what *fixes* a value). An `fvOptions` carried forward
from OpenFOAM 8 is read by neither, and the split is semantic, so it is not a
rename you can do with `mv` — entries have to be sorted into the two new files.

**OpenFOAM 10 — transport and thermophysical merge.** Both
`constant/transportProperties` and `constant/thermophysicalProperties` are
replaced by one `constant/physicalProperties`. This is the one that bites
hardest, because it affects nearly every case: 196 files across two names became
157 under one. (The single earlier hit is real but unrelated — `electrostaticFoam`
has had a `physicalProperties` since OpenFOAM 7.)

**OpenFOAM 11 — `regionProperties` goes.** Multi-region setup was reworked; the
file stops appearing in the tutorials.

Two more that are additions rather than renames: `system/functions` arrives in
**OpenFOAM 12** as a place to put the function-object block that used to sit
inside `controlDict`, and `constant/momentumTransfer` appears in **dev** for
multiphase momentum exchange.

Phase variants follow their base name. If your case had
`thermophysicalProperties.air` and `thermophysicalProperties.water` before
OpenFOAM 10, it has `physicalProperties.air` and `physicalProperties.water`
after; the same goes for `momentumTransport.air`.

## The OpenCFD side: nothing moves

The same measurement over the OpenCFD releases:

| file | v2106 | v2206 | v2212 | v2306 | v2412 | v2506 | v2606 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `constant/turbulenceProperties` | 318 | 348 | 363 | 364 | 429 | 430 | 432 |
| `constant/transportProperties` | 219 | 239 | 250 | 252 | 324 | 325 | 326 |
| `constant/thermophysicalProperties` | 148 | 162 | 163 | 163 | 163 | 163 | 165 |
| `constant/fvOptions` | 35 | 39 | 42 | 42 | 43 | 43 | 43 |
| `constant/momentumTransport` | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `constant/physicalProperties` | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `system/fvConstraints` | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Across five years, not one of these filenames changed. The counts only grow,
because the tutorial set grows. So:

- A case moving **between OpenCFD releases** rarely breaks on file names.
- A case moving **between forks**, or **across Foundation 8/9/10**, usually does.

The corollary is that the names are a reliable fork test. A case with
`constant/momentumTransport` in it is a Foundation 8+ case, and no OpenCFD
release will read that file.

## Names that differ between the forks

Not renames — the two forks simply chose different names for the same job.

| job | Foundation | OpenCFD |
|---|---|---|
| turbulence model (v8+) | `constant/momentumTransport` | `constant/turbulenceProperties` |
| transport + thermo (v10+) | `constant/physicalProperties` | `constant/transportProperties`, `constant/thermophysicalProperties` |
| sources and constraints (v9+) | `constant/fvModels`, `system/fvConstraints` | `constant/fvOptions`, `system/fvOptions` |
| surface feature extraction | `system/surfaceFeaturesDict` | `system/surfaceFeatureExtractDict` |

Some dictionaries exist on one side only: `system/optimisationDict` and
`constant/adjointRASProperties` (adjoint optimisation), `system/meshDict`
(cfMesh) and the finite-area trio `faSchemes` / `faSolution` /
`faMeshDefinition` are OpenCFD; `system/createZonesDict`,
`system/setWavesDict` and `constant/cloudProperties` are Foundation.

## Renames inside a file

Keys move too, and far more often than files do — scanning both forks' sources
for the compatibility declarations they leave behind yields around a hundred
old→new pairs. FoDE shows these in the **Detail pane** rather than in a document,
because the answer depends on the key you are looking at:

- a **renamed** key names its successor and the release the old spelling stopped
  being current — `convertToMeters` → `scale` (v1012),
  `minMedianAxisAngle` → `minMedialAxisAngle` (v1712);
- an **ineffective** key is one that appears in official tutorials but that no
  release ever reads, so writing it does nothing — `minFlatness` is the type
  case, shipped in `motorBike` since OpenFOAM 2.3.x while both forks read
  `minFaceFlatness`.

A compatibility entry is not forever. OpenCFD accepted `minMedianAxisAngle` up to
v2206 and dropped it in v2212, so the same spelling that works on an older
install is silently ignored on a newer one. Foundation still accepts both. Where
FoDE knows this, the Detail pane says so.

## What FoDE does about all this

- **The file list offers both spellings.** Every dictionary listed above is in
  FoDE's file list under both its old and its new name; only the one your case
  actually contains is shown. Nothing has to be configured.
- **Version labels on keys are measured, not guessed.** The *Supported in* line
  in the Detail pane comes from reading every release of both forks, so
  "OpenCFD v2106-v2606" means the key is in all of them, not that it is in the
  two that happened to be checked.
- **Comparing across releases is a menu item.** **Case > Find OpenFOAM
  Examples** searches an installation's `tutorials/`, and a hit can be opened as
  the comparison reference (**Case > Compare with Case**) or duplicated as a new
  editable case. Pointing it at the installation you are *targeting* is the
  quickest way to see what a modern case of the same kind looks like.

## Method, so you can check it

Every count above is the number of files with that name in the release's
`tutorials/` tree, at case level or one region level down, counted with `find`.
The trees used were OpenFOAM-7 through -12 and -dev, and OpenCFD v2106, v2206,
v2212, v2306, v2412, v2506 and v2606.

This measures **what the tutorials use**, which is a proxy for what the release
reads, not a proof of it. It is a good proxy — a rename shows up as one name
going to zero in the same release another appears — but for a specific key the
authority is the source, and for a specific case the authority is running it.
