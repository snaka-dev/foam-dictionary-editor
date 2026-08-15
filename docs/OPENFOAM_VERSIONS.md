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

<!-- BEGIN generated: foundation-table -->
| file | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `constant/turbulenceProperties` | 167 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `constant/momentumTransport` | 0 | 167 | 170 | 177 | 184 | 188 | 198 | 204 |
| `constant/transportProperties` | 110 | 111 | 112 | 0 | 0 | 0 | 0 | 0 |
| `constant/thermophysicalProperties` | 87 | 86 | 95 | 0 | 0 | 0 | 0 | 0 |
| `constant/physicalProperties` | 1 | 1 | 1 | 158 | 160 | 166 | 181 | 185 |
| `constant/fvOptions` | 23 | 22 | 0 | 0 | 0 | 0 | 0 | 0 |
| `system/fvOptions` | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 0 |
| `constant/fvModels` | 0 | 0 | 42 | 46 | 66 | 72 | 82 | 91 |
| `system/fvConstraints` | 0 | 0 | 43 | 44 | 50 | 52 | 55 | 58 |
| `constant/thermophysicalTransport` | 0 | 2 | 7 | 7 | 7 | 7 | 8 | 11 |
| `constant/regionProperties` | 4 | 4 | 5 | 5 | 0 | 0 | 0 | 0 |
| `system/functions` | 0 | 0 | 0 | 0 | 0 | 115 | 128 | 136 |
| `constant/momentumTransfer` | 0 | 0 | 0 | 0 | 0 | 0 | 29 | 31 |
<!-- END generated: foundation-table -->

Read down the columns and four clean switch-overs stand out:

**OpenFOAM 8 — turbulence.** `constant/turbulenceProperties` becomes
`constant/momentumTransport`, the same 167 files under a new name, in one
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
hardest, because it affects nearly every case: 207 files across two names became
158 under one. (The single earlier hit is real but unrelated — `electrostaticFoam`
has had a `physicalProperties` since OpenFOAM 7.)

**OpenFOAM 11 — `regionProperties` goes.** Multi-region setup was reworked; the
file stops appearing in the tutorials.

Two more that are additions rather than renames: `system/functions` arrives in
**OpenFOAM 12** as a place to put the function-object block that used to sit
inside `controlDict`, and `constant/momentumTransfer` appears in **OpenFOAM 13**
for multiphase momentum exchange.

OpenFOAM 14 introduces no new dictionary file and renames none. Its change to
your case files is one level down, inside `constant/momentumTransport` — see
the sub-dictionary section below.

Phase variants follow their base name. If your case had
`thermophysicalProperties.air` and `thermophysicalProperties.water` before
OpenFOAM 10, it has `physicalProperties.air` and `physicalProperties.water`
after; the same goes for `momentumTransport.air`.

## The OpenCFD side: nothing moves

The same measurement over the OpenCFD releases:

<!-- BEGIN generated: opencfd-table -->
| file | v2106 | v2112 | v2206 | v2212 | v2306 | v2312 | v2406 | v2412 | v2506 | v2512 | v2606 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `constant/turbulenceProperties` | 335 | 354 | 354 | 368 | 370 | 421 | 424 | 435 | 436 | 438 | 438 |
| `constant/transportProperties` | 245 | 264 | 246 | 256 | 259 | 312 | 315 | 331 | 332 | 333 | 333 |
| `constant/thermophysicalProperties` | 162 | 176 | 181 | 182 | 182 | 182 | 182 | 182 | 182 | 183 | 184 |
| `constant/fvOptions` | 39 | 41 | 39 | 42 | 42 | 42 | 42 | 43 | 43 | 43 | 43 |
| `system/fvOptions` | 13 | 15 | 16 | 16 | 16 | 41 | 41 | 43 | 43 | 44 | 45 |
| `constant/regionProperties` | 14 | 17 | 18 | 18 | 18 | 18 | 18 | 18 | 18 | 19 | 19 |
| `constant/momentumTransport` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `constant/physicalProperties` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `constant/fvModels` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `system/fvConstraints` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
<!-- END generated: opencfd-table -->

