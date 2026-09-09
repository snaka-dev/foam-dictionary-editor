# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Shinji NAKAGAWA
"""Tests for the foamlore-generated turbulence-model schema modules.

schemas/turbulence_properties.py and schemas/momentum_transport.py are
vendored from the foamlore repository (facts/tools/generate_fode_schemas.py)
and must never be edited by hand — regenerate them there instead.
"""
import re
from pathlib import Path

import pytest

from foam.parser import OpenFoamParser
from schemas import (
    _delta_models,
    _laminar_models,
    _turbulence_coeffs,
    momentum_transport,
    turbulence_properties,
)
from schemas._base import (
    FOUNDATION_SERIES,
    FOUNDATION_V7,
    FOUNDATION_V7_V8,
    FOUNDATION_V8_V14,
    FOUNDATION_V9_V14,
    FOUNDATION_V10_V14,
    OPENCFD_SERIES,
    OPENCFD_V2212_V2606,
    ChoiceItem,
    KeySchema,
)
from schemas.builtin import get_default_schema_config
from schemas.registry import SchemaRegistry

ROOT = Path(__file__).resolve().parents[2]

# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def schema_config_path(monkeypatch, tmp_path):
    path = tmp_path / "schema_config.json"
    monkeypatch.setattr("schemas.config_store.CONFIG_FILE", path)
    return path


@pytest.fixture
def registry(schema_config_path):
    return SchemaRegistry()


# ── module shape ──────────────────────────────────────────────────────────────

class TestModuleShape:
    @pytest.mark.parametrize(
        "module,target",
        [
            (turbulence_properties, "turbulenceProperties"),
            (momentum_transport, "momentumTransport"),
        ],
    )
    def test_target_file_and_types(self, module, target):
        assert module.TARGET_FILE == target
        assert isinstance(module.SCHEMAS, dict)
        assert module.SCHEMAS
        for key, schema in module.SCHEMAS.items():
            assert isinstance(schema, KeySchema), key
            for choice in schema.choices:
                assert isinstance(choice, ChoiceItem), key

    def test_registered_by_default(self):
        modules = get_default_schema_config()["schema_modules"]
        assert "schemas.turbulence_properties" in modules
        assert "schemas.momentum_transport" in modules

    def test_shared_body_is_not_registered(self):
        # _turbulence_coeffs holds the coefficient facts both per-file modules
        # build their tables from. It is imported, never registered: it has no
        # TARGET_FILE, so the registry would skip it anyway.
        modules = get_default_schema_config()["schema_modules"]
        assert "schemas._turbulence_coeffs" not in modules
        assert not hasattr(_turbulence_coeffs, "TARGET_FILE")
        assert _turbulence_coeffs.TARGET_FILES == (
            "turbulenceProperties", "momentumTransport")

    @pytest.mark.parametrize(
        ("name", "module"),
        [("_laminar_models", _laminar_models), ("_delta_models", _delta_models)],
    )
    def test_a_prose_module_is_not_registered(self, name, module):
        """The prose-only modules declare no target and contribute no key.

        Both are the same shape and exist for the same mechanical reason: the
        hand-written module owns coefficient containers the generator must not
        outrank -- `laminar.MaxwellCoeffs` and the six `LES.*Coeffs` -- and
        `schemas/builtin.py` loads generated modules *second*, so an emitted
        entry would silently replace rather than collide. A module carrying no
        table cannot win a key it should not own, which is why foamlore routes
        these two families by measurement directory and emits prose alone.

        foamlore asserts the same from its side over both modules. This is the
        matching assertion from ours, which is the point: neither repository's
        check depends on the other's.
        """
        modules = get_default_schema_config()["schema_modules"]
        assert f"schemas.{name}" not in modules
        assert not hasattr(module, "TARGET_FILE")
        assert not hasattr(module, "TARGET_FILES")
        assert not hasattr(module, "SCHEMAS")
        assert module.MODEL_DOCS

    def test_per_file_tables_differ(self):
        # The reason there are two modules rather than one declaring
        # TARGET_FILES: the registry merges a multi-file module's table into
        # every file it names identically, so an OpenCFD-only model would
        # become visible in constant/momentumTransport, which only Foundation
        # v8+ reads and which no OpenCFD release reads at all.
        tp = _turbulence_coeffs.build_schemas("turbulenceProperties")
        mt = _turbulence_coeffs.build_schemas("momentumTransport")
        assert "GEKOCoeffs" in tp and "GEKOCoeffs" not in mt
        assert "v2fCoeffs" in mt

    @pytest.mark.parametrize(
        "name",
        ["turbulence_properties", "momentum_transport", "_turbulence_coeffs",
         "turbulence_properties_viscosity", "momentum_transport_viscosity",
         "_generalised_newtonian", "_laminar_models"],
    )
    def test_generated_banner_present(self, name):
        # Guard against hand edits: the vendored files must keep the
        # foamlore GENERATED header.
        text = (Path("schemas") / f"{name}.py").read_text(encoding="utf-8")
        assert "GENERATED by foamlore" in text
        assert "NEVER edit by hand" in text


