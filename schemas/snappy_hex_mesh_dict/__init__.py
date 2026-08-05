# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from schemas._base import KeySchema

from . import (
    _add_layers,
    _castellated_mesh,
    _geometry,
    _mesh_quality,
    _snap_controls,
    _structure,
)

TARGET_FILE = "snappyHexMeshDict"

# _structure first, so a more specific entry in a stage module wins over the
# generic container description.
SCHEMAS: dict[str, KeySchema] = {
    **_structure.SCHEMAS,
    **_geometry.SCHEMAS,
    **_castellated_mesh.SCHEMAS,
    **_snap_controls.SCHEMAS,
    **_add_layers.SCHEMAS,
    **_mesh_quality.SCHEMAS,
}
