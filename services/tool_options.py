# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Option specs and command composition for the Tools-menu "Run *" actions.

Pure Python (no Qt): ``ui/dialogs/run_tool_dialog.py`` builds its widgets from
``TOOL_SPECS`` and delegates command composition to :func:`build_command`, so
the exact command line sent to the terminal stays unit-testable without a GUI.

Each spec lists only a curated handful of common flags; anything else goes
through the dialog's free-text "Extra options" field. Flag availability varies
between OpenFOAM forks and versions, so the curated set sticks to flags
supported by both the openfoam.com and openfoam.org lines.
"""
from __future__ import annotations

import dataclasses
import shlex
from typing import Literal

OptionKind = Literal["bool", "value", "file"]
OptionValue = bool | str


@dataclasses.dataclass(frozen=True)
class ToolOption:
    """One selectable command-line option of an OpenFOAM utility."""

    flag: str
    # Short English description; the dialog passes it through tr().
    label: str
    kind: OptionKind = "bool"
    # bool for "bool" options, str for "value"/"file" options.
    default: OptionValue = False
    # Hint text for "value"/"file" line edits.
    placeholder: str = ""


@dataclasses.dataclass(frozen=True)
class ToolSpec:
    """An OpenFOAM utility runnable from the Tools menu with options."""

    # Executable name; the run log is tee'd to ``log.<name>``.
    name: str
    options: tuple[ToolOption, ...]


_DICT_OPTION = ToolOption(
    "-dict", "Alternative dictionary", "file", "", "e.g. system/blockMeshDict.v2"
)
_REGION_OPTION = ToolOption(
    "-region", "Mesh region (multi-region case)", "value", "", "e.g. fluid"
)

TOOL_SPECS: dict[str, ToolSpec] = {
    "blockMesh": ToolSpec(
        "blockMesh",
        (_DICT_OPTION, _REGION_OPTION),
    ),
    "snappyHexMesh": ToolSpec(
        "snappyHexMesh",
        (
            ToolOption(
                "-overwrite",
                "Overwrite the existing mesh instead of writing a new time directory",
                "bool",
                True,
            ),
            _DICT_OPTION,
            _REGION_OPTION,
        ),
    ),
    "topoSet": ToolSpec(
        "topoSet",
        (_DICT_OPTION, _REGION_OPTION),
    ),
    "setFields": ToolSpec(
        "setFields",
        (_DICT_OPTION, _REGION_OPTION),
    ),
    "checkMesh": ToolSpec(
        "checkMesh",
        (
            ToolOption(
                "-allGeometry", "Run all geometry checks (including non-standard)"
            ),
            ToolOption(
                "-allTopology", "Run all topology checks (including non-standard)"
            ),
            ToolOption(
                "-writeSets",
                "Write faulty cells/faces as sets in this format",
                "value",
                "",
                "e.g. vtk",
            ),
            _REGION_OPTION,
        ),
    ),
}


def default_values(spec: ToolSpec) -> dict[str, OptionValue]:
    """Return the flag → value mapping of a pristine dialog for ``spec``."""
    return {opt.flag: opt.default for opt in spec.options}


def build_args(
    spec: ToolSpec, values: dict[str, OptionValue], extra: str = ""
) -> list[str]:
    """Compose the argument tokens for ``spec`` from dialog values.

    ``values`` maps a flag to its current value (bool for checkboxes, str for
    value/file fields; empty strings mean "not given"). ``extra`` is free
    shell-like text split with shlex; a malformed value (e.g. an unbalanced
    quote) raises ValueError.
    """
    args: list[str] = []
    for opt in spec.options:
        value = values.get(opt.flag, opt.default)
        if opt.kind == "bool":
            if value:
                args.append(opt.flag)
        else:
            # Guard against non-string values (e.g. the bool False default of
            # a spec that omits an explicit "" default, or stale session
            # state): only genuine text becomes a flag argument.
            text = value.strip() if isinstance(value, str) else ""
            if text:
                args += [opt.flag, text]
    extra = extra.strip()
    if extra:
        args += shlex.split(extra)
    return args


def build_command(
    spec: ToolSpec,
    values: dict[str, OptionValue],
    extra: str = "",
    prefix: str = "",
) -> str:
    """Compose the full shell command sent to the terminal panel.

    The output is always tee'd to ``log.<tool>`` — the log-summary feature and
    the Allrun "logs already exist" pre-flight rely on those exact filenames,
    so the log redirection is composed here rather than left to the user.
    ``prefix`` is an optional raw shell prefix (e.g. ``"rm -rf 0 && … && "``).
    """
    tokens = [spec.name, *build_args(spec, values, extra)]
    return f"{prefix}{shlex.join(tokens)} 2>&1 | tee log.{spec.name}"
