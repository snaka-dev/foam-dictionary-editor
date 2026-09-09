# foamlore generator: the request archive

The settled record of what FoDE asked the sibling foamlore repository to change
and what foamlore measured in reply. foamlore generates the schema modules
described under "Generated modules (vendored from foamlore)" in
[DEVELOPER.md](../DEVELOPER.md) and vendors them into FoDE. **No change in this
document has been made here** — foamlore is a separate repository with its own
remote, and the generated files must never be hand-edited in FoDE.

**New asks do not go in this file.** Write them in foamlore's `HANDOFF.md`,
which carries open items only and is cleared as they close; the writeup of a
closed item then lands here. The two halves have opposite lifecycles — an open
ask is short and volatile, a settled one is long and permanent — and this page
is cited from `RELEASE_NOTES.md` and `DEVELOPER.md`, so its item numbers have
to stay put. Splitting them also keeps a half-formed ask out of a file that is
cited as a record.

## Status (2026-09-05)

foamlore answers item by item in `fode-schemas/SPEC_RESPONSE.md` (and its `_ja`
pair) in that repository. That file is the other half of every item below —
this page carries the ask, that one carries the measurement — so the two are
meant to be read together.

| item | status |
|---|---|
| 1. Lift the three-model ceiling | **done** — 3 models → 29 (16 RAS, 13 LES/DES) |
| 2. `TARGET_FILES`, drop the duplicate module | **done, but not by merging** — see below |
| 3. Emit the new provenance fields | **measured: nothing to emit** — see below |
| 4. Widen the version tags | **done** — by scanning every release, not by relabelling |
| 5. Leave structural keys alone | agreed, and now checked mechanically |
| 6. Add the v2112 checkout | **done** (raised 2026-08-07, closed 2026-08-12) — see below |
| 7. The thermophysical family: which table decides validity? | **answered here** (raised 2026-08-13 by foamlore, answered 2026-08-14) — (a), both fields, three modules — see below |
| 8. OpenFOAM 14 | **done** (raised and closed 2026-08-13) — four constants, one test, one judgement call — see below |
| 9. `FOUNDATION_SERIES` still says v7-v13 | **done** (raised 2026-08-13, closed 2026-08-14) — the last 21 measured; 11 keys were never Foundation's — see below |
| 10. The rename scan has never seen most of FoDE's dictionaries | **done** (raised 2026-08-13, closed 2026-08-14 by foamlore `86a5bb4` and `2b314b8`) — all three asks landed — see below |
| 11. The `BOTH` tags have never been audited the way the narrow ones were | **measured and consumed 2026-09-08** — seven dictionaries, nineteen releases, 340 publishable spans; five dictionaries now agree completely, nine wrong tags retired, two of which rejected or aborted a run. The turbulence pair's per-file tags are deferred to an Update candidate — see below |
| 12. The laminar stress models are unmeasured, and `phaseSystemModels` is unfetched | **done** (raised 2026-09-03, closed by foamlore 2026-09-04; the offered follow-up taken 2026-09-05) — both asks answered, and the seven laminar blurbs now come from `_laminar_models.MODEL_DOCS` — see below |
| 13. The nested generalizedNewtonian/generalisedNewtonian viscosity models | **already measured by foamlore** (their SPEC_RESPONSE.md item 12, 2026-08-15) — FoDE picked the wiring option 2026-09-04; regeneration is the only remaining step — see below |

Item 2 was deliberately not done as written, and the reason is ours rather
than theirs: `schemas/registry.py::_build_file_key_schemas` does
`table.update(schemas)` once per entry of `TARGET_FILES`, with no per-key
filter, so a single module naming both files contributes an **identical**
table to each. `decayControl` and the whole of `GEKOCoeffs` — OpenCFD-only —
would then resolve inside `constant/momentumTransport`, which no OpenCFD
release reads and which Foundation reads only from v8. Today they correctly
return `None` there.

foamlore removed the duplication by splitting bodies instead: a generated
`schemas/_turbulence_coeffs.py` holds the coefficient facts once and exposes
`build_schemas(target_file)`, and the two per-file modules are ~25 lines each.
Only the facts are shared — every version tag, note and default list is
target-dependent, which is why one merged table cannot be right for both
files. `schemas/builtin.py` is unchanged: the shared module is imported, not
registered, and declares no `TARGET_FILE`.

**If we want the literal single-module form, the prerequisite is on this
side**: a per-key target filter in `_build_file_key_schemas`. Worth weighing
on its own merits; nothing needs it today.

Lifting the ceiling also forced a change we should know about. 28 of the 134
distinct coefficient names are read by more than one model (`Cmu` by nine,
plus `C1`, `C2`, `C3`, `sigmak`, `sigmaEps`, `kappa`, `Ck`, `betaStar`). The
generator's old rule emitted the flat key only for a name with exactly one
owner, so more models would have **silently removed the flat spelling for the
commonest coefficients** — the spelling `OPEN_NAMESPACES` exists to serve.
Those names now get one merged flat entry naming every owner and offering each
distinct default; inside a `<model>Coeffs` dictionary that model's own entry
still wins.

Item 3 turned out empty in the generator's territory. A quote-verified scan of
both declaration families across all eighteen releases found seven rename
declarations in the turbulence-model subtrees, and not one is a `<Model>Coeffs`
coefficient: six are the `RASModel`/`LESModel`/`laminarModel` → `model`
selectors this document assigns to `turbulence_structure.py` under item 5, and
the seventh is `relaxation` → `qrRelaxation`, a `thermalBaffle1D` boundary
condition key. The generator therefore emits no provenance fields, and is
required *not* to emit the selectors — `schemas/builtin.py` loads it after
`turbulence_structure`, so doing so would override our entries rather than
collide with them.

The suspicion recorded under item 3, that some pairs survive only in older
trees, is confirmed: `relaxation` → `qrRelaxation` is declared in v2106 and
v2112 and gone from v2206 onward.

Item 4 also corrected two rows of the table below, both from releases the hand
audit sampled past: the SpalartAllmaras `ft2` term arrived in **v2212**, not
v2306, and `sigmaNut`'s default changed at v2212 from `scalar(2)/scalar(3)` to
`0.66666`. Changes made here for it: `FOUNDATION_V8_V13` and
`OPENCFD_V2212_V2606` in `schemas/_base.py`, and the three assertions in
`tests/schemas/test_turbulence_schemas.py` that pinned the old narrow tags.

## What is already right

The generated content is accurate. Every coefficient was re-checked against the
`.C` constructors: `kOmegaSST` `a1`=0.31, `alphaK1`=0.85, `beta1`=0.075,
`betaStar`=0.09, and so on through kEpsilon and SpalartAllmaras. Not one wrong
name or value was found. `momentum_transport.py` correctly *omits* the
OpenCFD-only coefficients (`decayControl`, `kInf`, `omegaInf`, `ReyFactor`,
`ReyStar`, `twoLayerTreatment`, `ck`, `ft2`, `Ct3`, `Ct4`) that do not exist in
Foundation's constructors — a naive copy would have kept them. The pipeline is a
mechanical source extraction and the commit hashes in the banners are real.

The problems below are all about *scope*, not correctness.

## 1. Lift the three-model ceiling

`facts/tools/` has one hand-written extractor per model — `extract_kEpsilon.py`,
`extract_kOmegaSST.py`, `extract_SpalartAllmaras.py`. That design is why
coverage stops at three models: each new one costs a new script.

OpenCFD v2606 ships 14 RAS models and 7 LES models; Foundation adds `kOmega2006`
and `v2f` on the RAS side and the `SpalartAllmaras*DES` family on the LES side.
So 3 of ~16 RAS models are covered and **none** of the LES models.

Requested: generalise `facts/tools/foam_extract.py` into a table-driven
extractor, so a model is added by naming its source path rather than by writing
a script. The declarations to recognise are already common across models:

- `dimensioned<scalar>::getOrAddToDict("name", coeffDict(), default)`
- `Switch::getOrAddToDict("name", coeffDict(), default)`
- direct-constructor form, `Cmu_("Cmu", coeffDict(), 0.09)`

Note the paths differ by fork: OpenCFD uses
`src/TurbulenceModels/turbulenceModels/{RAS,LES}/`, Foundation uses
`src/MomentumTransportModels/momentumTransportModels/{RAS,LES}/`.

Coefficients that are *computed* rather than read must stay out — the existing
extractor already gets this right by excluding `SpalartAllmaras`'s `Cw1`
(`Cw1_(Cb1_/sqr(kappa_)+(1+Cb2_)/sigmaNut_)`), and that behaviour must survive
the rewrite.

## 2. Emit `TARGET_FILES` and drop the duplicate module

`momentum_transport.py`'s 57 keys are a strict subset of
`turbulence_properties.py`'s 77 — roughly 900 duplicated lines whose only reason
to exist was that FoDE's registry keyed schemas by a single `TARGET_FILE`, and
Foundation renamed `constant/turbulenceProperties` to `constant/momentumTransport`
in OpenFOAM 8.

FoDE now accepts a `TARGET_FILES` tuple and merges several modules into one
table per file, so the generator can emit **one** module:

```python
TARGET_FILES = ("turbulenceProperties", "momentumTransport")
```

with each key's `supported_in` carrying the fork information that currently
distinguishes the two files. Until that lands, both modules keep working
unchanged.

## 3. Emit the new provenance fields

`KeySchema` and `ChoiceItem` gained four optional fields (see DEVELOPER.md,
"Recording what a key *is*"):

```python
status: KeyStatus = "valid"      # "valid" | "renamed" | "ineffective"
use_instead: str = ""            # successor key, or the key actually read
renamed_from: tuple[str, ...] = ()
deprecated_since: str = ""
```

All are default-valued, so the current output stays valid. They matter to the
generator because both forks declare renames machine-readably and the extractor
is already walking that source:

- OpenCFD: `getCompat("newName", {{"oldName", apiVersion}})`
- Foundation: `lookupBackwardsCompatible<T>({"newName", "oldName"})`

Scanning those two call families across the checkouts yields ~100 old→new pairs
with per-fork version ranges — including `RASModel`/`LESModel` → `model` at API
2006, which is directly in this generator's territory. Emitting them as
`status="renamed"` entries would let the Detail pane explain an old spelling
instead of leaving it unrecognised.

Worth knowing: some pairs survive only in older trees because the compatibility
entry was later dropped. `minMedianAxisAngle` is declared in OpenCFD up to v2206
and absent from v2212 onward, while Foundation still accepts it. A generator
that reads only the newest checkout will miss those, so the scan should cover
every checkout and record the range.

## 4. Widen the version tags, or say they are a verification record

This one is user-visible today. A FoDE user on Foundation v10 selects `beta1` in
`constant/momentumTransport` and the Detail pane says **"Foundation v13"**,
which reads as "not available to you". The same complaint was reported against
`snappyHexMeshDict`'s `snap` and fixed FoDE-side by measuring every key across
every locally available release.

The generated tags are accurate about *what was checked* — the four checkouts in
`sources/` — but the pane presents them as support limits. Measured against
Foundation 7/8/9/10/11/12/dev and OpenCFD v2106/v2206/v2306/v2412/v2506/v2512/v2606:

| entries | tagged | actually present in |
|---|---|---|
| all 111 in `momentum_transport.py` | `Foundation v13` | **Foundation v8 → dev** (v7 has no `MomentumTransportModels`, consistent with the OpenFOAM 8 rename) |
| `beta1`, `Cmu`, `sigmaEps`, `decayControl`, … (111 entries) | `OpenCFD v2512, v2606` | **OpenCFD v2106 → v2606** |
| `ft2` | `OpenCFD v2512, v2606` | **v2306 → v2606** |
| `ReyFactor`, `ReyStar`, `twoLayerTreatment` | `OpenCFD v2512, v2606` | v2512 → v2606 — correct as-is |

