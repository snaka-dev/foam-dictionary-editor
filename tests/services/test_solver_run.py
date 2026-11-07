# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for services/solver_run.py (Run Solver / Run decomposePar inspection)."""
from __future__ import annotations

import os

import pytest

from services.solver_run import (
    SolverInfo,
    decomposed_count,
    has_mesh,
    is_valid_log_suffix,
    is_valid_solver_name,
    keep_log_prefix,
    next_part_suffix,
    processor_dirs,
    read_solver_info,
    read_subdomain_count,
    stale_decomposition,
    unreconstructed_times,
)


class TestReadSolverInfo:
    def test_classic_application(self):
        info = read_solver_info(
            "application simpleFoam;\nstartFrom startTime;\nstartTime 0;\n"
        )
        assert info == SolverInfo(
            application="simpleFoam", start_from="startTime", start_time="0"
        )

    def test_foam_run_module(self):
        info = read_solver_info("application foamRun;\nsolver incompressibleFluid;\n")
        assert info.application == "foamRun"
        assert info.module == "incompressibleFluid"

    def test_solver_entry_ignored_without_foam_run(self):
        # Only foamRun gives `solver` that meaning.
        assert read_solver_info("application icoFoam;\nsolver x;\n").module is None

    def test_foam_multi_run_regions(self):
        info = read_solver_info(
            "application foamMultiRun;\n"
            "regionSolvers { fluid fluid; solid solid; }\n"
        )
        assert info.region_modules == (("fluid", "fluid"), ("solid", "solid"))

    def test_quoted_application(self):
        assert read_solver_info('application "pimpleFoam";').application == "pimpleFoam"

    def test_missing_application(self):
        assert read_solver_info("startFrom latestTime;\n").application is None

    def test_unparseable_text_is_unknown(self):
        assert read_solver_info("application {{{ ;;; ((") == SolverInfo()
        assert read_solver_info("") == SolverInfo()


class TestSubdomainCount:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("numberOfSubdomains 4;\nmethod scotch;\n", 4),
            ("numberOfSubdomains 0;\n", None),
            ("numberOfSubdomains $n;\n", None),
            ("method scotch;\n", None),
        ],
    )
    def test_count(self, text, expected):
        assert read_subdomain_count(text) == expected


class TestSolverName:
    @pytest.mark.parametrize("name", ["simpleFoam", "foamRun", "my_solver-2", "a.b+c"])
    def test_valid(self, name):
        assert is_valid_solver_name(name)

    @pytest.mark.parametrize(
        "name", ["", "simple Foam", "a;rm -rf x", "$(x)", "../bin/x", "-help", "a|b"]
    )
    def test_invalid(self, name):
        assert not is_valid_solver_name(name)


class TestCaseDirs:
    def test_processor_dirs_sorted_numerically(self, tmp_path):
        for n in (10, 2, 0):
            (tmp_path / f"processor{n}").mkdir()
        (tmp_path / "processors4").mkdir()
        (tmp_path / "processorX").mkdir()
        (tmp_path / "processor1").write_text("not a dir")
        assert processor_dirs(str(tmp_path)) == [
            "processor0",
            "processor2",
            "processors4",
            "processor10",
        ]

    def test_processor_dirs_missing_case(self, tmp_path):
        assert processor_dirs(str(tmp_path / "nope")) == []

    def test_has_mesh_variants(self, tmp_path):
        assert not has_mesh(str(tmp_path))
        (tmp_path / "constant").mkdir()
        assert not has_mesh(str(tmp_path))
        (tmp_path / "constant" / "fluid" / "polyMesh").mkdir(parents=True)
        assert has_mesh(str(tmp_path))

    def test_has_mesh_decomposed_only(self, tmp_path):
        (tmp_path / "processor0" / "constant" / "polyMesh").mkdir(parents=True)
        assert has_mesh(str(tmp_path))


