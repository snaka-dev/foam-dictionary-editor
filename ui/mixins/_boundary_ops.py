# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QDialog, QMessageBox

from foam.nodes import FoamNode
from i18n import tr
from model.boundary_model import extract_boundary
from services.case_loader import FIELD_DIRS
from ui.dialogs.boundary_edit_dialog import BoundaryEditDialog, _parse_patch_content, _patch_inner_text
from ui.dialogs.rename_boundary_dialog import RenameBoundaryDialog, find_rename_targets
from ui.layout_constants import (
    STATUS_NORMAL as _STATUS_NORMAL,
)
from ui.layout_constants import (
    STATUS_SHORT as _STATUS_SHORT,
)


def _find_boundary_field(root: FoamNode) -> FoamNode | None:
    """Return root's 'boundaryField' dictionary child, or None."""
    return next(
        (n for n in root.children if n.name == "boundaryField" and n.node_type == "dictionary"),
        None,
    )


def _append_new_patch(boundary_field: FoamNode, patch_name: str) -> FoamNode:
    """Append an empty, modified patch dictionary to boundary_field."""
    patch = FoamNode(name=patch_name, node_type="dictionary", modified=True)
    patch.leading_trivia = ["\n"]
    patch.parent = boundary_field
    boundary_field.children.append(patch)
    boundary_field.modified = True
    return patch


def _set_patch_children(patch: FoamNode, children: list[FoamNode]) -> None:
    """Replace patch's children, reparent them, and force regeneration."""
    patch.children = children
    for child in children:
        child.parent = patch
    patch.modified = True
    patch.raw_text = ""


if TYPE_CHECKING:
    from ui.mixins._protocol import MainWindowProtocol as _Base
else:
    _Base = object


