# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import dataclasses
import re
from pathlib import Path

# Files offered for every case. Both forks are covered, so the list carries a
# name and its post-rename successor side by side: only one of each pair exists
# in a given case, and `list_case_files` skips whatever is absent. Foundation
# renamed constant/turbulenceProperties to constant/momentumTransport in v8,
# folded constant/transportProperties and constant/thermophysicalProperties into
# constant/physicalProperties in v10, and split fvOptions into constant/fvModels
# plus system/fvConstraints in v9 — measured across the OpenFOAM-7…dev and
# OpenCFD v2106…v2606 tutorial trees. Omitting a successor makes the file
# unreachable in the app, not merely unhelped: a name absent here is never
# listed, so a Foundation v10+ case showed no transport or thermophysical
# dictionary at all.
#
# Beyond the renames, the list is a measured sweep of the same trees: a name is
# here when it is a dictionary a user edits and it appears in at least four
# cases in at least one tree. Deliberately excluded are files that only look
# like dictionaries — Chemkin inputs (`constant/foam.inp`, `foam.dat`), READMEs
# — and numbered or templated variants of names already listed
# (`topoSetDict.1`, `blockMeshDict.m4`, `controlDict.orig`), which the Add
# files dialog covers. Some families are open-ended by nature: the Lagrangian
# clouds are named per case (`limestoneCloud1Properties` and friends), so only
# the common names are listed and the rest are added per case.
TARGET_FILES = [
    "system/blockMeshDict",
    "system/caseProperties",
    "system/changeDictionaryDict",
    "system/collapseDict",
    "system/columnAverage",
    "system/configDict",
    "system/controlDict",
    "system/createBafflesDict",
    "system/createNonConformalCouplesDict",
    "system/createPatchDict",
    "system/createZonesDict",
    "system/cuttingPlane",
    "system/decomposeParDict",
    "system/dsmcInitialiseDict",
    "system/extrudeMeshDict",
    "system/extrudeToRegionMeshDict",
    "system/faMeshDefinition",
    "system/faOptions",
    "system/faSchemes",
    "system/faSolution",
    "system/foamyHexMeshDict",
    "system/forceCoeffs",
    "system/functions",
    "system/fvConstraints",
    "system/fvOptions",
    "system/fvSchemes",
    "system/fvSolution",
    "system/mapFieldsDict",
    "system/mdEquilibrationDict",
    "system/mdInitialiseDict",
    "system/meshDict",
    "system/meshQualityDict",
    "system/mirrorMeshDict",
    "system/optimisationDict",
    "system/PDRblockMeshDict",
    "system/probes",
    "system/refineMeshDict",
    "system/residuals",
    "system/runTimePostProcessing",
    "system/sample",
    "system/sampling",
    "system/setAlphaFieldDict",
    "system/setFieldsDict",
    "system/setWavesDict",
    "system/singleGraph",
    "system/snappyHexMeshDict",
    "system/solverInfo",
    "system/streamLines",
    "system/streamlines",
    "system/subsetMeshDict",
    "system/surfaceFeatureExtractDict",
    "system/surfaceFeaturesDict",
    "system/surfaces",
    "system/topoSetDict",
    "system/vtkWrite",
    "constant/additionalControls",
    "constant/adjointRASProperties",
    "constant/boundaryRadiationProperties",
    "constant/chemistryProperties",
    "constant/cloudPositions",
    "constant/cloudProperties",
    "constant/combustionProperties",
    "constant/dsmcProperties",
    "constant/dynamicMeshDict",
    "constant/fvModels",
    "constant/fvOptions",
    "constant/g",
    "constant/heatTransfer",
    "constant/hRef",
    "constant/initialConditions",
    "constant/kinematicCloudPositions",
    "constant/kinematicCloudProperties",
    "constant/moleculeProperties",
    "constant/momentumTransfer",
    "constant/momentumTransport",
    "constant/motionProperties",
    "constant/MRFProperties",
    "constant/parcelInjectionProperties",
    "constant/particleTrackProperties",
    "constant/PDRProperties",
    "constant/phaseProperties",
    "constant/physicalProperties",
    "constant/porosityProperties",
    "constant/potentialDict",
    "constant/pRef",
    "constant/pyrolysisZones",
    "constant/radiationProperties",
    "constant/reactingCloud1Positions",
    "constant/reactingCloud1Properties",
    "constant/reactionProperties",
    "constant/reactions",
    "constant/reactionsGRI",
    "constant/regionProperties",
    "constant/speciesThermo",
    "constant/sprayCloudProperties",
    "constant/surfaceFilmProperties",
    "constant/thermo",
    "constant/thermodynamicProperties",
    "constant/thermophysicalProperties",
    "constant/thermophysicalTransport",
    "constant/transportProperties",
    "constant/turbulenceProperties",
    "constant/viewFactorsDict",
    "constant/waveProperties",
    "constant/zonesGenerator",
]

