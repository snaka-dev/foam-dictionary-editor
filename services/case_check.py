# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Qt-free pre-flight behind Tools > Check Case…: beginners' classic mistakes.

Most first-run failures are a handful of predictable mismatches that can be
found statically, before anything runs. ``check_case`` looks for them and
returns :class:`Finding` *codes*, never sentences -- the wording lives in
``ui/`` (``ui/case_check_text.py``), where the i18n scans can see it.

Every check is measured against the real solver (see DEVELOPER.md's "Check
Case"), and every one follows the same rule: **when in doubt, say nothing.**
A false alarm is worse than silence for a beginner, so anything this module
cannot read with confidence -- an unresolved ``#include``, a ``$macro`` splice,
a regex that will not compile, a mesh another utility will reshape -- turns
the affected check off for that file instead of guessing.

The boundary check mirrors ``GeometricBoundaryField::readField`` in both
forks, which match a patch in this order: a literal entry naming it, a literal
entry naming one of its groups (``inGroups``; a constraint patch -- ``empty``,
``cyclic``, … -- is always in the group named after its type, which is how
``#includeEtc "caseDicts/setConstraintTypes"`` covers it), an ``empty`` patch
with no entry at all (filled in automatically), then a regex key.
"""
from __future__ import annotations

import gzip
import math
import os
import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from foam.block_mesh_extractor import extract_block_mesh_data
from foam.include_expand import expand_includes
from foam.include_resolver import parse_include_directive
from foam.nodes import FoamNode
from foam.parser import OpenFoamParser
from foam.tree_utils import find_child, resolve_scalar, resolve_vector
from foam.var_resolver import build_var_map
from services.solver_run import decomposed_count

ERROR = "error"
WARNING = "warning"

# ── codes ───────────────────────────────────────────────────────────────────
# Findings. Each is worded by ui/case_check_text.py; a test there asserts
# every code here has a sentence.
NO_CONTROL_DICT = "no_control_dict"
NO_START_DIR = "no_start_dir"
MISSING_PATCH_ENTRY = "missing_patch_entry"
UNMATCHED_PATCH_ENTRY = "unmatched_patch_entry"
CONSTRAINT_MISMATCH = "constraint_mismatch"
NOTHING_WRITTEN = "nothing_written"
DELTA_T_EXCEEDS_RUN = "delta_t_exceeds_run"
ALREADY_AT_END = "already_at_end"
STOP_AT_LEFT = "stop_at_left"
DECOMPOSITION_PRODUCT = "decomposition_product"
PROCESSOR_COUNT = "processor_count"
MISSING_DICTIONARY = "missing_dictionary"
OTHER_FORK_DICTIONARY = "other_fork_dictionary"

FINDING_CODES = frozenset({
    NO_CONTROL_DICT, NO_START_DIR, MISSING_PATCH_ENTRY, UNMATCHED_PATCH_ENTRY,
    CONSTRAINT_MISMATCH, NOTHING_WRITTEN, DELTA_T_EXCEEDS_RUN, ALREADY_AT_END,
    STOP_AT_LEFT, DECOMPOSITION_PRODUCT, PROCESSOR_COUNT, MISSING_DICTIONARY,
    OTHER_FORK_DICTIONARY,
})

# Skips: what could not be checked, and why. Shown under the findings so
# "no problems found" never overstates what was looked at.
SKIP_NO_MESH = "no_mesh"              # no polyMesh, and blockMeshDict is not the whole story
SKIP_FIELD_UNREADABLE = "field_unreadable"  # an include/macro/regex we cannot follow
SKIP_REGIONS_PREMESH = "regions_premesh"    # multi-region case before splitMeshRegions

SKIP_CODES = frozenset({SKIP_NO_MESH, SKIP_FIELD_UNREADABLE, SKIP_REGIONS_PREMESH})


@dataclass(frozen=True)
class Finding:
    """One problem, located. ``path`` is case-relative ('' for the case itself)."""

    code: str
    severity: str
    path: str
    # 1-based line in ``path`` to open the editor at; 0 when there is none.
    line: int = 0
    # Values the sentence interpolates (field, patch, numbers…), all strings.
    args: dict[str, str] = field(default_factory=dict, hash=False)


@dataclass(frozen=True)
class Skip:
    """Something that was not checked. ``path`` is case-relative or ''."""

    code: str
    path: str = ""
    args: dict[str, str] = field(default_factory=dict, hash=False)


@dataclass(frozen=True)
class CaseCheck:
    findings: tuple[Finding, ...] = ()
    skipped: tuple[Skip, ...] = ()

    @property
    def errors(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity == ERROR)


# ── patch-type knowledge ─────────────────────────────────────────────────────

# Constraint types whose patch and patchField must agree. Each fork's
# ``setConstraintTypes`` keys a subset of these (union taken), and a
# constraint patch is automatically in the group named after its type.
CONSTRAINT_TYPES = frozenset({
    "empty", "cyclic", "cyclicAMI", "cyclicACMI", "cyclicSlip", "symmetryPlane",
    "symmetry", "wedge", "processor", "processorCyclic", "nonuniformTransformCyclic",
    "nonConformalCyclic", "nonConformalError", "nonConformalProcessorCyclic",
    "overset", "internal",
})
# Patch types that put a patch in a group of their own name (polyPatch.C for
# constraints; wallPolyPatch.C, mappedPolyPatch.C, … add theirs explicitly).
# A written boundary file lists these under inGroups already; blockMeshDict
# does not, so they are inferred for the pre-mesh check.
_SELF_GROUP_TYPES = CONSTRAINT_TYPES | {"wall", "mappedPatch", "mappedInternal"}
# Types derived from wallPolyPatch, which are in the "wall" group too.
_WALL_TYPES = frozenset({"wall", "mappedWall"})
# The constraint types the type-agreement check judges. A narrower set than
# above: these are the ones a beginner meets, and their patchField type is the
# patch type itself (cyclic's jump/fan derivatives are not, hence no cyclic).
_CHECKED_CONSTRAINTS = frozenset({"empty", "symmetryPlane", "symmetry", "wedge"})
# Mesh patch types known *not* to be constraints. A patch of any other type
# (mapped*, cyclic*, overset, …) is left out of the agreement check.
_PLAIN_PATCH_TYPES = frozenset({"patch", "wall"})
# patchField types that are certainly not constraint types; one of these on a
# checked constraint patch is OpenFOAM's "inconsistent patch and patchField
# types". Kept to the common ones -- an unlisted type is not judged.
_PLAIN_FIELD_TYPES = frozenset({
    "fixedValue", "zeroGradient", "fixedGradient", "calculated", "noSlip", "slip",
    "inletOutlet", "outletInlet", "totalPressure", "fixedFluxPressure",
    "pressureInletOutletVelocity", "flowRateInletVelocity", "uniformFixedValue",
    "movingWallVelocity", "kqRWallFunction", "epsilonWallFunction",
    "omegaWallFunction", "nutkWallFunction", "nutUWallFunction",
    "nutLowReWallFunction", "turbulentIntensityKineticEnergyInlet",
    "turbulentMixingLengthDissipationRateInlet",
    "turbulentMixingLengthFrequencyInlet", "variableHeightFlowRate",
    "variableHeightFlowRateInletVelocity", "mixed", "codedFixedValue",
})


# ── reading ──────────────────────────────────────────────────────────────────

ReadText = Callable[[str], "str | None"]

# Bigger files are not read at all: a check must stay quick enough for Run
# Solver's dialog, and a field this large is a result, not a beginner's input.
_MAX_FIELD_BYTES = 64 * 1024 * 1024
# Read from the FoamFile header, which may be written on one line.
_FIELD_CLASS_RE = re.compile(r"(?<![\w.])class\s+\"?((?:vol|surface|point)\w*Field)\"?\s*;")
_FORMAT_RE = re.compile(r"(?<![\w.])format\s+(\w+)\s*;")
# A nonuniform list, to blank out before parsing: only boundaryField's keys and
# types are needed, and a million-value internalField would dominate the parse.
_NONUNIFORM_RE = re.compile(r"nonuniform\s+(?:List<\w+>\s*)?\d*\s*(?=\()")
_PAREN_LIST_RE = re.compile(r"\((?:[^()]|\([^()]*\))*\)")


def _read(path: str, read_text: ReadText | None) -> str | None:
    if read_text is not None:
        text = read_text(path)
        if text is not None:
            return text
    try:
        if path.endswith(".gz"):
            with gzip.open(path, "rb") as f:
                data = f.read(_MAX_FIELD_BYTES + 1)
        else:
            if os.path.getsize(path) > _MAX_FIELD_BYTES:
                return None
            with open(path, "rb") as f:
                data = f.read()
    except OSError:
        return None
    if len(data) > _MAX_FIELD_BYTES:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def _parse(text: str) -> FoamNode | None:
    try:
        return OpenFoamParser(text).parse()
    except Exception:  # a broken dictionary means "unknown", not a crash
        return None


def _strip_lists(text: str) -> str:
    """*text* with every ``nonuniform`` list body replaced by ``()``."""
    out: list[str] = []
    pos = 0
    for m in _NONUNIFORM_RE.finditer(text):
        if m.start() < pos:
            continue
        body = _PAREN_LIST_RE.match(text, m.end())
        if body is None:
            continue
        out.append(text[pos:m.start()])
        out.append("nonuniform ()")
        pos = body.end()
    out.append(text[pos:])
    return "".join(out)


def _word(node: FoamNode | None) -> str | None:
    if node is None or node.children or node.value is None:
        return None
    text = str(node.value).strip().strip('"').strip()
    return text if re.fullmatch(r"[A-Za-z_][\w.:-]*", text) else None


def _rel(case_dir: str, path: str) -> str:
    return os.path.relpath(path, case_dir)


# ── time directories ─────────────────────────────────────────────────────────

def _time_dirs(case_dir: str) -> list[tuple[float, str]]:
    """Numeric directories at the case root, ``0`` included, ascending."""
    found: list[tuple[float, str]] = []
    try:
        entries = os.listdir(case_dir)
    except OSError:
        return []
    for name in entries:
        try:
            value = float(name)
        except ValueError:
            continue
        if math.isfinite(value) and os.path.isdir(os.path.join(case_dir, name)):
            found.append((value, name))
    return sorted(found)


@dataclass
class _Control:
    """The controlDict entries the checks read; None where unresolvable."""

    root: FoamNode | None = None
    application: str | None = None
    module: str | None = None
    start_from: str | None = None
    start_time: float | None = None
    end_time: float | None = None
    delta_t: float | None = None
    write_control: str | None = None
    write_interval: float | None = None
    adjust_time_step: bool = False
    stop_at: str | None = None
    lines: dict[str, int] = field(default_factory=dict)


def _read_control(text: str) -> _Control:
    root = _parse(text)
    ctl = _Control(root=root)
    if root is None:
        return ctl
    var_map = build_var_map(root)

    def scalar(key: str) -> float | None:
        node = find_child(root, key)
        if node is None:
            return None
        ctl.lines[key] = node.source_line
        try:
            return resolve_scalar(node, var_map)
        except (TypeError, ValueError):
            return None

    def word(key: str) -> str | None:
        node = find_child(root, key)
        if node is not None:
            ctl.lines[key] = node.source_line
        return _word(node)

    ctl.application = word("application")
    if ctl.application == "foamRun":
        ctl.module = word("solver")
    ctl.start_from = word("startFrom")
    ctl.start_time = scalar("startTime")
    ctl.end_time = scalar("endTime")
    ctl.delta_t = scalar("deltaT")
    ctl.write_control = word("writeControl")
    ctl.write_interval = scalar("writeInterval")
    ctl.adjust_time_step = (word("adjustTimeStep") or "").lower() in ("yes", "on", "true")
    ctl.stop_at = word("stopAt")
    return ctl


def _start_dir(case_dir: str, ctl: _Control) -> tuple[float, str] | None:
    """The time directory the solver starts from, or None if it cannot be told."""
    times = _time_dirs(case_dir)
    if not times:
        return None
    if ctl.start_from == "latestTime":
        return times[-1]
    if ctl.start_from == "firstTime":
        return times[0]
    if ctl.start_time is None:
        return None
    for value, name in times:
        if math.isclose(value, ctl.start_time, rel_tol=1e-9, abs_tol=1e-12):
            return value, name
    return None


# ── patches ──────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Patch:
    name: str
    type: str
    groups: frozenset[str] = frozenset()


def _groups_of(node: FoamNode, patch_type: str) -> frozenset[str]:
    groups: set[str] = set()
    in_groups = find_child(node, "inGroups")
    if in_groups is not None and in_groups.value is not None:
        text = re.sub(r"List\s*<\s*word\s*>", " ", str(in_groups.value))
        text = re.sub(r"^\s*\d+", " ", text)
        groups.update(re.findall(r"[A-Za-z_][\w.:-]*", text))
    # Any type but plain `patch` counts as its own group: the types known to
    # be (_SELF_GROUP_TYPES) and, leniently, every other -- a fork's own
    # constraint (Foundation 8/9's cyclicRepeatAMI) is unknown here, and an
    # extra group can only make coverage pass, never raise a false alarm.
    if patch_type and patch_type != "patch":
        groups.add(patch_type)
    if patch_type in _WALL_TYPES:
        groups.add("wall")
    return frozenset(groups)


def read_boundary_patches(text: str) -> list[Patch] | None:
    """Patches of a ``polyMesh/boundary`` file, in order; None if unreadable."""
    body = re.sub(r"\bFoamFile\s*\{.*?\}", " ", text, count=1, flags=re.S)
    body = re.sub(r"//[^\n]*|/\*.*?\*/", " ", body, flags=re.S)
    start = body.find("(")
    end = body.rfind(")")
    if start < 0 or end <= start:
        return None
    root = _parse(body[start + 1:end])
    if root is None:
        return None
    patches = []
    for child in root.children:
        if child.node_type != "dictionary" or not child.name:
            return None
        patch_type = _word(find_child(child, "type")) or ""
        patches.append(Patch(child.name, patch_type, _groups_of(child, patch_type)))
    return patches


# Utilities, dictionaries and words that mean the mesh the solver sees is not
# simply blockMeshDict's -- patches are added, renamed, split or retyped
# after blockMesh, or the mesh comes from somewhere else entirely. Any of them
# turns the pre-mesh boundary check off.
_RESHAPING_DICTS = (
    "snappyHexMeshDict", "createPatchDict", "extrudeMeshDict", "createBafflesDict",
    "mirrorMeshDict", "changeDictionaryDict", "foamyHexMeshDict", "extrude2DMeshDict",
    "stitchMeshDict", "mergeMeshesDict", "splitMeshRegionsDict", "createNonConformalCouplesDict",
    "extrudeToRegionMeshDict",
)
_RESHAPING_WORDS = re.compile(
    r"\b(snappyHexMesh|extrudeMesh|extrudeToRegionMesh|createPatch|createBaffles|mirrorMesh|stitchMesh|"
    r"mergeMeshes|changeDictionary|splitMeshRegions|\w+ToFoam|polyDualMesh|subsetMesh|"
    r"extrude2DMesh|foamyHexMesh|createNonConformalCouples|polyMesh|foamDictionary|"
    r"m4|blockMesh\s+-dict|cartesianMesh|refineWallLayer|moveMesh|transformPoints)\b"
)
_SCRIPT_NAMES = ("Allrun", "Allrun.pre", "Allmesh", "Allrun-parallel", "Allrun-serial")


def _block_mesh_only(case_dir: str, read_text: ReadText | None) -> bool:
    """Whether the mesh will be blockMeshDict's patches exactly."""
    system = os.path.join(case_dir, "system")
    for name in _RESHAPING_DICTS:
        if os.path.exists(os.path.join(system, name)):
            return False
    for name in _SCRIPT_NAMES:
        text = _read(os.path.join(case_dir, name), read_text)
        if text is None:
            continue
        code = "\n".join(line.split("#", 1)[0] for line in text.splitlines())
        if _RESHAPING_WORDS.search(code):
            return False
    return True


def _block_mesh_patches(
    case_dir: str, read_text: ReadText | None, etc_dirs: Sequence[Path]
) -> list[Patch] | None:
    path = os.path.join(case_dir, "system", "blockMeshDict")
    text = _read(path, read_text)
    if text is None:
        return None
    root = _parse(text)
    if root is None:
        return None
    expanded = expand_includes(
        root, source_file=Path(path), case_dir=Path(case_dir), etc_dirs=etc_dirs
    )
    if expanded.unresolved:
        return None
    merged = expanded.root
    if find_child(merged, "patches") is not None:
        return None  # the old list syntax, which the extractor does not read
    merge = find_child(merged, "mergePatchPairs")
    if merge is not None and str(merge.value or "").strip():
        return None  # merged patches can vanish (Foundation's condenser)
    boundary = find_child(merged, "boundary")
    if boundary is None:
        return None
    try:
        data = extract_block_mesh_data(merged)
    except Exception:
        return None
    if not data.hex_blocks or not data.boundary_faces:
        return None
    groups_by_name: dict[str, FoamNode] = {
        c.name: c for c in boundary.children if c.name and c.children
    }
    patches = []
    for name, (patch_type, _faces) in data.boundary_faces.items():
        if not re.fullmatch(r"[A-Za-z_][\w.:-]*", name) or not patch_type:
            return None  # a $macro or #eval name we cannot see through
        node = groups_by_name.get(name, FoamNode(name, "dictionary"))
        patches.append(Patch(name, patch_type, _groups_of(node, patch_type)))
    if data.default_faces:
        default = find_child(merged, "defaultPatch")
        default_node = default if default is not None else FoamNode("defaultPatch", "dictionary")
        default_name = _word(find_child(default_node, "name")) or "defaultFaces"
        default_type = _word(find_child(default_node, "type")) or "empty"
        # A patch declared under the default name (TJunction's `defaultFaces
        # { type wall; faces (); }`) receives the leftover faces itself and
        # keeps its declared type.
        declared = default_name in data.boundary_faces
        all_faces_read = all(faces for _t, faces in data.boundary_faces.values())
        if not declared and (default_type == "empty" or all_faces_read):
            patches.append(
                Patch(default_name, default_type, _groups_of(default_node, default_type))
            )
    return patches


# ── boundary coverage ───────────────────────────────────────────────────────

_SET_CONSTRAINT_TYPES_RE = re.compile(r"caseDicts/setConstraintTypes\b")


@dataclass
class _Entries:
    """A field's boundaryField entries, as OpenFOAM will match them."""

    literal: dict[str, FoamNode] = field(default_factory=dict)
    # Literal keys in dictionary order, for the reverse-order group rule.
    literal_order: list[str] = field(default_factory=list)
    regex: list[tuple[re.Pattern[str], FoamNode]] = field(default_factory=list)
    # Literal keys written in the field file itself (not from an include).
    own_literal: list[str] = field(default_factory=list)


def _field_entries(
    path: str, text: str, case_dir: str, etc_dirs: Sequence[Path]
) -> tuple[_Entries, FoamNode] | None:
    """The boundaryField entries of a field file, or None when unreadable."""
    root = _parse(_strip_lists(text))
    if root is None:
        return None
    own_bf = find_child(root, "boundaryField")
    expanded = expand_includes(
        root, source_file=Path(path), case_dir=Path(case_dir), etc_dirs=etc_dirs
    )
    bf = find_child(expanded.root, "boundaryField")
    if bf is None or own_bf is None:
        return None
    own_ids = {id(c) for c in own_bf.children}
    entries = _Entries()
    for child in bf.children:
        if child.node_type == "directive_entry":
            value = str(child.value)
            ref = parse_include_directive(value)
            if ref is not None and ref.kind == "includeEtc" and _SET_CONSTRAINT_TYPES_RE.search(value):
                # Unresolved only when no installation is found: what it
                # would have added is known, and installation-independent
                # enough for coverage.
                for name in sorted(CONSTRAINT_TYPES):
                    if name not in entries.literal:
                        entries.literal_order.append(name)
                    entries.literal[name] = FoamNode(name=name, node_type="dictionary")
                continue
            return None
        if child.node_type == "macro_entry":
            return None
        if child.node_type != "dictionary" or not child.name:
            continue
        name = child.name
        if name.startswith('"'):
            try:
                pattern = re.compile(name.strip('"'))
            except re.error:
                return None
            entries.regex.append((pattern, child))
            continue
        if name not in entries.literal:
            entries.literal_order.append(name)
        entries.literal[name] = child
        if id(child) in own_ids:
            entries.own_literal.append(name)
    return entries, own_bf


def _match(patch: Patch, entries: _Entries) -> FoamNode | None | bool:
    """The entry OpenFOAM uses for *patch*; True for an auto-filled empty patch."""
    if patch.name in entries.literal:
        return entries.literal[patch.name]
    for key in reversed(entries.literal_order):
        if key in patch.groups:
            return entries.literal[key]
    if patch.type == "empty":
        return True
    for pattern, node in reversed(entries.regex):
        if pattern.fullmatch(patch.name):
            return node
    return None


def _entry_type(node: FoamNode) -> str | None:
    if find_child(node, "patchType") is not None:
        return None  # an explicit override; OpenFOAM accepts the pairing
    if any(c.node_type in ("macro_entry", "directive_entry") for c in node.children):
        return None
    return _word(find_child(node, "type"))


def _constraint_problem(patch: Patch, field_type: str) -> bool:
    if patch.type in _CHECKED_CONSTRAINTS:
        if field_type in CONSTRAINT_TYPES:
            return field_type != patch.type
        return field_type in _PLAIN_FIELD_TYPES
    if patch.type in _PLAIN_PATCH_TYPES:
        return field_type in _CHECKED_CONSTRAINTS
    return False


# Fields a motion solver constructs with READ_IF_PRESENT and its own patch
# types (displacementLaplacianFvMotionSolver.C, …): a 0/ copy that lacks a
# patch is not necessarily read, and the overset heatTransferFluxConservation1D
# tutorial ships exactly that and runs. Not judged.
_OPTIONALLY_READ_FIELDS = frozenset({"cellDisplacement", "cellMotionU"})


def _field_files(directory: str) -> list[str]:
    try:
        names = sorted(os.listdir(directory))
    except OSError:
        return []
    return [
        n for n in names
        if not n.startswith(".") and not n.endswith((".orig", "~"))
        and ".bak" not in n and os.path.isfile(os.path.join(directory, n))
    ]


def _check_fields(
    case_dir: str,
    field_dir: str,
    patches: list[Patch],
    read_text: ReadText | None,
    etc_dirs: Sequence[Path],
    findings: list[Finding],
    skipped: list[Skip],
) -> None:
    for name in _field_files(field_dir):
        path = os.path.join(field_dir, name)
        text = _read(path, read_text)
        if text is None:
            continue
        head = text[:4000]
        field_class = _FIELD_CLASS_RE.search(head)
        if field_class is None:
            continue
        # pointPatchField::New quietly substitutes the patch's own constraint
        # type for an incompatible one (pointPatchFieldNew), so only vol and
        # surface fields can fail on a constraint mismatch.
        judge_constraints = not field_class.group(1).startswith("point")
        fmt = _FORMAT_RE.search(head)
        if fmt is not None and fmt.group(1) == "binary":
            continue
        rel = _rel(case_dir, path)
        field_name = name[:-3] if name.endswith(".gz") else name
        if field_name in _OPTIONALLY_READ_FIELDS:
            continue
        read = _field_entries(path, text, case_dir, etc_dirs)
        if read is None:
            skipped.append(Skip(SKIP_FIELD_UNREADABLE, rel, {"field": field_name}))
            continue
        entries, own_bf = read
        missing: list[str] = []
        for patch in patches:
            entry = _match(patch, entries)
            if entry is None:
                missing.append(patch.name)
                continue
            if entry is True or not isinstance(entry, FoamNode) or not judge_constraints:
                continue
            field_type = _entry_type(entry)
            if field_type is not None and _constraint_problem(patch, field_type):
                type_node = find_child(entry, "type")
                own = any(c is entry for c in own_bf.children)
                line = type_node.source_line if type_node is not None and own else 0
                findings.append(Finding(
                    CONSTRAINT_MISMATCH, ERROR, rel, line or own_bf.source_line,
                    {"field": field_name, "patch": patch.name,
                     "patch_type": patch.type, "field_type": field_type},
                ))
        if missing:
            findings.append(Finding(
                MISSING_PATCH_ENTRY, ERROR, rel, own_bf.source_line,
                {"field": field_name, "patches": ", ".join(missing)},
            ))
            known = {p.name for p in patches} | CONSTRAINT_TYPES
            for p in patches:
                known |= p.groups
            stray = [k for k in entries.own_literal if k not in known]
            if stray:
                node = entries.literal[stray[0]]
                findings.append(Finding(
                    UNMATCHED_PATCH_ENTRY, WARNING, rel, node.source_line or own_bf.source_line,
                    {"field": field_name, "entries": ", ".join(stray)},
                ))


def _check_boundaries(
    case_dir: str,
    start: str,
    read_text: ReadText | None,
    etc_dirs: Sequence[Path],
    findings: list[Finding],
    skipped: list[Skip],
) -> None:
    start_dir = os.path.join(case_dir, start)
    if os.path.exists(os.path.join(case_dir, "constant", "regionProperties")):
        any_region = False
        try:
            regions = sorted(os.listdir(start_dir))
        except OSError:
            regions = []
        for region in regions:
            region_dir = os.path.join(start_dir, region)
            if not os.path.isdir(region_dir) or region == "polyMesh" or region == "uniform":
                continue
            boundary = _mesh_boundary(case_dir, start, region)
            if boundary is None:
                continue
            any_region = True
            text = _read(boundary, None)
            region_patches = read_boundary_patches(text) if text is not None else None
            if region_patches:
                _check_fields(case_dir, region_dir, region_patches, read_text, etc_dirs, findings, skipped)
        if not any_region:
            skipped.append(Skip(SKIP_REGIONS_PREMESH))
        return

    boundary = _mesh_boundary(case_dir, start, "")
    patches: list[Patch] | None = None
    if boundary is not None:
        text = _read(boundary, None)
        patches = read_boundary_patches(text) if text is not None else None
    elif _block_mesh_only(case_dir, read_text):
        patches = _block_mesh_patches(case_dir, read_text, etc_dirs)
    if not patches:
        skipped.append(Skip(SKIP_NO_MESH))
        return
    _check_fields(case_dir, start_dir, patches, read_text, etc_dirs, findings, skipped)


def _mesh_boundary(case_dir: str, start: str, region: str) -> str | None:
    """The ``boundary`` file the solver will read for *region* ('' for none)."""
    for base in (os.path.join(case_dir, start), os.path.join(case_dir, "constant")):
        path = os.path.join(base, region, "polyMesh", "boundary")
        if os.path.isfile(path):
            return path
    return None


# ── controlDict ──────────────────────────────────────────────────────────────

_RUN_TIME_CONTROLS = frozenset({"runTime", "adjustableRunTime", "adjustable"})
# stopAt values that end the run as soon as it starts. Not ``nextWrite``
# (Run Solver's warning counts it, as FoDE's own Stop can leave it behind):
# a run starting with it still runs to its first write, a legitimate setup.
_IMMEDIATE_STOPS = frozenset({"writeNow", "noWriteNow"})
# A write interval this many times the run length is read as a deliberate
# "do not write" (OpenCFD's IO/systemCall: 25x, pitzDaily_fused: 500x), not
# the mistake of shortening endTime below the interval.
_DELIBERATE_NO_WRITE_RATIO = 10.0


def _check_control(
    ctl: _Control, start_value: float | None, findings: list[Finding]
) -> None:
    rel = os.path.join("system", "controlDict")
    if ctl.stop_at in _IMMEDIATE_STOPS:
        findings.append(Finding(
            STOP_AT_LEFT, ERROR, rel, ctl.lines.get("stopAt", 0), {"value": ctl.stop_at or ""},
        ))
        return  # the run stops at once anyway; the time checks would only add noise
    if ctl.stop_at not in (None, "endTime", "nextWrite") or ctl.end_time is None:
        return
    start = start_value if start_value is not None else ctl.start_time
    if start is None:
        return
    run = ctl.end_time - start
    fmt = _number
    if run <= 0:
        # Only when continuing from results: a case whose endTime is its
        # start time 0 is a mesh or utility demo, not a finished run.
        if start <= 0:
            return
        findings.append(Finding(
            ALREADY_AT_END, WARNING, rel, ctl.lines.get("endTime", 0),
            {"start": fmt(start), "end": fmt(ctl.end_time)},
        ))
        return
    dt = ctl.delta_t
    if dt is not None and dt > 0 and not ctl.adjust_time_step and dt > run * (1 + 1e-9):
        findings.append(Finding(
            DELTA_T_EXCEEDS_RUN, WARNING, rel, ctl.lines.get("deltaT", 0),
            {"delta_t": fmt(dt), "run": fmt(run)},
        ))
        return
    if ctl.write_interval is None or ctl.write_interval <= 0:
        return
    if ctl.write_control == "timeStep":
        if ctl.delta_t is None or ctl.delta_t <= 0 or ctl.adjust_time_step:
            return
        steps = run / ctl.delta_t
        if steps * (1 + 1e-9) < ctl.write_interval <= steps * _DELIBERATE_NO_WRITE_RATIO:
            findings.append(Finding(
                NOTHING_WRITTEN, WARNING, rel, ctl.lines.get("writeInterval", 0),
                {"interval": fmt(ctl.write_interval), "unit": "steps", "run": fmt(steps)},
            ))
    elif ctl.write_control in _RUN_TIME_CONTROLS:
        if run * (1 + 1e-9) < ctl.write_interval <= run * _DELIBERATE_NO_WRITE_RATIO:
            findings.append(Finding(
                NOTHING_WRITTEN, WARNING, rel, ctl.lines.get("writeInterval", 0),
                {"interval": fmt(ctl.write_interval), "unit": "time", "run": fmt(run)},
            ))


def _number(value: float) -> str:
    return f"{value:g}"


# ── decomposeParDict ─────────────────────────────────────────────────────────

_GEOMETRIC_METHODS = frozenset({"simple", "hierarchical"})


def _check_decomposition(
    case_dir: str, read_text: ReadText | None, findings: list[Finding]
) -> None:
    path = os.path.join(case_dir, "system", "decomposeParDict")
    text = _read(path, read_text)
    if text is None:
        return
    root = _parse(text)
    if root is None:
        return
    rel = _rel(case_dir, path)
    var_map = build_var_map(root)
    count_node = find_child(root, "numberOfSubdomains")
    if count_node is None:
        return
    try:
        count_value = resolve_scalar(count_node, var_map)
    except (TypeError, ValueError):
        count_value = None
    if count_value is None or count_value != int(count_value) or count_value < 1:
        return
    count = int(count_value)

    method = _word(find_child(root, "decomposer")) or _word(find_child(root, "method"))
    if method in _GEOMETRIC_METHODS:
        # OpenCFD: <method>Coeffs, then coeffs, then the dictionary itself;
        # Foundation: <method>Coeffs, then the dictionary itself.
        coeffs = find_child(root, f"{method}Coeffs") or find_child(root, "coeffs") or root
        n_node = find_child(coeffs, "n")
        if n_node is not None:
            try:
                n = resolve_vector(n_node, var_map)
            except (TypeError, ValueError):
                n = None
            if n is not None and len(n) == 3 and all(v == int(v) and v > 0 for v in n):
                product = int(n[0]) * int(n[1]) * int(n[2])
                if product != count:
                    findings.append(Finding(
                        DECOMPOSITION_PRODUCT, ERROR, rel, n_node.source_line,
                        {"n": " ".join(str(int(v)) for v in n), "product": str(product),
                         "count": str(count), "method": method or ""},
                    ))

    pieces = decomposed_count(case_dir)
    if pieces is not None and pieces != count:
        findings.append(Finding(
            PROCESSOR_COUNT, WARNING, rel, count_node.source_line,
            {"count": str(count), "pieces": str(pieces)},
        ))


# ── dictionaries the solver reads ────────────────────────────────────────────

# (name every fork reads, Foundation's later name, the Foundation version
# that introduced it). Foundation still reads the old name as a fallback --
# physicalProperties.C and momentumTransportModel.C both try it -- while
# OpenCFD reads only the old one.
_TRANSPORT = ("transportProperties", "physicalProperties", 10)
_TURBULENCE = ("turbulenceProperties", "momentumTransport", 8)

# What the common incompressible solvers read from constant/. Kept to the
# solvers beginners start with, and measured: every v2606 and Foundation-12
# tutorial running one of them has the files listed (tests/services/
# test_case_check_corpus.py). Others are not judged.
SOLVER_DICTIONARIES: dict[str, tuple[tuple[str, str, int], ...]] = {
    "icoFoam": (_TRANSPORT,),
    "nonNewtonianIcoFoam": (_TRANSPORT,),
    "simpleFoam": (_TRANSPORT, _TURBULENCE),
    "pimpleFoam": (_TRANSPORT, _TURBULENCE),
    "pisoFoam": (_TRANSPORT, _TURBULENCE),
    "SRFSimpleFoam": (_TRANSPORT, _TURBULENCE),
    "SRFPimpleFoam": (_TRANSPORT, _TURBULENCE),
    "porousSimpleFoam": (_TRANSPORT, _TURBULENCE),
    # Foundation 11+ module, run by foamRun.
    "foamRun:incompressibleFluid": (_TRANSPORT, _TURBULENCE),
}


@dataclass(frozen=True)
class Installation:
    """Which OpenFOAM the case will run on, as far as it is known."""

    fork: str  # "opencfd" | "foundation"
    version: float  # v2606 -> 2606; Foundation 12 -> 12; dev -> inf


def installation_info(installation: str | None) -> Installation | None:
    """Fork and version from an installation's ``etc/bashrc``; None if unknown."""
    if not installation:
        return None
    try:
        with open(os.path.join(installation, "etc", "bashrc"), encoding="utf-8", errors="replace") as f:
            text = f.read(20_000)
    except OSError:
        return None
    m = re.search(r"^\s*(?:export\s+)?WM_PROJECT_VERSION=['\"]?([^'\"\s]+)", text, re.M)
    if not m:
        return None
    version = m.group(1)
    if re.fullmatch(r"v\d+", version):
        return Installation("opencfd", float(version[1:]))
    if re.fullmatch(r"\d+(\.\d+)?", version):
        return Installation("foundation", float(version))
    if version == "dev":
        return Installation("foundation", math.inf)
    return None


def _check_dictionaries(
    case_dir: str, ctl: _Control, inst: Installation | None, findings: list[Finding]
) -> None:
    key = ctl.application or ""
    if ctl.application == "foamRun" and ctl.module:
        key = f"foamRun:{ctl.module}"
    needed = SOLVER_DICTIONARIES.get(key)
    if not needed:
        return
    constant = os.path.join(case_dir, "constant")
    try:
        present = set(os.listdir(constant))
    except OSError:
        return  # no constant/ at all: an incomplete case a script assembles
    if not any(os.path.isfile(os.path.join(constant, n)) for n in present):
        return  # only triSurface/ & co.: a meshing demo, not set up to solve
    solver = ctl.module or ctl.application or ""
    for old, new, since in needed:
        has_old = old in present and os.path.isfile(os.path.join(constant, old))
        has_new = new in present and os.path.isfile(os.path.join(constant, new))
        if has_old:
            continue
        if any(n.startswith((old + ".", new + ".")) for n in present):
            # `turbulenceProperties.template`, `.orig`, …: a script writes the
            # real file from it (NACA4412), so its absence is by design.
            continue
        reads_new = inst is not None and inst.fork == "foundation" and inst.version >= since
        if has_new:
            if inst is not None and not reads_new:
                findings.append(Finding(
                    OTHER_FORK_DICTIONARY, ERROR, os.path.join("constant", new), 0,
                    {"have": new, "want": old, "solver": solver},
                ))
            continue
        if inst is None:
            want = f"{old} / {new}"
        else:
            want = new if reads_new else old
        findings.append(Finding(
            MISSING_DICTIONARY, ERROR, "constant", 0, {"name": want, "solver": solver},
        ))


# ── entry point ─────────────────────────────────────────────────────────────

def check_case(
    case_dir: str,
    *,
    read_text: ReadText | None = None,
    etc_dirs: Iterable[str | os.PathLike[str]] = (),
    installation: str | None = None,
) -> CaseCheck:
    """Run every check on *case_dir*.

    ``read_text(abs_path)`` serves an unsaved editor buffer (None: read the
    disk), so an edit counts before it is saved. ``etc_dirs`` is where
    ``#includeEtc`` looks; ``installation`` is the OpenFOAM root the case will
    run on, for the fork-aware dictionary check (None: unknown, and that
    check then reports only a dictionary missing under both names).
    """
    findings: list[Finding] = []
    skipped: list[Skip] = []
    etc = tuple(Path(d) for d in etc_dirs)

    control_path = os.path.join(case_dir, "system", "controlDict")
    control_text = _read(control_path, read_text)
    if control_text is None:
        findings.append(Finding(NO_CONTROL_DICT, ERROR, os.path.join("system", "controlDict")))
        return CaseCheck(tuple(findings), tuple(skipped))
    ctl = _read_control(control_text)

    start = _start_dir(case_dir, ctl)
    if start is None and not _time_dirs(case_dir):
        # Only with a 0.orig/ to restore from -- the tutorial convention a
        # copied case trips over. A case with no time directory at all is a
        # mesh demo or a solver that reads none (chemFoam), not a mistake.
        if os.path.isdir(os.path.join(case_dir, "0.orig")):
            findings.append(Finding(NO_START_DIR, ERROR, "0.orig"))
    elif start is not None:
        _check_boundaries(case_dir, start[1], read_text, etc, findings, skipped)

    _check_control(ctl, start[0] if start is not None else None, findings)
    _check_decomposition(case_dir, read_text, findings)
    _check_dictionaries(case_dir, ctl, installation_info(installation), findings)
    return CaseCheck(tuple(findings), tuple(skipped))
