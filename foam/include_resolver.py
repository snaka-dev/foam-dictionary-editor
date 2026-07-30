# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Resolve an ``#include``-family directive to the file it pulls in.

``foam/parser.py`` turns every ``#word`` line into an opaque ``directive_entry``
node whose ``value`` is the raw source text (``'#include "initialConditions"'``,
``'#includeFunc mag(U)'``). This module is the first per-directive knowledge in
the codebase: it re-reads that text, and resolves the referenced file.

Two steps, deliberately separate:

``parse_include_directive``
    text -> ``IncludeRef``, or None when the directive is not an include.
``resolve_include``
    ``IncludeRef`` + the including file's location -> ``ResolvedInclude``.

The module stays Qt-free and stdlib-only, and does no installation discovery of
its own -- ``etc_dirs`` is a parameter, supplied by ``services/include_scan.py``.
That keeps the ``etc`` search path (which needs ``app_config``/``services``) out
of ``foam/``. See DEVELOPER.md's "Include resolution" section.
"""
from __future__ import annotations

import dataclasses
import os
import re
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Literal

from foam.utils import resolve_optionally_gzipped

IncludeKind = Literal["include", "sinclude", "includeIfPresent", "includeEtc", "includeFunc"]

IncludeStatus = Literal["resolved", "missing", "missing_optional", "no_installation"]

# Directives whose argument is a file path resolved against the case, as opposed
# to the two that reach into the OpenFOAM installation.
_CASE_PATH_KINDS: frozenset[str] = frozenset({"include", "sinclude", "includeIfPresent"})

# `#sinclude` and `#includeIfPresent` are synonyms: a missing target is legal.
_OPTIONAL_KINDS: frozenset[str] = frozenset({"sinclude", "includeIfPresent"})

# `\b` alone separates `#include` from `#includeEtc` (there is no word boundary
# between "e" and "E"), so the alternation needs no careful ordering.
_DIRECTIVE_RE = re.compile(
    r"^[ \t]*#(s?include|includeIfPresent|includeEtc|includeFunc)\b[ \t]*(.*)$"
)

# C++ sources included inside a `#codeStream`/`code` body are not dictionaries
# and must never reach the file list. Measured against the OpenFOAM v2512
# tutorials, every such include ends in one of these suffixes (createTime.H,
# argList.H, fvCFD.H, setRootCase.H, ...) and no dictionary include does.
_CPP_SUFFIXES: frozenset[str] = frozenset({".H", ".h", ".C", ".cc", ".cpp", ".hpp", ".hxx"})

# `#include <fvCFD.H>`. Anchored at both ends so the OpenFOAM path tokens
# (`<constant>/caseSettings`), which carry a path after the `>`, are unaffected.
_ANGLE_BRACKET_RE = re.compile(r"^<[^<>]*>$")

# Leading path tokens OpenFOAM's fileName::expand() understands. `<etc>` is
# handled separately, since it expands to one candidate per etc root.
_CASE_TOKENS: dict[str, tuple[str, ...]] = {
    "<case>": (),
    "<system>": ("system",),
    "<constant>": ("constant",),
}

_ETC_TOKEN = "<etc>"

# `#includeFunc` looks here, below each etc root, for a named function object.
_POST_PROCESSING_SUBDIR = ("caseDicts", "postProcessing")


@dataclasses.dataclass(frozen=True)
class IncludeRef:
    """One parsed ``#include``-family directive."""

    kind: IncludeKind
    arg: str        # argument as written, minus quotes/`;`/comment: 'mag(U)'
    target: str     # what to look for: 'mag' -- `arg` without a #includeFunc call
    optional: bool  # a missing target is legal (`#sinclude`, `#includeIfPresent`)


@dataclasses.dataclass(frozen=True)
class ResolvedInclude:
    """The outcome of resolving an ``IncludeRef`` against a case."""

    ref: IncludeRef
    source_file: Path
    path: Path | None  # the on-disk file; None when unresolved
    status: IncludeStatus

    @property
    def resolved(self) -> bool:
        return self.path is not None


def parse_include_directive(text: str) -> IncludeRef | None:
    """Parse a directive's source text into an ``IncludeRef``.

    Returns None for anything that is not an include the app can follow --
    a different directive (``#eval``, ``#codeStream``, ``#remove``), an empty
    argument, or a C++ header pulled in by a ``#codeStream`` body.
    """
    match = _DIRECTIVE_RE.match(text.strip())
    if not match:
        return None

    kind = match.group(1)
    arg = _strip_argument(match.group(2))
    if not arg:
        return None

    if kind in _CASE_PATH_KINDS and _looks_like_cpp_include(arg):
        return None

    # `#includeFunc mag(U)` names the file `mag`; the arguments are the function
    # object's, not part of the path.
    target = arg.split("(", 1)[0].strip() if kind == "includeFunc" else arg
    if not target:
        return None

    return IncludeRef(
        kind=kind,  # type: ignore[arg-type]  # constrained by _DIRECTIVE_RE
        arg=arg,
        target=target,
        optional=kind in _OPTIONAL_KINDS,
    )


