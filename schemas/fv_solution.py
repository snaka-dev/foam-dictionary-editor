# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from schemas._base import (
    ChoiceItem, KeySchema,
    FOUNDATION_V13, OPENCFD_SERIES,
)

TARGET_FILE = "fvSolution"

SCHEMAS: dict[str, KeySchema] = {
    "solver": KeySchema(
        key="solver",
        label="solvers/<field>/solver",
        description="Selects the linear solver used for the field.",
        supported_in=(FOUNDATION_V13,),
        note="Representative Foundation v13 linear-solver choices. Actual valid choices depend on matrix symmetry and case setup.",
        choices=(
            ChoiceItem("PCG", "Preconditioned conjugate-gradient solver for symmetric systems.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("PBiCG", "Preconditioned bi-conjugate-gradient solver.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("PBiCGStab", "Stabilised preconditioned bi-conjugate-gradient solver.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("smoothSolver", "Iterative solver using a smoothing method.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("GAMG", "Geometric-algebraic multi-grid solver.", supported_in=(FOUNDATION_V13,)),
        ),
    ),
    "preconditioner": KeySchema(
        key="preconditioner",
        label="solvers/<field>/preconditioner",
        description="Selects the preconditioner used by the chosen linear solver.",
        supported_in=(FOUNDATION_V13,),
        note="Availability depends on the chosen solver and matrix properties.",
        choices=(
            ChoiceItem("DIC", "Diagonal incomplete-Cholesky preconditioner.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("DILU", "Diagonal incomplete-LU preconditioner.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("diagonal", "Diagonal preconditioner.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("none", "No preconditioner.", supported_in=(FOUNDATION_V13,)),
        ),
    ),
    "smoother": KeySchema(
        key="smoother",
        label="solvers/<field>/smoother",
        description="Selects the smoother used by smoothSolver or GAMG.",
        supported_in=(FOUNDATION_V13,),
        choices=(
            ChoiceItem("GaussSeidel", "Gauss-Seidel smoother.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("symGaussSeidel", "Symmetric Gauss-Seidel smoother.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("DIC", "Diagonal incomplete-Cholesky smoother option.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("DILU", "Diagonal incomplete-LU smoother option.", supported_in=(FOUNDATION_V13,)),
        ),
    ),
    "cacheAgglomeration": KeySchema(
        key="cacheAgglomeration",
        label="GAMG/cacheAgglomeration",
        description="Controls whether agglomeration data is cached for reuse.",
        supported_in=(FOUNDATION_V13,),
        choices=(
            ChoiceItem("true", "Enable agglomeration caching.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("false", "Disable agglomeration caching.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("yes", "Alternative enabled switch form.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("no", "Alternative disabled switch form.", supported_in=(FOUNDATION_V13,)),
        ),
    ),
    "nCorrectors": KeySchema(
        key="nCorrectors",
        label="PIMPLE/SIMPLE/nCorrectors",
        description="Controls the number of corrector iterations in the algorithm loop.",
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        note="Common algorithm-control key across major OpenFOAM distributions.",
        choices=(),
    ),
    "nNonOrthogonalCorrectors": KeySchema(
        key="nNonOrthogonalCorrectors",
        label="PIMPLE/SIMPLE/nNonOrthogonalCorrectors",
        description="Controls the number of non-orthogonal correction passes.",
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        choices=(),
    ),
    "nOuterCorrectors": KeySchema(
        key="nOuterCorrectors",
        label="PIMPLE/nOuterCorrectors",
        description="Controls the number of outer PIMPLE iterations.",
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        choices=(),
    ),
    "momentumPredictor": KeySchema(
        key="momentumPredictor",
        label="PIMPLE/SIMPLE/momentumPredictor",
        description="Controls whether the momentum predictor step is performed.",
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        choices=(
            ChoiceItem("true", "Enable the momentum predictor.", supported_in=(FOUNDATION_V13, OPENCFD_SERIES)),
            ChoiceItem("false", "Disable the momentum predictor.", supported_in=(FOUNDATION_V13, OPENCFD_SERIES)),
            ChoiceItem("yes", "Alternative enabled switch form.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("no", "Alternative disabled switch form.", supported_in=(FOUNDATION_V13,)),
        ),
    ),
}

