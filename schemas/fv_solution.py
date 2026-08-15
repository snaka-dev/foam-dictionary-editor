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

from schemas._base import (
    BOTH,
    FOUNDATION_SERIES,
    FOUNDATION_V7_V13,
    FOUNDATION_V11_V14,
    FOUNDATION_V14,
    OPENCFD_SERIES,
    SWITCH_CHOICES,
    ChoiceItem,
    KeySchema,
    entry,
)

TARGET_FILE = "fvSolution"

_SOLVER_CHOICES = (
    ChoiceItem("smoothSolver", "Smoother used as a solver. Common for U, k, epsilon, omega.", BOTH),
    ChoiceItem("PCG", "Preconditioned conjugate gradient, for symmetric matrices such as p.", BOTH),
    ChoiceItem("GAMG", "Geometric-algebraic multigrid. Usually fastest for pressure.", BOTH),
    ChoiceItem("PBiCGStab", "Stabilised bi-conjugate gradient, for asymmetric matrices.", BOTH),
    ChoiceItem("PBiCG", "Bi-conjugate gradient, for asymmetric matrices.", BOTH),
    ChoiceItem("diagonal", "Direct solve of a diagonal matrix; used for explicit fields.", BOTH),
    ChoiceItem("FPCG", "Flexible preconditioned conjugate gradient.", BOTH),
    ChoiceItem("PPCG", "Pipelined preconditioned conjugate gradient.", BOTH),
    ChoiceItem("PPCR", "Pipelined preconditioned conjugate residual.", BOTH),
)

_PRECONDITIONER_CHOICES = (
    ChoiceItem("DIC", "Diagonal incomplete-Cholesky, for symmetric matrices.", BOTH),
    ChoiceItem("DILU", "Diagonal incomplete-LU, for asymmetric matrices.", BOTH),
    ChoiceItem("GAMG", "Multigrid used as a preconditioner.", BOTH),
    ChoiceItem("FDIC", "Faster DIC with cached reciprocals.", BOTH),
    ChoiceItem("diagonal", "Diagonal (Jacobi) preconditioning.", BOTH),
    ChoiceItem("none", "No preconditioning.", BOTH),
)

_SMOOTHER_CHOICES = (
    ChoiceItem("symGaussSeidel", "Symmetric Gauss-Seidel. The usual choice.", BOTH),
    ChoiceItem("GaussSeidel", "Gauss-Seidel sweep.", BOTH),
    ChoiceItem("DICGaussSeidel", "DIC followed by Gauss-Seidel; common in GAMG.", BOTH),
    ChoiceItem("DIC", "Diagonal incomplete-Cholesky smoothing.", BOTH),
    ChoiceItem("DILU", "Diagonal incomplete-LU smoothing.", BOTH),
    ChoiceItem("DILUGaussSeidel", "DILU followed by Gauss-Seidel.", BOTH),
    ChoiceItem("FDIC", "Faster DIC smoothing.", BOTH),
    ChoiceItem("nonBlockingGaussSeidel", "Gauss-Seidel overlapping communication.", BOTH),
)

# Keys valid in both SIMPLE and PIMPLE control dictionaries.
_SHARED_CONTROL = {
    "nNonOrthogonalCorrectors": entry(
        "nNonOrthogonalCorrectors", "Non-Orthogonal Correctors",
        "Extra pressure solutions per step correcting mesh non-orthogonality. "
        "0 on an orthogonal mesh; 1-2 otherwise.",
    ),
    "residualControl": entry(
        "residualControl", "Residual Control",
        "Per-field residual thresholds. In SIMPLE these end the run when met; "
        "in PIMPLE they end the outer-corrector loop.",
    ),
    "consistent": entry(
        "consistent", "Consistent (SIMPLEC)",
        "Enables the SIMPLEC variant, allowing much higher relaxation factors.",
        SWITCH_CHOICES,
    ),
    "transonic": entry(
        "transonic", "Transonic",
        "Selects the transonic form of the pressure equation.", SWITCH_CHOICES,
    ),
    "pRefCell": entry(
        "pRefCell", "Pressure Reference Cell",
        "Cell whose pressure is pinned when the case is fully enclosed, so the "
        "pressure level is defined. Ignored if any boundary fixes pressure.",
    ),
    "pRefValue": entry(
        "pRefValue", "Pressure Reference Value",
        "Pressure imposed at pRefCell.",
    ),
    "pRefPoint": entry(
        "pRefPoint", "Pressure Reference Point",
        "Location whose enclosing cell is pinned, as an alternative to pRefCell.",
    ),
    "correctPhi": entry(
        "correctPhi", "Correct Phi",
        "Re-derives a conservative flux after mesh motion or map. Costs an extra "
        "pressure solution.", SWITCH_CHOICES,
    ),
    "checkMeshCourantNo": entry(
        "checkMeshCourantNo", "Check Mesh Courant Number",
        "Reports the mesh Courant number on a moving mesh.", SWITCH_CHOICES,
    ),
    "moveMeshOuterCorrectors": entry(
        "moveMeshOuterCorrectors", "Move Mesh in Outer Correctors",
        "Moves the mesh inside the outer corrector loop rather than once per step.",
        SWITCH_CHOICES,
    ),
}

