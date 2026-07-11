# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Scan an OpenFOAM installation to build app_config/foam_keywords.json.

Shared by tools/generate_foam_keywords.py (CLI) and the Settings menu action.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Callable

OUTPUT = Path(__file__).parent / "foam_keywords.json"

_IDENTIFIER_RE = re.compile(r"^[A-Za-z]\w+$")
_TYPENAME_RE = re.compile(r'TypeName\s*\(\s*"(\w+)"')
_CLASSNAME_RE = re.compile(r'ClassName\s*\(\s*"(\w+)"')
_NAMED_RTST_RE = re.compile(
    r'addNamedToRunTimeSelectionTable\s*\(\s*\w+\s*,\s*\w+\s*,\s*\w+\s*,\s*(\w+)\s*\)'
)
_NAMED_MFST_RE = re.compile(
    r'addNamedToMemberFunctionSelectionTable\s*\(\s*\w+\s*,\s*\w+\s*,\s*\w+\s*,\s*\w+\s*,\s*(\w+)\s*\)'
)


def _is_keyword(tok: str) -> bool:
    return bool(_IDENTIFIER_RE.match(tok))


def _foam_dirs() -> tuple[Path, Path, str]:
    """Return (foam_etc, foam_src, project_label) from environment."""
    project = Path(os.environ.get("WM_PROJECT_DIR", ""))
    etc = Path(os.environ.get("FOAM_ETC", ""))
    src = Path(os.environ.get("FOAM_SRC", ""))
    if not etc.is_dir() and project.is_dir():
        etc = project / "etc"
    if not src.is_dir() and project.is_dir():
        src = project / "src"
    label = str(project) if project.is_dir() else "unknown"
    return etc, src, label


def _collect_node_words(node, out: set[str]) -> None:
    if node.name and _is_keyword(node.name):
        out.add(node.name)
    if node.node_type in ("word", "compound") and isinstance(node.value, str):
        for tok in node.value.split():
            if _is_keyword(tok):
                out.add(tok)
    for child in node.children:
        _collect_node_words(child, out)


def scan_casedicts(
    etc_dir: Path,
    progress: Callable[[str], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> set[str]:
    """Parse $FOAM_ETC/caseDicts/ and collect word/compound token values."""
    from foam.parser import OpenFoamParser  # local import — foam pkg may not be on path early

    casedicts = etc_dir / "caseDicts"
    if not casedicts.is_dir():
        if progress:
            progress(f"  [skip] {casedicts} not found")
        return set()

    words: set[str] = set()
    files = sorted(f for f in casedicts.rglob("*") if f.is_file())
    for i, path in enumerate(files):
        if cancelled and cancelled():
            break
        try:
            root = OpenFoamParser(path.read_text(errors="replace")).parse()
            _collect_node_words(root, words)
        except Exception:
            pass
        if progress and (i % 20 == 0 or i == len(files) - 1):
            progress(f"  caseDicts: {i + 1}/{len(files)} files, {len(words)} tokens so far")
    return words


def scan_src_typenames(
    src_dir: Path,
    progress: Callable[[str], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> set[str]:
    """Grep $FOAM_SRC/**/*.H for TypeName / ClassName macro registrations."""
    if not src_dir.is_dir():
        if progress:
            progress(f"  [skip] {src_dir} not found")
        return set()

    words: set[str] = set()
    headers = sorted(src_dir.rglob("*.H"))
    for i, path in enumerate(headers):
        if cancelled and cancelled():
            break
        try:
            text = path.read_text(errors="replace")
            for pattern in (_TYPENAME_RE, _CLASSNAME_RE):
                for m in pattern.finditer(text):
                    tok = m.group(1)
                    if _is_keyword(tok):
                        words.add(tok)
        except Exception:
            pass
        if progress and (i % 500 == 0 or i == len(headers) - 1):
            progress(f"  src headers: {i + 1}/{len(headers)} files, {len(words)} tokens so far")
    return words


def scan_src_named_registrations(
    src_dir: Path,
    progress: Callable[[str], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> set[str]:
    """Grep $FOAM_SRC/**/*.C for addNamedTo*() custom lookup-name identifiers."""
    if not src_dir.is_dir():
        if progress:
            progress(f"  [skip] {src_dir} not found")
        return set()

    words: set[str] = set()
    impls = sorted(src_dir.rglob("*.C"))
    for i, path in enumerate(impls):
        if cancelled and cancelled():
            break
        try:
            text = path.read_text(errors="replace")
            for pattern in (_NAMED_RTST_RE, _NAMED_MFST_RE):
                for m in pattern.finditer(text):
                    tok = m.group(1)
                    if _is_keyword(tok):
                        words.add(tok)
        except Exception:
            pass
        if progress and (i % 500 == 0 or i == len(impls) - 1):
            progress(f"  src impls: {i + 1}/{len(impls)} files, {len(words)} tokens so far")
    return words


def generate(
    progress: Callable[[str], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> tuple[int, Path]:
    """Run the full scan and write foam_keywords.json.

    Returns (keyword_count, output_path).
    Raises RuntimeError if nothing was collected (OpenFOAM not found).
    """
    etc, src, label = _foam_dirs()

    words: set[str] = set()

    if etc.is_dir():
        if progress:
            progress(f"Scanning caseDicts in {etc} …")
        words |= scan_casedicts(etc, progress=progress, cancelled=cancelled)
    else:
        if progress:
            progress("WM_PROJECT_DIR / FOAM_ETC not set — skipping caseDicts")

    if cancelled and cancelled():
        raise RuntimeError("Cancelled")

    if src.is_dir():
        if progress:
            progress(f"Scanning TypeName/ClassName macros in {src} …")
        words |= scan_src_typenames(src, progress=progress, cancelled=cancelled)
    else:
        if progress:
            progress("FOAM_SRC not found — skipping source scan")

    if cancelled and cancelled():
        raise RuntimeError("Cancelled")

    if src.is_dir():
        if progress:
            progress(f"Scanning named registrations in {src} …")
        words |= scan_src_named_registrations(src, progress=progress, cancelled=cancelled)

    if cancelled and cancelled():
        raise RuntimeError("Cancelled")

    if not words:
        raise RuntimeError(
            "No keywords collected.\n"
            "Source your OpenFOAM environment first:\n"
            "  source /opt/openfoam*/etc/bashrc"
        )

    payload = {"keywords": sorted(words), "source": label}
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n")
    return len(words), OUTPUT
