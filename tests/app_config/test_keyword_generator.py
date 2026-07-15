# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for app_config/keyword_generator.py."""
from __future__ import annotations

import json

import app_config.keyword_generator as kg


# ---------------------------------------------------------------------------
# scan_src_lookup_keywords
# ---------------------------------------------------------------------------

def test_lookup_scan_collects_dictionary_read_calls(tmp_path):
    (tmp_path / "a.C").write_text(
        'word app(runTime.controlDict().lookup("application"));\n'
        'scalar p = dict.get<scalar>("writePrecision");\n'
        'dict.readEntry("timePrecision", prec_);\n'
        'if (dict.found("purgeWrite")) {}\n'
        'label n = dict.getOrDefault<label>("nOuterCorrectors", 1);\n'
        'dict.readIfPresent("adjustTimeStep", adjust_);\n'
    )
    (tmp_path / "b.H").write_text(
        'const word method = coeffs.lookupOrDefault<word>("method", "metis");\n'
    )
    words = kg.scan_src_lookup_keywords(tmp_path)
    assert words == {
        "application",
        "writePrecision",
        "timePrecision",
        "purgeWrite",
        "nOuterCorrectors",
        "adjustTimeStep",
        "method",
    }


def test_lookup_scan_rejects_non_keyword_forms(tmp_path):
    (tmp_path / "a.C").write_text(
        'dict.lookup(name);\n'          # not a string literal
        'dict.get<scalar>("x");\n'      # single-char name — not an identifier
        'dict.readEntry("123abc");\n'   # starts with a digit
        'helper("word");\n'             # unrelated function name
        'Xlookup("word");\n'            # no word boundary before "lookup"
    )
    assert kg.scan_src_lookup_keywords(tmp_path) == set()


def test_lookup_scan_ignores_other_suffixes(tmp_path):
    (tmp_path / "a.txt").write_text('dict.lookup("fromTxt");\n')
    (tmp_path / "b.C").write_text('dict.lookup("fromSource");\n')
    assert kg.scan_src_lookup_keywords(tmp_path) == {"fromSource"}


def test_lookup_scan_missing_dir(tmp_path):
    assert kg.scan_src_lookup_keywords(tmp_path / "nope") == set()


# ---------------------------------------------------------------------------
# generate(project_dir=...)
# ---------------------------------------------------------------------------

def test_generate_from_explicit_project_dir(tmp_path, monkeypatch):
    install = tmp_path / "openfoam9999"
    (install / "etc" / "caseDicts").mkdir(parents=True)
    (install / "src").mkdir()
    (install / "applications").mkdir()

    (install / "etc" / "caseDicts" / "sampleDict").write_text(
        "startFrom latestTime;\n"
    )
    (install / "src" / "Time.C").write_text('dict.lookup("srcKeyword");\n')
    (install / "applications" / "solver.C").write_text(
        'dict.get<scalar>("appKeyword");\n'
    )

    out = tmp_path / "out.json"
    monkeypatch.setattr(kg, "OUTPUT", out)
    # Env must be ignored when project_dir is explicit.
    monkeypatch.setenv("WM_PROJECT_DIR", str(tmp_path / "elsewhere"))
    monkeypatch.setenv("WM_PROJECT_VERSION", "0000")

    count, path = kg.generate(project_dir=install)
    assert path == out
    payload = json.loads(out.read_text())
    assert count == len(payload["keywords"])
    assert {"startFrom", "latestTime", "srcKeyword", "appKeyword"} <= set(
        payload["keywords"]
    )
    assert payload["source"] == str(install)
    assert payload["version"] == "openfoam9999"
    assert payload["generated"]  # ISO date
    assert "OpenCFD" in payload["note"]


def test_generate_raises_when_nothing_found(tmp_path, monkeypatch):
    monkeypatch.setattr(kg, "OUTPUT", tmp_path / "out.json")
    empty = tmp_path / "empty"
    empty.mkdir()
    try:
        kg.generate(project_dir=empty)
    except RuntimeError:
        pass
    else:
        raise AssertionError("generate() should raise when nothing is collected")
