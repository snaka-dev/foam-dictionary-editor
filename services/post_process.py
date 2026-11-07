# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Qt-free: how to run a function object on results that already exist.

Behind Tools > Run postProcess…. The command differs by fork and by what
the function needs:

- plain ``postProcess -func <name>`` reads fields from disk -- enough for
  probes, sampling, ``mag(U)``, vorticity, and the rest;
- a function that needs the solver's physical models -- ``yPlus``,
  ``wallShearStress``, ``forces`` need the turbulence and transport models
  -- must run *through the solver*: ``simpleFoam -postProcess -func yPlus``
  in OpenCFD and Foundation up to 10, ``foamPostProcess -solver
  incompressibleFluid -func yPlus`` in Foundation 11 and later, where
  ``postProcess`` became ``foamPostProcess`` and solvers became modules.
  Run plainly instead, it exits without error and calculates nothing --
  only "Unable to find turbulence model in the database: yPlus will not be
  calculated" in the log (checked on v2606's pitzDaily), which is worse
  than failing.

Which tool an installation has is read from its own ``applications/`` tree;
whether a function needs the solver, from its ``type`` -- the
``system/<name>`` file's own or its template's -- so a forces function saved
as ``liftOnWing`` counts too.
"""
from __future__ import annotations

import os
import re

from services.case_loader import detect_time_dirs
from services.solver_run import decomposition_status

# Function objects that construct the solver's models, so must run through
# it. By type, as it appears in a function's dictionary or template name.
SOLVER_FUNCTIONS = frozenset(
    {
        "yPlus", "wallShearStress", "forces", "forceCoeffs", "wallHeatFlux",
        "turbulenceFields", "heatTransferCoeff", "wallHeatTransferCoeff",
        "turbulenceIntensity", "shearStress", "stressTensor",
    }
)

# Offered in the function list beside the case's own: one-offs OpenFOAM
# runs straight from its templates, no system/ file needed.
COMMON_FUNCTIONS = (
    "mag(U)", "vorticity", "Q", "CourantNo", "yPlus", "wallShearStress",
    "components(U)", "writeCellCentres", "writeCellVolumes",
)

# The function list's first entry: no -func, so every function object in
# controlDict's functions runs.
ALL_FUNCTIONS = ""

# A -func value: a name, optionally with arguments -- mag(U), residuals(p, U).
_FUNC_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*(\([^;`$\\]*\))?")
_TYPE_RE = re.compile(r"^\s*type\s+([A-Za-z0-9_]+)\s*;", re.MULTILINE)
_CFG_RE = re.compile(r'#includeEtc\s+"[^"]*/([A-Za-z0-9_]+)\.cfg"')


def post_process_tool(installation: str | None) -> str:
    """``foamPostProcess`` (Foundation 11+) or ``postProcess``, as installed.

    ``postProcess`` when the installation is unknown -- the name every fork
    and version but Foundation 11+ uses.
    """
    if installation:
        utilities = os.path.join(installation, "applications", "utilities", "postProcessing")
        if os.path.isdir(os.path.join(utilities, "foamPostProcess")):
            return "foamPostProcess"
    return "postProcess"


def is_valid_function(text: str) -> bool:
    """Whether *text* can go to ``-func`` (a name, maybe with arguments)."""
    return bool(_FUNC_RE.fullmatch(text.strip()))


def function_type(case_dir: str, func: str) -> str:
    """The type of function object *func* names, as far as it can be told.

    ``system/<name>``'s own ``type``, else the template it includes
    (``…/forcesIncompressible.cfg`` -> forcesIncompressible), else the name
    itself -- which for a template run straight by name (``yPlus``) is its
    type.
    """
    base = func.split("(", 1)[0].strip()
    path = os.path.join(case_dir, "system", base)
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read(200_000)
    except OSError:
        return base
    m = _TYPE_RE.search(text)
    if m:
        return m.group(1)
    m = _CFG_RE.search(text)
    return m.group(1) if m else base


def needs_solver(case_dir: str, func: str) -> bool:
    """Whether *func* must run through the solver (see the module docstring).

    Matched by prefix too, so a template named for its flavour --
    ``forcesIncompressible``, ``forceCoeffsCompressible`` -- counts.

    Every function in controlDict at once (no ``-func``) needs it too: plain
    ``postProcess`` then loads no fields at all, so each sampling function
    reports "Cannot find registered field matching (alpha.water)" and writes
    nothing -- checked on v2606's damBreak, where ``interFoam -postProcess``
    and ``postProcess -func <name>`` both write the gauges. The solver loads
    every field it has.
    """
    if func == ALL_FUNCTIONS:
        return True
    kind = function_type(case_dir, func)
    return any(kind == s or kind.startswith(s) for s in SOLVER_FUNCTIONS)


def invocation(
    tool: str, through_solver: bool, application: str | None, module: str | None
) -> list[str] | None:
    """The executable and its leading arguments, or None if it cannot be built.

    Through the solver: ``<application> -postProcess`` where the tool is
    ``postProcess``, ``foamPostProcess -solver <module>`` where it is
    Foundation 11+'s ``foamPostProcess``. None when the solver run needs an
    application or module controlDict does not name.
    """
    if not through_solver:
        return [tool]
    if tool == "foamPostProcess":
        return ["foamPostProcess", "-solver", module] if module else None
    return [application, "-postProcess"] if application else None


def post_process_command(
    installation: str | None,
    case_dir: str,
    name: str = "{name}",
    application: str | None = None,
    module: str | None = None,
) -> str:
    """The command that applies a function object to existing results.

    *name* defaults to a ``{name}`` placeholder, for showing the command
    before the name is final. Foundation 11+ renamed ``postProcess`` to
    ``foamPostProcess``; which one the installation has is read from its own
    ``applications/`` tree. A real *name* whose function needs the solver's
    models (services/post_process.py) runs through the solver -- run plainly
    it would finish without error and calculate nothing. When the latest
    results exist only in processor*, it runs in parallel over them. "" when
    the case has no results to apply it to.
    """
    tool = post_process_tool(installation)
    lead = None
    if name != "{name}" and needs_solver(case_dir, name):
        lead = invocation(tool, True, application, module)
    command = f"{' '.join(lead) if lead else tool} -func {name} -latestTime"
    decomposed = decomposition_status(case_dir)
    if decomposed is not None and decomposed.unreconstructed and not decomposed.collated:
        return f"mpirun -np {decomposed.count} {command} -parallel"
    if any(t != "0" for t in detect_time_dirs(case_dir)):
        return command
    return ""
