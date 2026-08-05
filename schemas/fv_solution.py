# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Schema for `system/fvSolution`.

Entries inside `solvers`, `relaxationFactors` and `residualControl` are named
after the fields and equations of the case, so they are reached two ways: the
per-field dictionary itself matches a ``"<parent>.*"`` wildcard, while the
settings inside it resolve through the grandparent form — for
``solvers { p { tolerance 1e-6; } }`` the registry looks up
``"solvers.tolerance"``.

Solver, preconditioner and smoother names are the `TypeName` registrations
under `src/OpenFOAM/matrices/lduMatrix/`; choices are ordered by tutorial
frequency.
"""
from __future__ import annotations

from schemas._base import FOUNDATION_SERIES, OPENCFD_SERIES, ChoiceItem, KeySchema

TARGET_FILE = "fvSolution"

_BOTH = (FOUNDATION_SERIES, OPENCFD_SERIES)

_SOLVER_CHOICES = (
    ChoiceItem("smoothSolver", "Smoother used as a solver. Common for U, k, epsilon, omega.", _BOTH),
    ChoiceItem("PCG", "Preconditioned conjugate gradient, for symmetric matrices such as p.", _BOTH),
    ChoiceItem("GAMG", "Geometric-algebraic multigrid. Usually fastest for pressure.", _BOTH),
    ChoiceItem("PBiCGStab", "Stabilised bi-conjugate gradient, for asymmetric matrices.", _BOTH),
    ChoiceItem("PBiCG", "Bi-conjugate gradient, for asymmetric matrices.", _BOTH),
    ChoiceItem("diagonal", "Direct solve of a diagonal matrix; used for explicit fields.", _BOTH),
    ChoiceItem("FPCG", "Flexible preconditioned conjugate gradient.", _BOTH),
    ChoiceItem("PPCG", "Pipelined preconditioned conjugate gradient.", _BOTH),
    ChoiceItem("PPCR", "Pipelined preconditioned conjugate residual.", _BOTH),
)

_PRECONDITIONER_CHOICES = (
    ChoiceItem("DIC", "Diagonal incomplete-Cholesky, for symmetric matrices.", _BOTH),
    ChoiceItem("DILU", "Diagonal incomplete-LU, for asymmetric matrices.", _BOTH),
    ChoiceItem("GAMG", "Multigrid used as a preconditioner.", _BOTH),
    ChoiceItem("FDIC", "Faster DIC with cached reciprocals.", _BOTH),
    ChoiceItem("diagonal", "Diagonal (Jacobi) preconditioning.", _BOTH),
    ChoiceItem("none", "No preconditioning.", _BOTH),
)

_SMOOTHER_CHOICES = (
    ChoiceItem("symGaussSeidel", "Symmetric Gauss-Seidel. The usual choice.", _BOTH),
    ChoiceItem("GaussSeidel", "Gauss-Seidel sweep.", _BOTH),
    ChoiceItem("DICGaussSeidel", "DIC followed by Gauss-Seidel; common in GAMG.", _BOTH),
    ChoiceItem("DIC", "Diagonal incomplete-Cholesky smoothing.", _BOTH),
    ChoiceItem("DILU", "Diagonal incomplete-LU smoothing.", _BOTH),
    ChoiceItem("DILUGaussSeidel", "DILU followed by Gauss-Seidel.", _BOTH),
    ChoiceItem("FDIC", "Faster DIC smoothing.", _BOTH),
    ChoiceItem("nonBlockingGaussSeidel", "Gauss-Seidel overlapping communication.", _BOTH),
)

_BOOL_CHOICES = (
    ChoiceItem("yes", "Enabled.", _BOTH),
    ChoiceItem("no", "Disabled.", _BOTH),
    ChoiceItem("true", "Enabled.", _BOTH),
    ChoiceItem("false", "Disabled.", _BOTH),
    ChoiceItem("on", "Enabled.", _BOTH),
    ChoiceItem("off", "Disabled.", _BOTH),
)


def _entry(key: str, label: str, description: str, choices: tuple[ChoiceItem, ...] = ()) -> KeySchema:
    return KeySchema(
        key=key, label=label, description=description,
        supported_in=_BOTH, choices=choices,
    )


# Keys valid in both SIMPLE and PIMPLE control dictionaries.
_SHARED_CONTROL = {
    "nNonOrthogonalCorrectors": _entry(
        "nNonOrthogonalCorrectors", "Non-Orthogonal Correctors",
        "Extra pressure solutions per step correcting mesh non-orthogonality. "
        "0 on an orthogonal mesh; 1-2 otherwise.",
    ),
    "residualControl": _entry(
        "residualControl", "Residual Control",
        "Per-field residual thresholds. In SIMPLE these end the run when met; "
        "in PIMPLE they end the outer-corrector loop.",
    ),
    "consistent": _entry(
        "consistent", "Consistent (SIMPLEC)",
        "Enables the SIMPLEC variant, allowing much higher relaxation factors.",
        _BOOL_CHOICES,
    ),
    "transonic": _entry(
        "transonic", "Transonic",
        "Selects the transonic form of the pressure equation.", _BOOL_CHOICES,
    ),
    "pRefCell": _entry(
        "pRefCell", "Pressure Reference Cell",
        "Cell whose pressure is pinned when the case is fully enclosed, so the "
        "pressure level is defined. Ignored if any boundary fixes pressure.",
    ),
    "pRefValue": _entry(
        "pRefValue", "Pressure Reference Value",
        "Pressure imposed at pRefCell.",
    ),
    "pRefPoint": _entry(
        "pRefPoint", "Pressure Reference Point",
        "Location whose enclosing cell is pinned, as an alternative to pRefCell.",
    ),
    "correctPhi": _entry(
        "correctPhi", "Correct Phi",
        "Re-derives a conservative flux after mesh motion or map. Costs an extra "
        "pressure solution.", _BOOL_CHOICES,
    ),
    "checkMeshCourantNo": _entry(
        "checkMeshCourantNo", "Check Mesh Courant Number",
        "Reports the mesh Courant number on a moving mesh.", _BOOL_CHOICES,
    ),
    "moveMeshOuterCorrectors": _entry(
        "moveMeshOuterCorrectors", "Move Mesh in Outer Correctors",
        "Moves the mesh inside the outer corrector loop rather than once per step.",
        _BOOL_CHOICES,
    ),
}

SCHEMAS: dict[str, KeySchema] = {
    # ── solvers ───────────────────────────────────────────────────────────────
    "solvers": _entry(
        "solvers", "Solvers",
        "One sub-dictionary per field, giving the linear solver and its settings.",
    ),
    "solvers.*": _entry(
        "*", "solvers/<field>",
        "Linear-solver settings for one field. The name matches the field, "
        "optionally with a 'Final' suffix for the last PIMPLE corrector, and may "
        "be a regular expression such as \"(U|k|epsilon)\".",
    ),
    "solvers.solver": _entry("solver", "Linear Solver",
        "Algorithm used to solve this field's matrix.", _SOLVER_CHOICES),
    "solvers.preconditioner": _entry("preconditioner", "Preconditioner",
        "Preconditioner for the conjugate-gradient family.", _PRECONDITIONER_CHOICES),
    "solvers.smoother": _entry("smoother", "Smoother",
        "Smoother for smoothSolver and GAMG.", _SMOOTHER_CHOICES),
    "solvers.tolerance": _entry("tolerance", "Absolute Tolerance",
        "Solving stops when the residual falls below this. Typically 1e-6 or smaller."),
    "solvers.relTol": _entry("relTol", "Relative Tolerance",
        "Solving stops when the residual drops by this factor within one step. "
        "0 forces a solve to the absolute tolerance — usual for the final corrector."),
    "solvers.maxIter": _entry("maxIter", "Maximum Iterations",
        "Upper bound on solver iterations per step."),
    "solvers.minIter": _entry("minIter", "Minimum Iterations",
        "Iterations always performed, even if the tolerance is already met."),
    "solvers.nSweeps": _entry("nSweeps", "Sweeps",
        "Smoother sweeps between residual checks."),
    "solvers.nPreSweeps": _entry("nPreSweeps", "Pre-Sweeps",
        "GAMG smoother sweeps before coarsening."),
    "solvers.nPostSweeps": _entry("nPostSweeps", "Post-Sweeps",
        "GAMG smoother sweeps after refining."),
    "solvers.nFinestSweeps": _entry("nFinestSweeps", "Finest Sweeps",
        "GAMG smoother sweeps on the finest level."),
    "solvers.cacheAgglomeration": _entry("cacheAgglomeration", "Cache Agglomeration",
        "Reuses the GAMG agglomeration between steps. Leave on for a static mesh.",
        _BOOL_CHOICES),
    "solvers.agglomerator": _entry("agglomerator", "Agglomerator",
        "How GAMG builds its coarse levels.",
        (
            ChoiceItem("faceAreaPair", "Pairs cells by shared face area. The usual choice.", _BOTH),
            ChoiceItem("assembledFaceAreaPair", "faceAreaPair for assembled (e.g. overset) matrices.", _BOTH),
        )),
    "solvers.nCellsInCoarsestLevel": _entry("nCellsInCoarsestLevel", "Cells in Coarsest Level",
        "Target cell count for the coarsest GAMG level. Typically 10-100."),
    "solvers.mergeLevels": _entry("mergeLevels", "Merge Levels",
        "GAMG levels merged per agglomeration step. 1 is safest."),
    "solvers.directSolveCoarsest": _entry("directSolveCoarsest", "Direct Solve Coarsest",
        "Solves the coarsest GAMG level directly.", _BOOL_CHOICES),
    "solvers.processorAgglomerator": _entry("processorAgglomerator", "Processor Agglomerator",
        "Agglomerates across processors in parallel GAMG runs."),

    # ── relaxation ────────────────────────────────────────────────────────────
    "relaxationFactors": _entry(
        "relaxationFactors", "Relaxation Factors",
        "Under-relaxation, damping the change applied each iteration. Essential "
        "for steady (SIMPLE) runs.",
    ),
    "relaxationFactors.fields": _entry(
        "fields", "Field Relaxation",
        "Relaxation applied to solved field values, most often p or p_rgh.",
    ),
    "relaxationFactors.equations": _entry(
        "equations", "Equation Relaxation",
        "Relaxation applied to the equations before solving, e.g. U and turbulence.",
    ),
    "fields.*": _entry("*", "relaxationFactors/fields/<field>",
        "Relaxation factor for one field. 0-1; lower is more stable and slower."),
    "equations.*": _entry("*", "relaxationFactors/equations/<equation>",
        "Relaxation factor for one equation. 0-1; lower is more stable and slower."),

    # ── solution control ──────────────────────────────────────────────────────
    "SIMPLE": _entry(
        "SIMPLE", "SIMPLE Controls",
        "Controls for the steady-state SIMPLE pressure-velocity coupling.",
    ),
    "PIMPLE": _entry(
        "PIMPLE", "PIMPLE Controls",
        "Controls for the transient PIMPLE coupling — PISO inside an outer loop.",
    ),
    "PISO": _entry(
        "PISO", "PISO Controls",
        "Controls for the transient PISO pressure-velocity coupling.",
    ),
    "potentialFlow": _entry(
        "potentialFlow", "Potential Flow",
        "Controls for the potential-flow initialisation used by potentialFoam.",
    ),
    "cache": _entry(
        "cache", "Cache",
        "Fields kept in memory between iterations, typically grad(U).",
    ),

    **{f"SIMPLE.{k}": v for k, v in _SHARED_CONTROL.items()},
    **{f"PIMPLE.{k}": v for k, v in _SHARED_CONTROL.items()},

    "PIMPLE.nCorrectors": _entry("nCorrectors", "Correctors",
        "PISO pressure corrections per outer iteration. Usually 2-3."),
    "PIMPLE.nOuterCorrectors": _entry("nOuterCorrectors", "Outer Correctors",
        "Outer PIMPLE loops per time step. 1 makes PIMPLE behave as PISO."),
    "PIMPLE.momentumPredictor": _entry("momentumPredictor", "Momentum Predictor",
        "Solves the momentum equation before the pressure correction. Often off "
        "for low-Reynolds or multiphase cases.", _BOOL_CHOICES),
    "PIMPLE.turbOnFinalIterOnly": _entry("turbOnFinalIterOnly", "Turbulence On Final Iteration Only",
        "Solves the turbulence equations only on the last outer corrector.", _BOOL_CHOICES),
    "PIMPLE.finalOnLastPimpleIterOnly": _entry("finalOnLastPimpleIterOnly", "Final On Last Iteration Only",
        "Applies the 'Final' solver settings only on the last outer corrector.", _BOOL_CHOICES),
    "PISO.nCorrectors": _entry("nCorrectors", "Correctors",
        "PISO pressure corrections per time step. Usually 2-3."),
    "PISO.nNonOrthogonalCorrectors": _SHARED_CONTROL["nNonOrthogonalCorrectors"],
    "potentialFlow.nNonOrthogonalCorrectors": _SHARED_CONTROL["nNonOrthogonalCorrectors"],
    "residualControl.*": _entry("*", "residualControl/<field>",
        "Residual threshold for one field. In PIMPLE this may instead be a "
        "dictionary with 'tolerance' and 'relTol'."),
    # GAMG may be configured as a nested preconditioner dictionary, in which
    # case its own settings sit one level deeper than the solver's.
    "preconditioner.*": _entry("*", "preconditioner/<setting>",
        "Setting for a preconditioner given as a dictionary, e.g. a nested GAMG "
        "with its own tolerance, smoother and nVcycles."),
    "solvers.nVcycles": _entry("nVcycles", "V-Cycles",
        "GAMG V-cycles per solver iteration."),

    # MULES — the phase-fraction solution in the VOF solvers. These live in the
    # alpha field's solver dictionary rather than in a control dictionary.
    "solvers.nAlphaSubCycles": _entry("nAlphaSubCycles", "Alpha Sub-Cycles",
        "Sub-cycles of the phase-fraction equation per time step, letting alpha "
        "run at a smaller step than the momentum equations."),
    "solvers.nAlphaCorr": _entry("nAlphaCorr", "Alpha Correctors",
        "Corrector loops within each phase-fraction solution."),
    "solvers.cAlpha": _entry("cAlpha", "Interface Compression",
        "Strength of the artificial interface-compression term. 1 is standard; "
        "0 disables it and blurs the interface."),
    "solvers.MULESCorr": _entry("MULESCorr", "MULES Corrector",
        "Enables the semi-implicit MULES limiter, which allows a larger time step.",
        _BOOL_CHOICES),
    "solvers.nLimiterIter": _entry("nLimiterIter", "Limiter Iterations",
        "Iterations used to compute the MULES limiter."),
    "solvers.alphaApplyPrevCorr": _entry("alphaApplyPrevCorr", "Apply Previous Correction",
        "Reuses the previous step's alpha correction as a starting point.",
        _BOOL_CHOICES),
    "solvers.smoothSolver": _entry("smoothSolver", "Smooth Solver Settings",
        "Nested settings for a smoothSolver given as a dictionary."),
}