# Default files to look for inside each region's system/ subdirectory. Shorter
# than TARGET_FILES on purpose: this is what a multi-region case actually splits
# per region, measured the same way. The finite-area trio and faOptions appear
# only here — OpenCFD's tutorials put them under system/<region>/, not at the
# case root.
REGION_SYSTEM_FILES = [
    "blockMeshDict",
    "caseProperties",
    "changeDictionaryDict",
    "createBafflesDict",
    "createPatchDict",
    "decomposeParDict",
    "extrudeToRegionMeshDict",
    "faMeshDefinition",
    "faOptions",
    "faSchemes",
    "faSolution",
    "fvConstraints",
    "fvOptions",
    "fvSchemes",
    "fvSolution",
    "meshQualityDict",
    "setFieldsDict",
    "topoSetDict",
]

# Default files to look for inside each region's constant/ subdirectory.
REGION_CONSTANT_FILES = [
    "boundaryRadiationProperties",
    "chemistryProperties",
    "cloudProperties",
    "dynamicMeshDict",
    "fvModels",
    "fvOptions",
    "g",
    "momentumTransport",
    "parcelInjectionProperties",
    "phaseProperties",
    "physicalProperties",
    "pRef",
    "radiationProperties",
    "reactions",
    "speciesThermo",
    "thermo",
    "thermophysicalProperties",
    "thermophysicalTransport",
    "turbulenceProperties",
    "viewFactorsDict",
]

# Base names whose phase variants (e.g. thermophysicalProperties.air) are
# auto-collected from constant/ and constant/<region>/ by glob. Foundation's
# multiphase cases spell the same variants as momentumTransport.air /
# physicalProperties.water, so both successors need an entry here too, and the
# thermo/reaction data files are suffixed the same way (thermo.compressibleGas,
# reactions.vapour). The glob needs a literal dot, so "thermo" here does not
# also collect thermophysicalProperties.
PHASE_FILE_BASES = [
    "momentumTransport",
    "physicalProperties",
    "reactions",
    "reactionsGRI",
    "thermo",
    "thermophysicalProperties",
    "thermophysicalTransport",
    "turbulenceProperties",
]

FIELD_DIRS = ("0", "0.orig")

# Case-root script files (Allrun, Allrun.pre, Allclean, …) are auto-listed so
# the scripts run from the Tools menu can be inspected/edited in the app.
ROOT_SCRIPT_GLOB = "All*"


def detect_regions(case_dir: str) -> list[str]:
    """Return sorted region names when system/ contains subdirectories, else []."""
    system_dir = Path(case_dir) / "system"
    if not system_dir.is_dir():
        return []
    return sorted(d.name for d in system_dir.iterdir() if d.is_dir())


def list_region_files(case_dir: str, regions: list[str]) -> list[str]:
    """Return default target file paths for all regions (only files that exist)."""
    base = Path(case_dir)
    result: list[str] = []
    for region in regions:
        for fname in REGION_SYSTEM_FILES:
            p = base / "system" / region / fname
            if p.is_file():
                result.append(str(p))
        for fname in REGION_CONSTANT_FILES:
            p = base / "constant" / region / fname
            if p.is_file():
                result.append(str(p))
    return result


def _list_phase_files(case_dir: str, subdir: str) -> list[str]:
    """Return files matching '<stem>.*' patterns in case_dir/subdir/."""
    d = Path(case_dir) / subdir
    if not d.is_dir():
        return []
    return [
        str(f)
        for stem in PHASE_FILE_BASES
        for f in sorted(d.glob(f"{stem}.*"), key=lambda p: p.name.lower())
        if f.is_file()
    ]


def detect_time_dirs(case_dir: str, extra_dirs: list[str] | None = None) -> list[str]:
    """Return numeric time directories at the case root, sorted ascending.

    Excludes FIELD_DIRS and any directories already listed in extra_dirs (those
    appear as full group headers rather than in the Results indicator).
    """
    base = Path(case_dir)
    if not base.is_dir():
        return []
    excluded = set(FIELD_DIRS) | set(extra_dirs or [])
    dirs: list[tuple[float, str]] = []
    for d in base.iterdir():
        if not d.is_dir() or d.name in excluded:
            continue
        try:
            dirs.append((float(d.name), d.name))
        except ValueError:
            continue
    return [name for _, name in sorted(dirs)]


