# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
import json
import pytest
from schemas._base import (
    ChoiceItem,
    KeySchema,
    FOUNDATION_V13,
    OPENCFD_SERIES,
    _versions_text,
)
from schemas.builtin import get_default_schema_config
from schemas.config_store import (
    delete_schema_config,
    load_schema_config,
    reset_schema_config,
    save_schema_config,
)
from schemas.registry import SchemaRegistry


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def config_path(monkeypatch, tmp_path):
    path = tmp_path / "schema_config.json"
    monkeypatch.setattr("schemas.config_store.CONFIG_FILE", path)
    return path


@pytest.fixture
def registry(config_path):
    return SchemaRegistry()


# ── _base.py ──────────────────────────────────────────────────────────────────

class TestChoiceItem:
    def test_fields(self):
        item = ChoiceItem(value="ascii", description="ASCII format")
        assert item.value == "ascii"
        assert item.description == "ASCII format"

    def test_defaults(self):
        item = ChoiceItem(value="x", description="y")
        assert item.supported_in == ()
        assert item.note == ""

    def test_frozen(self):
        item = ChoiceItem(value="x", description="y")
        with pytest.raises(Exception):
            item.value = "z"  # type: ignore

    def test_with_supported_in(self):
        item = ChoiceItem(value="x", description="y", supported_in=(FOUNDATION_V13,))
        assert FOUNDATION_V13 in item.supported_in

    def test_with_note(self):
        item = ChoiceItem(value="x", description="y", note="a note")
        assert item.note == "a note"


class TestKeySchema:
    def test_fields(self):
        schema = KeySchema(key="startFrom", label="Start From", description="Controls start")
        assert schema.key == "startFrom"
        assert schema.label == "Start From"
        assert schema.description == "Controls start"

    def test_defaults(self):
        schema = KeySchema(key="k", label="l", description="d")
        assert schema.supported_in == ()
        assert schema.note == ""
        assert schema.choices == ()

    def test_frozen(self):
        schema = KeySchema(key="k", label="l", description="d")
        with pytest.raises(Exception):
            schema.key = "x"  # type: ignore

    def test_with_choices(self):
        item = ChoiceItem(value="v", description="d")
        schema = KeySchema(key="k", label="l", description="d", choices=(item,))
        assert len(schema.choices) == 1
        assert schema.choices[0].value == "v"


class TestVersionsText:
    def test_single_version(self):
        assert _versions_text((FOUNDATION_V13,)) == FOUNDATION_V13

    def test_multiple_versions_joined(self):
        result = _versions_text((FOUNDATION_V13, OPENCFD_SERIES))
        assert FOUNDATION_V13 in result
        assert OPENCFD_SERIES in result
        assert ", " in result

    def test_returns_string(self):
        assert isinstance(_versions_text((FOUNDATION_V13,)), str)


# ── builtin.py ────────────────────────────────────────────────────────────────

class TestDefaultConfig:
    def test_returns_dict(self):
        assert isinstance(get_default_schema_config(), dict)

    def test_has_schema_modules_key(self):
        assert "schema_modules" in get_default_schema_config()

    def test_schema_modules_is_list(self):
        assert isinstance(get_default_schema_config()["schema_modules"], list)

    def test_contains_builtin_modules(self):
        modules = get_default_schema_config()["schema_modules"]
        assert "schemas.control_dict" in modules
        assert "schemas.fv_schemes" in modules
        assert "schemas.fv_solution" in modules

    def test_no_file_key_mapping(self):
        assert "file_key_mapping" not in get_default_schema_config()


# ── config_store.py ───────────────────────────────────────────────────────────

class TestLoadSchemaConfig:
    def test_returns_defaults_when_no_file(self, config_path):
        assert load_schema_config() == get_default_schema_config()

    def test_loads_existing_file(self, config_path):
        data = {"schema_modules": ["custom.module"]}
        config_path.write_text(json.dumps(data), encoding="utf-8")
        assert load_schema_config()["schema_modules"] == ["custom.module"]

    def test_returns_dict(self, config_path):
        assert isinstance(load_schema_config(), dict)