class TestKeptLogs:
    @pytest.mark.parametrize("suffix", ["part1", "before-refine", "run_2", "v1.2"])
    def test_valid_suffix(self, suffix):
        assert is_valid_log_suffix(suffix)

    @pytest.mark.parametrize("suffix", ["", ".x", "a b", "a/b", "a;b", "$x", "..", "*"])
    def test_invalid_suffix(self, suffix):
        assert not is_valid_log_suffix(suffix)

    def test_next_part_is_one_past_highest(self, tmp_path):
        assert next_part_suffix(str(tmp_path), "log.simpleFoam") == "part1"
        (tmp_path / "log.simpleFoam.part1").write_text("")
        (tmp_path / "log.simpleFoam.part4").write_text("")
        (tmp_path / "log.simpleFoam.partX").write_text("")
        (tmp_path / "log.pimpleFoam.part9").write_text("")
        # part2/part3 were deleted: still continue after part4, not into the gap.
        assert next_part_suffix(str(tmp_path), "log.simpleFoam") == "part5"

    def test_keep_log_prefix_quotes(self):
        assert keep_log_prefix("log.a", "log.a.part1") == "mv log.a log.a.part1 && "


class TestDecomposedState:
    def test_count_uncollated_and_collated(self, tmp_path):
        assert decomposed_count(str(tmp_path)) is None
        for n in range(3):
            (tmp_path / f"processor{n}").mkdir()
        assert decomposed_count(str(tmp_path)) == 3

    def test_count_collated(self, tmp_path):
        (tmp_path / "processors8").mkdir()
        assert decomposed_count(str(tmp_path)) == 8

    def test_unreconstructed_times(self, tmp_path):
        for n in range(2):
            for t in ("0", "0.5", "1", "2"):
                (tmp_path / f"processor{n}" / t).mkdir(parents=True)
        (tmp_path / "1").mkdir()  # already reconstructed
        assert unreconstructed_times(str(tmp_path)) == ["0.5", "2"]

    def test_stale_none_when_not_decomposed(self, tmp_path):
        (tmp_path / "0").mkdir()
        assert stale_decomposition(str(tmp_path)) == []

    def test_stale_mesh(self, tmp_path):
        import os

        proc_mesh = tmp_path / "processor0" / "constant" / "polyMesh"
        proc_mesh.mkdir(parents=True)
        (proc_mesh / "points").write_text("")
        root_mesh = tmp_path / "constant" / "polyMesh"
        root_mesh.mkdir(parents=True)
        (root_mesh / "points").write_text("")
        t = os.path.getmtime(proc_mesh / "points")
        os.utime(root_mesh / "points", (t - 10, t - 10))
        assert stale_decomposition(str(tmp_path)) == []
        os.utime(root_mesh / "points", (t + 10, t + 10))
        assert stale_decomposition(str(tmp_path)) == [os.path.join("constant", "polyMesh")]

    def test_reconstructed_time_dirs_are_not_stale(self, tmp_path):
        import os

        (tmp_path / "processor0" / "0.5").mkdir(parents=True)
        (tmp_path / "processor0" / "0.5" / "U").write_text("")
        (tmp_path / "0.5").mkdir()
        (tmp_path / "0.5" / "U").write_text("")
        t = os.path.getmtime(tmp_path / "processor0" / "0.5" / "U")
        os.utime(tmp_path / "0.5" / "U", (t + 10, t + 10))
        assert stale_decomposition(str(tmp_path)) == []

    def test_pending_save_counts_as_stale(self, tmp_path):
        (tmp_path / "processor0" / "0").mkdir(parents=True)
        (tmp_path / "0").mkdir()
        assert stale_decomposition(str(tmp_path), [str(tmp_path / "0" / "U")]) == ["0"]


# ── check_processor_deletion: may processor* go without losing data? ─────────

from services.solver_run import check_processor_deletion  # noqa: E402
from tests.services._processor_cases import _owner, _reconstructed_case  # noqa: E402


