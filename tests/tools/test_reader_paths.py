# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Shinji NAKAGAWA
"""Guards on `tools/fode-reader-paths.json`, FoDE's half of the version-tag oracle.

The file tells foamlore where each dictionary's keys are read, so it can measure
`supported_in` instead of FoDE hand-asserting it — see DEVELOPER.md and
docs/foamlore-schema-spec.md item 11.

Two failure modes are worth a test. The `keys` list is derived from the live
registry, so it goes stale the moment a schema entry's tag changes; and a
`readers` entry that names a path no OpenFOAM release has is a silent
"UNSEEN everywhere" for that whole dictionary, which reads as both forks
dropping it. The first is checked here unconditionally. The second needs a
source tree and is checked only when one is present.
"""
from __future__ import annotations

import importlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MAP = ROOT / "tools" / "fode-reader-paths.json"

#: Trees to validate reader paths against, if any is on this machine. One per
#: fork is enough: a path is checked for existing *somewhere*, not everywhere.
CANDIDATE_TREES = (
    Path.home() / "FoDE" / "openfoam-sources" / "OpenFOAM-12",
    Path("/usr/lib/openfoam/openfoam2606"),
)


@pytest.fixture(scope="module")
def payload():
    assert MAP.is_file(), f"{MAP.name} is missing; run tools/gen_reader_paths.py"
    return json.loads(MAP.read_text(encoding="utf-8"))


