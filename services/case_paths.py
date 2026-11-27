# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Where FoDE may write: the one containment test, by operation.

A case can come from someone else, and it can hold symlinks or ``..``
paths that lead out of it. Text comparisons (``Path.relative_to``) cannot
see either, so every check here resolves the path on disk first
(``os.path.realpath(strict=True)``: every symlink followed, ``..`` collapsed)
and compares the result with the resolved case directory, component by
component. A path that cannot be resolved -- missing where it must exist, a
link loop, no permission -- is refused.

FoDE still *reads* outside files (a linked dictionary, an ``#include``
into the installation): showing the user their own data is not the risk.
These checks guard writes, and each operation has its own:

* :func:`editable` -- overwrite an existing file's contents;
  :func:`writable` adds re-creating one deleted on disk (Save).
* :func:`creatable` -- create a new file (New File, Backup, Duplicate,
  Copy into Case); the caller then opens it with exclusive create.
* :func:`removable` -- unlink one directory entry (Delete File, Clean
  Backups); ``os.unlink`` never follows a final symlink, so only the
  containing directory needs resolving.
* :func:`removable_tree` -- ``rmtree`` a directory (Delete Directory).
* :func:`copy_destination_problem` -- where Duplicate Case / Save As may
  put the new case.
* :func:`conflicting_writes` -- two unsaved buffers that are one file on disk.

The open case's root is pinned (:func:`pin_case_root`): if its path comes to
name another directory, every check refuses.

