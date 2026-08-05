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

Model names are the directory listings under
`src/TurbulenceModels/turbulenceModels/{RAS,LES}` (OpenCFD) and
`src/MomentumTransportModels/momentumTransportModels/{RAS,LES}` (Foundation), so
entries that exist in only one fork are tagged accordingly.
"""
from __future__ import annotations

from schemas._base import (
    FOUNDATION_SERIES,
    OPENCFD_SERIES,
    ChoiceItem,
    KeySchema,
)

TARGET_FILES = ("turbulenceProperties", "momentumTransport")

# These dictionaries have structural keys of their own, but OpenFOAM's
# `optionalSubDict` idiom also lets a model's coefficients be written directly
# into them — `RAS { Cmu 0.09; }` rather than `RAS { kEpsilonCoeffs { Cmu … } }`.
# Declaring them open keeps the flat coefficient fallback working inside them;
# the `<model>Coeffs` dictionaries stay closed, so one model's coefficient is
# never explained by another's.
OPEN_NAMESPACES = ("RAS", "LES", "laminar")

_BOTH = (FOUNDATION_SERIES, OPENCFD_SERIES)
_OC = (OPENCFD_SERIES,)
_FD = (FOUNDATION_SERIES,)

_BOOL_CHOICES = (
    ChoiceItem("on", "Enabled.", _BOTH),
    ChoiceItem("off", "Disabled.", _BOTH),
    ChoiceItem("yes", "Enabled.", _BOTH),
    ChoiceItem("no", "Disabled.", _BOTH),
    ChoiceItem("true", "Enabled.", _BOTH),
    ChoiceItem("false", "Disabled.", _BOTH),
)

_RAS_MODELS = (
    ChoiceItem("kEpsilon", "Standard k-epsilon. The most widely used RAS model.", _BOTH),
    ChoiceItem("kOmegaSST", "Menter k-omega SST. Good for adverse pressure gradients "
                            "and separation.", _BOTH),
    ChoiceItem("SpalartAllmaras", "One-equation eddy-viscosity model, common in "
                                  "external aerodynamics.", _BOTH),
    ChoiceItem("realizableKE", "Realizable k-epsilon; better for round jets and "
                               "strong streamline curvature.", _BOTH),
    ChoiceItem("RNGkEpsilon", "RNG k-epsilon; improved for swirling and low-Reynolds flow.", _BOTH),
    ChoiceItem("LaunderSharmaKE", "Low-Reynolds k-epsilon that resolves the viscous sublayer.", _BOTH),
    ChoiceItem("kOmega", "Wilcox k-omega.", _BOTH),
    ChoiceItem("kOmegaSSTLM", "kOmegaSST with the Langtry-Menter transition model.", _BOTH),
    ChoiceItem("kOmegaSSTSAS", "kOmegaSST with scale-adaptive simulation.", _BOTH),
    ChoiceItem("LRR", "Launder-Reece-Rodi Reynolds-stress model.", _BOTH),
    ChoiceItem("SSG", "Speziale-Sarkar-Gatski Reynolds-stress model.", _BOTH),
    ChoiceItem("EBRSM", "Elliptic-blending Reynolds-stress model.", _OC),
    ChoiceItem("GEKO", "Generalised k-omega with tunable coefficients.", _OC),
    ChoiceItem("kEpsilonPhitF", "k-epsilon-phit-f four-equation model.", _OC),
    ChoiceItem("kOmega2006", "Wilcox 2006 revision of k-omega.", _FD),
    ChoiceItem("v2f", "v2-f four-equation model.", _FD),
    ChoiceItem("laminar", "No turbulence model; laminar stress only.", _BOTH),
)

_LES_MODELS = (
    ChoiceItem("kEqn", "One-equation eddy-viscosity SGS model.", _BOTH),
    ChoiceItem("Smagorinsky", "Classic Smagorinsky SGS model.", _BOTH),
    ChoiceItem("WALE", "Wall-adapting local eddy-viscosity; correct near-wall scaling.", _BOTH),
    ChoiceItem("dynamicKEqn", "kEqn with a dynamically computed coefficient.", _BOTH),
    ChoiceItem("dynamicLagrangian", "Lagrangian dynamic SGS model.", _BOTH),
    ChoiceItem("DeardorffDiffStress", "Deardorff differential stress SGS model.", _BOTH),
    ChoiceItem("sigma", "Sigma SGS model.", _OC),
    ChoiceItem("SpalartAllmarasDES", "Spalart-Allmaras detached-eddy simulation.", _FD),
    ChoiceItem("SpalartAllmarasDDES", "Delayed DES variant.", _FD),
    ChoiceItem("SpalartAllmarasIDDES", "Improved delayed DES variant.", _FD),
    ChoiceItem("kOmegaSSTDES", "kOmegaSST-based DES.", _FD),
)

_DELTA_MODELS = (
    ChoiceItem("cubeRootVol", "Cube root of the cell volume. The usual choice.", _BOTH),
    ChoiceItem("vanDriest", "Adds van Driest damping near walls.", _BOTH),
    ChoiceItem("smooth", "Limits how fast delta may change between neighbouring cells.", _BOTH),
    ChoiceItem("maxDeltaxyz", "Largest cell edge length.", _BOTH),
    ChoiceItem("Prandtl", "Prandtl-based damping.", _BOTH),
    ChoiceItem("IDDESDelta", "Delta formulation required by IDDES.", _BOTH),
    ChoiceItem("maxDeltaxyzCubeRootLESDelta", "Blend of maxDeltaxyz and cubeRootVol.", _OC),
    ChoiceItem("DeltaOmegaTilde", "Vorticity-based delta.", _OC),
    ChoiceItem("SLADelta", "Shear-layer-adapted delta.", _OC),
)


def _entry(key: str, label: str, description: str,
           choices: tuple[ChoiceItem, ...] = (),
           supported_in: tuple[str, ...] = _BOTH, note: str = "") -> KeySchema:
    return KeySchema(
        key=key, label=label, description=description,
        supported_in=supported_in, choices=choices, note=note,
    )


# `turbulence` and `printCoeffs` sit in whichever of RAS/LES is active.
_SHARED = {
    "turbulence": _entry(
        "turbulence", "Turbulence",
        "Switches the turbulence model on. With it off the model is constructed "
        "but contributes nothing, leaving a laminar solution.",
        _BOOL_CHOICES,
    ),
    "printCoeffs": _entry(
        "printCoeffs", "Print Coefficients",
        "Prints the model's coefficients to the log at start-up — the quickest "
        "way to see which defaults are actually in force.",
        _BOOL_CHOICES,
    ),
}

SCHEMAS: dict[str, KeySchema] = {
    "simulationType": _entry(
        "simulationType", "Simulation Type",
        "Which family of turbulence treatment the case uses. Selects which of "
        "the dictionaries below is read.",
        (
            ChoiceItem("RAS", "Reynolds-averaged simulation; reads the RAS dictionary.", _BOTH),
            ChoiceItem("LES", "Large-eddy simulation; reads the LES dictionary.", _BOTH),
            ChoiceItem("laminar", "No turbulence modelling.", _BOTH),
        ),
    ),

    # ── RAS ───────────────────────────────────────────────────────────────────
    "RAS": _entry("RAS", "RAS Settings",
        "Settings for Reynolds-averaged simulation, read when simulationType is RAS."),
    "RAS.model": _entry(
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
        supported_in=_BOTH,
        status="renamed",
        use_instead="model",
        deprecated_since="v2006",
        choices=_RAS_MODELS,
    ),
    **{f"RAS.{k}": v for k, v in _SHARED.items()},

    # ── LES ───────────────────────────────────────────────────────────────────
    "LES": _entry("LES", "LES Settings",
        "Settings for large-eddy simulation, read when simulationType is LES."),
    "LES.model": _entry(
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
        supported_in=_BOTH,
        status="renamed",
        use_instead="model",
        deprecated_since="v2006",
        choices=_LES_MODELS,
    ),
    **{f"LES.{k}": v for k, v in _SHARED.items()},
    "LES.delta": _entry(
        "delta", "Delta Model",
        "How the sub-grid length scale is computed from the mesh. Each choice "
        "reads its own <name>Coeffs sub-dictionary.",
        _DELTA_MODELS,
    ),
    "LES.filter": _entry(
        "filter", "Filter",
        "Filter used by the dynamic SGS models.",
        (
            ChoiceItem("simple", "Simple box filter.", _BOTH),
            ChoiceItem("anisotropic", "Anisotropic filter.", _BOTH),
            ChoiceItem("laplace", "Laplacian filter.", _BOTH),
        ),
    ),
    "LES.turbulenceModelCoeffs": _entry("turbulenceModelCoeffs", "Model Coefficients",
        "Coefficients for the selected SGS model."),

    # ── delta coefficient dictionaries ────────────────────────────────────────
    "LES.cubeRootVolCoeffs": _entry("cubeRootVolCoeffs", "cubeRootVol Coefficients",
        "Coefficients for the cubeRootVol delta model."),
    "LES.vanDriestCoeffs": _entry("vanDriestCoeffs", "vanDriest Coefficients",
        "Coefficients for the vanDriest delta model."),
    "LES.smoothCoeffs": _entry("smoothCoeffs", "smooth Coefficients",
        "Coefficients for the smooth delta model."),
    "LES.maxDeltaxyzCoeffs": _entry("maxDeltaxyzCoeffs", "maxDeltaxyz Coefficients",
        "Coefficients for the maxDeltaxyz delta model."),
    "LES.PrandtlCoeffs": _entry("PrandtlCoeffs", "Prandtl Coefficients",
        "Coefficients for the Prandtl delta model."),
    "LES.IDDESDeltaCoeffs": _entry("IDDESDeltaCoeffs", "IDDESDelta Coefficients",
        "Coefficients for the IDDES delta model."),

    "deltaCoeff": _entry("deltaCoeff", "Delta Coefficient",
        "Scaling applied to the computed delta. Usually 1."),
    "maxDeltaRatio": _entry("maxDeltaRatio", "Maximum Delta Ratio",
        "Largest permitted ratio of delta between neighbouring cells, used by "
        "the smooth delta model."),
    "Cdelta": _entry("Cdelta", "Cdelta",
        "Delta coefficient of the Prandtl and van Driest delta models."),
    "Aplus": _entry("Aplus", "A+",
        "Van Driest damping constant, normally 26."),
    "Cmu": _entry("Cmu", "Cmu",
        "Cmu as used by the delta models when converting between length scales."),
    "kappa": _entry("kappa", "von Karman Constant",
        "Von Karman constant, normally 0.41."),

    # Each delta model reads its own sub-dictionary, whose entries are the
    # scalars above; the wildcard keeps them answerable without repeating each
    # coefficient under every dictionary name.
    # ── laminar ───────────────────────────────────────────────────────────────
    "laminar": _entry("laminar", "Laminar Settings",
        "Settings read when simulationType is laminar — the stress model used in "
        "place of a turbulence model."),
    "laminar.model": _entry(
        "model", "Laminar Stress Model",
        "Which laminar stress model to use.",
        (
            ChoiceItem("Stokes", "Newtonian Stokes stress. The usual choice.", _BOTH),
            ChoiceItem("Maxwell", "Maxwell viscoelastic stress model.", _BOTH),
            ChoiceItem("lambdaThixotropic", "Thixotropic viscoelastic model.", _BOTH),
            ChoiceItem("generalisedNewtonian", "Generalised Newtonian stress.", _BOTH),
        ),
    ),
    **{f"laminar.{k}": v for k, v in _SHARED.items()},
    "laminar.laminarModel": KeySchema(
        key="laminarModel", label="Laminar Model (former name)",
        description="Former name of the laminar 'model' selector.",
        supported_in=_BOTH, status="renamed", use_instead="model",
        deprecated_since="v2006",
    ),
    "density": _entry("density", "Density Treatment",
        "Whether the transport model is solved in incompressible or compressible form.",
        (
            ChoiceItem("incompressible", "Incompressible formulation.", _BOTH),
            ChoiceItem("compressible", "Compressible formulation.", _BOTH),
        )),

    # ── per-model coefficient dictionaries ────────────────────────────────────
    # The generated modules carry the coefficients themselves; these entries
    # name the dictionaries that hold them, including models the generator does
    # not yet cover.
    **{
        f"{family}.{model}Coeffs": _entry(
            f"{model}Coeffs", f"{model} Coefficients",
            f"Coefficients overriding the {model} model's source defaults. Any "
            f"coefficient left out keeps its built-in value.",
        )
        for family, models in (("RAS", (
            "kEpsilon", "kOmegaSST", "SpalartAllmaras", "realizableKE", "RNGkEpsilon",
            "LaunderSharmaKE", "kOmega", "kOmega2006", "kOmegaSSTLM", "kOmegaSSTSAS",
            "LRR", "SSG", "EBRSM", "GEKO", "kEpsilonPhitF", "v2f", "PDRkEpsilon",
            "buoyantKEpsilon", "kL",
        )), ("LES", (
            "kEqn", "Smagorinsky", "WALE", "dynamicKEqn", "dynamicLagrangian",
            "DeardorffDiffStress", "sigma", "SpalartAllmarasDES",
            "SpalartAllmarasDDES", "SpalartAllmarasIDDES", "kOmegaSSTDES",
        )))
        for model in models
    },

    # A coefficient the generated modules do not carry still gets named help
    # from its dictionary. Exact entries win, so this never shadows them — and
    # it keeps one model's coefficient from being explained by another's.
    **{
        f"{model}Coeffs.*": _entry(
            "*", f"{model}Coeffs/<coefficient>",
            f"A coefficient of the {model} model.",
        )
        for model in (
            "kEpsilon", "kOmegaSST", "SpalartAllmaras", "realizableKE", "RNGkEpsilon",
            "LaunderSharmaKE", "kOmega", "kOmega2006", "kOmegaSSTLM", "kOmegaSSTSAS",
            "LRR", "SSG", "EBRSM", "GEKO", "kEpsilonPhitF", "v2f", "PDRkEpsilon",
            "buoyantKEpsilon", "kL", "kEqn", "Smagorinsky", "WALE", "dynamicKEqn",
            "dynamicLagrangian", "DeardorffDiffStress", "sigma",
            "SpalartAllmarasDES", "SpalartAllmarasDDES", "SpalartAllmarasIDDES",
            "kOmegaSSTDES",
        )
    },

    "cubeRootVolCoeffs.*": _entry("*", "cubeRootVolCoeffs/<entry>",
        "Coefficient of the cubeRootVol delta model."),
    "vanDriestCoeffs.*": _entry("*", "vanDriestCoeffs/<entry>",
        "Coefficient of the vanDriest delta model."),
    "smoothCoeffs.*": _entry("*", "smoothCoeffs/<entry>",
        "Coefficient of the smooth delta model."),
    "maxDeltaxyzCoeffs.*": _entry("*", "maxDeltaxyzCoeffs/<entry>",
        "Coefficient of the maxDeltaxyz delta model."),
    "PrandtlCoeffs.*": _entry("*", "PrandtlCoeffs/<entry>",
        "Coefficient of the Prandtl delta model."),
    "IDDESDeltaCoeffs.*": _entry("*", "IDDESDeltaCoeffs/<entry>",
        "Coefficient of the IDDES delta model."),
}
