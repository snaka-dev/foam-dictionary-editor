# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for services/include_scan.py.

The scan runs on every file-list refresh, so its cheapness guarantees (the
substring gate, the size limit, the mtime memo) are pinned here alongside its
results. The etc-root discovery chain is exercised with a monkeypatched
environment so no real OpenFOAM installation is needed.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from foam.include_resolver import parse_include_directive
from services import include_scan
from services.include_scan import (
    clear_foam_etc_cache,
    clear_scan_cache,
    copy_destination_for,
    foam_etc_dirs,
    included_files,
    resolve_directive_text,
    scan_includes,
)


@pytest.fixture(autouse=True)
def _clear_caches():
    clear_scan_cache()
    clear_foam_etc_cache()
    yield
    clear_scan_cache()
    clear_foam_etc_cache()


def _case(tmp_path: Path) -> Path:
    """Build a case skeleton in a *subdirectory*, so tmp_path stays available
    for things that must sit outside the case (an OpenFOAM install, say)."""
    case = tmp_path / "case"
    for sub in ("system", "constant", "0"):
        (case / sub).mkdir(parents=True, exist_ok=True)
    return case


def _write(path: Path, text: str = "// stub\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


# ── scanning ──────────────────────────────────────────────────────────────────


class TestScanIncludes:
    def test_scan_finds_include_in_control_dict(self, tmp_path):
        case = _case(tmp_path)
        src = _write(case / "system" / "controlDict", 'application foo;\n#include "extra"\n')
        _write(case / "system" / "extra")
        hits = scan_includes(str(case), [str(src)])
        assert len(hits) == 1
        assert hits[0].ref.target == "extra"
        assert hits[0].line == 2
        assert hits[0].text == '#include "extra"'
        assert hits[0].resolved.path == case / "system" / "extra"

    def test_hit_text_matches_parser_directive_value(self, tmp_path):
        # The tooltip lookup keys on this, so it must equal what the parser
        # stores as a directive_entry's value.
        from foam.parser import OpenFoamParser

        case = _case(tmp_path)
        body = '#include "extra"\n#includeFunc mag(U)\n'
        src = _write(case / "system" / "controlDict", body)
        _write(case / "system" / "extra")
        scanned = [h.text for h in scan_includes(str(case), [str(src)])]
        parsed = [
            str(c.value)
            for c in OpenFoamParser(body).parse().children
            if c.node_type == "directive_entry"
        ]
        assert scanned == parsed

    def test_scan_skips_code_stream_cpp_headers(self, tmp_path):
        case = _case(tmp_path)
        src = _write(
            case / "system" / "controlDict",
            'code\n#{\n    #include "createTime.H"\n    #include <fvCFD.H>\n#};\n',
        )
        assert scan_includes(str(case), [str(src)]) == []

    def test_scan_is_not_transitive(self, tmp_path):
        case = _case(tmp_path)
        src = _write(case / "system" / "controlDict", '#include "a"\n')
        _write(case / "system" / "a", '#include "b"\n')
        _write(case / "system" / "b")
        hits = scan_includes(str(case), [str(src)])
        assert [h.ref.target for h in hits] == ["a"]

    def test_scan_skips_large_files(self, tmp_path):
        case = _case(tmp_path)
        padding = "// pad\n" * 100_000  # comfortably over the 512 KB limit
        src = _write(case / "constant" / "big", padding + '#include "extra"\n')
        assert src.stat().st_size > 512 * 1024
        assert scan_includes(str(case), [str(src)]) == []

    def test_scan_skips_log_files(self, tmp_path):
        case = _case(tmp_path)
        src = _write(case / "log.blockMesh", '#include "extra"\n')
        assert scan_includes(str(case), [str(src)]) == []

    def test_scan_skips_scripts(self, tmp_path):
        case = _case(tmp_path)
        src = _write(case / "Allrun", '#!/bin/sh\n#include "extra"\n')
        assert scan_includes(str(case), [str(src)]) == []

    def test_scan_tolerates_missing_file(self, tmp_path):
        case = _case(tmp_path)
        assert scan_includes(str(case), [str(case / "system" / "gone")]) == []

    def test_scan_reports_each_occurrence(self, tmp_path):
        case = _case(tmp_path)
        a = _write(case / "0" / "U", '#include "shared"\n')
        b = _write(case / "0" / "p", '#include "shared"\n')
        _write(case / "0" / "shared")
        hits = scan_includes(str(case), [str(a), str(b)])
        assert len(hits) == 2
        # The resolution is memoised, but each hit still names its own file.
        assert {h.source_file for h in hits} == {a, b}
        assert {h.resolved.source_file for h in hits} == {a, b}


class TestScanCache:
    def test_cache_reuses_unchanged_file(self, tmp_path, monkeypatch):
        case = _case(tmp_path)
        src = _write(case / "system" / "controlDict", '#include "extra"\n')
        _write(case / "system" / "extra")

        reads = []
        original = include_scan.read_foam_file

        def counting_read(path):
            reads.append(str(path))
            return original(path)

        monkeypatch.setattr(include_scan, "read_foam_file", counting_read)
        scan_includes(str(case), [str(src)])
        scan_includes(str(case), [str(src)])
        assert reads.count(str(src)) == 1

    def test_cache_invalidated_on_change(self, tmp_path):
        case = _case(tmp_path)
        src = _write(case / "system" / "controlDict", '#include "a"\n')
        _write(case / "system" / "a")
        _write(case / "system" / "b")
        assert [h.ref.target for h in scan_includes(str(case), [str(src)])] == ["a"]

        # Rewrite with a different size so the (mtime, size) key changes even if
        # the filesystem timestamp resolution is coarse.
        src.write_text('#include "bb"\n#include "b"\n')
        assert [h.ref.target for h in scan_includes(str(case), [str(src)])] == ["bb", "b"]


# ── the file-list view ────────────────────────────────────────────────────────


class TestIncludedFiles:
    def test_splits_inside_and_outside_case(self, tmp_path):
        case = _case(tmp_path)
        etc = tmp_path / "install" / "etc"
        outside = _write(etc / "caseDicts" / "setConstraintTypes")
        inside = _write(case / "constant" / "caseSettings")
        src_u = _write(case / "0" / "U", '#includeEtc "caseDicts/setConstraintTypes"\n')
        src_c = _write(case / "constant" / "dynamicMeshDict", '#include "caseSettings"\n')

        new, origins, read_only = included_files(
            str(case), [str(src_u), str(src_c)], etc_dirs=[etc]
        )
        assert set(new) == {str(outside), str(inside)}
        assert read_only == {str(outside)}
        assert origins[str(inside)] == "constant/dynamicMeshDict"

    def test_already_listed_target_is_not_returned(self, tmp_path):
        case = _case(tmp_path)
        src = _write(case / "system" / "controlDict", '#include "extra"\n')
        extra = _write(case / "system" / "extra")
        new, _origins, _ro = included_files(str(case), [str(src), str(extra)])
        assert new == []

    def test_symlinked_target_deduped_against_its_real_file(self, tmp_path):
        case = _case(tmp_path)
        real = _write(case / "system" / "shared")
        link = case / "system" / "alias"
        try:
            link.symlink_to(real)
        except (OSError, NotImplementedError):
            pytest.skip("symlinks unsupported on this platform")
        src = _write(case / "system" / "controlDict", '#include "alias"\n')
        new, _origins, _ro = included_files(str(case), [str(src), str(real)])
        assert new == []  # the alias resolves to a file already listed

    def test_origin_label_joins_several_includers(self, tmp_path):
        case = _case(tmp_path)
        target = _write(case / "0" / "shared")
        sources = []
        for name in ("U", "p", "k", "epsilon"):
            sources.append(str(_write(case / "0" / name, '#include "shared"\n')))
        _new, origins, _ro = included_files(str(case), sources)
        assert origins[str(target)] == "0/U, 0/p +2 more"

    def test_gz_target_is_not_listed(self, tmp_path):
        # It resolves, but read_foam_file cannot decompress it.
        case = _case(tmp_path)
        _write(case / "constant" / "big.gz")
        src = _write(case / "constant" / "props", '#include "big"\n')
        new, _origins, _ro = included_files(str(case), [str(src)])
        assert new == []

    def test_unresolved_include_is_not_listed(self, tmp_path):
        case = _case(tmp_path)
        src = _write(case / "system" / "controlDict", '#sinclude "nope"\n')
        new, _origins, read_only = included_files(str(case), [str(src)])
        assert new == []
        assert read_only == set()


# ── on-demand resolution ──────────────────────────────────────────────────────


class TestResolveDirectiveText:
    def test_resolves_one_directive(self, tmp_path):
        case = _case(tmp_path)
        src = _write(case / "system" / "controlDict")
        target = _write(case / "system" / "extra")
        got = resolve_directive_text('#include "extra"', str(src), str(case))
        assert got is not None and got.path == target

    def test_returns_none_for_other_directives(self, tmp_path):
        case = _case(tmp_path)
        src = _write(case / "system" / "controlDict")
        assert resolve_directive_text("#eval{1+2}", str(src), str(case)) is None


# ── copy destination ──────────────────────────────────────────────────────────


class TestCopyDestination:
    def test_include_func_goes_to_system(self, tmp_path):
        case = _case(tmp_path)
        ref = parse_include_directive("#includeFunc solverInfo")
        src = Path("/opt/openfoam/etc/caseDicts/postProcessing/numerical/solverInfo")
        assert copy_destination_for(src, case, ref) == case / "system" / "solverInfo"

    def test_include_etc_flattens_to_system(self, tmp_path):
        case = _case(tmp_path)
        ref = parse_include_directive('#includeEtc "caseDicts/postProcessing/graphs/sampleDict.cfg"')
        src = Path("/opt/openfoam/etc/caseDicts/postProcessing/graphs/sampleDict.cfg")
        assert copy_destination_for(src, case, ref) == case / "system" / "sampleDict.cfg"

    def test_plain_include_mirrors_relative_target(self, tmp_path):
        # Keeping the relative path means the directive re-resolves to the copy
        # with no edit at all.
        case = _case(tmp_path)
        ref = parse_include_directive('#include "include/initialConditions"')
        src = Path("/elsewhere/include/initialConditions")
        assert copy_destination_for(src, case, ref) == case / "include" / "initialConditions"

    def test_absolute_target_falls_back_to_system(self, tmp_path):
        case = _case(tmp_path)
        ref = parse_include_directive('#include "/abs/shared"')
        assert copy_destination_for(Path("/abs/shared"), case, ref) == case / "system" / "shared"

    def test_parent_traversal_falls_back_to_system(self, tmp_path):
        case = _case(tmp_path)
        ref = parse_include_directive('#include "../outside/shared"')
        src = Path("/elsewhere/outside/shared")
        assert copy_destination_for(src, case, ref) == case / "system" / "shared"

    def test_no_ref_falls_back_to_system(self, tmp_path):
        case = _case(tmp_path)
        assert copy_destination_for(Path("/a/b/thing"), case, None) == case / "system" / "thing"


# ── etc root discovery ────────────────────────────────────────────────────────


class TestFoamEtcDirs:
    def test_empty_without_installation(self, tmp_path, monkeypatch):
        monkeypatch.setattr(include_scan, "discover_installations", lambda: [])
        monkeypatch.setattr(
            include_scan, "foam_env_dirs", lambda: _FakeEnvDirs(version=None, etc_dir=None)
        )
        monkeypatch.setattr(include_scan, "get_app_config", lambda: _FakeConfig(None))
        clear_foam_etc_cache()
        assert foam_etc_dirs() == ()

    def test_prefers_user_override(self, tmp_path, monkeypatch):
        user_etc = tmp_path / "chosen" / "etc"
        user_etc.mkdir(parents=True)
        env_etc = tmp_path / "env" / "etc"
        env_etc.mkdir(parents=True)
        monkeypatch.setattr(include_scan, "discover_installations", lambda: [])
        monkeypatch.setattr(
            include_scan, "foam_env_dirs", lambda: _FakeEnvDirs(version=None, etc_dir=env_etc)
        )
        monkeypatch.setattr(
            include_scan, "get_app_config", lambda: _FakeConfig(str(tmp_path / "chosen"))
        )
        clear_foam_etc_cache()
        assert foam_etc_dirs() == (user_etc, env_etc)

    def test_skips_directories_that_do_not_exist(self, tmp_path, monkeypatch):
        monkeypatch.setattr(include_scan, "discover_installations", lambda: [])
        monkeypatch.setattr(
            include_scan,
            "foam_env_dirs",
            lambda: _FakeEnvDirs(version=None, etc_dir=tmp_path / "gone"),
        )
        monkeypatch.setattr(include_scan, "get_app_config", lambda: _FakeConfig(None))
        clear_foam_etc_cache()
        assert foam_etc_dirs() == ()


class _FakeEnvDirs:
    def __init__(self, version, etc_dir):
        self.version = version
        self.etc_dir = etc_dir


class _FakeConfig:
    def __init__(self, openfoam_dir):
        self._dir = openfoam_dir

    def get_openfoam_dir(self):
        return self._dir
