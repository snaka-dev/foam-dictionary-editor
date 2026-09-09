#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Shinji NAKAGAWA
"""Emit `tools/fode-reader-paths.json`, FoDE's half of the version-tag oracle.

foamlore measures whether each fork reads a key; it cannot know *where to look*,
because which source subtree implements a dictionary's readers is FoDE's
knowledge — FoDE is the side that decided which dictionaries get a schema. This
script writes that map, in the `fode-reader-paths/v1` shape foamlore's
`HANDOFF.md` specifies, and fills the `keys` list from the live registry so the
two cannot drift.

See docs/foamlore-schema-spec.md item 11 for why the oracle exists at all. The
short version: 1,040 of FoDE's 1,130 hand-written `supported_in` claims are an
unaudited `BOTH`, and the instrument needed to audit them once is the same
instrument that would generate them correctly forever.

Two things this file is deliberately *not*:

- It is not derived from a directory listing. `READERS` below is hand-authored
  and reviewed, for the same reason foamlore declares `CENSUS_SUBTREES` rather
  than taking whatever a sparse checkout happens to hold: a map that reads
  itself off the disk cannot notice that the disk is wrong.
- It is not a complete list of every file that mentions a key. It is the set of
  subtrees whose absence of a key is *evidence*. Over-broad paths are the
  failure mode that makes the whole exercise useless — scanning all of `src`
  returns "present" for `type`, `scale` and `geometry` no matter who reads
  them.
- **A nested list is an alternative group** (`fode-reader-paths/v2`). A plain
  string is a path expected in every release; a nested list says *the reader is
  in one of these*, because upstream renamed or moved it and no release has
  more than one. `src/dynamicMesh/motionSmoother` and `src/meshCheck` are the
  same Foundation reader either side of v12; `src/TurbulenceModels` and
  `src/MomentumTransportModels` either side of v8. Without the distinction a
  consumer must treat every declared path as required, so every release is
  blind on whichever half it does not have, and the strict refusal rule then
  discards answers that were otherwise clean -- seven of nineteen refusals at
  the time this was added. Note this is *not* release-qualification, which was
  proposed earlier and declined: a group names no release, so it does not go
  stale when upstream moves again, it just gains a member.
- **Historical homes are listed, release-qualification is not.** `readers` is
  declared per fork, but where a key is read is a fact per *release*, and
  subtrees move. The rule is to name the narrowest path that covers every home
  a reader has had across the measured releases -- widening to a parent where
  one exists, listing siblings where it does not -- rather than qualifying
  entries by release. Paths are declarative and a stale one costs nothing when
  another hits, whereas a partial span from a moving subtree is indistinguishable
  from a key that was added or dropped. That indistinguishability is why this
  matters more than it looks: `functions.mode` is a real drop and `MULESCorr`
  is a relocation, and they produce the same shape.
- It does not chase a key into an individual solver. `fvSchemes`'s `fluxScheme`
  is read only by `rhoCentralFoam` (OpenCFD) and `shockFluid` (Foundation), and
  naming those directories would make the map brittle to a solver rename for no
  gain. A solver-specific key falls through to the shipped-dictionary scan,
  which is the second of the three evidence sources and finds it in the
  tutorials that set it.

Usage:
    python3 tools/gen_reader_paths.py            # write the JSON
    python3 tools/gen_reader_paths.py --check    # exit 1 if it is stale
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from schemas._base import (  # noqa: E402
    FOUNDATION_SERIES,
    OPENCFD_SERIES,
)

OUT = REPO_ROOT / "tools" / "fode-reader-paths.json"
SCHEMA = "fode-reader-paths/v2"

#: Case-relative dictionary path -> the hand-written module that schemas it.
#: Only hand-written modules appear: the generated ones already carry measured
#: tags and are not what item 11 is about.
MODULES = {
    "system/controlDict": "schemas.control_dict",
    "system/fvSchemes": "schemas.fv_schemes",
    "system/fvSolution": "schemas.fv_solution",
    "system/blockMeshDict": "schemas.block_mesh_dict",
    "system/snappyHexMeshDict": "schemas.snappy_hex_mesh_dict",
    "constant/turbulenceProperties": "schemas.turbulence_structure",
    "constant/momentumTransport": "schemas.turbulence_structure",
}

#: Where each dictionary's keys are actually read, per fork. `"*"` is the
#: default and a fork key overrides it entirely (not merged), so a fork that
#: moved a subtree lists its own full set. A nested list is an alternative
#: group: at least one member is expected per release, not all of them.
#:
#: Derived by indexing every string literal in both forks' `src` and
#: `applications`, bucketing by subtree, and looking up each `BOTH` key — then
#: read and trimmed by hand. The counts in the comments are how many of that
#: dictionary's `BOTH` keys were found in that subtree, from
#: OpenFOAM-12 and openfoam2606.
READERS: dict[str, dict[str, list]] = {
    "system/controlDict": {
        # Time itself owns startFrom/stopAt/deltaT/write*; the functionObjects
        # machinery owns the `functions {}` block, and the individual function
        # objects own their own keys. Three more owners sit outside all of
        # those and were missing until 2026-09-06: `fvOptions` is read by
        # fvModels.C and fvConstraints.C under cfdTools, `fileHandler` by
        # argList.C and fileOperation.C, and `graphFormat` by writeEk.C in the
        # randomProcesses library. All three had read as Foundation absences.
        "*": [
            "src/OpenFOAM/db/Time",
            "src/OpenFOAM/db/functionObjects",
            "src/OpenFOAM/db/dynamicLibrary",
            "src/OpenFOAM/global",
            "src/finiteVolume/cfdTools",
            "src/functionObjects",
            "src/sampling",
            "src/randomProcesses",
        ],
    },
    "system/fvSchemes": {
        # A real fork split, and the reason `readers` is keyed by fork at all:
        # Foundation reads the scheme selectors in finiteVolume alongside the
        # discretisation they configure, while OpenCFD moved the lookup out to
        # src/OpenFOAM/matrices/schemes. A single shared list would report
        # ddtSchemes, snGradSchemes, d2dt2Schemes and fluxRequired as unread by
        # OpenCFD -- four of the most basic keys in the file.
        "foundation": [
            "src/finiteVolume/finiteVolume",
            "src/finiteVolume/fvMesh",
            "src/finiteVolume/interpolation",
        ],
        "opencfd": [
            "src/OpenFOAM/matrices/schemes",
            "src/finiteVolume/finiteVolume",
            "src/finiteVolume/fvMesh",
            "src/finiteVolume/interpolation",
        ],
    },
    "system/fvSolution": {
        # Four owners, and the fork split is not the obvious one. The linear
        # solver settings are lduMatrix's, the PIMPLE/SIMPLE/PISO controls are
        # cfdTools', and `solvers` itself -- the primary block of the file --
        # is read by neither: solution.C in matrices/solution, the sibling of
        # lduMatrix, in both forks, along with relaxationFactors, cache, fields
        # and equations. Omitting it made the file's most load-bearing key read
        # as shipped-only in both forks, the minVol shape again.
        #
        # The remaining split runs *both ways*, because each fork moved a
        # different group out of cfdTools. Foundation keeps the dynamic-mesh
        # controls (checkMeshCourantNo, correctPhi, moveMeshOuterCorrectors)
        # there while OpenCFD reads them in dynamicFvMesh/include; OpenCFD
        # keeps the VoF controls (MULESCorr, nAlphaCorr, nAlphaSubCycles,
        # alphaApplyPrevCorr) there while Foundation reads them in
        # twoPhaseModels/VoF/alphaControls.H. A single "*" list therefore
        # favoured neither fork consistently -- it reported four keys as
        # Foundation-only and four as OpenCFD-only, an apparent fork
        # difference that was entirely a map difference.
        "foundation": [
            "src/OpenFOAM/matrices/lduMatrix",
            "src/OpenFOAM/matrices/solution",
            "src/finiteVolume/finiteVolume",
            "src/finiteVolume/cfdTools",
            # `src/twoPhaseModels`, not `src/twoPhaseModels/VoF`: a path is
            # declared per fork but is a fact per *release*, and Foundation
            # moved alphaControls.H three times -- cfdTools/general/include at
            # v7, twoPhaseModels/twoPhaseMixture/VoF at v8-v10,
            # twoPhaseModels/VoF at v11-v12. The narrow spelling covered two of
            # eight releases, so MULESCorr and its siblings read absent from
            # the other six, which is shaped exactly like a key that was added
            # or dropped. The parent covers every home the file has had and the
            # next move inside that tree, at a cost of 3 files to 78 -- still
            # negligible beside src/ at 8000. See "Historical homes" in the
            # module docstring.
            # A group, not two paths: the VoF controls are read in
            # transportModels/interfaceProperties at v7 and in twoPhaseModels
            # from v8. The two subtrees DO coexist at v8 and v9, but not as
            # readers of this file -- transportModels contributes none of its
            # keys there while twoPhaseModels contributes five -- so for this
            # dictionary they are alternatives, and listing them flat made
            # every release blind on whichever it lacked.
            ["src/twoPhaseModels", "src/transportModels"],
            # nLimiterIter is read in fvMatrices/solvers/MULES, in both forks
            # and every release. 15 files against finiteVolume/finiteVolume's
            # 180, so it is a narrow addition rather than a widening.
            "src/finiteVolume/fvMatrices",
            # scalarTransport.C reads MULESCorr, nSubCycles and nCorr from
            # `mesh_.solution().solverDict(fieldName_)` -- solution::solvers_
            # is `subDict("solvers")`, so that is fvSolution's own solvers
            # block, not the function object's dictionary. Library code in an
            # unmapped subtree, which the library-versus-solver rule says
            # belongs here. Missing it made MULESCorr and nAlphaCorr look
            # dropped at v13, and a retraction was needed after foamlore had
            # already built a finding on it. Declared for both forks: the
            # subtree exists in every release of each, and a path that
            # contributes nothing costs nothing.
            "src/functionObjects/solvers",
        ],
        "opencfd": [
            "src/OpenFOAM/matrices/lduMatrix",
            "src/OpenFOAM/matrices/solution",
            "src/finiteVolume/finiteVolume",
            "src/finiteVolume/cfdTools",
            "src/dynamicFvMesh",
            "src/functionObjects/solvers",
            # Both readers are OpenCFD's too, and adding them only to the
            # Foundation list was an asymmetry rather than a fork difference:
            # fvMatrices/solvers/MULES reads nLimiterIter in every release of
            # both forks, and interfaceProperties.C still reads cAlpha here
            # where Foundation moved it into the solver modules at v11.
            #
            # src/phaseSystemModels is deliberately NOT here. nAlphaCorr and
            # nAlphaSubCycles do have readers under it, but both keys already
            # resolve in the mapped paths, so it contributes nothing and would
            # add 1428 files of literals -- the polyTopoChange shape, where a
            # path that makes nothing new resolve can only make something
            # wrong resolve later.
            "src/finiteVolume/fvMatrices",
            "src/transportModels",
        ],
    },
    "system/blockMeshDict": {
        # Three readers, and the third is the cautionary one. blockMesh reads
        # the geometry; polyMesh owns the `boundary` entry types, which is why
        # `inGroups` is valid here while absent from src/mesh/blockMesh; and
        # the *application* reads `mergePatchPairs` -- in OpenCFD that is the
        # only place it appears, so a map naming src/mesh/blockMesh alone
        # would report a live key as unread by that fork. `meshes` rather than
        # `meshes/polyMesh` because `inGroups` is read in
        # meshes/Identifiers/patch/patchIdentifier.C.
        "*": [
            "src/mesh/blockMesh",
            "src/OpenFOAM/meshes",
            "src/meshTools/searchableSurfaces",
            "applications/utilities/mesh/generation/blockMesh",
        ],
        "foundation": [
            "src/mesh/blockMesh",
            "src/OpenFOAM/meshes",
            "src/meshTools/searchableSurfaces",
            "src/generic/genericPatches",
            "src/polyTopoChange",
            "applications/utilities/mesh/generation/blockMesh",
        ],
    },
    "system/snappyHexMeshDict": {
        # Same shape as blockMeshDict, and the same trap: the *stages* --
        # castellatedMesh, snap, addLayers and their control sub-dictionaries --
        # are read by the application, not the library. Both forks agree here.
        # The library owns the controls inside each stage.
        #
        # meshQualityControls is a third owner again, and the forks disagree
        # about where it lives: OpenCFD reads minVol and its siblings in
        # motionSmoother, Foundation in meshCheck. Omitting those made minVol
        # read as unseen in *both* forks while every fork reads it and
        # tutorials set it -- a map gap presenting as a finding, which is the
        # failure mode this file's header warns about.
        # Foundation reads the mesh-quality controls in motionSmoother at
        # v7-v11 and in meshCheck from v12, so both are named; each is absent
        # from the releases the other serves. src/OpenFOAM/meshes covers two
        # more readers: Identifiers for inGroups -- the same correction
        # blockMeshDict needed -- and primitiveShapes/plane for planeType.
        #
        # Neither polyTopoChange path is here, and that is measured rather than
        # assumed. src/dynamicMesh/polyTopoChange contributes no key of this
        # file at any release, and src/polyTopoChange contributes exactly two:
        # `e1` and `e3`, matched in meshCut/directions/directions.C, which is
        # mesh-cut code and not snappy geometry. Foundation ships no
        # searchableRotatedBox in any release v7-v14, so those two are a
        # confirmed one-fork absence -- and declaring the path would have
        # turned a real finding into a false READ. Item 11 predicted this exact
        # pair as the radius1 shape before either side measured it.
        "foundation": [
            "src/mesh/snappyHexMesh",
            "src/meshTools/searchableSurfaces",
            "src/OpenFOAM/meshes",
            # One reader, renamed at v12. No release has both.
            ["src/dynamicMesh/motionSmoother", "src/meshCheck"],
            "applications/utilities/mesh/generation/snappyHexMesh",
        ],
        "opencfd": [
            "src/mesh/snappyHexMesh",
            "src/meshTools/searchableSurfaces",
            "src/OpenFOAM/meshes",
            "src/dynamicMesh/motionSmoother",
            "applications/utilities/mesh/generation/snappyHexMesh",
        ],
    },
    # Foundation renamed the subtree at OpenFOAM 8, which is the case the
    # per-fork keying exists for: one shared list would go stale on whichever
    # fork moved and then read as that fork dropping the dictionary.
    "constant/turbulenceProperties": {
        "foundation": [
            # One subtree, renamed at v8. No release has both.
            ["src/MomentumTransportModels/momentumTransportModels",
             "src/TurbulenceModels/turbulenceModels"],
        ],
        "opencfd": [
            "src/TurbulenceModels/turbulenceModels",
        ],
    },
    "constant/momentumTransport": {
        "foundation": [
            ["src/MomentumTransportModels/momentumTransportModels",
             "src/TurbulenceModels/turbulenceModels"],
        ],
        "opencfd": [
            "src/TurbulenceModels/turbulenceModels",
        ],
    },
}

#: Keys known to be assembled at run time, so a literal scan cannot see them
#: whatever subtree it is pointed at. Passed through so the oracle reports
#: `no-verdict` rather than `UNSEEN`, which would read as "the fork dropped it".
#:
#: **This list, and `known_unseen` below, mean the scan should not LOOK -- not
#: that the key is unsupported.** The distinction is not academic: both lists
#: suppress a verdict, and a key suppressed in every release leaves a span with
#: no evidence at all, which published bare asserts "supported in no release"
#: about a key nobody measured. Five keys were doing exactly that before
#: foamlore added its `no_evidence` refusal -- three of them from this list.
#: A suppression written for one consumer became an assertion to another, and
#: nothing here said which it was.
#: `executeInterval` is `prefix_ + "Interval"` and was one reading away from
#: being retagged out of Foundation during item 9; `executeControl` is the same
#: construction, found by the index this map was built from. Note `writeControl`
#: and `writeInterval` are *not* here: the function objects assemble them the
#: same way, but `Time` also reads them as plain literals, so a scan does see
#: them. `<Model>Coeffs` is `typeName + "Coeffs"` — 41 of
#: `turbulenceProperties`'s 63 `BOTH` keys, all generic placeholders whose real
#: facts foamlore already owns.
RUNTIME_ASSEMBLED = (
    "executeInterval",
    "executeControl",
    # `coeffs_(dict.optionalSubDict(type() + "Coeffs"))` in
    # advectionDiffusionPatchDistMethod, both forks. Named explicitly rather
    # than caught by the rule below because it is not a `<Model>Coeffs` model
    # dictionary, and because a literal *does* exist for it in OpenCFD -- in
    # src/optimisation/adjointOptimisation, an unrelated subtree reading its
    # own dictionary. The radius1 pattern: a name matched, the wrong reader
    # owned it.
    "advectionDiffusionCoeffs",
    # `word refCellName = field.name() + "RefCell"` in findRefCell.C, and
    # likewise RefPoint and RefValue, so the key is the field's own name plus a
    # suffix and no literal exists for any of the three. Solvers call
    # `setRefCell(p, simple.dict(), pRefCell, pRefValue)` where those are C++
    # variables, not strings. Shipped fvSolution dictionaries do set them.
    #
    # pRefCell was in `known_unseen` until 2026-09-08, which was the wrong
    # list: it said "read by neither fork" when the truth is "assembled, so
    # unseeable". pRefPoint and pRefValue were in no list at all and came back
    # as spans with no evidence.
    "pRefCell",
    "pRefPoint",
    "pRefValue",
)


def _model_coeff_keys(names: set[str]) -> list[str]:
    """The `<Model>Coeffs` names, which OpenFOAM builds as `typeName + "Coeffs"`.

    These cannot be seen by any literal scan, whatever subtree it is pointed
    at, so they must reach the oracle as `no-verdict` rather than `UNSEEN` --
    an absence would read as the fork having dropped the model.

    Derived from the key table rather than listed, because the set grows every
    time foamlore measures a family, and an out-of-date list would silently
    start reporting new models as absent.

    **Not a suffix rule**, and `printCoeffs` is why. It ends in `Coeffs` and is
    not a model dictionary at all -- it is a structural boolean that OpenFOAM
    reads as a plain literal, so suppressing it would throw away a verdict that
    is genuinely available. Structural keys are excluded here for that reason;
    they are measured like any other key and tagged separately.
    """
    return sorted(n for n in names
                  if n.endswith("Coeffs") and n not in STRUCTURAL_KEYS)

#: Keys `schemas/turbulence_structure.py` hand-owns: the dictionary's skeleton
#: and its selectors, not a model coefficient. Flagged rather than dropped,
#: which is a deliberate reading of where item 5's boundary actually runs.
#:
#: Item 5 forbids foamlore *emitting a `KeySchema`* for these, and the reason is
#: mechanical: `schemas/builtin.py` loads the generated modules after
#: `turbulence_structure`, so an emitted entry would silently override the
#: hand-written one rather than collide with it. The oracle emits **data** — a
#: measured span per fork, which FoDE consumes into its own module — so that
#: override cannot happen and the mechanism does not transfer.
#:
#: Dropping them instead would leave 22 hand-asserted `BOTH` claims (eleven
#: keys across two dictionaries) permanently unaudited, which is the thing item
#: 11 exists to end. They are measurable: every one resolves inside the scoped
#: reader path, `simulationType` in two files and `printCoeffs` in eight. So the
#: fact goes to foamlore and everything else about the key stays here, which is
#: the by-kind-of-claim line item 11 settled on. The flag marks that split
#: explicitly so a reader of this file is not left to infer it.
STRUCTURAL_KEYS = (
    "simulationType",
    "RAS",
    "LES",
    "laminar",
    "RASModel",
    "LESModel",
    "laminarModel",
    "model",
    "turbulence",
    "printCoeffs",
    "delta",
)

#: Keys a literal scan finds nowhere in *either* fork, for reasons already
#: established, so an `UNSEEN` verdict on them is expected rather than a
#: finding. Recorded here so the oracle does not re-report them every run.
#:
#: Only keys unseen in both forks belong here. A key unseen in one fork is
#: exactly what this exercise is looking for, so listing it would suppress the
#: finding — `pRefPoint` (unseen in OpenCFD, read by Foundation) and
#: `advectionDiffusionCoeffs` (unseen in Foundation) are deliberately left out
#: as live candidates.
#:
#: `minFlatness` is an upstream defect: documented in the shipped
#: `meshQualityDict` and read by neither fork, reported to OpenCFD as #3592.
#: `minFlatness` is the only entry, and the only genuine both-fork absence
#: this exercise found: every other symmetric absence turned out to be a
#: missing reader path. `pRefCell` was here until 2026-09-08 and belongs in
#: `RUNTIME_ASSEMBLED` -- it is unseeable, not unread.
KNOWN_UNSEEN = (
    "minFlatness",
)


def both_keys(module_name: str) -> list[str]:
    """Bare key names in `module_name` whose tag is exactly `BOTH`.

    Wildcard rows (`<parent>.*`) are dropped: they carry no name the source
    could contain. The bare name is what a C++ literal would be, so the
    `<parent>.` prefix goes too.
    """
    mod = importlib.import_module(module_name)
    names = set()
    for table_key, schema in mod.SCHEMAS.items():
        if table_key.endswith(".*"):
            continue
        tags = tuple(schema.supported_in or ())
        if FOUNDATION_SERIES in tags and OPENCFD_SERIES in tags:
            names.add(getattr(schema, "key", None) or table_key.rsplit(".", 1)[-1])
    return sorted(names)


def build() -> dict:
    dictionaries = []
    for path, module_name in MODULES.items():
        readers = READERS.get(path)
        if not readers:
            raise SystemExit(f"no READERS entry for {path}")
        keys = [{"key": k, "claimed": "BOTH"} for k in both_keys(module_name)]
        dictionaries.append({
            "file": path,
            "module": module_name.replace(".", "/") + ".py",
            "readers": readers,
            "keys": keys,
        })
    return {
        "schema": SCHEMA,
        "note": (
            "Generated by tools/gen_reader_paths.py from schemas/ — do not "
            "hand-edit; edit READERS in that script and re-run. `readers` is "
            "hand-authored, `keys` is derived from the live registry."
        ),
        # Load-bearing, not advisory. A verdict set built from two pinned
        # releases is a cross-check artifact: a disagreement between two
        # implementations means a measurement error rather than a release
        # difference, which is what makes the comparison worth running. It is
        # NOT a source of supported_in. `functions.mode` is the demonstration:
        # on foundation-12 against opencfd-v2606 it reads as OpenCFD-only,
        # and Foundation ships fieldMinMax reading it at v7 and v8 before
        # dropping the model at v9. Publishing that pair's verdict would
        # replace one wrong tag with another and give it the authority of a
        # measurement. Cross-check on two, publish from nineteen.
        "verdicts_publishable_from": "all_releases",
        "exclude_dirs": ["lnInclude"],
        "runtime_assembled": sorted(
            set(RUNTIME_ASSEMBLED)
            | set(_model_coeff_keys(
                {k["key"] for d in dictionaries for k in d["keys"]}))),
        "known_unseen": list(KNOWN_UNSEEN),
        "structural_keys": list(STRUCTURAL_KEYS),
        "dictionaries": dictionaries,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if the committed file is stale")
    args = ap.parse_args()

    payload = json.dumps(build(), indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if not OUT.is_file():
            print(f"{OUT.name} is missing; run tools/gen_reader_paths.py")
            return 1
        if OUT.read_text(encoding="utf-8") != payload:
            print(f"{OUT.name} is stale; re-run tools/gen_reader_paths.py")
            return 1
        print(f"{OUT.name} is current")
        return 0

    OUT.write_text(payload, encoding="utf-8")
    n = sum(len(d["keys"]) for d in build()["dictionaries"])
    print(f"wrote {OUT.relative_to(REPO_ROOT)}: "
          f"{len(MODULES)} dictionaries, {n} keys")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
