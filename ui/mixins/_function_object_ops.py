# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Mixin: Tools > Add Function Object… (see ui/dialogs/function_object_dialog.py)."""
from __future__ import annotations

import os
import re
from functools import partial
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QDialog, QMessageBox

from foam.nodes import FoamNode
from foam.parser import OpenFoamParser
from foam.sampling_extractor import extract_sampling_data
from i18n import tr
from services.case_loader import detect_time_dirs
from services.domain_bounds import domain_bounds
from services.function_templates import (
    add_include_func,
    case_field_names,
    case_patch_names,
    function_names,
    legacy_plane_keywords,
    list_templates,
    suggest_values,
    template_root,
)
from services.include_scan import foam_etc_dirs
from services.post_process import (
    ALL_FUNCTIONS,
    COMMON_FUNCTIONS,
    post_process_command,
    post_process_tool,
)
from services.solver_run import decomposition_status, read_solver_info
from services.tool_options import POST_PROCESS_SPEC
from ui import viewer_dicts
from ui.dialogs.function_object_dialog import FunctionObjectDialog, existing_names
from ui.dialogs.run_post_process_dialog import RunPostProcessDialog
from ui.layout_constants import STATUS_NORMAL

# The 3-D view's key for the dialog's live preview: not a path, so it can
# never be mistaken for, or overwrite, a file's own shapes.
_PREVIEW_KEY = "<function object preview>"


if TYPE_CHECKING:
    from ui.mixins._protocol import MainWindowProtocol as _Base
else:
    _Base = object


def _include_func_names(control_text: str) -> list[str]:
    """controlDict's ``#includeFunc`` names, in order, each once."""
    names = re.findall(r"^\s*#includeFunc\s+([A-Za-z][A-Za-z0-9_]*)", control_text, re.MULTILINE)
    return list(dict.fromkeys(names))


def _installation() -> str | None:
    root = template_root(str(d) for d in foam_etc_dirs())
    return os.path.dirname(os.path.dirname(os.path.dirname(root))) if root else None


