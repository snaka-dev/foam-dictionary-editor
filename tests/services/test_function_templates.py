# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""services/function_templates.py: function-object templates, read and filled."""
from __future__ import annotations

import os

import pytest

from foam.parser import OpenFoamParser
from services.function_templates import (
    add_include_func,
    case_field_names,
    case_patch_names,
    form_text,
    format_value,
    function_names,
    is_valid_function_name,
    list_templates,
    parse_template,
    render,
    template_root,
    value_problem,
)

# OpenCFD style: example values, the list of points spread over lines.
OPENCFD_PROBES = """\
/*---------------------------------------------------------------------------*\\
Description
    Writes out values of fields from cells nearest to specified locations.

\\*---------------------------------------------------------------------------*/

#includeEtc "caseDicts/postProcessing/probes/probes.cfg"

fields (p U);
probeLocations
(
    (0 0 0)
);

// ************************************************************************* //
"""

# Foundation 9+ style: typed <placeholders>, plumbing, comments.
FOUNDATION_FORCES = """\
/*---------------------------------------------------------------------------*\\
Description
    Calculates pressure and viscous forces over specified patches.

\\*---------------------------------------------------------------------------*/

type            forces;
libs            ("libforces.so");

patches     (<patchNames>); // Names of patches on which to calculate forces

rhoInf      <rhoInf>;       // Far field density; e.g., 1.225 kg/m^3 for air

CofR        <CofR>;         // Centre of rotation; e.g., (0 0 0)

nPoints     <number>;
axis        distance; // The independent variable

writeControl    timeStep;
writeInterval   1;

#includeEtc "caseDicts/functions/forces/forcesIncompressible.cfg"

// ************************************************************************* //
"""


def _kinds(text):
    return {e.key: (e.kind, e.required) for e in parse_template(text).entries}


class TestParse:
    def test_opencfd_examples(self):
        assert _kinds(OPENCFD_PROBES) == {
            "fields": ("fields", False),
            "probeLocations": ("points", False),  # a list of one point, not a point
        }
        entries = {e.key: e for e in parse_template(OPENCFD_PROBES).entries}
        assert form_text("points", entries["probeLocations"].value) == "0 0 0"

    def test_foundation_placeholders(self):
        assert _kinds(FOUNDATION_FORCES) == {
            "patches": ("patches", True),
            "rhoInf": ("number", True),
            "CofR": ("vector", True),
            "nPoints": ("number", True),
            "axis": ("word", False),
            "writeControl": ("word", False),
            "writeInterval": ("number", False),
        }

    def test_plumbing_is_not_in_the_form(self):
        keys = _kinds(FOUNDATION_FORCES)
        assert "type" not in keys and "libs" not in keys

    def test_placeholders_start_blank_with_their_comment_as_hint(self):
        entries = {e.key: e for e in parse_template(FOUNDATION_FORCES).entries}
        assert entries["CofR"].value == ""
        assert entries["CofR"].hint == "Centre of rotation; e.g., (0 0 0)"

    def test_a_placeholder_named_obscurely_takes_the_keys_meaning(self):
        text = "field           <specieName>;\n"
        assert _kinds(text) == {"field": ("field", True)}

    def test_entries_sharing_a_line_are_left_alone(self):
        text = "a 1; b 2;\nc 3;\n"
        assert list(_kinds(text)) == ["c"]

    def test_a_template_with_code_is_not_formable(self):
        text = "const word a;\nconst word b;\nfields (p);\n"
        parsed = parse_template(text)
        assert not parsed.formable and parsed.entries == ()


class TestRender:
    def test_untouched_is_byte_for_byte(self):
        for text in (OPENCFD_PROBES, FOUNDATION_FORCES):
            parsed = parse_template(text)
            same = {e.key: form_text(e.kind, e.value) for e in parsed.entries if not e.required}
            assert render(parsed, same) == text

    def test_editing_points_rewrites_only_that_entry(self):
        parsed = parse_template(OPENCFD_PROBES)
        out = render(parsed, {"probeLocations": "0.1 0 0\n0.2 0 0", "fields": "p U"})
        assert "probeLocations\n(\n    (0.1 0 0)\n    (0.2 0 0)\n);" in out
        assert "fields (p U);" in out
        assert out.replace(
            "    (0.1 0 0)\n    (0.2 0 0)", "    (0 0 0)"
        ) == OPENCFD_PROBES

    def test_filling_placeholders_keeps_padding_and_comments(self):
        parsed = parse_template(FOUNDATION_FORCES)
        out = render(
            parsed,
            {"patches": "walls", "rhoInf": "1.225", "CofR": "0 0 0", "nPoints": "100"},
        )
        assert "patches     (walls); // Names of patches on which to calculate forces" in out
        assert "rhoInf      1.225;       // Far field density" in out
        assert "CofR        (0 0 0);         // Centre of rotation" in out
        assert '#includeEtc "caseDicts/functions/forces/forcesIncompressible.cfg"' in out
        assert "<" not in out.split("*/", 1)[1].split("//")[0]
        OpenFoamParser(out).parse()


