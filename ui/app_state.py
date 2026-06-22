# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import dataclasses
import subprocess

from foam.nodes import FoamNode
from model.tree_model import FoamTreeModel
from services.case_files_config import CaseFilesConfig


@dataclasses.dataclass
class AppState:
    """Centralised shared state for a MainWindow session.

    All cross-mixin data lives here so every shared dependency shows up as
    ``self.state.<field>`` rather than a bare ``self.<attr>`` that could
    belong anywhere.
    """

    # ── current file / tree ───────────────────────────────────────────────────
    current_case_dir: str | None = None
    current_file: str | None = None
    current_root: FoamNode = dataclasses.field(
        default_factory=lambda: FoamNode(name="root", node_type="dictionary")
    )
    current_model: FoamTreeModel | None = dataclasses.field(default=None)

    # ── file buffers & dirty tracking ─────────────────────────────────────────
    file_buffers: dict[str, str] = dataclasses.field(default_factory=dict)
    file_dirty: dict[str, bool] = dataclasses.field(default_factory=dict)
    text_dirty: bool = False

    # ── internal flags ────────────────────────────────────────────────────────
    source_lines_valid: bool = False
    syncing: bool = False

    # ── case config & parse cache ─────────────────────────────────────────────
    case_files_config: CaseFilesConfig | None = None
    parsed_roots: dict[str, FoamNode] = dataclasses.field(default_factory=dict)

    # ── diff / comparison state ───────────────────────────────────────────────
    diff_case_dir: str | None = None
    diff_parsed_roots: dict[str, FoamNode] = dataclasses.field(default_factory=dict)

    # ── foamMonitor state ─────────────────────────────────────────────────────
    foam_monitor_proc: subprocess.Popen | None = None
    foam_monitor_script_tmp: str | None = None
    foam_monitor_last_file: str = ""
    foam_monitor_last_options: dict = dataclasses.field(default_factory=dict)

    # ── panel state ───────────────────────────────────────────────────────────
    bm_side_by_side: bool = False

    def __post_init__(self) -> None:
        if self.current_model is None:
            self.current_model = FoamTreeModel(self.current_root)
