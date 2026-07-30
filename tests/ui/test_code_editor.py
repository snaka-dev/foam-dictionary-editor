# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for ui/widgets/code_editor.py — fold map, toggle, and auto-fold."""
from __future__ import annotations

from ui.widgets.code_editor import CodeEditor

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _editor(text: str, qapp) -> CodeEditor:  # noqa: ARG001 (qapp required by PySide6)
    ed = CodeEditor()
    ed.setPlainText(text)
    return ed


# ---------------------------------------------------------------------------
# _compute_fold_map
# ---------------------------------------------------------------------------

class TestComputeFoldMap:
    def test_empty_text(self, qapp):
        ed = _editor("", qapp)
        assert ed._fold_map == {}

    def test_single_pair(self, qapp):
        text = "FoamFile\n{\n    version 2.0;\n}\n"
        ed = _editor(text, qapp)
        # line 1 ('{') should map to line 3 ('}')
        assert 1 in ed._fold_map
        assert ed._fold_map[1] == 3

    def test_single_line_braces_excluded(self, qapp):
        text = "key { value; }\n"
        ed = _editor(text, qapp)
        assert ed._fold_map == {}

    def test_nested_pairs(self, qapp):
        text = "outer\n{\n    inner\n    {\n        x 1;\n    }\n}\n"
        ed = _editor(text, qapp)
        # outer: line 1 → line 6; inner: line 3 → line 5
        assert ed._fold_map.get(1) == 6
        assert ed._fold_map.get(3) == 5

    def test_multiple_top_level_pairs(self, qapp):
        text = "a\n{\n    x 1;\n}\nb\n{\n    y 2;\n}\n"
        ed = _editor(text, qapp)
        assert ed._fold_map.get(1) == 3
        assert ed._fold_map.get(5) == 7

    def test_line_comment_brace_ignored(self, qapp):
        text = "a\n{\n    // } fake close\n    x 1;\n}\n"
        ed = _editor(text, qapp)
        assert ed._fold_map.get(1) == 4

    def test_block_comment_brace_ignored(self, qapp):
        text = "a\n{\n    /* { nested */ x 1;\n}\n"
        ed = _editor(text, qapp)
        assert ed._fold_map.get(1) == 3

    def test_string_literal_brace_ignored(self, qapp):
        text = 'a\n{\n    s "value { here";\n}\n'
        ed = _editor(text, qapp)
        assert ed._fold_map.get(1) == 3

    def test_multiline_block_comment(self, qapp):
        text = "/*\n{\n*/\na\n{\n    x 1;\n}\n"
        ed = _editor(text, qapp)
        # block comment spans lines 0-2, so first real '{' is line 4
        assert 1 not in ed._fold_map
        assert ed._fold_map.get(4) == 6


# ---------------------------------------------------------------------------
# _toggle_fold
# ---------------------------------------------------------------------------

class TestToggleFold:
    def _foam_text(self) -> str:
        return (
            "FoamFile\n"
            "{\n"
            "    version 2.0;\n"
            "    format  ascii;\n"
            "}\n"
            "a 1;\n"
        )

    def test_collapse_hides_inner_blocks(self, qapp):
        ed = _editor(self._foam_text(), qapp)
        # FoamFile block: open=1, close=4
        open_ln = 1
        assert open_ln in ed._fold_map
        # ensure it's expanded first (auto-fold would have already collapsed it)
        # toggle twice: expand then collapse, or just check state
        if open_ln in ed._folded:
            ed._toggle_fold(open_ln)  # expand
        ed._toggle_fold(open_ln)      # collapse
        doc = ed.document()
        for ln in range(open_ln + 1, ed._fold_map[open_ln] + 1):
            assert not doc.findBlockByNumber(ln).isVisible(), f"block {ln} should be hidden"
        assert open_ln in ed._folded

    def test_expand_restores_visibility(self, qapp):
        ed = _editor(self._foam_text(), qapp)
        open_ln = 1
        if open_ln not in ed._folded:
            ed._toggle_fold(open_ln)  # collapse
        ed._toggle_fold(open_ln)       # expand
        doc = ed.document()
        for ln in range(open_ln + 1, ed._fold_map[open_ln] + 1):
            assert doc.findBlockByNumber(ln).isVisible(), f"block {ln} should be visible"
        assert open_ln not in ed._folded

    def test_toggle_unknown_line_is_noop(self, qapp):
        ed = _editor(self._foam_text(), qapp)
        ed._toggle_fold(99)  # should not raise
        assert ed._folded == {1}  # only auto-folded FoamFile remains