# ── registry lookup ───────────────────────────────────────────────────────────

class TestRegistryLookup:
    def test_qualified_coefficient(self, registry):
        schema = registry.schema_for_file_key(
            "constant/turbulenceProperties", "beta1", parent_key="kOmegaSSTCoeffs"
        )
        assert schema is not None
        assert schema.key == "beta1"
        # beta1 has been in every OpenCFD release foamlore scans, so it gets
        # the fork label rather than the two releases that were once checked.
        # Foundation stays at v7 alone: v8 renamed the file this schema is for.
        assert schema.supported_in == (FOUNDATION_V7, OPENCFD_SERIES)
        assert any(c.value == "0.075" for c in schema.choices)

    def test_plain_fallback_in_ras_dict(self, registry):
        # coefficient placed directly in the RAS dict (optionalSubDict idiom).
        # Cmu is read by several models, so the flat entry is a merged one:
        # it names every owner and offers each distinct default, rather than
        # disappearing because the name is ambiguous.
        schema = registry.schema_for_file_key(
            "constant/turbulenceProperties", "Cmu", parent_key="RAS"
        )
        assert schema is not None
        assert any(c.value == "0.09" for c in schema.choices)
        assert "kEpsilon" in schema.description
        assert "RNGkEpsilon" in schema.description
        # inside a model's own dictionary that model's entry still wins
        own = registry.schema_for_file_key(
            "constant/turbulenceProperties", "Cmu", parent_key="RNGkEpsilonCoeffs"
        )
        assert own is not None and own.description != schema.description

    def test_momentum_transport_lookup(self, registry):
        schema = registry.schema_for_file_key(
            "constant/momentumTransport", "sigmaNut", parent_key="SpalartAllmarasCoeffs"
        )
        assert schema is not None
        # Every release that reads constant/momentumTransport, i.e. v8 onward.
        assert schema.supported_in == (FOUNDATION_V8_V14,)

    def test_fork_specific_coefficient(self, registry):
        # Absent from Foundation's constructors entirely, so only the OpenCFD
        # label appears — and it spans that fork rather than naming releases.
        schema = registry.schema_for_file_key(
            "constant/turbulenceProperties", "decayControl", parent_key="kOmegaSSTCoeffs"
        )
        assert schema is not None
        assert schema.supported_in == (OPENCFD_SERIES,)
        assert "Only present in" in schema.note

    def test_version_specific_coefficient(self, registry):
        # ft2 was added to SpalartAllmaras in v2212, so the tag has a real
        # lower bound. This is the case the range labels exist for: the user
        # needs to know it is unavailable below v2212.
        schema = registry.schema_for_file_key(
            "constant/turbulenceProperties", "ft2", parent_key="SpalartAllmarasCoeffs"
        )
        assert schema is not None
        assert schema.supported_in == (OPENCFD_V2212_V2606,)
        assert "Only present in" in schema.note

    def test_coeffs_dict_entry(self, registry):
        schema = registry.schema_for_file_key(
            "constant/turbulenceProperties", "kEpsilonCoeffs", parent_key="RAS"
        )
        assert schema is not None
        assert "kEpsilon" in schema.description

    def test_no_leak_into_other_files(self, registry):
        assert (
            registry.schema_for_file_key("system/controlDict", "beta1", parent_key="RAS")
            is None
        )


# ── model selector prose ──────────────────────────────────────────────────────

