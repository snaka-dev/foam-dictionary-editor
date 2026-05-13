# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from services.case_loader import is_openfoam_case, list_case_files, list_directory_files, detect_time_dirs


def test_list_case_files(tmp_path):  # legacy top-level test kept for compatibility
    (tmp_path / "system").mkdir()
    (tmp_path / "constant").mkdir()

    (tmp_path / "system" / "controlDict").write_text("application interFoam;", encoding="utf-8")
    (tmp_path / "system" / "fvSchemes").write_text("ddtSchemes { default Euler; }", encoding="utf-8")
    (tmp_path / "constant" / "transportProperties").write_text("transportModel Newtonian;", encoding="utf-8")

    files = list_case_files(str(tmp_path))

    assert str(tmp_path / "system" / "controlDict") in files
    assert str(tmp_path / "system" / "fvSchemes") in files
    assert str(tmp_path / "constant" / "transportProperties") in files


import pytest
from pathlib import Path
from services.case_loader import (
    list_case_files,
    list_directory_files,
    detect_regions,
    detect_time_dirs,
    list_region_files,
    TARGET_FILES,
    FIELD_DIRS,
    REGION_SYSTEM_FILES,
    REGION_CONSTANT_FILES,
    PHASE_FILE_BASES,
)


# ── TARGET_FILES: files that exist are returned ───────────────────────────────

class TestTargetFiles:
    def test_target_file_included_when_exists(self, tmp_path):
        """An existing file defined in TARGET_FILES is included in the result"""
        (tmp_path / "system").mkdir()
        (tmp_path / "system" / "blockMeshDict").write_text("FoamFile{}", encoding="utf-8")
        files = list_case_files(str(tmp_path))
        assert str(tmp_path / "system" / "blockMeshDict") in files

    def test_target_file_not_included_when_missing(self, tmp_path):
        """A file defined in TARGET_FILES but absent on disk is not included"""
        (tmp_path / "system").mkdir()
        # do not create blockMeshDict
        files = list_case_files(str(tmp_path))
        assert str(tmp_path / "system" / "blockMeshDict") not in files

    def test_all_existing_target_files_are_included(self, tmp_path):
        """All existing TARGET_FILES are included when multiple files are present"""
        (tmp_path / "system").mkdir()
        (tmp_path / "constant").mkdir()
        (tmp_path / "system" / "fvSchemes").write_text("", encoding="utf-8")
        (tmp_path / "system" / "fvSolution").write_text("", encoding="utf-8")
        (tmp_path / "constant" / "transportProperties").write_text("", encoding="utf-8")
        files = list_case_files(str(tmp_path))
        assert str(tmp_path / "system" / "fvSchemes") in files
        assert str(tmp_path / "system" / "fvSolution") in files
        assert str(tmp_path / "constant" / "transportProperties") in files

    def test_empty_case_returns_empty_list(self, tmp_path):
        """An empty case directory returns an empty list"""
        files = list_case_files(str(tmp_path))
        assert files == []


# ── FIELD_DIRS: field files under 0/ and 0.orig/ ─────────────────────────────

