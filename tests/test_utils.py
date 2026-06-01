# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
import pytest
from foam.utils import (
    format_embedded_value,
    format_scalar,
    is_int,
    is_large_non_foam_file,
    is_number,
    parse_box_pair,
)


class TestIsLargeNonFoamFile:
    def test_small_file_no_header_not_flagged(self, tmp_path):
        f = tmp_path / "custom_dict"
        f.write_bytes(b"someKey 1;\n")
        flag, size = is_large_non_foam_file(f)
        assert flag is False
        assert size == f.stat().st_size

    def test_large_file_with_foam_header_not_flagged(self, tmp_path):
        f = tmp_path / "U"
        content = b"FoamFile\n{\n    version 2.0;\n}\n" + b"x " * 60_000
        f.write_bytes(content)
        flag, size = is_large_non_foam_file(f)
        assert flag is False
        assert size == len(content)

    def test_large_file_without_foam_header_flagged(self, tmp_path):
        f = tmp_path / "log.simpleFoam"
        content = b"Starting simpleFoam\n" + b"residual 0.001\n" * 8_000
        f.write_bytes(content)
        assert len(content) > 100 * 1024
        flag, size = is_large_non_foam_file(f)
        assert flag is True
        assert size == len(content)

    def test_missing_file_returns_false_zero(self, tmp_path):
        flag, size = is_large_non_foam_file(tmp_path / "nonexistent")
        assert flag is False
        assert size == 0

    def test_foam_header_anywhere_in_sniff_window_not_flagged(self, tmp_path):
        f = tmp_path / "dict_with_comment"
        content = b"// comment\nFoamFile\n{\n}\n" + b"y " * 60_000
        f.write_bytes(content)
        flag, _ = is_large_non_foam_file(f)
        assert flag is False


class TestIsInt:
    def test_positive(self):
        assert is_int("1") is True

    def test_zero(self):
        assert is_int("0") is True

    def test_negative(self):
        assert is_int("-5") is True

    def test_float_rejected(self):
        assert is_int("1.0") is False

    def test_scientific_lower_rejected(self):
        assert is_int("1e3") is False

    def test_scientific_upper_rejected(self):
        assert is_int("1E3") is False

    def test_word_rejected(self):
        assert is_int("abc") is False

    def test_empty_rejected(self):
        assert is_int("") is False


class TestIsNumber:
    def test_integer_string(self):
        assert is_number("1") is True

    def test_float_string(self):
        assert is_number("1.0") is True

    def test_negative_float(self):
        assert is_number("-2.5") is True

    def test_scientific_notation(self):
        assert is_number("1e-3") is True

    def test_word_rejected(self):
        assert is_number("abc") is False

    def test_empty_rejected(self):
        assert is_number("") is False


class TestFormatScalar:
    def test_int_value(self):
        assert format_scalar(1) == "1"

    def test_negative_int(self):
        assert format_scalar(-3) == "-3"

    def test_float_that_is_integer(self):
        assert format_scalar(2.0) == "2"

    def test_float_non_integer(self):
        result = format_scalar(1.5)
        assert float(result) == pytest.approx(1.5)

    def test_string_passthrough(self):
        assert format_scalar("word") == "word"

    def test_high_precision_roundtrip(self):
        val = 1.23456789012345
        assert float(format_scalar(val)) == pytest.approx(val, rel=1e-10)


class TestParseBoxPair:
    def test_unit_box(self):
        assert parse_box_pair("(0 0 0) (1 1 1)") == [[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]

    def test_negative_values(self):
        assert parse_box_pair("(-1.0 -2.0 -3.0) (1.0 2.0 3.0)") == [
            [-1.0, -2.0, -3.0],
            [1.0, 2.0, 3.0],
        ]

    def test_extra_whitespace(self):
        assert parse_box_pair("  ( 0 0 0 )  ( 1 1 1 )  ") == [
            [0.0, 0.0, 0.0],
            [1.0, 1.0, 1.0],
        ]

    def test_single_vector_returns_none(self):
        assert parse_box_pair("(0 0 0)") is None

    def test_missing_closing_paren_returns_none(self):
        assert parse_box_pair("(0 0 0) (1 1 1") is None

    def test_wrong_vector_length_returns_none(self):
        assert parse_box_pair("(0 0) (1 1 1)") is None

    def test_non_numeric_returns_none(self):
        assert parse_box_pair("(a b c) (1 1 1)") is None

    def test_empty_string_returns_none(self):
        assert parse_box_pair("") is None

    def test_no_parens_returns_none(self):
        assert parse_box_pair("0 0 0 1 1 1") is None


class TestFormatEmbeddedValue:
    def test_vector(self):
        assert format_embedded_value("vector", [1.0, 2.0, 3.0], None) == "(1 2 3)"

    def test_int_list(self):
        assert format_embedded_value("int_list", [1, 2, 3], None) == "(1 2 3)"

    def test_scalar_list(self):
        result = format_embedded_value("scalar_list", [1.5, 2.0], None)
        assert result.startswith("(") and result.endswith(")")
        assert "1.5" in result and "2" in result

    def test_raw_list_with_parens(self):
        assert format_embedded_value("raw_list", None, "(a b c)") == "(a b c)"

    def test_raw_list_without_parens_adds_them(self):
        assert format_embedded_value("raw_list", None, "a b c") == "(a b c)"

    def test_raw_list_falls_back_to_value_when_no_raw(self):
        result = format_embedded_value("raw_list", "x y", None)
        assert "x y" in result

    def test_int_type(self):
        assert format_embedded_value("int", 5, None) == "5"

    def test_scalar_type(self):
        assert float(format_embedded_value("scalar", 1.5, None)) == pytest.approx(1.5)

    def test_unknown_type_uses_raw_value(self):
        assert format_embedded_value("word", "parsed", "raw") == "raw"

    def test_unknown_type_falls_back_to_value_when_no_raw(self):
        assert format_embedded_value("word", "parsed", None) == "parsed"
