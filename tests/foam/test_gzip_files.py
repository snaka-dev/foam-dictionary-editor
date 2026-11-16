# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Gzip-compressed dictionaries: read transparently, written back compressed.

Reading ``0/U.gz`` as plain text used to show the compressed bytes, and one
Ctrl+S re-encoded them as UTF-8 so the file was no longer gzip.
"""
from __future__ import annotations

import gzip
from pathlib import Path

import pytest

from foam.utils import is_gzip_file, is_large_non_foam_file, read_foam_file, write_foam_file

TEXT = (
    "FoamFile { version 2.0; format ascii; class volVectorField; object U; }\n"
    "internalField uniform (0 0 0);\n"
)


def test_read_decompresses(tmp_path: Path):
    f = tmp_path / "U.gz"
    f.write_bytes(gzip.compress(TEXT.encode()))
    assert read_foam_file(f) == TEXT


def test_compression_is_recognised_by_content_not_name(tmp_path: Path):
    plain_named_gz = tmp_path / "U.gz"
    plain_named_gz.write_text(TEXT)
    assert read_foam_file(plain_named_gz) == TEXT
    gz_named_plain = tmp_path / "U"
    gz_named_plain.write_bytes(gzip.compress(TEXT.encode()))
    assert is_gzip_file(gz_named_plain)
    assert read_foam_file(gz_named_plain) == TEXT


def test_crlf_in_a_compressed_file_reads_like_a_plain_one(tmp_path: Path):
    f = tmp_path / "U.gz"
    f.write_bytes(gzip.compress(TEXT.replace("\n", "\r\n").encode()))
    assert read_foam_file(f) == TEXT


def test_damaged_archive_raises_oserror(tmp_path: Path):
    f = tmp_path / "U.gz"
    f.write_bytes(gzip.compress(TEXT.encode())[:20])
    with pytest.raises(OSError):
        read_foam_file(f)


def test_write_compresses_by_name(tmp_path: Path):
    f = tmp_path / "U.gz"
    write_foam_file(f, TEXT)
    assert gzip.decompress(f.read_bytes()).decode() == TEXT
    g = tmp_path / "U"
    write_foam_file(g, TEXT)
    assert g.read_text() == TEXT


def test_write_compress_override(tmp_path: Path):
    backup = tmp_path / "U.gz.bak_20261114_120000"
    write_foam_file(backup, TEXT, compress=True)
    assert gzip.decompress(backup.read_bytes()).decode() == TEXT


def test_large_compressed_dictionary_is_not_mistaken_for_a_log(tmp_path: Path):
    f = tmp_path / "U.gz"
    body = TEXT + "".join(f"// line {i} with some padding to make it big\n" for i in range(20000))
    f.write_bytes(gzip.compress(body.encode(), compresslevel=0))
    assert f.stat().st_size > 100 * 1024
    assert is_large_non_foam_file(f)[0] is False
