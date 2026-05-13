# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
import pytest
from foam.utils import (
    format_embedded_value,
    format_scalar,
    is_int,
    is_number,
    parse_box_pair,
)


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
