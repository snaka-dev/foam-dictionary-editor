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
FOUNDATION_V14 = "Foundation v14"

# OpenCFD (OpenFOAM.com) releases. Two a year, `yymm` with mm = 06 or 12; the
# list is complete, so a gap in it is a missing release rather than a year in
# which OpenCFD shipped once.
OPENCFD_V2106  = "OpenCFD v2106"
OPENCFD_V2112  = "OpenCFD v2112"
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
#
# The adjective and the span do different jobs, and both bind. "Collective"
# says why a key qualifies — it is shared, not release-specific. The range says
# what was actually checked: these entries were audited across Foundation 7-13
# and OpenCFD v2106-v2606 (commit 15720b5, with per-file tutorial coverage
# measured before and after), so the string is a verification record, not a
# synonym for "the whole fork". Extending either end therefore costs the same
# audit that earned it, and is not free when a new release appears — a
# collective label is exempt from naming *one* release, not from measurement.
# The Foundation span reaches v14 because it was measured there, not because a
# release appeared: `tools/scan_foundation14_keys.py` differentially scanned
# foundation-13 against foundation-14 (source *and* tutorials), and the model
# coefficient dictionaries — whose names never appear as literals, being built
# as `typeName + "Coeffs"` — are covered by foamlore's own reading of
# `dictionary::optionalTypeDict` under item 8.
FOUNDATION_SERIES = "Foundation v7-v14"
OPENCFD_SERIES    = "OpenCFD v2106-v2606"

# A Foundation span that *closed* at 13: read through v13, measured absent in
# v14. This is no longer the "not yet looked at" label it was written as — the
# item 9 scan (2026-08-14) measured every key that carried it against complete
# `src` + `applications` trees for both releases, and the ~21 stragglers
# resolved into keys that were widened, keys that were never Foundation's at
# all, and this one. It is now carried by `processorAgglomerator` alone.
#
# The sentence this comment used to end with has inverted, and the inversion is
# the point: a key measured and found absent in v14 is exactly what belongs
# here, always beside a `deprecated_since` saying so. A key nobody has looked at
# does not — there are none, which is why `OPEN_ENDED_SERIES` below is empty.
FOUNDATION_V7_V13 = "Foundation v7-v13"

# Shorthand for the common case: a key or choice supported by both forks
# across every measured release. The default `supported_in` for `entry()`
# below, and otherwise passed explicitly wherever a `ChoiceItem`/`KeySchema`
# is built outside that helper.
BOTH = (FOUNDATION_SERIES, OPENCFD_SERIES)

# Ranges, for an entry that arrived in a known release and has been there ever
# since. Same purpose as the series labels — say where a key exists, not which
# releases happened to be measured — but honest about the lower bound.
# These are emitted by foamlore's generator, each because a coefficient or a
# whole model arrived in that release and has been there since: v8 is the
# Foundation rename of constant/turbulenceProperties to
# constant/momentumTransport, v9 added kOmega2006, v10 moved Smagorinsky's Ck
# into LESeddyViscosity, v2206 added EBRSM, v2212 added the SpalartAllmaras
# ft2 term, and v2412 changed a GEKO default. Foundation 14 added no
# coefficient and dropped none, so the three Foundation ranges below simply
# extend to it rather than closing.
FOUNDATION_V8_V14   = "Foundation v8-v14"
FOUNDATION_V9_V14   = "Foundation v9-v14"
FOUNDATION_V10_V14  = "Foundation v10-v14"
FOUNDATION_V11_V14  = "Foundation v11-v14"
OPENCFD_V2206_V2606 = "OpenCFD v2206-v2606"
OPENCFD_V2212_V2606 = "OpenCFD v2212-v2606"
OPENCFD_V2412_V2606 = "OpenCFD v2412-v2606"

# A closed range, for an entry that existed for a span and was then
# superseded — the opposite shape from the "still there" ranges above.
# SpalartAllmaras's sigmaNut read scalar(2)/scalar(3) through v2106, v2112
# and v2206, then changed to the literal 0.66666 at v2212 (foamlore
# request item 6, the generator's spec: v2112 was the missing
# checkout that turned the old "v2106, v2206" explicit pair, which read as
# "skipped v2112", into this measured range).
OPENCFD_V2106_V2206 = "OpenCFD v2106-v2206"

# Another closed range, from the viscosity models (foamlore spec item 7,
# transport half). Casson::read() reads its clipping limits under the keys
# "nuMin_" and "nuMax_" -- with the member's trailing underscore, an upstream
# typo -- from v2106 through v2212, fixed to "nuMin"/"nuMax" at v2306. Both
# forks shipped it; Foundation never fixed it, because the family moved out of
# transportProperties at v10 before anyone noticed.
OPENCFD_V2106_V2212 = "OpenCFD v2106-v2212"