Across five years and eleven releases, not one of these filenames changed. The
counts mostly grow with the tutorial set, though not monotonically — the
reorganisation between v2112 and v2206 moved cases around, which is why
`transportProperties` dips from 264 to 246 without anything being renamed. That
is the point of reading a whole row rather than its endpoints: a rename shows up
as a column going to zero while another appears in the same release, and nothing
here does that. So:

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

**The forks can also disagree about which spelling is current**, which makes
"prefer the newer name" bad advice on its own. Foundation 11 renamed
`turbOnFinalIterOnly` to `transportCorrectionFinal` and has accepted both since;
OpenCFD reads `turbOnFinalIterOnly` as its *current* name and has never had the
other one at all. The `fvSolution` pair `SIMPLErho` / `simpleRho` splits the same
way and is older still — every Foundation release from v7 reads `simpleRho`.
There is no single modern spelling for either: the right one depends on the fork
you are running, so a case carried across forks needs the key changed rather than
merely kept.

### The measured pairs

The table below is not the whole hundred. It is every rename declared in the
source subtrees foamlore fetches — the readers of the dictionaries FoDE has
schemas for, plus what those trees happen to touch — measured across all 19
checkouts and regenerated from source rather than counted once. A dash means
that fork never declares the pair, which is what makes the disagreement above
readable at a glance.

A span says where the *declaration* is, and that is not the same as where the
old spelling still works. Foundation 7 and 8 read both `SIMPLErho` and
`simpleRho` through two plain lookups, under a source comment saying the first
is kept for compatibility — accepted, but never declared, so the table starts
that row at 9.

<!-- BEGIN generated: renames-table -->
| old → new | read from | Foundation | OpenCFD |
|---|---|---|---|
| `centre` → `origin` | `0/<field> boundaryField entry` | — | v2106-v2606 (api 1712) |
| `redirectType` → `name` | `0/<field> boundaryField entry` | — | v2106-v2606 (api 1706) |
| `relaxation` → `qrRelaxation` | `0/<field> boundaryField entry` | — | v2106-v2606 (api 1712) |
| `motionSolver` → `pointMeshMover` | `constant/dynamicMeshDict` | 14 | — |
| `LESModel` → `model` | `constant/momentumTransport` / `constant/turbulenceProperties` | 9-14 | v2106-v2606 (api -2006) |
| `RASModel` → `model` | `constant/momentumTransport` / `constant/turbulenceProperties` | 9-14 | v2106-v2606 (api -2006) |
| `laminarModel` → `model` | `constant/momentumTransport` / `constant/turbulenceProperties` | 9-14 | v2106-v2606 (api -2006) |
| `transportModel` → `viscosityModel` | `constant/physicalProperties` | 10-13 † | — |
| `Es` → `es` | `constant/thermophysicalProperties` | 12-14 | — |
| `Esref` → `esRef` | `constant/thermophysicalProperties` | 12-14 | — |
| `Hf` → `hf` | `constant/thermophysicalProperties` | 12-14 | — |
| `Hs` → `hs` | `constant/thermophysicalProperties` | 12-14 | — |
| `Hsref` → `hsRef` | `constant/thermophysicalProperties` | 12-14 | — |
| `K` → `kappa` | `constant/thermophysicalProperties` | 9-14 | v2106-v2606 (api 1612) |
| `Sf` → `sf` | `constant/thermophysicalProperties` | 12-14 | — |
| `a` → `Av` | `constant/thermophysicalProperties` | 11-14 | — |
| `chemistrySolver` → `solver` | `constant/thermophysicalProperties` | 9-13 | v2106-v2606 (api -1712) |
| `convergence` → `tolerance` | `constant/thermophysicalProperties` | — | v2106-v2606 (api 1712) |
| `inertSpecie` → `defaultSpecie` | `constant/thermophysicalProperties` | 9-14 | — |
| `mode` → `type` | `constant/thermophysicalProperties` | — | v2106-v2606 (api 1812) |
| `convertToMeters` → `scale` | `system/blockMeshDict` | — | v2106-v2606 (api 1012) |
| `writeFrequency` → `writeInterval` | `system/controlDict` | 12-14 | — |
| `CofR` → `origin` | `system/controlDict functions entry` | 14 | — |
| `Prl` → `Pr` | `system/controlDict functions entry` | 9-14 | — |
| `alphaD` → `alphal` | `system/controlDict functions entry` | 13-14 | — |
| `alphaDt` → `alphat` | `system/controlDict functions entry` | 13-14 | — |
| `calcCoeff` → `mode` | `system/controlDict functions entry` | — | v2106-v2606 (api 1812) |
| `calcTotal` → `mode` | `system/controlDict functions entry` | — | v2106-v2606 (api 1812) |
| `nCorr` → `nCorrectors` | `system/controlDict functions entry` | 13-14 | — |
| `name` → `faceZone` | `system/controlDict functions entry` | 11-12 | — |
| `name` → `field` | `system/controlDict functions entry` | 11-14 | — |
| `name` → `patch` | `system/controlDict functions entry` | 11-12 | — |
| `regionType` → `select` | `system/controlDict functions entry` | 11-12 | — |
| `timeVsFile` → `fileVsTime` | `system/controlDict functions entry` | 11-14 | — |
| `SIMPLErho` → `simpleRho` | `system/fvSolution` | 9-14 | — |
| `nCellsInCoarsestLevel` → `minCellsPerProcessor` | `system/fvSolution` | 14 | — |
| `turbOnFinalIterOnly` → `transportCorrectionFinal` | `system/fvSolution` | 11-14 | — |
| `minMedianAxisAngle` → `minMedialAxisAngle` | `system/snappyHexMeshDict` | 12-14 | v2106-v2206 (api 1712) |