class TestProcessorDeletion:
    def test_fully_reconstructed_case_is_safe(self, tmp_path):
        check = check_processor_deletion(str(_reconstructed_case(tmp_path)))
        assert check.safe, check.problems
        assert check.dirs == ("processor0", "processor1")
        assert check.total_bytes > 0

    def test_nothing_to_delete_is_not_safe(self, tmp_path):
        check = check_processor_deletion(str(tmp_path))
        assert check.dirs == () and not check.safe

    def test_a_time_left_only_in_processors(self, tmp_path):
        """reconstructPar -latestTime: earlier times exist nowhere else."""
        case = _reconstructed_case(tmp_path)
        import shutil

        shutil.rmtree(case / "0.5")
        check = check_processor_deletion(str(case))
        assert not check.safe
        assert [(p.kind, p.time) for p in check.problems] == [("time_missing", "0.5")]
        assert check.problems[0].detail == ("processor0", "processor1")

    def test_fields_left_only_in_processors(self, tmp_path):
        """reconstructPar -fields '(U)': p was never reconstructed."""
        case = _reconstructed_case(tmp_path)
        for t in ("0.5", "1"):
            (case / t / "p").unlink()
        check = check_processor_deletion(str(case))
        assert [(p.kind, p.time, p.detail) for p in check.problems] == [
            ("files_missing", "0.5", ("p",)),
            ("files_missing", "1", ("p",)),
        ]

    def test_nested_data_is_compared_too(self, tmp_path):
        case = _reconstructed_case(tmp_path)
        lag = case / "processor0" / "1" / "lagrangian" / "cloud"
        lag.mkdir(parents=True)
        (lag / "positions").write_text("x")
        problems = check_processor_deletion(str(case)).problems
        assert [(p.kind, p.time, p.detail) for p in problems] == [
            ("files_missing", "1", ("lagrangian/cloud/positions",)),
        ]

    def test_processor_addressing_is_not_required_at_the_root(self, tmp_path):
        """A dynamic-mesh time keeps *ProcAddressing in the decomposed copy only."""
        case = _reconstructed_case(tmp_path)
        pm = case / "processor0" / "1" / "polyMesh"
        pm.mkdir()
        (pm / "points").write_text("x")
        (pm / "cellProcAddressing").write_text("x")
        (case / "1" / "polyMesh").mkdir()
        (case / "1" / "polyMesh" / "points").write_text("x")
        assert check_processor_deletion(str(case)).safe

    def test_parallel_mesh_not_reconstructed(self, tmp_path):
        """snappyHexMesh -parallel, no reconstructParMesh: the root holds the background mesh."""
        case = _reconstructed_case(tmp_path)
        _owner(case / "constant" / "polyMesh", 5)
        problems = check_processor_deletion(str(case)).problems
        assert [(p.kind, p.detail) for p in problems] == [("mesh_differs", ("5", "16"))]

    def test_mesh_only_in_processors(self, tmp_path):
        case = _reconstructed_case(tmp_path)
        import shutil

        shutil.rmtree(case / "constant" / "polyMesh")
        kinds = [p.kind for p in check_processor_deletion(str(case)).problems]
        assert kinds == ["mesh_missing"]

    def test_unreadable_cell_count_refuses(self, tmp_path):
        case = _reconstructed_case(tmp_path)
        (case / "processor1" / "constant" / "polyMesh" / "owner").write_text("binary junk")
        kinds = [p.kind for p in check_processor_deletion(str(case)).problems]
        assert kinds == ["mesh_unknown"]

    def test_sets_only_in_processors(self, tmp_path):
        """reconstructPar -noSets leaves topoSet's sets in the decomposed copy."""
        case = _reconstructed_case(tmp_path)
        sets = case / "processor0" / "constant" / "polyMesh" / "sets"
        sets.mkdir()
        (sets / "heater").write_text("x")
        problems = check_processor_deletion(str(case)).problems
        assert [(p.kind, p.detail) for p in problems] == [("sets_missing", ("heater",))]
        root_sets = case / "constant" / "polyMesh" / "sets"
        root_sets.mkdir()
        (root_sets / "heater").write_text("x")
        assert check_processor_deletion(str(case)).safe

    def test_collated_data_is_refused(self, tmp_path):
        (tmp_path / "processors2" / "0.5").mkdir(parents=True)
        check = check_processor_deletion(str(tmp_path))
        assert [p.kind for p in check.problems] == ["collated"]
        assert not check.safe


