# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Regression guard: every user-visible string literal in ui/ goes through tr().

DEVELOPER.md's i18n section claims "All user-visible strings in ui/ are
wrapped with tr()". Before 2026-08, that was false for four panels
(block_mesh_panel.py, editor_panel.py, comparison_tree_panel.py,
terminal_panel.py had zero/partial tr() coverage between them) plus a
scattering of dialogs and widgets found while building this guard. This test
is what keeps the claim true going forward.

Design (deliberately narrow, to keep false positives at zero):

- Scope: ui/**/*.py, excluding block_mesh_renderer.py and shape_mesh.py —
  those draw text with VTK's own label font, which has no glyph for
  non-ASCII characters and silently draws *nothing* for one (see
  DEVELOPER.md's "Text drawn by VTK, not Qt" note); a Japanese label there
  would vanish, not translate. tests/ui/test_shape_mesh.py and
  tests/ui/test_block_mesh_renderer_colors.py already AST-assert those two
  modules are ASCII-only, so they must stay tr()-free by construction.
- Sinks are a fixed, narrow set of Qt constructors/methods known to take
  display text, plus QMessageBox's classmethods and QInputDialog.getText.
  setStyleSheet/setObjectName/setProperty/findChild are deliberately not
  sinks — they were the biggest false-positive source in an earlier pass.
- A plain sink scan misses text routed through this codebase's own helpers
  (_menu_button, _ShapeOverlayMenu's master_label/legend_title kwargs), so
  _LOCAL_SINKS names those explicitly by argument position/keyword.
- An f-string reaching a sink is flagged the same as a bare literal, unless
  every letter came from inside a {…} placeholder (i.e. only interpolated
  data, no fixed prose) or from HTML tag syntax (f"<b>{value}</b>" carries
  no prose to translate — only the tag *name* has letters).
- Suppression: (a) a literal with no ASCII letter is skipped, so "-", "▾",
  "…" pass silently; (b) _ALLOWED lists specific strings with a one-line
  reason (axis symbols, OpenFOAM dictionary keywords that must match what
  the user's file actually says); (c) a trailing "# i18n: skip" comment for
  one-off cases (ast discards comments, so these are collected separately
  via tokenize).
- Anti-rot: every _LOCAL_SINKS and _ALLOWED entry is asserted to still
  exist/match somewhere in ui/, in both directions — the same rule this
  repo already applies to test_main_window_split.py's ownership lists — so
  a renamed helper or a deleted call site doesn't quietly disable a check.
"""
from __future__ import annotations

import ast
import pathlib
import re
import tokenize

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
UI_ROOT = PROJECT_ROOT / "ui"

# VTK draws this module's text with its own label font, which has no glyph
# for non-ASCII characters and draws nothing rather than a translated label
# (see this file's module docstring, and DEVELOPER.md's i18n section).
_EXCLUDED_FILES = {
    UI_ROOT / "panels" / "block_mesh_renderer.py",
    UI_ROOT / "panels" / "shape_mesh.py",
}

_CTOR_SINKS = {
    "QLabel", "QPushButton", "QCheckBox", "QRadioButton", "QAction", "QGroupBox", "QMenu",
}
_METHOD_SINKS = {
    "setText", "setToolTip", "setPlaceholderText", "setWindowTitle", "setTitle",
    "setStatusTip", "addAction", "addTab", "addRow", "addMenu", "setLabelText",
    "setHorizontalHeaderLabels", "showMessage",
}
_QMESSAGEBOX_METHODS = {"information", "warning", "critical", "question"}
_QINPUTDIALOG_METHODS = {"getText"}

# Helper sinks a plain scan of the Qt classes above would miss: name ->
# argument positions to check (int = positional index, str = keyword name).
_LOCAL_SINKS: dict[str, list[int | str]] = {
    "_menu_button": [0, 2],  # (text, menu, tooltip=None) — both positional
    "_ShapeOverlayMenu": ["master_label", "legend_title"],  # keyword-only in __init__
}

# Literal -> one-line reason it is deliberately not translated. Every entry
# must still occur as a string literal somewhere under ui/ (see
# test_allowed_entries_still_exist_in_ui), so a removed call site trims the
# list instead of leaving a stale, unverifiable exemption.
_ALLOWED: dict[str, str] = {
    "+X": "camera-view button label -- axis symbol, identical in Japanese",
    "-X": "camera-view button label -- axis symbol, identical in Japanese",
    "+Y": "camera-view button label -- axis symbol, identical in Japanese",
    "-Y": "camera-view button label -- axis symbol, identical in Japanese",
    "+Z": "camera-view button label -- axis symbol, identical in Japanese",
    "-Z": "camera-view button label -- axis symbol, identical in Japanese",
    "Iso": "camera-view button label -- identical in Japanese",
    "X": "vertex-table coordinate column header -- identical in Japanese",
    "Y": "vertex-table coordinate column header -- identical in Japanese",
    "Z": "vertex-table coordinate column header -- identical in Japanese",
    "new": "topoSet action keyword -- the literal word in the dict file being viewed",
    "add": "topoSet action keyword -- the literal word in the dict file being viewed",
    "subtract": "topoSet action keyword -- the literal word in the dict file being viewed",
    "subset": "topoSet action keyword -- the literal word in the dict file being viewed",
    "invert": "topoSet action keyword -- the literal word in the dict file being viewed",
    "surface": "snappyHexMesh category keyword -- the literal word in the dict file being viewed",
    "region": "snappyHexMesh category keyword -- the literal word in the dict file being viewed",
    "geometry": "snappyHexMesh category keyword -- the literal word in the dict file being viewed",
}

_TAG_RE = re.compile(r"<[^>]*>")


def _has_ascii_letter(s: str) -> bool:
    return any(c.isalpha() and c.isascii() for c in s)


def _skip_comment_lines(path: pathlib.Path) -> set[int]:
    """Source lines carrying a trailing '# i18n: skip' comment.

    ast discards comments, so this is a separate tokenize pass, matching
    how this repo already collects other comment-driven exemptions.
    """
    lines: set[int] = set()
    with open(path, "rb") as f:
        for tok in tokenize.tokenize(f.readline):
            if tok.type == tokenize.COMMENT and "i18n: skip" in tok.string:
                lines.add(tok.start[0])
    return lines


def _check_value(node: ast.AST, findings: list[tuple[int, str]], skip_lines: set[int]) -> None:
    """Record a violation if *node* is an unwrapped literal carrying prose."""
    if isinstance(node, ast.List):
        for elt in node.elts:
            _check_value(elt, findings, skip_lines)
        return

    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        text = node.value
        if not _has_ascii_letter(text) or text in _ALLOWED or node.lineno in skip_lines:
            return
        findings.append((node.lineno, repr(text)))
        return

    if isinstance(node, ast.JoinedStr):
        # Only the literal (non-interpolated) parts matter: an f-string whose
        # letters all live inside {…} placeholders carries no fixed prose to
        # translate. HTML tag syntax is stripped too -- f"<b>{value}</b>"
        # wraps dynamic data in markup, not prose (only the tag *name* has
        # letters); a real f"<b>Some prose</b>" still trips this, since the
        # prose itself survives the strip.
        const_parts = "".join(
            v.value for v in node.values
            if isinstance(v, ast.Constant) and isinstance(v.value, str)
        )
        prose = _TAG_RE.sub("", const_parts)
        if not _has_ascii_letter(prose) or node.lineno in skip_lines:
            return
        findings.append((node.lineno, f"f-string with fixed text {const_parts!r}"))


def _call_name(node: ast.Call) -> tuple[str | None, bool, str | None]:
    """Return (name, is_method_call, owner_name_if_a_simple_attribute_access)."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id, False, None
    if isinstance(func, ast.Attribute):
        owner = func.value.id if isinstance(func.value, ast.Name) else None
        return func.attr, True, owner
    return None, False, None


def _scan_file(path: pathlib.Path) -> list[tuple[int, str]]:
    findings: list[tuple[int, str]] = []
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    skip_lines = _skip_comment_lines(path)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name, is_method, owner = _call_name(node)

        if name in _CTOR_SINKS or (is_method and name in _METHOD_SINKS):
            for arg in node.args:
                _check_value(arg, findings, skip_lines)
        elif is_method and owner == "QMessageBox" and name in _QMESSAGEBOX_METHODS:
            for arg in node.args:
                _check_value(arg, findings, skip_lines)
        elif is_method and owner == "QInputDialog" and name in _QINPUTDIALOG_METHODS:
            for arg in node.args:
                _check_value(arg, findings, skip_lines)
        elif name in _LOCAL_SINKS:
            for spec in _LOCAL_SINKS[name]:
                if isinstance(spec, int):
                    if len(node.args) > spec:
                        _check_value(node.args[spec], findings, skip_lines)
                else:
                    for kw in node.keywords:
                        if kw.arg == spec:
                            _check_value(kw.value, findings, skip_lines)
    return findings


def _ui_files() -> list[pathlib.Path]:
    return [p for p in sorted(UI_ROOT.rglob("*.py")) if p not in _EXCLUDED_FILES]


def test_every_ui_string_reaching_a_sink_is_translated():
    """Fail on a hardcoded English string handed straight to a Qt display sink.

    Fix: wrap the literal with tr("...") (see i18n/__init__.py) and add the
    matching entry to i18n/ja.py, or — if it genuinely should not be
    translated (an axis symbol, an OpenFOAM keyword the dict file itself
    uses) — add it to this file's _ALLOWED with a one-line reason, or mark
    the line with a trailing '# i18n: skip' comment for a one-off case.
    """
    all_findings = []
    for path in _ui_files():
        for lineno, text in _scan_file(path):
            all_findings.append((path.relative_to(PROJECT_ROOT), lineno, text))

    assert not all_findings, "Untranslated string(s) reaching a UI sink:\n" + "\n".join(
        f"  {path}:{lineno}: {text} -- wrap with tr(), or allowlist/skip if intentional"
        for path, lineno, text in all_findings
    )


def _defined_names(paths: list[pathlib.Path]) -> set[str]:
    names: set[str] = set()
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name)
    return names


def test_local_sinks_still_exist_in_ui():
    """Anti-rot: a _LOCAL_SINKS entry naming a helper that no longer exists
    silently stops checking it. Keep the list matching real code, in both
    directions.
    """
    defined = _defined_names(_ui_files())
    stale = sorted(set(_LOCAL_SINKS) - defined)
    assert not stale, (
        "tests/ui/test_translatable_strings.py's _LOCAL_SINKS names a helper "
        f"no longer defined under ui/: {stale} -- update or remove the entry"
    )


def _all_string_literals(paths: list[pathlib.Path]) -> set[str]:
    literals: set[str] = set()
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                literals.add(node.value)
    return literals


def test_allowed_entries_still_exist_in_ui():
    """Anti-rot: an _ALLOWED literal that no longer appears anywhere in ui/
    is a stale exemption -- the code it excused is gone, so drop the entry
    rather than let it excuse nothing forever.
    """
    literals = _all_string_literals(_ui_files())
    stale = sorted(text for text in _ALLOWED if text not in literals)
    assert not stale, (
        "tests/ui/test_translatable_strings.py's _ALLOWED lists a string that "
        f"no longer occurs in ui/: {stale} -- remove the stale entry"
    )