class TestValues:
    @pytest.mark.parametrize(
        "kind, value, problem",
        [
            ("fields", "p U", ""),
            ("fields", "", "empty"),
            ("fields", "p <x>", "placeholder"),
            ("fields", "p;U", "names"),
            ("field", "p U", "names"),
            ("number", "1.5e-3", ""),
            ("number", "abc", "number"),
            ("vector", "0 0 1", ""),
            ("vector", "(0, 0, 1)", ""),
            ("vector", "0 0", "vector"),
            ("points", "0 0 0\n1 0 0", ""),
            ("points", "0 0 0\n1 0", "points"),
            ("word", "timeStep", ""),
        ],
    )
    def test_value_problem(self, kind, value, problem):
        assert value_problem(kind, value) == problem

    def test_format_and_back(self):
        for kind, shown in (("fields", "p U"), ("vector", "0 0 1"), ("points", "0 0 0\n1 2 3")):
            assert form_text(kind, format_value(kind, shown)) == shown

    @pytest.mark.parametrize("name, ok", [("probes", True), ("probes2", True),
                                          ("my_probe", True), ("2probes", False),
                                          ("pro bes", False), ("../x", False)])
    def test_function_names(self, name, ok):
        assert is_valid_function_name(name) is ok


CONTROL = """\
FoamFile { version 2.0; format ascii; class dictionary; object controlDict; }
application icoFoam;

functions
{
    #includeFunc residuals(p, U)
    myProbes
    {
        type probes;
    }
}

// ************************************************************************* //
"""


class TestControlDict:
    def test_names_in_both_forms(self):
        assert function_names(CONTROL) == {"residuals", "myProbes"}

    def test_add_into_an_existing_block(self):
        out = add_include_func(CONTROL, "probes")
        assert "        type probes;\n    }\n    #includeFunc probes\n}" in out
        assert function_names(out) == {"residuals", "myProbes", "probes"}

    def test_already_there_is_left_alone(self):
        once = add_include_func(CONTROL, "probes")
        assert add_include_func(once, "probes") == once

    def test_one_line_block_is_opened_up(self):
        out = add_include_func("application icoFoam;\nfunctions {}\n", "probes")
        assert "functions\n{\n    #includeFunc probes\n}" in out

    def test_a_missing_block_goes_before_the_divider(self):
        text = "application icoFoam;\n\n// " + "*" * 73 + " //\n"
        out = add_include_func(text, "probes")
        assert out.index("functions") < out.index("// ***")
        assert function_names(out) == {"probes"}

    def test_a_missing_block_without_divider_goes_at_the_end(self):
        out = add_include_func("application icoFoam;", "probes")
        assert out.endswith("functions\n{\n    #includeFunc probes\n}\n")

    def test_functions_that_is_not_a_dictionary_is_refused(self):
        assert add_include_func("functions ();\n", "probes") is None


class TestCaseNames:
    def test_patches_from_the_mesh(self, tmp_path):
        mesh = tmp_path / "constant" / "polyMesh"
        mesh.mkdir(parents=True)
        (mesh / "boundary").write_text(
            "FoamFile { version 2.0; class polyBoundaryMesh; object boundary; }\n"
            "3\n(\n    movingWall\n    {\n        type wall;\n        inGroups 1(wall);\n"
            "    }\n    fixedWalls { type wall; }\n    frontAndBack { type empty; }\n)\n"
        )
        assert case_patch_names(str(tmp_path)) == ["movingWall", "fixedWalls", "frontAndBack"]

    def test_patches_from_0_before_there_is_a_mesh(self, tmp_path):
        (tmp_path / "0").mkdir()
        (tmp_path / "0" / "p").write_text(
            "FoamFile { object p; }\ninternalField uniform 0;\n"
            'boundaryField\n{\n    inlet { type zeroGradient; }\n    ".*Wall" { type wall; }\n'
            "    outlet\n    {\n        type fixedValue;\n        value uniform 0;\n    }\n}\n"
        )
        assert case_patch_names(str(tmp_path)) == ["inlet", "outlet"]

    def test_no_names_without_mesh_or_fields(self, tmp_path):
        assert case_patch_names(str(tmp_path)) == []

    def test_fields_from_0_and_the_latest_time(self, tmp_path):
        for d, names in (("0", ("p", "U", "p.orig")), ("0.5", ("p", "U", "phi.gz"))):
            (tmp_path / d).mkdir()
            for n in names:
                (tmp_path / d / n).write_text("")
        (tmp_path / "0.5" / "uniform").mkdir()
        assert case_field_names(str(tmp_path), "0.5") == ["p", "phi", "U"]


