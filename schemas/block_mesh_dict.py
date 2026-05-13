# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from schemas._base import (
    ChoiceItem, KeySchema,
    FOUNDATION_V13, OPENCFD_SERIES,
)

TARGET_FILE = "blockMeshDict"

SCHEMAS: dict[str, KeySchema] = {
    "convertToMeters": KeySchema(
        key="convertToMeters",
        label="Convert To Meters",
        description=(
            "Scaling factor applied to all vertex coordinates. "
            "A value of 0.001 converts millimetres to metres."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        note=(
            "Foundation v13 uses 'scale' as the canonical key; "
            "older cases and OpenCFD releases commonly use 'convertToMeters'. "
            "Both forms are typically accepted."
        ),
    ),
    "scale": KeySchema(
        key="scale",
        label="Scale",
        description=(
            "Scaling factor applied to all vertex coordinates. "
            "Equivalent to convertToMeters; preferred in Foundation v13."
        ),
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        note="Use 'scale' in Foundation v13 cases; 'convertToMeters' in older or OpenCFD cases.",
    ),
    "mergeType": KeySchema(
        key="mergeType",
        label="Merge Type",
        description="Controls how block topology is merged when building the final mesh.",
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        choices=(
            ChoiceItem(
                "merge",
                "Merge coincident points between adjacent blocks.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "points",
                "Match points between blocks without full topological merge.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
        ),
    ),
    "verbose": KeySchema(
        key="verbose",
        label="Verbose",
        description="When enabled, blockMesh writes additional diagnostic output during meshing.",
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        choices=(
            ChoiceItem("true", "Enable verbose output.", supported_in=(FOUNDATION_V13, OPENCFD_SERIES)),
            ChoiceItem("false", "Disable verbose output.", supported_in=(FOUNDATION_V13, OPENCFD_SERIES)),
            ChoiceItem("yes", "Alternative enabled switch form.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("no", "Alternative disabled switch form.", supported_in=(FOUNDATION_V13,)),
        ),
    ),
}