One tag is already exactly right and should not be widened:
`turbulence_properties.py` marks Foundation support as **v7 only**, which is
correct — Foundation renamed the file to `momentumTransport` in OpenFOAM 8, so
v7 is genuinely the last Foundation release that reads
`constant/turbulenceProperties`.

Two ways to fix, either acceptable:

1. **Scan more checkouts.** `fetch_sources.sh` pulls four; pulling the full
   Foundation 7-13 and OpenCFD v2106-v2606 sets would let the generator emit a
   real range. This is what FoDE did by hand for the snappy audit, and it is
   what produced the table above.
2. **Emit a range label rather than a checkout list.** FoDE's `schemas/_base.py`
   exports `FOUNDATION_SERIES` (`"Foundation v7-v13"`) and `OPENCFD_SERIES`
   (`"OpenCFD v2106-v2606"`) for exactly this: an entry that is not tied to a
   release should say so instead of naming the releases that happened to be on
   disk. Cheaper, and honest, though less precise than (1).

Whichever is chosen, the distinction that matters is between "this key arrived
in release X" and "release X is where we happened to look". Only the first
belongs in `supported_in`; the second belongs in the banner, which already
records the source commits.

## 5. Leave structural keys alone

`simulationType`, `RAS`/`LES`/`laminar`, the `model` selector, `turbulence`,
`printCoeffs`, `delta` and the delta coefficient dictionaries are now covered by
the hand-written `schemas/turbulence_structure.py`. They are not derivable from
a model constructor and should stay out of the generator; the registry merges
both modules into one table, so there is no gap between them.

## 6. Add the v2112 checkout (2026-08-07)

The checkout set is missing one OpenCFD release. `sources/` holds v2106, v2206,
v2212, v2306, v2312, v2406, v2412, v2506, v2512 and v2606 — ten of the eleven
releases in the v2106-v2606 span. OpenCFD ships twice a year, `yymm` with
`mm` = 06 or 12, so **v2112** belongs between v2106 and v2206 and is absent.

This is not a labelling nicety. Item 4 was answered by measuring every release,
and `collapse()` decides between a range constant and an explicit release list
from the set of checkouts a key was found in. A key present in v2106 and v2206
but not measured in v2112 therefore renders as the explicit pair
`"OpenCFD v2106, OpenCFD v2206"` — which a user reads as "skipped v2112",
a claim nothing supports. `_turbulence_coeffs.py` already emits that pair.

Requested: add `opencfd-v2112` to `fetch_sources.sh` and to the generator's
`CHECKOUTS` table, and re-derive. The store grows by one checkout; the span
becomes eleven OpenCFD releases plus Foundation 7-13, so eighteen in all.

FoDE side, done in the same change: `schemas/_base.py` now exports
`OPENCFD_V2112`, and the one hand-written tag that enumerated across the gap
(`addLayersControls.minMedianAxisAngle` in
`schemas/snappy_hex_mesh_dict/_add_layers.py`) lists it. That entry is
inference, not measurement — v2112 is the one release in the span with no local
source tree, and the compatibility entry it names is present in the releases on
either side. A generator with the checkout would replace the inference with a
reading.

## 7. The thermophysical family: which table decides validity? (2026-08-13)

This item runs the other way. Items 1-6 are requests to foamlore; this one was
raised **by** foamlore after a probe fetch, and the question at the top of it
has to be answered **here** before the generator's output shape can be fixed.
[SCHEMA_CANDIDATES.md](SCHEMA_CANDIDATES.md) ranks
`constant/physicalProperties` / `transportProperties` +
`thermophysicalProperties` first among the dictionaries to generate — 165 files
in Foundation 12's tutorials, 491 in OpenCFD v2606. foamlore sparse-fetched
`src/thermophysicalModels` and `src/transportModels` into one checkout
(`opencfd-v2606`, commit `481094f`) to size the job. Everything below is
measured from that tree.

**The question: a combination is registered into three tables at once, and
validity depends on which one the solver asks.** `makeThermoPhysicsThermos` in
`src/thermophysicalModels/basic/fluidThermo/makeThermo.H` expands every
combination into `addThermoPhysicsThermo` for `basicThermo`, for `fluidThermo`,
**and** for the specific base thermo. On v2606 that specific base is
`psiThermo` for 26 of the 132 `makeThermos` invocations and `rhoThermo` for the
other 106. A combination registered only under `rhoThermo` is therefore a
runtime error for a solver that constructs a `psiThermo`, even though the
spelling is a real one that appears in other tutorials. The Detail pane sees
the dictionary and nothing else.

Three shapes are possible, and the generator can emit any of them. The choice
has to be made now because it decides whether the store's key is the
combination or the (combination, table) pair — that is not a rendering
detail that can be changed later without a re-derive:

- **(a) Emit the tables, narrow here.** Each combination carries the RTS tables
  it is registered in; FoDE decides what to show, and can later narrow by
  `controlDict`'s `application` if that is worth building. foamlore recommends
  this one: it is the only shape that records what the source actually says,
  and it leaves the narrowing decision on this side where the solver context
  lives.
- **(b) Emit the union, unqualified.** Simplest, and wrong in the direction
  that matters — it tells a user a combination is valid when their solver will
  reject it.
- **(c) Emit one choice list per table.** Honest, but pushes the whole
  solver-to-table mapping into the schema, and that mapping is not in the
  thermophysical tree.

**Second question: `KeySchema` has no `default` field.** For the turbulence
models that never mattered, because every coefficient has a default and the
generator writes it into `description`. The viscosity models do not:
`CrossPowerLaw.C:71-78` reads `nu0`, `nuInf`, `m` and `n` as required entries
with no fallback. So a generated entry would have to say "required, no default"
in prose. Is that acceptable, or does `_base.py` want a `required: bool` (or a
`default: str`) that the Detail pane can render distinctly? Prose is fine by
foamlore; the field is cheap on this side and would be visible in every
dictionary, not just this family.

**Third question: three `TARGET_FILE` modules, per item 2's outcome?** The file
is fork-renamed — Foundation merged `transportProperties` and
`thermophysicalProperties` into `physicalProperties` at v10, OpenCFD kept the
pair ([OPENFOAM_VERSIONS.md](OPENFOAM_VERSIONS.md)). By the same reasoning that
settled item 2, this wants a shared generated body plus three thin per-file
modules rather than one module with `TARGET_FILES`, or a Foundation-only key
resolves inside a file OpenCFD reads with different meaning. Confirming that
before the generator is written costs nothing; discovering it afterwards costs
a re-derive.

### What the probe settled, so it need not be re-argued

**The cost gate is much lower than SCHEMA_CANDIDATES.md assumes.** That page
treats "fetch a new subtree for all of them" as the thing to weigh. Adding both
subtrees to an existing blobless checkout took 1.5 s and grew it from 11 MB to
18 MB — roughly 130 MB and a few minutes across all eighteen. The fetch is not
the expensive part; the second extractor is.

**It is seven-or-four slots, not seven.** `basicThermo.C:52-68` defines
`componentHeader7` (`type`/`mixture`/`transport`/`thermo`/`equationOfState`/
`specie`/`energy`) and `componentHeader4` (`type`/`mixture`/`properties`/
`energy`), selected at `basicThermo.C:126` by whether the dict has a
`properties` entry. The liquid-properties path uses the short form. A schema
has to describe both shapes, and the Detail pane will need to know which one
the user is in.

**Validity is exact-string membership in an enumerable table.**
`makeThermoName` (`basicThermo.C:135-156`) concatenates the slots into
`type<mixture<transport<thermo<eqnOfState<specie>>,energy>>>` and looks that
string up. This is the strongest argument for generating rather than
hand-writing the family: the answer is mechanical, and no user can compute it
by hand.

**Enumeration is tractable and the typedef indirection fully resolves.** One
checkout carries 277 macro invocations in eight spellings:

| macro | uses | argument shape |
|---|---:|---|
| `makeThermos` | 132 | the 7-slot tuple, literally |
| `makeReactionThermos` | 52 | 9 args |
| `makeThermoPhysicsReactionThermos` | 50 | thermo-physics typedef |
| `makeThermoPhysicsReactionThermo` | 20 | thermo-physics typedef |
| `makeSolidThermo` and others | 23 | 8 args |

The 132 `makeThermos` calls yield 132 distinct combinations directly. The 70
reaction-thermo calls pass a bundle such as `constGasHThermoPhysics` instead;
all 20 distinct tokens resolve against the 24 typedefs in
`thermoPhysicsTypes.H`, with **none unresolved**. Those typedefs are nested
templates, which foamlore's existing `<>`-aware argument splitter already
handles.

### Proposed split

Two work items, not one. The transport half —
`src/transportModels/incompressible/viscosityModels`, nine models reading
through `optionalSubDict(typeName + "Coeffs")` — is close to an ordinary
addition to foamlore's model registry and depends on none of the three
questions above except the `default` one. The `thermoType` half is a genuinely
new extractor (macro expansion plus typedef resolution) whose output shape
depends on the answer to the first question. foamlore intends to start on the
transport half; the thermophysical half waits on this document.

Whenever the family does land, `tests/schemas/test_schema_coverage.py` needs a
floor for each new dictionary in the same change.

### Answered here (2026-08-14)

All three questions, in the order they were asked. The generator is unblocked.

**Q1 — output shape: (a), emit the tables.** foamlore's own recommendation, and
it is right for a reason worth stating: (a) is the only shape whose store key
survives a change of mind. The key becomes the `(combination, table)` pair, so
if FoDE later builds the `controlDict` `application` → solver → base-thermo
narrowing, (a) supports it with no re-derive, while (b) and (c) both need one.
(b) is wrong in the direction this repository has consistently refused to be
wrong in — it says valid where the solver will reject, and the whole tagging
discipline here (the `FOUNDATION_SERIES` verification rule, `processorAgglomerator`,
the fork-asymmetric treatment of `turbOnFinalIterOnly`) rests on understating
being the cheaper error. (c) would put the solver-to-table mapping in the schema,
and that mapping is not in the thermophysical tree — the same objection this
document raised to item 2's merged table: a fact the source does not carry
should not be invented by the generator.

Two constraints so the shape is not guessed at:

- **Emit the table set as a `note`, not into `supported_in`.** That field means
  "which release", and `_supported_in_text`, `_qualified_supported_in` and
  `tests/schemas/test_schema_coverage.py`'s
  `test_long_standing_keys_are_not_tagged_to_one_release` all parse its entries
  by their `Foundation`/`OpenCFD` prefix. A table name in there would be read as
  a release and rendered as one.
- **The seven-or-four slot split is ours, not the generator's.** Both
  `componentHeader7` and `componentHeader4` become key sets in the same module,
  distinguished by whether the dictionary has a `properties` entry. That is a
  parent-key question for `schemas/registry.py`, so it constrains nothing about
  the output shape.

**Q2 — `KeySchema` gains both `default: str` and `required: bool`.** Done in
this change, both default-valued, so current output stays valid — the same
argument item 3 used for the provenance fields. They are mutually exclusive and
`tests/schemas/test_default_and_required.py` enforces it; the Detail pane gives
them one **If Omitted** row, because they are two answers to one question. Not
on `ChoiceItem`: a default belongs to a key, not to one of its values.

Prose would have been acceptable for `default`, but not for `required`. That one
is machine-readable, so a future "your case omits a key OpenFOAM needs" check can
consume it, which no sentence in `description` could ever support — and it is
exactly what `CrossPowerLaw.C:71-78` needs.

