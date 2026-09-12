# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Splice ``#include``d entries into a copy of a dictionary tree.

A case can keep every dimension in one file and have each dictionary pull it in
with ``#include``. ``foam/parser.py`` keeps the directive opaque and
``services/include_scan.py`` only resolves it to a path for the file list, so
the including file's own tree holds none of those definitions --
``var_resolver.build_var_map`` sees an empty scope and every ``$var`` geometry
silently fails to resolve.

This module builds the tree the *extractors* need: a merged, *read-only* view in
which each resolvable include directive is replaced by the entries of the file
it names, in document order (OpenFOAM inserts them textually, so a later
definition shadows an earlier one).

**The merged tree is for reading only.** The tree view, editor, writer and every
save path keep working on the original unmerged root, which this module never
mutates -- see DEVELOPER.md's "Include resolution" section.

Qt-free and no dependency on ``services``: ``etc_dirs`` arrives as a parameter,
the same rule ``foam/include_resolver.py`` already follows.
"""
from __future__ import annotations

import copy
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from foam.include_resolver import parse_include_directive, resolve_include
from foam.nodes import FoamNode
from foam.parser import OpenFoamParser
from foam.utils import read_foam_file

# How many include levels to follow. Expansion is transitive (unlike the file
# list's one-level scan), so this plus the per-branch visited set is what keeps
# a mutually-referential pair from recursing forever.
DEFAULT_MAX_DEPTH = 8

# path -> (mtime, size, parsed root). Extraction re-runs on every tree edit, so
# an included file must not be re-read and re-parsed per keystroke. Same
# (mtime, size) memo style as services/include_scan.py.
_parse_cache: dict[str, tuple[float, int, FoamNode]] = {}


def clear_expand_cache() -> None:
    """Drop the parsed-include memo (on a case switch, and in tests)."""
    _parse_cache.clear()


@dataclass(frozen=True)
class ExpandedTree:
    """The result of expanding one dictionary's includes.

    ``root`` is the merged view -- the *original* object when nothing expanded,
    so the common no-include case allocates nothing.
    """

    root: FoamNode
    # Absolute paths whose content was spliced in. The caller uses this to know
    # which files the viewer now depends on, so editing one can refresh it.
    sources: frozenset[str] = frozenset()
    # Directive texts that could not be expanded, for reporting. A failure is a
    # non-event: the directive_entry stays exactly where it was.
    unresolved: tuple[str, ...] = ()

    @property
    def expanded(self) -> bool:
        return bool(self.sources)


@dataclass
class _Ctx:
    """Everything constant across one expand_includes() call."""

    case_dir: Path
    etc_dirs: Sequence[Path]
    read_text: Callable[[Path], str | None] | None
    sources: set[str] = field(default_factory=set)
    unresolved: list[str] = field(default_factory=list)


def expand_includes(
    root: FoamNode,
    *,
    source_file: Path,
    case_dir: Path,
    etc_dirs: Sequence[Path] = (),
    read_text: Callable[[Path], str | None] | None = None,
    max_depth: int = DEFAULT_MAX_DEPTH,
) -> ExpandedTree:
    """Return a read-only copy of *root* with its includes spliced in.

    ``read_text`` lets a caller serve an unsaved editor buffer instead of the
    file on disk, so a change to an included file shows up before it is saved;
    returning None from it falls back to reading the file.

    ``#includeFunc`` is deliberately *not* expanded: its targets are already
    resolved into the file list and rendered on their own, so splicing them
    too would duplicate the geometry.
    """
    ctx = _Ctx(case_dir=case_dir, etc_dirs=etc_dirs, read_text=read_text)
    merged, _ = _expand_node(
        root, ctx, source_file=source_file, depth=max_depth, seen=frozenset({_key(source_file)})
    )
    return ExpandedTree(
        root=merged,
        sources=frozenset(ctx.sources),
        unresolved=tuple(ctx.unresolved),
    )


def _key(path: Path) -> str:
    """Identity for the cycle guard: the real path, so a symlink alias matches."""
    try:
        return str(path.resolve())
    except OSError:
        return str(path)


def _expand_node(
    node: FoamNode,
    ctx: _Ctx,
    *,
    source_file: Path,
    depth: int,
    seen: frozenset[str],
) -> tuple[FoamNode, bool]:
    """Expand within one node. Returns (node, changed).

    Copy-on-write: a subtree holding no expandable include is returned as-is and
    shared with the original tree, so only the path from the root down to a
    splice is rebuilt.
    """
    new_children: list[FoamNode] = []
    changed = False

    for child in node.children:
        if child.node_type == "directive_entry":
            spliced = _splice(child, ctx, source_file=source_file, depth=depth, seen=seen)
            if spliced is not None:
                new_children.extend(spliced)
                changed = True
                continue
        expanded, child_changed = _expand_node(
            child, ctx, source_file=source_file, depth=depth, seen=seen
        )
        new_children.append(expanded)
        changed = changed or child_changed

    if not changed:
        return node, False

    merged = copy.copy(node)
    merged.children = new_children
    return merged, True


def _splice(
    directive: FoamNode,
    ctx: _Ctx,
    *,
    source_file: Path,
    depth: int,
    seen: frozenset[str],
) -> list[FoamNode] | None:
    """Return the entries *directive* pulls in, or None to leave it in place."""
    if depth <= 0:
        return None
    ref = parse_include_directive(str(directive.value))
    # #includeFunc names a function object, not a parameter file; its target is
    # already listed and rendered standalone.
    if ref is None or ref.kind == "includeFunc":
        return None

    resolved = resolve_include(
        ref, source_file=source_file, case_dir=ctx.case_dir, etc_dirs=ctx.etc_dirs
    )
    if resolved.path is None:
        # An optional include whose target is absent is legal OpenFOAM, not a
        # problem to report.
        if not ref.optional:
            ctx.unresolved.append(str(directive.value))
        return None

    target = resolved.path
    if _key(target) in seen:
        # A cycle, not a failure of resolution -- report it so the caller can
        # say why the entries are missing.
        ctx.unresolved.append(str(directive.value))
        return None

    included = _parse_target(target, ctx)
    if included is None:
        ctx.unresolved.append(str(directive.value))
        return None

    ctx.sources.add(str(target))
    expanded, _ = _expand_node(
        included, ctx, source_file=target, depth=depth - 1, seen=seen | {_key(target)}
    )
    # A shallow copy per spliced entry: the memo hands out the same node objects
    # on every call, and the merged tree must not re-parent them. Nothing below
    # reads `parent` -- no extractor walks upward -- so the grandchildren are
    # shared untouched.
    return [copy.copy(child) for child in expanded.children if child.name != "FoamFile"]


def _parse_target(path: Path, ctx: _Ctx) -> FoamNode | None:
    """Parse an included file, memoised on (mtime, size). None if unusable."""
    if ctx.read_text is not None:
        text = ctx.read_text(path)
        if text is not None:
            # Buffer content is not on disk, so it cannot be keyed on stat; it is
            # one small file and only while it is dirty.
            return _parse_text(text)

    path_str = str(path)
    try:
        stat = path.stat()
    except OSError:
        return None

    cached = _parse_cache.get(path_str)
    if cached is not None and cached[0] == stat.st_mtime and cached[1] == stat.st_size:
        return cached[2]

    try:
        text = read_foam_file(path_str)
    except OSError:
        return None
    parsed = _parse_text(text)
    if parsed is None:
        return None
    _parse_cache[path_str] = (stat.st_mtime, stat.st_size, parsed)
    return parsed


def _parse_text(text: str) -> FoamNode | None:
    try:
        return OpenFoamParser(text).parse()
    except Exception:
        # A file that will not parse is left to the directive it came from; the
        # viewer degrades to the unexpanded tree rather than erroring.
        return None