@dataclasses.dataclass
class PolyMeshInfo:
    """Cheap summary of constant/polyMesh/, parsed from the owner file header."""

    n_points: int | None
    n_cells: int | None
    n_faces: int | None
    stale: bool  # blockMeshDict mtime > constant/polyMesh/owner mtime


_OWNER_NOTE_RE = re.compile(r"nPoints:(\d+)\s+nCells:(\d+)\s+nFaces:(\d+)")


def detect_poly_mesh(case_dir: str) -> PolyMeshInfo | None:
    """Return a PolyMeshInfo if constant/polyMesh/owner exists, else None.

    Counts come from the owner file's FoamFile header `note` field (e.g.
    "nPoints:9261  nCells:8000  nFaces:25200  nInternalFaces:22800") rather
    than parsing the mesh itself, so this stays a cheap, no-dependency check.
    """
    owner = Path(case_dir) / "constant" / "polyMesh" / "owner"
    if not owner.is_file():
        return None
    try:
        header = owner.read_text(errors="replace")[:2000]
    except OSError:
        header = ""
    match = _OWNER_NOTE_RE.search(header)
    n_points: int | None
    n_cells: int | None
    n_faces: int | None
    if match:
        n_points, n_cells, n_faces = (int(g) for g in match.groups())
    else:
        n_points = n_cells = n_faces = None
    stale = False
    dict_path = Path(case_dir) / "system" / "blockMeshDict"
    try:
        if dict_path.is_file():
            stale = dict_path.stat().st_mtime > owner.stat().st_mtime
    except OSError:
        pass
    return PolyMeshInfo(n_points=n_points, n_cells=n_cells, n_faces=n_faces, stale=stale)


def is_openfoam_case(directory: str) -> bool:
    """Return True if directory contains at least one of 'system' or 'constant'."""
    base = Path(directory)
    return (base / "system").is_dir() or (base / "constant").is_dir()


def list_case_files(
    case_dir: str,
    extra_files: list[str] | None = None,
    extra_dirs: list[tuple[str, bool]] | None = None,
) -> list[str]:
    base = Path(case_dir)
    result: list[str] = []
    seen: set[str] = set()

    def _add(s: str) -> None:
        if s not in seen:
            result.append(s)
            seen.add(s)

    targets = list(TARGET_FILES) + (extra_files or [])

    for rel in targets:
        path = base / rel
        if path.is_file():
            _add(str(path))

    # Phase variant files in constant/ (e.g. thermophysicalProperties.air)
    for s in _list_phase_files(case_dir, "constant"):
        _add(s)

    # Field directories (0/, 0.orig/) — direct files and one level of region subdirs
    for dir_name in FIELD_DIRS:
        field_dir = base / dir_name
        if not field_dir.is_dir():
            continue
        for path in sorted(field_dir.iterdir(), key=lambda p: p.name.lower()):
            if path.is_file():
                _add(str(path))
            elif path.is_dir():
                for sub_path in sorted(path.iterdir(), key=lambda p: p.name.lower()):
                    if sub_path.is_file():
                        _add(str(sub_path))

    # Extra directories: flat or recursive scan depending on the flag.
    # Hidden entries (dotfiles like .foam-editor-files.json, dirs like .git/)
    # are always skipped — the app's own config must not become editable.
    for rel_dir, recursive in (extra_dirs or []):
        d = base / rel_dir
        if not d.is_dir():
            continue
        if recursive:
            for path in sorted(d.rglob("*"), key=lambda p: (str(p.parent), p.name.lower())):
                if any(part.startswith(".") for part in path.relative_to(d).parts):
                    continue
                if path.is_file():
                    _add(str(path))
        else:
            for path in sorted(d.iterdir(), key=lambda p: p.name.lower()):
                if path.is_file() and not path.name.startswith("."):
                    _add(str(path))

    # Case-root scripts (Allrun, Allclean, …)
    for path in sorted(base.glob(ROOT_SCRIPT_GLOB), key=lambda p: p.name.lower()):
        if path.is_file():
            _add(str(path))

    # MultiRegion: region target files and their phase variants
    regions = detect_regions(case_dir)
    for s in list_region_files(case_dir, regions):
        _add(s)
    for region in regions:
        for s in _list_phase_files(case_dir, f"constant/{region}"):
            _add(s)

    return result


def list_directory_files(case_dir: str, subdir: str) -> list[str]:
    """Return absolute paths of all non-hidden files directly inside case_dir/subdir/."""
    d = Path(case_dir) / subdir
    if not d.is_dir():
        return []
    return [
        str(p)
        for p in sorted(d.iterdir(), key=lambda p: p.name.lower())
        if p.is_file() and not p.name.startswith(".")
    ]