† Declared in a subtree that is not fetched for every checkout, so the span says where it was looked at, not where it exists.
<!-- END generated: renames-table -->

## The model sub-dictionary: OpenFOAM 14 adds a spelling

Files get renamed and keys get renamed — and in OpenFOAM 14, the *sub-dictionary
a turbulence model reads its coefficients from* gained a new accepted name.

Through OpenFOAM 13, a model looked for `<model>Coeffs` and, failing that, read
straight from the enclosing block:

```
RAS
{
    model           kEpsilon;
    kEpsilonCoeffs  { Cmu 0.09; }   // looked for first
    Cmu             0.09;           // otherwise read from RAS itself
}
```

OpenFOAM 14 tries the **bare model name** first, then the old `Coeffs` name, then
the enclosing block:

```
RAS
{
    model     kEpsilon;
    kEpsilon  { Cmu 0.09; }         // new in 14, tried first
    kEpsilonCoeffs { Cmu 0.09; }    // still accepted
    Cmu       0.09;                 // still accepted
}
```

**Nothing you already have stops working.** OpenFOAM 14 is a strict superset
here: it adds the bare spelling without dropping either older one, so a case
written for 8-13 runs on 14 unchanged.

**The break is the other way, and it is silent.** A case written on OpenFOAM 14
using `kEpsilon { … }` and then run on 13 or earlier hits the fallback — the
sub-dictionary is not recognised, so the block is skipped and **every
coefficient in it quietly takes its default**. No error, no warning; the run
just uses 0.09 for `Cmu` and whatever the model's built-in defaults are for the
rest. If you are moving a case *backwards* from 14, rename the block to
`<model>Coeffs`.

This is Foundation only — OpenCFD releases are unaffected, and v14's own model
headers were rewritten to document the new form (22 of them, e.g. `kEpsilon.H`
now shows `kEpsilon { … }` where 13 showed `kEpsilonCoeffs { … }`).

