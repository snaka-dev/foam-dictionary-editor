# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations


def get_default_schema_config() -> dict:
    """Return the default schema configuration."""
    return {
        "schema_modules": [
            "schemas.control_dict",
            "schemas.fv_schemes",
            "schemas.fv_solution",
            "schemas.block_mesh_dict",
            "schemas.snappy_hex_mesh_dict",
        ],
    }
