# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from pathlib import Path


TARGET_FILES = [
    "system/blockMeshDict",
    "system/changeDictionaryDict",
    "system/controlDict",
    "system/createBafflesDict",
    "system/createPatchDict",
    "system/decomposeParDict",
    "system/extrudeMeshDict",
    "system/fvOptions",
    "system/fvSchemes",
    "system/fvSolution",
    "system/meshQualityDict",
    "system/mirrorMeshDict",
    "system/refineMeshDict",
    "system/setFieldsDict",
    "system/snappyHexMeshDict",
    "system/surfaceFeatureExtractDict",
    "system/topoSetDict",
    "constant/boundaryRadiationProperties",
    "constant/dynamicMeshDict",
    "constant/fvOptions",
    "constant/g",
    "constant/kinematicCloudProperties",
    "constant/radiationProperties",
    "constant/regionProperties",
    "constant/thermophysicalProperties",
    "constant/transportProperties",
    "constant/turbulenceProperties",
]

# Default files to look for inside each region's system/ subdirectory.
REGION_SYSTEM_FILES = [
    "changeDictionaryDict",
    "decomposeParDict",
    "fvOptions",
    "fvSchemes",
    "fvSolution",
    "meshQualityDict",
]

# Default files to look for inside each region's constant/ subdirectory.
REGION_CONSTANT_FILES = [
    "boundaryRadiationProperties",
    "dynamicMeshDict",
    "fvOptions",
    "radiationProperties",
    "thermophysicalProperties",
    "turbulenceProperties",
]

# Base names whose phase variants (e.g. thermophysicalProperties.air) are
# auto-collected from constant/ and constant/<region>/ by glob.
PHASE_FILE_BASES = [
    "thermophysicalProperties",
    "turbulenceProperties",
]

FIELD_DIRS = ("0", "0.orig")


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
    for rel_dir, recursive in (extra_dirs or []):
        d = base / rel_dir
        if not d.is_dir():
            continue
        if recursive:
            for path in sorted(d.rglob("*"), key=lambda p: (str(p.parent), p.name.lower())):
                if path.is_file():
                    _add(str(path))
        else:
            for path in sorted(d.iterdir(), key=lambda p: p.name.lower()):
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
    """Return absolute paths of all files directly inside case_dir/subdir/."""
    d = Path(case_dir) / subdir
    if not d.is_dir():
        return []
    return [
        str(p)
        for p in sorted(d.iterdir(), key=lambda p: p.name.lower())
        if p.is_file()
    ]