class TestFieldDirs:
    def test_field_files_in_0_dir_are_included(self, tmp_path):
        """Files in the 0/ directory are included"""
        field_dir = tmp_path / "0"
        field_dir.mkdir()
        (field_dir / "U").write_text("", encoding="utf-8")
        (field_dir / "p").write_text("", encoding="utf-8")
        files = list_case_files(str(tmp_path))
        assert str(field_dir / "U") in files
        assert str(field_dir / "p") in files

    def test_field_files_in_0_orig_dir_are_included(self, tmp_path):
        """Files in the 0.orig/ directory are included"""
        field_dir = tmp_path / "0.orig"
        field_dir.mkdir()
        (field_dir / "T").write_text("", encoding="utf-8")
        files = list_case_files(str(tmp_path))
        assert str(field_dir / "T") in files

    def test_field_dir_not_exist_does_not_raise(self, tmp_path):
        """Missing 0/ or 0.orig/ directories do not raise an error"""
        files = list_case_files(str(tmp_path))
        assert isinstance(files, list)

    def test_field_files_sorted_alphabetically(self, tmp_path):
        """Field files in 0/ are sorted alphabetically"""
        field_dir = tmp_path / "0"
        field_dir.mkdir()
        for name in ["p_rgh", "alpha.water", "U", "T"]:
            (field_dir / name).write_text("", encoding="utf-8")
        files = list_case_files(str(tmp_path))
        field_files = [f for f in files if str(field_dir) in f]
        names = [Path(f).name for f in field_files]
        assert names == sorted(names, key=lambda n: n.lower())

    def test_subdirectory_inside_field_dir_is_excluded(self, tmp_path):
        """Subdirectories inside 0/ are not included"""
        field_dir = tmp_path / "0"
        field_dir.mkdir()
        subdir = field_dir / "subdir"
        subdir.mkdir()
        (field_dir / "p").write_text("", encoding="utf-8")
        files = list_case_files(str(tmp_path))
        assert str(subdir) not in files
        assert str(field_dir / "p") in files

    def test_both_0_and_0_orig_files_included(self, tmp_path):
        """Files from both 0/ and 0.orig/ are included when both directories exist"""
        (tmp_path / "0").mkdir()
        (tmp_path / "0.orig").mkdir()
        (tmp_path / "0" / "U").write_text("", encoding="utf-8")
        (tmp_path / "0.orig" / "U").write_text("", encoding="utf-8")
        files = list_case_files(str(tmp_path))
        assert str(tmp_path / "0" / "U") in files
        assert str(tmp_path / "0.orig" / "U") in files


# ── Combined: TARGET_FILES and FIELD_DIRS together ────────────────────────────

class TestCombined:
    def test_target_files_and_field_files_coexist(self, tmp_path):
        """Both target files and field files are included together"""
        (tmp_path / "system").mkdir()
        (tmp_path / "constant").mkdir()
        (tmp_path / "0").mkdir()
        (tmp_path / "system" / "controlDict").write_text("", encoding="utf-8")
        (tmp_path / "constant" / "g").write_text("", encoding="utf-8")
        (tmp_path / "0" / "p").write_text("", encoding="utf-8")
        files = list_case_files(str(tmp_path))
        assert str(tmp_path / "system" / "controlDict") in files
        assert str(tmp_path / "constant" / "g") in files
        assert str(tmp_path / "0" / "p") in files

    def test_unrelated_files_not_included(self, tmp_path):
        """Files not matching TARGET_FILES or FIELD_DIRS are excluded"""
        (tmp_path / "system").mkdir()
        (tmp_path / "system" / "unknownFile").write_text("", encoding="utf-8")
        files = list_case_files(str(tmp_path))
        assert str(tmp_path / "system" / "unknownFile") not in files

    def test_returns_list_type(self, tmp_path):
        """The return value is always a list"""
        result = list_case_files(str(tmp_path))
        assert isinstance(result, list)

    def test_no_duplicates_in_result(self, tmp_path):
        """The result list contains no duplicates"""
        (tmp_path / "system").mkdir()
        (tmp_path / "system" / "fvSchemes").write_text("", encoding="utf-8")
        (tmp_path / "0").mkdir()
        (tmp_path / "0" / "U").write_text("", encoding="utf-8")
        files = list_case_files(str(tmp_path))
        assert len(files) == len(set(files))


# ── Constants: validate TARGET_FILES and FIELD_DIRS values ───────────────────

