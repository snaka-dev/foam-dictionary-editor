# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Suffixed variants in the file list: listed, dimmed, and explained in the tooltip."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from ui.theme import colors


def _dict(obj: str) -> str:
    return (
        "FoamFile\n{\n    version 2.0;\n    format ascii;\n    class dictionary;\n"
        f"    object {obj};\n}}\n"
    )


def _item(panel, path: str):
    for i in range(panel._list.count()):
        item = panel._list.item(i)
        if item.data(Qt.ItemDataRole.UserRole) == path:
            return item
    return None


def test_variant_row_is_dimmed_with_a_tooltip(main_window, tmp_path: Path):
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "controlDict").write_text(_dict("controlDict"))
    (tmp_path / "system" / "decomposeParDict").write_text(_dict("decomposeParDict"))
    (tmp_path / "system" / "decomposeParDict.4").write_text(_dict("decomposeParDict"))
    main_window._load_case_dir(str(tmp_path))
    panel = main_window.file_list_panel

    variant = _item(panel, str(tmp_path / "system" / "decomposeParDict.4"))
    assert variant is not None
    assert "A variant of decomposeParDict" in variant.toolTip()
    assert variant.foreground().color() == QColor(colors().file_text_only_fg)

    base = _item(panel, str(tmp_path / "system" / "decomposeParDict"))
    assert "A variant of" not in base.toolTip()
    assert base.foreground().color() != QColor(colors().file_text_only_fg)