**Two asks back, so the fact does not end up with two spellings.** At the next
re-derive, emit `default=` **and stop writing the default into `description` in
the same change**. Until then the generated modules keep prose defaults and an
empty field, which is why `default=""` is defined here to mean "not recorded",
never "no default exists" — otherwise every generated coefficient would read as
required. The carve-out: the 28 coefficient names read by more than one model
(`Cmu` by nine, plus `C1`, `C2`, `C3`, `sigmak`, `sigmaEps`, `kappa`, `Ck`,
`betaStar`) get one merged flat entry offering each owner's value, and a scalar
`default: str` cannot express "0.09 under kEpsilon, something else under
RNGkEpsilon". Those must leave `default` empty and keep offering the values
through their `ChoiceItem` list, as they already do. Better said now than
discovered after the re-derive.

**Q3 — three thin per-file modules over one shared generated body.** Confirmed,
and the reason is sharper than item 2's. Foundation's `constant/physicalProperties`
(v10+) is the **union** of the viscosity half and the `thermoType` half, while
OpenCFD keeps `constant/transportProperties` (viscosity only) and
`constant/thermophysicalProperties` (`thermoType` only). So one merged table is
wrong in **both directions at once** — it would resolve `thermoType` inside
OpenCFD's `transportProperties`, which does not read it, *and* the viscosity
keys inside OpenCFD's `thermophysicalProperties`, which does not read those.
Item 2's failure mode was one-directional; this one is symmetric.

The mechanical reason is unchanged and is ours:
`schemas/registry.py::_build_file_key_schemas` still does `table.update(schemas)`
once per target file with no per-key filter. The prerequisite for the literal
single-module form remains a per-key filter here, and still nothing needs it.

Concretely: a generated `schemas/_thermophysical.py` exposing
`build_schemas(target_file)`, plus `schemas/physical_properties.py`,
`schemas/thermophysical_properties.py` and `schemas/transport_properties.py` at
~25 lines each. `schemas/builtin.py` registers the three; the shared body is
imported and never registered, declaring no `TARGET_FILE`. Exactly the
`_turbulence_coeffs.py` shape. `services/case_loader.py` already lists all three
file names, so nothing is needed there.

**On the coverage floor: yes, and not yet.**
`tests/schemas/test_schema_coverage.py` keys its floor by fixture name and
asserts the fixture parsed to something, so adding a floor entry before the
fixtures exist fails immediately. The floor lands in the same change as the
modules, with three fixtures taken from real tutorial cases (one Foundation
`physicalProperties`, one OpenCFD pair), opening at **0.70** — matching
`turbulenceProperties`, the other generated dictionary, rather than the
0.85-0.90 the hand-written core files carry.

**The transport half is unblocked now.** It depended only on the `default`
question, which this change answers, so it need not wait for the `thermoType`
extractor or for anything further here.

## 8. OpenFOAM 14 is measured; four constants and one judgement call (2026-08-13)

Like item 7, this one runs the other way: the measurement is done in foamlore
and the remaining work is **here**. Done on 2026-08-13; what changed is
recorded at the end of this item.

Foundation released OpenFOAM 14 on 2026-07-14. foamlore added it as the 19th
checkout — `foundation-14` = `OpenFOAM-dev` at tag `version-14`, commit
`c046c72`, the frozen tag rather than `OpenFOAM-14`'s moving master — and
re-derived. Full record in `facts/VERIFICATION.md`, "2026-08-13 — OpenFOAM 14
renamed the accessor and moved no value", and the reasoning in
`fode-schemas/SPEC_RESPONSE.md` item 8.

**The release moves no value.** Against `foundation-13`: 0 of the 350
(model, coefficient) pairs differ, none added, none dropped, model set
identical, still `constant/momentumTransport`. The 441 previously committed
stores regenerated byte-identically, 23 additions only.

What it renames is the coefficient-dict accessor, `this->coeffDict()` →
`this->typeDict(type)`. That is worth knowing here rather than filing as
foamlore trivia, because the key looked up changed with it:
`coeffDict()` was `RASDict().optionalSubDict(type() + "Coeffs")`, and
`typeDict(type)` is `RASDict().optionalTypeDict(type)`. **v14 reads
`kEpsilon`, not `kEpsilonCoeffs`** — a dictionary spelling no earlier release
accepted, and v14's own headers now document it (22 model headers rewrote
their worked example from `kEpsilonCoeffs { … }` to `kEpsilon { … }`). A
`<parent>.<key>` table keyed on `<model>Coeffs` does not see the new form.

**Measured (2026-08-13, after this item was first written).** foamlore added
`src/OpenFOAM/db/dictionary` as a third sparse subtree in all 19 checkouts and
read `optionalTypeDict` (`dictionary.C:920-940`, foundation-14 `c046c72`). It
resolves three spellings in order:

| order | spelling | accepted in |
|---|---|---|
| 1 | `RAS { kEpsilon { … } }` | **v14 only** |
| 2 | `RAS { kEpsilonCoeffs { … } }` | v7-v14 |
| 3 | flat `RAS { Cmu 0.09; }` | v7-v14 |

**v14 is a strict superset of v13, so nothing here breaks.** The bare-type
spelling is added; the `Coeffs` spelling is not removed. Our `<parent>.<key>`
tables keyed on `<model>Coeffs` keep resolving exactly what they resolved
before, and v13's `optionalSubDict` (`dictionary.C:926-941`) had no fallback
chain at all — one lookup, then the enclosing dict. `::optionalTypeDict` is
absent from foundation 7-13 and from every opencfd release.

That downgrades the `<parent>.<key>` work from a repair to an optional gain:
adding `<model>` alongside `<model>Coeffs` would help v14 users and breaks
nothing, but no existing key is wrong today. Both quotes are cached and
quote-verified in foamlore (`get_fact model=dictionary`).

### What this side has to do

1. **Four constants in `schemas/_base.py`.** One new, three renamed — the
   existing Foundation ranges each extend by one release, and because v14 has
   every coefficient v13 had, the runs stay contiguous:

   ```python
   FOUNDATION_V14      = "Foundation v14"    # new
   FOUNDATION_V8_V13   -> FOUNDATION_V8_V14  = "Foundation v8-v14"
   FOUNDATION_V9_V13   -> FOUNDATION_V9_V14  = "Foundation v9-v14"
   FOUNDATION_V10_V13  -> FOUNDATION_V10_V14 = "Foundation v10-v14"
   ```

   Renaming rather than adding is safe here: foamlore checked, and the three
   `_V13` range constants are cited **only** by the generated
   `_turbulence_coeffs.py`. No hand-written schema entry uses them.

2. **Re-vendor two modules** from foamlore `fode-schemas/`:
   `_turbulence_coeffs.py` and `momentum_transport.py`.
   `turbulence_properties.py` did **not** change — the target file is chosen
   by `n == "7"`, the permanent OpenFOAM 8 rename boundary, so its Foundation
   tag stays `FOUNDATION_V7` exactly as item 4 asked, and cannot widen.

3. **One test assertion**, the same shape item 4 hit:
   `tests/schemas/test_turbulence_schemas.py:138` pins
   `schema.supported_in == (FOUNDATION_V8_V13,)` by exact tuple equality.
   It stays exact, just against the measured value.

4. **`docs/OPENFOAM_VERSIONS.md` (+ `_ja`)** — the fork/rename tables there
   stop at Foundation 13. v14 renames nothing in the dictionaries that page
   tracks, so this is a row, not a rewrite.

### The judgement call, which is ours and was left open on purpose

`FOUNDATION_SERIES` is still `"Foundation v7-v13"`. Widening it to `v7-v14`
also widens `BOTH`, and `BOTH` tags roughly 256 hand-written entries across
`control_dict.py`, `fv_schemes.py`, `fv_solution.py`, `block_mesh_dict.py` and
`turbulence_structure.py`. foamlore measures turbulence models only; it cannot
support a v14 claim for `controlDict` or `fvSchemes` keys on our behalf, so it
declined to widen the label and said so rather than quietly doing it.

Leaving it at `v7-v13` understates coverage in the Detail pane. Widening it
asserts something unverified about ~256 keys. The generated modules do not
import `FOUNDATION_SERIES` at all, so either choice regenerates cleanly and
this can be decided independently of items 1-3 above.

Note that `tests/schemas/test_schema_coverage.py:224` asserts
`FOUNDATION_SERIES in foundation` for keys that have existed since v7 — that
assertion is about the constant's *identity*, not its text, so it is unaffected
either way.

### Done here (2026-08-13)

`schemas/_base.py` gains `FOUNDATION_V14` and renames the three Foundation
ranges to `FOUNDATION_V8_V14`, `FOUNDATION_V9_V14` and `FOUNDATION_V10_V14`;
`_turbulence_coeffs.py`, `momentum_transport.py` and the generated
`THIRD-PARTY.md` are re-vendored (`turbulence_properties.py` was byte-identical
and is untouched); the one pinned assertion in
`tests/schemas/test_turbulence_schemas.py` follows the rename, still by exact
tuple equality. Point 4 above — the `OPENFOAM_VERSIONS.md` tables — was already
carried by commits `30c48f8`, `3dfa186` and `05eec50`.

`THIRD-PARTY.md` was the one file this item did not list and the one that had
already drifted: it is generated by foamlore's `gen_attribution.py`, and v14's
headers carry copyright years FoDE was not crediting (`2011–2024` → `2011–2026`,
18 checkouts → 19, and fourteen per-file rows gaining a line). Nothing in either
repository guards it — foamlore's `test_vendored_copy_matches` is parametrised
over `fode-schemas/*.py` only — so it is worth asking foamlore to widen that
parametrisation. A licence-attribution file is the wrong one to let drift
silently.

**The judgement call was decided: `FOUNDATION_SERIES` stays at
`"Foundation v7-v13"`.** The ~256 hand-written entries it tags have been
measured against Foundation 7-13 and a `dev` tree predating the `version-14`
tag; nothing has measured a `controlDict` or `fvSchemes` key against 14.
Understating coverage is the cheaper error — a label that stops one release
short is a gap, a label that runs one release long is a false claim. Carried
forward as item 9.

## 9. `FOUNDATION_SERIES` still says v7-v13 (2026-08-13)

Raised by the decision recorded at the end of item 8, and open on this side
rather than foamlore's: the label now stops one release short of what FoDE
supports everywhere else.

For a user running Foundation 14, every key tagged `BOTH` — `writeControl`,
`ddtSchemes.default`, `solvers.solver`, `scale`, the whole shared
`finiteVolume`/`lduMatrix` surface — reads in the Detail pane as
`Foundation v7-v13, OpenCFD v2106-v2606`, i.e. "not available in the release you
are running". That is the same too-narrow-tag failure item 6 existed to kill,
one release later.

Widening `FOUNDATION_SERIES` also widens `BOTH`, which is 360 tag sites:

| module | `BOTH` tags |
|---|---|
| `control_dict.py` | 88 |
| `fv_schemes.py` | 81 |
| `snappy_hex_mesh_dict/*` | 115 |
| `turbulence_structure.py` | 29 |
| `fv_solution.py` | 25 |
| `block_mesh_dict.py` | 22 |

**No test will notice either way.** `tests/schemas/test_schema_coverage.py:224`
asserts `FOUNDATION_SERIES in foundation` — the constant's *identity*, not its
text — so it passes before and after. A green suite is not evidence here, and
the next person to look at this should not mistake it for any.

Two things to fix at the same time, when it is widened:

