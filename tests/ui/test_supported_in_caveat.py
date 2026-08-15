# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Shinji NAKAGAWA
"""The Detail pane qualifies a span that stops where the measuring stopped --
ui/panels/detail_panel.py, schemas/_base.py.

`OPEN_ENDED_SERIES` is **empty** now that the generator's spec item 9 is
closed: every span FoDE carries ends where the measurement found an end, so no
label earns the caveat. The mechanism stays, because the next unmeasured release
will need it, and these tests keep it working while nothing exercises it in
production -- `TestRendering` injects a synthetic label rather than borrowing a
real one, so emptying the set did not quietly stop testing anything.

Shown bare, a span that stops short reads to a user on a later release as "not
available in the release I am running" -- the misreading that once told OpenCFD
users 61 shared `finiteVolume`/`lduMatrix` keys were Foundation-only.

Nothing else guards this. `tests/schemas/test_schema_coverage.py` compares
`FOUNDATION_SERIES` by identity, so it passes whatever the label says and
whatever the pane renders.
"""
from __future__ import annotations

import importlib

import pytest

from schemas._base import (
    BOTH,
    FOUNDATION_SERIES,
    FOUNDATION_V7_V13,
    FOUNDATION_V8_V14,
    OPEN_ENDED_SERIES,
    OPENCFD_SERIES,
    KeySchema,
    has_unmeasured_successor,
)
from schemas.builtin import get_default_schema_config
from ui.panels.detail_panel import _qualified_supported_in

CAVEAT = "(newer releases not yet measured)"

#: A label no schema carries, injected into `OPEN_ENDED_SERIES` to exercise the
#: caveat. Using a real label here would couple these tests to whichever span
#: happens to be unmeasured today, which is exactly what broke when item 9
#: closed and the set emptied.
SYNTHETIC = "Fork v1-v2"
NARROW = (SYNTHETIC, OPENCFD_SERIES)


@pytest.fixture
def open_ended(monkeypatch):
    """Make `SYNTHETIC` the one open-ended label, for the rendering tests.

    `has_unmeasured_successor` reads the module global when called and
    `detail_panel` imports the function rather than the set, so patching
    `schemas._base.OPEN_ENDED_SERIES` reaches the pane. Do not "simplify" this
    into a real label -- see SYNTHETIC.
    """
    monkeypatch.setattr("schemas._base.OPEN_ENDED_SERIES", frozenset({SYNTHETIC}))


def _schema(**kwargs: object) -> KeySchema:
    base: dict[str, object] = {
        "key": "k", "label": "K", "description": "d", "supported_in": BOTH,
    }
    base.update(kwargs)
    return KeySchema(**base)  # type: ignore[arg-type]


def _live_schemas():
    """Every registered `KeySchema`, so the set can be checked against reality."""
    for mod_name in get_default_schema_config()["schema_modules"]:
        mod = importlib.import_module(mod_name)
        yield from getattr(mod, "SCHEMAS", {}).values()


class TestOpenEndedSet:
    def test_every_open_ended_label_is_actually_carried_unmeasured(self):
        # The invariant, replacing an assertion that pinned the exact set: a
        # label is open-ended only while some schema carries it *without* a
        # `deprecated_since`. Stated this way it survives the set emptying, and
        # it fails if a label is left behind after its last unmeasured key is
        # measured -- the drift that would make the caveat a lie.
        unmeasured = {
            label
            for schema in _live_schemas()
            if not schema.deprecated_since
            for label in schema.supported_in
        }
        stale = OPEN_ENDED_SERIES - unmeasured
        assert not stale, (
            f"{sorted(stale)} in OPEN_ENDED_SERIES but no live schema carries "
            "it without a deprecated_since -- it was measured, so remove it"
        )

    def test_a_closed_span_is_not_open_ended(self):
        # `processorAgglomerator` carries FOUNDATION_V7_V13 with
        # deprecated_since="Foundation v14": measured and gone, not unchecked.
        # Listing that label would tell users a proven removal might be a gap.
        assert FOUNDATION_V7_V13 not in OPEN_ENDED_SERIES

    def test_measured_labels_are_not_open_ended(self):
        # FOUNDATION_SERIES reaches v14 on evidence; FOUNDATION_V8_V14 was
        # earned by foamlore scanning every release. Neither may be qualified,
        # or the pane understates what is actually known.
        for label in (FOUNDATION_SERIES, FOUNDATION_V8_V14, OPENCFD_SERIES):
            assert label not in OPEN_ENDED_SERIES
            assert not has_unmeasured_successor((label,))

    def test_the_two_foundation_labels_are_distinct(self):
        # They differ by one release and mean different things -- "measured to
        # v14" versus "measured to v13, v14 unchecked". Collapsing them would
        # silently re-widen the 21 stragglers.
        assert FOUNDATION_SERIES != FOUNDATION_V7_V13

    def test_widened_label_must_leave_the_set(self):
        # Guards the failure that would otherwise be silent: a label naming v14
        # while still listed as open-ended makes the caveat a lie.
        for label in OPEN_ENDED_SERIES:
            assert "v14" not in label, (
                f"{label!r} names v14 yet is still in OPEN_ENDED_SERIES -- "
                "remove it, or the caveat contradicts the label"
            )


