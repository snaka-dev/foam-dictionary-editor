# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# Foundation (OpenFOAM.org) releases.
FOUNDATION_V7  = "Foundation v7"
FOUNDATION_V8  = "Foundation v8"
FOUNDATION_V9  = "Foundation v9"
FOUNDATION_V10 = "Foundation v10"
FOUNDATION_V11 = "Foundation v11"
FOUNDATION_V12 = "Foundation v12"
FOUNDATION_V13 = "Foundation v13"

# OpenCFD (OpenFOAM.com) releases.
OPENCFD_V2106  = "OpenCFD v2106"
OPENCFD_V2206  = "OpenCFD v2206"
OPENCFD_V2212  = "OpenCFD v2212"
OPENCFD_V2306  = "OpenCFD v2306"
OPENCFD_V2312  = "OpenCFD v2312"
OPENCFD_V2406  = "OpenCFD v2406"
OPENCFD_V2412  = "OpenCFD v2412"
OPENCFD_V2506  = "OpenCFD v2506"
OPENCFD_V2512  = "OpenCFD v2512"
OPENCFD_V2606  = "OpenCFD v2606"

# Collective labels, for entries shared across a whole fork rather than tied to
# one release. Most of the finiteVolume/lduMatrix surface is in this category:
# tagging such a key with a single release reads as "only available there".
FOUNDATION_SERIES = "Foundation v7-v13"
OPENCFD_SERIES    = "OpenCFD v2106-v2606"

# Ranges, for an entry that arrived in a known release and has been there ever
# since. Same purpose as the series labels — say where a key exists, not which
# releases happened to be measured — but honest about the lower bound.
# These are emitted by foamlore's generator, each because a coefficient or a
# whole model arrived in that release and has been there since: v8 is the
# Foundation rename of constant/turbulenceProperties to
# constant/momentumTransport, v9 added kOmega2006, v10 moved Smagorinsky's Ck
# into LESeddyViscosity, v2206 added EBRSM, v2212 added the SpalartAllmaras
# ft2 term, and v2412 changed a GEKO default.
FOUNDATION_V8_V13   = "Foundation v8-v13"
FOUNDATION_V9_V13   = "Foundation v9-v13"
FOUNDATION_V10_V13  = "Foundation v10-v13"
OPENCFD_V2206_V2606 = "OpenCFD v2206-v2606"
OPENCFD_V2212_V2606 = "OpenCFD v2212-v2606"
OPENCFD_V2412_V2606 = "OpenCFD v2412-v2606"

# What a key entry represents. Most keys are `valid`; the other two exist
# because OpenFOAM dictionaries in the wild are full of names that are no
# longer current, or that never worked at all.
#
# `renamed`     - a historical spelling. OpenCFD declares these in source as
#                 `getCompat("newName", {{"oldName", api}})`, so the successor
#                 and the API version are both recoverable; see DEVELOPER.md.
# `ineffective` - the key appears in official tutorials but no reader consumes
#                 it, so writing it has no effect. `minFlatness` is the type
#                 case: both forks read `minFaceFlatness`, yet motorBike has
#                 shipped `minFlatness 0.5;` since OpenFOAM-2.3.x.
KeyStatus = Literal["valid", "renamed", "ineffective"]


@dataclass(frozen=True)
class ChoiceItem:
    value: str
    description: str
    supported_in: tuple[str, ...] = ()
    note: str = ""
    status: KeyStatus = "valid"
    #: For `renamed`/`ineffective`, the value that should be written instead.
    use_instead: str = ""
    #: Version or API level at which this spelling stopped being current.
    deprecated_since: str = ""


@dataclass(frozen=True)
class KeySchema:
    key: str
    label: str
    description: str
    supported_in: tuple[str, ...] = ()
    note: str = ""
    choices: tuple[ChoiceItem, ...] = ()
    status: KeyStatus = "valid"
    #: For `renamed`, the current key name; for `ineffective`, the key OpenFOAM
    #: actually reads. One field rather than two, because `status` already says
    #: which of the two situations it is and the Detail pane words it from that.
    use_instead: str = ""
    #: Historical spellings of *this* key, so a schema can be found from an old
    #: name and so the current entry can mention where it came from.
    renamed_from: tuple[str, ...] = ()
    #: Version or API level at which the old spelling stopped being current,
    #: e.g. "v1712" for minMedianAxisAngle -> minMedialAxisAngle.
    deprecated_since: str = ""


def _versions_text(items: tuple[str, ...]) -> str:
    return ", ".join(items)
