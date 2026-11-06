# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""The "Show in 3-D view as" override -- the escape hatch when detection cannot help.

`ui/viewer_dicts.py` identifies a file by its name and then its FoamFile `object` header.
That covers a renamed topoSetDict, but not a renamed *sampling* dict: a standalone
sample/probes file is one function-object entry with no header at all, so there is nothing
to read. The override is how the user says what the program cannot work out.
"""
from __future__ import annotations

import json

import pytest

from foam.parser import OpenFoamParser
from ui import viewer_dicts as vd

SAMPLE = """type sets;
libs (sampling);
sets
{
    line { type uniform; axis x; start (0 0 0); end (1 0 0); nPoints 10; }
}
"""
TOPO = ("FoamFile { version 2.0; format ascii; class dictionary; object topoSetDict; }\n"
        "actions ( { name c0; type cellSet; action new; source boxToCell;"
        " box (0 0 0) (1 1 1); } );\n")


class TestTheResolver:
    def test_an_override_makes_an_unrecognisable_file_viewable(self):
        root = OpenFoamParser(SAMPLE).parse()
        assert vd.viewer_dict_kind("/case/system/sample-extra", root) is None
        assert vd.viewer_dict_kind("/case/system/sample-extra", root, vd.SAMPLING) == vd.SAMPLING

    def test_an_override_beats_the_header(self):
        # The user can see what a file is when its header is simply wrong.
        root = OpenFoamParser(TOPO).parse()
        assert vd.viewer_dict_kind("/case/system/topoSetDict", root) == vd.TOPO_SET
        assert vd.viewer_dict_kind("/case/system/topoSetDict", root, vd.SET_FIELDS) == vd.SET_FIELDS

    def test_an_unknown_override_is_not_trusted(self):
        # A hand-edited .foam-editor-files.json must not be able to name a nonexistent
        # overlay and have it dispatched.
        root = OpenFoamParser(TOPO).parse()
        assert vd.viewer_dict_kind("/case/system/topoSetDict", root, "nonsense") is None

    def test_an_empty_override_means_automatic(self):
        root = OpenFoamParser(TOPO).parse()
        assert vd.viewer_dict_kind("/case/system/topoSetDict", root, "") == vd.TOPO_SET


class TestPersistence:
    def test_the_choice_survives_a_reload_and_is_case_relative(self, tmp_path):
        from services.case_files_config import CaseFilesConfig

        cfg = CaseFilesConfig(str(tmp_path))
        cfg.set_viewer_kind("system/sample-extra", vd.SAMPLING)
        cfg.save()
        assert CaseFilesConfig(str(tmp_path)).get_viewer_kind("system/sample-extra") == vd.SAMPLING
        # Case-relative on disk, so moving the case directory does not strand the choice.
        stored = json.loads((tmp_path / ".foam-editor-files.json").read_text())
        assert stored["viewer_kinds"] == {"system/sample-extra": vd.SAMPLING}

    def test_clearing_returns_the_file_to_automatic(self, tmp_path):
        from services.case_files_config import CaseFilesConfig

        cfg = CaseFilesConfig(str(tmp_path))
        cfg.set_viewer_kind("system/sample-extra", vd.SAMPLING)
        cfg.set_viewer_kind("system/sample-extra", "")
        cfg.save()
        assert CaseFilesConfig(str(tmp_path)).get_viewer_kind("system/sample-extra") == ""
        # and leaves no empty key behind in the file
        stored = json.loads((tmp_path / ".foam-editor-files.json").read_text())
        assert "viewer_kinds" not in stored

    def test_an_absent_file_reports_automatic(self, tmp_path):
        from services.case_files_config import CaseFilesConfig

        assert CaseFilesConfig(str(tmp_path)).get_viewer_kind("system/anything") == ""


class TestTheWholeWayThrough:
    @pytest.fixture
    def case(self, tmp_path):
        (tmp_path / "system").mkdir()
        (tmp_path / "system" / "sample-extra").write_text(SAMPLE, encoding="utf-8")
        (tmp_path / "system" / "controlDict").write_text(
            "FoamFile { version 2.0; format ascii; class dictionary; object controlDict; }\n"
            "application icoFoam;\n", encoding="utf-8")
        return tmp_path

    def test_setting_the_override_renders_the_file(self, main_window, case):
        win = main_window
        win._load_case_dir(str(case))
        path = str(case / "system" / "sample-extra")
        assert win._viewer_kind_for(path, None) is None

        win._on_viewer_kind_requested(path, vd.SAMPLING)

        root = win.state.parsed_roots.get(path) or win._cache_parsed_root(path)
        assert win._viewer_kind_for(path, root) == vd.SAMPLING
        # ...and it was written, not just held in memory
        assert win.state.case_files_config.get_viewer_kind("system/sample-extra") == vd.SAMPLING

    def test_clearing_the_override_takes_it_back_out(self, main_window, case):
        win = main_window
        win._load_case_dir(str(case))
        path = str(case / "system" / "sample-extra")
        win._on_viewer_kind_requested(path, vd.SAMPLING)
        win._on_viewer_kind_requested(path, "")
        assert win._viewer_kind_for(path, None) is None
        assert win.state.case_files_config.get_viewer_kind("system/sample-extra") == ""

    def test_a_file_outside_the_case_is_refused(self, main_window, case, tmp_path):
        # An out-of-case include is read-only and has no case config to write to.
        win = main_window
        win._load_case_dir(str(case))
        outside = tmp_path.parent / "elsewhere"
        win._on_viewer_kind_requested(str(outside / "sample"), vd.SAMPLING)
        assert win.state.case_files_config.get_viewer_kinds() == {}
