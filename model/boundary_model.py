# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from pathlib import Path

from foam.nodes import FoamNode


def extract_boundary(root: FoamNode) -> dict[str, FoamNode]:
    """Return {patch_name: patch_dict_node} from root's boundaryField dict."""
    for node in root.children:
        if node.name == "boundaryField" and node.node_type == "dictionary":
            return {
                child.name: child
                for child in node.children
                if child.node_type == "dictionary"
            }
    return {}


def _is_in_dir(path: str, case_dir: str, dir_name: str) -> bool:
    try:
        return Path(path).is_relative_to(Path(case_dir) / dir_name)
    except ValueError:
        return False


class BoundaryModel:
    """Holds field roots and boundary extraction logic for the boundary view panel."""

    def __init__(self) -> None:
        self.case_dir: str | None = None
        self._field_roots: dict[str, FoamNode] = {}
        self._available_dirs: list[str] = []

    # ── public API ────────────────────────────────────────────────────────────

    @property
    def field_roots(self) -> dict[str, FoamNode]:
        return self._field_roots

    @property
    def available_dirs(self) -> list[str]:
        return self._available_dirs

    def load(
        self,
        field_roots: dict[str, FoamNode],
        case_dir: str,
        available_dirs: list[str],
    ) -> None:
        self._field_roots = dict(field_roots)
        self.case_dir = case_dir
        self._available_dirs = list(available_dirs)

    def update_field(self, path: str, root: FoamNode) -> None:
        self._field_roots[path] = root

    def clear(self) -> None:
        self._field_roots.clear()
        self.case_dir = None
        self._available_dirs = []

    def is_in_dir(self, path: str, dir_name: str) -> bool:
        if not self.case_dir:
            return False
        return _is_in_dir(path, self.case_dir, dir_name)

    def boundaries_for_dir(self, dir_filter: str) -> dict[str, dict[str, FoamNode]]:
        """Return {path: {patch_name: patch_node}} for files in the given directory."""
        if not self.case_dir:
            return {}
        return {
            path: extract_boundary(root)
            for path, root in self._field_roots.items()
            if _is_in_dir(path, self.case_dir, dir_filter)
        }