class TestSaveSchemaConfig:
    def test_creates_file(self, config_path):
        save_schema_config({"schema_modules": []})
        assert config_path.exists()

    def test_content_round_trips(self, config_path):
        save_schema_config({"schema_modules": ["a.b", "c.d"]})
        content = json.loads(config_path.read_text(encoding="utf-8"))
        assert content["schema_modules"] == ["a.b", "c.d"]


class TestResetSchemaConfig:
    def test_returns_defaults(self, config_path):
        assert reset_schema_config() == get_default_schema_config()

    def test_overwrites_existing_file(self, config_path):
        config_path.write_text(json.dumps({"schema_modules": ["custom"]}), encoding="utf-8")
        reset_schema_config()
        assert json.loads(config_path.read_text(encoding="utf-8")) == get_default_schema_config()


class TestDeleteSchemaConfig:
    def test_returns_defaults(self, config_path):
        config_path.write_text(json.dumps({"schema_modules": ["custom"]}), encoding="utf-8")
        assert delete_schema_config() == get_default_schema_config()

    def test_no_error_when_file_missing(self, config_path):
        assert not config_path.exists()
        delete_schema_config()  # should not raise

    def test_file_recreated_with_defaults(self, config_path):
        config_path.write_text(json.dumps({"schema_modules": ["x"]}), encoding="utf-8")
        delete_schema_config()
        assert json.loads(config_path.read_text(encoding="utf-8")) == get_default_schema_config()


# ── registry.py ───────────────────────────────────────────────────────────────

class TestSchemaRegistryLookup:
    def test_schema_for_controldict_key(self, registry):
        schema = registry.schema_for_file_key("/case/system/controlDict", "startFrom")
        assert schema is not None
        assert schema.key == "startFrom"

    def test_schema_for_fvschemes_key(self, registry):
        assert registry.schema_for_file_key("/case/system/fvSchemes", "default.ddtSchemes") is not None

    def test_schema_for_fvsolution_key(self, registry):
        assert registry.schema_for_file_key("/case/system/fvSolution", "solver") is not None

    def test_unknown_file_returns_none(self, registry):
        assert registry.schema_for_file_key("/case/constant/unknown", "key") is None

    def test_unknown_key_returns_none(self, registry):
        assert registry.schema_for_file_key("/case/system/controlDict", "unknownKey") is None

    def test_none_path_returns_none(self, registry):
        assert registry.schema_for_file_key(None, "startFrom") is None

    def test_none_key_returns_none(self, registry):
        assert registry.schema_for_file_key("/case/system/controlDict", None) is None

    def test_choices_for_controldict_key(self, registry):
        choices = registry.choices_for_file_key("/case/system/controlDict", "startFrom")
        assert "firstTime" in choices
        assert "startTime" in choices
        assert "latestTime" in choices

    def test_choices_empty_for_unknown(self, registry):
        assert registry.choices_for_file_key("/unknown", "key") == []

    def test_choice_description_nonempty(self, registry):
        desc = registry.choice_description_for_value(
            "/case/system/controlDict", "startFrom", "firstTime"
        )
        assert len(desc) > 0

    def test_choice_description_empty_for_unknown_value(self, registry):
        assert (
            registry.choice_description_for_value(
                "/case/system/controlDict", "startFrom", "nosuchvalue"
            )
            == ""
        )

    def test_choice_note_nonempty_when_present(self, registry):
        note = registry.choice_note_for_value(
            "/case/system/controlDict", "writeCompression", "yes"
        )
        assert len(note) > 0

    def test_choice_note_empty_when_absent(self, registry):
        assert (
            registry.choice_note_for_value(
                "/case/system/controlDict", "startFrom", "firstTime"
            )
            == ""
        )

    def test_choice_supported_in_nonempty(self, registry):
        text = registry.choice_supported_in_for_value(
            "/case/system/controlDict", "startFrom", "firstTime"
        )
        assert len(text) > 0

    def test_choice_supported_in_empty_for_unknown_value(self, registry):
        assert (
            registry.choice_supported_in_for_value(
                "/case/system/controlDict", "startFrom", "nosuchvalue"
            )
            == ""
        )

    def test_schema_supported_in_nonempty(self, registry):
        assert len(registry.schema_supported_in_text("/case/system/controlDict", "startFrom")) > 0

    def test_schema_supported_in_empty_for_unknown(self, registry):
        assert registry.schema_supported_in_text("/unknown", "key") == ""

    def test_schema_note_nonempty_when_present(self, registry):
        assert len(registry.schema_note_text("/case/system/controlDict", "startFrom")) > 0

    def test_schema_note_empty_when_absent(self, registry):
        assert registry.schema_note_text("/case/system/controlDict", "writeFormat") == ""


