# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from schemas._base import BOTH, ChoiceItem

# OpenFOAM's Switch accepts all of these spellings in both forks
# (src/OpenFOAM/primitives/bools/Switch/Switch.cxx), so none of them is
# fork-specific.
#
# Deliberately not `schemas._base.SWITCH_CHOICES`: this tuple names true/false
# as the primary pair and marks the rest as alternative spellings, wording that
# the Detail panel shows to the user. The shared tuple describes every spelling
# the same way, so importing it here would change visible text.
SWITCH_CHOICES = (
    ChoiceItem("true", "Enable.", BOTH),
    ChoiceItem("false", "Disable.", BOTH),
    ChoiceItem("yes", "Alternative enabled form.", BOTH),
    ChoiceItem("no", "Alternative disabled form.", BOTH),
    ChoiceItem("on", "Alternative enabled form.", BOTH),
    ChoiceItem("off", "Alternative disabled form.", BOTH),
)
