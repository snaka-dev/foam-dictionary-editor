# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from schemas._base import FOUNDATION_V13, OPENCFD_SERIES, ChoiceItem

SWITCH_CHOICES = (
    ChoiceItem("true", "Enable.", supported_in=(FOUNDATION_V13, OPENCFD_SERIES)),
    ChoiceItem("false", "Disable.", supported_in=(FOUNDATION_V13, OPENCFD_SERIES)),
    ChoiceItem("yes", "Alternative enabled switch form.", supported_in=(FOUNDATION_V13,)),
    ChoiceItem("no", "Alternative disabled switch form.", supported_in=(FOUNDATION_V13,)),
)
