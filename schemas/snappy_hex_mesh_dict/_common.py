# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from schemas._base import FOUNDATION_SERIES, OPENCFD_SERIES, ChoiceItem

_BOTH = (FOUNDATION_SERIES, OPENCFD_SERIES)

# OpenFOAM's Switch accepts all of these spellings in both forks
# (src/OpenFOAM/primitives/bools/Switch/Switch.cxx), so none of them is
# fork-specific.
SWITCH_CHOICES = (
    ChoiceItem("true", "Enable.", _BOTH),
    ChoiceItem("false", "Disable.", _BOTH),
    ChoiceItem("yes", "Alternative enabled form.", _BOTH),
    ChoiceItem("no", "Alternative disabled form.", _BOTH),
    ChoiceItem("on", "Alternative enabled form.", _BOTH),
    ChoiceItem("off", "Alternative disabled form.", _BOTH),
)