class TestKeepLatest:
    """Keep the newest processor time and constant/, delete the rest."""

    def test_keeps_the_latest_time_and_the_mesh(self, tmp_path):
        from services.solver_run import delete_processor_data

        case = _reconstructed_case(tmp_path)
        check = check_processor_deletion(str(case), keep_latest=True)
        assert check.safe and check.keep_latest and check.kept_time == "1"
        assert delete_processor_data(str(case), check).failed == ()
        for n in (0, 1):
            proc = case / f"processor{n}"
            assert sorted(p.name for p in proc.iterdir()) == ["1", "constant"]
            assert (proc / "constant" / "polyMesh" / "owner").exists()
            assert (proc / "1" / "U").exists()
        assert (case / "0.5" / "U").exists()  # the root is untouched

    def test_frees_less_than_deleting_everything(self, tmp_path):
        case = _reconstructed_case(tmp_path)
        whole = check_processor_deletion(str(case))
        keep = check_processor_deletion(str(case), keep_latest=True)
        assert 0 < keep.total_bytes < whole.total_bytes

    def test_the_kept_time_need_not_be_at_the_root(self, tmp_path):
        """It is not deleted, so it is not checked."""
        import shutil

        case = _reconstructed_case(tmp_path)
        shutil.rmtree(case / "1")
        assert not check_processor_deletion(str(case)).safe
        assert check_processor_deletion(str(case), keep_latest=True).safe

    def test_earlier_times_are_still_checked(self, tmp_path):
        import shutil

        case = _reconstructed_case(tmp_path)
        shutil.rmtree(case / "0.5")
        check = check_processor_deletion(str(case), keep_latest=True)
        assert [(p.kind, p.time) for p in check.problems] == [("time_missing", "0.5")]

    def test_mesh_and_sets_are_kept_so_not_checked(self, tmp_path):
        case = _reconstructed_case(tmp_path)
        _owner(case / "constant" / "polyMesh", 5)  # parallel mesh, never reconstructed
        sets = case / "processor0" / "constant" / "polyMesh" / "sets"
        sets.mkdir()
        (sets / "heater").write_text("x")
        assert not check_processor_deletion(str(case)).safe
        assert check_processor_deletion(str(case), keep_latest=True).safe

    def test_reports_the_newest_root_time(self, tmp_path):
        case = _reconstructed_case(tmp_path)
        (case / "2").mkdir()  # a serial run carried on past the processors
        check = check_processor_deletion(str(case), keep_latest=True)
        assert (check.kept_time, check.latest_root_time) == ("1", "2")

    def test_nothing_to_keep_never_means_delete_everything(self, tmp_path):
        from services.solver_run import delete_processor_data

        _owner(tmp_path / "processor0" / "constant" / "polyMesh", 4)
        check = check_processor_deletion(str(tmp_path), keep_latest=True)
        assert check.keep_latest and check.kept_time is None
        assert delete_processor_data(str(tmp_path), check).failed == ()
        assert (tmp_path / "processor0" / "constant" / "polyMesh" / "owner").exists()

    def test_whole_mode_deletes_the_directories(self, tmp_path):
        from services.solver_run import delete_processor_data

        case = _reconstructed_case(tmp_path)
        assert delete_processor_data(str(case), check_processor_deletion(str(case))).failed == ()
        assert not (case / "processor0").exists() and not (case / "processor1").exists()


