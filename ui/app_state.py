# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

import dataclasses
import subprocess

from foam.nodes import FoamNode
from model.tree_model import FoamTreeModel
from services.case_files_config import CaseFilesConfig


@dataclasses.dataclass
class DiffState:
    case_dir: str | None = None
    parsed_roots: dict[str, FoamNode] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class FoamMonitorState:
    proc: subprocess.Popen | None = None
    script_tmp: str | None = None
    last_file: str = ""
    last_options: dict = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class UndoSnapshot:
    """Pre-mutation state of every file a tree operation touches."""

    texts: dict[str, str]     # path → serialized text before the mutation
    dirty: dict[str, bool]    # path → file_dirty flag before the mutation


@dataclasses.dataclass
class UndoState:
    """Snapshot-based undo/redo for tree edits.

    A single global timeline (not per file): each snapshot records every file
    the operation touched, so multi-file boundary operations undo as one step
    and a redo branch is invalidated by *any* subsequent edit.
    """

    undo_stack: list[UndoSnapshot] = dataclasses.field(default_factory=list)
    redo_stack: list[UndoSnapshot] = dataclasses.field(default_factory=list)
    # Pre-mutation snapshot stashed by the model's about_to_change signal (which
    # fires before the edit is validated). It is committed onto undo_stack only
    # once the edit is confirmed to have changed something (see
    # _commit_pending_undo); a rejected or value-unchanged inline edit therefore
    # leaves the undo/redo stacks untouched.
    pending: UndoSnapshot | None = None
    # True while an operation that already took its explicit checkpoint runs,
    # so the model's about_to_change signal does not stash a second (mid-state)
    # snapshot. Reset on the next event-loop tick.
    op_active: bool = False
    # True while an undo/redo restore runs, so nothing re-checkpoints.
    restoring: bool = False


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
    diff: DiffState = dataclasses.field(default_factory=DiffState)

    # ── foamMonitor state ─────────────────────────────────────────────────────
    foam_monitor: FoamMonitorState = dataclasses.field(default_factory=FoamMonitorState)

    # ── Tools-menu "Run *" dialogs: last-used option values per tool ──────────
    run_tool_options: dict[str, dict] = dataclasses.field(default_factory=dict)

    # ── tree-edit undo/redo ───────────────────────────────────────────────────
    undo: UndoState = dataclasses.field(default_factory=UndoState)

    # ── panel state ───────────────────────────────────────────────────────────
    bm_side_by_side: bool = False

    def __post_init__(self) -> None:
        if self.current_model is None:
            self.current_model = FoamTreeModel(self.current_root)
