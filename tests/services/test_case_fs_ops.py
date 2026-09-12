# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for services/case_fs_ops.py -- the Case Browser's filesystem safety layer.

These are the bulk of the coverage for the "Path safety" step of the Case Browser
feature. The negative tests are the point of this module: each one asserts the
filesystem is left *unchanged* by a refusal, not merely that the right Refusal code
came back -- in particular, a refusal must never silently do part of the operation
(the shutil.move-into-existing-directory foot-gun above all).

A true cross-filesystem (EXDEV) move cannot be exercised in-process -- it needs two
real mounts -- so cross-device behaviour here is covered by stubbing os.stat() to
report differing st_dev values.
"""
from __future__ import annotations

import os
import shutil
import stat as stat_module
from pathlib import Path

import pytest

from services.case_fs_ops import (
    CopyFailure,
    Refusal,
    check_copy,
    check_delete,
    check_move,
    check_new_folder,
    check_rename,
    perform_copy,
    perform_delete,
    perform_move,
    perform_new_folder,
    unique_name,
)

# ── helpers ────────────────────────────────────────────────────────────────────

def _tree(root: Path, *, with_symlink: bool = False, executable: str | None = None) -> Path:
    """Build a small case-directory-shaped tree under *root* and return it."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "system").mkdir()
    (root / "system" / "controlDict").write_text("controlDict\n")
    (root / "constant").mkdir()
    (root / "constant" / "polyMesh").mkdir()
    if executable is not None:
        script = root / executable
        script.write_text("#!/bin/sh\nblockMesh\n")
        script.chmod(script.stat().st_mode | stat_module.S_IXUSR | stat_module.S_IXGRP)
    if with_symlink:
        (root / "linked").symlink_to(root / "constant", target_is_directory=True)
    return root


# ── is_within / normalisation precedent ─────────────────────────────────────────

class TestSubtreeContainment:
    def test_move_into_own_subtree_direct(self, tmp_path):
        src = _tree(tmp_path / "case")
        dst = src / "system" / "nested"
        result = check_move(src, dst)
        assert result.refusal is Refusal.INTO_OWN_SUBTREE
        assert src.exists() and not dst.exists()

    def test_move_into_own_subtree_via_symlink(self, tmp_path):
        # The symlink lives OUTSIDE src and points back at it, so a lexical
        # (normpath-only) containment check would miss this -- only resolve() catches it.
        src = _tree(tmp_path / "case")
        link = tmp_path / "link"
        link.symlink_to(src, target_is_directory=True)
        dst = link / "nested_copy"
        result = check_move(src, dst)
        assert result.refusal is Refusal.INTO_OWN_SUBTREE
        assert not dst.exists()

    def test_copy_into_own_subtree(self, tmp_path):
        src = _tree(tmp_path / "case")
        dst = src / "constant" / "nested"
        result = check_copy(src, dst)
        assert result.refusal is Refusal.INTO_OWN_SUBTREE
        assert not dst.exists()

    def test_operating_on_an_unrelated_directory_is_not_refused(self, tmp_path):
        # Documents a boundary: this module has no notion of "the currently open
        # case" (that's UI-layer state), so it only refuses subtree/protected/name
        # issues -- an ordinary move of an unrelated directory must succeed.
        other = _tree(tmp_path / "other")
        dst = tmp_path / "moved_other"
        result = check_move(other, dst)
        assert result.ok


# ── destination-exists foot-gun ─────────────────────────────────────────────────