Measured from source rather than from tutorials: `dictionary::optionalTypeDict`
in `src/OpenFOAM/db/dictionary/dictionary.C` (v14, lines 920-940) looks up
`typeName`, then `typeName + "Coeffs"`, then returns the enclosing dictionary;
OpenFOAM 13's `optionalSubDict` (same file, lines 926-941) has no such chain.
`optionalTypeDict` does not exist in Foundation 7-13 or in any OpenCFD release.

## OpenFOAM 14 also drops a key, and that one bites forwards

The sub-dictionary change above is safe in the 8-13 → 14 direction. One other
v14 change is not, and it deserves its own heading because it fails the same
quiet way: parallel `GAMG` lost `processorAgglomerator`.

Through 13, `fvSolution` chose the processor-agglomeration method with a word:

```
solvers
{
    p
    {
        solver                 GAMG;
        processorAgglomerator  masterCoarsest;
    }
}
```

14 reads a sub-dictionary instead, and chooses the method inside it:

```
solvers
{
    p
    {
        solver  GAMG;
        processorAgglomeration
        {
            agglomerator  pair;
        }
    }
}
```

**There is no compatibility lookup here.** 13 asked
`controlDict.found("processorAgglomerator")`; 14 asks
`controlDict.isDict("processorAgglomeration")` and, finding no such dictionary,
leaves the agglomerator pointer null. So an existing case is not misread — the
old key is not read at all, and a parallel run that used to agglomerate across
processors simply stops doing so. No error, no warning; the only symptom is how
long it takes.

The method names changed with it, so rewriting the block is not purely
mechanical. `manual` and `none` survive; **`masterCoarsest`, `eager` and
`procFaces` are gone**, and `all`, `sequential` and `pair` are new.

Foundation only, and measured from `GAMGAgglomeration.C` plus the `TypeName`
registrations under `GAMGProcAgglomerations/` in both trees. OpenCFD v2606 still
reads `processorAgglomerator` as a word, exactly as Foundation 13 did.

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
`tutorials/` tree, at case level (`<case>/constant/<name>`) or one region level
down (`<case>/constant/<region>/<name>`). Phase variants such as
`physicalProperties.air` are *not* counted separately; only the exact file name
is.

Every release of both forks is counted — Foundation 7 through 14 and all eleven
OpenCFD releases v2106 through v2606, with no gaps — each at a pinned commit,
so the table can be reproduced rather than taken on trust:

<!-- BEGIN generated: commit-table -->
| fork | releases | commits |
|---|---|---|
| Foundation | 7-14 | `6334942`, `a86b07b`, `d87800e`, `89f925d`, `9cbf94f`, `0b487fc`, `17489db`, `c046c72` |
| OpenCFD | v2106-v2606 | `c15bfde`, `14aeaf8`, `76d719d`, `6690815`, `a6e826b`, `1d8f0d5`, `630d60d`, `d394908`, `615aae6`, `87ed40d`, `481094f` |
<!-- END generated: commit-table -->

13 and 14 are `OpenFOAM-dev` at tags `version-13` and `version-14`; the rest are
the release repositories. Each count comes from `git ls-tree -r` against that
commit, so no working tree is involved and the numbers cannot drift with a
later checkout.

**These counts supersede an earlier edition of this table**, which sampled seven
OpenCFD releases and used a `dev` column that predated the 13 and 14 tags. Most
cells moved by 0-2; the OpenCFD column set changed more, because four releases
that had never been counted are now included. Nothing in the *conclusions*
changed — the same four Foundation switch-overs, and still no rename at all on
the OpenCFD side.

This measures **what the tutorials use**, which is a proxy for what the release
reads, not a proof of it. It is a good proxy — a rename shows up as one name
going to zero in the same release another appears — but for a specific key the
authority is the source, and for a specific case the authority is running it.
The sub-dictionary change described above is deliberately **not** in these
tables: it happens inside a file rather than to a file name, so a filename count
cannot see it, and it was read from the source instead.