class TestConstants:
    def test_target_files_contains_key_dicts(self):
        """TARGET_FILES contains the key dictionary files"""
        assert "system/controlDict" in TARGET_FILES
        assert "system/fvSchemes" in TARGET_FILES
        assert "system/fvSolution" in TARGET_FILES
        assert "constant/transportProperties" in TARGET_FILES

    def test_field_dirs_contains_0_and_0_orig(self):
        """FIELD_DIRS contains '0' and '0.orig'"""
        assert "0" in FIELD_DIRS
        assert "0.orig" in FIELD_DIRS

    def test_target_files_all_have_subdir(self):
        """Every entry in TARGET_FILES has a subdirectory prefix"""
        for entry in TARGET_FILES:
            assert "/" in entry, f"'{entry}' must include a subdirectory prefix"

    def test_target_files_no_duplicates(self):
        """TARGET_FILES has no duplicate entries"""
        assert len(TARGET_FILES) == len(set(TARGET_FILES))

    def test_target_files_contains_new_system_entries(self):
        """TARGET_FILES contains newly added system dictionary files"""
        assert "system/snappyHexMeshDict" in TARGET_FILES
        assert "system/surfaceFeatureExtractDict" in TARGET_FILES
        assert "system/fvOptions" in TARGET_FILES
        assert "system/createBafflesDict" in TARGET_FILES

    def test_target_files_contains_new_constant_entries(self):
        """TARGET_FILES contains newly added constant dictionary files"""
        assert "constant/thermophysicalProperties" in TARGET_FILES
        assert "constant/dynamicMeshDict" in TARGET_FILES
        assert "constant/kinematicCloudProperties" in TARGET_FILES
        assert "constant/regionProperties" in TARGET_FILES


class TestIsOpenfoamCase:
    def test_both_dirs_present(self, tmp_path):
        (tmp_path / "system").mkdir()
        (tmp_path / "constant").mkdir()
        assert is_openfoam_case(str(tmp_path)) is True

    def test_only_system_present(self, tmp_path):
        (tmp_path / "system").mkdir()
        assert is_openfoam_case(str(tmp_path)) is True

    def test_only_constant_present(self, tmp_path):
        (tmp_path / "constant").mkdir()
        assert is_openfoam_case(str(tmp_path)) is True

    def test_neither_dir_present(self, tmp_path):
        assert is_openfoam_case(str(tmp_path)) is False

    def test_system_file_not_dir(self, tmp_path):
        (tmp_path / "system").write_text("not a dir", encoding="utf-8")
        assert is_openfoam_case(str(tmp_path)) is False

    def test_empty_directory(self, tmp_path):
        assert is_openfoam_case(str(tmp_path)) is False


# ── extra_files: user-specified additional files ──────────────────────────────

class TestExtraFiles:
    def test_extra_file_included_when_exists(self, tmp_path):
        """An extra file on disk is included when passed via extra_files"""
        (tmp_path / "system").mkdir()
        (tmp_path / "system" / "myCustomDict").write_text("", encoding="utf-8")
        files = list_case_files(str(tmp_path), extra_files=["system/myCustomDict"])
        assert str(tmp_path / "system" / "myCustomDict") in files

    def test_extra_file_not_included_when_missing(self, tmp_path):
        """An extra file absent on disk is not included even if listed"""
        (tmp_path / "system").mkdir()
        files = list_case_files(str(tmp_path), extra_files=["system/myCustomDict"])
        assert str(tmp_path / "system" / "myCustomDict") not in files

    def test_extra_file_not_duplicated_if_already_in_target(self, tmp_path):
        """Passing a TARGET_FILES entry as extra_files does not produce a duplicate"""
        (tmp_path / "system").mkdir()
        (tmp_path / "system" / "controlDict").write_text("", encoding="utf-8")
        files = list_case_files(str(tmp_path), extra_files=["system/controlDict"])
        assert files.count(str(tmp_path / "system" / "controlDict")) == 1

    def test_none_extra_files_behaves_like_no_extras(self, tmp_path):
        """Passing extra_files=None gives the same result as not passing it"""
        (tmp_path / "system").mkdir()
        (tmp_path / "system" / "controlDict").write_text("", encoding="utf-8")
        assert list_case_files(str(tmp_path)) == list_case_files(str(tmp_path), extra_files=None)

    def test_multiple_extra_files(self, tmp_path):
        """Multiple extra files are all included when they exist"""
        (tmp_path / "system").mkdir()
        (tmp_path / "system" / "dictA").write_text("", encoding="utf-8")
        (tmp_path / "system" / "dictB").write_text("", encoding="utf-8")
        files = list_case_files(str(tmp_path), extra_files=["system/dictA", "system/dictB"])
        assert str(tmp_path / "system" / "dictA") in files
        assert str(tmp_path / "system" / "dictB") in files