class TestInstallation:
    def test_template_root_and_listing(self, tmp_path):
        root = tmp_path / "etc" / "caseDicts" / "postProcessing"
        (root / "probes").mkdir(parents=True)
        (root / "probes" / "probes").write_text(OPENCFD_PROBES)
        (root / "probes" / "probes.cfg").write_text("type probes;\n")
        assert template_root([tmp_path / "nowhere", tmp_path / "etc"]) == str(root)
        (t,) = list_templates(str(root))
        assert (t.category, t.name) == ("probes", "probes")
        assert t.description.startswith("Writes out values of fields")

    def test_no_installation(self, tmp_path):
        assert template_root([tmp_path]) is None


_INSTALLED = "/usr/lib/openfoam/openfoam2606/etc"


@pytest.mark.skipif(not os.path.isdir(_INSTALLED), reason="needs an OpenFOAM v2606 installation")
def test_every_installed_template_round_trips():
    root = template_root([_INSTALLED])
    templates = list_templates(root)
    assert len(templates) > 40
    for t in templates:
        with open(t.path, encoding="utf-8", errors="replace") as f:
            text = f.read()
        parsed = parse_template(text)
        same = {e.key: form_text(e.kind, e.value) for e in parsed.entries if not e.required}
        assert render(parsed, same) == text, t.path


OPENCFD_SURFACES = """\
#includeEtc "caseDicts/postProcessing/visualization/surfaces.cfg"

fields       (p U);

surfaces
(
    xNormal
    {
        $cuttingPlane;
    }

    zNormal
    {
        $cuttingPlane;
        pointAndNormalDict
        {
            basePoint    (0 0 2); // Overrides default basePoint (0 0 0)
            normalVector $z;
        }
    }

    CAD
    {
        $patchSurface;
        patches     (CAD);
    }
);
"""


class TestSurfaces:
    """OpenCFD's nested surfaces template gets a form of its own."""

    def _entry(self):
        return next(e for e in parse_template(OPENCFD_SURFACES).entries if e.key == "surfaces")

    def test_planes_and_the_rest(self):
        from services.function_templates import SURFACES_SEPARATOR

        entry = self._entry()
        assert entry.kind == "surfaces"
        planes, others = entry.value.split(SURFACES_SEPARATOR)
        assert planes.strip().split("\n") == ["xNormal  0 0 0  1 0 0", "zNormal  0 0 2  0 0 1"]
        assert "CAD" in others and "$patchSurface;" in others

    def test_untouched_round_trips(self):
        parsed = parse_template(OPENCFD_SURFACES)
        same = {e.key: form_text(e.kind, e.value) for e in parsed.entries}
        assert render(parsed, same) == OPENCFD_SURFACES

    def test_edited_planes_are_written_explicitly(self):
        from services.function_templates import SURFACES_SEPARATOR

        parsed = parse_template(OPENCFD_SURFACES)
        out = render(parsed, {"surfaces": f"mid  0.05 0.05 0.005  0 0 1\n{SURFACES_SEPARATOR}\n"})
        # Today's keywords: OpenCFD warns on basePoint/normalVector (v1612+).
        assert (
            "    mid\n    {\n        $cuttingPlane;\n        pointAndNormalDict\n        {\n"
            "            point  (0.05 0.05 0.005);\n"
            "            normal (0 0 1);\n        }\n    }\n);"
        ) in out
        assert "CAD" not in out  # deleted from the "other surfaces" box
        OpenFoamParser(out).parse()

    def test_foundation_7_and_8_get_the_old_keywords(self):
        # They read basePoint *before* point, and $cuttingPlane supplies one:
        # a point written there would be ignored and the plane sit at the origin.
        from services.function_templates import SURFACES_SEPARATOR

        out = render(
            parse_template(OPENCFD_SURFACES),
            {"surfaces": f"mid  0.05 0.05 0.005  0 0 1\n{SURFACES_SEPARATOR}\n"},
            legacy_plane_keys=True,
        )
        assert "basePoint    (0.05 0.05 0.005);" in out
        assert "normalVector (0 0 1);" in out

    @pytest.mark.parametrize(
        "version, legacy",
        [("v2606", False), ("v2106", False), ("7", True), ("8", True), ("9", False),
         ("12", False), ("dev", False)],
    )
    def test_which_installations_need_the_old_keywords(self, tmp_path, version, legacy):
        from services.function_templates import legacy_plane_keywords

        (tmp_path / "etc").mkdir()
        (tmp_path / "etc" / "bashrc").write_text(f"export WM_PROJECT_VERSION={version}\n")
        assert legacy_plane_keywords(str(tmp_path)) is legacy
        assert legacy_plane_keywords(None) is False
        assert legacy_plane_keywords(str(tmp_path / "missing")) is False

    @pytest.mark.parametrize(
        "planes, problem",
        [("mid 0 0 0 0 0 1", ""), ("mid 0 0 0 0 0", "planes"), ("1x 0 0 0 0 0 1", "planes"), ("", "empty")],
    )
    def test_plane_rows_are_checked(self, planes, problem):
        from services.function_templates import SURFACES_SEPARATOR

        assert value_problem("surfaces", f"{planes}\n{SURFACES_SEPARATOR}\n") == problem
