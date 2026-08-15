#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Shinji NAKAGAWA
"""Differential scan of collectively-tagged Foundation keys against a newer checkout.

`schemas/_base.py`'s `FOUNDATION_SERIES` span is a verification record, not a
synonym for "the whole fork" (see the generator's spec item 9), so
extending it costs a measurement, and this script is that measurement: for every
hand-written key carrying either collective Foundation label, it looks for the
key name in two OpenFOAM source checkouts and reports what changed between them.

Usage:
    python3 tools/scan_foundation14_keys.py
    python3 tools/scan_foundation14_keys.py --sources ../foamlore/sources \\
        --old foundation-13 --new foundation-14 --subtrees src,applications

Why a *differential* scan. The checkouts are sparse — foamlore fetches only the
subtrees its own derivation needs — so "key not found in the new tree" is
ambiguous on its own: the key may be gone, or its reader may simply not be
checked out. Comparing against the older tree with the identical method removes
that ambiguity:

    present in old AND new  -> STILL READ    (evidence the key survives)
    present in old, not new -> REMOVED       (the finding worth having)
    absent from both        -> ABSENT        (no reader found; see below)

The third verdict used to be called NOT COVERED, and the rename records a real
change in what it means. Once both checkouts hold all of `src` and
`applications`, absence is no longer "we did not look there" — it is evidence
the release does not read the key, and the likely follow-up is that the key
belongs to the *other* fork. It is still not proof, because a name assembled at
runtime appears as no literal at all; `<Model>Coeffs` (`typeName + "Coeffs"`)
and `executeInterval` (`prefix_ + "Interval"`) are the standing examples, and
the second was very nearly retagged out of Foundation on this scan's word.
Read every ABSENT by hand.

Matching is deliberately over-inclusive: a key counts as present if its name
appears as a double-quoted C++ string literal anywhere in a `.C`/`.H` file. That
admits comments and unrelated uses, which is the right bias here — a false
"STILL READ" understates what needs a closer look, while a false "REMOVED"
would be noticed immediately on inspection. Every REMOVED hit is meant to be
read by a human, not trusted blindly.

Exit status is 0 whatever the findings; this is a report, not a test.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from schemas._base import (  # noqa: E402
    FOUNDATION_SERIES,
    FOUNDATION_V7_V13,
    FOUNDATION_V13,
)

#: The Foundation labels whose span this tool can speak to. `FOUNDATION_V7_V13`
#: is the live target -- the keys still unmeasured, which this tool exists to
#: retire. `FOUNDATION_SERIES` is kept in scope so a re-run re-verifies what was
#: already widened, rather than only ever looking at the shrinking remainder.
#: `FOUNDATION_V13` catches the explicit enumerations that stop at 13 rather
#: than using a collective label -- today only `geometry.radius1`/`radius2` --
#: so a span ending one release short is measured rather than hand-grepped, and
#: any future one is picked up without editing this list.
SCANNED_LABELS = (FOUNDATION_SERIES, FOUNDATION_V7_V13, FOUNDATION_V13)

#: Subtrees compared between the two checkouts. Both must hold the same set or
#: the differential measures the directory layout rather than the source; see
#: `index_tree`.
DEFAULT_SUBTREES = ("src", "applications")

#: Where a release ships dictionaries a user would copy. `etc/caseDicts` is not
#: decoration -- see `index_shipped_dicts`.
SHIPPED_DIRS = ("tutorials", "etc/caseDicts")

#: Hand-written modules whose entries carry a collective label. The generated
#: turbulence modules are excluded on purpose: foamlore measures those already,
#: and they use per-release constants rather than the collective label.
MODULES = (
    "schemas.control_dict",
    "schemas.fv_schemes",
    "schemas.fv_solution",
    "schemas.block_mesh_dict",
    "schemas.turbulence_structure",
    "schemas.snappy_hex_mesh_dict",
)

SOURCE_SUFFIXES = (".C", ".H")


def collect_keys() -> dict[str, set[str]]:
    """Map module name -> set of bare key names carrying a scanned label.

    Table keys are `<parent>.<key>` (and sometimes `<parent>.*`), but what the
    C++ source contains is the bare name, so the parent prefix and the wildcard
    entries are dropped here.
    """
    import importlib

    found: dict[str, set[str]] = {}
    for mod_name in MODULES:
        mod = importlib.import_module(mod_name)
        names: set[str] = set()
        for table_key, schema in mod.SCHEMAS.items():
            if table_key.endswith(".*"):
                continue
            tags = getattr(schema, "supported_in", ())
            if not any(label in tags for label in SCANNED_LABELS):
                continue
            # `schema.key` is the bare name; fall back to the table key's tail.
            names.add(getattr(schema, "key", None) or table_key.rsplit(".", 1)[-1])
        found[mod_name] = names
    return found


def index_tree(root: Path, subtrees: tuple[str, ...]) -> set[str]:
    """Every double-quoted string literal in the named subtrees' C++ sources.

    Scanning *named* subtrees rather than the whole checkout is not tidiness.
    The two trees are not guaranteed to hold the same top-level directories --
    `foundation-14` carries `tutorials/` and `foundation-13` does not -- and a
    handful of `.C`/`.H` files live under `tutorials/`. Rglobbing the root would
    therefore add literals to one side of a *differential* comparison only,
    biasing every verdict toward STILL READ and able to hide a REMOVED outright.
    Naming the subtrees makes both sides measure the same thing by construction.
    """
    literals: set[str] = set()
    pattern = re.compile(r'"([^"\\\n]{1,80})"')
    for name in subtrees:
        base = root / name
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.suffix not in SOURCE_SUFFIXES or not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            literals.update(pattern.findall(text))
    return literals


def index_shipped_dicts(root: Path, keys: set[str]) -> set[str]:
    """Which of `keys` the release *ships* as a dictionary entry.

    Two directories, and the second is not optional. `tutorials/` is the obvious
    one. `etc/caseDicts/` is where Foundation ships its function-object
    templates, and it is the only place some keys appear at all: `executeInterval`
    is in `etc/caseDicts/functions/mesh/checkMesh` and in no `.C` file anywhere,
    because the reader builds the name as `prefix_ + "Interval"`.

    **What a hit means here has inverted.** While the checkouts were sparse this
    was a *rescue* -- evidence for keys whose readers were not fetched. Now that
    `index_tree` covers all of `src` and `applications`, absence from the source
    is itself meaningful, so a key that is shipped with no reader found is the
    `minFlatness` shape: something a release writes into its own cases while
    nothing reads it. That is a candidate for `status="ineffective"`, not
    reassurance.

    A key counts when it opens a line, which is how OpenFOAM writes an entry
    (`key value;` or `key { … }`). Anchoring to line-start keeps a key from
    matching its own use as a *value* elsewhere.
    """
    wanted = {k for k in keys if k.isidentifier()}
    if not wanted:
        return set()
    pattern = re.compile(
        r"^[ \t]*(" + "|".join(sorted(map(re.escape, wanted), key=len, reverse=True)) + r")\b",
        re.MULTILINE,
    )
    seen: set[str] = set()
    for name in SHIPPED_DIRS:
        base = root / name
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            seen.update(pattern.findall(text))
            if seen >= wanted:
                return seen
    return seen


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sources", type=Path, default=REPO_ROOT.parent / "foamlore" / "sources")
    parser.add_argument("--old", default="foundation-13")
    parser.add_argument("--new", default="foundation-14")
    parser.add_argument(
        "--subtrees", default=",".join(DEFAULT_SUBTREES),
        help="comma-separated subtrees to compare; both checkouts must hold the same set",
    )
    args = parser.parse_args(argv)

    subtrees = tuple(s.strip() for s in args.subtrees.split(",") if s.strip())
    old_root, new_root = args.sources / args.old, args.sources / args.new
    for root in (old_root, new_root):
        if not root.is_dir():
            parser.error(f"no such checkout: {root}")

    # A subtree present on one side only would make the comparison measure the
    # checkout layout instead of the source, which is the exact defect the
    # `tutorials`-only-on-the-new-tree asymmetry used to cause.
    lopsided = [s for s in subtrees if (old_root / s).is_dir() != (new_root / s).is_dir()]
    if lopsided:
        parser.error(
            f"subtree(s) {lopsided} exist in only one checkout; expand both "
            f"identically (git sparse-checkout add {' '.join(lopsided)}) first"
        )

    print(f"indexing {old_root} {list(subtrees)} ...", file=sys.stderr)
    old_literals = index_tree(old_root, subtrees)
    print(f"indexing {new_root} {list(subtrees)} ...", file=sys.stderr)
    new_literals = index_tree(new_root, subtrees)

    by_module = collect_keys()
    all_keys = {k for keys in by_module.values() for k in keys}
    print(f"scanning {new_root} {list(SHIPPED_DIRS)} ...", file=sys.stderr)
    shipped = index_shipped_dicts(new_root, all_keys)

    buckets: dict[str, list[tuple[str, str]]] = defaultdict(list)
    per_module: dict[str, dict[str, int]] = {}
    shipped_counts: dict[str, int] = {}
    verdicts = ("STILL READ", "REMOVED", "ABSENT")

    for mod_name, keys in by_module.items():
        counts = dict.fromkeys(verdicts, 0)
        shipped_counts[mod_name] = sum(1 for k in keys if k in shipped)
        for key in sorted(keys):
            if key not in old_literals:
                verdict = "ABSENT"
            elif key in new_literals:
                verdict = "STILL READ"
            else:
                verdict = "REMOVED"
            counts[verdict] += 1
            buckets[verdict].append((mod_name.rsplit(".", 1)[-1], key))
        per_module[mod_name] = counts

    total = sum(sum(c.values()) for c in per_module.values())
    labels = " / ".join(repr(x) for x in SCANNED_LABELS)
    print(f"\n{args.old} -> {args.new}: {total} keys tagged {labels}")
    print(f"compared over {list(subtrees)}; shipped-dict evidence from {list(SHIPPED_DIRS)}\n")
    print(f"{'module':<28} {'still read':>11} {'removed':>8} {'absent':>8} {'shipped':>9}")
    print("-" * 68)
    for mod_name, counts in per_module.items():
        print(f"{mod_name.rsplit('.', 1)[-1]:<28} {counts['STILL READ']:>11} "
              f"{counts['REMOVED']:>8} {counts['ABSENT']:>8} "
              f"{shipped_counts[mod_name]:>9}")
    print("-" * 68)
    totals = {k: sum(c[k] for c in per_module.values()) for k in verdicts}
    print(f"{'TOTAL':<28} {totals['STILL READ']:>11} {totals['REMOVED']:>8} "
          f"{totals['ABSENT']:>8} {sum(shipped_counts.values()):>9}")

    # Deliberately no combined "confirmed" roll-up. While the checkouts were
    # sparse, a shipped hit rescued a key the source scan could not reach and
    # was added to the confirmed count. With complete subtrees the two are
    # different findings, and adding them would hide the interesting one below.
    absent_keys = {key for _, key in buckets["ABSENT"]}
    shipped_but_unread = sorted(absent_keys & shipped)

    if shipped_but_unread:
        print(f"\nSHIPPED BUT NO READER FOUND — {args.new} writes these into its own")
        print("dictionaries while no literal in the scanned source reads them. Either")
        print("the name is assembled at runtime, or the key is ineffective (minFlatness):")
        for key in shipped_but_unread:
            print(f"  {key}")

    if buckets["REMOVED"]:
        print("\nREMOVED — present in the old tree, absent from the new one.")
        print("Each of these needs reading by hand before it is believed:")
        for mod, key in buckets["REMOVED"]:
            print(f"  {mod:<26} {key}")

    if buckets["ABSENT"]:
        print("\nABSENT — no literal in either tree's scanned subtrees.")
        for mod, key in buckets["ABSENT"]:
            flag = "  (shipped)" if key in shipped else ""
            print(f"  {mod:<26} {key}{flag}")

    print("\nABSENT means the name appears as no double-quoted literal under the")
    print("scanned subtrees. With complete subtrees that is evidence of absence, but")
    print("it is not proof: a key assembled at runtime is invisible here. The standing")
    print("examples are <Model>Coeffs (typeName + \"Coeffs\") and executeInterval")
    print("(prefix_ + \"Interval\", timeControl.C). Read every ABSENT by hand, and")
    print("check the other fork, before acting on it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