The guarantee covers paths as they stand when FoDE checks them. Entries
changed between the check and the write, and hard links, are outside it --
see DEVELOPER.md's "Writes stay inside the case".
"""
from __future__ import annotations

import os
import stat
from collections.abc import Mapping
from pathlib import Path


def real_path(path: str | os.PathLike[str]) -> Path | None:
    """*path* fully resolved, or None when it cannot be (missing, a loop)."""
    try:
        return Path(os.path.realpath(path, strict=True))
    except (OSError, RuntimeError, ValueError):
        return None


# The open case as it was when opened: (the path as given, where it resolved,
# device, inode). One case is open at a time, so one pin.
_pinned: tuple[str, Path | None, int, int] | None = None


def _pin_key(case_dir: str | os.PathLike[str]) -> str:
    return os.path.abspath(os.fspath(case_dir))


def pin_case_root(case_dir: str | os.PathLike[str] | None) -> None:
    """Remember which directory *case_dir* names now; None forgets it.

    FoDE keeps the path a case was opened by and resolves it at every write.
    If that path comes to name another directory -- the folder renamed and a
    new one put in its place, a link retargeted -- the buffers in memory
    belong to the old one and must not be written into the new. With the
    root pinned, every check in this module refuses until the case is
    opened again (which pins it afresh).
    """
    global _pinned
    _pinned = None
    if case_dir is None:
        return
    key = _pin_key(case_dir)
    # A root that cannot be identified is pinned as such: refusing until the
    # case is opened again, not writing unpinned if the path appears later.
    _pinned = (key, None, 0, 0)
    root = real_path(case_dir)
    if root is None:
        return
    try:
        st = os.stat(root)
    except OSError:
        return
    _pinned = (key, root, st.st_dev, st.st_ino)


def case_root_changed(case_dir: str | os.PathLike[str]) -> bool:
    """True when *case_dir* is the pinned case and no longer the directory it was."""
    pin = _pinned
    if pin is None or _pin_key(case_dir) != pin[0]:
        return False
    root = real_path(case_dir)
    if pin[1] is None or root is None or root != pin[1]:
        return True
    try:
        st = os.stat(root)
    except OSError:
        return True
    return (st.st_dev, st.st_ino) != pin[2:]


def _root(case_dir: str | os.PathLike[str]) -> Path | None:
    """The resolved case root, or None when it cannot be resolved or has changed."""
    if case_root_changed(case_dir):
        return None
    return real_path(case_dir)


def _within(path: Path, root: Path) -> bool:
    return path == root or path.is_relative_to(root)


def resolves_inside(path: str | os.PathLike[str], case_dir: str | os.PathLike[str]) -> bool:
    """True when *path* exists and resolves to *case_dir* or below it."""
    root = _root(case_dir)
    target = real_path(path)
    return root is not None and target is not None and _within(target, root)


def editable(path: str | os.PathLike[str], case_dir: str | os.PathLike[str]) -> bool:
    """True when *path* is a regular file whose real location is inside the case.

    The test for writing over an existing file. A symlink to a file outside,
    a file under a linked directory, and an ``#include "../.."`` that climbs
    out all fail it.
    """
    root = _root(case_dir)
    target = real_path(path)
    if root is None or target is None or not _within(target, root):
        return False
    try:
        return stat.S_ISREG(os.stat(target).st_mode)
    except OSError:
        return False


def writable(path: str | os.PathLike[str], case_dir: str | os.PathLike[str]) -> bool:
    """True when Save may write *path*: an :func:`editable` file, or -- a file
    deleted on disk while its buffer was open -- a :func:`creatable` name."""
    return editable(path, case_dir) or creatable(path, case_dir)


def creatable(path: str | os.PathLike[str], case_dir: str | os.PathLike[str]) -> bool:
    """True when a new file may be created at *path*.

    Nothing may exist at the name -- not even a dangling symlink, which an
    ordinary ``open(path, "w")`` would follow -- and the nearest existing
    ancestor must be a directory inside the case. Missing directories in
    between are allowed: the caller creates them, then the file with
    exclusive create. A ``..`` component is refused outright rather than
    resolved, since it would be resolved after a symlink it follows.
    """
    p = Path(path)
    if ".." in p.parts or os.path.lexists(p):
        return False
    root = _root(case_dir)
    if root is None:
        return False
    ancestor = p.parent
    while not os.path.lexists(ancestor):
        if ancestor.parent == ancestor:
            return False
        ancestor = ancestor.parent
    real = real_path(ancestor)
    return real is not None and real.is_dir() and _within(real, root)


def removable(path: str | os.PathLike[str], case_dir: str | os.PathLike[str]) -> bool:
    """True when the directory entry *path* may be unlinked.

    ``os.unlink`` removes the entry itself, a symlink included, never what it
    points to; so what must be inside the case is the directory holding the
    entry. A directory entry is refused -- that is :func:`removable_tree`'s.
    """
    p = Path(path)
    try:
        st = os.lstat(p)
    except OSError:
        return False
    if stat.S_ISDIR(st.st_mode):
        return False
    root = _root(case_dir)
    parent = real_path(p.parent)
    return root is not None and parent is not None and _within(parent, root)


def removable_tree(path: str | os.PathLike[str], case_dir: str | os.PathLike[str]) -> bool:
    """True when *path* is a real directory (not a link to one) below the case root."""
    p = Path(path)
    try:
        st = os.lstat(p)
    except OSError:
        return False
    if not stat.S_ISDIR(st.st_mode):
        return False
    root = _root(case_dir)
    real = real_path(p)
    return root is not None and real is not None and real != root and _within(real, root)


def file_identity(path: str | os.PathLike[str]) -> object:
    """A key equal for two paths exactly when they are one file on disk.

    Device and inode for a path that exists -- resolved text misses letter
    case on a case-insensitive filesystem, Unicode normalisation and hard
    links -- and the path with ``.``/``..`` folded for one that does not.
    """
    try:
        st = os.stat(path)
    except (OSError, ValueError):
        return os.path.normpath(os.fspath(path))
    return (st.st_dev, st.st_ino)


def conflicting_writes(texts: Mapping[str, str]) -> set[str]:
    """Those of *texts*' paths that share a real file with another path holding different text.

    Two listed names can be one file (a link inside the case to another case
    file; two spellings of an include). Written one after the other, the
    last buffer would silently win, so neither is written and the user
    settles it. Names holding the same text are no conflict.
    """
    by_file: dict[object, list[str]] = {}
    for path in texts:
        by_file.setdefault(file_identity(path), []).append(path)
    return {
        path
        for group in by_file.values()
        if len({texts[p] for p in group}) > 1
        for path in group
    }


# Codes for copy_destination_problem; ui/mixins/_case_ops.py words them.
DEST_IS_SOURCE = "same"
DEST_INSIDE_SOURCE = "inside"
DEST_CONTAINS_SOURCE = "contains"
DEST_IS_LINK = "link"
DEST_PARENT_MISSING = "parent"
SOURCE_UNRESOLVABLE = "source"


def copy_destination_problem(
    source: str | os.PathLike[str], dest: str | os.PathLike[str]
) -> str | None:
    """Why *dest* cannot receive a copy of the case *source*, or None.

    Checked before anything is removed: an existing destination is offered
    for overwrite, and overwriting means ``rmtree``. So the destination must
    not be the source, nor inside it, nor contain it -- through any alias --
    and it must not be a symlink (live or dangling), which the overwrite
    would remove or the copy would follow.
    """
    src = _root(source)
    if src is None or not src.is_dir():
        return SOURCE_UNRESOLVABLE
    d = Path(dest)
    if d.is_symlink():
        return DEST_IS_LINK
    parent = real_path(d.parent)
    if parent is None or not parent.is_dir():
        return DEST_PARENT_MISSING
    # The parent resolved; the last component is a plain name or a real directory.
    real_dest = real_path(d) if os.path.lexists(d) else parent / d.name
    if real_dest is None:
        return DEST_IS_LINK
    if real_dest == src:
        return DEST_IS_SOURCE
    if _within(real_dest, src):
        return DEST_INSIDE_SOURCE
    if _within(src, real_dest):
        return DEST_CONTAINS_SOURCE
    return _identity_overlap(src, real_dest)


def _same_entry(a: Path, b: Path) -> bool:
    try:
        return os.path.samefile(a, b)
    except OSError:
        return False


def _identity_overlap(src: Path, dest: Path) -> str | None:
    """The overlap the text comparison cannot see, or None.

    Two spellings can name one directory with no symlink involved: letter
    case on a case-insensitive filesystem (macOS, Windows), Unicode
    normalisation, a second mount of the same tree. ``realpath`` keeps the
    spelling it was given, so *dest* and its ancestors are also compared with
    *src* and its ancestors by device and inode.
    """
    if os.path.lexists(dest):
        if _same_entry(dest, src):
            return DEST_IS_SOURCE
        if any(_same_entry(dest, ancestor) for ancestor in src.parents):
            return DEST_CONTAINS_SOURCE
    if any(_same_entry(ancestor, src) for ancestor in dest.parents):
        return DEST_INSIDE_SOURCE
    return None