class TestModelSelectorProse:
    """The seam between the two modules: hand-written keys, extracted prose.

    `turbulence_structure` owns the selector and its choice *list*; the text
    describing each model comes from `_turbulence_coeffs.MODEL_DOCS`. The
    lookups here go through the registry with the real file path and parent
    key, because that is what `DetailPanel` does — a normal case writes only
    `RASModel kEpsilon;`, with no `kEpsilonCoeffs` dictionary to hang the
    description on.
    """

    @pytest.mark.parametrize(
        "path", ["constant/turbulenceProperties", "constant/momentumTransport"]
    )
    @pytest.mark.parametrize("key", ["RASModel", "model"])
    def test_ras_selector_quotes_upstream(self, registry, path, key):
        schema = registry.schema_for_file_key(path, key, parent_key="RAS")
        assert schema is not None
        choice = next(c for c in schema.choices if c.value == "kEpsilon")
        assert choice.description == _turbulence_coeffs.MODEL_DOCS["kEpsilon"][0]
        assert "rapid distortion" in choice.description
        assert choice.note.startswith("Reference:")
        assert "Launder" in choice.note

    @pytest.mark.parametrize("key", ["LESModel", "model"])
    def test_les_selector_quotes_upstream(self, registry, key):
        schema = registry.schema_for_file_key(
            "constant/turbulenceProperties", key, parent_key="LES"
        )
        assert schema is not None
        choice = next(c for c in schema.choices if c.value == "WALE")
        assert choice.description == _turbulence_coeffs.MODEL_DOCS["WALE"][0]
        assert choice.note.startswith("Reference:")

    def test_every_choice_is_described(self, registry):
        for parent in ("RAS", "LES", "laminar"):
            schema = registry.schema_for_file_key(
                "constant/turbulenceProperties", "model", parent_key=parent
            )
            assert schema is not None
            for choice in schema.choices:
                assert choice.description, f"{parent}.{choice.value}"

    def test_fallback_covers_what_foamlore_does_not(self, registry):
        # `laminar` names no model class, so MODEL_DOCS has nothing for it and
        # the hand-written blurb stands. If foamlore ever covers every choice
        # this is the test that says the fallback has become dead code.
        assert "laminar" not in _turbulence_coeffs.MODEL_DOCS
        assert "laminar" not in _laminar_models.MODEL_DOCS
        schema = registry.schema_for_file_key(
            "constant/turbulenceProperties", "RASModel", parent_key="RAS"
        )
        assert schema is not None
        choice = next(c for c in schema.choices if c.value == "laminar")
        assert choice.description == "No turbulence model; laminar stress only."
        assert choice.note == ""

    def test_bundled_pitz_daily_case(self, registry):
        # The end-to-end version: parse the bundled case, walk it, ask what the
        # pane would ask. pitzDaily is the only bundled case with a turbulence
        # model and it writes the dictionary the way the upstream tutorial does
        # — `RASModel kEpsilon;` and no coefficient dictionary at all, which is
        # exactly the shape in which the extracted prose used to be invisible.
        text = (
            ROOT / "tutorials" / "pitzDaily" / "constant" / "turbulenceProperties"
        ).read_text(encoding="utf-8")
        ras = next(
            c for c in OpenFoamParser(text).parse().children if c.name == "RAS"
        )
        assert not any(c.node_type == "dictionary" for c in ras.children or [])
        selector = next(c for c in ras.children if c.name == "RASModel")
        assert selector.value == "kEpsilon"

        schema = registry.schema_for_file_key(
            "constant/turbulenceProperties", selector.name, parent_key=ras.name
        )
        assert schema is not None
        choice = next(c for c in schema.choices if c.value == selector.value)
        assert choice.description and choice.note


# ── selector choice lists ─────────────────────────────────────────────────────

#: The laminar stress models, measured across all nineteen foamlore checkouts by
#: grepping `makeLaminarModel(...)` — the run-time selection table, so a name
#: absent from it cannot be constructed whatever the source tree holds.
#:
#: Still hand-written here even though the *prose* is now extracted
#: (`_laminar_models.MODEL_DOCS`, spec item 12): a `supported_in` tag is a
#: structural fact about the selector, which stays FoDE's, and checking it
#: against a table written independently of `turbulence_structure.py` is the
#: point of this fixture. The RAS/LES tags are checked against foamlore's own
#: table instead — see `TestSelectorChoiceLists.test_des_models_are_in_both_forks`.
_LAMINAR_TAGS = {
    "Stokes": (FOUNDATION_SERIES, OPENCFD_SERIES),
    "Maxwell": (FOUNDATION_SERIES, OPENCFD_SERIES),
    "generalizedNewtonian": (FOUNDATION_V7_V8, OPENCFD_SERIES),
    "generalisedNewtonian": (FOUNDATION_V9_V14,),
    "lambdaThixotropic": (FOUNDATION_V9_V14,),
    "Giesekus": (FOUNDATION_SERIES,),
    "PTT": (FOUNDATION_V8_V14,),
}


