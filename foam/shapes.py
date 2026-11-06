# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Shared base dataclass for extractor shape classes.

``topo_set_extractor.TopoShape``, ``set_fields_extractor.SetFieldsShape``,
``sampling_extractor.SamplingShape``, and ``snappy_hex_mesh_extractor.SnappyShape``
all describe one renderable (or listable) shape pulled out of a dictionary
tree, and share this ``label``/``kind``/``geometry`` field scheme — display
name, geometry/source keyword, and the parsed geometry dict whose keys depend
on ``kind`` — plus whatever extra fields their own source format needs (e.g.
topoSet's ``action``, snappyHexMesh's ``category``/``level``/``mode``). This is
what the BlockMesh panel/renderer (``ui/panels/block_mesh_renderer.py``) and
the Export-STL dialog (``ui/dialogs/export_stl_dialog.py``) consume; see
DEVELOPER.md's ``foam/`` extractor bullets for the full picture.
"""
from __future__ import annotations

import dataclasses


@dataclasses.dataclass
class SourceShape:
    """Common fields shared by every extractor shape class."""

    label: str      # display name (entry/action name, or a summary for setFields)
    kind: str       # geometry/source keyword, e.g. "boxToCell", "sphere", "plane"
    geometry: dict  # parsed geometry: keys depend on `kind`
    # Basename of the file this shape came from, stamped by the UI layer rather than the
    # extractor -- an extractor is handed a tree, not a path. Empty until then.
    #
    # Every one of these dictionaries can be present more than once in a case under a
    # non-default name (`topoSetDict-slices`, `topoSetDict.1`), and the panel merges all
    # loaded files into one overlay menu, so a shape has to be able to say which file it
    # came from. Sampling needed this first and carried the field alone; it moved here when
    # the other three gained the same ability.
    # kw_only so the subclasses' own required fields (TopoShape.action,
    # SnappyShape.category) can still follow a field that has a default.
    source_file: str = dataclasses.field(default="", kw_only=True)
