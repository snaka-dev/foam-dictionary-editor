# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from schemas._base import ChoiceItem, KeySchema, FOUNDATION_V13

TARGET_FILE = "fvSchemes"

SCHEMAS: dict[str, KeySchema] = {
    "default.ddtSchemes": KeySchema(
        key="default.ddtSchemes",
        label="ddtSchemes/default",
        description="Selects the temporal discretisation scheme used by default.",
        supported_in=(FOUNDATION_V13,),
        note="The representative values below are taken from Foundation v13 user-guide material. OpenCFD availability may differ by solver and release.",
        choices=(
            ChoiceItem("steadyState", "Steady-state time discretisation.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("Euler", "First-order implicit Euler scheme.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("backward", "Second-order backward differencing scheme.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("CrankNicolson", "Blended second-order Crank-Nicolson scheme.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("localEuler", "Local time-stepping Euler scheme.", supported_in=(FOUNDATION_V13,)),
        ),
    ),
    "default.gradSchemes": KeySchema(
        key="default.gradSchemes",
        label="gradSchemes/default",
        description="Selects the default gradient discretisation scheme.",
        supported_in=(FOUNDATION_V13,),
        note="Foundation guide commonly presents Gauss-based gradient schemes with interpolation variants.",
        choices=(
            ChoiceItem("Gauss linear", "Gauss gradient with linear interpolation.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("leastSquares", "Least-squares gradient reconstruction.", supported_in=(FOUNDATION_V13,)),
        ),
    ),
    "default.snGradSchemes": KeySchema(
        key="default.snGradSchemes",
        label="snGradSchemes/default",
        description="Selects the default surface-normal gradient scheme.",
        supported_in=(FOUNDATION_V13,),
        choices=(
            ChoiceItem("corrected", "Apply non-orthogonality correction.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("uncorrected", "No non-orthogonality correction.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("orthogonal", "Assume orthogonal mesh behavior.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("limited corrected 0.33", "Limited corrected form with limiter 0.33.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("limited corrected 0.5", "Limited corrected form with limiter 0.5.", supported_in=(FOUNDATION_V13,)),
        ),
    ),
    "default.interpolationSchemes": KeySchema(
        key="default.interpolationSchemes",
        label="interpolationSchemes/default",
        description="Selects the default interpolation scheme for values transferred to faces.",
        supported_in=(FOUNDATION_V13,),
        choices=(
            ChoiceItem("linear", "Linear interpolation.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("cubic", "Cubic interpolation.", supported_in=(FOUNDATION_V13,)),
        ),
    ),
    "default.laplacianSchemes": KeySchema(
        key="default.laplacianSchemes",
        label="laplacianSchemes/default",
        description="Selects the default Laplacian discretisation form.",
        supported_in=(FOUNDATION_V13,),
        note="Common forms combine Gauss linear with snGrad handling; exact syntax depends on the case entry.",
        choices=(
            ChoiceItem("Gauss linear corrected", "Gauss Laplacian with corrected snGrad handling.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("Gauss linear uncorrected", "Gauss Laplacian with uncorrected snGrad handling.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("Gauss linear limited corrected 0.33", "Gauss Laplacian with limited correction 0.33.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("Gauss linear limited corrected 0.5", "Gauss Laplacian with limited correction 0.5.", supported_in=(FOUNDATION_V13,)),
        ),
    ),
}