SCHEMAS: dict[str, KeySchema] = {
    # ── solvers ───────────────────────────────────────────────────────────────
    "solvers": entry(
        "solvers", "Solvers",
        "One sub-dictionary per field, giving the linear solver and its settings.",
    ),
    "solvers.*": entry(
        "*", "solvers/<field>",
        "Linear-solver settings for one field. The name matches the field, "
        "optionally with a 'Final' suffix for the last PIMPLE corrector, and may "
        "be a regular expression such as \"(U|k|epsilon)\".",
    ),
    "solvers.solver": entry("solver", "Linear Solver",
        "Algorithm used to solve this field's matrix.", _SOLVER_CHOICES),
    "solvers.preconditioner": entry("preconditioner", "Preconditioner",
        "Preconditioner for the conjugate-gradient family.", _PRECONDITIONER_CHOICES),
    "solvers.smoother": entry("smoother", "Smoother",
        "Smoother for smoothSolver and GAMG.", _SMOOTHER_CHOICES),
    "solvers.tolerance": entry("tolerance", "Absolute Tolerance",
        "Solving stops when the residual falls below this. Typically 1e-6 or smaller."),
    "solvers.relTol": entry("relTol", "Relative Tolerance",
        "Solving stops when the residual drops by this factor within one step. "
        "0 forces a solve to the absolute tolerance — usual for the final corrector."),
    "solvers.maxIter": entry("maxIter", "Maximum Iterations",
        "Upper bound on solver iterations per step."),
    "solvers.minIter": entry("minIter", "Minimum Iterations",
        "Iterations always performed, even if the tolerance is already met."),
    "solvers.nSweeps": entry("nSweeps", "Sweeps",
        "Smoother sweeps between residual checks."),
    "solvers.nPreSweeps": entry("nPreSweeps", "Pre-Sweeps",
        "GAMG smoother sweeps before coarsening."),
    "solvers.nPostSweeps": entry("nPostSweeps", "Post-Sweeps",
        "GAMG smoother sweeps after refining."),
    "solvers.nFinestSweeps": entry("nFinestSweeps", "Finest Sweeps",
        "GAMG smoother sweeps on the finest level."),
    "solvers.cacheAgglomeration": entry("cacheAgglomeration", "Cache Agglomeration",
        "Reuses the GAMG agglomeration between steps. Leave on for a static mesh.",
        SWITCH_CHOICES),
    "solvers.agglomerator": entry("agglomerator", "Agglomerator",
        "How GAMG builds its coarse levels.",
        (
            ChoiceItem("faceAreaPair", "Pairs cells by shared face area. The usual choice.", BOTH),
            ChoiceItem("assembledFaceAreaPair", "faceAreaPair for assembled (e.g. overset) matrices.", BOTH),
        )),
    # Foundation 14 renamed this to minCellsPerProcessor, but reads both through
    # lookupOrDefaultBackwardsCompatible<label>({"minCellsPerProcessor",
    # "nCellsInCoarsestLevel"}, 10) (GAMGAgglomeration.C), and OpenCFD still
    # reads this spelling as the current one (v2606). So it stays `valid`
    # rather than `renamed`: marking it renamed globally would tell an OpenCFD
    # user to write a key their fork does not read.
    "solvers.nCellsInCoarsestLevel": entry("nCellsInCoarsestLevel", "Cells in Coarsest Level",
        "Target cell count for the coarsest GAMG level. Typically 10-100.",
        note="Foundation v14 prefers minCellsPerProcessor, but still accepts "
             "this spelling. OpenCFD reads this name."),
    "solvers.minCellsPerProcessor": KeySchema(
        key="minCellsPerProcessor",
        label="Min Cells per Processor",
        description=(
            "Target cell count for the coarsest GAMG level, per processor. "
            "Foundation v14's name for nCellsInCoarsestLevel."
        ),
        supported_in=(FOUNDATION_V14,),
        note="Foundation v14 only. Earlier releases and OpenCFD read "
             "nCellsInCoarsestLevel.",
        renamed_from=("nCellsInCoarsestLevel",),
    ),
    "solvers.mergeLevels": entry("mergeLevels", "Merge Levels",
        "GAMG levels merged per agglomeration step. 1 is safest."),
    "solvers.directSolveCoarsest": entry("directSolveCoarsest", "Direct Solve Coarsest",
        "Solves the coarsest GAMG level directly.", SWITCH_CHOICES),
    # Foundation 14 dropped this word entry for a sub-dictionary and provides no
    # compatibility lookup, so writing it there is silently ignored. OpenCFD
    # still reads it (v2606, GAMGAgglomeration.C), hence BOTH plus the note
    # rather than an OpenCFD-only tag. `deprecated_since` records that the span
    # ends for a known reason, which is what keeps the Detail pane from adding
    # its "newer releases not yet measured" caveat: this one *was* measured.
    "solvers.processorAgglomerator": KeySchema(
        key="processorAgglomerator",
        label="Processor Agglomerator",
        description="Agglomerates across processors in parallel GAMG runs.",
        # Measured absent from v14, so this is a closed Foundation range rather
        # than a bare narrow span's "not yet looked at". `deprecated_since` keeps
        # the Detail pane from adding its unmeasured caveat: we did look.
        supported_in=(FOUNDATION_V7_V13, OPENCFD_SERIES),
        note="Foundation v14 replaced this with the processorAgglomeration "
             "sub-dictionary and does not read the old spelling. OpenCFD reads it.",
        deprecated_since="Foundation v14",
    ),
    "solvers.processorAgglomeration": KeySchema(
        key="processorAgglomeration",
        label="Processor Agglomeration",
        description=(
            "Sub-dictionary configuring cross-processor GAMG agglomeration. "
            "Foundation v14's replacement for the processorAgglomerator entry."
        ),
        supported_in=(FOUNDATION_V14,),
        note="Foundation v14 only, and read as a dictionary rather than a word.",
        renamed_from=("processorAgglomerator",),
    ),

    # ── relaxation ────────────────────────────────────────────────────────────
    "relaxationFactors": entry(
        "relaxationFactors", "Relaxation Factors",
        "Under-relaxation, damping the change applied each iteration. Essential "
        "for steady (SIMPLE) runs.",
    ),
    "relaxationFactors.fields": entry(
        "fields", "Field Relaxation",
        "Relaxation applied to solved field values, most often p or p_rgh.",
    ),
    "relaxationFactors.equations": entry(
        "equations", "Equation Relaxation",
        "Relaxation applied to the equations before solving, e.g. U and turbulence.",
    ),
    "fields.*": entry("*", "relaxationFactors/fields/<field>",
        "Relaxation factor for one field. 0-1; lower is more stable and slower."),
    "equations.*": entry("*", "relaxationFactors/equations/<equation>",
        "Relaxation factor for one equation. 0-1; lower is more stable and slower."),

    # ── solution control ──────────────────────────────────────────────────────
    "SIMPLE": entry(
        "SIMPLE", "SIMPLE Controls",
        "Controls for the steady-state SIMPLE pressure-velocity coupling.",
    ),
    "PIMPLE": entry(
        "PIMPLE", "PIMPLE Controls",
        "Controls for the transient PIMPLE coupling — PISO inside an outer loop.",
    ),
    "PISO": entry(
        "PISO", "PISO Controls",
        "Controls for the transient PISO pressure-velocity coupling.",
    ),
    "potentialFlow": entry(
        "potentialFlow", "Potential Flow",
        "Controls for the potential-flow initialisation used by potentialFoam.",
    ),
    "cache": entry(
        "cache", "Cache",
        "Fields kept in memory between iterations, typically grad(U).",
    ),

    **{f"SIMPLE.{k}": v for k, v in _SHARED_CONTROL.items()},
    **{f"PIMPLE.{k}": v for k, v in _SHARED_CONTROL.items()},

    "PIMPLE.nCorrectors": entry("nCorrectors", "Correctors",
        "PISO pressure corrections per outer iteration. Usually 2-3."),
    "PIMPLE.nOuterCorrectors": entry("nOuterCorrectors", "Outer Correctors",
        "Outer PIMPLE loops per time step. 1 makes PIMPLE behave as PISO."),
    "PIMPLE.momentumPredictor": entry("momentumPredictor", "Momentum Predictor",
        "Solves the momentum equation before the pressure correction. Often off "
        "for low-Reynolds or multiphase cases.", SWITCH_CHOICES),
    # Fork-asymmetric, measured per release in pimpleNoLoopControl.C: Foundation
    # renamed this to transportCorrectionFinal at v11 and has read both since
    # (lookupOrDefaultBackwardsCompatible), while OpenCFD reads this spelling as
    # the current one (v2606, pimpleControl.C) and has no transportCorrectionFinal
    # at all. So it stays `valid` rather than `renamed`: marking it renamed
    # globally would tell an OpenCFD user to write a key their fork cannot read.
    "PIMPLE.turbOnFinalIterOnly": KeySchema(
        key="turbOnFinalIterOnly",
        label="Turbulence On Final Iteration Only",
        description="Solves the turbulence equations only on the last outer corrector.",
        supported_in=BOTH,
        choices=SWITCH_CHOICES,
        note="Foundation v11 renamed this to transportCorrectionFinal and still "
             "accepts this spelling. OpenCFD reads this name.",
        deprecated_since="Foundation v11",
    ),
    "PIMPLE.transportCorrectionFinal": KeySchema(
        key="transportCorrectionFinal",
        label="Transport Correction Final",
        description=(
            "Solves the transport (turbulence) equations only on the last outer "
            "corrector. Foundation v11's name for turbOnFinalIterOnly."
        ),
        supported_in=(FOUNDATION_V11_V14,),
        choices=SWITCH_CHOICES,
        note="Foundation v11 onward. OpenCFD reads turbOnFinalIterOnly instead.",
        renamed_from=("turbOnFinalIterOnly",),
    ),
    # Same shape, but the rename is older than the measured span: every
    # Foundation release from v7 reads simpleRho and accepts SIMPLErho, and
    # OpenCFD reads only SIMPLErho.
    "PIMPLE.simpleRho": KeySchema(
        key="simpleRho",
        label="Simple Rho",
        description="Updates density the SIMPLE way, before the pressure equation.",
        supported_in=(FOUNDATION_SERIES,),
        choices=SWITCH_CHOICES,
        note="Foundation's name. OpenCFD reads SIMPLErho instead.",
        renamed_from=("SIMPLErho",),
    ),
    "PIMPLE.SIMPLErho": KeySchema(
        key="SIMPLErho",
        label="SIMPLE Rho",
        description="Updates density the SIMPLE way, before the pressure equation.",
        supported_in=BOTH,
        choices=SWITCH_CHOICES,
        note="OpenCFD's current name; Foundation reads it as the historical "
             "spelling of simpleRho.",
    ),
    # OpenCFD only: no Foundation release reads it. Foundation's equivalent
    # switch is the `transportCorrectionFinal` / `turbOnFinalIterOnly` pair
    # above, which is a different key with a different name in each fork.
    "PIMPLE.finalOnLastPimpleIterOnly": entry("finalOnLastPimpleIterOnly", "Final On Last Iteration Only",
        "Applies the 'Final' solver settings only on the last outer corrector.", SWITCH_CHOICES,
        supported_in=(OPENCFD_SERIES,)),
    "PISO.nCorrectors": entry("nCorrectors", "Correctors",
        "PISO pressure corrections per time step. Usually 2-3."),
    "PISO.nNonOrthogonalCorrectors": _SHARED_CONTROL["nNonOrthogonalCorrectors"],
    "potentialFlow.nNonOrthogonalCorrectors": _SHARED_CONTROL["nNonOrthogonalCorrectors"],
    "residualControl.*": entry("*", "residualControl/<field>",
        "Residual threshold for one field. In PIMPLE this may instead be a "
        "dictionary with 'tolerance' and 'relTol'."),
    # GAMG may be configured as a nested preconditioner dictionary, in which
    # case its own settings sit one level deeper than the solver's.
    "preconditioner.*": entry("*", "preconditioner/<setting>",
        "Setting for a preconditioner given as a dictionary, e.g. a nested GAMG "
        "with its own tolerance, smoother and nVcycles."),
    "solvers.nVcycles": entry("nVcycles", "V-Cycles",
        "GAMG V-cycles per solver iteration."),

    # MULES — the phase-fraction solution in the VOF solvers. These live in the
    # alpha field's solver dictionary rather than in a control dictionary.
    "solvers.nAlphaSubCycles": entry("nAlphaSubCycles", "Alpha Sub-Cycles",
        "Sub-cycles of the phase-fraction equation per time step, letting alpha "
        "run at a smaller step than the momentum equations."),
    "solvers.nAlphaCorr": entry("nAlphaCorr", "Alpha Correctors",
        "Corrector loops within each phase-fraction solution."),
    "solvers.cAlpha": entry("cAlpha", "Interface Compression",
        "Strength of the artificial interface-compression term. 1 is standard; "
        "0 disables it and blurs the interface."),
    "solvers.MULESCorr": entry("MULESCorr", "MULES Corrector",
        "Enables the semi-implicit MULES limiter, which allows a larger time step.",
        SWITCH_CHOICES),
    "solvers.nLimiterIter": entry("nLimiterIter", "Limiter Iterations",
        "Iterations used to compute the MULES limiter."),
    "solvers.alphaApplyPrevCorr": entry("alphaApplyPrevCorr", "Apply Previous Correction",
        "Reuses the previous step's alpha correction as a starting point.",
        SWITCH_CHOICES),
    "solvers.smoothSolver": entry("smoothSolver", "Smooth Solver Settings",
        "Nested settings for a smoothSolver given as a dictionary."),
}