class TestSelectorChoiceLists:
    """The three model selectors, and the fork tags they carry.

    These lists are the hand-written half of the turbulence schema — foamlore
    is required *not* to emit them (docs/foamlore-schema-spec.md item 5) — so
    nothing upstream checks them. What follows is that check.
    """

    @pytest.mark.parametrize(
        "path", ["constant/turbulenceProperties", "constant/momentumTransport"]
    )
    @pytest.mark.parametrize(
        ("parent", "former"),
        [("RAS", "RASModel"), ("LES", "LESModel"), ("laminar", "laminarModel")],
    )
    def test_old_and_new_spellings_offer_one_list(self, registry, path, parent, former):
        """Both spellings are one selector, so both must offer one list.

        Every family reads the old name through a compatibility lookup —
        OpenCFD `getCompat("model", {{"<X>Model", -2006}})`, Foundation
        `lookupBackwardsCompatible({"model", "<X>Model"})` — so which spelling
        the file uses cannot change which models exist. `laminar` was the
        family that drifted: `model` carried four choices and `laminarModel`
        carried none, leaving the commoner spelling with no help at all.
        """
        current = registry.schema_for_file_key(path, "model", parent_key=parent)
        historical = registry.schema_for_file_key(path, former, parent_key=parent)
        assert current is not None and historical is not None
        assert current.choices, f"{parent}.model offers nothing to choose from"
        assert historical.choices == current.choices

    #: Trees to check registered type names against, if any is on this
    #: machine. One per fork suffices: a name must be registered *somewhere*,
    #: and the fork tags are checked separately above.
    _TREES = (
        Path("/usr/lib/openfoam/openfoam2606"),
        Path.home() / "FoDE" / "openfoam-sources" / "OpenFOAM-12",
    )

    def test_every_delta_model_is_covered_by_foamlore(self, registry):
        """The delta blurbs are OpenFOAM's own words, like the other two selectors.

        Same shape as the laminar assertion above and taken for the same
        reason: the nine hand-written blurbs became `_delta_models.MODEL_DOCS`
        once foamlore measured the family. `supported_in` stays ours, and so
        does the choice list -- which is why the `maxDeltaxyzCubeRoot`
        correction was ours to make and not something the prose could have
        fixed.

        `vanDriest` is the documented exception and is checked as one below.
        """
        schema = registry.schema_for_file_key(
            "constant/turbulenceProperties", "delta", parent_key="LES")
        assert schema is not None
        docs = _delta_models.MODEL_DOCS
        assert {c.value for c in schema.choices} <= set(docs)
        for choice in schema.choices:
            if choice.value == "vanDriest":
                continue
            assert choice.description == docs[choice.value][0], choice.value

    def test_vandriest_description_is_foundations_not_opencfds(self, registry):
        """OpenCFD's header for vanDriestDelta describes the wrong model.

        Every OpenCFD release from v2106 to v2606 repeats cubeRootVolDelta's
        summary verbatim in vanDriestDelta.H -- "Simple cube-root of cell
        volume delta used in incompressible LES models" -- while every
        Foundation release from v7 carries the correct description. The
        extraction reports one description per model and reported OpenCFD's.

        This is the only place `_model()`'s `description` override is used, and
        the test exists so that a future regeneration silently reinstating the
        wrong text is a failure rather than a diff nobody reads. If OpenCFD
        ever fixes its header the override becomes redundant, and this test is
        what will say so.
        """
        schema = registry.schema_for_file_key(
            "constant/turbulenceProperties", "delta", parent_key="LES")
        assert schema is not None
        choice = next(c for c in schema.choices if c.value == "vanDriest")
        assert "van Driest damping" in choice.description
        assert "cube-root" not in choice.description
        # and the upstream text it replaces is still the wrong one
        assert "cube-root" in _delta_models.MODEL_DOCS["vanDriest"][0]

    def test_density_offers_only_values_openfoam_accepts(self, registry):
        """The wrong value here is a fatal error, not an ignored entry.

        `incompressibleInterPhaseTransportModel` reads `density` from
        `constant/turbulenceProperties` and accepts exactly `variable` and
        `uniform`; anything else hits `FatalErrorInFunction` with "Available
        types are : variable or uniform". This entry used to offer
        `incompressible` and `compressible` and to claim both forks, so every
        value it offered would have aborted the run, and it offered them to
        Foundation users whose fork has no reader for the key at all.

        Foundation ships no reader in v7 through v14 and no dictionary that
        sets it. Five OpenCFD tutorials set it, all to `variable`.
        """
        schema = registry.schema_for_file_key(
            "constant/turbulenceProperties", "density")
        assert schema is not None
        assert {c.value for c in schema.choices} == {"variable", "uniform"}
        assert schema.supported_in == (OPENCFD_SERIES,)
        for choice in schema.choices:
            assert OPENCFD_SERIES in choice.supported_in

    def test_no_key_claims_a_name_upstream_never_had(self, registry):
        """`LES.turbulenceModelCoeffs` was in no release of either fork.

        Not a rename, not a drop within the supported range, and not a generic
        placeholder -- it sat among real keys with an ordinary description.
        Searched across Foundation v7-v14 and OpenCFD v2106-v2606, whole
        checkouts rather than the turbulence subtree, in both this repository
        and foamlore's nineteen: zero files. Removed rather than tagged,
        because a closed span plus `deprecated_since` would assert it once
        worked in a release FoDE supports, which is unmeasured and probably
        untrue.

        The guard is narrow on purpose: it names the one key rather than
        asserting a rule, because "every key exists upstream" is what the
        version-tag oracle is for and cannot be checked from here.
        """
        assert registry.schema_for_file_key(
            "constant/turbulenceProperties", "turbulenceModelCoeffs",
            parent_key="LES") is None

    def test_a_key_is_not_offered_in_a_file_no_release_reads_it(self, registry):
        """The two spellings are read by disjoint sets of releases.

        `constant/turbulenceProperties` is read by Foundation v7 and every
        OpenCFD release; `constant/momentumTransport` by Foundation v8-v14 and
        no OpenCFD release at all. The registry merges one module's table into
        both names identically, so before `only_in_files` every key appeared
        under both -- and 26 of them could not be written in one of the two by
        any release that supports them. `lambdaThixotropic` needs Foundation
        v9+, which reads `momentumTransport`; `density` is OpenCFD-only, and
        OpenCFD never opens `momentumTransport`.

        This is `docs/foamlore-schema-spec.md` item 2's hazard from the
        hand-written side, and it was found by phase 3's first diff against
        measured spans rather than by anything here.
        """
        cases = [
            ("laminar", "lambdaThixotropic", "momentumTransport"),
            ("laminar", "PTT", "momentumTransport"),
            ("laminar", "generalisedNewtonian", "momentumTransport"),
            (None, "modes", "momentumTransport"),
            (None, "density", "turbulenceProperties"),
            ("laminar", "generalizedNewtonianCoeffs", "turbulenceProperties"),
        ]
        for parent, key, belongs_in in cases:
            for target in ("turbulenceProperties", "momentumTransport"):
                got = registry.schema_for_file_key(
                    f"constant/{target}", key, parent_key=parent)
                if target == belongs_in:
                    assert got is not None, f"{key} missing from {target}"
                else:
                    assert got is None, (
                        f"{key} is offered in {target}, which no release that "
                        "supports it reads")

    def test_every_restriction_follows_from_its_own_tag(self):
        """The derivation must agree with the labels it is derived from.

        `only_in_files` is computed from `supported_in` rather than annotated
        per key, so a Foundation-v9+ key added later is restricted without
        anyone remembering. This asserts the two never disagree, and -- the
        part that matters -- that no label is missing from `_LABEL_FILES`: an
        unknown label falls back to both files, which is the safe direction but
        silently stops restricting. A missing entry is invisible in behaviour
        and visible here.
        """
        from schemas import turbulence_structure as ts
        seen = set()
        for schema in ts.SCHEMAS.values():
            labels = tuple(schema.supported_in or ())
            seen.update(labels)
            expected = ts._files_for(labels)
            actual = schema.only_in_files or ts.TARGET_FILES
            assert actual == expected, (
                f"{schema.key}: restricted to {actual}, tags {labels} imply "
                f"{expected}")
        unknown = seen - set(ts._LABEL_FILES)
        assert not unknown, (
            f"label(s) with no _LABEL_FILES entry, so they silently reach both "
            f"files: {sorted(unknown)}")

    def test_delta_choices_are_registered_type_names(self, registry):
        """Every `delta` choice must be a run-time type, not a class or a directory.

        The one hazard this list has that the RAS/LES lists do not: they are
        cross-checked against foamlore's `MODEL_DOCS`, and this one is checked
        against nothing. It carried `maxDeltaxyzCubeRootLESDelta` -- the class
        and the directory -- where OpenFOAM registers `maxDeltaxyzCubeRoot`, so
        a user picking it wrote a value OpenFOAM rejects. foamlore found it on
        2026-09-06; nothing here would have.

        The suffix is not strippable by rule, which is why this compares against
        `TypeName(...)` rather than deriving anything. Four of the nine classes
        end in `Delta` and register without it (`cubeRootVolDelta` ->
        `cubeRootVol`, and `Prandtl`, `smooth`, `vanDriest` likewise), while
        `IDDESDelta` and `SLADelta` register under the full class name.
        """
        trees = [t for t in self._TREES if t.is_dir()]
        if not trees:
            pytest.skip("no OpenFOAM source tree on this machine")

        registered = set()
        for tree in trees:
            for header in (tree / "src").rglob("*.H"):
                if "lnInclude" in header.parts or "LESdeltas" not in header.parts:
                    continue
                found = re.search(r'TypeName\("([^"]+)"\)',
                                  header.read_text(errors="ignore"))
                if found:
                    registered.add(found.group(1))
        assert registered, "found no LESdelta TypeName in any tree"

        schema = registry.schema_for_file_key(
            "constant/turbulenceProperties", "delta", parent_key="LES")
        assert schema is not None
        bad = [c.value for c in schema.choices if c.value not in registered]
        assert not bad, (
            "delta choice(s) are not a registered run-time type -- a user "
            "selecting one writes a value OpenFOAM rejects:\n"
            + "\n".join(f"  {v}" for v in bad))


    @pytest.mark.parametrize(
        "model",
        [
            "SpalartAllmarasDES",
            "SpalartAllmarasDDES",
            "SpalartAllmarasIDDES",
            "kOmegaSSTDES",
        ],
    )
    def test_des_models_are_in_both_forks(self, registry, model):
        """OpenCFD registers the DES family too, from a sibling `DES/` directory.

        These four were tagged Foundation-only because the original survey
        listed `.../LES/` and OpenCFD keeps DES models next door in `.../DES/`.
        OpenCFD's own tutorials select them, so the tag told a user the model
        they were successfully running did not exist in their fork.
        """
        schema = registry.schema_for_file_key(
            "constant/turbulenceProperties", "model", parent_key="LES"
        )
        assert schema is not None
        choice = next(c for c in schema.choices if c.value == model)
        assert set(choice.supported_in) == {FOUNDATION_SERIES, OPENCFD_SERIES}

    @pytest.mark.parametrize("model", ["kOmegaSSTDDES", "kOmegaSSTIDDES"])
    def test_opencfd_only_des_models_quote_upstream(self, registry, model):
        """The two the selector omitted entirely, though foamlore had the prose.

        Their coefficients were already vendored, so FoDE could explain
        `kOmegaSSTDDESCoeffs` while refusing to offer `kOmegaSSTDDES`. Asserting
        the description comes from `MODEL_DOCS` is what keeps them quoting
        upstream rather than acquiring a hand-written blurb.
        """
        schema = registry.schema_for_file_key(
            "constant/turbulenceProperties", "model", parent_key="LES"
        )
        assert schema is not None
        choice = next(c for c in schema.choices if c.value == model)
        assert choice.supported_in == (OPENCFD_SERIES,)
        assert choice.description == _turbulence_coeffs.MODEL_DOCS[model][0]
        assert choice.note.startswith("Reference:")

    def test_laminar_models_match_the_measured_table(self, registry):
        schema = registry.schema_for_file_key(
            "constant/turbulenceProperties", "model", parent_key="laminar"
        )
        assert schema is not None
        assert {c.value for c in schema.choices} == set(_LAMINAR_TAGS)
        for choice in schema.choices:
            assert choice.supported_in == _LAMINAR_TAGS[choice.value], choice.value

    def test_the_two_generalised_newtonian_spellings_stay_apart(self, registry):
        """The divergence is a fact, not a comment — this fails if it is tidied.

        OpenCFD has only ever registered `generalizedNewtonian`; Foundation
        renamed the class to `generalisedNewtonian` at v9. Neither fork declares
        a compatible spelling for the other's, so each is a construction error
        on the opposite side and collapsing them back to one `BOTH` choice would
        hand half of FoDE's users a name their build cannot resolve.
        """
        schema = registry.schema_for_file_key(
            "constant/turbulenceProperties", "model", parent_key="laminar"
        )
        assert schema is not None
        by_value = {c.value: c for c in schema.choices}
        american, british = by_value["generalizedNewtonian"], by_value["generalisedNewtonian"]
        assert OPENCFD_SERIES in american.supported_in
        assert OPENCFD_SERIES not in british.supported_in
        assert not set(american.supported_in) & set(british.supported_in)
        # A closed span belongs beside a `deprecated_since`, which is what keeps
        # it out of `OPEN_ENDED_SERIES`; see schemas/_base.py.
        assert american.deprecated_since
        # Not `renamed`: the `z` spelling is current on OpenCFD, and telling
        # that user to write the `s` one would be wrong.
        assert american.status == "valid"

    def test_every_laminar_model_is_covered_by_foamlore(self, registry):
        """The former tripwire, inverted — docs/foamlore-schema-spec.md item 12.

        This used to assert the opposite: no laminar name appeared in
        `MODEL_DOCS`, so a hand-written blurb was the only text available and
        the assertion was what would notice when foamlore extended the store to
        `.../laminar/`. It did (78 stores, seven models), and the prose is now
        vendored in `_laminar_models.MODEL_DOCS` — emitted with no `KeySchema`,
        so it cannot collide with the coefficient keys this module owns.

        The two tables stay disjoint: the RAS/LES one must not acquire a
        laminar name, or the merged lookup in `turbulence_structure` would
        silently pick whichever module was written second.
        """
        laminar_docs = set(_laminar_models.MODEL_DOCS)
        assert set(_LAMINAR_TAGS) <= laminar_docs
        # Three tables now, so the disjointness has to be three-way: the merged
        # lookup in `_model()` must not depend on which module was written last.
        ras_les, delta = (set(_turbulence_coeffs.MODEL_DOCS),
                          set(_delta_models.MODEL_DOCS))
        assert not laminar_docs & ras_les
        assert not laminar_docs & delta
        assert not delta & ras_les

        schema = registry.schema_for_file_key(
            "constant/turbulenceProperties", "model", parent_key="laminar"
        )
        assert schema is not None
        for choice in schema.choices:
            assert choice.description == _laminar_models.MODEL_DOCS[
                choice.value][0], choice.value

    @pytest.mark.parametrize(
        ("model", "cited"),
        [
            ("Maxwell", True),
            ("Giesekus", True),
            ("PTT", True),
            ("lambdaThixotropic", True),
            ("Stokes", False),
            ("generalizedNewtonian", False),
            ("generalisedNewtonian", False),
        ],
    )
    def test_laminar_notes_cite_only_where_upstream_does(self, registry,
                                                         model, cited):
        """Four of the seven headers carry a `Reference:` block; three do not.

        The same shape as `test_opencfd_only_des_models_quote_upstream`, and
        the same purpose: a note that begins "Reference:" is foamlore quoting
        upstream's own citation, so requiring one for exactly the four classes
        that have one is what stops a plausible-looking paper being invented
        for `Stokes` or either generali[sz]edNewtonian spelling.

        The two spellings are the case where a note exists without a citation:
        theirs is FoDE's own fork-divergence caveat, appended to upstream's
        (empty) note rather than replacing it.
        """
        schema = registry.schema_for_file_key(
            "constant/turbulenceProperties", "model", parent_key="laminar"
        )
        assert schema is not None
        choice = next(c for c in schema.choices if c.value == model)
        assert choice.note.startswith("Reference:") is cited, choice.note
        if not cited:
            assert not choice.note.startswith("Reference")

    def test_simulation_type_offers_two_phase_transport(self, registry):
        schema = registry.schema_for_file_key(
            "constant/turbulenceProperties", "simulationType"
        )
        assert schema is not None
        assert [c.value for c in schema.choices] == [
            "RAS", "LES", "laminar", "twoPhaseTransport",
        ]