# Closed Foundation spans, all measured by the item 9 scan (2026-08-14) against
# complete `src` + `applications` trees. Each names a key Foundation once read
# and dropped while OpenCFD still reads it as current -- so the entry keeps its
# `OPENCFD_SERIES` tag beside one of these, plus a `deprecated_since` saying
# which release stopped reading it. That combination is what distinguishes
# "measured and gone" from "not yet looked at"; see `FOUNDATION_V7_V13` above.
FOUNDATION_V7_V9  = "Foundation v7-v9"    # minTriangleTwist, dropped at v10
FOUNDATION_V7_V11 = "Foundation v7-v11"   # functions timeStart/timeEnd, at v12
FOUNDATION_V7_V12 = "Foundation v7-v12"   # maxDi and functions regionType, v13

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
    #: What OpenFOAM uses when the key is absent, spelled as the source spells
    #: it. Empty means "no default recorded here", NOT "there is no default" --
    #: `required` is how the second is said. The distinction matters because the
    #: generated turbulence modules still carry their defaults in `description`
    #: prose, so an empty field there is silence, not a claim.
    default: str = ""
    #: The reader has no fallback: omitting the key is an error rather than a
    #: choice. Mutually exclusive with `default` -- a key cannot both have a
    #: default and require you to supply one, and a test asserts no schema does
    #: both. This is the one fact prose could not express: `required` is
    #: machine-readable, so a future "your case omits a required key" check can
    #: consume it, which a sentence in `description` could never support.
    required: bool = False


def _versions_text(items: tuple[str, ...]) -> str:
    return ", ".join(items)


#: Labels whose span ends where the measuring stopped, not where the fork did.
#: The Detail pane qualifies these, because shown bare a v7-v13 span reads to a
#: v14 user as "not available in the release you are running" — the same
#: misreading that once told OpenCFD users 61 shared keys were Foundation-only.
#:
#: **Empty, and that is the closed state of the generator's spec item
#: 9** — not an oversight, and not a set waiting to be filled. Every span FoDE
#: carries now ends where the measuring found an end, so no label needs the
#: caveat and the Detail pane appends nothing.
#:
#: The rule for putting one back: a label belongs here only while some live
#: schema carries it *without* a `deprecated_since`. That combination is what
#: "we stopped looking" means. A closed span beside a `deprecated_since` means
#: "we looked and it is gone" and must stay out, or the pane would tell a user
#: a measured removal might just be an unchecked release.
#:
#: Naming the *fact* here and the wording in `ui/` keeps this module i18n-free.
#: `tests/ui/test_supported_in_caveat.py` enforces the rule in both directions.
OPEN_ENDED_SERIES: frozenset[str] = frozenset()


def has_unmeasured_successor(items: tuple[str, ...]) -> bool:
    """Whether any label in `items` stops at the newest release we measured."""
    return any(item in OPEN_ENDED_SERIES for item in items)


# OpenFOAM's Switch accepts all of these spellings in both forks
# (src/OpenFOAM/primitives/bools/Switch/Switch.cxx), so none of them is
# fork-specific.
#
# This is the plain spelling list, in the order controlDict and fvSolution
# present it. Two schema modules deliberately keep their own tuple instead of
# importing this one, and should stay that way: turbulence_structure.py leads
# with on/off because `turbulence on;` is how the tutorials spell it, and
# snappy_hex_mesh_dict/_common.py names true/false as the primary pair and the
# rest as alternative forms. Both orderings and both wordings reach the user in
# the Detail panel's choice list, so folding them in here would change visible
# text, not just remove duplication.
SWITCH_CHOICES = (
    ChoiceItem("yes", "Enabled.", BOTH),
    ChoiceItem("no", "Disabled.", BOTH),
    ChoiceItem("true", "Enabled.", BOTH),
    ChoiceItem("false", "Disabled.", BOTH),
    ChoiceItem("on", "Enabled.", BOTH),
    ChoiceItem("off", "Disabled.", BOTH),
)


def entry(key: str, label: str, description: str,
          choices: tuple[ChoiceItem, ...] = (),
          supported_in: tuple[str, ...] = BOTH, note: str = "") -> KeySchema:
    """Build a `KeySchema` for a key supported in both forks unless overridden.

    The shared shape behind each schema module's local `_entry`/`entry`
    helper: same key/label/description/choices, `supported_in` defaulting to
    `BOTH` for the common case, and an optional `note`.
    """
    return KeySchema(
        key=key, label=label, description=description,
        supported_in=supported_in, choices=choices, note=note,
    )