class TestSchemaRegistryContextLookup:
    """parent_key-aware lookup for snappyHexMeshDict and fallback behaviour."""

    _SNAPPY = "/case/system/snappyHexMeshDict"

    def test_context_key_found_with_parent(self, registry):
        schema = registry.schema_for_file_key(
            self._SNAPPY, "nRelaxIter", parent_key="snapControls"
        )
        assert schema is not None
        assert "snap" in schema.label.lower() or "Snap" in schema.label

    def test_context_key_disambiguation(self, registry):
        snap_schema = registry.schema_for_file_key(
            self._SNAPPY, "nRelaxIter", parent_key="snapControls"
        )
        layer_schema = registry.schema_for_file_key(
            self._SNAPPY, "nRelaxIter", parent_key="addLayersControls"
        )
        assert snap_schema is not None
        assert layer_schema is not None
        assert snap_schema.label != layer_schema.label

    def test_flat_root_key_found_without_parent(self, registry):
        schema = registry.schema_for_file_key(self._SNAPPY, "castellatedMesh")
        assert schema is not None

    def test_flat_root_key_found_with_irrelevant_parent(self, registry):
        schema = registry.schema_for_file_key(
            self._SNAPPY, "castellatedMesh", parent_key="someBlock"
        )
        assert schema is not None

    def test_context_key_falls_back_when_no_parent(self, registry):
        # castellatedMeshControls.maxLocalCells has no plain fallback — returns None
        schema = registry.schema_for_file_key(self._SNAPPY, "maxLocalCells")
        assert schema is None

    def test_context_key_found_with_correct_parent(self, registry):
        schema = registry.schema_for_file_key(
            self._SNAPPY, "maxLocalCells", parent_key="castellatedMeshControls"
        )
        assert schema is not None

    def test_wrong_parent_falls_back_to_flat(self, registry):
        # nRelaxIter has no plain flat entry — wrong parent yields None
        schema = registry.schema_for_file_key(
            self._SNAPPY, "nRelaxIter", parent_key="unknownBlock"
        )
        assert schema is None

    def test_choices_resolved_with_parent(self, registry):
        choices = registry.choices_for_file_key(
            self._SNAPPY, "implicitFeatureSnap", parent_key="snapControls"
        )
        assert "true" in choices
        assert "false" in choices

    def test_switch_choices_on_root_key(self, registry):
        choices = registry.choices_for_file_key(self._SNAPPY, "snap")
        assert "true" in choices

    def test_meshquality_key_found_with_parent(self, registry):
        schema = registry.schema_for_file_key(
            self._SNAPPY, "maxNonOrtho", parent_key="meshQualityControls"
        )
        assert schema is not None

    def test_parent_key_none_equivalent_to_omitted(self, registry):
        a = registry.schema_for_file_key(self._SNAPPY, "snap", parent_key=None)
        b = registry.schema_for_file_key(self._SNAPPY, "snap")
        assert a == b