# ── laminar coefficient dictionaries ───────────────────────────────────────────

class TestLaminarCoeffs:
    """The coefficient dictionaries for Maxwell/Giesekus/PTT/lambdaThixotropic
    and the generalizedNewtonian/generalisedNewtonian nested viscosity model.

    None of this comes from foamlore — `MODEL_DOCS` and `_turbulence_coeffs`
    cover RAS/LES only — so it is hand-written and hand-tested here, the same
    boundary `test_no_laminar_model_is_covered_by_foamlore` already draws for
    the model names themselves.
    """

    @pytest.mark.parametrize(
        ("parent", "key"),
        [
            ("laminar", "MaxwellCoeffs"), ("laminar", "Maxwell"),
            ("MaxwellCoeffs", "nuM"), ("Maxwell", "nuM"), ("laminar", "nuM"),
            ("MaxwellCoeffs", "lambda"), ("laminar", "lambda"),
            ("laminar", "GiesekusCoeffs"), ("laminar", "Giesekus"),
            ("GiesekusCoeffs", "alphaG"),
            ("laminar", "PTTCoeffs"), ("laminar", "PTT"),
            ("PTTCoeffs", "epsilon"),
            ("laminar", "lambdaThixotropicCoeffs"),
            ("laminar", "lambdaThixotropic"),
            ("lambdaThixotropicCoeffs", "a"), ("lambdaThixotropicCoeffs", "b"),
            ("lambdaThixotropicCoeffs", "c"), ("lambdaThixotropicCoeffs", "d"),
            ("lambdaThixotropicCoeffs", "nu0"),
            ("lambdaThixotropicCoeffs", "nuInf"),
            ("lambdaThixotropicCoeffs", "sigmay"),
            ("lambdaThixotropicCoeffs", "residualAlpha"),
            ("laminar", "generalizedNewtonianCoeffs"),
            ("laminar", "generalisedNewtonianCoeffs"),
            ("laminar", "generalisedNewtonian"),
            ("laminar", "viscosityModel"),
            ("generalizedNewtonianCoeffs", "viscosityModel"),
        ],
    )
    def test_resolves(self, registry, parent, key):
        """Resolves in whichever of the two spellings its releases read.

        Checked across both files rather than against `turbulenceProperties`
        alone, which is what this asserted until 2026-09-07. The two names are
        read by disjoint sets of releases, so a Foundation-v9+ entry such as
        `lambdaThixotropic` resolves only in `momentumTransport` -- and this
        test passed before only because every key was offered in both files
        regardless of which releases could read it. It was encoding the bug.

        Existence and prose are this test's business; *which* file each key
        belongs in is `test_a_key_is_not_offered_in_a_file_no_release_reads_it`,
        so the two are not both asserting placement from the same derivation.
        """
        found = [
            registry.schema_for_file_key(f"constant/{target}", key,
                                         parent_key=parent)
            for target in ("turbulenceProperties", "momentumTransport")
        ]
        resolved = [f for f in found if f is not None]
        assert resolved, f"{parent}.{key} resolves in neither spelling"
        for schema in resolved:
            assert schema.description

    def test_three_container_spellings_all_resolve(self, registry):
        """OpenCFD's laminarModel base tries "<Type>Coeffs" then flat;
        Foundation's tries the bare type name, then "<Type>Coeffs", then flat
        — three spellings in real use, confirmed against tutorials in both
        forks. All three must resolve for a coefficient shared with Giesekus
        and PTT (which subclass Maxwell and read the same nuM/lambda pair).
        """
        for parent in ("MaxwellCoeffs", "Maxwell", "laminar"):
            schema = registry.schema_for_file_key(
                "constant/turbulenceProperties", "nuM", parent_key=parent
            )
            assert schema is not None, parent
            assert schema.required

    def test_flat_coefficients_are_shared_across_the_three_open_namespaces(
        self, registry
    ):
        """Not a bug: RAS/LES/laminar are all `OPEN_NAMESPACES`, and the LES
        delta coefficients (Cmu, kappa, Aplus, ...) already resolve under RAS
        for the same reason -- flat fallback does not know which family a
        coefficient conceptually belongs to, only that the dictionary allows
        arbitrary keys. `nuM`/`lambda` behave identically; asserting the
        opposite here would just pin an inconsistency with the pre-existing
        delta-coefficient entries.
        """
        assert registry.schema_for_file_key(
            "constant/turbulenceProperties", "nuM", parent_key="RAS"
        ) is not None
        assert registry.schema_for_file_key(
            "constant/turbulenceProperties", "Cmu", parent_key="RAS"
        ) is not None

    def test_generic_names_resolve_to_the_nested_viscosity_models(self, registry):
        """lambdaThixotropic and CrossPowerLaw/BirdCarreau both use `nu0`/
        `nuInf` for a different physical quantity, one step apart inside
        generalizedNewtonian's own nested `viscosityModel`. A real Foundation
        tutorial (offsetCylinder) selects CrossPowerLaw and writes `nuInf`,
        `m`, `n` directly in `laminar{}` -- proof this is a real file shape,
        not a hypothetical.

        These used to be out of scope, and this test asserted they resolved to
        nothing. docs/foamlore-schema-spec.md item 13 is what changed that:
        foamlore now generates the nested classes' own coefficients into
        schemas/turbulence_properties_viscosity.py, measured separately from
        constant/transportProperties's identically-named classes.

        The regression actually guarded here never was "they do not resolve" —
        it is that **lambdaThixotropic's blurb must not answer for them**. So
        the assertion inverts rather than disappears: the three the nested
        models really read must now resolve *and* describe a viscosity model,
        while `nu0` — which lambdaThixotropic reads and no nested class does —
        must still resolve to nothing here.
        """
        for key in ("nuInf", "m", "n"):
            schema = registry.schema_for_file_key(
                "constant/turbulenceProperties", key,
                parent_key="generalisedNewtonianCoeffs",
            )
            assert schema is not None, (
                f"{key} should resolve to the nested viscosity model since "
                f"spec item 13 landed"
            )
            assert "viscosity model" in schema.description, (
                f"{key} resolves, but not to a viscosity model entry — "
                f"{schema.description!r}"
            )
            assert "lambdaThixotropic" not in schema.description, (
                f"{key} is being answered by lambdaThixotropic's blurb"
            )

        assert registry.schema_for_file_key(
            "constant/turbulenceProperties", "nu0",
            parent_key="generalisedNewtonianCoeffs",
        ) is None, (
            "nu0 is read by lambdaThixotropic and by none of the nested "
            "viscosity classes, so it must not resolve in a nested context"
        )

    def test_opencfd_tutorial_resolves_end_to_end(self, registry):
        """planarContraction writes Maxwell's coefficients flat, with no
        wrapper dict at all -- the shape OpenCFD's optionalSubDict falls back
        to when "MaxwellCoeffs" is absent.
        """
        path = (
            "/usr/lib/openfoam/openfoam2606/tutorials/incompressible/"
            "pimpleFoam/laminar/planarContraction/constant/turbulenceProperties"
        )
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError:
            pytest.skip("local OpenFOAM installation not present")
        laminar = next(
            c for c in OpenFoamParser(text).parse().children if c.name == "laminar"
        )
        for child in laminar.children:
            schema = registry.schema_for_file_key(
                "constant/turbulenceProperties", child.name, parent_key="laminar"
            )
            assert schema is not None, child.name

    def test_viscosity_model_choices_match_both_forks(self, registry):
        schema = registry.schema_for_file_key(
            "constant/turbulenceProperties", "viscosityModel",
            parent_key="laminar",
        )
        assert schema is not None
        by_value = {c.value: c for c in schema.choices}
        for shared in (
            "BirdCarreau", "Casson", "CrossPowerLaw", "HerschelBulkley",
            "powerLaw", "strainRateFunction",
        ):
            assert set(by_value[shared].supported_in) == {
                FOUNDATION_SERIES, OPENCFD_SERIES,
            }, shared
        # Newtonian first registers at foundation-10 (confirmed absent
        # in 7/8/9); FOUNDATION_SERIES over-claimed it by three releases.
        assert by_value["Newtonian"].supported_in == (FOUNDATION_V10_V14,)