- `schemas/snappy_hex_mesh_dict/_structure.py:230,234` tags `radius1`/`radius2`
  `(FOUNDATION_V12, FOUNDATION_V13, OPENCFD_SERIES)` — an explicit enumeration,
  not a range. Now that `FOUNDATION_V14` exists, that reads as "v14 was checked
  and `searchableCone` is absent", which nothing measured. Left alone
  deliberately in the item 8 change: the honest fix is a reading, not a
  relabelling.
- The comment at `schemas/snappy_hex_mesh_dict/_add_layers.py:150-155` says
  every Foundation release "from v7 to dev" still declares the compatibility
  entry. That `dev` tree predates the `version-14` tag, so widening would
  silently extend `minMedianAxisAngle`'s claim past what the comment covers.

### What the label asserts, settled before measuring anything

`schemas/_base.py` gave the label two readings that pointed opposite ways: the
collective-label comment called it "for entries shared across a whole fork
**rather than tied to one release**" (a fork-wide claim, which v14 would join
for free), while `BOTH`'s comment called it supported "across **every measured
release**" (a verification claim, which v14 has not earned).

Settled by the history rather than by preference. Commit `15720b5`, which
introduced `FOUNDATION_SERIES`, states that it audited every schema "against
Foundation 7-13 / OpenCFD v2106-v2606 for cross-version facts" and records
per-file tutorial coverage measured before and after. **The span was earned by
an audit, so it is a verification record.** "Collective" exempts a key from
naming one release; it does not exempt it from measurement. Both comments in
`_base.py` now say so, as does DEVELOPER.md.

That forecloses the cheap way out: item 9 cannot be closed by relabelling, only
by measuring.

### How far the evidence already reaches

foamlore's `foundation-14` checkout is no longer turbulence-only — items 7 and 8
added `src/finiteVolume/finiteVolume` and `src/OpenFOAM/db/dictionary` to its
sparse set. Two of the six modules are therefore measurable with no new fetch:

- **`fvSolution`'s reader directory is byte-identical between `foundation-13`
  and `foundation-14`.** That covers `fv_solution.py`'s 25 tags.
- **`fvSchemes`'s reader was refactored without losing a key.**
  `read(const dictionary&)` became `readDict()`, reading `*this` rather than a
  passed-in dictionary, but `ddtSchemes`, `d2dt2Schemes`, `interpolationSchemes`,
  `divSchemes`, `gradSchemes`, `snGradSchemes`, `laplacianSchemes` and
  `fluxRequired` are all still read.
- **v14 did remove one thing there:** `fvSchemes::dict()`, which resolved
  `select <name>;` into a sub-dictionary, is gone from both `.C` and `.H`. FoDE
  never carried a `select` key, so nothing here is wrong — but it is the proof
  that this scan is real work and not a formality. One release, one silent
  removal, in the dictionary family nobody had checked.

### Measured (2026-08-13): 246 confirmed, 1 removed, 60 unmeasured

The first pass reached only 34 of 307 keys, because the sparse checkouts held
almost none of the relevant readers. Both `foundation-13` and `foundation-14`
are **partial clones** (`blob:none`), not shallow ones, so `git sparse-checkout
add` pulls only the blobs for the paths added — `src/OpenFOAM/db/Time`,
`src/OpenFOAM/matrices`, `src/finiteVolume`, `src/mesh/blockMesh`,
`src/mesh/snappyHexMesh` took 1.7 s and 1.5 MB. `tutorials` took 6 s and 31 MB.
Both checkouts must be expanded identically or the differential measures
nothing.

| module | still read | removed | not covered | in tutorials |
|---|---:|---:|---:|---:|
| `control_dict.py` | 38 | 0 | 28 | 52 |
| `fv_schemes.py` | 11 | 0 | 4 | 11 |
| `fv_solution.py` | 40 | 1 | 8 | 37 |
| `block_mesh_dict.py` | 15 | 0 | 6 | 18 |
| `turbulence_structure.py` | 17 | 0 | 39 | 16 |
| `snappy_hex_mesh_dict/*` | 65 | 0 | 35 | 87 |
| **total** | **186** | **1** | **120** | **221** |

Counting a tutorial appearance as evidence in its own right — the release ships
a case using the key — **246 confirmed, 1 removed, 60 still unmeasured**. The
tutorial pass is not a weaker substitute for the source pass but a different
witness: source says a reader exists, a tutorial says a shipped case uses it. It
rescued 60 keys the source scan could not reach, and it is the evidence commit
`15720b5` used for the original audit.

**`sources/` is gitignored, regenerable working data in foamlore** (`/sources/*`,
only `.gitkeep` tracked), so expanding it commits nothing — but the state is not
reproducible until `facts/tools/fetch_sources.sh` carries those subtrees. That
is the request into foamlore; the scan itself lives here.

#### What the scan found, and why it settles the judgement call

One key came back **REMOVED**, and it is not a false positive.
`processorAgglomerator` is read by `foundation-13`'s `GAMGAgglomeration.C`
(`controlDict.found` / `.lookup`) and is absent from `foundation-14`, which
replaced it with a `processorAgglomeration { … }` sub-dictionary selected via
`isDict`/`subDict` — **with no compatibility lookup**, so the old spelling is
silently ignored there. OpenCFD v2606 still reads it. FoDE had that key tagged
`BOTH`. **Had `FOUNDATION_SERIES` been widened to v7-v14 without measuring, that
tag would have become a false claim** — which is the concrete answer to whether
this item was worth opening.

Reading the surrounding v14 code by hand turned up a second change the scan
could not flag: `minCellsPerProcessor` and `nCellsInCoarsestLevel` now share a
`lookupOrDefaultBackwardsCompatible<label>` pair, i.e. **Foundation 14 renamed
`nCellsInCoarsestLevel` to `minCellsPerProcessor`** and still accepts the old
name. The scan stayed silent correctly: the old name still appears as a literal
in v14, inside the compatibility list, so reporting it "removed" would have been
wrong. Automated differencing finds disappearances; it does not find renames
that keep both spellings.

Both are fixed in `schemas/fv_solution.py`, and both only changed on the
Foundation side — OpenCFD v2606 reads both spellings as current — so neither is
marked `status="renamed"` globally: doing that would tell an OpenCFD user to
write a key their fork does not read. `processorAgglomerator` keeps `BOTH` plus
a `deprecated_since` and a note; `minCellsPerProcessor` and
`processorAgglomeration` are new `FOUNDATION_V14` entries carrying
`renamed_from`.

#### What the caveat does and does not cover

`schemas/_base.py`'s `OPEN_ENDED_SERIES` makes the Detail pane render
`FOUNDATION_SERIES` with "(newer releases not yet measured)", so a v14 user no
longer reads a v13 span as "unavailable to me" — and `tests/ui/
test_supported_in_caveat.py` guards it, including the case where widening the
label without emptying the set would turn the caveat into a lie.

It is deliberately **label-level, not key-level**. The 246 keys measured above
still render the caveat, because `FOUNDATION_SERIES` is one shared string and
`supported_in` records no per-key measurement date. That is the right trade for
now — it understates rather than overstates — and it disappears entirely when
this item closes and the label widens.

### First pass, superseded (kept for the method)

`tools/scan_foundation14_keys.py` runs the scan. It is *differential* by design:
the checkouts are sparse, so "absent from the new tree" is ambiguous on its own
— the key may be gone, or its reader may simply not be checked out. Comparing
`foundation-13` and `foundation-14` with an identical method removes the
ambiguity, at the cost of only ever reporting on what the older tree can already
see. Matching is deliberately over-inclusive (the key name as a double-quoted
literal in any `.C`/`.H`), because a false "still read" merely understates what
needs a closer look, while a false "removed" would be caught on inspection.

Result over the 307 hand-written `KeySchema` entries tagged `FOUNDATION_SERIES`
(wildcard `<parent>.*` rows excluded):

| module | still read | removed | not covered |
|---|---:|---:|---:|
| `control_dict.py` | 5 | 0 | 61 |
| `fv_schemes.py` | 9 | 0 | 6 |
| `fv_solution.py` | 1 | 0 | 48 |
| `block_mesh_dict.py` | 1 | 0 | 20 |
| `turbulence_structure.py` | 17 | 0 | 39 |
| `snappy_hex_mesh_dict/*` | 1 | 0 | 99 |
| **total** | **34** | **0** | **273** |

**The reach is far smaller than a module-level count suggests, and the earlier
estimate in this item was wrong.** Having `src/finiteVolume/finiteVolume` in the
checkout does not cover `fv_schemes.py`'s keys, only the nine that
`fvSchemes.C` itself reads — the scheme *names* (`Gauss`, `linear`, `limited`,
…) are declared in `src/finiteVolume/interpolation` and elsewhere. `fvSolution/`
in the sparse set is a single header, `fvSolution.H`, with no `.C` at all: every
`solvers`/`relaxationFactors`/`PIMPLE` key is read from
`src/OpenFOAM/matrices/lduMatrix` and `src/finiteVolume/cfdTools`, neither of
which is checked out. Spot-checked against raw `grep`: `ddtSchemes` and
`simulationType` are present in both trees, `writeControl` and `solver` in
neither.

So the honest position is **34 keys measured with zero removals** — weak but
real positive evidence — and 273 still unmeasured. That is not enough to widen
`FOUNDATION_SERIES`.

Completing it needs `src/OpenFOAM/db/Time`, `src/OpenFOAM/matrices/lduMatrix`,
`src/finiteVolume/cfdTools`, `src/mesh/blockMesh` and `src/mesh/snappyHexMesh`
added to both the `foundation-13` and `foundation-14` checkouts — both, because
the scan is differential and an unmatched pair measures nothing. Mechanically a
`git sparse-checkout add`, but the local mirror has no `version-14` tag, so it
costs an upstream fetch. The checkout table lives in foamlore's
`facts/tools/fetch_sources.sh`, so that half is a request there; the scan itself
is this script and stays here.

### Resolved on the evidence (2026-08-13): the label is widened

The "60 unmeasured" figure above was itself wrong, and the correction changed
the cheapest fix. **37 of those keys are invisible by construction, not
unchecked**: the model coefficient dictionaries — `kEpsilonCoeffs`,
`kOmegaSSTCoeffs`, `SmagorinskyCoeffs`, the LES delta `…Coeffs` — never appear
as literals in any OpenFOAM source, in either tree, because they are built at
runtime as `typeName + "Coeffs"` (`dictionary.C:882/906/929`). No literal scan
will ever see them however many subtrees are fetched. They are also already
measured: foamlore's reading of `optionalTypeDict` under item 8 is exactly that
measurement.

That leaves **283 covered, 1 removed, ~21 genuinely unmeasured**. Retagging 283
measured keys would have been the large edit; retagging 21 stragglers is the
small one, and it makes the Detail pane's caveat key-accurate for free. So:

- `FOUNDATION_SERIES` is now `"Foundation v7-v14"`.
- `FOUNDATION_V7_V13` is new, carried by the ~21 keys whose readers were never
  reached — `control_dict` 9 (`fileHandler`, `functions` and its common
  members, `maxDi`), `fv_schemes` 2 (overset), `fv_solution` 3
  (`nAlphaCorr`, `nAlphaSubCycles`, `finalOnLastPimpleIterOnly`),
  `block_mesh_dict` 2, `snappy_hex_mesh_dict` 4, plus `printCoeffs`.
- `OPEN_ENDED_SERIES` holds `FOUNDATION_V7_V13` alone, so only those keys are
  qualified in the pane.
- `processorAgglomerator` was retagged **first**, and deliberately: widening
  `FOUNDATION_SERIES` while it still carried `BOTH` would have extended its
  claim into the one release we proved it absent from. It now carries the
  closed span plus `deprecated_since`, which is what distinguishes "measured
  and gone" from "not yet looked at".

