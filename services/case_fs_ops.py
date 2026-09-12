# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Filesystem safety checks and operations for the Case Browser.

Pure stdlib, no Qt. This module deliberately returns *reason codes* (:class:`Refusal`)
rather than user-facing prose: ``tests/test_i18n.py`` only AST-scans ``ui/`` for
``tr()`` coverage, so any message string manufactured down here would be an untranslated
hole invisible to that guard. The UI layer owns mapping a :class:`Refusal` to translated
text.

Every ``check_*`` function is a pure precondition test -- it never mutates the
filesystem, only reads it (``exists``/``resolve``/``stat``/``samefile``). Every
``perform_*`` function is the actual mutation and does not re-run the checks; callers
are expected to call the matching ``check_*`` first and only proceed on ``.ok``.
``perform_*`` still carries a few defensive backstops of its own (see
``perform_move``'s handling of an existing, non-same-file destination) because the
most important invariant here -- never hand an existing directory to ``shutil.move``
-- is cheap to enforce twice and expensive to get wrong once.

A true cross-filesystem (EXDEV) move cannot be exercised in-process (it needs two real
mounts); it is covered here only by stubbing ``os.stat`` to report differing
``st_dev`` values, per CASE_BROWSER_PLAN.md's "Flagged" section.
"""
from __future__ import annotations

import os
import shutil
from collections.abc import Callable, Collection, Iterator
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path

_PROGRESS_EVERY = 20


class Refusal(Enum):
    """Why a filesystem operation was refused. No message text lives here on purpose."""

    DESTINATION_EXISTS = auto()
    INTO_OWN_SUBTREE = auto()
    SAME_PATH = auto()
    NOT_A_DIRECTORY = auto()
    SOURCE_MISSING = auto()
    PROTECTED_PATH = auto()
    NAME_HAS_SEPARATOR = auto()
    NAME_EMPTY = auto()
    ESCAPES_PARENT = auto()
    PERMISSION = auto()


@dataclass(frozen=True)
class Precheck:
    """Result of a safety check.

    ``detail`` carries a bare path or name for the UI to interpolate into its own
    translated message -- never a pre-built sentence.
    """

    refusal: Refusal | None
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.refusal is None


@dataclass(frozen=True)
class CopyFailure:
    """One file that could not be copied during :func:`perform_copy`."""

    path: str
    error: str


@dataclass(frozen=True)
class CopyReport:
    """Outcome of :func:`perform_copy`."""

    files_copied: int
    cancelled: bool
    failures: tuple[CopyFailure, ...] = field(default_factory=tuple)


def is_within(child: Path, parent: Path) -> bool:
    """True if *child* resolves to *parent* itself or to a path inside it.

    ``Path.relative_to`` is purely lexical, so a symlink can dodge a normpath-only
    containment check; both sides are resolved first (see ``ui/mixins/_file_mgmt_ops.py``
    for the precedent this follows).
    """
    try:
        child_r = child.resolve()
        parent_r = parent.resolve()
    except OSError:
        child_r, parent_r = child, parent
    return child_r == parent_r or parent_r in child_r.parents


def _fs_root() -> Path:
    return Path(os.path.abspath(os.sep))


def _protected_set(protected: Collection[Path]) -> set[Path]:
    resolved = {_fs_root()}
    try:
        resolved.add(Path.home().resolve())
    except (RuntimeError, OSError):
        pass
    for p in protected:
        try:
            resolved.add(Path(p).resolve())
        except OSError:
            resolved.add(Path(p))
    return resolved


def _is_protected(path: Path, protected: Collection[Path]) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path
    return resolved in _protected_set(protected)


def _is_same_file(a: Path, b: Path) -> bool:
    try:
        return os.path.samefile(a, b)
    except OSError:
        return False


def _validate_name(name: str, parent: Path) -> Refusal | None:
    """Shared name validation for :func:`check_new_folder` and :func:`check_rename`.

    Order matters: the containment check must run *before* the literal-separator
    check, because a traversal name like ``"../escaped"`` contains a ``/`` too, and
    such a name must report ``ESCAPES_PARENT`` rather than ``NAME_HAS_SEPARATOR``. A
    separator-containing name that still normalizes to inside *parent* (e.g.
    ``"sub/dir"``) falls through to ``NAME_HAS_SEPARATOR``.
    """
    if not name or not name.strip() or name in (".", ".."):
        return Refusal.NAME_EMPTY
    normalized = os.path.normpath(os.path.join(str(parent), name))
    parent_norm = os.path.normpath(str(parent))
    if normalized != parent_norm and not normalized.startswith(parent_norm + os.sep):
        return Refusal.ESCAPES_PARENT
    if "/" in name or "\\" in name:
        return Refusal.NAME_HAS_SEPARATOR
    return None


def is_cross_device(src: Path, dst: Path) -> bool:
    try:
        return os.stat(src).st_dev != os.stat(dst.parent).st_dev
    except OSError:
        return False


def check_move(src: Path, dst: Path, protected: Collection[Path] = ()) -> Precheck:
    src = Path(src)
    dst = Path(dst)
    if not os.path.lexists(src):
        return Precheck(Refusal.SOURCE_MISSING, str(src))
    if _is_protected(src, protected):
        return Precheck(Refusal.PROTECTED_PATH, str(src))
    if os.path.normpath(str(src)) == os.path.normpath(str(dst)):
        return Precheck(Refusal.SAME_PATH, str(dst))
    if is_within(dst, src):
        return Precheck(Refusal.INTO_OWN_SUBTREE, str(dst))
    if os.path.lexists(dst):
        if _is_same_file(src, dst):
            return Precheck(None)  # case-only rename on a case-insensitive filesystem
        return Precheck(Refusal.DESTINATION_EXISTS, str(dst))
    if not os.access(dst.parent, os.W_OK):
        return Precheck(Refusal.PERMISSION, str(dst.parent))
    return Precheck(None)


def check_copy(src: Path, dst: Path, protected: Collection[Path] = ()) -> Precheck:
    src = Path(src)
    dst = Path(dst)
    if not os.path.lexists(src):
        return Precheck(Refusal.SOURCE_MISSING, str(src))
    if _is_protected(src, protected):
        return Precheck(Refusal.PROTECTED_PATH, str(src))
    if os.path.normpath(str(src)) == os.path.normpath(str(dst)):
        return Precheck(Refusal.SAME_PATH, str(dst))
    if is_within(dst, src):
        return Precheck(Refusal.INTO_OWN_SUBTREE, str(dst))
    if os.path.lexists(dst):
        return Precheck(Refusal.DESTINATION_EXISTS, str(dst))
    if not os.access(dst.parent, os.W_OK):
        return Precheck(Refusal.PERMISSION, str(dst.parent))
    return Precheck(None)


def check_delete(target: Path, protected: Collection[Path] = ()) -> Precheck:
    target = Path(target)
    if not os.path.lexists(target):
        return Precheck(Refusal.SOURCE_MISSING, str(target))
    if _is_protected(target, protected):
        return Precheck(Refusal.PROTECTED_PATH, str(target))
    if not os.access(target.parent, os.W_OK):
        return Precheck(Refusal.PERMISSION, str(target.parent))
    return Precheck(None)


def check_rename(src: Path, new_name: str, protected: Collection[Path] = ()) -> Precheck:
    src = Path(src)
    reason = _validate_name(new_name, src.parent)
    if reason is not None:
        return Precheck(reason, new_name)
    dst = Path(os.path.normpath(os.path.join(str(src.parent), new_name)))
    return check_move(src, dst, protected)


def check_new_folder(parent: Path, name: str) -> Precheck:
    parent = Path(parent)
    reason = _validate_name(name, parent)
    if reason is not None:
        return Precheck(reason, name)
    if not parent.is_dir():
        return Precheck(Refusal.NOT_A_DIRECTORY, str(parent))
    dst = Path(os.path.normpath(os.path.join(str(parent), name)))
    if os.path.lexists(dst):
        return Precheck(Refusal.DESTINATION_EXISTS, str(dst))
    return Precheck(None)


def unique_name(parent: Path, base: str, suffix: str = "_copy") -> str:
    """First of ``base + suffix``, ``base + suffix + "2"``, ``… + "3"``, … not present
    under *parent*. Matches the suffix ``ui/dialogs/duplicate_case_dialog.py`` proposes.
    """
    parent = Path(parent)
    candidate = f"{base}{suffix}"
    if not (parent / candidate).exists():
        return candidate
    n = 2
    while (parent / f"{base}{suffix}{n}").exists():
        n += 1
    return f"{base}{suffix}{n}"


def perform_move(src: Path, dst: Path) -> None:
    """Move *src* to *dst*.

    Never hands an existing directory to ``shutil.move`` (it would nest *src* inside
    *dst* instead of failing). On any exception the source is left intact -- no
    automatic rollback of a partial destination is attempted.
    """
    src = Path(src)
    dst = Path(dst)
    if not os.path.lexists(src):
        raise FileNotFoundError(str(src))
    if os.path.lexists(dst):
        if _is_same_file(src, dst):
            src.rename(dst)
            return
        raise FileExistsError(str(dst))
    if is_cross_device(src, dst):
        shutil.move(str(src), str(dst))
    else:
        try:
            os.rename(src, dst)
        except OSError:
            shutil.move(str(src), str(dst))


def _iter_relative_entries(root: Path) -> Iterator[Path]:
    """Yield every directory, file, and symlink under *root*, relative to it.

    A symlinked directory is yielded once (as an entry of its parent) and never
    descended into, courtesy of ``followlinks=False`` -- callers copy it as a link.
    """
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        base = Path(dirpath)
        for name in dirnames:
            yield (base / name).relative_to(root)
        for name in filenames:
            yield (base / name).relative_to(root)


def perform_copy(
    src: Path,
    dst: Path,
    *,
    progress: Callable[[str, int, int], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> CopyReport:
    """Copy *src* to *dst*.

    Implemented as an explicit walk over ``shutil.copy2`` rather than
    ``shutil.copytree``, which has no cancellation hook. Symlinks are replicated as
    symlinks (never followed into a full copy of their target). A cancelled or
    partially-failed copy leaves whatever was already written in place -- no
    auto-cleanup of the partial destination.
    """
    src = Path(src)
    dst = Path(dst)
    if not os.path.lexists(src):
        raise FileNotFoundError(str(src))

    def _is_cancelled() -> bool:
        return cancelled() if cancelled is not None else False

    if src.is_symlink():
        os.symlink(os.readlink(src), dst)
        return CopyReport(files_copied=0, cancelled=False, failures=())

    if not src.is_dir():
        if _is_cancelled():
            return CopyReport(files_copied=0, cancelled=True, failures=())
        try:
            shutil.copy2(src, dst)
            if progress is not None:
                progress(src.name, 1, 1)
            return CopyReport(files_copied=1, cancelled=False, failures=())
        except OSError as exc:
            failure = CopyFailure(str(src), str(exc))
            return CopyReport(files_copied=0, cancelled=False, failures=(failure,))

    dst.mkdir(parents=True, exist_ok=False)
    entries = list(_iter_relative_entries(src))
    total = len(entries)
    files_copied = 0
    was_cancelled = False
    failures: list[CopyFailure] = []
    for i, rel in enumerate(entries, start=1):
        if _is_cancelled():
            was_cancelled = True
            break
        s = src / rel
        d = dst / rel
        try:
            if s.is_symlink():
                d.parent.mkdir(parents=True, exist_ok=True)
                os.symlink(os.readlink(s), d)
                files_copied += 1
            elif s.is_dir():
                d.mkdir(parents=True, exist_ok=True)
            else:
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(s, d)
                files_copied += 1
        except OSError as exc:
            failures.append(CopyFailure(str(s), str(exc)))
        if progress is not None and (i == total or i % _PROGRESS_EVERY == 0):
            progress(str(rel), i, total)
    return CopyReport(files_copied=files_copied, cancelled=was_cancelled, failures=tuple(failures))


def perform_delete(target: Path, *, remove: Callable[[Path], None] | None = None) -> None:
    """Delete *target* via *remove* (default: a permanent stdlib delete).

    *remove* is injected because the real UI remover is Qt's
    ``QFile.moveToTrash()``, which this Qt-free module cannot call itself.
    """
    remover = remove if remove is not None else _default_remove
    remover(Path(target))


def _default_remove(path: Path) -> None:
    if path.is_symlink() or not path.is_dir():
        os.remove(path)
    else:
        shutil.rmtree(path)


def perform_new_folder(parent: Path, name: str) -> Path:
    dst = Path(os.path.normpath(os.path.join(str(parent), name)))
    dst.mkdir(parents=False, exist_ok=False)
    return dst