# ── list_directory_files ──────────────────────────────────────────────────────

class TestListDirectoryFiles:
    def test_returns_files_in_subdir(self, tmp_path):
        """Returns absolute paths of files directly inside the subdirectory"""
        (tmp_path / "system").mkdir()
        (tmp_path / "system" / "controlDict").write_text("", encoding="utf-8")
        (tmp_path / "system" / "fvSchemes").write_text("", encoding="utf-8")
        result = list_directory_files(str(tmp_path), "system")
        assert str(tmp_path / "system" / "controlDict") in result
        assert str(tmp_path / "system" / "fvSchemes") in result

    def test_missing_subdir_returns_empty(self, tmp_path):
        """Returns an empty list when the subdirectory does not exist"""
        assert list_directory_files(str(tmp_path), "nonexistent") == []

    def test_subdirectories_excluded(self, tmp_path):
        """Subdirectories inside the scanned directory are not returned"""
        (tmp_path / "system").mkdir()
        (tmp_path / "system" / "nested").mkdir()
        (tmp_path / "system" / "controlDict").write_text("", encoding="utf-8")
        result = list_directory_files(str(tmp_path), "system")
        assert str(tmp_path / "system" / "nested") not in result

    def test_results_sorted_alphabetically(self, tmp_path):
        """Results are sorted alphabetically by file name (case-insensitive)"""
        (tmp_path / "system").mkdir()
        for name in ["zFile", "aFile", "MFile"]:
            (tmp_path / "system" / name).write_text("", encoding="utf-8")
        result = list_directory_files(str(tmp_path), "system")
        names = [Path(f).name for f in result]
        assert names == sorted(names, key=str.lower)


# ── detect_regions ────────────────────────────────────────────────────────────

class TestDetectRegions:
    def test_no_regions_in_single_region_case(self, tmp_path):
        (tmp_path / "system").mkdir()
        (tmp_path / "system" / "controlDict").write_text("", encoding="utf-8")
        assert detect_regions(str(tmp_path)) == []

    def test_detects_region_subdirs(self, tmp_path):
        (tmp_path / "system").mkdir()
        (tmp_path / "system" / "region1").mkdir()
        (tmp_path / "system" / "region2").mkdir()
        regions = detect_regions(str(tmp_path))
        assert "region1" in regions
        assert "region2" in regions

    def test_regions_sorted(self, tmp_path):
        (tmp_path / "system").mkdir()
        (tmp_path / "system" / "water").mkdir()
        (tmp_path / "system" / "air").mkdir()
        assert detect_regions(str(tmp_path)) == ["air", "water"]

    def test_no_system_dir_returns_empty(self, tmp_path):
        assert detect_regions(str(tmp_path)) == []

    def test_files_in_system_not_counted_as_regions(self, tmp_path):
        (tmp_path / "system").mkdir()
        (tmp_path / "system" / "controlDict").write_text("", encoding="utf-8")
        assert detect_regions(str(tmp_path)) == []


# ── list_region_files ─────────────────────────────────────────────────────────