`tests/ui/test_supported_in_caveat.py` guards the distinction from both ends,
including the case where a label naming v14 is left in `OPEN_ENDED_SERIES`.

**What still closes this item:** those ~21 keys measured. Their readers are in
solver applications rather than `src/`, so it needs `applications/` added to
both checkouts — the same `sparse-checkout add`, one directory larger.

One caveat worth recording rather than acting on: the two `fv_schemes` overset
entries are tagged as Foundation-supported at all, which is doubtful — overset
is an OpenCFD feature. The scan cannot settle it from a sparse tree, and it is a
pre-existing tagging question rather than anything v14 introduced, so it is
named here instead of being changed on suspicion.

### Closed on the measurement (2026-08-14)

`foundation-13` and `foundation-14` were expanded to an identical sparse set of
the whole of `src`, `applications` and `etc` (107 MB and 246 MB, one
`sparse-checkout add`), and the 21 were measured. **The label needed no further
widening; what the keys needed was correcting.** They resolved three ways:

| outcome | count | keys |
|---|---:|---|
| Foundation reads it in v14 → `BOTH` | 9 | `fileHandler`, `functions`, `functions.executeInterval`, `nAlphaSubCycles`, `nAlphaCorr`, `boundary.separationVector`, `minFaceFlatness`, `geometry.planeType`, `singleRegionName` |
| **never a Foundation key** → `(OPENCFD_SERIES,)` | 6 | `functions.writeToFile`, `functions.useUserTime`, `finalOnLastPimpleIterOnly`, `oversetInterpolation`, `oversetInterpolationSuppressed`, `mergeType` |
| Foundation read it and stopped → closed span + `deprecated_since` | 5 | `maxDi` (v13), `functions.regionType` (v13), `functions.timeEnd` (v12), `functions.formatOptions` (v8), `minTriangleTwist` (v10) |
| already closed | 1 | `processorAgglomerator` (v14) |

Two more were corrected in the same pass, both found by the widened scope rather
than by the 21: `functions.timeStart`, which carried `FOUNDATION_SERIES` and is
Foundation v7-v11 (dropped at v12, like its `timeEnd` twin); and
`geometry.radius1`/`radius2`, which is the eleventh mistagged key and the
clearest illustration in this whole document of why a literal needs a reading
behind it — see below. `schemas/_base.py` gains `FOUNDATION_V7_V9`,
`FOUNDATION_V7_V11` and `FOUNDATION_V7_V12` for the closed spans.

**`OPEN_ENDED_SERIES` is now empty**, which is the closed state of this item.
`FOUNDATION_V7_V13` survives, carried by `processorAgglomerator` alone, and its
meaning has inverted: it no longer says "not yet looked at" but "measured, and
it closed at 13". The Detail pane appends no caveat anywhere, because there is
nothing left it would be true of.

#### Four things this document had wrong, corrected in place

- **The readers are not where this item said they were.** "Their readers are in
  solver applications rather than `src/`" (above) was only half right: they were
  spread across `src/OpenFOAM/global`, `src/OpenFOAM/meshes`,
  `src/functionObjects/field`, `src/twoPhaseModels/VoF` and `src/meshCheck` as
  well as `applications/`. Fetching only `applications/` would have left most of
  them unmeasured.
- **The 21 were miscounted.** The enumeration above gives `fv_solution` 3 and
  adds "plus `printCoeffs`". In the code it is `fv_solution` 4 — the fourth
  being `processorAgglomerator`, which spells its tuple out rather than using
  the module shorthand — and `printCoeffs` carries `BOTH`, not the narrow label.
- **The overset caveat was right and far too small.** It named two keys as
  doubtfully Foundation-tagged. Measured, it is **eleven**: the two overset
  categories and their two `.*` wildcard rows, `mergeType`, `minTriangleTwist`,
  `finalOnLastPimpleIterOnly`, `writeToFile`, `useUserTime`, and
  `geometry.radius1`/`radius2`. Every one told a Foundation user that a key was
  available which their fork does not read.
- **`searchableCone` never reached Foundation.** The `radius1`/`radius2` tag
  said "reached Foundation in v12"; Foundation's `src/meshTools/searchableSurfaces/`
  holds `box closedTriSurface collection cylinder disk extrudedCircle plane
  plate sphere triSurface withGaps` and **no cone**, in every release v7-v14.
  The v12 evidence was a literal `"radius1"` belonging to `truncatedConeToCell`,
  an unrelated topoSet/zone source. A literal matched; the wrong reader owned it.

#### The near-miss, and why every ABSENT is now gated on a hand read

`executeInterval` was on its way to being retagged OpenCFD-only. It appears as a
literal in **no** Foundation source, because `timeControl.C:93` builds the name
as `prefix_ + "Interval"` — and Foundation ships it in
`etc/caseDicts/functions/mesh/checkMesh`. It is the same blindness that hid the
37 `<Model>Coeffs` keys, in a hand-written key this time, and it is why the scan
now reads `etc/caseDicts` beside `tutorials` and why its third verdict was
renamed from `NOT COVERED` to **`ABSENT`** with an explicit warning attached.

Three more keys sit in the same category and are correct as they stand:
`advectionDiffusionCoeffs` (`+ "Coeffs"`), `pRefCell`
(`field.name() + "RefCell"`, `findRefCell.C:43`), and `minFlatness`, which has
no reader in either fork and is already `status="ineffective"`.

**Closure condition, and it is met:** every key is STILL READ, or REMOVED with a
`deprecated_since`, or off the Foundation label, or an ABSENT with a named
runtime construction. The scan's remaining 42 ABSENT are the 38 `<Model>Coeffs`
plus those four.

### Two asks back into foamlore

**1. Carry the widened scope in `fetch_sources.sh`.** It has `RENAME_SUBTREES`
but not `src`, `applications` or `etc`, so a fresh `foundation-13`/`foundation-14`
checkout cannot reproduce this scan — the same "reproducible only by accident"
state item 10's first ask fixed for the rename census. Please add the three to
the Foundation checkouts. `src` + `applications` cost about 83 MB per checkout
and `etc` a further 4.5 MB, measured against a complete tree.

**`etc` is load-bearing, not a rounding error.** It is the only place
`executeInterval` appears anywhere in the Foundation tree, and dropping it would
reintroduce exactly the false retag described above.

**2. The rename census is missing a pair, and the reason is item 10 recurring.**
Dating `functions.regionType` turned up
`dict.lookupBackwardsCompatible({"select", "regionType"})` at
`src/functionObjects/field/fieldValues/surfaceFieldValue/surfaceFieldValue.C:668`
and `:698` in Foundation 12 — exactly the declaration family `scan_renames.py`
exists to collect. It is **not** in `facts/derived/renames.json`, whose 21 pairs
cover nine dictionaries; `src/functionObjects` is in neither `fetch_sources.sh`
nor `scan_renames.py`'s `DICTIONARY_OF_PATH`, so the census cannot see it.

That is item 10's finding one subtree further out: the census still reports on
whatever happens to be checked out, and `controlDict`'s `functions` block — a
dictionary FoDE has a schema for — is outside it. Please add
`src/functionObjects` to both the fetch scope and the path map, and re-derive.
The pair is worth having beyond the count: Foundation read `regionType` only as
a backwards-compatible spelling of `select` and reads neither since v13, while
OpenCFD reads `regionType` as its current name — the fork-disagreement shape the
"Renames inside a file" section of [OPENFOAM_VERSIONS.md](OPENFOAM_VERSIONS.md)
already warns about, with a third variant (Foundation dropped *both* spellings)
that page has no example of yet.

FoDE has already tagged the key from this reading, so nothing here is blocked on
the re-derive; what the census gains is the pair itself and whatever else that
subtree declares across nineteen checkouts.

## 10. The rename scan has never seen most of FoDE's dictionaries (2026-08-13)

This one is a by-product. Item 9 needed `src/OpenFOAM/db/Time`,
`src/OpenFOAM/matrices`, `src/finiteVolume`, `src/mesh/blockMesh` and
`src/mesh/snappyHexMesh` in the Foundation checkouts, so they were added by
hand. `scan_renames.py` reads `sources/*/`, i.e. whatever is checked out — so
until now it has only ever looked at the turbulence subtree.

Counting `lookupBackwardsCompatible` declarations in `foundation-14` outside
`src/MomentumTransportModels`, and discarding `dictionary.C`/`.H`/
`dictionaryTemplates.C` (which *define* the mechanism rather than call it),
there are five real call sites, in dictionaries FoDE covers:

| file | dictionary |
|---|---|
| `db/Time/TimeIO.C` | `controlDict` |
| `cfdTools/…/pimpleNoLoopControl.C` (×2) | `fvSolution` |
| `lduMatrix/…/GAMGAgglomeration.C` | `fvSolution` |
| `mesh/snappyHexMesh/…/medialAxisMeshMover.C` | `snappyHexMeshDict` |
| `finiteVolume/pointMesh/pointMeshMover.C` | — |

**One was already a FoDE defect, and it is not a v14 problem.**
`pimpleNoLoopControl.C` declares `{"transportCorrectionFinal",
"turbOnFinalIterOnly"}`. FoDE carried `turbOnFinalIterOnly` as a plain valid key
tagged `BOTH` and had no `transportCorrectionFinal` at all — presenting a
historical spelling as current and unable to name its successor. Measured per
release across all eight Foundation checkouts, **the rename is Foundation 11**,
with backwards compatibility retained through v14. It had been wrong here for
three releases, and only became visible because a subtree was fetched for an
unrelated reason. The same file's `{"simpleRho", "SIMPLErho"}` pair is older
still: every Foundation release from v7 reads `simpleRho`, and FoDE had neither
spelling.

Both are fixed on this side (`schemas/fv_solution.py`, plus a new
`FOUNDATION_V11_V14`), fork-asymmetrically — OpenCFD v2606 reads
`turbOnFinalIterOnly` and `SIMPLErho` as its *current* names and has neither
Foundation spelling, so neither is marked `status="renamed"` globally.

### The three asks

1. **Widen the fetch scope.** Add those five subtrees to `fetch_sources.sh` for
   every Foundation checkout (they are already added by hand locally, so the
   measurement above is reproducible only by accident until this lands). They
   are cheap: the checkouts are partial clones (`blob:none`), so
   `git sparse-checkout add` pulls only the added paths — 1.7 s and 1.5 MB per
   checkout, and `tutorials` a further 6 s and 31 MB.

2. **Re-derive renames over the widened scope.** The five call sites above are
   what one release shows; eight Foundation checkouts and eleven OpenCFD ones
   will show more, and each feeds `renamed_from`/`use_instead`/
   `deprecated_since` here and the "Renames inside a file" section of
   `OPENFOAM_VERSIONS.md`, which foamlore splices. Note that section currently
   records none of these.

3. **Guard `THIRD-PARTY.md`.** It is generated by `gen_attribution.py` and
   vendored into FoDE, but `test_vendored_copy_matches` is parametrised over
   `fode-schemas/*.py` only, so nothing notices when it drifts — and it had
   drifted by 32 lines when the v14 work found it (`2011–2024` vs `2011–2026`,
   18 checkouts vs 19, fourteen per-file copyright rows). It is a
   licence-attribution record, which is the worst kind of file to let drift
   silently.

### Done in foamlore (2026-08-14)

