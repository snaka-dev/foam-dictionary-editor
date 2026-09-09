# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Structural keys for `constant/turbulenceProperties` and `constant/momentumTransport`.

Foundation renamed the file to `momentumTransport` in OpenFOAM 8; OpenCFD kept
`turbulenceProperties`. The contents are the same shape, so this module targets
both names through `TARGET_FILES`.

This covers the *structure* — `simulationType`, the `RAS`/`LES` dictionaries,
the model selector, and the LES delta models. The per-model coefficients come
from the generated `turbulence_properties` / `momentum_transport` modules, which
are vendored from foamlore and must not be edited here; the registry merges all
of them into one table per file.

The model *names* are structural and stay here, but what each one is is quoted
from its own OpenFOAM header — through `_turbulence_coeffs.MODEL_DOCS` for the
RAS/LES models, and `_laminar_models.MODEL_DOCS` for the laminar stress ones.
Plain imports, not registrations: neither module declares a `TARGET_FILE`, so
`schemas/builtin.py`'s module order does not come into it. Without this the
extracted description would only ever be reachable through `<Model>Coeffs`, a
key that exists only in the cases that override a default — which most do not.

Two generated tables rather than one because the laminar half is prose *only*.
That family's coefficient keys (`laminar.MaxwellCoeffs`, `nuM`, `lambda`,
`modes`) are hand-written below and the generated modules load *second*, so
foamlore emits no `KeySchema` for it at all — `docs/foamlore-schema-spec.md`
item 5's boundary, kept by putting the prose in a module that has nothing else
in it.

Model names are the *run-time selection table* — every name passed to
`makeRASModel`/`makeLESModel`/`makeLaminarModel`, swept across all nineteen
foamlore checkouts — so entries that exist in only one fork, or that arrived
part-way through a series, are tagged accordingly.

