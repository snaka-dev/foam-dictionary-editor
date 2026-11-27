# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Writes stay inside the case: the containment checks and the Qt-free writers.

A case from someone else may hold symlinks or ``..`` paths that lead out of
it. Each test builds such a case under ``tmp_path`` beside an ``outside``
directory standing for the rest of the user's disk, and checks that nothing
there changes. The UI half is ``tests/ui/test_case_containment.py``.
"""
from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from app_config.json_io import atomic_write_text, save_json
from foam.utils import write_foam_file
from services import case_paths as cp
from services.background_run import STOP_FILE, request_stop
from services.case_copier import copy_visible_files
from services.case_files_config import CaseFilesConfig
from services.include_scan import clear_scan_cache, included_files

CONTROL_DICT = (
    "FoamFile { version 2.0; format ascii; class dictionary; object controlDict; }\n"
    "application icoFoam;\nendTime 1;\n"
)
SECRET = "the user's own file\n"


@pytest.fixture
def layout(tmp_path):
    """``case/`` with ordinary files, and ``outside/`` with what it must not touch."""
    case = tmp_path / "case"
    (case / "system").mkdir(parents=True)
    (case / "system" / "controlDict").write_text(CONTROL_DICT, encoding="utf-8")
    outside = tmp_path / "outside"
    (outside / "dir").mkdir(parents=True)
    (outside / "secret").write_text(SECRET, encoding="utf-8")
    (outside / "dir" / "f").write_text(SECRET, encoding="utf-8")
    return case, outside


class TestContainment:
    def test_ordinary_files_are_editable(self, layout):
        case, _ = layout
        assert cp.editable(case / "system" / "controlDict", case)
        assert cp.resolves_inside(case / "system", case)

    def test_a_symlinked_file_is_not(self, layout):
        case, outside = layout
        (case / "system" / "fvSolution").symlink_to(outside / "secret")
        assert not cp.editable(case / "system" / "fvSolution", case)

    def test_a_file_under_a_linked_directory_is_not(self, layout):
        case, outside = layout
        (case / "linkdir").symlink_to(outside / "dir")
        assert not cp.editable(case / "linkdir" / "f", case)

    def test_dot_dot_is_resolved_not_compared_as_text(self, layout):
        case, _ = layout
        climbing = case / "system" / ".." / ".." / "outside" / "secret"
        assert climbing.is_relative_to(case)  # what the old text check saw
        assert not cp.editable(climbing, case)
        # A ".." that stays inside is fine.
        assert cp.editable(case / "system" / ".." / "system" / "controlDict", case)

    def test_a_link_inside_the_case_is_fine(self, layout):
        case, _ = layout
        (case / "system" / "alias").symlink_to("controlDict")
        assert cp.editable(case / "system" / "alias", case)

    def test_a_case_opened_through_a_link_still_works(self, layout, tmp_path):
        case, _ = layout
        alias = tmp_path / "alias"
        alias.symlink_to(case)
        assert cp.editable(alias / "system" / "controlDict", alias)
        assert cp.editable(case / "system" / "controlDict", alias)

    def test_unresolvable_paths_are_refused(self, layout):
        case, _ = layout
        loop = case / "system" / "loop"
        loop.symlink_to(loop)
        assert not cp.editable(loop, case)
        assert not cp.editable(case / "system" / "missing", case)
        assert not cp.editable(case / "system", case)  # a directory is not a file

    def test_creatable(self, layout):
        case, outside = layout
        assert cp.creatable(case / "system" / "new", case)
        assert cp.creatable(case / "a" / "b" / "new", case)  # missing parents are made
        assert not cp.creatable(case / "system" / "controlDict", case)  # exists
        (case / "system" / "dangling").symlink_to(outside / "nothing-here")
        assert not cp.creatable(case / "system" / "dangling", case)
        (case / "linkdir").symlink_to(outside / "dir")
        assert not cp.creatable(case / "linkdir" / "new", case)
        assert not cp.creatable(case / "linkdir" / "deeper" / "new", case)
        assert not cp.creatable(case / "system" / ".." / "x", case)

    def test_writable_allows_recreating_a_deleted_file(self, layout):
        case, outside = layout
        assert cp.writable(case / "system" / "gone", case)
        (case / "system" / "fvSolution").symlink_to(outside / "secret")
        assert not cp.writable(case / "system" / "fvSolution", case)

    def test_removable(self, layout):
        case, outside = layout
        (case / "system" / "link").symlink_to(outside / "secret")
        assert cp.removable(case / "system" / "link", case)  # the link, not its target
        (case / "linkdir").symlink_to(outside / "dir")
        assert not cp.removable(case / "linkdir" / "f", case)
        assert not cp.removable(case / "system", case)  # a directory

    def test_removable_tree(self, layout):
        case, outside = layout
        (case / "0").mkdir()
        assert cp.removable_tree(case / "0", case)
        (case / "linkdir").symlink_to(outside / "dir")
        assert not cp.removable_tree(case / "linkdir", case)
        assert not cp.removable_tree(case, case)
        assert not cp.removable_tree(case / "system" / "controlDict", case)


class TestCopyDestination:
    def test_a_sibling_is_fine(self, layout, tmp_path):
        case, _ = layout
        assert cp.copy_destination_problem(case, tmp_path / "copy") is None

    @pytest.mark.parametrize("name, code", [
        ("case", cp.DEST_IS_SOURCE),
        ("case/system/x", cp.DEST_INSIDE_SOURCE),
        (".", cp.DEST_CONTAINS_SOURCE),
        ("..", cp.DEST_CONTAINS_SOURCE),
        ("case/..", cp.DEST_CONTAINS_SOURCE),
    ])
    def test_overlap_by_any_spelling(self, layout, tmp_path, name, code):
        case, _ = layout
        assert cp.copy_destination_problem(case, tmp_path / name) == code

    def test_overlap_through_an_alias(self, layout, tmp_path):
        case, _ = layout
        (tmp_path / "alias").symlink_to(tmp_path)
        assert cp.copy_destination_problem(case, tmp_path / "alias" / "case") == cp.DEST_IS_SOURCE
        assert cp.copy_destination_problem(
            tmp_path / "alias" / "case", tmp_path / "case"
        ) == cp.DEST_IS_SOURCE

    @pytest.mark.parametrize("name, code", [
        ("case", cp.DEST_IS_SOURCE),
        ("case/system/x", cp.DEST_INSIDE_SOURCE),
        ("", cp.DEST_CONTAINS_SOURCE),
    ])
    def test_overlap_the_path_text_cannot_show(self, layout, tmp_path, monkeypatch, name, code):
        """Two spellings of one directory that resolving does not unify -- letter
        case on a case-insensitive filesystem. Stood in for here by an alias
        and a ``real_path`` that leaves it unresolved, as realpath leaves case."""
        case, _ = layout
        (tmp_path / "alias").symlink_to(tmp_path.parent)
        other = tmp_path / "alias" / tmp_path.name  # tmp_path, spelled differently
        monkeypatch.setattr(cp, "real_path", lambda p: Path(os.path.abspath(p)))
        assert cp.copy_destination_problem(case, other / name) == code
        assert cp.copy_destination_problem(case, other / "copy") is None

    def test_a_link_or_dangling_link_is_refused(self, layout, tmp_path):
        case, outside = layout
        (tmp_path / "dangling").symlink_to(tmp_path / "nowhere")
        (tmp_path / "live").symlink_to(outside)
        assert cp.copy_destination_problem(case, tmp_path / "dangling") == cp.DEST_IS_LINK
        assert cp.copy_destination_problem(case, tmp_path / "live") == cp.DEST_IS_LINK

    def test_a_missing_parent_is_refused(self, layout, tmp_path):
        case, _ = layout
        assert cp.copy_destination_problem(
            case, tmp_path / "no" / "such" / "copy"
        ) == cp.DEST_PARENT_MISSING


class TestIncludeScan:
    def test_a_climbing_include_is_read_only(self, layout):
        case, outside = layout
        (case / "system" / "controlDict").write_text(
            CONTROL_DICT + '#include "../../outside/secret"\n', encoding="utf-8"
        )
        clear_scan_cache()
        new, _, read_only = included_files(str(case), [str(case / "system" / "controlDict")],
                                           etc_dirs=())
        assert len(new) == 1 and set(new) == read_only

    def test_an_include_through_a_linked_directory_is_read_only(self, layout):
        case, outside = layout
        (case / "linkdir").symlink_to(outside / "dir")
        (case / "system" / "controlDict").write_text(
            CONTROL_DICT + '#include "../linkdir/f"\n', encoding="utf-8"
        )
        clear_scan_cache()
        new, _, read_only = included_files(str(case), [str(case / "system" / "controlDict")],
                                           etc_dirs=())
        assert len(new) == 1 and set(new) == read_only

    def test_an_include_that_stays_inside_is_editable(self, layout):
        case, _ = layout
        (case / "constant").mkdir()
        (case / "constant" / "params").write_text("a 1;\n", encoding="utf-8")
        (case / "system" / "controlDict").write_text(
            CONTROL_DICT + '#include "../constant/params"\n', encoding="utf-8"
        )
        clear_scan_cache()
        new, _, read_only = included_files(str(case), [str(case / "system" / "controlDict")],
                                           etc_dirs=())
        assert len(new) == 1 and not read_only

    def test_one_file_under_several_spellings_is_listed_once(self, layout):
        case, _ = layout
        (case / "constant").mkdir()
        (case / "constant" / "shared").write_text("a 1;\n", encoding="utf-8")
        users = {
            case / "constant" / "transportProperties": '#include "shared"\n',
            case / "system" / "controlDict": CONTROL_DICT + '#include "../constant/shared"\n',
            case / "system" / "fvSolution": '#include "../system/../constant/shared"\n',
        }
        for path, text in users.items():
            path.write_text(text, encoding="utf-8")
        clear_scan_cache()
        new, origins, read_only = included_files(str(case), [str(p) for p in users], etc_dirs=())
        assert len(new) == 1 and not read_only
        assert os.path.samefile(new[0], case / "constant" / "shared")
        # The one row still counts every file that includes it.
        assert origins[new[0]].endswith("+1 more")


class TestConflictingWrites:
    def test_two_names_for_one_file_with_different_text(self, layout):
        case, _ = layout
        real = case / "system" / "controlDict"
        (case / "system" / "alias").symlink_to(real)
        other = case / "system" / "other"
        other.write_text("x", encoding="utf-8")
        a, b, c = str(real), str(case / "system" / "alias"), str(other)
        assert cp.conflicting_writes({a: "1", b: "2", c: "3"}) == {a, b}
        assert cp.conflicting_writes({a: "1", b: "1", c: "3"}) == set()
        dotted = str(case / "system" / ".." / "system" / "controlDict")
        assert cp.conflicting_writes({a: "1", dotted: "2"}) == {a, dotted}
        assert cp.conflicting_writes({a: "1"}) == set()

    def test_a_missing_file_is_matched_by_its_folded_name(self, layout):
        case, _ = layout
        a = str(case / "system" / "gone")
        b = str(case / "system" / ".." / "system" / "gone")
        assert cp.conflicting_writes({a: "1", b: "2"}) == {a, b}


class TestPinnedRoot:
    """The path a case was opened by can come to name another directory.
    Buffers read from the first must not be written into the second."""

    @pytest.fixture
    def pinned(self, layout):
        case, _ = layout
        cp.pin_case_root(case)
        yield case
        cp.pin_case_root(None)

    def _replace_folder(self, case: Path) -> None:
        case.rename(case.with_name("case.old"))
        (case / "system").mkdir(parents=True)
        (case / "system" / "controlDict").write_text(CONTROL_DICT, encoding="utf-8")

    def test_every_check_passes_while_the_folder_is_the_same(self, pinned):
        assert not cp.case_root_changed(pinned)
        assert cp.editable(pinned / "system" / "controlDict", pinned)
        assert cp.creatable(pinned / "system" / "new", pinned)

    def test_a_replaced_folder_refuses_every_write(self, pinned):
        self._replace_folder(pinned)
        f = pinned / "system" / "controlDict"
        assert cp.case_root_changed(pinned)
        assert not cp.editable(f, pinned)
        assert not cp.writable(f, pinned)
        assert not cp.creatable(pinned / "system" / "new", pinned)
        assert not cp.removable(f, pinned)
        assert not cp.removable_tree(pinned / "system", pinned)
        assert cp.copy_destination_problem(pinned, pinned.with_name("copy")) == cp.SOURCE_UNRESOLVABLE

    def test_a_retargeted_link_refuses_every_write(self, layout, tmp_path):
        case, _ = layout
        other = tmp_path / "other"
        (other / "system").mkdir(parents=True)
        (other / "system" / "controlDict").write_text(CONTROL_DICT, encoding="utf-8")
        opened = tmp_path / "opened"
        opened.symlink_to(case)
        cp.pin_case_root(opened)
        try:
            assert cp.editable(opened / "system" / "controlDict", opened)
            opened.unlink()
            opened.symlink_to(other)
            assert cp.case_root_changed(opened)
            assert not cp.editable(opened / "system" / "controlDict", opened)
        finally:
            cp.pin_case_root(None)

    def test_opening_again_pins_the_new_folder(self, pinned):
        self._replace_folder(pinned)
        cp.pin_case_root(pinned)
        assert not cp.case_root_changed(pinned)
        assert cp.editable(pinned / "system" / "controlDict", pinned)

    def test_another_directory_is_not_held_to_the_pin(self, pinned, tmp_path):
        other = tmp_path / "other"
        (other / "system").mkdir(parents=True)
        self._replace_folder(pinned)
        assert cp.creatable(other / "system" / "new", other)

    def test_a_folder_that_could_not_be_identified_refuses_until_reopened(self, tmp_path):
        late = tmp_path / "late"
        cp.pin_case_root(late)  # not there yet
        try:
            (late / "system").mkdir(parents=True)
            (late / "system" / "controlDict").write_text(CONTROL_DICT, encoding="utf-8")
            assert cp.case_root_changed(late)
            assert not cp.editable(late / "system" / "controlDict", late)
            assert not cp.creatable(late / "system" / "new", late)
            cp.pin_case_root(late)
            assert cp.editable(late / "system" / "controlDict", late)
        finally:
            cp.pin_case_root(None)

    def test_the_case_config_is_neither_written_nor_deleted(self, pinned):
        config = CaseFilesConfig(str(pinned))
        config.add_file("system/extra")
        assert config.save() is True
        self._replace_folder(pinned)
        planted = pinned / ".foam-editor-files.json"
        planted.write_text('{"extra_files": ["theirs"]}', encoding="utf-8")
        config.add_file("system/more")
        assert config.save() is False
        assert config.delete_config_file() is False
        assert planted.read_text(encoding="utf-8") == '{"extra_files": ["theirs"]}'


class TestFileIdentity:
    """Stood in for a case-insensitive filesystem by a hard link: two names
    whose resolved text differs and which are one file."""

    def test_two_names_of_one_file_conflict(self, layout):
        case, _ = layout
        a = case / "system" / "controlDict"
        b = case / "system" / "CONTROLDICT"
        os.link(a, b)
        assert cp.real_path(a) != cp.real_path(b)
        assert cp.file_identity(a) == cp.file_identity(b)
        assert cp.conflicting_writes({str(a): "1", str(b): "2"}) == {str(a), str(b)}

    def test_the_include_scan_lists_such_a_file_once(self, layout):
        case, _ = layout
        (case / "system" / "shared").write_text("a 1;\n", encoding="utf-8")
        os.link(case / "system" / "shared", case / "system" / "SHARED")
        (case / "system" / "controlDict").write_text(
            CONTROL_DICT + '#include "shared"\n#include "SHARED"\n', encoding="utf-8"
        )
        clear_scan_cache()
        new, _, _ = included_files(str(case), [str(case / "system" / "controlDict")], etc_dirs=())
        assert len(new) == 1


class TestCopyVisibleFiles:
    def test_outside_entries_are_skipped_and_reported(self, layout, tmp_path):
        case, outside = layout
        (case / "system" / "fvSolution").symlink_to(outside / "secret")
        (case / "linkdir").symlink_to(outside / "dir")
        config = CaseFilesConfig(str(case))
        config.add_file("linkdir/f")
        config.save()
        dest = tmp_path / "copy"
        report = copy_visible_files(str(case), dest)
        assert "system/controlDict" in report.copied
        assert sorted(report.skipped) == ["linkdir/f", "system/fvSolution"]
        assert not (dest / "system" / "fvSolution").exists()
        assert not (dest / "linkdir").exists()
        # Nothing in the copy holds the outside file's contents.
        for p in dest.rglob("*"):
            if p.is_file():
                assert SECRET not in p.read_text(encoding="utf-8")

    def test_a_linked_case_config_is_not_copied(self, layout, tmp_path):
        case, outside = layout
        (case / ".foam-editor-files.json").symlink_to(outside / "secret")
        report = copy_visible_files(str(case), tmp_path / "copy")
        assert ".foam-editor-files.json" in report.skipped
        assert not os.path.lexists(tmp_path / "copy" / ".foam-editor-files.json")


class TestAtomicConfigWrite:
    def test_a_planted_temp_name_is_not_written_through(self, layout):
        """F5: a fixed ``<name>.tmp`` let a case overwrite any file of the user's."""
        case, outside = layout
        (case / ".foam-editor-files.json.tmp").symlink_to(outside / "secret")
        config = CaseFilesConfig(str(case))
        config.add_file("system/controlDict")
        config.save()
        assert (outside / "secret").read_text(encoding="utf-8") == SECRET
        assert CaseFilesConfig(str(case)).get_extra_files() == ["system/controlDict"]

    def test_a_link_at_the_final_name_is_replaced_not_followed(self, layout):
        case, outside = layout
        (case / ".foam-editor-files.json").symlink_to(outside / "secret")
        save_json(case / ".foam-editor-files.json", {"extra_files": []})
        assert (outside / "secret").read_text(encoding="utf-8") == SECRET
        assert not (case / ".foam-editor-files.json").is_symlink()

    def test_an_existing_file_keeps_its_mode(self, tmp_path):
        path = tmp_path / "c.json"
        path.write_text("{}", encoding="utf-8")
        path.chmod(0o640)
        atomic_write_text(path, "{}")
        assert stat.S_IMODE(path.stat().st_mode) == 0o640

    def test_a_new_file_gets_the_requested_mode_less_the_umask(self, tmp_path):
        old = os.umask(0o022)
        try:
            atomic_write_text(tmp_path / "shared.json", "{}")
            atomic_write_text(tmp_path / "private.json", "{}", new_mode=0o600)
        finally:
            os.umask(old)
        assert stat.S_IMODE((tmp_path / "shared.json").stat().st_mode) == 0o644
        assert stat.S_IMODE((tmp_path / "private.json").stat().st_mode) == 0o600

    def test_a_failed_replace_leaves_no_temp_and_the_old_contents(self, tmp_path, monkeypatch):
        import app_config.json_io as json_io

        path = tmp_path / "c.json"
        path.write_text("old", encoding="utf-8")
        monkeypatch.setattr(json_io.os, "replace", lambda *a: (_ for _ in ()).throw(OSError()))
        with pytest.raises(OSError):
            atomic_write_text(path, "new")
        assert path.read_text(encoding="utf-8") == "old"
        assert sorted(p.name for p in tmp_path.iterdir()) == ["c.json"]