def test_map_is_current(payload):
    """Regenerating must reproduce the committed file byte for byte.

    `keys` carries each entry's currently claimed tag so foamlore's first pass
    is a diff rather than a replacement. A stale file would diff against tags
    FoDE no longer holds, and the mismatch would look like a measurement
    disagreeing with the schema when it is only disagreeing with history.
    """
    result = subprocess.run(
        [sys.executable, "tools/gen_reader_paths.py", "--check"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_shape_matches_the_agreed_schema(payload):
    """The fields foamlore's HANDOFF.md specifies, and their invariants."""
    assert payload["schema"] == "fode-reader-paths/v2"
    assert payload["dictionaries"], "no dictionaries in the map"

    for d in payload["dictionaries"]:
        where = d["file"]
        # A case-relative path, not a bare name: constant/physicalProperties
        # and a system/ file of a similar name are different dictionaries.
        assert "/" in where, f"{where} is not case-relative"
        assert where.split("/")[0] in ("system", "constant"), where

        readers = d["readers"]
        assert readers, f"{where} has an empty readers map — foamlore treats a "
        # A fork key replaces "*" rather than merging, so a map with neither a
        # "*" default nor an entry for a fork says nothing about that fork.
        assert "*" in readers or {"foundation", "opencfd"} <= set(readers), (
            f"{where} has neither a '*' default nor both forks named")
        for fork, paths in readers.items():
            assert paths, f"{where}/{fork} has no reader paths"
            for entry in paths:
                # v2: a nested list is an alternative group -- one reader that
                # upstream renamed, so at least one member exists per release
                # rather than all of them. A group of one is meaningless and a
                # sign the author meant a plain path.
                group = entry if isinstance(entry, list) else [entry]
                if isinstance(entry, list):
                    assert len(group) > 1, f"{where}: {entry} is a group of one"
                for p in group:
                    assert isinstance(p, str), f"{where}: {p!r} is not a path"
                    assert not p.startswith("/"), f"{where}: {p} is not tree-relative"
                    assert p.split("/")[0] in ("src", "applications"), p

        assert d["keys"], f"{where} contributes no keys"
        for k in d["keys"]:
            assert k["claimed"] == "BOTH", k
            assert "." not in k["key"], (
                f"{k['key']} still carries a parent prefix; the source contains "
                "the bare name")


def test_lninclude_is_excluded(payload):
    """OpenCFD's build symlinks would double-count every literal.

    `src/OpenFOAM/lnInclude` alone is ~2000 symlinks to headers already counted
    under their real paths. Left in, it inflates every "present" verdict and
    makes two forks look more alike than they are.
    """
    assert "lnInclude" in payload["exclude_dirs"]


def test_runtime_assembled_keys_are_flagged_not_dropped(payload):
    """A key the scan cannot see must report no-verdict, not absence.

    `executeInterval` is built as `prefix_ + "Interval"` and was one reading
    away from being retagged out of Foundation during item 9. Treating "no
    literal found" as "the fork does not read it" is the mistake this whole
    exercise exists to stop making.
    """
    flagged = set(payload["runtime_assembled"])
    assert "executeInterval" in flagged
    assert "executeControl" in flagged
    # writeControl/writeInterval are assembled the same way by the function
    # objects but Time reads them as plain literals too, so a scan does see
    # them; listing them would suppress a verdict that is available.
    assert "writeControl" not in flagged
    assert "writeInterval" not in flagged

    # The `<Model>Coeffs` family, which OpenFOAM builds as typeName + "Coeffs".
    # Derived from the key table rather than listed, so a family foamlore adds
    # later cannot start reporting as absent because a hand list went stale.
    keys = {k["key"] for d in payload["dictionaries"] for k in d["keys"]}
    model_coeffs = {n for n in keys if n.endswith("Coeffs")}
    assert len(model_coeffs) > 40, "the derivation found suspiciously few"

    # ...but NOT by suffix, and printCoeffs is the proof. It ends in Coeffs,
    # is not a model dictionary, and OpenFOAM reads it as a plain literal --
    # so suppressing it would discard a verdict that is genuinely available.
    # This is the counter-example that makes the rule an enumeration rather
    # than a pattern, and a scanner applying `endswith("Coeffs")` would be
    # wrong on exactly this key.
    assert "printCoeffs" in model_coeffs
    assert "printCoeffs" not in flagged
    assert "printCoeffs" in set(payload["structural_keys"])
    assert model_coeffs - {"printCoeffs"} <= flagged

    # advectionDiffusionCoeffs is assembled the same way but is not a
    # <Model>Coeffs dictionary, so it is named rather than derived.
    assert "advectionDiffusionCoeffs" in flagged


def test_known_unseen_holds_only_symmetric_cases(payload):
    """A key unseen in one fork is the finding, not something to suppress.

    `known_unseen` exists so the oracle stops re-reporting keys already
    explained. Putting a one-fork case in it would hide exactly the asymmetry
    item 11 is looking for -- `pRefPoint` is unseen in OpenCFD and read by
    Foundation, and `advectionDiffusionCoeffs` is unseen in Foundation only.
    """
    known = set(payload["known_unseen"])
    flagged = set(payload["runtime_assembled"])
    assert "minFlatness" in known
    assert "advectionDiffusionCoeffs" not in known

    # minFlatness is the only entry, and the only genuine both-fork absence
    # this exercise produced -- every other symmetric absence was a missing
    # reader path. The pRef trio sat here or nowhere until 2026-09-08 and
    # belongs in runtime_assembled: findRefCell.C builds the key as
    # `field.name() + "RefCell"`, so it is unseeable rather than unread, and
    # the distinction is the one known_unseen exists to make.
    assert known == {"minFlatness"}
    for key in ("pRefCell", "pRefPoint", "pRefValue"):
        assert key not in known, f"{key} is unseeable, not unread"
        assert key in flagged


def test_structural_keys_are_flagged_not_dropped(payload):
    """FoDE's own structural keys stay in the map, marked rather than removed.

    foamlore asked for `printCoeffs` to be dropped as item 5's boundary. The
    same reasoning covers eleven keys, not one -- the whole skeleton of
    `constant/turbulenceProperties` -- so singling one out would be
    inconsistent either way it went.

    They are kept because item 5's mechanism does not reach here. What it
    forbids is foamlore *emitting a KeySchema* for a structural key, which
    would silently override the hand-written entry given `builtin.py`'s load
    order. The oracle emits a measured span that FoDE consumes into its own
    module, so no override is possible. Dropping them would instead leave 22
    hand-asserted `BOTH` claims unaudited forever, which is the thing item 11
    exists to end.
    """
    flagged = set(payload["structural_keys"])
    assert {"simulationType", "printCoeffs", "model", "delta"} <= flagged
    covered = [k["key"] for d in payload["dictionaries"] for k in d["keys"]
               if k["key"] in flagged]
    assert len(covered) == 22, (
        f"expected the eleven structural keys across both turbulence "
        f"dictionaries, got {len(covered)}")


def test_no_generated_module_declares_a_structural_key(payload):
    """Item 5's guarantee, enforced here rather than intended.

    `structural_keys` is not only a hint to whoever reads the map. It is the
    list this test drives, which makes the field load-bearing on both sides:
    foamlore tags those spans so nothing downstream can turn one into a
    `KeySchema`, and FoDE checks that none ever arrives as one.

    The hazard is specific and has happened in the neighbourhood before. The
    registry merges every module's table per file and later modules win, and
    `schemas/builtin.py` loads the generated modules *after*
    `turbulence_structure`. So a generated `simulationType` would not collide
    with the hand-written entry, it would silently replace it. foamlore's
    generator hit the same shape once already: the laminar derived files had to
    be routed by measurement directory, because the alternative emitted
    `laminar.MaxwellCoeffs` over keys `turbulence_structure.py` owns and
    resolved in the generator's favour with nothing but a debug log to show for
    it.

    Nothing today violates this. The point is that nothing today *checks* it,
    and a future path from oracle output into a schema generator would reopen
    it.
    """
    structural = set(payload["structural_keys"])
    assert structural, "structural_keys is empty; the guard would be vacuous"

    offenders = []
    for path in sorted((ROOT / "schemas").glob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "GENERATED by foamlore" not in text:
            continue
        module = importlib.import_module(f"schemas.{path.stem}")
        tables = []
        if hasattr(module, "SCHEMAS"):
            tables.append(module.SCHEMAS)
        if hasattr(module, "build_schemas"):
            for target in ("turbulenceProperties", "momentumTransport"):
                tables.append(module.build_schemas(target))
        for table in tables:
            for table_key in table:
                bare = table_key.rsplit(".", 1)[-1]
                if bare in structural:
                    offenders.append(f"{path.name}: {table_key}")

    assert not offenders, (
        "a generated module declares a key turbulence_structure.py hand-owns. "
        "builtin.py loads generated modules last, so this silently overrides "
        "the hand-written entry rather than colliding with it:\n"
        + "\n".join(f"  {o}" for o in sorted(set(offenders))))


def test_alternative_groups_are_alternatives_as_readers(payload):
    """In any release, at most one member of a group reads this dictionary.

    That is the claim a group makes, and it is about *readers*, not about
    directories. An earlier version of this test asserted at most one member
    existed on disk, which is a different and stricter thing: Foundation ships
    both src/transportModels and src/twoPhaseModels at v8 and v9, while the VoF
    controls live in exactly one of them. The directory test passed anyway,
    because the two trees checked here (v12 and v2606) happen to be releases
    where the pair does not coexist -- a guard passing for the wrong reason,
    which is worse than one that fails.

    So the property is measured: for each release, count members that
    contribute at least one of this dictionary's keys. Two contributing
    members would mean the reader is split across both, and grouping them
    would let a consumer treat one as sufficient.
    """
    trees = [t for t in CANDIDATE_TREES if t.is_dir()]
    if not trees:
        pytest.skip("no OpenFOAM source tree on this machine")

    literal = re.compile(r'"([^"\\\n]{1,80})"')
    block, line = re.compile(r"/\*.*?\*/", re.S), re.compile(r"//[^\n]*")

    def contributes(tree, path, keys):
        base = tree / path
        if not base.is_dir():
            return False
        for f in base.rglob("*"):
            if f.suffix not in (".C", ".H") or not f.is_file():
                continue
            try:
                text = f.read_text(errors="ignore")
            except OSError:
                continue
            if keys & set(literal.findall(line.sub("", block.sub("", text)))):
                return True
        return False

    groups = [(d["file"], fork, entry, {k["key"] for k in d["keys"]})
              for d in payload["dictionaries"]
              for fork, paths in d["readers"].items()
              for entry in paths if isinstance(entry, list)]
    assert groups, "no alternative groups; this guard would be vacuous"

    for where, fork, group, keys in groups:
        for tree in trees:
            live = [p for p in group if contributes(tree, p, keys)]
            assert len(live) <= 1, (
                f"{where} [{fork}]: in {tree.name}, {live} all read this "
                "dictionary, so they are not alternatives -- grouping them "
                "lets a consumer stop at the first and miss the rest")


def test_the_map_declares_what_its_verdicts_may_be_used_for(payload):
    """A two-release verdict set cannot produce a `supported_in` value.

    This is the constraint that invalidates output rather than misreading it,
    so it is declared in the artifact rather than left to whoever consumes it.
    Pinning one release per fork is right for cross-checking two independent
    implementations -- a disagreement then means a measurement error rather
    than a release difference -- and wrong for publishing a tag.

    `functions.mode` is the case that proved it. Measured on foundation-12
    against opencfd-v2606 it reads OpenCFD-only, which is a clean, plausible
    fork split. Foundation ships `fieldMinMax` reading
    `lookupOrDefault<word>("mode", "magnitude")` at v7 and v8 and drops the
    model at v9, so the true answer is a span. Taking the pinned pair's
    verdict would have replaced one wrong tag with another and given it a
    measurement's authority, which is the specific harm item 11 exists to
    prevent -- nothing downstream questions a measurement.

    Cross-check on two, publish from nineteen.
    """
    assert payload["verdicts_publishable_from"] == "all_releases"


def test_reader_paths_exist_in_a_real_tree(payload):
    """A path no release has is a silent 'both forks dropped this dictionary'.

    Only paths that could belong to the available tree's fork are checked, and
    a path is required to exist in *some* tree rather than all of them: the
    map deliberately names both spellings where a fork moved a subtree, so
    `src/MomentumTransportModels` and `src/TurbulenceModels` are each correct
    for a different release.
    """
    trees = [t for t in CANDIDATE_TREES if t.is_dir()]
    if not trees:
        pytest.skip("no OpenFOAM source tree on this machine")

    missing = []
    for d in payload["dictionaries"]:
        for fork, paths in d["readers"].items():
            for entry in paths:
                # For a group it is the group that must exist somewhere, not
                # every member: the members are alternatives across a rename,
                # so a release has one of them by construction.
                group = entry if isinstance(entry, list) else [entry]
                if not any((t / p).is_dir() for t in trees for p in group):
                    missing.append(f"{d['file']} [{fork}]: {entry}")
    assert not missing, (
        "reader path(s) found in none of "
        + ", ".join(t.name for t in trees)
        + " — a path that exists nowhere yields UNSEEN for every key in that "
        "dictionary, which reads as the fork dropping it:\n"
        + "\n".join(f"  {m}" for m in missing))
