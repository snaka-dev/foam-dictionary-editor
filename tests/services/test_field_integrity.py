# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""services/field_integrity.py: is one OpenFOAM output file whole?"""
from __future__ import annotations

import gzip
import os

import pytest

import services.field_integrity as fi
from services.field_integrity import Cancelled, MeshSizes, inspect_file, read_mesh_sizes
from tests.services._processor_cases import END_LINE, _field_text, _owner, _write


def _file(tmp_path, text, name="p", gz=False):
    _write(tmp_path / name, text, gz=gz)
    return str(tmp_path / (name + (".gz" if gz else "")))


class TestPlainFiles:
    def test_whole_ascii_field(self, tmp_path):
        state = inspect_file(_file(tmp_path, _field_text("p", 16)))
        assert state.readable and state.ended is True
        assert (state.object_name, state.field_class, state.count) == ("p", "volScalarField", 16)

    def test_whole_binary_field(self, tmp_path):
        # The count is plain text even in binary format; the payload may hold
        # any byte, braces and semicolons included, without confusing either end.
        state = inspect_file(_file(tmp_path, _field_text("p", 16, binary=True)))
        assert state.ended is True and state.count == 16

    @pytest.mark.parametrize("keep", [0.3, 0.6, 0.95])
    def test_cut_off_anywhere_lacks_the_closing_line(self, tmp_path, keep):
        text = _field_text("p", 2000)
        state = inspect_file(_file(tmp_path, text[: int(len(text) * keep)]))
        assert state.readable and state.ended is False

    def test_cut_off_inside_boundary_field(self, tmp_path):
        text = _field_text("p", 16)
        cut = text[: text.index("boundaryField") + 30]
        assert inspect_file(_file(tmp_path, cut)).ended is False

    def test_trailing_whitespace_is_fine_but_trailing_zeros_are_not(self, tmp_path):
        text = _field_text("p", 16)
        assert inspect_file(_file(tmp_path, text + "\n\n  \n")).ended is True
        # What a crash leaves when the size was set but the data never landed.
        assert inspect_file(_file(tmp_path, text + "\x00" * 4096, "q")).ended is False

    def test_large_file_reads_only_its_two_ends(self, tmp_path):
        state = inspect_file(_file(tmp_path, _field_text("p", 50000)))
        assert state.ended is True and state.count == 50000

    def test_uniform_field_has_no_count(self, tmp_path):
        state = inspect_file(_file(tmp_path, _field_text("p")))
        assert state.ended is True and state.count is None

    def test_header_object_names_the_file(self, tmp_path):
        path = _file(tmp_path, _field_text("U", 16), name="p")
        assert not inspect_file(path).names(path)
        assert not inspect_file(_file(tmp_path, "garbage\n" + END_LINE, "q")).header_ok

    def test_missing_file_is_unreadable(self, tmp_path):
        assert not inspect_file(str(tmp_path / "nope")).readable


class TestCompressedFiles:
    def test_small_gz_is_read_whole(self, tmp_path):
        path = _file(tmp_path, _field_text("p", 16), gz=True)
        state = inspect_file(path)
        assert state.ended is True and state.names(path)

    def test_cut_off_gz_is_unreadable(self, tmp_path):
        path = _file(tmp_path, _field_text("p", 16), gz=True)
        os.truncate(path, os.path.getsize(path) - 20)
        assert not inspect_file(path).readable

    def test_large_gz_reads_its_head_only_unless_asked(self, tmp_path, monkeypatch):
        monkeypatch.setattr(fi, "_HEAD_BYTES", 300)
        path = _file(tmp_path, _field_text("p", 2000), gz=True)
        state = inspect_file(path)
        assert state.readable and state.ended is None and state.count == 2000
        assert inspect_file(path, full=True).ended is True

    def test_large_gz_cut_off_is_found_only_by_the_full_read(self, tmp_path, monkeypatch):
        monkeypatch.setattr(fi, "_HEAD_BYTES", 300)
        path = _file(tmp_path, _field_text("p", 2000), gz=True)
        os.truncate(path, os.path.getsize(path) - 20)
        assert inspect_file(path).ended is None
        assert not inspect_file(path, full=True).readable

    def test_gz_whose_data_ends_early(self, tmp_path, monkeypatch):
        # A stream that is itself whole but holds a truncated file.
        monkeypatch.setattr(fi, "_HEAD_BYTES", 300)
        text = _field_text("p", 2000)
        path = _file(tmp_path, text[: len(text) // 2], gz=True)
        state = inspect_file(path, full=True)
        assert state.readable and state.ended is False

    def test_full_read_reports_progress_and_can_be_cancelled(self, tmp_path, monkeypatch):
        monkeypatch.setattr(fi, "_HEAD_BYTES", 300)
        monkeypatch.setattr(fi, "_CHUNK", 1024)
        path = _file(tmp_path, _field_text("p", 20000) * 3, gz=True)
        seen = []
        inspect_file(path, full=True, progress=seen.append)
        assert sum(seen) == os.path.getsize(path)
        with pytest.raises(Cancelled):
            inspect_file(path, full=True, cancelled=lambda: True)


class TestMeshSizes:
    def test_read_from_owner_or_owner_gz(self, tmp_path):
        _owner(tmp_path, 8)
        assert read_mesh_sizes(str(tmp_path / "owner")) == MeshSizes(10, 8, 5)
        with gzip.open(tmp_path / "owner.gz", "wb") as f:
            f.write((tmp_path / "owner").read_bytes())
        assert read_mesh_sizes(str(tmp_path / "owner.gz")) == MeshSizes(10, 8, 5)

    def test_no_note_means_unknown(self, tmp_path):
        (tmp_path / "owner").write_text("FoamFile { object owner; }\n")
        assert read_mesh_sizes(str(tmp_path / "owner")) is None
        assert read_mesh_sizes(str(tmp_path / "missing")) is None

    @pytest.mark.parametrize(
        "cls, expected",
        [
            ("volScalarField", 8),
            ("volVectorField", 8),
            ("surfaceScalarField", 5),
            ("pointVectorField", 10),
            ("volScalarField::Internal", None),
            ("areaScalarField", None),
            ("dictionary", None),
        ],
    )
    def test_expected_count_per_class(self, cls, expected):
        assert MeshSizes(10, 8, 5).expected_count(cls) == expected