# ---------------------------------------------------------------------------
# _auto_fold_foamfile
# ---------------------------------------------------------------------------

class TestAutoFoldFoamFile:
    def test_foamfile_block_auto_collapsed(self, qapp):
        text = (
            "FoamFile\n"
            "{\n"
            "    version 2.0;\n"
            "}\n"
            "key value;\n"
        )
        ed = _editor(text, qapp)
        assert 1 in ed._folded

    def test_foamfile_brace_same_line(self, qapp):
        text = (
            "FoamFile {\n"
            "    version 2.0;\n"
            "}\n"
            "key value;\n"
        )
        ed = _editor(text, qapp)
        assert 0 in ed._folded

    def test_non_foamfile_block_not_auto_folded(self, qapp):
        text = (
            "subDict\n"
            "{\n"
            "    x 1;\n"
            "}\n"
        )
        ed = _editor(text, qapp)
        assert ed._folded == set()

    def test_setplaintext_resets_fold_state(self, qapp):
        text = "FoamFile\n{\n    version 2.0;\n}\nkey value;\n"
        ed = _editor(text, qapp)
        assert ed._folded  # FoamFile auto-folded
        ed.setPlainText("simple 1;\n")
        assert ed._folded == set()
        assert ed._fold_map == {}


# ---------------------------------------------------------------------------
# _compute_comment_folds
# ---------------------------------------------------------------------------

class TestComputeCommentFolds:
    def test_block_comment_folds(self, qapp):
        text = "/* a\n b\n c */\nkey value;\n"
        ed = _editor(text, qapp)
        assert ed._comment_folds.get(0) == 2
        # comment folds are merged into the shared fold map
        assert ed._fold_map.get(0) == 2

    def test_line_comment_run_folds(self, qapp):
        text = "// one\n// two\n// three\nkey value;\n"
        ed = _editor(text, qapp)
        assert ed._comment_folds.get(0) == 2

    def test_single_comment_line_not_folded(self, qapp):
        text = "key value;\n// lonely\nother 1;\n"
        ed = _editor(text, qapp)
        assert ed._comment_folds == {}

    def test_blank_line_breaks_run(self, qapp):
        text = "// one\n\n// two\nkey value;\n"
        ed = _editor(text, qapp)
        assert ed._comment_folds == {}

    def test_code_after_block_close_not_comment(self, qapp):
        text = "/* a\n b */ code;\nkey value;\n"
        ed = _editor(text, qapp)
        # line 1 has real code after '*/', so the run is only line 0 → no fold
        assert ed._comment_folds == {}


# ---------------------------------------------------------------------------
# _auto_fold_header_comment
# ---------------------------------------------------------------------------

class TestAutoFoldHeaderComment:
    def test_header_banner_auto_collapsed(self, qapp):
        text = "/*----\n banner\n----*/\nkey value;\n"
        ed = _editor(text, qapp)
        assert 0 in ed._folded

    def test_lower_comment_block_not_auto_folded(self, qapp):
        text = (
            "key value;\n"   # 0
            "other 1;\n"     # 1
            "more 2;\n"      # 2
            "extra 3;\n"     # 3
            "pad 4;\n"       # 4
            "pad 5;\n"       # 5
            "// block a\n"   # 6
            "// block b\n"   # 7
            "// block c\n"   # 8
        )
        ed = _editor(text, qapp)
        assert ed._comment_folds.get(6) == 8
        # starts below the top-of-file threshold, so it is not auto-collapsed
        assert 6 not in ed._folded
        assert ed._folded == set()
