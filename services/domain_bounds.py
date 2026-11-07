# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Qt-free: where the case's domain is, from its blockMeshDict.

Used to give a new probe, sample line or cutting plane a starting place
inside the domain rather than a template's example coordinates, which are
often on a corner or outside it entirely (OpenCFD's probes example is
``(0 0 0)``). Read from ``blockMeshDict`` -- the same read the 3-D view
makes, ``$variables``, ``#eval``, ``#include`` and ``scale`` resolved -- and
never from ``constant/polyMesh/points``, which can be gigabytes. A case
meshed with snappyHexMesh has a blockMeshDict too, but it is only the
background box, whose centre may sit inside a solid body; that is reported,
not hidden.
"""
from __future__ import annotations

import dataclasses
import os
from collections.abc import Callable, Sequence
from pathlib import Path

from foam.block_mesh_extractor import extract_block_mesh_data
from foam.include_expand import expand_includes
from foam.parser import OpenFoamParser


@dataclasses.dataclass(frozen=True)
class DomainBounds:
    lo: tuple[float, float, float]
    hi: tuple[float, float, float]
    # The blockMesh is only snappyHexMesh's background box: its centre need
    # not be in the fluid.
    background: bool = False

    @property
    def centre(self) -> tuple[float, float, float]:
        return tuple((a + b) / 2 for a, b in zip(self.lo, self.hi))  # type: ignore[return-value]

    @property
    def span(self) -> tuple[float, float, float]:
        return tuple(b - a for a, b in zip(self.lo, self.hi))  # type: ignore[return-value]


def domain_bounds(
    case_dir: str,
    etc_dirs: Sequence[Path] = (),
    read_text: Callable[[Path], str | None] | None = None,
) -> DomainBounds | None:
    """The bounding box of the case's blockMesh, or None if there is none.

    ``system/blockMeshDict``, else the older ``constant/polyMesh/
    blockMeshDict``. *read_text* lets the caller serve an unsaved editor
    buffer, as the 3-D view does. None when no vertices resolve.
    """
    for rel in (("system", "blockMeshDict"), ("constant", "polyMesh", "blockMeshDict")):
        path = Path(case_dir, *rel)
        text = read_text(path) if read_text is not None else None
        if text is None:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
        try:
            root = OpenFoamParser(text).parse()
            root = expand_includes(
                root, source_file=path, case_dir=Path(case_dir),
                etc_dirs=etc_dirs, read_text=read_text,
            ).root
            vertices = extract_block_mesh_data(root).vertices
        except Exception:
            return None
        if not vertices:
            return None
        lo = tuple(min(v[i] for v in vertices) for i in range(3))
        hi = tuple(max(v[i] for v in vertices) for i in range(3))
        background = os.path.isfile(os.path.join(case_dir, "system", "snappyHexMeshDict"))
        return DomainBounds(lo, hi, background)  # type: ignore[arg-type]
    return None
