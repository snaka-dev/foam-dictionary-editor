# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Sentences for ``services/log_advice`` codes: a title and an explanation.

The service returns codes, never prose, because ``tests/test_i18n.py`` scans
``ui/`` only. Every code in ``log_advice.ADVICE_CODES`` has both here
(``tests/ui/test_log_advice_ui.py``).
"""
from __future__ import annotations

from i18n import tr
from services import log_advice as la


def advice_title(advice: la.Advice) -> str:
    a = advice.args
    code = advice.code
    if code == la.MISSING_PATCH_ENTRY:
        return tr("A patch has no boundary condition")
    if code == la.UNKNOWN_NAME:
        return tr("Unknown name: {name}").format(name=a.get("name", ""))
    if code == la.CONSTRAINT_MISMATCH:
        return tr("Patch type and boundary condition disagree")
    if code == la.MISSING_ENTRY:
        return tr("Missing entry: {key}").format(key=a.get("key", ""))
    if code == la.NO_REFERENCE_CELL:
        return tr("No pressure reference")
    if code == la.MISSING_FILE:
        return tr("Missing file: {path}").format(path=a.get("path", ""))
    if code == la.NO_MESH:
        return tr("No mesh")
    if code == la.DECOMPOSITION_DIVISIONS:
        return tr("Decomposition does not add up")
    if code == la.PROCESSOR_COUNT:
        return tr("Wrong number of processes")
    if code == la.SYNTAX_ERROR:
        return tr("Dictionary syntax error")
    if code == la.MAX_ITERATIONS:
        return tr("Temperature could not be calculated")
    if code == la.FLOATING_POINT:
        return tr("The solution diverged (floating point exception)")
    return code


def advice_text(advice: la.Advice) -> str:
    a = advice.args
    code = advice.code
    if code == la.MISSING_PATCH_ENTRY:
        return tr(
            "Every patch of the mesh needs an entry in each field's "
            "boundaryField, and {field} has none for {patch}. Add one, or "
            "check that the name matches constant/polyMesh/boundary exactly "
            "(names are case-sensitive). Tools > Check Case… finds these "
            "before a run."
        ).format(field=a.get("field") or tr("the field"), patch=a.get("patch", ""))
    if code == la.UNKNOWN_NAME:
        text = tr(
            "OpenFOAM does not know the {what} \"{name}\". It is usually a "
            "misspelling (names are case-sensitive), or a name from the "
            "other OpenFOAM fork or another version — the log lists the "
            "names this installation accepts."
        ).format(what=a.get("what", ""), name=a.get("name", ""))
        if a.get("suggestion"):
            text += " " + tr("Did you mean \"{suggestion}\"?").format(suggestion=a["suggestion"])
        return text
    if code == la.CONSTRAINT_MISMATCH:
        return tr(
            "The mesh says the patch is of type {patch_type}, but {field} "
            "gives it {field_type}. For empty, symmetry, wedge and cyclic "
            "patches the field's type must be the patch's type. Change the "
            "field, or change the patch type in blockMeshDict and re-run "
            "blockMesh."
        ).format(
            patch_type=a.get("patch_type", ""),
            field=a.get("field") or tr("the field"),
            field_type=a.get("field_type", ""),
        )
    if code == la.MISSING_ENTRY:
        if a.get("present"):
            return tr(
                "{key} is written in {dict}, yet OpenFOAM could not find it. "
                "That almost always means the entry before it is missing its "
                "closing ';' (so it swallowed {key}), or a brace is out of "
                "place. Check the line above it."
            ).format(key=a.get("key", ""), dict=a.get("dict", ""))
        return tr(
            "OpenFOAM needs the entry {key} in {dict}, and it is not there. "
            "Add it — Find OpenFOAM Examples shows how the tutorials write "
            "it — or check its spelling, and that the entry before it ends "
            "with ';'."
        ).format(key=a.get("key", ""), dict=a.get("dict", ""))
    if code == la.NO_REFERENCE_CELL:
        return tr(
            "{field} has no fixed value on any boundary, so its level is "
            "undefined. Set pRefCell and pRefValue (or pRefPoint) in the "
            "solver's dictionary in fvSolution (PISO, PIMPLE or SIMPLE), as "
            "the cavity tutorial does — or give {field} a fixedValue "
            "boundary such as an outlet."
        ).format(field=a.get("field", ""))
    if code == la.MISSING_FILE:
        if a.get("orig"):
            return tr(
                "The solver could not find {path}. This case keeps its "
                "initial fields in {orig}/ — copy them with Tools > Restore "
                "0/ from 0.orig, which is what the tutorial's Allrun does "
                "first."
            ).format(path=a.get("path", ""), orig=a.get("orig", ""))
        return tr(
            "The solver could not find {path}. Create it, copy it from a "
            "tutorial (Find OpenFOAM Examples), or check whether the case "
            "was written for another OpenFOAM version that names the file "
            "differently (Tools > Check Case… tells)."
        ).format(path=a.get("path", ""))
    if code == la.NO_MESH:
        return tr(
            "There is no mesh yet (constant/polyMesh). Run blockMesh, or "
            "snappyHexMesh, first — Tools > Run blockMesh…."
        )
    if code == la.DECOMPOSITION_DIVISIONS:
        return tr(
            "n ({n}) splits the domain into {product} pieces, but "
            "numberOfSubdomains is {count}. Make the product of n equal "
            "numberOfSubdomains."
        ).format(n=a.get("n", ""), product=a.get("product", ""), count=a.get("count", ""))
    if code == la.PROCESSOR_COUNT:
        return tr(
            "The case is set up for {want} processes but the run was started "
            "with {got}. Use mpirun -np {want}, or change numberOfSubdomains "
            "and run decomposePar again."
        ).format(want=a.get("want", ""), got=a.get("got", ""))
    if code == la.SYNTAX_ERROR:
        return tr(
            "OpenFOAM could not read the dictionary: \"{message}\". Look for "
            "an unbalanced brace or bracket, or a missing ';', at or just "
            "before the line it names — the problem is often a line or two "
            "earlier."
        ).format(message=a.get("message", ""))
    if code == la.MAX_ITERATIONS:
        return tr(
            "The temperature could not be recovered from the energy — "
            "usually because the solution has already diverged and the "
            "energy is unphysical. Look at the boundary and initial "
            "conditions for T and p, and try a smaller deltaT."
        )
    if code == la.FLOATING_POINT:
        if a.get("courant"):
            return tr(
                "The run crashed at time {time} with the Courant number at "
                "{courant}. Above about 1 most solvers become unstable: lower "
                "deltaT, or set adjustTimeStep yes with maxCo in controlDict "
                "so the solver chooses it."
            ).format(time=a.get("time", ""), courant=a.get("courant", ""))
        return tr(
            "The solution diverged and the run crashed. Common causes: a "
            "deltaT that is too large, a boundary condition that does not "
            "fit the flow, a poor mesh (run checkMesh), or schemes that are "
            "too aggressive for a first run."
        )
    return code