class TestListRegionFiles:
    def _make_region(self, tmp_path, region: str):
        (tmp_path / "system" / region).mkdir(parents=True)
        (tmp_path / "constant" / region).mkdir(parents=True)
        (tmp_path / "system" / region / "fvSchemes").write_text("", encoding="utf-8")
        (tmp_path / "system" / region / "fvSolution").write_text("", encoding="utf-8")
        (tmp_path / "constant" / region / "thermophysicalProperties").write_text("", encoding="utf-8")
        (tmp_path / "constant" / region / "turbulenceProperties").write_text("", encoding="utf-8")

    def test_returns_existing_region_files(self, tmp_path):
        self._make_region(tmp_path, "fluid")
        files = list_region_files(str(tmp_path), ["fluid"])
        assert str(tmp_path / "system" / "fluid" / "fvSchemes") in files
        assert str(tmp_path / "constant" / "fluid" / "thermophysicalProperties") in files

    def test_missing_files_not_included(self, tmp_path):
        (tmp_path / "system" / "fluid").mkdir(parents=True)
        (tmp_path / "constant" / "fluid").mkdir(parents=True)
        (tmp_path / "system" / "fluid" / "fvSchemes").write_text("", encoding="utf-8")
        files = list_region_files(str(tmp_path), ["fluid"])
        assert str(tmp_path / "system" / "fluid" / "fvSolution") not in files

    def test_multiple_regions(self, tmp_path):
        self._make_region(tmp_path, "region1")
        self._make_region(tmp_path, "region2")
        files = list_region_files(str(tmp_path), ["region1", "region2"])
        assert str(tmp_path / "system" / "region1" / "fvSchemes") in files
        assert str(tmp_path / "system" / "region2" / "fvSchemes") in files

    def test_empty_regions_list(self, tmp_path):
        assert list_region_files(str(tmp_path), []) == []

    def test_region_system_files_contains_decompose(self):
        assert "decomposeParDict" in REGION_SYSTEM_FILES

    def test_region_constant_files_defined(self):
        assert "thermophysicalProperties" in REGION_CONSTANT_FILES
        assert "turbulenceProperties" in REGION_CONSTANT_FILES


# ── phase files (_list_phase_files via list_case_files) ───────────────────────

class TestPhaseFiles:
    def test_phase_variants_included(self, tmp_path):
        (tmp_path / "constant").mkdir()
        (tmp_path / "constant" / "thermophysicalProperties").write_text("", encoding="utf-8")
        (tmp_path / "constant" / "thermophysicalProperties.air").write_text("", encoding="utf-8")
        (tmp_path / "constant" / "thermophysicalProperties.liquid").write_text("", encoding="utf-8")
        files = list_case_files(str(tmp_path))
        assert str(tmp_path / "constant" / "thermophysicalProperties.air") in files
        assert str(tmp_path / "constant" / "thermophysicalProperties.liquid") in files

    def test_phase_file_not_duplicated_with_base(self, tmp_path):
        (tmp_path / "constant").mkdir()
        (tmp_path / "constant" / "thermophysicalProperties").write_text("", encoding="utf-8")
        (tmp_path / "constant" / "thermophysicalProperties.air").write_text("", encoding="utf-8")
        files = list_case_files(str(tmp_path))
        assert files.count(str(tmp_path / "constant" / "thermophysicalProperties")) == 1

    def test_turbulence_properties_phase_variants(self, tmp_path):
        (tmp_path / "constant").mkdir()
        (tmp_path / "constant" / "turbulenceProperties.gas").write_text("", encoding="utf-8")
        files = list_case_files(str(tmp_path))
        assert str(tmp_path / "constant" / "turbulenceProperties.gas") in files

    def test_unrelated_dot_files_not_included(self, tmp_path):
        (tmp_path / "constant").mkdir()
        (tmp_path / "constant" / "someOtherDict.air").write_text("", encoding="utf-8")
        files = list_case_files(str(tmp_path))
        assert str(tmp_path / "constant" / "someOtherDict.air") not in files

    def test_phase_file_bases_defined(self):
        assert "thermophysicalProperties" in PHASE_FILE_BASES
        assert "turbulenceProperties" in PHASE_FILE_BASES


# ── list_case_files: multiRegion ──────────────────────────────────────────────