class TestDestinationExists:
    def test_move_to_existing_destination_is_refused(self, tmp_path):
        src = _tree(tmp_path / "cavity")
        dst = _tree(tmp_path / "cases")
        result = check_move(src, dst)
        assert result.refusal is Refusal.DESTINATION_EXISTS
        # The shutil.move foot-gun: never let src land INSIDE dst.
        assert not (dst / src.name).exists()
        assert src.exists()

    def test_perform_move_refuses_rather_than_nesting(self, tmp_path):
        src = _tree(tmp_path / "cavity")
        dst = _tree(tmp_path / "cases")
        with pytest.raises(FileExistsError):
            perform_move(src, dst)
        assert not (dst / src.name).exists()
        assert src.exists()

    def test_copy_to_existing_destination_is_refused(self, tmp_path):
        src = _tree(tmp_path / "cavity")
        dst = _tree(tmp_path / "cases")
        result = check_copy(src, dst)
        assert result.refusal is Refusal.DESTINATION_EXISTS
        assert not (dst / src.name).exists()

    def test_new_folder_existing_name_is_refused(self, tmp_path):
        (tmp_path / "existing").mkdir()
        result = check_new_folder(tmp_path, "existing")
        assert result.refusal is Refusal.DESTINATION_EXISTS


# ── name validation / traversal ─────────────────────────────────────────────────

class TestNameValidation:
    @pytest.mark.parametrize("name", ["", "   ", ".", ".."])
    def test_empty_or_dot_names(self, tmp_path, name):
        result = check_new_folder(tmp_path, name)
        assert result.refusal is Refusal.NAME_EMPTY
        assert list(tmp_path.iterdir()) == []

    @pytest.mark.parametrize("name", ["a/b", "a\\b"])
    def test_separator_in_name_that_does_not_escape(self, tmp_path, name):
        result = check_new_folder(tmp_path, name)
        assert result.refusal is Refusal.NAME_HAS_SEPARATOR
        assert list(tmp_path.iterdir()) == []

    @pytest.mark.parametrize("name", ["../escaped", "a/../../escaped"])
    def test_traversal_reports_escapes_parent_not_separator(self, tmp_path, name):
        result = check_new_folder(tmp_path, name)
        assert result.refusal is Refusal.ESCAPES_PARENT
        # Nothing must have been created anywhere, in particular not outside tmp_path.
        assert not (tmp_path.parent / "escaped").exists()
        assert list(tmp_path.iterdir()) == []

    def test_rename_traversal_also_escapes_parent(self, tmp_path):
        src = _tree(tmp_path / "case")
        result = check_rename(src, "../escaped")
        assert result.refusal is Refusal.ESCAPES_PARENT
        assert src.exists()


# ── protected paths ──────────────────────────────────────────────────────────────

class TestProtectedPaths:
    def test_filesystem_root_is_protected(self):
        result = check_delete(Path(os.path.abspath(os.sep)))
        assert result.refusal is Refusal.PROTECTED_PATH

    def test_home_is_protected(self):
        result = check_delete(Path.home())
        assert result.refusal is Refusal.PROTECTED_PATH

    def test_caller_supplied_protected_path(self, tmp_path):
        guarded = _tree(tmp_path / "library_root")
        result = check_delete(guarded, protected=[guarded])
        assert result.refusal is Refusal.PROTECTED_PATH
        assert guarded.exists()

    def test_move_source_protected(self, tmp_path):
        guarded = _tree(tmp_path / "guarded")
        result = check_move(guarded, tmp_path / "elsewhere", protected=[guarded])
        assert result.refusal is Refusal.PROTECTED_PATH
        assert guarded.exists()


# ── symlink handling ──────────────────────────────────────────────────────────────

class TestSymlinks:
    def test_delete_symlink_leaves_target_intact(self, tmp_path):
        target = _tree(tmp_path / "target")
        link = tmp_path / "link"
        link.symlink_to(target, target_is_directory=True)
        assert check_delete(link).ok
        perform_delete(link)
        assert not link.exists() and not link.is_symlink()
        assert (target / "system" / "controlDict").exists()

    def test_copy_does_not_follow_symlinks(self, tmp_path):
        src = _tree(tmp_path / "case", with_symlink=True)
        dst = tmp_path / "case_copy"
        assert check_copy(src, dst).ok
        report = perform_copy(src, dst)
        assert report.failures == ()
        assert (dst / "linked").is_symlink()
        assert os.readlink(dst / "linked") == os.readlink(src / "linked")


# ── case-only rename (samefile carve-out) ───────────────────────────────────────