class _BoundaryOpsMixin(_Base):
    """Boundary view population and patch-level edit operations."""

    # ── panel population ──────────────────────────────────────────────────────

    def _available_field_dirs(self) -> list[str]:
        if not self.state.current_case_dir:
            return []
        result: list[str] = []
        for base in FIELD_DIRS:
            d = Path(self.state.current_case_dir) / base
            if not d.is_dir():
                continue
            result.append(base)
            for sub in sorted(d.iterdir(), key=lambda x: x.name.lower()):
                if sub.is_dir() and any(f.is_file() for f in sub.iterdir()):
                    result.append(f"{base}/{sub.name}")
        return result

    def _reload_boundary_panel(self) -> None:
        if not self.state.current_case_dir:
            self.boundary_panel.clear()
            return
        available = self._available_field_dirs()
        if not available:
            self.boundary_panel.clear()
            return
        field_roots: dict[str, FoamNode] = {}
        for dir_name in available:
            d = Path(self.state.current_case_dir) / dir_name
            if not d.is_dir():
                continue
            for p in sorted(d.iterdir(), key=lambda x: x.name.lower()):
                if p.is_file():
                    path = str(p)
                    if path not in self.state.parsed_roots:
                        self._cache_parsed_root(path)
                    root = self.state.parsed_roots.get(path)
                    if root is not None:
                        field_roots[path] = root

        case_base = Path(self.state.current_case_dir)
        dirs_with_fields = [
            d for d in available
            if any(Path(p).parent == case_base / d for p in field_roots)
        ]
        if not dirs_with_fields:
            self.boundary_panel.clear()
            return
        self.boundary_panel.load_case(field_roots, self.state.current_case_dir, dirs_with_fields)

    # ── patch edit signals ────────────────────────────────────────────────────

    def _on_patch_edit_requested(self, path: str, patch_name: str, patch_node: object) -> None:
        root = self.state.parsed_roots.get(path)
        if root is None:
            return

        live_patch = extract_boundary(root).get(patch_name)
        if live_patch is None:
            QMessageBox.warning(
                self, tr("Boundary Not Found"),
                tr("Patch '{name}' not found in {file}.").format(name=patch_name, file=Path(path).name),
            )
            return

        field_name = Path(path).name
        original_text = _patch_inner_text(live_patch)
        dlg = BoundaryEditDialog(field_name, patch_name, live_patch, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        new_type = dlg.new_type

        if dlg.is_complex_mode:
            type_node = next((c for c in live_patch.children if c.name == "type"), None)
            current_type = str(type_node.value) if type_node and type_node.value is not None else ""
            if not new_type or new_type == current_type:
                return
            self._checkpoint_for_undo([path])
            if type_node is not None:
                type_node.value = new_type
                type_node.modified = True
            live_patch.modified = True
        else:
            if dlg.new_dict_text.strip() == original_text.strip():
                return
            try:
                new_children = _parse_patch_content(dlg.new_dict_text)
            except Exception as e:
                QMessageBox.warning(
                    self, tr("Parse Error"), tr("Could not parse patch content:\n{e}").format(e=e)
                )
                return
            self._checkpoint_for_undo([path])
            _set_patch_children(live_patch, new_children)

        self._apply_boundary_root_change(path, root)
        self.statusBar().showMessage(
            tr("Boundary updated: {file} / {patch}").format(file=Path(path).name, patch=patch_name),
            _STATUS_SHORT,
        )

    def _on_patch_create_requested(self, path: str, patch_name: str) -> None:
        root = self.state.parsed_roots.get(path)
        if root is None:
            return

        field_name = Path(path).name
        empty_patch = FoamNode(name=patch_name, node_type="dictionary")
        dlg = BoundaryEditDialog(field_name, patch_name, empty_patch, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        content = dlg.new_dict_text.strip()
        if not content:
            return
        try:
            new_children = _parse_patch_content(content)
        except Exception as e:
            QMessageBox.warning(
                self, tr("Parse Error"), tr("Could not parse patch content:\n{e}").format(e=e)
            )
            return

        boundary_field = _find_boundary_field(root)
        if boundary_field is None:
            QMessageBox.warning(
                self, tr("Error"), tr("No boundaryField found in {field}.").format(field=field_name)
            )
            return

        self._checkpoint_for_undo([path])
        new_patch = _append_new_patch(boundary_field, patch_name)
        _set_patch_children(new_patch, new_children)

        self._apply_boundary_root_change(path, root)
        self.statusBar().showMessage(
            tr("Created boundary: {field} / {patch}").format(field=field_name, patch=patch_name),
            _STATUS_SHORT,
        )

    def _on_patch_paste_requested(self, path: str, patch_name: str, content: str) -> None:
        root = self.state.parsed_roots.get(path)
        if root is None:
            return
        try:
            new_children = _parse_patch_content(content)
        except Exception as e:
            QMessageBox.warning(
                self, tr("Paste Error"), tr("Could not parse copied content:\n{e}").format(e=e)
            )
            return

        live_patch = extract_boundary(root).get(patch_name)
        if live_patch is None:
            boundary_field = _find_boundary_field(root)
            if boundary_field is None:
                QMessageBox.warning(
                    self, tr("Paste Error"), tr("No boundaryField in {file}.").format(file=Path(path).name)
                )
                return
            self._checkpoint_for_undo([path])
            live_patch = _append_new_patch(boundary_field, patch_name)
        else:
            self._checkpoint_for_undo([path])

        _set_patch_children(live_patch, new_children)

        self._apply_boundary_root_change(path, root)
        self.statusBar().showMessage(
            tr("Pasted to {file} / {patch}").format(file=Path(path).name, patch=patch_name),
            _STATUS_SHORT,
        )

    def _on_patch_delete_requested(self, path: str, patch_name: str) -> None:
        root = self.state.parsed_roots.get(path)
        if root is None:
            return
        boundary_field = _find_boundary_field(root)
        if boundary_field is None:
            return
        patch_node = next((c for c in boundary_field.children if c.name == patch_name), None)
        if patch_node is None:
            return

        self._checkpoint_for_undo([path])
        boundary_field.children.remove(patch_node)
        boundary_field.modified = True

        self._apply_boundary_root_change(path, root)
        self.boundary_panel.refresh()
        self.statusBar().showMessage(
            tr("Deleted boundary: {file} / {patch}").format(file=Path(path).name, patch=patch_name),
            _STATUS_SHORT,
        )

    def _on_rename_boundary_by_name(self, old_name: str) -> None:
        # Ensure all loaded files are parsed
        for path in list(self.state.file_buffers):
            if path not in self.state.parsed_roots:
                self._cache_parsed_root(path)

        # Use the live current_root for the open file
        roots: dict[str, FoamNode] = dict(self.state.parsed_roots)
        if self.state.current_file and self.state.current_root is not None:
            roots[self.state.current_file] = self.state.current_root

        targets = find_rename_targets(old_name, roots)

        dlg = RenameBoundaryDialog(old_name, targets, self.state.current_case_dir or "", self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        new_name = dlg.new_name
        selected = set(dlg.selected_paths)

        self._checkpoint_for_undo(sorted(selected))
        for path in selected:
            root = roots.get(path)
            if root is None:
                continue
            for n in targets.get(path, []):
                n.name = new_name
                n.modified = True
            self._apply_boundary_root_change(path, root)

        self.boundary_panel.refresh()
        self.statusBar().showMessage(
            tr("Renamed '{old}' → '{new}' in {n} file(s).").format(
                old=old_name, new=new_name, n=len(selected)
            ),
            _STATUS_NORMAL,
        )

    def _on_patch_selected(self, path: str, patch_name: str) -> None:
        if path != self.state.current_file:
            self.load_selected_file(path)
            self.file_list_panel.select_file(path)
        self.editor_panel.jump_to_text(patch_name)

    def _apply_boundary_root_change(self, path: str, root: FoamNode) -> None:
        text = self._write_root_to_buffer(path, root)
        if path == self.state.current_file:
            self.editor_panel.set_text(text)
            self._load_tree(root)
        self.boundary_panel.update_field(path, root)

    def _on_patch_delete_all_requested(self, patch_name: str) -> None:
        affected = [
            path for path, root in self.state.parsed_roots.items()
            if patch_name in extract_boundary(root)
        ]
        if not affected:
            return

        file_list = "\n".join(f"  • {Path(p).name}" for p in sorted(affected, key=lambda p: Path(p).name))
        if not self._confirm(
            tr("Delete BoundaryField"),
            tr("Delete '{patch}' from {n} file(s)?\n\n{files}").format(
                patch=patch_name, n=len(affected), files=file_list
            ),
        ):
            return

        self._checkpoint_for_undo(sorted(affected))
        for path in affected:
            root = self.state.parsed_roots[path]
            boundary_field = _find_boundary_field(root)
            if boundary_field is None:
                continue
            patch_node = next((c for c in boundary_field.children if c.name == patch_name), None)
            if patch_node is None:
                continue
            boundary_field.children.remove(patch_node)
            boundary_field.modified = True
            self._apply_boundary_root_change(path, root)

        self.boundary_panel.refresh()
        self.statusBar().showMessage(
            tr("Deleted BoundaryField '{patch}' from {n} file(s).").format(
                patch=patch_name, n=len(affected)
            ),
            _STATUS_SHORT,
        )

    def _on_patch_add_all_requested(self, patch_name: str) -> None:
        targets = [
            path for path, root in self.state.parsed_roots.items()
            if patch_name not in extract_boundary(root)
            and _find_boundary_field(root) is not None
        ]
        if not targets:
            return

        if not self._confirm(
            tr("Add BoundaryField"),
            tr(
                "An empty entry will be added to {n} field file(s).\n"
                "Edit each cell to add boundary condition content.\n\n"
                "Proceed?"
            ).format(n=len(targets)),
        ):
            return

        self._checkpoint_for_undo(sorted(targets))
        added: list[str] = []
        for path in targets:
            root = self.state.parsed_roots[path]
            boundary_field = _find_boundary_field(root)
            if boundary_field is None:
                continue

            _append_new_patch(boundary_field, patch_name)
            self._apply_boundary_root_change(path, root)
            added.append(path)

        if added:
            self.boundary_panel.refresh()
            self.statusBar().showMessage(
                tr(
                    "Added BoundaryField '{patch}' to {n} file(s). "
                    "Edit each cell to add boundary condition content."
                ).format(patch=patch_name, n=len(added)),
                _STATUS_NORMAL,
            )