class TestRendering:
    def test_unmeasured_span_gets_the_caveat(self, open_ended):
        assert _qualified_supported_in(_schema(supported_in=NARROW)).endswith(CAVEAT)

    def test_measured_spans_do_not(self):
        assert CAVEAT not in _qualified_supported_in(_schema())
        assert _qualified_supported_in(_schema(supported_in=(FOUNDATION_V8_V14,))) == (
            FOUNDATION_V8_V14
        )

    def test_known_end_of_life_does_not(self, open_ended):
        # `processorAgglomerator`: v14 dropped it for the processorAgglomeration
        # sub-dictionary. The span ends for a reason we established, so "not yet
        # measured" would be actively wrong -- `deprecated_since` suppresses it.
        text = _qualified_supported_in(
            _schema(supported_in=NARROW, deprecated_since="Foundation v14")
        )
        assert CAVEAT not in text

    def test_empty_stays_empty(self):
        assert _qualified_supported_in(_schema(supported_in=())) == ""

    def test_none_is_tolerated(self):
        assert _qualified_supported_in(None) == ""

    def test_caveat_is_appended_not_substituted(self, open_ended):
        text = _qualified_supported_in(_schema(supported_in=NARROW))
        assert text.startswith(f"{SYNTHETIC}, {OPENCFD_SERIES}")


class TestRealSchemas:
    @pytest.mark.parametrize(
        ("file_path", "key", "parent"),
        [
            ("system/controlDict", "writeControl", None),
            ("system/fvSchemes", "default", "ddtSchemes"),
            ("system/fvSolution", "solver", "solvers"),
            ("system/blockMeshDict", "scale", None),
            # Measured by the item 9 scan and widened from the narrow span:
            # readers found in Foundation 14's src/ or applications/.
            ("system/controlDict", "fileHandler", None),
            ("system/fvSolution", "nAlphaCorr", "solvers"),
            ("system/snappyHexMeshDict", "minFaceFlatness", "meshQualityControls"),
            ("system/snappyHexMeshDict", "singleRegionName", None),
            # Foundation builds this one as `prefix_ + "Interval"`, so it is a
            # literal in no source file and the scan reported it ABSENT. It is
            # shipped in etc/caseDicts/functions/mesh/checkMesh all the same --
            # the reading that stopped it being retagged out of Foundation.
            ("system/controlDict", "executeInterval", "functions"),
        ],
    )
    def test_measured_core_keys_render_clean(self, file_path, key, parent):
        from schemas import schema_for_file_key

        schema = schema_for_file_key(file_path, key, parent)
        assert schema is not None, f"{file_path}: {key} has no schema"
        text = _qualified_supported_in(schema)
        assert text.startswith(FOUNDATION_SERIES)
        assert CAVEAT not in text

    @pytest.mark.parametrize(
        ("file_path", "key", "parent"),
        [
            ("system/blockMeshDict", "mergeType", None),
            ("system/fvSchemes", "oversetInterpolation", None),
            ("system/fvSchemes", "oversetInterpolationSuppressed", None),
            ("system/fvSolution", "finalOnLastPimpleIterOnly", "PIMPLE"),
            ("system/controlDict", "writeToFile", "functions"),
            ("system/controlDict", "useUserTime", "functions"),
            ("system/snappyHexMeshDict", "radius1", "geometry"),
        ],
    )
    def test_opencfd_only_keys_claim_no_foundation_support(self, file_path, key, parent):
        # The regression guard for the defect this scan found: these keys were
        # tagged as shared, so a Foundation user was told a key was available
        # that their fork does not read. Measured over complete src/ +
        # applications/ trees for v7, v12, v13 and v14 -- no Foundation reader
        # in any of them, and an OpenCFD reader in all.
        from schemas import schema_for_file_key

        schema = schema_for_file_key(file_path, key, parent)
        assert schema is not None, f"{file_path}: {key} has no schema"
        foundation = [t for t in schema.supported_in if t.startswith("Foundation")]
        assert not foundation, (
            f"{file_path}: {key} claims {foundation}; no Foundation release reads it"
        )

    @pytest.mark.parametrize(
        ("file_path", "key", "parent", "dropped_at"),
        [
            ("system/controlDict", "maxDi", None, "Foundation v13"),
            ("system/controlDict", "regionType", "functions", "Foundation v13"),
            ("system/controlDict", "timeEnd", "functions", "Foundation v12"),
            ("system/controlDict", "timeStart", "functions", "Foundation v12"),
            ("system/controlDict", "formatOptions", "functions", "Foundation v8"),
            ("system/snappyHexMeshDict", "minTriangleTwist", "meshQualityControls",
             "Foundation v10"),
        ],
    )
    def test_dropped_foundation_keys_say_when(self, file_path, key, parent, dropped_at):
        # Foundation read these and stopped; OpenCFD reads them as current. The
        # span has to close *and* carry `deprecated_since`, or the pane cannot
        # tell "gone" from "not yet checked" -- and the caveat must stay off.
        from schemas import schema_for_file_key

        schema = schema_for_file_key(file_path, key, parent)
        assert schema is not None, f"{file_path}: {key} has no schema"
        assert schema.deprecated_since == dropped_at
        assert any(t.startswith("OpenCFD") for t in schema.supported_in)
        assert CAVEAT not in _qualified_supported_in(schema)

    def test_removed_key_says_so_without_the_caveat(self):
        # processorAgglomerator is the one key the scan proved absent from v14.
        from schemas import schema_for_file_key

        schema = schema_for_file_key("system/fvSolution", "processorAgglomerator", "solvers")
        assert schema is not None
        assert schema.deprecated_since == "Foundation v14"
        text = _qualified_supported_in(schema)
        assert text.startswith(FOUNDATION_V7_V13)
        assert CAVEAT not in text

    def test_generated_turbulence_key_renders_its_measured_range(self):
        from schemas import schema_for_file_key

        schema = schema_for_file_key(
            "constant/momentumTransport", "sigmaNut", parent_key="SpalartAllmarasCoeffs"
        )
        assert schema is not None
        assert _qualified_supported_in(schema) == FOUNDATION_V8_V14
