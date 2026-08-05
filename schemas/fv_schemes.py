# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Schema for `system/fvSchemes`.

Keys are qualified ``"<parent>.<key>"``, matching the lookup the registry
performs (`schema_for_file_key` builds ``f"{parent_key}.{key_name}"``). Each
category also declares a ``"<category>.*"`` wildcard, because its per-term
entries — ``div(phi,U)``, ``laplacian(nuEff,U)``, ``grad(p)`` — are named after
the fields of the case and cannot be enumerated.

Scheme names come from the `TypeName` registrations under
`src/finiteVolume/finiteVolume/*Schemes/` and
`src/finiteVolume/interpolation/surfaceInterpolation/`; choices are ordered by
how often each occurs in the shipped tutorials.
"""
from __future__ import annotations

from schemas._base import FOUNDATION_SERIES, OPENCFD_SERIES, ChoiceItem, KeySchema

TARGET_FILE = "fvSchemes"

_BOTH = (FOUNDATION_SERIES, OPENCFD_SERIES)


def _category(key: str, label: str, description: str) -> KeySchema:
    """A top-level scheme category — the dictionary itself, not its entries."""
    return KeySchema(key=key, label=label, description=description, supported_in=_BOTH)


# Ordered by tutorial frequency: linear 2325, upwind 634, limitedLinear 401, ...
_DIV_CHOICES = (
    ChoiceItem("Gauss linear", "Second-order central differencing. Accurate but unbounded.", _BOTH),
    ChoiceItem("Gauss upwind", "First-order upwind. Very stable, strongly diffusive.", _BOTH),
    ChoiceItem("Gauss limitedLinear 1", "Linear limited towards upwind. The usual robust choice.", _BOTH),
    ChoiceItem("Gauss linearUpwind grad(U)", "Second-order upwind using a gradient scheme.", _BOTH),
    ChoiceItem("Gauss vanLeer", "TVD scheme, common for phase fractions.", _BOTH),
    ChoiceItem("Gauss limitedLinearV 1",
               "Vector-aware limitedLinear; one limiter for all components.", _BOTH),
    ChoiceItem("Gauss linearUpwindV grad(U)", "Vector-aware linearUpwind.", _BOTH),
    ChoiceItem("Gauss LUST grad(U)", "75% linear / 25% linearUpwind blend, used in LES.", _BOTH),
    ChoiceItem("bounded Gauss upwind", "Adds the -div(phi)*U correction for steady runs.", _BOTH),
    ChoiceItem("bounded Gauss limitedLinear 1", "Bounded limitedLinear, typical for SIMPLE.", _BOTH),
    ChoiceItem("Gauss cubic", "Fourth-order; needs a good mesh.", _BOTH),
    ChoiceItem("none", "No scheme. Every div term must then be named explicitly.", _BOTH),
)

_GRAD_CHOICES = (
    ChoiceItem("Gauss linear", "Standard Gauss gradient with linear interpolation.", _BOTH),
    ChoiceItem("cellLimited Gauss linear 1",
               "Limits the gradient so extrapolated faces stay bounded.", _BOTH),
    ChoiceItem("leastSquares", "Least-squares fit; better on distorted meshes.", _BOTH),
    ChoiceItem("cellMDLimited Gauss linear 1", "Cell limiter applied per direction.", _BOTH),
    ChoiceItem("faceLimited Gauss linear 1", "Face-based gradient limiter.", _BOTH),
    ChoiceItem("faceMDLimited Gauss linear 1", "Face limiter applied per direction.", _BOTH),
    ChoiceItem("fourth", "Fourth-order gradient.", _BOTH),
    ChoiceItem("none", "No gradient scheme.", _BOTH),
)

_DDT_CHOICES = (
    ChoiceItem("steadyState", "Drops the time derivative — steady-state runs.", _BOTH),
    ChoiceItem("Euler", "First-order implicit, bounded. The usual transient choice.", _BOTH),
    ChoiceItem("backward", "Second-order implicit; less stable than Euler.", _BOTH),
    ChoiceItem("CrankNicolson 0.9",
               "Second-order; the coefficient blends towards Euler (0 = pure CN).", _BOTH),
    ChoiceItem("localEuler", "Local time stepping, for steady runs via pseudo-time.", _BOTH),
    ChoiceItem("bounded", "Wrapper adding the -div(phi) correction to another ddt scheme.", _BOTH),
    ChoiceItem("CoEuler", "Courant-number-limited Euler.", _BOTH),
    ChoiceItem("SLTS", "Stabilised local time stepping.", _BOTH),
    ChoiceItem("none", "No time scheme.", _BOTH),
)

_LAPLACIAN_CHOICES = (
    ChoiceItem("Gauss linear corrected", "Full non-orthogonal correction. The usual choice.", _BOTH),
    ChoiceItem("Gauss linear limited corrected 0.33", "Correction limited for poor meshes.", _BOTH),
    ChoiceItem("Gauss linear orthogonal", "No correction — valid only on orthogonal meshes.", _BOTH),
    ChoiceItem("Gauss linear uncorrected", "Skips the correction; cheap but mesh-sensitive.", _BOTH),
    ChoiceItem("Gauss linear limited 0.5", "Blend between corrected and uncorrected.", _BOTH),
    ChoiceItem("none", "No laplacian scheme.", _BOTH),
)

_SNGRAD_CHOICES = (
    ChoiceItem("corrected", "Full non-orthogonal correction.", _BOTH),
    ChoiceItem("limited corrected 0.33", "Correction limited for non-orthogonal meshes.", _BOTH),
    ChoiceItem("orthogonal", "No correction — orthogonal meshes only.", _BOTH),
    ChoiceItem("uncorrected", "Skips the correction.", _BOTH),
    ChoiceItem("limited 0.5", "Bare limited form, without a named sub-scheme.", _BOTH),
    ChoiceItem("faceCorrected", "Face-based correction.", _BOTH),
    ChoiceItem("relaxed", "Relaxed correction.", _BOTH),
    ChoiceItem("skewCorrected", "Adds a skewness correction.", _BOTH),
    ChoiceItem("none", "No surface-normal gradient scheme.", _BOTH),
)

_INTERP_CHOICES = (
    ChoiceItem("linear", "Central differencing. Almost always the choice here.", _BOTH),
    ChoiceItem("cubic", "Fourth-order interpolation.", _BOTH),
    ChoiceItem("pointLinear", "Interpolates via point values.", _BOTH),
    ChoiceItem("harmonic", "Harmonic mean — for sharply varying properties.", _BOTH),
    ChoiceItem("midPoint", "Plain face-midpoint average.", _BOTH),
    ChoiceItem("skewCorrected linear", "Linear with a skewness correction.", _BOTH),
    ChoiceItem("none", "No interpolation scheme.", _BOTH),
)

_WALLDIST_CHOICES = (
    ChoiceItem("meshWave", "Mesh-wave search. The usual method.", _BOTH),
    ChoiceItem("Poisson", "Solves a Poisson equation for the distance.", _BOTH),
    ChoiceItem("advectionDiffusion", "Advection-diffusion method.", _BOTH),
    ChoiceItem("directionalMeshWave", "Mesh wave restricted to a direction.", _BOTH),
)

SCHEMAS: dict[str, KeySchema] = {
    # ── time ──────────────────────────────────────────────────────────────────
    "ddtSchemes": _category(
        "ddtSchemes", "Time Schemes",
        "Discretisation of the time derivatives d/dt — steady-state versus transient.",
    ),
    "ddtSchemes.default": KeySchema(
        key="default", label="ddtSchemes/default",
        description="Time scheme applied to every d/dt term unless overridden by name.",
        supported_in=_BOTH, choices=_DDT_CHOICES,
    ),
    "ddtSchemes.*": KeySchema(
        key="*", label="ddtSchemes/<term>",
        description="Time scheme for one named term, overriding the default.",
        supported_in=_BOTH, choices=_DDT_CHOICES,
    ),

    # ── gradient ──────────────────────────────────────────────────────────────
    "gradSchemes": _category(
        "gradSchemes", "Gradient Schemes",
        "Discretisation of gradient terms grad(...).",
    ),
    "gradSchemes.default": KeySchema(
        key="default", label="gradSchemes/default",
        description="Gradient scheme applied to every grad term unless overridden.",
        supported_in=_BOTH, choices=_GRAD_CHOICES,
    ),
    "gradSchemes.*": KeySchema(
        key="*", label="gradSchemes/<term>",
        description="Gradient scheme for one named term, e.g. grad(U) or grad(p).",
        supported_in=_BOTH, choices=_GRAD_CHOICES,
    ),

    # ── divergence ────────────────────────────────────────────────────────────
    "divSchemes": _category(
        "divSchemes", "Divergence Schemes",
        "Discretisation of divergence terms div(...). Usually the decisive choice "
        "for stability versus accuracy, and the one most often set per term.",
    ),
    "divSchemes.default": KeySchema(
        key="default", label="divSchemes/default",
        description="Divergence scheme for every div term unless overridden. Very "
                    "often 'none', which forces each term to be named explicitly.",
        supported_in=_BOTH, choices=_DIV_CHOICES,
    ),
    "divSchemes.*": KeySchema(
        key="*", label="divSchemes/<term>",
        description="Divergence scheme for one named term, e.g. div(phi,U) or div(phi,k).",
        supported_in=_BOTH, choices=_DIV_CHOICES,
    ),

    # ── laplacian ─────────────────────────────────────────────────────────────
    "laplacianSchemes": _category(
        "laplacianSchemes", "Laplacian Schemes",
        "Discretisation of laplacian terms, including the non-orthogonal correction.",
    ),
    "laplacianSchemes.default": KeySchema(
        key="default", label="laplacianSchemes/default",
        description="Laplacian scheme for every laplacian term unless overridden.",
        supported_in=_BOTH, choices=_LAPLACIAN_CHOICES,
    ),
    "laplacianSchemes.*": KeySchema(
        key="*", label="laplacianSchemes/<term>",
        description="Laplacian scheme for one named term, e.g. laplacian(nuEff,U).",
        supported_in=_BOTH, choices=_LAPLACIAN_CHOICES,
    ),

    # ── interpolation ─────────────────────────────────────────────────────────
    "interpolationSchemes": _category(
        "interpolationSchemes", "Interpolation Schemes",
        "Cell-to-face interpolation used outside the divergence schemes.",
    ),
    "interpolationSchemes.default": KeySchema(
        key="default", label="interpolationSchemes/default",
        description="Cell-to-face interpolation applied unless overridden. Almost always 'linear'.",
        supported_in=_BOTH, choices=_INTERP_CHOICES,
    ),
    "interpolationSchemes.*": KeySchema(
        key="*", label="interpolationSchemes/<term>",
        description="Interpolation scheme for one named term.",
        supported_in=_BOTH, choices=_INTERP_CHOICES,
    ),

    # ── surface-normal gradient ───────────────────────────────────────────────
    "snGradSchemes": _category(
        "snGradSchemes", "Surface Normal Gradient Schemes",
        "Gradient normal to a face, and how far the non-orthogonal correction is trusted.",
    ),
    "snGradSchemes.default": KeySchema(
        key="default", label="snGradSchemes/default",
        description="Surface-normal gradient scheme applied unless overridden.",
        supported_in=_BOTH, choices=_SNGRAD_CHOICES,
    ),
    "snGradSchemes.*": KeySchema(
        key="*", label="snGradSchemes/<term>",
        description="Surface-normal gradient scheme for one named term.",
        supported_in=_BOTH, choices=_SNGRAD_CHOICES,
    ),

    # ── wall distance ─────────────────────────────────────────────────────────
    "wallDist": _category(
        "wallDist", "Wall Distance",
        "How the distance to the nearest wall is computed. Needed by most RAS models.",
    ),
    "wallDist.method": KeySchema(
        key="method", label="wallDist/method",
        description="Algorithm used to compute the wall-distance field.",
        supported_in=_BOTH, choices=_WALLDIST_CHOICES,
    ),
    "wallDist.*": KeySchema(
        key="*", label="wallDist/<entry>",
        description="Option for the selected wall-distance method.",
        supported_in=_BOTH,
    ),
    "wallDist.advectionDiffusionCoeffs": _category(
        "advectionDiffusionCoeffs", "Advection-Diffusion Coefficients",
        "Settings for the advectionDiffusion wall-distance method.",
    ),
    "advectionDiffusionCoeffs.*": KeySchema(
        key="*", label="advectionDiffusionCoeffs/<entry>",
        description="Setting for the advectionDiffusion wall-distance solve, "
                    "such as its tolerance, maxIter or epsilon.",
        supported_in=_BOTH,
    ),

    # ── second time derivative ────────────────────────────────────────────────
    "d2dt2Schemes": _category(
        "d2dt2Schemes", "Second Time Derivative Schemes",
        "Discretisation of d2/dt2 terms, used by solvers with a second-order "
        "time derivative such as the solid-displacement solvers.",
    ),
    "d2dt2Schemes.default": KeySchema(
        key="default", label="d2dt2Schemes/default",
        description="Scheme for every d2/dt2 term unless overridden.",
        supported_in=_BOTH,
        choices=(
            ChoiceItem("Euler", "First-order implicit second time derivative.", _BOTH),
            ChoiceItem("steadyState", "Drops the second time derivative.", _BOTH),
        ),
    ),
    "d2dt2Schemes.*": KeySchema(
        key="*", label="d2dt2Schemes/<term>",
        description="Second-time-derivative scheme for one named term.",
        supported_in=_BOTH,
    ),

    # ── remaining categories ──────────────────────────────────────────────────
    "fluxScheme": KeySchema(
        key="fluxScheme", label="Flux Scheme",
        description="Flux formulation used by rhoCentralFoam. Only these two "
                    "values are accepted; anything else is a fatal error.",
        supported_in=_BOTH,
        choices=(
            ChoiceItem("Kurganov", "Kurganov-Tadmor central-upwind flux. The default.", _BOTH),
            ChoiceItem("Tadmor", "Tadmor central flux.", _BOTH),
        ),
    ),
    "oversetInterpolationSuppressed": _category(
        "oversetInterpolationSuppressed", "Overset Interpolation Suppressed",
        "Fields excluded from overset interpolation.",
    ),
    "oversetInterpolationSuppressed.*": KeySchema(
        key="*", label="oversetInterpolationSuppressed/<field>",
        description="A field excluded from overset interpolation.",
        supported_in=_BOTH,
    ),
    "fluxRequired": _category(
        "fluxRequired", "Flux Required",
        "Fields whose flux must be generated after their equation is solved.",
    ),
    "fluxRequired.*": KeySchema(
        key="*", label="fluxRequired/<field>",
        description="A field needing flux generation; written as a bare name with no value.",
        supported_in=_BOTH,
    ),
    "oversetInterpolation": _category(
        "oversetInterpolation", "Overset Interpolation",
        "Interpolation between overlapping meshes in overset (chimera) cases.",
    ),
    "oversetInterpolation.*": KeySchema(
        key="*", label="oversetInterpolation/<entry>",
        description="Overset interpolation setting.",
        supported_in=_BOTH,
    ),
}