class TestCaseOnlyRename:
    def test_check_move_allows_samefile_destination(self, tmp_path, monkeypatch):
        src = _tree(tmp_path / "cavity")
        dst = tmp_path / "Cavity"
        dst.mkdir()  # real, distinct, empty directory so os.path.lexists(dst) is True
        monkeypatch.setattr(os.path, "samefile", lambda a, b: True)
        result = check_move(src, dst)
        assert result.ok

    def test_perform_move_uses_path_rename_not_shutil_move(self, tmp_path, monkeypatch):
        src = _tree(tmp_path / "cavity")
        dst = tmp_path / "Cavity"
        dst.mkdir()
        monkeypatch.setattr(os.path, "samefile", lambda a, b: True)

        def _boom(*_a, **_kw):
            raise AssertionError("shutil.move must not be used for a case-only rename")

        monkeypatch.setattr(shutil, "move", _boom)
        perform_move(src, dst)
        assert not src.exists()
        assert (dst / "system" / "controlDict").exists()

    def test_check_rename_allows_samefile_destination(self, tmp_path, monkeypatch):
        src = _tree(tmp_path / "cavity")
        (tmp_path / "Cavity").mkdir()
        monkeypatch.setattr(os.path, "samefile", lambda a, b: True)
        result = check_rename(src, "Cavity")
        assert result.ok


# ── delete via injected remover ─────────────────────────────────────────────────

class TestPerformDelete:
    def test_calls_injected_remover_with_expected_path(self, tmp_path):
        target = _tree(tmp_path / "case")
        calls: list[Path] = []
        perform_delete(target, remove=calls.append)
        assert calls == [target]
        assert target.exists()  # the fake remover didn't actually delete anything

    def test_remover_oserror_propagates(self, tmp_path):
        target = _tree(tmp_path / "case")

        def _fail(_path: Path) -> None:
            raise OSError("permission denied")

        with pytest.raises(OSError):
            perform_delete(target, remove=_fail)
        assert target.exists()

    def test_default_remove_deletes_directory(self, tmp_path):
        target = _tree(tmp_path / "case")
        perform_delete(target)
        assert not target.exists()

    def test_default_remove_deletes_file(self, tmp_path):
        target = tmp_path / "file.txt"
        target.write_text("x")
        perform_delete(target)
        assert not target.exists()


# ── copy: cancellation and partial failure ──────────────────────────────────────

class TestPerformCopyCancellation:
    def test_cancelled_partway_leaves_partial_destination(self, tmp_path):
        src = tmp_path / "case"
        src.mkdir()
        for i in range(5):
            (src / f"file{i}.txt").write_text(str(i))
        dst = tmp_path / "case_copy"

        seen = {"n": 0}

        def _cancelled() -> bool:
            seen["n"] += 1
            return seen["n"] > 2

        report = perform_copy(src, dst, cancelled=_cancelled)
        assert report.cancelled is True
        assert dst.exists()  # partial destination is left in place, not auto-deleted
        assert report.files_copied < 5

    def test_per_file_failure_is_reported_not_raised(self, tmp_path, monkeypatch):
        src = tmp_path / "case"
        src.mkdir()
        (src / "good.txt").write_text("ok")
        (src / "bad.txt").write_text("boom")
        dst = tmp_path / "case_copy"

        real_copy2 = shutil.copy2

        def _flaky_copy2(s, d, *a, **kw):
            if Path(s).name == "bad.txt":
                raise OSError("disk full")
            return real_copy2(s, d, *a, **kw)

        monkeypatch.setattr(shutil, "copy2", _flaky_copy2)
        report = perform_copy(src, dst)
        assert report.files_copied == 1
        assert report.failures == (CopyFailure(str(src / "bad.txt"), "disk full"),)
        assert (dst / "good.txt").exists()
        assert not (dst / "bad.txt").exists()


# ── move: cross-device detection and exception safety ───────────────────────────