class TestDeletionProgress:
    def test_targets_are_one_time_directory_at_a_time(self, tmp_path):
        from services.solver_run import deletion_targets

        case = _reconstructed_case(tmp_path)

        def rel_targets(**kw):
            check = check_processor_deletion(str(case), **kw)
            return [os.path.relpath(t, case) for t in deletion_targets(str(case), check)]

        assert rel_targets(keep_latest=True) == [
            "processor0/0", "processor0/0.5", "processor1/0", "processor1/0.5",
        ]
        whole = rel_targets()
        assert whole == [
            "processor0/0", "processor0/0.5", "processor0/1", "processor0",
            "processor1/0", "processor1/0.5", "processor1/1", "processor1",
        ]

    def test_progress_and_stopping_part_way(self, tmp_path):
        from services.solver_run import delete_processor_data

        case = _reconstructed_case(tmp_path)
        seen = []
        result = delete_processor_data(
            str(case),
            check_processor_deletion(str(case)),
            progress=lambda done, total, rel: seen.append((done, total, rel)),
            cancelled=lambda: len(seen) >= 3,
        )
        assert result.stopped and (result.done, result.total) == (3, 8)
        assert [s[2] for s in seen] == ["processor0/0", "processor0/0.5", "processor0/1"]
        # Stopped between targets: what went was whole and verified; the rest is intact.
        assert sorted(p.name for p in (case / "processor0").iterdir()) == ["constant"]
        assert (case / "processor1" / "0.5" / "U").exists()


# ── soundness: is the case-root copy whole, not merely present? ──────────────

import services.field_integrity as _fi  # noqa: E402
from services.solver_run import case_activity_problem, verify_compressed  # noqa: E402
from tests.services._processor_cases import (  # noqa: E402
    _field_text,
    _sound_case,
    _write,
)


def _kinds(check):
    return [(p.kind, p.time, p.detail) for p in check.problems]