Deliberately not a directory listing, which is what this once was and what got
the DES models wrong: OpenCFD keeps them in a sibling
`src/TurbulenceModels/turbulenceModels/DES/` rather than under `LES/`, so
listing `LES/` alone reported four models as Foundation-only that both forks
register. A name absent from the selection table cannot be constructed whatever
the source tree holds, which is the question a choice list is answering.
"""
from __future__ import annotations

from schemas._base import (
    BOTH,
    FOUNDATION_SERIES,
    FOUNDATION_V7_V8,
    FOUNDATION_V8_V14,
    FOUNDATION_V9_V14,
    FOUNDATION_V10_V14,
    FOUNDATION_V11_V14,
    FOUNDATION_V12_V14,
    OPENCFD_SERIES,
    OPENCFD_V2206_V2606,
    OPENCFD_V2212_V2606,
    OPENCFD_V2606,
    ChoiceItem,
    KeySchema,
    entry,
)
from schemas._delta_models import MODEL_DOCS as DELTA_MODEL_DOCS
from schemas._laminar_models import MODEL_DOCS as LAMINAR_MODEL_DOCS
from schemas._turbulence_coeffs import MODEL_DOCS

TARGET_FILES = ("turbulenceProperties", "momentumTransport")

# These dictionaries have structural keys of their own, but OpenFOAM's
# `optionalSubDict` idiom also lets a model's coefficients be written directly
# into them — `RAS { Cmu 0.09; }` rather than `RAS { kEpsilonCoeffs { Cmu … } }`.
# Declaring them open keeps the flat coefficient fallback working inside them;
# the `<model>Coeffs` dictionaries stay closed, so one model's coefficient is
# never explained by another's.
OPEN_NAMESPACES = ("RAS", "LES", "laminar")

_OC = (OPENCFD_SERIES,)
_FD = (FOUNDATION_SERIES,)


#: All three generated prose tables under one lookup. The name sets are
#: mutually disjoint — 33 RAS/LES model classes, seven laminar stress ones and
#: nine LES delta ones — and live in separate modules only because the laminar
#: and delta halves emit no coefficient keys, so a table they do not have
#: cannot win a key `turbulence_structure` owns. A test asserts the
#: disjointness, so the merged lookup cannot come to depend on write order.
_MODEL_PROSE = {**MODEL_DOCS, **LAMINAR_MODEL_DOCS, **DELTA_MODEL_DOCS}


def _model(name: str, supported_in: tuple[str, ...] = BOTH,
           fallback: str = "", note: str = "",
           deprecated_since: str = "", description: str = "") -> ChoiceItem:
    """One entry of a model selector, in OpenFOAM's own words where they exist.

    The generated tables carry the summary from each model's header and the
    paper it cites, extracted and quote-verified by foamlore; between them they
    cover every model class named below. `fallback` is for a choice that names
    no model class — `laminar`, which is the absence of one — so nothing
    upstream describes it.

    `note` is FoDE's own, and is *appended* to upstream's rather than replacing
    it. The two generali[sz]edNewtonian spellings need one: that they are a
    fork rename with no compatible spelling either way is a fact about the pair
    of forks, which neither class's header states and no extraction can reach.

    `description` *replaces* upstream's, and is the one case where that is
    right: where the two forks document the same class differently and one of
    them is wrong. The extraction reports a single description per model, so it
    reports whichever fork it read; which of the two is correct is a judgement
    about the pair, and judgements are this module's half of the boundary.
    Only `vanDriest` needs it today, and the reason is recorded there.
    """
    upstream_description, upstream_note = _MODEL_PROSE.get(name, ("", ""))
    description = description or upstream_description
    return ChoiceItem(
        name, description or fallback, supported_in,
        note=" ".join(x for x in (upstream_note, note) if x),
        deprecated_since=deprecated_since,
    )


# A narrow span here means the model *arrived* in that release and has been
# there since — not that measurement stopped early. `_base.py` draws the same
# distinction for keys; a whole-series tag on a model that shipped later tells
# a user on an older release that a name they cannot construct is available.
_RAS_MODELS = (
    _model("kEpsilon"),
    _model("kOmegaSST"),
    _model("SpalartAllmaras"),
    _model("realizableKE"),
    _model("RNGkEpsilon"),
    _model("LaunderSharmaKE"),
    _model("kOmega"),
    _model("kOmegaSSTLM"),
    _model("kOmegaSSTSAS"),
    _model("LRR"),
    _model("SSG"),
    _model("buoyantKEpsilon", BOTH,
           "kEpsilon with a buoyancy production term in the k equation."),
    _model("EBRSM", (OPENCFD_V2206_V2606,)),
    _model("GEKO", (OPENCFD_V2606,)),
    _model("kEpsilonPhitF", _OC),
    _model("kOmega2006", (FOUNDATION_V9_V14,)),
    _model("v2f", _FD),
    _model("kEpsilonLopesdaCosta", _FD,
           "kEpsilon with the Lopes da Costa porosity/canopy source terms."),
    _model("laminar", BOTH, "No turbulence model; laminar stress only."),
)

_LES_MODELS = (
    _model("kEqn"),
    _model("Smagorinsky"),
    _model("WALE"),
    _model("dynamicKEqn"),
    _model("dynamicLagrangian"),
    _model("DeardorffDiffStress"),
    _model("sigma", (OPENCFD_V2212_V2606,)),
    # The DES family. OpenCFD registers these through `makeLESModel` from a
    # sibling `DES/` directory rather than `LES/`, which is why reading the
    # directory listing once marked the first four Foundation-only — they are
    # in every release of both forks, and OpenCFD's own tutorials select them.
    _model("SpalartAllmarasDES"),
    _model("SpalartAllmarasDDES"),
    _model("SpalartAllmarasIDDES"),
    _model("kOmegaSSTDES"),
    _model("kOmegaSSTDDES", _OC),
    _model("kOmegaSSTIDDES", _OC),
)

# Built with `_model()` like the RAS/LES and laminar selectors: foamlore
# measured this family into `facts/store/delta/` and exports its headers as
# `_delta_models.MODEL_DOCS`, so the blurbs that used to be hand-written here
# are OpenFOAM's own words. The `supported_in` tags stay ours -- they are the
# run-time selection table, which is a structural fact -- and so does the
# choice list itself, which is why the `maxDeltaxyzCubeRoot` correction was
# ours to make.
_DELTA_MODELS = (
    _model("cubeRootVol"),
    # The one description this module overrides rather than quotes. OpenCFD's
    # vanDriestDelta.H repeats cubeRootVolDelta's summary verbatim -- "Simple
    # cube-root of cell volume delta used in incompressible LES models" -- in
    # every release from v2106 to v2606, describing a different model. Every
    # Foundation release from v7 carries the correct text, used here. The
    # extraction reports one description per model and reported OpenCFD's;
    # choosing between two forks' prose is a judgement, which is this module's
    # half of the boundary rather than the generator's.
    _model("vanDriest",
           description="Apply van Driest damping function to the specified "
                       "geometric delta to improve near-wall behaviour of LES "
                       "SGS models.",
           note="OpenCFD's header for this class duplicates cubeRootVol's "
                "description; the text here is Foundation's, which is the "
                "accurate one."),
    _model("smooth"),
    _model("maxDeltaxyz"),
    _model("Prandtl"),
    _model("IDDESDelta"),
    # The run-time type, not the class or its directory, both of which are
    # `maxDeltaxyzCubeRootLESDelta` -- the one entry in this list that had taken
    # its name from `ls` rather than from `TypeName(...)`. Every other name here
    # is already the registered type, including the four whose class differs
    # (`cubeRootVolDelta`, `PrandtlDelta`, `smoothDelta`, `vanDriestDelta`), so
    # the suffix is not strippable by rule: `IDDESDelta` and `SLADelta` register
    # under their full class name. Found by foamlore, 2026-09-06.
    _model("maxDeltaxyzCubeRoot", _OC),
    _model("DeltaOmegaTilde", _OC),
    _model("SLADelta", _OC),
)

# The laminar stress models, the third selector family. Built with `_model()`
# like the other two: foamlore measured this family into `facts/store/laminar/`
# and now exports its headers as `_laminar_models.MODEL_DOCS`, so the blurbs
# that used to be hand-written here are OpenFOAM's own words
# (`docs/foamlore-schema-spec.md` item 12). The `supported_in` tags stay ours —
# they are the run-time selection table, which is a structural fact.
#
# Module-level and shared, for the same reason `_RAS_MODELS` is: both forks
# read `model` with `laminarModel` as a backwards-compatible spelling (OpenCFD
# `getCompat("model", {{"laminarModel", -2006}})`, Foundation
# `lookupBackwardsCompatible({"model", "laminarModel"})`), so the two keys are
# one selector and must offer one list.
#
# The two generalised-Newtonian spellings are different classes in different
# forks, not a typo: OpenCFD has only ever registered the `z` form, Foundation
# renamed it to the `s` form at v9, and neither declares a compatible spelling
# for the other's. Each is therefore a hard construction error on the opposite
# fork, which is why they are two choices rather than one — see
# `_base.py`'s `FOUNDATION_V7_V8`. Their `note`s say so, and are FoDE's own:
# upstream describes each class without mentioning that the other fork's
# spelling exists, so the caveat is appended to the extracted prose rather
# than replacing it.
_LAMINAR_MODELS = (
    _model("Stokes"),
    _model("Maxwell"),
    _model("generalizedNewtonian", (FOUNDATION_V7_V8, OPENCFD_SERIES),
        note="OpenCFD's spelling, and the only one it registers. Foundation "
             "renamed the class to 'generalisedNewtonian' at v9 and declares "
             "no compatible spelling, so this name cannot be constructed on "
             "Foundation v9 and later.",
        deprecated_since="Foundation v9"),
    _model("generalisedNewtonian", (FOUNDATION_V9_V14,),
        note="Foundation's spelling from v9. OpenCFD has only ever registered "
             "'generalizedNewtonian', so this name cannot be constructed "
             "there."),
    _model("lambdaThixotropic", (FOUNDATION_V9_V14,)),
    _model("Giesekus", (FOUNDATION_SERIES,)),
    _model("PTT", (FOUNDATION_V8_V14,)),
)


# `turbulence` and `printCoeffs` sit in whichever of RAS/LES is active.
# Deliberately not `schemas._base.SWITCH_CHOICES`: the shared tuple leads with
# yes/no, but the tutorials spell these two keys `turbulence on;`, so on/off
# comes first here. The Detail panel shows the choices in this order.
_BOOL_CHOICES = (
    ChoiceItem("on", "Enabled.", BOTH),
    ChoiceItem("off", "Disabled.", BOTH),
    ChoiceItem("yes", "Enabled.", BOTH),
    ChoiceItem("no", "Disabled.", BOTH),
    ChoiceItem("true", "Enabled.", BOTH),
    ChoiceItem("false", "Disabled.", BOTH),
)

_SHARED = {
    "turbulence": entry(
        "turbulence", "Turbulence",
        "Switches the turbulence model on. With it off the model is constructed "
        "but contributes nothing, leaving a laminar solution.",
        _BOOL_CHOICES,
    ),
    "printCoeffs": entry(
        "printCoeffs", "Print Coefficients",
        "Prints the model's coefficients to the log at start-up — the quickest "
        "way to see which defaults are actually in force.",
        _BOOL_CHOICES,
    ),
}

#: Which of this module's two target files each version label can appear in.
#:
#: The two spellings are the same dictionary renamed at OpenFOAM 8, and they
#: are read by *disjoint* sets of releases: `constant/turbulenceProperties` by
#: Foundation v7 and every OpenCFD release, `constant/momentumTransport` by
#: Foundation v8-v14 and no OpenCFD release at all. A key whose entire
#: `supported_in` falls outside a file's readership cannot be written in that
#: file, and offering it there is `docs/foamlore-schema-spec.md` item 2's
#: hazard seen from the hand-written side -- the registry merges one table into
#: both names, so without this every key appears under both.
#:
#: Derived rather than annotated per key: `_restrict_to_files` below applies it
#: to the whole table, so a Foundation-v9+ key added later is restricted
#: without anyone remembering to mark it. The labels are listed rather than
#: parsed, because a label is an opaque display string and reading releases out
#: of its text would be a second, silent way of representing the same fact.
_LABEL_FILES: dict[str, tuple[str, ...]] = {
    # Foundation labels that include v7 reach both files; those starting at v8
    # or later reach momentumTransport only.
    FOUNDATION_SERIES:   TARGET_FILES,
    FOUNDATION_V7_V8:    TARGET_FILES,
    FOUNDATION_V8_V14:   ("momentumTransport",),
    FOUNDATION_V9_V14:   ("momentumTransport",),
    FOUNDATION_V10_V14:  ("momentumTransport",),
    FOUNDATION_V11_V14:  ("momentumTransport",),
    FOUNDATION_V12_V14:  ("momentumTransport",),
    # No OpenCFD release reads momentumTransport.
    OPENCFD_SERIES:      ("turbulenceProperties",),
    OPENCFD_V2206_V2606: ("turbulenceProperties",),
    OPENCFD_V2212_V2606: ("turbulenceProperties",),
    OPENCFD_V2606:       ("turbulenceProperties",),
}


def _files_for(supported_in: tuple[str, ...]) -> tuple[str, ...]:
    """The target files a key with these labels can be written in.

    The union across labels, not the intersection: a key supported on both
    Foundation v9+ and OpenCFD belongs in both files, in each case for a
    different fork's sake. An untagged key is unrestricted, and a label absent
    from `_LABEL_FILES` is treated the same way -- a missing entry must not
    silently hide a key, and the test below is what catches one instead.
    """
    if not supported_in:
        return TARGET_FILES
    files: set[str] = set()
    for label in supported_in:
        files.update(_LABEL_FILES.get(label, TARGET_FILES))
    return tuple(f for f in TARGET_FILES if f in files)


def _restrict_to_files(
        table: dict[str, KeySchema]) -> dict[str, KeySchema]:
    """Set `only_in_files` on every key whose labels do not reach both files."""
    import dataclasses
    out: dict[str, KeySchema] = {}
    for name, schema in table.items():
        files = _files_for(tuple(schema.supported_in or ()))
        out[name] = (schema if files == TARGET_FILES
                     else dataclasses.replace(schema, only_in_files=files))
    return out


SCHEMAS: dict[str, KeySchema] = {
    "simulationType": entry(
        "simulationType", "Simulation Type",
        "Which family of turbulence treatment the case uses. Selects which of "
        "the dictionaries below is read - or, with twoPhaseTransport, none of "
        "them.",
        (
            ChoiceItem("RAS", "Reynolds-averaged simulation; reads the RAS dictionary.", BOTH),
            ChoiceItem("LES", "Large-eddy simulation; reads the LES dictionary.", BOTH),
            ChoiceItem("laminar", "No turbulence modelling.", BOTH),
            ChoiceItem("twoPhaseTransport",
                "Each phase carries its own transport model, read by the "
                "two-phase interface solvers; this file then holds no further "
                "dictionary.", BOTH),
        ),
    ),

    # ── RAS ───────────────────────────────────────────────────────────────────
    "RAS": entry("RAS", "RAS Settings",
        "Settings for Reynolds-averaged simulation, read when simulationType is RAS."),
    "RAS.model": entry(
        "model", "RAS Model",
        "Which Reynolds-averaged model to use.",
        _RAS_MODELS,
        note="Both forks now read 'model'; 'RASModel' remains as a "
             "backward-compatible alias.",
    ),
    "RAS.RASModel": KeySchema(
        key="RASModel", label="RAS Model (former name)",
        description="Former name of the RAS 'model' selector, still accepted by "
                    "both forks and still the spelling in most tutorials.",
        supported_in=BOTH,
        status="renamed",
        use_instead="model",
        deprecated_since="v2006",
        choices=_RAS_MODELS,
    ),
    **{f"RAS.{k}": v for k, v in _SHARED.items()},

    # ── LES ───────────────────────────────────────────────────────────────────
    "LES": entry("LES", "LES Settings",
        "Settings for large-eddy simulation, read when simulationType is LES."),
    "LES.model": entry(
        "model", "LES Model",
        "Which sub-grid-scale model to use.",
        _LES_MODELS,
        note="Both forks now read 'model'; 'LESModel' remains as a "
             "backward-compatible alias.",
    ),
    "LES.LESModel": KeySchema(
        key="LESModel", label="LES Model (former name)",
        description="Former name of the LES 'model' selector, still accepted by "
                    "both forks and still the spelling in most tutorials.",
        supported_in=BOTH,
        status="renamed",
        use_instead="model",
        deprecated_since="v2006",
        choices=_LES_MODELS,
    ),
    **{f"LES.{k}": v for k, v in _SHARED.items()},
    "LES.delta": entry(
        "delta", "Delta Model",
        "How the sub-grid length scale is computed from the mesh. Each choice "
        "reads its own <name>Coeffs sub-dictionary.",
        _DELTA_MODELS,
    ),
    "LES.filter": entry(
        "filter", "Filter",
        "Filter used by the dynamic SGS models.",
        (
            ChoiceItem("simple", "Simple box filter.", BOTH),
            ChoiceItem("anisotropic", "Anisotropic filter.", BOTH),
            ChoiceItem("laplace", "Laplacian filter.", BOTH),
        ),
    ),
    # ── delta coefficient dictionaries ────────────────────────────────────────
    "LES.cubeRootVolCoeffs": entry("cubeRootVolCoeffs", "cubeRootVol Coefficients",
        "Coefficients for the cubeRootVol delta model."),
    "LES.vanDriestCoeffs": entry("vanDriestCoeffs", "vanDriest Coefficients",
        "Coefficients for the vanDriest delta model."),
    "LES.smoothCoeffs": entry("smoothCoeffs", "smooth Coefficients",
        "Coefficients for the smooth delta model."),
    "LES.maxDeltaxyzCoeffs": entry("maxDeltaxyzCoeffs", "maxDeltaxyz Coefficients",
        "Coefficients for the maxDeltaxyz delta model."),
    "LES.PrandtlCoeffs": entry("PrandtlCoeffs", "Prandtl Coefficients",
        "Coefficients for the Prandtl delta model."),
    "LES.IDDESDeltaCoeffs": entry("IDDESDeltaCoeffs", "IDDESDelta Coefficients",
        "Coefficients for the IDDES delta model."),

    "deltaCoeff": entry("deltaCoeff", "Delta Coefficient",
        "Scaling applied to the computed delta. Usually 1."),
    "maxDeltaRatio": entry("maxDeltaRatio", "Maximum Delta Ratio",
        "Largest permitted ratio of delta between neighbouring cells, used by "
        "the smooth delta model."),
    "Cdelta": entry("Cdelta", "Cdelta",
        "Delta coefficient of the Prandtl and van Driest delta models."),
    "Aplus": entry("Aplus", "A+",
        "Van Driest damping constant, normally 26."),
    "Cmu": entry("Cmu", "Cmu",
        "Cmu as used by the delta models when converting between length scales."),
    "kappa": entry("kappa", "von Karman Constant",
        "Von Karman constant, normally 0.41."),

    # Each delta model reads its own sub-dictionary, whose entries are the
    # scalars above; the wildcard keeps them answerable without repeating each
    # coefficient under every dictionary name.
    # ── laminar ───────────────────────────────────────────────────────────────
    "laminar": entry("laminar", "Laminar Settings",
        "Settings read when simulationType is laminar — the stress model used in "
        "place of a turbulence model."),
    "laminar.model": entry(
        "model", "Laminar Stress Model",
        "Which laminar stress model to use.",
        _LAMINAR_MODELS,
        note="Both forks now read 'model'; 'laminarModel' remains as a "
             "backward-compatible alias.",
    ),
    **{f"laminar.{k}": v for k, v in _SHARED.items()},
    "laminar.laminarModel": KeySchema(
        key="laminarModel", label="Laminar Model (former name)",
        description="Former name of the laminar 'model' selector, still "
                    "accepted by both forks.",
        supported_in=BOTH, status="renamed", use_instead="model",
        deprecated_since="v2006",
        choices=_LAMINAR_MODELS,
    ),

    # ── laminar coefficient dictionaries ────────────────────────────────────
    # Where a laminar model's coefficients live is fork-divergent in the same
    # way its own name can be: OpenCFD's laminarModel base looks up the
    # literal key "<Type>Coeffs" only (optionalSubDict, falling back to flat);
    # Foundation's tries the bare type name first, then "<Type>Coeffs", then
    # flat (dictionary::optionalTypeDict). So Foundation genuinely accepts a
    # third spelling OpenCFD does not, and the container name itself differs
    # by the model's own registered spelling — OpenCFD's is
    # "generalizedNewtonianCoeffs", Foundation's "generalisedNewtonianCoeffs".
    # Real tutorials write all three shapes; see the entries below.
    "laminar.MaxwellCoeffs": entry("MaxwellCoeffs", "Maxwell Coefficients",
        "Coefficients for the Maxwell viscoelastic stress model."),
    "laminar.Maxwell": entry("Maxwell", "Maxwell Coefficients (bare form)",
        "Coefficients for the Maxwell viscoelastic stress model, written "
        "directly under this name rather than 'MaxwellCoeffs'.",
        supported_in=(FOUNDATION_SERIES,)),
    "laminar.GiesekusCoeffs": entry("GiesekusCoeffs", "Giesekus Coefficients",
        "Coefficients for the Giesekus viscoelastic stress model.",
        supported_in=(FOUNDATION_SERIES,)),
    "laminar.Giesekus": entry("Giesekus", "Giesekus Coefficients (bare form)",
        "Coefficients for the Giesekus viscoelastic stress model, written "
        "directly under this name rather than 'GiesekusCoeffs'.",
        supported_in=(FOUNDATION_SERIES,)),
    "laminar.PTTCoeffs": entry("PTTCoeffs", "PTT Coefficients",
        "Coefficients for the Phan-Thien-Tanner viscoelastic stress model.",
        supported_in=(FOUNDATION_V8_V14,)),
    "laminar.PTT": entry("PTT", "PTT Coefficients (bare form)",
        "Coefficients for the Phan-Thien-Tanner viscoelastic stress model, "
        "written directly under this name rather than 'PTTCoeffs'.",
        supported_in=(FOUNDATION_V8_V14,)),
    "laminar.lambdaThixotropicCoeffs": entry(
        "lambdaThixotropicCoeffs", "lambdaThixotropic Coefficients",
        "Coefficients for the thixotropic viscosity model, driven by a "
        "transported structure parameter.",
        supported_in=(FOUNDATION_V9_V14,)),
    "laminar.lambdaThixotropic": entry(
        "lambdaThixotropic", "lambdaThixotropic Coefficients (bare form)",
        "Coefficients for the thixotropic viscosity model, written directly "
        "under this name rather than 'lambdaThixotropicCoeffs'.",
        supported_in=(FOUNDATION_V9_V14,)),
    # `viscosityModel`'s own choices each read their own coefficients one
    # level deeper (`BirdCarreauCoeffs`, `CasonCoeffs`, ...) which are NOT
    # covered here — see the note on `viscosityModel` below for why that is
    # deliberate rather than an oversight.
    "laminar.generalizedNewtonianCoeffs": entry(
        "generalizedNewtonianCoeffs", "generalizedNewtonian Coefficients",
        "Selects and configures the nested viscosity model (see "
        "'viscosityModel' below). OpenCFD's spelling of the container name.",
        supported_in=(OPENCFD_SERIES,)),
    "laminar.generalisedNewtonianCoeffs": entry(
        "generalisedNewtonianCoeffs", "generalisedNewtonian Coefficients",
        "Selects and configures the nested viscosity model (see "
        "'viscosityModel' below). Foundation's spelling of the container name.",
        supported_in=(FOUNDATION_V9_V14,)),
    "laminar.generalisedNewtonian": entry(
        "generalisedNewtonian", "generalisedNewtonian Coefficients (bare form)",
        "Selects and configures the nested viscosity model (see "
        "'viscosityModel' below), written directly under this name rather "
        "than 'generalisedNewtonianCoeffs'.",
        supported_in=(FOUNDATION_V9_V14,)),

    # These coefficients are plain (unqualified) rather than qualified under
    # their container names above, the same choice the RAS/LES delta
    # coefficients make: none of the container names above gains a qualified
    # child, so they never become closed namespaces, and a plain entry
    # resolves through 'laminar's open-namespace fallback whichever of the
    # three spellings — bare, Coeffs, or flat inside laminar{} itself — a
    # case actually uses.
    "nuM": KeySchema(
        key="nuM", label="Mode Viscosity (nuM)",
        description="Added viscosity of this viscoelastic mode. Foundation's "
                    "Maxwell/Giesekus/PTT read one nuM per entry of 'modes' "
                    "when that list is given, or a single nuM otherwise.",
        supported_in=BOTH, required=True),
    "lambda": KeySchema(
        key="lambda", label="Relaxation Time (lambda)",
        description="Relaxation time of this viscoelastic mode. Same "
                    "per-mode behaviour as nuM.",
        supported_in=BOTH, required=True),
    # Measured (foamlore SPEC_RESPONSE item 12/13, 2026-09-04): 'modes'
    # changes syntactic category at Foundation 14, and the old form does not
    # degrade gracefully -- it aborts. v8-v13 read it as a LIST via
    # `dict.lookup("modes")`: `modes ( { lambda 0.01; } { lambda 0.04; } );`.
    # v14 reads it as a DICTIONARY via `dict.subOrEmptyDict("modes")`:
    # `modes { mode0 { lambda 0.01; } mode1 { lambda 0.04; } }`. Feeding v14
    # the v13 list form is not silently accepted or ignored -- `subOrEmptyDict`
    # finds the entry, calls `entry::dict()` on what is really a primitive
    # (list) entry, and that is a FatalError, not a warning. Foundation 14's
    # own bundled tutorial (incompressibleFluid/planarContraction) still
    # documents the list form in its comments, which is how this was found.
    "modes": entry("modes", "Modes",
        "A list of named relaxation modes (v8-v13: "
        "'modes ( { lambda 0.01; } { lambda 0.04; } );'), or a dictionary of "
        "them (v14: 'modes { mode0 { lambda 0.01; } mode1 { ... } }'). Each "
        "mode supplies its own nuM/lambda (and alphaG or epsilon, for "
        "Giesekus or PTT). When given, read in preference to a single flat "
        "nuM/lambda pair. The v13 list form is not read on v14 -- it is a "
        "fatal error there, not a silent fallback -- so a case carried "
        "forward across that boundary needs the dictionary form.",
        supported_in=(FOUNDATION_V8_V14,)),
    "alphaG": KeySchema(
        key="alphaG", label="Mobility Factor (alphaG)",
        description="Deformation-dependent mobility factor of the Giesekus "
                    "model's extra stress term.",
        supported_in=(FOUNDATION_SERIES,), required=True),
    "epsilon": KeySchema(
        key="epsilon", label="Extensibility Parameter (epsilon)",
        description="Extensibility parameter of the PTT model's extra "
                    "stress term.",
        supported_in=(FOUNDATION_V8_V14,), required=True),
    # Qualified rather than flat, unlike nuM/lambda above: "nu0"/"nuInf" (and
    # the bare letters "a"-"d") are generic enough that BirdCarreau and
    # CrossPowerLaw use the same names for a different physical quantity, one
    # step away inside generalizedNewtonian's own nested viscosity model. A
    # flat entry would leak lambdaThixotropic's description into that
    # context — caught by resolving a real Foundation tutorial that uses
    # CrossPowerLaw's nuInf/m/n and finding lambdaThixotropic's blurb
    # answering for the first of them.
    **{
        f"{container}.{key}": schema
        for container in ("lambdaThixotropicCoeffs", "lambdaThixotropic")
        for key, schema in (
            ("a", KeySchema(
                key="a", label="Structure Build-Up Rate (a)",
                description="Rate coefficient in lambdaThixotropic's "
                            "structural parameter evolution equation.",
                supported_in=(FOUNDATION_V9_V14,), required=True)),
            ("b", KeySchema(
                key="b", label="Structure Build-Up Exponent (b)",
                description="Exponent in lambdaThixotropic's structural "
                            "parameter evolution equation.",
                supported_in=(FOUNDATION_V9_V14,), required=True)),
            ("c", KeySchema(
                key="c", label="Structure Breakdown Rate (c)",
                description="Rate coefficient in lambdaThixotropic's "
                            "structural parameter evolution equation.",
                supported_in=(FOUNDATION_V9_V14,), required=True)),
            ("d", KeySchema(
                key="d", label="Structure Breakdown Exponent (d)",
                description="Shear-rate exponent in lambdaThixotropic's "
                            "structural parameter evolution equation.",
                supported_in=(FOUNDATION_V9_V14,), required=True)),
            ("nu0", KeySchema(
                key="nu0", label="Viscosity at Full Structure (nu0)",
                description="lambdaThixotropic's limiting viscosity when the "
                            "structural parameter is 1 (fully built up).",
                supported_in=(FOUNDATION_V9_V14,), required=True)),
            ("nuInf", KeySchema(
                key="nuInf", label="Viscosity at Zero Structure (nuInf)",
                description="lambdaThixotropic's limiting viscosity when the "
                            "structural parameter is 0 (fully broken down).",
                supported_in=(FOUNDATION_V9_V14,), required=True)),
            ("sigmay", KeySchema(
                key="sigmay", label="Yield Stress (sigmay)",
                description="Optional Bingham-plastic yield stress for "
                            "lambdaThixotropic. Its presence switches the "
                            "model into Bingham-plastic handling; omitting "
                            "it leaves that handling off.",
                supported_in=(FOUNDATION_V11_V14,))),
            ("residualAlpha", KeySchema(
                key="residualAlpha", label="Residual Alpha",
                description="Small structural-parameter floor "
                            "lambdaThixotropic clips to, avoiding a "
                            "division by a fully broken-down structure.",
                supported_in=(FOUNDATION_V12_V14,), default="1e-6")),
        )
    },
    # This selector's own choices are a genuinely separate class hierarchy
    # from constant/transportProperties's identically-named one (legacy
    # nonNewtonianIcoFoam-style solvers): two independent C++ implementations
    # under different source directories, not one class read from two files.
    # They share a name and a family resemblance, not always a coefficient
    # set. Measured directly against source (docs/foamlore-schema-spec.md
    # item 13, shipped 2026-09-04): three of the six diverge from their
    # transportProperties namesake, each by the nested class carrying one
    # coefficient the legacy one lacks or vice versa —
    #   BirdCarreau: nested has no nu0, gains tauStar on Foundation only
    #   HerschelBulkley: nested gains k on Foundation only
    #   powerLaw: nested gains k on Foundation only
    # — while Casson and CrossPowerLaw are identical to their legacy
    # namesake on every coefficient. (An earlier hand-measurement pass
    # claimed Casson diverges too, from a grep whose character class
    # silently excluded any identifier containing a digit, dropping
    # `tau0_` from what it saw. Corrected here and in
    # docs/foamlore-schema-spec.md; the shipped schema was never wrong,
    # only that document's evidence table was.)
    #
    # Each choice's own coefficients now resolve — not from this module,
    # but from the sibling generated schemas/turbulence_properties_viscosity.py
    # / schemas/momentum_transport_viscosity.py over a shared
    # schemas/_generalised_newtonian.py, registered in schemas/builtin.py.
    # This selector's choice list and supported_in tags stay hand-owned here
    # (item 5's boundary); the generator is explicitly told not to emit
    # `viscosityModel` itself (schemas/_transport.py's `_SELECTOR_FILES`),
    # since it collided with this entry when first tried.
    "viscosityModel": KeySchema(
        key="viscosityModel", label="Viscosity Model",
        description="Which nested viscosity model the generalizedNewtonian/"
                    "generalisedNewtonian laminar stress model uses. Each "
                    "choice reads its own coefficients directly alongside "
                    "this key, in its own <Model>Coeffs sub-dictionary.",
        supported_in=BOTH, required=True,
        choices=(
            ChoiceItem("BirdCarreau", "Bird-Carreau shear-thinning model.", BOTH),
            ChoiceItem("Casson", "Casson yield-stress model.", BOTH),
            ChoiceItem("CrossPowerLaw", "Cross power-law shear-thinning model.", BOTH),
            ChoiceItem("HerschelBulkley", "Herschel-Bulkley yield-stress model.", BOTH),
            ChoiceItem("powerLaw", "Simple power-law model.", BOTH),
            ChoiceItem("strainRateFunction", "Run-time selected strain-rate "
                       "function.", BOTH),
            # Measured (foamlore SPEC_RESPONSE item 12/13, 2026-09-04): the
            # nested Newtonian class is absent from foundation-7/8/9 and first
            # registers at foundation-10 -- FOUNDATION_SERIES over-claimed it
            # by three releases, the same direction of error as GEKO/sigma/
            # EBRSM/kOmega2006 above.
            ChoiceItem("Newtonian", "Uniform constant viscosity — the trivial "
                       "case, included so 'viscosityModel' need not change "
                       "when comparing against Stokes.", (FOUNDATION_V10_V14,)),
        ),
    ),
    # OpenCFD only, and the two values are the ones the reader accepts -- not
    # the incompressible/compressible pair this entry used to offer, which
    # OpenFOAM rejects with FatalErrorInFunction rather than ignoring:
    #
    #     Available types are :
    #      variable or uniform.
    #
    # Read by incompressibleInterPhaseTransportModel, so it selects how the
    # two-phase inter solver treats density, not the form of the transport
    # model. Foundation has no reader for it in any release from v7 to v14 and
    # ships no dictionary that sets it; five OpenCFD tutorials do, all writing
    # `variable`. Corrected 2026-09-07 after foamlore's nineteen-release sweep
    # refused the key and could not say why from its side.
    "density": entry("density", "Density Treatment",
        "How the two-phase inter solver treats the density field.",
        (
            ChoiceItem("variable", "Density varies with the phase fraction.", _OC),
            ChoiceItem("uniform", "Density is uniform within each phase.", _OC),
        ),
        supported_in=_OC,
        note="OpenCFD only, and read by the two-phase inter solvers. Any other "
             "value is a fatal error, not an ignored entry."),

    # ── per-model coefficient dictionaries ────────────────────────────────────
    # The generated modules carry the coefficients themselves; these entries
    # name the dictionaries that hold them, including models the generator does
    # not yet cover.
    **{
        f"{family}.{model}Coeffs": entry(
            f"{model}Coeffs", f"{model} Coefficients",
            f"Coefficients overriding the {model} model's source defaults. Any "
            f"coefficient left out keeps its built-in value.",
        )
        for family, models in (("RAS", (
            "kEpsilon", "kOmegaSST", "SpalartAllmaras", "realizableKE", "RNGkEpsilon",
            "LaunderSharmaKE", "kOmega", "kOmega2006", "kOmegaSSTLM", "kOmegaSSTSAS",
            "LRR", "SSG", "EBRSM", "GEKO", "kEpsilonPhitF", "v2f", "PDRkEpsilon",
            "buoyantKEpsilon", "kEpsilonLopesdaCosta", "kL",
        )), ("LES", (
            "kEqn", "Smagorinsky", "WALE", "dynamicKEqn", "dynamicLagrangian",
            "DeardorffDiffStress", "sigma", "SpalartAllmarasDES",
            "SpalartAllmarasDDES", "SpalartAllmarasIDDES", "kOmegaSSTDES",
            "kOmegaSSTDDES", "kOmegaSSTIDDES",
        )))
        for model in models
    },

    # A coefficient the generated modules do not carry still gets named help
    # from its dictionary. Exact entries win, so this never shadows them — and
    # it keeps one model's coefficient from being explained by another's.
    **{
        f"{model}Coeffs.*": entry(
            "*", f"{model}Coeffs/<coefficient>",
            f"A coefficient of the {model} model.",
        )
        for model in (
            "kEpsilon", "kOmegaSST", "SpalartAllmaras", "realizableKE", "RNGkEpsilon",
            "LaunderSharmaKE", "kOmega", "kOmega2006", "kOmegaSSTLM", "kOmegaSSTSAS",
            "LRR", "SSG", "EBRSM", "GEKO", "kEpsilonPhitF", "v2f", "PDRkEpsilon",
            "buoyantKEpsilon", "kEpsilonLopesdaCosta", "kL", "kEqn", "Smagorinsky",
            "WALE", "dynamicKEqn",
            "dynamicLagrangian", "DeardorffDiffStress", "sigma",
            "SpalartAllmarasDES", "SpalartAllmarasDDES", "SpalartAllmarasIDDES",
            "kOmegaSSTDES", "kOmegaSSTDDES", "kOmegaSSTIDDES",
        )
    },

    "cubeRootVolCoeffs.*": entry("*", "cubeRootVolCoeffs/<entry>",
        "Coefficient of the cubeRootVol delta model."),
    "vanDriestCoeffs.*": entry("*", "vanDriestCoeffs/<entry>",
        "Coefficient of the vanDriest delta model."),
    "smoothCoeffs.*": entry("*", "smoothCoeffs/<entry>",
        "Coefficient of the smooth delta model."),
    "maxDeltaxyzCoeffs.*": entry("*", "maxDeltaxyzCoeffs/<entry>",
        "Coefficient of the maxDeltaxyz delta model."),
    "PrandtlCoeffs.*": entry("*", "PrandtlCoeffs/<entry>",
        "Coefficient of the Prandtl delta model."),
    "IDDESDeltaCoeffs.*": entry("*", "IDDESDeltaCoeffs/<entry>",
        "Coefficient of the IDDES delta model."),
}

SCHEMAS = _restrict_to_files(SCHEMAS)
