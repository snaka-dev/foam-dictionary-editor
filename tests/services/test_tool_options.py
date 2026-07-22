# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for services/tool_options.py (Run-tool option specs and commands)."""
from __future__ import annotations

import pytest

from services.tool_options import (
    TOOL_SPECS,
    ToolOption,
    ToolSpec,
    build_args,
    build_command,
    default_values,
)


class TestSpecs:
    def test_all_expected_tools_present(self):
        assert set(TOOL_SPECS) == {
            "blockMesh",
            "snappyHexMesh",
            "topoSet",
            "setFields",
            "checkMesh",
        }

    def test_spec_name_matches_key(self):
        for key, spec in TOOL_SPECS.items():
            assert spec.name == key

    def test_snappy_overwrite_defaults_on(self):
        values = default_values(TOOL_SPECS["snappyHexMesh"])
        assert values["-overwrite"] is True

    def test_defaults_produce_expected_commands(self):
        for name, expected in [
            ("blockMesh", "blockMesh 2>&1 | tee log.blockMesh"),
            (
                "snappyHexMesh",
                "snappyHexMesh -overwrite 2>&1 | tee log.snappyHexMesh",
            ),
            ("topoSet", "topoSet 2>&1 | tee log.topoSet"),
            ("setFields", "setFields 2>&1 | tee log.setFields"),
            ("checkMesh", "checkMesh 2>&1 | tee log.checkMesh"),
        ]:
            spec = TOOL_SPECS[name]
            assert build_command(spec, default_values(spec)) == expected


class TestBuildArgs:
    SPEC = ToolSpec(
        "demoTool",
        (
            ToolOption("-flagA", "a bool"),
            ToolOption("-flagB", "a bool on by default", "bool", True),
            ToolOption("-value", "a value", "value"),
            ToolOption("-dict", "a file", "file"),
        ),
    )

    def test_defaults(self):
        assert build_args(self.SPEC, default_values(self.SPEC)) == ["-flagB"]

    def test_bool_toggling(self):
        values = {"-flagA": True, "-flagB": False}
        assert build_args(self.SPEC, values) == ["-flagA"]

    def test_empty_value_options_are_omitted(self):
        values = {"-value": "   ", "-dict": ""}
        assert build_args(self.SPEC, values) == ["-flagB"]

    def test_value_options_keep_spec_order(self):
        values = {
            "-flagA": True,
            "-flagB": False,
            "-value": "fluid",
            "-dict": "system/demoDict",
        }
        assert build_args(self.SPEC, values) == [
            "-flagA",
            "-value",
            "fluid",
            "-dict",
            "system/demoDict",
        ]

    def test_extra_is_shlex_split(self):
        args = build_args(self.SPEC, {"-flagB": False}, extra="-time '0.5' -noSync")
        assert args == ["-time", "0.5", "-noSync"]

    def test_extra_with_unbalanced_quote_raises(self):
        with pytest.raises(ValueError):
            build_args(self.SPEC, {}, extra="-y '[0:1]")

    def test_unknown_flags_in_values_are_ignored(self):
        # Stale session state (e.g. after a spec change) must not leak into
        # the command line.
        assert build_args(self.SPEC, {"-flagB": False, "-gone": True}) == []


class TestBuildCommand:
    SPEC = ToolSpec("demoTool", (ToolOption("-dict", "a file", "file"),))

    def test_tee_log_uses_tool_name(self):
        cmd = build_command(self.SPEC, {})
        assert cmd.endswith("2>&1 | tee log.demoTool")

    def test_values_needing_quotes_are_quoted(self):
        cmd = build_command(self.SPEC, {"-dict": "system/my dict"})
        assert cmd == "demoTool -dict 'system/my dict' 2>&1 | tee log.demoTool"

    def test_extra_tokens_are_requoted(self):
        cmd = build_command(self.SPEC, {}, extra="-y [0:1]")
        assert cmd == "demoTool -y '[0:1]' 2>&1 | tee log.demoTool"

    def test_prefix_is_prepended_raw(self):
        cmd = build_command(
            self.SPEC, {}, prefix="rm -rf 0 && cp -r 0.orig 0 && "
        )
        assert cmd == (
            "rm -rf 0 && cp -r 0.orig 0 && demoTool 2>&1 | tee log.demoTool"
        )