class TestSoundness:
    def test_a_sound_case_is_safe_in_both_modes(self, tmp_path):
        _sound_case(tmp_path)
        assert check_processor_deletion(str(tmp_path)).safe
        assert check_processor_deletion(str(tmp_path), keep_latest=True).safe

    def test_a_field_cut_off_at_the_root_is_refused(self, tmp_path):
        _sound_case(tmp_path)
        f = tmp_path / "0.5" / "p"
        os.truncate(f, f.stat().st_size // 2)
        assert _kinds(check_processor_deletion(str(tmp_path))) == [
            ("files_cut_off", "0.5", ("p",))
        ]

    def test_the_kept_time_is_not_checked(self, tmp_path):
        # Keep-latest leaves processor*/1 in place, so a damaged root 1/ loses nothing.
        _sound_case(tmp_path)
        f = tmp_path / "1" / "p"
        os.truncate(f, f.stat().st_size // 2)
        assert not check_processor_deletion(str(tmp_path)).safe
        assert check_processor_deletion(str(tmp_path), keep_latest=True).safe

    def test_a_root_file_is_held_only_to_its_processor_copys_standard(self, tmp_path):
        # Neither copy has a closing line or header: OpenFOAM wrote it that way.
        _sound_case(tmp_path)
        for d in ("processor0", "processor1", "."):
            (tmp_path / d / "0.5" / "extra").write_text("raw data\n")
        assert check_processor_deletion(str(tmp_path)).safe

    def test_a_damaged_header_is_refused(self, tmp_path):
        _sound_case(tmp_path)
        text = _field_text("p", 16)
        _write(tmp_path / "0.5" / "p", text.replace("FoamFile", "FoamFi1e"))
        assert _kinds(check_processor_deletion(str(tmp_path))) == [
            ("files_bad_header", "0.5", ("p",))
        ]

    def test_a_field_from_another_mesh_is_refused(self, tmp_path):
        _sound_case(tmp_path)
        _write(tmp_path / "0.5" / "p", _field_text("p", 12))  # mesh has 16
        assert _kinds(check_processor_deletion(str(tmp_path))) == [
            ("files_wrong_size", "0.5", ("p: 12 ≠ 16",))
        ]

    def test_surface_fields_count_internal_faces(self, tmp_path):
        _sound_case(tmp_path)
        for d, n in (("processor0", 2), ("processor1", 3), (".", 5)):
            _write(tmp_path / d / "0.5" / "phi", _field_text("phi", n, "surfaceScalarField"))
        assert check_processor_deletion(str(tmp_path)).safe

    def test_a_mesh_written_into_a_time_directory_applies_from_then_on(self, tmp_path):
        # A topology-changing run (dynamicRefineFvMesh) writes <t>/polyMesh.
        _sound_case(tmp_path)
        _owner(tmp_path / "0.5" / "polyMesh", 20)
        for d in ("processor0", "processor1"):
            _owner(tmp_path / d / "0.5" / "polyMesh", 10)
        _write(tmp_path / "0.5" / "p", _field_text("p", 20))
        _write(tmp_path / "1" / "p", _field_text("p", 20))
        assert check_processor_deletion(str(tmp_path)).safe

    def test_a_region_field_uses_its_regions_mesh(self, tmp_path):
        _sound_case(tmp_path)
        _owner(tmp_path / "constant" / "solid" / "polyMesh", 6)
        for d in ("processor0", "processor1"):
            _write(tmp_path / d / "0.5" / "solid" / "T", _field_text("T", 3))
        _write(tmp_path / "0.5" / "solid" / "T", _field_text("T", 6))
        assert check_processor_deletion(str(tmp_path)).safe
        _write(tmp_path / "0.5" / "solid" / "T", _field_text("T", 16))
        assert _kinds(check_processor_deletion(str(tmp_path))) == [
            ("files_wrong_size", "0.5", (os.path.join("solid", "T") + ": 16 ≠ 6",))
        ]


class TestCompressedCases:
    def test_compressed_names_match_uncompressed_ones(self, tmp_path):
        # decomposePar writes processor*/0/p.gz from an uncompressed 0/p, and
        # the processor mesh as owner.gz: neither is data missing at the root.
        _sound_case(tmp_path, gz=True)
        for d in ("processor0", "processor1"):
            owner = tmp_path / d / "constant" / "polyMesh" / "owner"
            _write(owner, owner.read_text(), gz=True)
            owner.unlink()
        assert check_processor_deletion(str(tmp_path)).safe

    def test_small_gz_files_are_read_whole_in_the_quick_check(self, tmp_path):
        _sound_case(tmp_path, gz=True)
        f = tmp_path / "0.5" / "p.gz"
        os.truncate(f, f.stat().st_size - 20)
        check = check_processor_deletion(str(tmp_path))
        assert _kinds(check) == [("files_cut_off", "0.5", ("p.gz",))]
        assert check.unverified_gz == ()

    def test_large_gz_files_are_left_for_verify_compressed(self, tmp_path, monkeypatch):
        monkeypatch.setattr(_fi, "_HEAD_BYTES", 200)
        _sound_case(tmp_path, gz=True)
        f = tmp_path / "0.5" / "p.gz"
        os.truncate(f, f.stat().st_size - 20)
        check = check_processor_deletion(str(tmp_path))
        assert check.safe  # the quick check cannot see it…
        assert ("0.5", "p.gz") in check.unverified_gz
        assert check.unverified_gz_bytes == sum(
            os.path.getsize(tmp_path / t / r) for t, r in check.unverified_gz
        )
        seen = []
        found = verify_compressed(str(tmp_path), check, lambda d, t, r: seen.append((d, t)))
        assert [(p.kind, p.time, p.detail) for p in found] == [
            ("files_cut_off", "0.5", ("p.gz",))
        ]  # …the full read can
        assert seen[-1][0] == seen[-1][1] == check.unverified_gz_bytes
        assert verify_compressed(str(tmp_path), check, cancelled=lambda: True) is None

    def test_keep_mode_leaves_the_kept_time_unread(self, tmp_path, monkeypatch):
        monkeypatch.setattr(_fi, "_HEAD_BYTES", 200)
        _sound_case(tmp_path, gz=True)
        keep = check_processor_deletion(str(tmp_path), keep_latest=True)
        assert {t for t, _ in keep.unverified_gz} == {"0.5"}
        assert verify_compressed(str(tmp_path), keep) == ()


def test_case_activity_ignores_fode_itself(tmp_path):
    # This test process is the "FoDE" here; nothing else works in tmp_path.
    assert case_activity_problem(str(tmp_path)) is None
