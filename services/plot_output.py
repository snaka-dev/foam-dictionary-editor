# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Where Plot Results may write its images and scripts, and how.

Plot Results reads a case and never needs to change it; what it writes --
an image, a ``.py``/``.gp`` script, a gnuplot ``.dat`` snapshot -- belongs
beside the case's files, not among them. The save dialogs start in the case
directory, so one mistyped or misclicked name could otherwise land a
``force.dat`` over the forces a run wrote (a gnuplot export names its data
file after the script, silently choosing the stem), or a stray file in
``postProcessing/`` that the next scan lists as a data set.

:func:`refusal` is the rule, as a code the dialog words: inside an
OpenFOAM case nothing is written into the directories OpenFOAM owns, and the
run's logs, scripts and ParaView stub at the case root are never replaced.
Asking would not be enough -- an "Overwrite?" box is the one a user has
learned to click through. :func:`write_atomically` makes a replacement
all-or-nothing, so a failed write (disk full) cannot leave a truncated file
where the old one was.

Qt-free; ``ui/dialogs/plot_results_dialog.py`` holds the words.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

# A case's subdirectories that OpenFOAM, its utilities or FoDE read.
OWNED_DIRS = frozenset({"system", "constant", "postProcessing", "dynamicCode", "VTK"})

# How far up from the target directory to look for the case it is in.
_MAX_DEPTH = 8


def _is_time_dir(name: str) -> bool:
    try:
        float(name)
    except ValueError:
        return name.endswith(".orig") and _is_time_dir(name[: -len(".orig")])
    return True


def _owned(name: str) -> bool:
    return name in OWNED_DIRS or name.startswith("processor") or _is_time_dir(name)


def case_root_of(path: str) -> str | None:
    """The OpenFOAM case holding *path* (a file or directory), or None."""
    here = Path(path).parent
    for _ in range(_MAX_DEPTH):
        if (here / "system").is_dir() or (here / "constant").is_dir():
            return str(here)
        if here.parent == here:
            return None
        here = here.parent
    return None


def _root_file_protected(name: str) -> bool:
    return (
        name.startswith(("log.", "All", "."))
        or name.endswith(".foam")
    )


def refusal(
    path: str,
    protected: frozenset[str] = frozenset(),
    cases: tuple[str, ...] = (),
) -> str | None:
    """Why Plot Results must not write *path*, or None when it may.

    Codes: ``"protected"`` -- one of *protected* (the files being plotted);
    ``"case_dir"`` -- inside a directory of a case that OpenFOAM owns
    (``system/``, ``constant/``, ``postProcessing/``, a time or
    ``processor*`` directory, …); ``"case_file"`` -- an existing log,
    ``All*`` script, hidden or ``.foam`` file at a case root. A symlink is
    judged by where it points as well as where it is.

    A case is a directory with ``system/`` or ``constant/`` above the path,
    or any of *cases* -- the window's own, which may be results copied
    without their dictionaries.
    """
    candidates = [os.path.abspath(path)]
    real = os.path.realpath(path)
    if real != candidates[0]:
        candidates.append(real)
    protected_real = {os.path.realpath(p) for p in protected}
    for target in candidates:
        if target in protected_real or os.path.realpath(target) in protected_real:
            return "protected"
        roots = {case_root_of(target)}
        for case in cases:
            for base in {os.path.abspath(case), os.path.realpath(case)}:
                if target.startswith(base.rstrip(os.sep) + os.sep):
                    roots.add(base)
        for root in roots - {None}:
            assert root is not None
            parts = Path(os.path.relpath(target, root)).parts
            if len(parts) > 1 and _owned(parts[0]):
                return "case_dir"
            if len(parts) == 1 and os.path.lexists(target) and _root_file_protected(parts[0]):
                return "case_file"
    return None


def write_atomically(path: str, data: bytes | str) -> None:
    """Write *data* to *path* through a sibling temporary file and a rename.

    A replaced file keeps its permission bits. Raises ``OSError``; on failure
    *path* is left as it was and the temporary file is removed.
    """
    raw = data.encode("utf-8") if isinstance(data, str) else data
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".plot-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(raw)
        try:
            os.chmod(tmp, os.stat(path).st_mode & 0o7777)
        except FileNotFoundError:
            os.chmod(tmp, 0o666 & ~_umask())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def _umask() -> int:
    mask = os.umask(0)
    os.umask(mask)
    return mask