class TestMultiRegionCaseFiles:
    def _make_multiregion_case(self, tmp_path):
        """Create a minimal chtMultiRegionFoam-like case structure."""
        (tmp_path / "system").mkdir()
        (tmp_path / "constant").mkdir()
        (tmp_path / "system" / "controlDict").write_text("", encoding="utf-8")
        for region in ("fluid", "solid"):
            (tmp_path / "system" / region).mkdir()
            (tmp_path / "constant" / region).mkdir()
            (tmp_path / "system" / region / "fvSchemes").write_text("", encoding="utf-8")
            (tmp_path / "system" / region / "fvSolution").write_text("", encoding="utf-8")
            (tmp_path / "constant" / region / "thermophysicalProperties").write_text("", encoding="utf-8")
            (tmp_path / "constant" / region / "turbulenceProperties").write_text("", encoding="utf-8")
        (tmp_path / "constant" / "regionProperties").write_text("", encoding="utf-8")

    def test_multiregion_files_included(self, tmp_path):
        self._make_multiregion_case(tmp_path)
        files = list_case_files(str(tmp_path))
        assert str(tmp_path / "system" / "fluid" / "fvSchemes") in files
        assert str(tmp_path / "system" / "solid" / "fvSchemes") in files
        assert str(tmp_path / "constant" / "fluid" / "thermophysicalProperties") in files

    def test_multiregion_phase_files_included(self, tmp_path):
        self._make_multiregion_case(tmp_path)
        (tmp_path / "constant" / "fluid" / "thermophysicalProperties.liquid").write_text("", encoding="utf-8")
        files = list_case_files(str(tmp_path))
        assert str(tmp_path / "constant" / "fluid" / "thermophysicalProperties.liquid") in files

    def test_multiregion_no_duplicates(self, tmp_path):
        self._make_multiregion_case(tmp_path)
        files = list_case_files(str(tmp_path))
        assert len(files) == len(set(files))

    def test_single_region_case_unaffected(self, tmp_path):
        (tmp_path / "system").mkdir()
        (tmp_path / "system" / "controlDict").write_text("", encoding="utf-8")
        files = list_case_files(str(tmp_path))
        assert str(tmp_path / "system" / "controlDict") in files


# ── detect_time_dirs ──────────────────────────────────────────────────────────

class TestDetectTimeDirs:
    def test_returns_empty_for_empty_case(self, tmp_path):
        """No numeric directories → empty list."""
        assert detect_time_dirs(str(tmp_path)) == []

    def test_returns_empty_for_missing_case(self, tmp_path):
        """Non-existent directory does not raise and returns empty list."""
        assert detect_time_dirs(str(tmp_path / "does_not_exist")) == []

    def test_detects_integer_time_dirs(self, tmp_path):
        """Integer-named directories such as '1' and '2' are returned."""
        (tmp_path / "1").mkdir()
        (tmp_path / "2").mkdir()
        result = detect_time_dirs(str(tmp_path))
        assert "1" in result
        assert "2" in result

    def test_detects_float_time_dirs(self, tmp_path):
        """Float-named directories such as '0.5' and '1.5' are returned."""
        (tmp_path / "0.5").mkdir()
        (tmp_path / "1.5").mkdir()
        result = detect_time_dirs(str(tmp_path))
        assert "0.5" in result
        assert "1.5" in result

    def test_excludes_0_and_0_orig(self, tmp_path):
        """'0' and '0.orig' are excluded because they are FIELD_DIRS."""
        (tmp_path / "0").mkdir()
        (tmp_path / "0.orig").mkdir()
        (tmp_path / "1").mkdir()
        result = detect_time_dirs(str(tmp_path))
        assert "0" not in result
        assert "0.orig" not in result
        assert "1" in result

    def test_excludes_non_numeric_dirs(self, tmp_path):
        """Non-numeric directories like 'system' and 'constant' are excluded."""
        (tmp_path / "system").mkdir()
        (tmp_path / "constant").mkdir()
        (tmp_path / "processor0").mkdir()
        (tmp_path / "1").mkdir()
        result = detect_time_dirs(str(tmp_path))
        assert "system" not in result
        assert "constant" not in result
        assert "processor0" not in result
        assert "1" in result

    def test_sorted_numerically(self, tmp_path):
        """Results are sorted in ascending numeric order."""
        for name in ("10", "0.5", "1", "100"):
            (tmp_path / name).mkdir()
        result = detect_time_dirs(str(tmp_path))
        assert result == ["0.5", "1", "10", "100"]

    def test_files_not_treated_as_dirs(self, tmp_path):
        """A file named with a number is not included (only directories)."""
        (tmp_path / "1").write_text("", encoding="utf-8")
        assert "1" not in detect_time_dirs(str(tmp_path))

    def test_returns_only_names_not_paths(self, tmp_path):
        """Returns bare directory names, not absolute paths."""
        (tmp_path / "2").mkdir()
        result = detect_time_dirs(str(tmp_path))
        assert result == ["2"]
        assert "/" not in result[0]