class TestPerformMoveCrossDevice:
    def test_cross_device_takes_copy_and_delete_route(self, tmp_path, monkeypatch):
        src = _tree(tmp_path / "case")
        dst = tmp_path / "moved"

        real_stat = os.stat

        def _stat(path, *a, **kw):
            result = real_stat(path, *a, **kw)
            dev = 1 if str(path) == str(src) else 2
            fields = list(result)
            fields[2] = dev
            return os.stat_result(fields)

        monkeypatch.setattr(os, "stat", _stat)
        # Spy only on the top-level dispatch: our own perform_move must hand off to
        # shutil.move (which owns the real EXDEV copy+delete fallback) rather than
        # calling os.rename itself -- what shutil.move does internally is its own
        # concern, not ours.
        calls = {"move": 0}
        real_move = shutil.move

        def _move(s, d):
            calls["move"] += 1
            return real_move(s, d)

        monkeypatch.setattr(shutil, "move", _move)
        perform_move(src, dst)
        assert calls == {"move": 1}
        assert dst.exists() and not src.exists()

    def test_move_failure_leaves_source_intact(self, tmp_path, monkeypatch):
        src = _tree(tmp_path / "case")
        dst = tmp_path / "moved"

        real_stat = os.stat

        def _stat(path, *a, **kw):
            result = real_stat(path, *a, **kw)
            dev = 1 if str(path) == str(src) else 2
            fields = list(result)
            fields[2] = dev
            return os.stat_result(fields)

        monkeypatch.setattr(os, "stat", _stat)

        def _boom(*_a, **_kw):
            raise OSError("copy failed partway")

        monkeypatch.setattr(shutil, "move", _boom)
        with pytest.raises(OSError):
            perform_move(src, dst)
        assert src.exists()
        assert (src / "system" / "controlDict").exists()


# ── unique_name ──────────────────────────────────────────────────────────────────

class TestUniqueName:
    def test_first_candidate_when_free(self, tmp_path):
        assert unique_name(tmp_path, "myCase") == "myCase_copy"

    def test_increments_past_existing_copies(self, tmp_path):
        (tmp_path / "myCase_copy").mkdir()
        (tmp_path / "myCase_copy2").mkdir()
        assert unique_name(tmp_path, "myCase") == "myCase_copy3"


# ── positive round trips ─────────────────────────────────────────────────────────

class TestRoundTrips:
    def test_move(self, tmp_path):
        src = _tree(tmp_path / "cavity")
        dst = tmp_path / "moved_cavity"
        assert check_move(src, dst).ok
        perform_move(src, dst)
        assert not src.exists()
        assert (dst / "system" / "controlDict").exists()

    def test_rename(self, tmp_path):
        src = _tree(tmp_path / "cavity")
        assert check_rename(src, "renamedCavity").ok
        dst = src.parent / "renamedCavity"
        perform_move(src, dst)
        assert dst.exists() and not src.exists()

    def test_copy_preserves_executable_bit(self, tmp_path):
        src = _tree(tmp_path / "cavity", executable="Allrun")
        dst = tmp_path / "cavity_copy"
        assert check_copy(src, dst).ok
        report = perform_copy(src, dst)
        assert report.failures == ()
        mode = (dst / "Allrun").stat().st_mode
        assert mode & stat_module.S_IXUSR

    def test_delete(self, tmp_path):
        target = _tree(tmp_path / "cavity")
        assert check_delete(target).ok
        perform_delete(target)
        assert not target.exists()

    def test_new_folder(self, tmp_path):
        assert check_new_folder(tmp_path, "New Case").ok
        created = perform_new_folder(tmp_path, "New Case")
        assert created.is_dir()
        assert created == tmp_path / "New Case"


# ── permission (best-effort; root bypasses POSIX permission bits) ──────────────

@pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses permission bits")
class TestPermission:
    def test_move_into_read_only_directory_is_refused(self, tmp_path):
        src = _tree(tmp_path / "cavity")
        locked = tmp_path / "locked"
        locked.mkdir()
        locked.chmod(0o555)
        try:
            result = check_move(src, locked / "cavity")
            assert result.refusal is Refusal.PERMISSION
        finally:
            locked.chmod(0o755)
