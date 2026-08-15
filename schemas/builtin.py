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
            # Structural keys first, then the generated coefficient modules —
            # the registry merges them into one table per file.
            "schemas.turbulence_structure",
            "schemas.turbulence_properties",
            "schemas.momentum_transport",
            # The viscosity models. Foundation renamed the file
            # constant/transportProperties -> constant/physicalProperties at
            # v10 and moved the non-Newtonian models into the momentum
            # transport tree at the same time, so physicalProperties reads
            # `nu` and nothing else — the two are not the same table.
            "schemas.transport_properties",
            "schemas.physical_properties",
        ],
    }