All three landed, in commits `86a5bb4` ("Fetch the dictionary readers too, and
guard the attribution file") and `2b314b8` ("Widen the rename census past the
turbulence subtree").

1. **The fetch scope is widened.** `facts/tools/fetch_sources.sh` now carries a
   `RENAME_SUBTREES` list — `src/OpenFOAM/db/Time`, `src/OpenFOAM/matrices`,
   `src/finiteVolume`, `src/mesh/blockMesh`, `src/mesh/snappyHexMesh` — applied
   to every checkout beside `src/OpenFOAM/db/dictionary`. The measurement above
   is reproducible rather than accidental.

2. **The renames are re-derived over that scope.** `facts/derived/renames.json`
   holds **21 pairs, 0 unresolved**, rendered through `render_renames.py` into
   `fode-docs/renames_table.md` and spliced into this repository's
   [OPENFOAM_VERSIONS.md](OPENFOAM_VERSIONS.md) generated `renames-table` region
   by commit `1ca5680`. All five call sites listed above are in it —
   `writeFrequency` → `writeInterval`, `SIMPLErho` → `simpleRho`,
   `turbOnFinalIterOnly` → `transportCorrectionFinal`, `nCellsInCoarsestLevel` →
   `minCellsPerProcessor`, `minMedianAxisAngle` → `minMedialAxisAngle` — along
   with `motionSolver` → `pointMeshMover`, which the `pointMeshMover.C` row
   above could not name a dictionary for at the time. **Ask 2's closing
   sentence, "Note that section currently records none of these", no longer
   holds and is retracted here.**

3. **`THIRD-PARTY.md` is guarded.** Not by widening `test_vendored_copy_matches`
   — that is parametrised over `fode-schemas/*.py`, and the attribution file is
   neither in that directory nor a `.py` — but by a purpose-built twin,
   `test_vendored_attribution_matches()` in
   `facts/tests/test_generated_schemas.py`, comparing foamlore's copy against
   FoDE's byte for byte. The two are identical today.

### What this side owes back

Nothing yet, beyond keeping `tools/scan_foundation14_keys.py` pointed at
whatever the checkouts become. That script is a stopgap for a question foamlore
answers better: it reads literals, so it is blind to any key assembled at
runtime, and it finds disappearances but not renames that keep both spellings,
which is exactly how `nCellsInCoarsestLevel` → `minCellsPerProcessor` escaped it
and had to be read by hand.

The runtime-assembly blindness is no longer illustrated only by the
`<Model>Coeffs` family. Item 9's closing measurement found a second live
instance in a hand-written key: `executeInterval` is built as
`prefix_ + "Interval"` (`src/OpenFOAM/db/functionObjects/timeControl/
timeControl.C:93`), appears as a literal in no Foundation tree, and is
nonetheless shipped by Foundation in `etc/caseDicts/functions/mesh/checkMesh`.
A literal scan would have concluded the key was not Foundation's at all. See
item 9.

**And this item's own finding recurs one subtree further out.** The three asks
above were raised because the census had only ever seen the turbulence subtree.
It now sees five more — and it still does not see `src/functionObjects`, where
Foundation 12 declares `lookupBackwardsCompatible({"select", "regionType"})`
(`surfaceFieldValue.C:668,698`). That pair is absent from the re-derived
`renames.json`. It is filed as item 9's second ask rather than repeated here,
but the lesson belongs to this item: **widening the fetch scope once does not
finish the census, it only moves its edge.** Each dictionary FoDE gains a schema
for is a candidate subtree, and the census is complete only against the set that
is actually checked out — which is why the scope, not the scan, is the thing to
keep an eye on.

## 11. The `BOTH` tags have never been audited the way the narrow ones were (2026-08-14; replanned 2026-09-05)

Opened by item 9's result rather than by a report. Of the 21 keys item 9
measured, **eleven claimed a fork that never read them** — and nothing about
that failure mode was specific to those keys. They were simply the ones sitting
under a label that invited scrutiny: `FOUNDATION_V7_V13` existed to say
"unverified", so somebody eventually verified them. `BOTH` asserts *two* forks
and advertises no doubt at all.

### What the population actually is

Measured from the registry on 2026-09-05, not from the module text:

| module | `BOTH` keys | (of which wildcard) | `BOTH` **choices** |
|---|---:|---:|---:|
| `snappy_hex_mesh_dict/*` | 120 | 7 | 97 |
| `turbulence_structure.py` | 108 | 39 | 107 |
| `control_dict.py` | 66 | 3 | 142 |
| `fv_solution.py` | 66 | 5 | 145 |
| `fv_schemes.py` | 29 | 10 | 110 |
| `block_mesh_dict.py` | 22 | 1 | 28 |
| **total** | **411** | **65** | **629** |

Two corrections to the 2026-08-14 record. The key count is 411, not ~360. And
**choice values were never counted**: there are 629 more, and they are not a
lesser population — two shipped defects were choice values, `processorAgglomerator`'s
method names (gone from Foundation 14) and the `generalizedNewtonian` fork
rename. The real surface is ~1,040 sites.

Sizing the whole schema layer puts that in proportion. Every hand-written entry
carries a `supported_in`: 467 keys and 663 choices, 1,130 claims, of which
**1,040 — 92% — are the unaudited `BOTH`**. The generated modules carry 964 keys
and 807 choices, every one measured across 19 releases. The Detail pane renders
both identically, so a user cannot tell a measured span from a guess.

### Why item 9's method does not transfer

Item 11 was first recorded as "the procedure is written down and the scanner
already scans `BOTH`". Testing that on 2026-09-05 showed otherwise, and the
reason is structural rather than a missing feature.

**A whole-tree literal scan does not discriminate.** OpenCFD's `src` yields
30,351 distinct string literals. Run against `block_mesh_dict`'s 20 checkable
`BOTH` keys it returns **0 ABSENT in either fork** — generic names (`type`,
`name`, `faces`, `scale`, `geometry`) match something in a pool that size no
matter who reads them. That is item 9's `radius1`/`truncatedConeToCell` failure
at scale. The method worked there because item 9 was a **differential** between
two checkouts of one fork, where a shared false-positive rate cancels; `BOTH`
asks an absolute question, where it does not.

**Reader-scoping restores discrimination and introduces two new error modes.**
Scoped to `src/mesh/blockMesh` the pool is 362 literals, 84x less noise, and
`inGroups` correctly flips to ABSENT for the blockMesh reader. But:

- `inGroups` is still a valid `blockMeshDict` entry — it is handled downstream by
  `polyPatch`. Scoping to one reader can be *too* narrow.
- `mergePatchPairs` is read in **`applications/`, not `src/`** — in OpenCFD
  `applications/utilities/mesh/generation/blockMesh/blockMesh.C` is the only
  place it appears at all. A map naming `src/mesh/blockMesh` reports a live key
  as unread by that fork.

  *(An earlier draft of this section claimed `mergePatchPairs` appears in zero
  `.C`/`.H` files of either fork. That was wrong, from a truncated grep followed
  by one scoped to the wrong directory; corrected 2026-09-05. The key is a
  reader-map hazard, not a literal-scan blind spot — which makes it a sharper
  warning about the part of this design that is actually risky, not a softer
  one.)*

The genuine literal-scan blind spots are separate and confirmed by the full
index: `executeInterval` and `executeControl` are `prefix_ + "Interval"` and
appear nowhere as literals; the 41 `<Model>Coeffs` names among
`turbulenceProperties`'s 63 `BOTH` keys are `typeName + "Coeffs"`; `minFlatness`
is read by neither fork at all, an upstream defect reported to OpenCFD as #3592.
Together with `radius1` (wrong reader matched), that is why **no retag on scan
output alone** is a design constraint here rather than a caution.

### The evidence was not where this item assumed (closed 2026-09-05)

| | Foundation | OpenCFD, as found |
|---|---|---|
| foamlore `sources/` | complete: `src` + `applications` + `etc`, 8.5-9.3k `.C`/`.H` per checkout | **13 of 50 `src` subdirs, no `applications/`, no `etc/`** — ~3.5k files |
| elsewhere on disk | `openfoam-sources/OpenFOAM-{7..12,dev}` | `/usr/lib/openfoam/openfoam{2212..2606}` at ~21k files, plus `OpenFOAM-v{2106,2206}` |

Foundation was widened during items 9 and 10; OpenCFD never was. A *content*
scan of those checkouts would have marked hundreds of valid OpenCFD keys absent
and stripped the fork from them — the failure the source-tree note warns about.

**What that did *not* invalidate.** The first version of this section claimed
the narrow checkouts also made foamlore's rename census and dictionary-file
counts unsound, and that the widening was therefore a repair. Both claims were
wrong, and foamlore corrected them on 2026-09-05:

- The checkouts are **partial clones** (`filter=blob:none`), so every path was
  always listed; only blob *contents* were missing from disk. `opencfd-v2606`
  listed 26,137 paths — 11,608 of them under `tutorials/` — while far fewer were
  materialised.
- `scan_dictionary_files.py` reads `git ls-tree` on the pinned commit, never the
  working tree, deliberately for determinism. Its counts were sound throughout.
- The rename census was **bounded, not unsound**. `scan_renames.scope_of()` is
  `CENSUS_SUBTREES ∩ what the checkout carries` — a *declared* list, not the raw
  sparse set, exactly so both forks are scanned to the same width whichever is
  physically wider. Within that scope "OpenCFD does not declare this" was sound;
  outside it no verdict was made.

So the width asymmetry was real but narrow in consequence: it blocked a
whole-tree **content** scan, which is precisely what the oracle below needs, and
nothing else. A prerequisite for this item, not a repair of anything published.

**Closed the same day.** All 19 checkouts now fetch `src applications etc
tutorials`; `opencfd-v2606` went from 13 to 50 `src` subdirs and gained the three
top-level trees it had none of, `sources/` from 2.0 GB to 4.9 GB. `tutorials`
was added beyond what this item asked for, because the shipped-dictionary scan
in Phase 1 needs it and the original ask said only `src` + `applications` +
`etc` — underspecified for its own next phase. `regen_check.sh` came back
byte-identical across all six artifact layers afterwards and 134 tests pass,
which is itself the evidence that nothing published had depended on the narrow
width.

### The decision: generate `supported_in`, do not audit it

Taken 2026-09-05, after weighing three options.

Moving *all* schema generation to foamlore was rejected: `executeInterval` and
the 41 `<Model>Coeffs` names show a constructor-reading generator cannot see
every key; per-key judgement
(`renamed_from`, `status`, `use_instead`) is a decision about what to tell the
user and foamlore already declined it under item 3; a second extractor per
family is the expensive thing, as `docs/SCHEMA_CANDIDATES.md` says; and FoDE
would lose the ability to add a schema without the sibling repo.

Keeping the split but **moving the line** was taken instead. Today it runs by
*family* — turbulence generated, the rest hand-written — which was the tractable
boundary rather than a principled one. It should run by **kind of claim**:

| claim | owner |
|---|---|
| `supported_in` — does fork X release Y read key K | **foamlore** — pure fact, no judgement |
| choice *lists* — the run-time selection table | FoDE |
| `renamed_from` / `status` / `use_instead` | FoDE — judgement |
| `required` / `default` semantics | FoDE |
| descriptions, notes, anything about FoDE's own UI | FoDE |
| coefficient facts | foamlore, unchanged |

The argument that decides it: **the instrument this item needs is the
version-tag oracle.** Reader-scoped scan plus shipped-dictionary scan across
both forks has to be built either way. Run once as an audit, it fixes 1,040
sites and must be re-run at every OpenFOAM release, because hand-written tags
decay. Wired in as a generator, the tag is correct by construction and this item
becomes a test that fails when a release moves. Same Phase 1 cost, no Phase 5.

### Outcome (2026-09-08)

Measurement complete: seven dictionaries, nineteen releases, 354 spans of
which 340 publish. Every one of the fourteen refusals carries a written reason
and is *terminal* — seven `scope_limited`, where the reader migrated into
`applications/modules` and this side excludes solvers by design, and seven
`no_evidence`, where FoDE's own `runtime_assembled` or `known_unseen` correctly
told the scan not to look.

Consumption is complete for five of the seven. `blockMeshDict`, `fvSchemes`,
`fvSolution`, `controlDict` and `snappyHexMeshDict` now agree with the
measurement on **every** comparable key — 189 of them — which is the first time
this project's version claims have been verified rather than merely
self-consistent. The turbulence pair's 108 remaining differences are one cause,
recorded under **Update candidates** in DEVELOPER.md: one module serves two
dictionary spellings from one table, so every key claims `BOTH` where the
per-file measurements correctly differ. The wrong-*file* half of that is fixed
(`KeySchema.only_in_files`); the per-file *tags* are not.

**Nine wrong tags were retired between the two sides**, and none of them was
found by FoDE's own tests:

| key | was | is |
|---|---|---|
| `functions.mode` | BOTH | Foundation v7-v8 + OpenCFD |
| `fastMerge` | BOTH | Foundation only |
| `geometry.e1`, `geometry.e3`, `geometry.innerRadius`, `addLayersControls.solver` | BOTH | OpenCFD only |
| `density` | BOTH, two values that abort the run | OpenCFD only, `variable`/`uniform` |
| `LES.turbulenceModelCoeffs` | BOTH | removed; in no release of either fork |
| 26 keys | offered in both spellings | restricted to the one their releases read |

Two of those reject or abort a run rather than merely misinform, and two
OpenFOAM defects were reported upstream and merged for v2612 — neither
reachable by reading schemas.

### Plan

**Phase 0 — the evidence (foamlore). Done 2026-09-05.** The `opencfd-*`
checkouts are widened to `src applications etc tutorials`, matching the
Foundation ones and adding `tutorials` for Phase 1's shipped-dictionary scan.
See the section above for what this did and did not fix.

**Phase 1 — the oracle (foamlore, with FoDE's input).** Three evidence sources,
because no single one is sound:

1. a reader-scoped literal scan, driven by a dictionary -> reader-path map FoDE
   supplies (~15 entries: `blockMeshDict` -> `src/mesh/blockMesh`,
   `snappyHexMeshDict` -> `src/mesh/snappyHexMesh`, `controlDict` ->
   `src/OpenFOAM/db/Time` + `src/functionObjects`, and so on);
2. a shipped-dictionary scan over `tutorials/`, `etc/caseDicts/` and
   `applications/test/*/system/`, which is the only evidence for a key no
   source reads under any name — `SHIPPED_DIRS` already exists in
   `tools/scan_foundation14_keys.py`;
3. a hand read of whatever survives both.

Verdicts are per fork and three-valued — `READ`, `SHIPPED-ONLY`, `UNSEEN` — not
the present binary.

**Phase 2 — consume, smallest module first.** `block_mesh_dict` (22) ->
`fv_schemes` (29) -> `fv_solution` / `control_dict` (66 each) ->
`snappy_hex_mesh_dict` (120) -> `turbulence_structure` (108, of which 39 are
wildcards and much is already foamlore's). On the first pass per module, keep
the existing hand-written tag and *diff* against the oracle rather than
replacing it: a wrong reader-map entry mislabels a whole dictionary at once,
where a hand-written tag is wrong one key at a time. Each module is a shippable
correction on its own.

**Cross-check on two, publish from nineteen.** A verdict set measured on one
pinned release per fork is a *cross-check* artifact: a disagreement between two
independent implementations then means a measurement error rather than a
release difference, which is what makes comparing them worth anything. It is
not a source of `supported_in`. `functions.mode` proved this on 2026-09-06 —
measured on foundation-12 against opencfd-v2606 it reads as cleanly
OpenCFD-only, and Foundation ships `fieldMinMax` reading
`lookupOrDefault<word>("mode", "magnitude")` at v7 and v8 before dropping the
model at v9. Publishing that verdict would have replaced one wrong tag with
another and given it the authority of a measurement, which is the specific harm
this item exists to prevent. `tools/fode-reader-paths.json` declares the
constraint as `verdicts_publishable_from: all_releases` rather than leaving it
to whoever consumes the output, and a test pins it.

**Phase 3 — the 629 choices**, same instrument, once keys are done.

**Cost.** The instrument is roughly a day. The hand-reading does not compress:
expect 300-400 sites needing a human read across keys and choices. The
difference from the original plan is that this cost is paid once rather than
every release.

## 12. The laminar stress models are unmeasured, and `phaseSystemModels` is unfetched (2026-09-03, closed 2026-09-04)

Neither ask blocks anything: FoDE has landed the fix that raised them, with the
prose hand-written and the tags measured locally. Both are about closing the gap
between "measured by hand, here" and "derived in the store, once".

### How this came up

A report that the RAS selector lost its choices when `RASModel` was renamed. It
had not — `RAS.RASModel` and `RAS.model` have always shared one list, and a test
pins it — but checking turned up five real defects in the *same* hand-written
lists, four of them tags that were simply wrong:

| defect | what it said | what nineteen checkouts say |
|---|---|---|
| `SpalartAllmarasDES`/`DDES`/`IDDES`, `kOmegaSSTDES` | Foundation-only | both forks, every release |
| `kOmegaSSTDDES`, `kOmegaSSTIDDES` | not offered at all | OpenCFD, every release |
| `GEKO` | OpenCFD v2106-v2606 | v2606 only |
| `sigma` / `EBRSM` | OpenCFD v2106-v2606 | v2212+ / v2206+ |
| `kOmega2006` | Foundation v7-v14 | v9+ |
| `laminar` selector | 4 choices, all `BOTH` | 7 choices, five of them fork- or range-specific |

The cause of the first two rows is worth recording because it is a *method*
error, not a transcription one: the list was read off a directory listing of
`.../turbulenceModels/LES/`, and OpenCFD keeps the DES models in a sibling
`DES/`. The list is now the run-time selection table instead — every name passed
to `makeRASModel`/`makeLESModel`/`makeLaminarModel` — because a name absent from
that table cannot be constructed whatever the tree contains.

Note that `kOmegaSSTDDES` and `kOmegaSSTIDDES` were already in `MODEL_DOCS`.
foamlore had derived them; only the hand-written list omitted them, so FoDE
could explain `kOmegaSSTDDESCoeffs` while refusing to offer `kOmegaSSTDDES`.

### The asks

**Ask 1 — extend the fact store to the laminar stress models.** This is item 5's
boundary applied consistently. Item 5 assigns the choice *list and its tags* to
`turbulence_structure.py` and leaves the *prose* to the generator; `MODEL_DOCS`
honours that for 29 RAS/LES models and for zero laminar ones. So `laminar.model`
is the one selector where FoDE hand-writes every description, which is the
asymmetry item 5 exists to prevent. It should be cheap:

- the seven classes live in `laminar/`, a sibling of `RAS/` and `LES/` inside
  the subtree `fetch_sources.sh` already pulls — no fetch change;
- each carries the same Doxygen `Description` block the extractor already reads,
  and `Maxwell`, `Giesekus`, `PTT` and `lambdaThixotropic` carry `Reference:`
  blocks in the shape `MODEL_DOCS` notes already quote;
- the fork-divergent spelling is just two model names with disjoint checkout
  sets, which `collapse()` already handles.

The measured table, as the expected output to check a reply against:

| model | Foundation | OpenCFD |
|---|---|---|
| `Stokes` | 7-14 | v2106-v2606 |
| `Maxwell` | 7-14 | v2106-v2606 |
| `generalizedNewtonian` | 7-8 | v2106-v2606 |
| `generalisedNewtonian` | 9-14 | — |
| `lambdaThixotropic` | 9-14 | — |
| `Giesekus` | 7-14 | — |
| `PTT` | 8-14 | — |

`tests/schemas/test_turbulence_schemas.py::TestSelectorChoiceLists::test_no_laminar_model_is_covered_by_foamlore`
is the tripwire: it asserts none of these names is in `MODEL_DOCS`, so it fails
the moment this ask lands — which is the signal to delete the hand-written
blurbs in favour of the upstream headers.

**Ask 2 — the OpenCFD checkouts cannot see `twoPhaseTransport`.**
`fetch_sources.sh` gives Foundation rows the whole of `src` + `applications` +
`etc`, but OpenCFD rows get only `src/TurbulenceModels` plus the census
subtrees. `src/phaseSystemModels` is in neither, so
`simulationType twoPhaseTransport` — a *value* of a key in a dictionary FoDE has
a schema for, written by tutorials in every release of both forks — is
unmeasurable across OpenCFD from `sources/`. It was closed here only by reading
a separate complete v2606 tree. That is item 10 recurring one subtree further
out. The ask is `src/phaseSystemModels` on the OpenCFD rows.

### Answered (2026-09-04)

Both asks done — `facts/store/laminar/`, 78 stores, a fourth family
(`facts/tools/laminar_models.py`), reproducing FoDE's expected table exactly
(including the three spans measured by hand: `lambdaThixotropic` at
`FOUNDATION_V9_V14`, `sigmay` at `FOUNDATION_V11_V14`, `residualAlpha` at
`FOUNDATION_V12_V14` — "nothing needed correcting"); `src/phaseSystemModels`
now joins `CENSUS_SUBTREES`, so `twoPhaseTransport`'s `BOTH` tag is confirmed
against OpenCFD's own tree rather than a Foundation reading of the same class.

**`MODEL_DOCS` coverage was deliberately not wired** when this item closed, and the
offer was taken up on **2026-09-05**. The reasoning for the delay stands and is why the
shape shipped is the narrow one: `generate_fode_schemas.py` emits both prose *and* a
`SCHEMAS` entry for every model it is given, and the laminar models' `SCHEMAS` entry
would have collided with what `turbulence_structure.py` already hand-owns
(`laminar.MaxwellCoeffs`, `nuM`/`lambda`/`modes`, `required=True` where the generator
produces none — several with prose about `modes` no extractor emits). `builtin.py` loads
the hand-written module first and the collision would have resolved silently in the
generator's favour.

**What shipped instead**, item 5's boundary applied exactly: a *prose-only* generated
module, `schemas/_laminar_models.py`, carrying `MODEL_DOCS` and not one other statement —
no `KeySchema`, no `SCHEMAS`, no `TARGET_FILE`, so there is nothing for the registry to
merge and nothing that can outrank a hand-written key. foamlore routes it by the
directory a fact was measured into (`facts/derived/laminar/` is prose-only), so a laminar
model cannot be talked into emitting a coefficient by how the generator is invoked, and a
guard test on that side asserts the module names neither `KeySchema` nor `ChoiceItem`.

On this side, `_LAMINAR_MODELS`'s five plain `ChoiceItem`s became `_model(...)` calls like
the RAS/LES selectors, their `fallback` blurbs deleted; `_model()` gained an optional
`note`/`deprecated_since` so the two generali[sz]edNewtonian entries keep FoDE's own
fork-divergence caveat — which is *appended* to upstream's note, not substituted for it,
because it is a fact about the pair of forks that neither header states. Every
`supported_in` tag is unchanged: those are FoDE's measurement, and
`test_laminar_models_match_the_measured_table` still checks them against a table written
independently of the module. `test_no_laminar_model_is_covered_by_foamlore` is now
`test_every_laminar_model_is_covered_by_foamlore` — the same tripwire read the other way,
plus an assertion that the two prose tables stay disjoint — and a new
`test_laminar_notes_cite_only_where_upstream_does` pins which four of the seven carry a
`Reference:` note (`Maxwell`, `Giesekus`, `PTT`, `lambdaThixotropic`) and which three must
not (`Stokes` and both generali[sz]edNewtonian spellings), so no paper can be invented for
a class whose header cites none.

One wart worth knowing: `lambdaThixotropic`'s Description is the only quoted string in any
generated module that still carries Doxygen formula markup — it reads "…the structural
parameter \f$ \lambda \f$:". foamlore's `demarkup()` is deliberately narrow (`\c` and the
verbatim fences, nothing else) so that an unhandled directive survives visibly instead of
being silently mangled, and widening it is a store-wide re-extraction rather than a change
to this wiring.

Three findings from the extraction, worth knowing before touching
`turbulence_structure.py`'s laminar entries again — full detail in foamlore's
`fode-schemas/SPEC_RESPONSE.md`, section "12 (yours)":

- **`modes` changes syntactic category at Foundation 14** — a list through
  v13, a dictionary from v14 — and the v13 form is not silently ignored on
  v14, it is a fatal error (already reflected in FoDE's `modes` description
  as of the item-13 delivery audit, 2026-09-04).
- **`nuM` becomes per-mode at Foundation 14**: with `modes` present, each mode
  sub-dictionary must carry its own `nuM`; a top-level flat one is *ignored
  with a warning*, not an error.
- **No key in this family ever uses `getOrDefault`/`lookupOrDefault`** except
  `sigmay` (default 0, guarded by `found("sigmay")`), `residualAlpha` (default
  `1e-6`) and `modes` itself. Any other laminar key carrying a `default=` is
  wrong.


## 13. The nested generalizedNewtonian/generalisedNewtonian viscosity models — already measured, FoDE never answered the wiring question (2026-09-04, corrected 2026-09-04)

Found while closing out item 12's sibling task — the laminar stress models'
own coefficient dictionaries. `laminar { model generalizedNewtonian; }` (or
`generalisedNewtonian`) reads a further nested `viscosityModel` selector, whose
six shared choices (`BirdCarreau`, `Casson`, `CrossPowerLaw`, `HerschelBulkley`,
`powerLaw`, `strainRateFunction`, plus Foundation-only `Newtonian`) FoDE now
offers correctly. Their own coefficients are a different matter.

### The mistake this corrects

An implementation pass assumed these six classes were the *same* ones already
covered by `constant/transportProperties`'s identically-named `viscosityModel`
selector (`_transport.py`) — same name, same family, so surely the same
coefficients, reachable by pointing at that existing schema. That assumption
shipped in a commit message, three code comments and two RELEASE_NOTES entries
before a review caught it.

It is wrong on two independent grounds:

1. **The registry is file-scoped.** `_transport.py` declares
   `TARGET_FILES = ("transportProperties", "physicalProperties")`; nothing
   registered there is ever reachable from `constant/turbulenceProperties` or
   `constant/momentumTransport`, whatever the key names have in common. So the
   "reuse" would not even resolve — a coverage gap, not a leak, but also not
   what "already documented" claimed.
2. **Even if it resolved, it would be wrong for some of the six.** These are
   independently implemented C++ classes under different source directories,
   not one class read from two files, and three of the six do not share a
   coefficient set with their `transportProperties` namesake — though the
   other two turn out to be identical, corrected below:

   | model | transportProperties (legacy) | OpenCFD nested | Foundation nested |
   |---|---|---|---|
   | `BirdCarreau` | `nu0, nuInf, k, n, a` | `nuInf, k, n, a` (no `nu0`) | `nuInf, k, tauStar, n, a` (a fifth OpenCFD lacks) |
   | `HerschelBulkley` | — | `n, tau0` | `n, tau0, k` (Foundation adds `k`) |
   | `powerLaw` | — | `n, nuMin, nuMax` | `k, n, nuMin, nuMax` (Foundation adds `k`) |
   | `Casson` | — | `m, tau0, nuMin, nuMax` | `m, tau0, nuMin, nuMax` — **identical** |
   | `CrossPowerLaw` | — | `nuInf, m, n, tauStar` | `nuInf, m, tauStar, n` — **identical** |

   **Correction (2026-09-04):** this table originally claimed `HerschelBulkley`
   swaps `tau0` for `k` and that `Casson` drops `tau0` on Foundation — both
   wrong, from a hand grep (`grep -n "dimensionedScalar [a-zA-Z]*_;"`) whose
   character class silently excludes any identifier containing a digit,
   dropping `tau0_` from what it matched. Foundation's `HerschelBulkley`
   *adds* `k` alongside the shared `n, tau0`, and `Casson` is identical
   between forks. Re-verified against the shipped, vendored schema (a
   registry probe, not a second grep) rather than against source directly —
   `foamlore`'s own extraction never had this bug; only this document's
   evidence table did. `BirdCarreau`, `HerschelBulkley` and `powerLaw` still
   diverge, which remains enough to make the original "reuse
   `transportProperties`" claim wrong. Reusing that schema for the nested
   classes would have reported `nu0` as a valid `BirdCarreau` coefficient on
   both forks' momentumTransport-nested class, where neither actually reads
   it — the same class of bug item 12's own report caught for
   `lambdaThixotropic`/`CrossPowerLaw`, on a second axis.

Measured directly against source (`.H` member lists plus the `.C`
constructor/`read()` calls that pull each name from the coeffDict), not
assumed from the shared name. Currently only OpenCFD v2606 and Foundation-14
have been checked this way; the divergence is real but the *exact* per-release
extent (did any of these coefficients change shape across the measured span,
the way Maxwell/Giesekus/PTT gained multi-mode support at Foundation v8?) is
not yet swept across all nineteen checkouts.

### Correction: this was never an ask to make — it already landed on foamlore's side

The paragraphs above were written assuming the fact store needed extending.
It doesn't. `facts/store/generalisedNewtonian/` in the foamlore repo already
holds 119 derived JSONs — all six shared classes (`BirdCarreau`, `Casson`,
`CrossPowerLaw`, `HerschelBulkley`, `powerLaw`, `strainRateFunction`) times up
to nineteen checkouts, registered as their own `Family` in
`facts/tools/families.py`. `facts/tools/generate_transport_schemas.py`
already has a generator ready: two `Target` rows sit commented out —

```python
# Target("momentumTransport", "momentum_transport_viscosity",
#        "generalisedNewtonian", tuple(f"foundation-{n}" for n in range(8, 15))),
# Target("turbulenceProperties", "turbulence_properties_viscosity",
#        "generalisedNewtonian", OPENCFD_ALL + ("foundation-7",)),
```

foamlore raised this back on 2026-08-15, in *their* `fode-schemas/SPEC_RESPONSE.md`
item 12 (an independent numbering from this document's — a coincidence, not
the same item): "Nothing is blocked on the answer. ... Whichever you pick
costs a table row and a regeneration, not a re-derive." They offered FoDE
three wiring options (a second thin module per file, like the two rows above;
a per-key target filter in `_build_file_key_schemas`; or folding into the
turbulence generator's output) and left the choice to FoDE, since it is a
question about this repo's own registry. Nobody on the FoDE side answered it
— which is how this document came to independently re-derive the same
divergence table foamlore had already measured, and to mistake "unwired" for
"unmeasured."

**Decision (2026-09-04): the first option.** A second thin module per file,
matching the existing `turbulence_properties.py`/`momentum_transport.py`
pattern exactly — cheapest, and foamlore had already named the modules for it.
The measured key sets are disjoint today (`nu0`, `nuInf`, `tauStar`, `k`, `m`,
`n`, `nuMin`, `nuMax`, `tau0`, `function` vs. the turbulence coefficients), and
rather than build the heavier per-key target filter against a collision that
has not happened, FoDE will add a test asserting the two module's key sets
stay disjoint from every other module registered against the same
`TARGET_FILE` — so a real collision fails loudly at generation-check time
instead of silently mis-resolving, and the heavier fix stays available if that
test ever trips.

**The actual remaining task, entirely on the foamlore side:** uncomment the
two `Target` rows above, regenerate, and vendor
`momentum_transport_viscosity.py` / `turbulence_properties_viscosity.py` into
FoDE `schemas/` the way `turbulence_properties.py`/`momentum_transport.py`
already are. `strainRateFunction` reads a nested `Function1<scalar>` rather
than a fixed coefficient set and may need different handling in the
generator — flagged for that pass, not resolved here.

### Shipped (2026-09-04): what "uncomment and regenerate" actually needed

foamlore did not do the literal ask. Running exactly "uncomment the two
`Target` rows" would have shipped wrong schemas three ways, all found before
vendoring:

1. **One shared module per family, not one overall.** `_MODELS`/`_COEFFS` key
   by bare model name; feeding both families into one module unions their
   coefficients, so `BirdCarreauCoeffs` would have carried both `nu0`
   (legacy-only) and `tauStar` (nested-Foundation-only) on every target file —
   the exact bug this item opens by describing, reached from the generator
   side. Fixed with a shared `_generalised_newtonian.py`, mirroring how the
   store already namespaces the family. Nine generated modules now, not six.
2. **A parser bug dropped a required key on three releases.** Foundation 12
   inserted dimension arguments into `Function1<scalar>::New(...)`, which a
   positional parser misread, silently dropping `strainRateFunction`'s
   `function` key for foundation-12/13/14 and would have shipped
   `supported_in=('Foundation v8-v11',)` — unavailable on releases that
   require it. Fixed; confirmed via registry probe at `Foundation v8-v14`.
3. **`container_of` didn't know Foundation 14's accessor**, so every
   Foundation-14 nested model recorded no container and would have answered
   only to a flat write — it never reached output only because the generator
   happened to source the container name from whichever checkout sorts last.

**And FoDE's own "the key sets are disjoint today" decision was not quite
right**, which the disjointness-guard test above was meant to catch but a
collision beat it to landing: `viscosityModel` itself collided, since
`turbulence_structure.py` hand-writes it and the generator would have loaded
second and silently won. foamlore suppressed emission of that one key at the
generator (`Target.emit_selector` / `_transport.py`'s `_SELECTOR_FILES`)
rather than let it override FoDE's hand-written entry — confirmed by registry
probe: `viscosityModel` still resolves to the hand-written 7-choice entry on
both target files.

Two measured findings were reported rather than applied, and are now
resolved:

- **`Newtonian`'s tag over-claimed by three releases.** Tagged
  `FOUNDATION_SERIES` (v7-v14); the nested `Newtonian` class first registers
  at foundation-10 (confirmed absent from foundation-7/8/9's directory
  listing). Fixed to `FOUNDATION_V10_V14`.
- **`viscosityModel`'s `supported_in=BOTH` doesn't distinguish which file
  each Foundation version actually reads it from** (v7 only for
  `turbulenceProperties`, v8+ for `momentumTransport`). Left as is: every
  other entry in this single shared module has the identical imprecision —
  `RAS.model`'s choices are tagged the same coarse way — so narrowing just
  this one key would be an inconsistency, not a fix, given the module's
  one-table-serves-both-files architecture.

Also fixed while auditing the delivery: `modes` changes syntactic category at
Foundation 14 (a list through v13, a dictionary from v14) and the old form is
not silently ignored there — it is a fatal error (`subOrEmptyDict` calling
`entry::dict()` on what is really a primitive/list entry). FoDE's `modes`
description now says so; it previously described only the list form.

`turbulence_structure.py`'s `viscosityModel` entry now names the six choices
*and* their coefficients resolve — from the sibling generated
`turbulence_properties_viscosity.py` / `momentum_transport_viscosity.py`, not
from this hand-written module. See the code comment above that `KeySchema`
and `DEVELOPER.md`'s matching paragraph.