class TestGrandparentContextLookup:
    """grandparent_key fallback for blocks with user-defined parent names."""

    _SNAPPY = "/case/system/snappyHexMeshDict"

    # refinementSurfaces — parent is user-defined surface name
    def test_surface_level_via_grandparent(self, registry):
        schema = registry.schema_for_file_key(
            self._SNAPPY, "level",
            parent_key="motorBike",
            grandparent_key="refinementSurfaces",
        )
        assert schema is not None
        assert "Surface" in schema.label

    def test_surface_face_zone_via_grandparent(self, registry):
        schema = registry.schema_for_file_key(
            self._SNAPPY, "faceZone",
            parent_key="sphere1",
            grandparent_key="refinementSurfaces",
        )
        assert schema is not None

    def test_surface_cell_zone_inside_choices(self, registry):
        choices = registry.choices_for_file_key(
            self._SNAPPY, "cellZoneInside",
            parent_key="anyName",
            grandparent_key="refinementSurfaces",
        )
        assert set(choices) == {"inside", "outside", "insidePoint"}

    def test_surface_face_type_choices(self, registry):
        choices = registry.choices_for_file_key(
            self._SNAPPY, "faceType",
            parent_key="anyName",
            grandparent_key="refinementSurfaces",
        )
        assert "internal" in choices
        assert "baffle" in choices
        assert "boundary" in choices

    # refinementRegions — parent is user-defined region name
    def test_region_mode_via_grandparent(self, registry):
        schema = registry.schema_for_file_key(
            self._SNAPPY, "mode",
            parent_key="box1",
            grandparent_key="refinementRegions",
        )
        assert schema is not None

    def test_region_mode_choices(self, registry):
        choices = registry.choices_for_file_key(
            self._SNAPPY, "mode",
            parent_key="box1",
            grandparent_key="refinementRegions",
        )
        assert set(choices) == {"inside", "outside", "distance"}

    def test_region_levels_via_grandparent(self, registry):
        schema = registry.schema_for_file_key(
            self._SNAPPY, "levels",
            parent_key="sphere1",
            grandparent_key="refinementRegions",
        )
        assert schema is not None

    # layers — parent is user-defined patch name
    def test_n_surface_layers_via_grandparent(self, registry):
        schema = registry.schema_for_file_key(
            self._SNAPPY, "nSurfaceLayers",
            parent_key="motorBike_.*",
            grandparent_key="layers",
        )
        assert schema is not None

    # fallback behaviour
    def test_grandparent_not_used_when_parent_matches(self, registry):
        # patchInfo.type matches at parent level; grandparent should not interfere
        schema_parent = registry.schema_for_file_key(
            self._SNAPPY, "type",
            parent_key="patchInfo",
            grandparent_key="refinementSurfaces",
        )
        schema_no_grand = registry.schema_for_file_key(
            self._SNAPPY, "type",
            parent_key="patchInfo",
        )
        assert schema_parent is schema_no_grand

    def test_unknown_grandparent_falls_through_to_flat(self, registry):
        # snap has a flat entry; unknown grandparent should still return it
        schema = registry.schema_for_file_key(
            self._SNAPPY, "snap",
            parent_key="unknownParent",
            grandparent_key="unknownGrandparent",
        )
        assert schema is not None

    def test_no_match_at_any_level_returns_none(self, registry):
        schema = registry.schema_for_file_key(
            self._SNAPPY, "nonExistentKey",
            parent_key="anyParent",
            grandparent_key="anyGrandparent",
        )
        assert schema is None

    def test_grandparent_none_equivalent_to_omitted(self, registry):
        a = registry.schema_for_file_key(
            self._SNAPPY, "snap",
            grandparent_key=None,
        )
        b = registry.schema_for_file_key(self._SNAPPY, "snap")
        assert a == b


