# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Scan an OpenFOAM installation to build app_config/foam_keywords.json.

Shared by tools/generate_foam_keywords.py (CLI) and the Settings menu action.
The output file is the user-local override; the repository ships a baseline as
app_config/foam_keywords.default.json (see DEVELOPER.md).
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import date
from pathlib import Path

from app_config.foam_env import foam_env_dirs
from app_config.json_io import atomic_write_text

OUTPUT = Path(__file__).parent / "foam_keywords.json"

# License/provenance note embedded in the generated JSON. The file contains
# identifier names only (no source code); names are recorded here so the
# origin of the shipped default list stays auditable.
_NOTE = (
    "Keyword identifier names mechanically extracted from an OpenFOAM "
    "installation for syntax highlighting. This file contains keyword names "
    "only, no source code. OpenFOAM is a registered trademark of OpenCFD "
    "Ltd.; OpenFOAM sources are Copyright OpenCFD Ltd. and licensed GPL-3.0."
)

_IDENTIFIER_RE = re.compile(r"^[A-Za-z]\w+$")
_TYPENAME_RE = re.compile(r'TypeName\s*\(\s*"(\w+)"')
_CLASSNAME_RE = re.compile(r'ClassName\s*\(\s*"(\w+)"')
_NAMED_RTST_RE = re.compile(
    r'addNamedToRunTimeSelectionTable\s*\(\s*\w+\s*,\s*\w+\s*,\s*\w+\s*,\s*(\w+)\s*\)'
)
_NAMED_MFST_RE = re.compile(
    r'addNamedToMemberFunctionSelectionTable\s*\(\s*\w+\s*,\s*\w+\s*,\s*\w+\s*,\s*\w+\s*,\s*(\w+)\s*\)'
)
# Dictionary-read calls: dict.lookup("kw"), dict.get<scalar>("kw"),
# readEntry("kw", ...), found("kw"), ... — these name real dictionary keywords
# (e.g. controlDict's "application"/"writePrecision") that never appear in
# caseDicts templates or TypeName macros.
_LOOKUP_RE = re.compile(
    r'\b(?:lookup|lookupOrDefault|get|getOrDefault|getCheck|readEntry|readIfPresent|found)'
    r'\s*(?:<[^<>]*>)?\s*\(\s*"(?P<kw>[A-Za-z]\w+)"'
)


def _is_keyword(tok: str) -> bool:
    return bool(_IDENTIFIER_RE.match(tok))


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


def scan_src_lookup_keywords(
    root_dir: Path,
    progress: Callable[[str], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> set[str]:
    """Grep root_dir/**/*.{C,H} for dictionary-read calls (see _LOOKUP_RE)."""
    if not root_dir.is_dir():
        if progress:
            progress(f"  [skip] {root_dir} not found")
        return set()

    words: set[str] = set()
    files = sorted(f for f in root_dir.rglob("*") if f.suffix in (".C", ".H"))
    for i, path in enumerate(files):
        if cancelled and cancelled():
            break
        try:
            text = path.read_text(errors="replace")
            for m in _LOOKUP_RE.finditer(text):
                tok = m.group("kw")
                if _is_keyword(tok):
                    words.add(tok)
        except Exception:
            pass
        if progress and (i % 500 == 0 or i == len(files) - 1):
            progress(
                f"  {root_dir.name} lookups: {i + 1}/{len(files)} files, "
                f"{len(words)} tokens so far"
            )
    return words


def generate(
    progress: Callable[[str], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
    project_dir: Path | None = None,
) -> tuple[int, Path]:
    """Run the full scan and write foam_keywords.json.

    When ``project_dir`` is given, etc/src/applications are derived from that
    installation root; otherwise the sourced environment (WM_PROJECT_DIR,
    FOAM_ETC, FOAM_SRC, FOAM_APP) is used.

    Returns (keyword_count, output_path).
    Raises RuntimeError if nothing was collected (OpenFOAM not found).
    """
    etc: Path | None
    src: Path | None
    apps: Path | None
    if project_dir is not None:
        root = project_dir

        def _sub(name: str) -> Path | None:
            path = root / name
            return path if path.is_dir() else None

        etc, src, apps = _sub("etc"), _sub("src"), _sub("applications")
        label = str(project_dir)
        version = project_dir.name
    else:
        dirs = foam_env_dirs()
        etc, src, apps = dirs.etc_dir, dirs.src_dir, dirs.apps_dir
        label = str(dirs.project_dir) if dirs.project_dir is not None else "unknown"
        version = dirs.version or "unknown"

    words: set[str] = set()

    if etc is not None:
        if progress:
            progress(f"Scanning caseDicts in {etc} …")
        words |= scan_casedicts(etc, progress=progress, cancelled=cancelled)
    else:
        if progress:
            progress("WM_PROJECT_DIR / FOAM_ETC not set — skipping caseDicts")

    if cancelled and cancelled():
        raise RuntimeError("Cancelled")

    if src is not None:
        if progress:
            progress(f"Scanning TypeName/ClassName macros in {src} …")
        words |= scan_src_typenames(src, progress=progress, cancelled=cancelled)
    else:
        if progress:
            progress("FOAM_SRC not found — skipping source scan")

    if cancelled and cancelled():
        raise RuntimeError("Cancelled")

    if src is not None:
        if progress:
            progress(f"Scanning named registrations in {src} …")
        words |= scan_src_named_registrations(src, progress=progress, cancelled=cancelled)

    if cancelled and cancelled():
        raise RuntimeError("Cancelled")

    for lookup_dir in (src, apps):
        if lookup_dir is not None:
            if progress:
                progress(f"Scanning dictionary-read calls in {lookup_dir} …")
            words |= scan_src_lookup_keywords(
                lookup_dir, progress=progress, cancelled=cancelled
            )
        if cancelled and cancelled():
            raise RuntimeError("Cancelled")

    if not words:
        raise RuntimeError(
            "No keywords collected.\n"
            "Choose an installation directory, or source your OpenFOAM "
            "environment first:\n"
            "  source /opt/openfoam*/etc/bashrc"
        )

    payload = {
        "note": _NOTE,
        "source": label,
        "version": version,
        "generated": date.today().isoformat(),
        "keywords": sorted(words),
    }
    atomic_write_text(OUTPUT, json.dumps(payload, indent=2) + "\n")
    return len(words), OUTPUT
