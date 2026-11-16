# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Sentences for ``services/case_check`` codes.

The service returns codes, never prose: ``tests/test_i18n.py`` scans ``ui/``
only, so a ``tr()`` literal anywhere else would ship untranslated in silence.
Every code in ``case_check.FINDING_CODES``/``SKIP_CODES`` has a sentence here
(``tests/ui/test_case_check_text.py``).
"""
from __future__ import annotations

from i18n import tr
from services import case_check as cc


def severity_label(severity: str) -> str:
    return tr("Error") if severity == cc.ERROR else tr("Warning")


def finding_location(finding: cc.Finding) -> str:
    """``0/U:21`` -- the file and line, or the directory, or '' for the case."""
    if finding.path and finding.line:
        return f"{finding.path}:{finding.line}"
    return finding.path


def finding_message(finding: cc.Finding) -> str:
    a = finding.args
    code = finding.code
    if code == cc.NO_CONTROL_DICT:
        return tr("system/controlDict is missing — every solver reads it.")
    if code == cc.NO_START_DIR:
        return tr(
            "There is no 0/ directory, so the solver will stop with "
            "\"cannot find file 0/…\". This case keeps its initial fields in "
            "0.orig/ — copy them with Tools > Restore 0/ from 0.orig (what the "
            "tutorial's Allrun does first)."
        )
    if code == cc.MISSING_PATCH_ENTRY:
        return tr(
            "{field} has no boundaryField entry for patch {patches}, so the "
            "solver will stop with \"Cannot find patchField entry\". Add an "
            "entry for it, or check its spelling against the mesh."
        ).format(field=a.get("field", ""), patches=a.get("patches", ""))
    if code == cc.UNMATCHED_PATCH_ENTRY:
        return tr(
            "{field} has entries that match no patch of the mesh: {entries}. "
            "A misspelt patch name?"
        ).format(field=a.get("field", ""), entries=a.get("entries", ""))
    if code == cc.CONSTRAINT_MISMATCH:
        if a.get("patch_type") in cc.CONSTRAINT_TYPES:
            return tr(
                "Patch {patch} is of type {patch_type} in the mesh, so {field} "
                "must give it type {patch_type} too, not {field_type} — the "
                "solver stops with \"inconsistent patch and patchField types\"."
            ).format(**_args(a, "patch", "patch_type", "field", "field_type"))
        return tr(
            "{field} gives patch {patch} type {field_type}, but the mesh patch "
            "is of type {patch_type}. Change the field's type, or the patch's "
            "type (in blockMeshDict, then re-run blockMesh)."
        ).format(**_args(a, "patch", "patch_type", "field", "field_type"))
    if code == cc.NOTHING_WRITTEN:
        if a.get("unit") == "steps":
            return tr(
                "writeInterval is {interval} time steps, but the run is only "
                "{run} steps long, so no results will be written."
            ).format(interval=a.get("interval", ""), run=a.get("run", ""))
        return tr(
            "writeInterval ({interval}) is longer than the run ({run}), so no "
            "results will be written."
        ).format(interval=a.get("interval", ""), run=a.get("run", ""))
    if code == cc.DELTA_T_EXCEEDS_RUN:
        return tr(
            "deltaT ({delta_t}) is longer than the whole run ({run}), so the "
            "solver takes at most a single step, past endTime."
        ).format(delta_t=a.get("delta_t", ""), run=a.get("run", ""))
    if code == cc.ALREADY_AT_END:
        return tr(
            "The run starts at time {start}, which is already endTime ({end}), "
            "so the solver will do nothing. To run further, raise endTime."
        ).format(start=a.get("start", ""), end=a.get("end", ""))
    if code == cc.STOP_AT_LEFT:
        return tr(
            "stopAt is {value}, so the solver will stop right after it starts. "
            "Set it back to endTime unless that is what you want."
        ).format(value=a.get("value", ""))
    if code == cc.DECOMPOSITION_PRODUCT:
        return tr(
            "{method} decomposition n ({n}) makes {product} pieces, but "
            "numberOfSubdomains is {count}, so decomposePar will stop with "
            "\"Wrong number of … divisions\"."
        ).format(**_args(a, "method", "n", "product", "count"))
    if code == cc.PROCESSOR_COUNT:
        return tr(
            "numberOfSubdomains is {count}, but the case is decomposed into "
            "{pieces} — re-run decomposePar before a parallel run."
        ).format(count=a.get("count", ""), pieces=a.get("pieces", ""))
    if code == cc.MISSING_DICTIONARY:
        return tr("constant/{name} is missing, and {solver} reads it.").format(
            name=a.get("name", ""), solver=a.get("solver", "")
        )
    if code == cc.OTHER_FORK_DICTIONARY:
        return tr(
            "{solver} on this OpenFOAM reads constant/{want}, but the case has "
            "{have} — the OpenFOAM Foundation name for it. Copy it to {want} "
            "and check its entries, which differ between the two."
        ).format(**_args(a, "solver", "want", "have"))
    return code


def skip_message(skip: cc.Skip) -> str:
    if skip.code == cc.SKIP_NO_MESH:
        return tr(
            "Boundary conditions were not checked: there is no mesh yet, and "
            "this case's mesh does not come from blockMeshDict alone. Check "
            "again after meshing."
        )
    if skip.code == cc.SKIP_FIELD_UNREADABLE:
        return tr(
            "{path}: boundaryField not checked — it uses an #include or $macro "
            "that could not be followed."
        ).format(path=skip.path)
    if skip.code == cc.SKIP_REGIONS_PREMESH:
        return tr(
            "Multi-region case: boundary conditions are checked once the "
            "region meshes exist."
        )
    return skip.code


def _args(args: dict[str, str], *names: str) -> dict[str, str]:
    return {name: args.get(name, "") for name in names}