class TestExclusiveCreate:
    def test_a_dangling_link_is_not_followed(self, layout):
        case, outside = layout
        planted = case / "system" / "new"
        planted.symlink_to(outside / "created-elsewhere")
        with pytest.raises(FileExistsError):
            write_foam_file(planted, "x 1;\n", exclusive=True)
        assert not (outside / "created-elsewhere").exists()

    def test_gzip_still_applies(self, tmp_path):
        import gzip

        write_foam_file(tmp_path / "U.gz", "x 1;\n", exclusive=True)
        assert gzip.decompress((tmp_path / "U.gz").read_bytes()) == b"x 1;\n"


class TestBackgroundStop:
    def test_a_linked_control_dict_is_not_rewritten(self, layout):
        case, outside = layout
        (outside / "secret").write_text(CONTROL_DICT, encoding="utf-8")
        cd = case / "system" / "controlDict"
        cd.unlink()
        cd.symlink_to(outside / "secret")
        assert request_stop(str(case)) is not None  # an error, not a write
        assert (outside / "secret").read_text(encoding="utf-8") == CONTROL_DICT

    def test_a_planted_record_link_is_not_written_through(self, layout):
        case, outside = layout
        (case / STOP_FILE).symlink_to(outside / "record-elsewhere")
        request_stop(str(case))
        assert not (outside / "record-elsewhere").exists()


def test_case_paths_never_follows_text_alone(layout):
    """The v1.21.1 text filter alone passes a linked directory; this is why both exist."""
    from services.case_files_config import is_inside_case

    case, outside = layout
    (case / "linkdir").symlink_to(outside / "dir")
    assert is_inside_case("linkdir/f")
    assert not cp.editable(Path(case) / "linkdir" / "f", case)