def _strip_argument(raw: str) -> str:
    """Strip a trailing comment, `;`, whitespace, and one layer of quotes."""
    arg = raw.split("//", 1)[0].strip()
    arg = arg.rstrip(";").strip()
    if len(arg) >= 2 and arg[0] == arg[-1] and arg[0] in "\"'":
        arg = arg[1:-1].strip()
    return arg


def _looks_like_cpp_include(arg: str) -> bool:
    """Return True for a C++ source pulled in by a ``#codeStream`` body."""
    return bool(_ANGLE_BRACKET_RE.match(arg)) or Path(arg).suffix in _CPP_SUFFIXES


def include_candidates(
    ref: IncludeRef,
    *,
    source_file: Path,
    case_dir: Path,
    etc_dirs: Sequence[Path] = (),
) -> list[Path]:
    """Return the paths OpenFOAM would try, in order, for this reference.

    Public so tooltips and tests can show *why* a reference did not resolve.
    """
    if ref.kind == "includeEtc":
        return [root / ref.target for root in etc_dirs]

    if ref.kind == "includeFunc":
        # A case-local system/<name> wins, which is what makes "Copy into case"
        # an override that needs no edit to the directive.
        candidates = [case_dir / "system" / ref.target]
        for root in etc_dirs:
            found = _post_processing_index(root).get(ref.target)
            if found is not None:
                candidates.append(found)
        return candidates

    expanded = _expand(ref.target, case_dir=case_dir, etc_dirs=etc_dirs)
    if expanded:
        return expanded
    # Relative to the including file first, then the case -- one rule that
    # covers `0/U` + "include/initialConditions" and
    # `system/snappyHexMeshDict` + "meshQualityDict" alike.
    return [source_file.parent / ref.target, case_dir / ref.target]


def resolve_include(
    ref: IncludeRef,
    *,
    source_file: Path,
    case_dir: Path,
    etc_dirs: Sequence[Path] = (),
) -> ResolvedInclude:
    """Resolve a reference to an on-disk file, transparent to gzip.

    Always returns a ``ResolvedInclude``; ``path is None`` means unresolved and
    ``status`` says why. An optional reference that is simply absent reports
    ``missing_optional``, which is legal OpenFOAM and never an error.
    """
    for candidate in include_candidates(
        ref, source_file=source_file, case_dir=case_dir, etc_dirs=etc_dirs
    ):
        found = resolve_optionally_gzipped(candidate)
        if found is not None:
            return ResolvedInclude(ref, source_file, found, "resolved")

    if ref.optional:
        status: IncludeStatus = "missing_optional"
    elif ref.kind in {"includeEtc", "includeFunc"} and not etc_dirs:
        # Distinct from "missing" so the UI can point at the installation
        # picker rather than claim the file does not exist.
        status = "no_installation"
    else:
        status = "missing"
    return ResolvedInclude(ref, source_file, None, status)


def _expand(target: str, *, case_dir: Path, etc_dirs: Sequence[Path]) -> list[Path]:
    """Expand env vars and a leading OpenFOAM path token.

    Returns [] when the target needs the per-kind relative rules instead. An
    unset environment variable stays literal and simply fails to resolve --
    running FoDE without a sourced OpenFOAM environment is not an error.
    """
    expanded = os.path.expandvars(target)

    head, sep, rest = expanded.partition("/")
    if head == _ETC_TOKEN:
        return [root / rest for root in etc_dirs] if sep else list(etc_dirs)
    if head in _CASE_TOKENS:
        base = case_dir.joinpath(*_CASE_TOKENS[head])
        return [base / rest if sep else base]

    path = Path(expanded)
    return [path] if path.is_absolute() else []


@lru_cache(maxsize=8)
def _post_processing_index(etc_root: Path) -> dict[str, Path]:
    """Map function-object name -> path under ``<etc>/caseDicts/postProcessing``.

    Cached per root: the tree has a few hundred entries and never changes
    while the app runs.
    """
    base = etc_root.joinpath(*_POST_PROCESSING_SUBDIR)
    if not base.is_dir():
        return {}
    index: dict[str, Path] = {}
    for path in sorted(base.rglob("*")):
        if path.is_file():
            index.setdefault(path.name, path)
    return index


def clear_post_processing_cache() -> None:
    """Drop the ``#includeFunc`` name index (for tests, and installation changes)."""
    _post_processing_index.cache_clear()