class TestSnappyHexMeshDictSchema:
    """Coverage for all major additions to the snappyHexMeshDict schema."""

    _SNAPPY = "/case/system/snappyHexMeshDict"

    # top-level new keys
    def test_merge_tolerance(self, registry):
        assert registry.schema_for_file_key(self._SNAPPY, "mergeTolerance") is not None

    def test_debug(self, registry):
        assert registry.schema_for_file_key(self._SNAPPY, "debug") is not None

    # castellatedMeshControls additions
    def test_planar_angle(self, registry):
        schema = registry.schema_for_file_key(
            self._SNAPPY, "planarAngle", parent_key="castellatedMeshControls"
        )
        assert schema is not None

    # snapControls addition
    def test_detect_near_surfaces_snap(self, registry):
        schema = registry.schema_for_file_key(
            self._SNAPPY, "detectNearSurfacesSnap", parent_key="snapControls"
        )
        assert schema is not None

    # addLayersControls additions
    @pytest.mark.parametrize("key", [
        "nSmoothSurfaceNormals",
        "nSmoothNormals",
        "nSmoothThickness",
        "maxFaceThicknessRatio",
        "maxThicknessToMedialRatio",
        "minMedianAxisAngle",
        "nMedialAxisIter",
        "nBufferCellsNoExtrude",
        "nRelaxedIter",
        "slipFeatureAngle",
    ])
    def test_add_layers_key(self, registry, key):
        schema = registry.schema_for_file_key(
            self._SNAPPY, key, parent_key="addLayersControls"
        )
        assert schema is not None, f"missing schema for addLayersControls.{key}"

    def test_n_relax_iter_layers_differs_from_snap(self, registry):
        snap = registry.schema_for_file_key(
            self._SNAPPY, "nRelaxIter", parent_key="snapControls"
        )
        layers = registry.schema_for_file_key(
            self._SNAPPY, "nRelaxIter", parent_key="addLayersControls"
        )
        assert snap is not None and layers is not None
        assert snap.label != layers.label

    def test_n_relaxed_iter_differs_from_n_relax_iter(self, registry):
        relax = registry.schema_for_file_key(
            self._SNAPPY, "nRelaxIter", parent_key="addLayersControls"
        )
        relaxed = registry.schema_for_file_key(
            self._SNAPPY, "nRelaxedIter", parent_key="addLayersControls"
        )
        assert relax is not None and relaxed is not None
        assert relax.label != relaxed.label

    # meshQualityControls.relaxed sub-dict
    @pytest.mark.parametrize("key", [
        "maxNonOrtho",
        "maxBoundarySkewness",
        "maxInternalSkewness",
        "minTwist",
    ])
    def test_relaxed_quality_key(self, registry, key):
        schema = registry.schema_for_file_key(self._SNAPPY, key, parent_key="relaxed")
        assert schema is not None, f"missing schema for relaxed.{key}"

    def test_relaxed_label_distinguished_from_standard(self, registry):
        standard = registry.schema_for_file_key(
            self._SNAPPY, "maxNonOrtho", parent_key="meshQualityControls"
        )
        relaxed = registry.schema_for_file_key(
            self._SNAPPY, "maxNonOrtho", parent_key="relaxed"
        )
        assert standard is not None and relaxed is not None
        assert standard.label != relaxed.label

    # patchInfo.type choices
    def test_patch_info_type_has_choices(self, registry):
        choices = registry.choices_for_file_key(
            self._SNAPPY, "type", parent_key="patchInfo"
        )
        assert "wall" in choices
        assert "patch" in choices
        assert "symmetry" in choices

    def test_patch_info_type_choice_has_description(self, registry):
        desc = registry.choice_description_for_value(
            self._SNAPPY, "type", "wall", parent_key="patchInfo"
        )
        assert len(desc) > 0


class TestSchemaRegistryModules:
    def test_default_modules_loaded(self, registry):
        modules = registry.get_schema_modules()
        assert "schemas.control_dict" in modules
        assert "schemas.fv_schemes" in modules
        assert "schemas.fv_solution" in modules

    def test_get_config_has_schema_modules_key(self, registry):
        assert "schema_modules" in registry.get_config()

    def test_set_modules_updates_list(self, registry):
        registry.set_schema_modules(["schemas.control_dict"])
        assert registry.get_schema_modules() == ["schemas.control_dict"]

    def test_apply_and_reload_clears_all_schemas(self, registry):
        registry.set_schema_modules([])
        registry.apply_and_reload()
        assert registry.schema_for_file_key("/case/system/controlDict", "startFrom") is None

    def test_apply_and_reload_with_partial_modules(self, registry):
        registry.set_schema_modules(["schemas.fv_schemes"])
        registry.apply_and_reload()
        assert registry.schema_for_file_key("/case/system/fvSchemes", "default.ddtSchemes") is not None
        assert registry.schema_for_file_key("/case/system/controlDict", "startFrom") is None

    def test_invalid_module_does_not_raise(self, registry):
        registry.set_schema_modules(["nonexistent.module.xyz"])
        registry.apply_and_reload()

    def test_invalid_module_results_in_empty_lookup(self, registry):
        registry.set_schema_modules(["nonexistent.module.xyz"])
        registry.apply_and_reload()
        assert registry.schema_for_file_key("/case/system/controlDict", "startFrom") is None

    def test_save_writes_config_file(self, registry, config_path):
        registry.save()
        assert config_path.exists()
        content = json.loads(config_path.read_text(encoding="utf-8"))
        assert "schema_modules" in content