class _FunctionObjectOpsMixin(_Base):
    def _on_run_post_process_clicked(self, preset: str = ALL_FUNCTIONS) -> None:
        """Tools > Run postProcess…, or a function file's right-click (*preset*)."""
        case_dir = self.state.current_case_dir
        if not case_dir or self.terminal_panel is None:
            return
        if self._refuse_while_running(tr("running postProcess")):
            return
        tool = post_process_tool(_installation())
        control_text = self._current_text(os.path.join(case_dir, "system", "controlDict")) or ""
        info = read_solver_info(control_text)

        warnings = []
        decomposed = decomposition_status(case_dir)
        results_at_root = any(t != "0" for t in detect_time_dirs(case_dir))
        if not results_at_root and not (decomposed and decomposed.unreconstructed):
            warnings.append(
                tr(
                    "This case has no results yet: postProcess works on time "
                    "directories a run has written. Function objects in "
                    "controlDict run with the solver anyway."
                )
            )
        if self._dirty_paths():
            warnings.append(
                tr(
                    "Some files have unsaved edits. postProcess reads them from "
                    "disk — save first for a changed function object to count."
                )
            )
        parallel_np = None
        parallel_default = False
        if decomposed is not None and not decomposed.collated:
            parallel_np = decomposed.count
            # The latest results live only in processor*: process them there.
            parallel_default = bool(decomposed.unreconstructed)

        dlg = RunPostProcessDialog(
            case_dir,
            tool,
            _include_func_names(control_text),
            COMMON_FUNCTIONS,
            info.application,
            info.module,
            self.state.run_tool_options.get(POST_PROCESS_SPEC.name),
            "\n".join(warnings),
            self,
            preset=preset,
            parallel_np=parallel_np,
            parallel_default=parallel_default,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        # Options only, like Run Solver: the function is chosen afresh each time.
        self.state.run_tool_options[POST_PROCESS_SPEC.name] = dlg.get_values()
        self._run_in_terminal(dlg.get_command())

    def _function_file_paths(self) -> set[str]:
        """``system/<name>`` files controlDict runs with ``#includeFunc <name>``."""
        case_dir = self.state.current_case_dir
        if not case_dir:
            return set()
        text = self._current_text(os.path.join(case_dir, "system", "controlDict")) or ""
        paths = {os.path.join(case_dir, "system", n) for n in _include_func_names(text)}
        return {p for p in paths if os.path.isfile(p)}

    def _on_run_post_process_for_file(self, path: str) -> None:
        """A function file's right-click: Run postProcess with it pre-filled."""
        self._on_run_post_process_clicked(os.path.basename(path))

    def _on_add_function_object_clicked(self) -> None:
        case_dir = self.state.current_case_dir
        if not case_dir:
            return
        root = template_root(str(d) for d in foam_etc_dirs())
        if root is None:
            QMessageBox.warning(
                self,
                tr("No OpenFOAM installation found"),
                tr(
                    "The function-object templates come from an OpenFOAM "
                    "installation, and none was found. Source OpenFOAM's "
                    "bashrc before starting FoDE, or choose an installation "
                    "in Tools > Find OpenFOAM Examples…."
                ),
            )
            return
        control_dict = os.path.join(case_dir, "system", "controlDict")
        if self.state.file_dirty.get(control_dict):
            QMessageBox.warning(
                self,
                tr("Add Function Object"),
                tr(
                    "system/controlDict has unsaved edits. Save or reload it "
                    "first: adding a function object writes to it."
                ),
            )
            return
        try:
            with open(control_dict, encoding="utf-8") as f:
                control_text = f.read()
        except OSError:
            QMessageBox.warning(
                self,
                tr("Add Function Object"),
                tr("This case has no system/controlDict to add a function object to."),
            )
            return

        times = detect_time_dirs(case_dir)
        installation = os.path.dirname(os.path.dirname(os.path.dirname(root)))
        # The domain, for starting places inside it: blockMeshDict as FoDE has
        # it, unsaved edits included, as the 3-D view reads it.
        bounds = domain_bounds(
            case_dir, foam_etc_dirs(),
            lambda p: self._current_text(str(p), fallback=False),
        )
        dlg = FunctionObjectDialog(
            list_templates(root),
            installation,
            case_field_names(case_dir, times[-1] if times else None),
            case_patch_names(case_dir),
            existing_names(case_dir, function_names(control_text)),
            self,
            post_process=(
                post_process_command(installation, case_dir)
                if self.terminal_panel is not None else ""
            ),
            legacy_plane_keys=legacy_plane_keywords(installation),
            suggest=partial(suggest_values, bounds=bounds) if bounds else None,
            background=bool(bounds and bounds.background),
        )
        self._preview_shown = False
        if self.block_mesh_panel is not None:
            dlg.preview_changed.connect(self._preview_function_object)
        try:
            accepted = dlg.exec() == QDialog.DialogCode.Accepted
        finally:
            self._clear_function_object_preview()
        if not accepted:
            return
        name, content = dlg.result_name(), dlg.result_text()
        tool = post_process_tool(installation)
        if self._write_function_object(case_dir, control_dict, control_text, name, content, tool):
            if dlg.run_post_process() and not self._refuse_while_running(
                tr("running postProcess")
            ):
                info = read_solver_info(control_text)
                command = post_process_command(
                    installation, case_dir, name, info.application, info.module
                )
                self._run_in_terminal(f"{command} 2>&1 | tee log.{tool}")

    def _preview_function_object(self, name: str, text: str) -> None:
        """Draw the dialog's file in the 3-D view as it is being filled in."""
        if self.block_mesh_panel is None or not self.state.current_case_dir:
            return
        try:
            root = OpenFoamParser(text).parse()
        except Exception:
            return  # half-typed: keep the last good preview
        path = os.path.join(self.state.current_case_dir, "system", name or "preview")
        expanded = self._expand_includes_for_viewer(path, root).root
        self.block_mesh_panel.update_sampling(_PREVIEW_KEY, expanded, name=name or "preview")
        if not self._preview_shown and extract_sampling_data(expanded, name).shapes:
            # Bring the 3-D view forward once, the first time there is
            # something to see, without fighting the user afterwards.
            self._preview_shown = True
            if self.upper_tabs.indexOf(self.block_mesh_panel) != -1:
                self.upper_tabs.setCurrentWidget(self.block_mesh_panel)

    def _clear_function_object_preview(self) -> None:
        if self.block_mesh_panel is not None:
            self.block_mesh_panel.update_sampling(
                _PREVIEW_KEY, FoamNode(name="root", node_type="dictionary")
            )

    def _write_function_object(
        self,
        case_dir: str,
        control_dict: str,
        control_text: str,
        name: str,
        content: str,
        tool: str = "postProcess",
    ) -> bool:
        """Write ``system/<name>`` and its ``#includeFunc`` line, then show both.

        True when both were written.
        """
        target = os.path.join(case_dir, "system", name)
        new_control = add_include_func(control_text, name)
        if new_control is None:
            QMessageBox.warning(
                self,
                tr("Add Function Object"),
                tr(
                    "controlDict's functions entry is not a dictionary FoDE "
                    "can add to. Nothing was written; add #includeFunc {name} "
                    "to it by hand after creating system/{name}."
                ).format(name=name),
            )
            return False
        if os.path.exists(target):
            self._error(
                tr("Add Function Object"),
                tr("system/{name} already exists; nothing was written.").format(name=name),
            )
            return False
        try:
            with open(target, "w", encoding="utf-8") as f:
                f.write(content if content.endswith("\n") else content + "\n")
            # In place, like every other controlDict write: a running solver
            # may be watching the file.
            with open(control_dict, "w", encoding="utf-8") as f:
                f.write(new_control)
        except OSError as e:
            self._error(tr("Add Function Object"), str(e))
            return False
        config = self.state.case_files_config
        rel = os.path.join("system", name)
        if config is not None and name not in viewer_dicts.SAMPLING_DICT_NAMES:
            try:
                data = extract_sampling_data(OpenFoamParser(content).parse(), name)
            except Exception:
                data = None
            if data is not None and (data.shapes or data.non_geometric):
                # Recognised by name only for the default names; a sampling
                # function saved as probes1 is drawn because FoDE says so.
                config.set_viewer_kind(rel, viewer_dicts.SAMPLING)
                config.save()
        self._reload_clean_file_from_disk(control_dict)
        self._reload_file_list()
        if not self.file_list_panel.has_file(target) and self.state.case_files_config is not None:
            # Not one of the names the file list shows by itself: add it.
            self.state.case_files_config.add_file(os.path.join("system", name))
            self.state.case_files_config.save()
            self._reload_file_list()
        self.load_selected_file(target)
        self.statusBar().showMessage(
            tr(
                "Added function object {name}: system/{name}, and "
                "#includeFunc {name} in controlDict. It runs with the solver; "
                "for existing results, run {tool} -func {name}."
            ).format(name=name, tool=tool),
            STATUS_NORMAL,
        )
        return True
