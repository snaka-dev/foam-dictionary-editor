# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for the boundary table's per-cell label (_make_cell_item)."""
from __future__ import annotations

from foam.parser import OpenFoamParser
from ui.panels.boundary_view_panel import _EXTRA_LINE_CHAR_LIMIT, _make_cell_item

# A postProcess-written field (wallHeatFlux, gradT, ...) carries a full
# nonuniform list on each wall patch.
_VALUES = "\n".join("234.854" for _ in range(2250))
_FIELD = f"""
boundaryField
{{
    hot
    {{
        type            calculated;
        value           nonuniform List<scalar>
2250
(
{_VALUES}
)
;
    }}
    other
    {{
        type            fixedValue;
        note            "{"x" * 300}";
    }}
}}
"""


def _patch(name: str):
    root = OpenFoamParser(_FIELD).parse()
    bf = next(c for c in root.children if c.name == "boundaryField")
    return next(c for c in bf.children if c.name == name)


def test_nonuniform_list_is_summarised(qapp):
    item = _make_cell_item(_patch("hot"), "/case/0/wallHeatFlux", "hot", n_lines=3)
    assert item.text() == "calculated †\nvalue  nonuniform List<scalar> (2250 values)"
    assert "234.854" not in item.text()


def test_long_value_is_cut(qapp):
    item = _make_cell_item(_patch("other"), "/case/0/U", "other", n_lines=3)
    extra = item.text().split("\n")[1]
    assert extra.endswith(" …")
    assert len(extra) <= len("note  ") + _EXTRA_LINE_CHAR_LIMIT + 2
