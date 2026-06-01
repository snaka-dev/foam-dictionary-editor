# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QDialog, QMessageBox

from foam.nodes import FoamNode
from foam.parser import OpenFoamParser
from foam.utils import read_foam_file
from foam.writer import write_root
from services.case_loader import FIELD_DIRS
from i18n import tr
from ui.layout_constants import (
    STATUS_NORMAL as _STATUS_NORMAL,
    STATUS_SHORT as _STATUS_SHORT,
)


class _BoundaryOpsMixin:
    """Boundary view population and patch-level edit operations."""

    # ── panel population ──────────────────────────────────────────────────────

    def _available_field_dirs(self) -> list[str]:
        if not self.current_case_dir:
            return []
        return [d for d in FIELD_DIRS if (Path(self.current_case_dir) / d).is_dir()]

    def _cache_parsed_root(self, path: str) -> FoamNode | None:
        text = self.file_buffers.get(path)
        if text is None:
            try:
                text = read_foam_file(path)
            except OSError:
                return None
        try:
            root = OpenFoamParser(text).parse()
            self._parsed_roots[path] = root
            return root
        except Exception:
            return None

    def _reload_boundary_panel(self) -> None:
        if not self.current_case_dir:
            self.boundary_panel.clear()
            return
        available = self._available_field_dirs()
        if not available:
            self.boundary_panel.clear()
            return
        field_roots: dict[str, FoamNode] = {}
        for dir_name in available:
            d = Path(self.current_case_dir) / dir_name
            if not d.is_dir():
                continue
            for p in sorted(d.iterdir(), key=lambda x: x.name.lower()):
                if p.is_file():
                    path = str(p)
                    if path not in self._parsed_roots:
                        self._cache_parsed_root(path)
                    root = self._parsed_roots.get(path)
                    if root is not None:
                        field_roots[path] = root

        case_base = Path(self.current_case_dir)
        dirs_with_fields = [
            d for d in available
            if any(Path(p).parent == case_base / d for p in field_roots)
        ]
        if not dirs_with_fields:
            self.boundary_panel.clear()
            return
        self.boundary_panel.load_case(field_roots, self.current_case_dir, dirs_with_fields)

    # ── patch edit signals ────────────────────────────────────────────────────

    def _on_patch_edit_requested(self, path: str, patch_name: str, patch_node: object) -> None:
        from ui.boundary_edit_dialog import BoundaryEditDialog, _parse_patch_content, _patch_inner_text
        from ui.boundary_view_panel import _extract_boundary

        root = self._parsed_roots.get(path)
        if root is None:
            return

        live_patch = _extract_boundary(root).get(patch_name)
        if live_patch is None:
            QMessageBox.warning(
                self, tr("Boundary Not Found"),
                tr("Patch '{name}' not found in {file}.").format(name=patch_name, file=Path(path).name),
            )
            return

        field_name = Path(path).name
        original_text = _patch_inner_text(live_patch)
        dlg = BoundaryEditDialog(field_name, patch_name, live_patch, self)
        if dlg.exec() != QDialog.Accepted:
            return

        new_type = dlg.new_type

        if dlg.is_complex_mode:
            type_node = next((c for c in live_patch.children if c.name == "type"), None)
            current_type = str(type_node.value) if type_node and type_node.value is not None else ""
            if not new_type or new_type == current_type:
                return
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
                QMessageBox.warning(self, tr("Parse Error"), tr("Could not parse patch content:\n{e}").format(e=e))
                return
            live_patch.children = new_children
            for child in new_children:
                child.parent = live_patch
            live_patch.modified = True
            live_patch.raw_text = ""

        self._apply_boundary_root_change(path, root)
        self.statusBar().showMessage(tr("Boundary updated: {file} / {patch}").format(file=Path(path).name, patch=patch_name), _STATUS_SHORT)

    def _on_patch_create_requested(self, path: str, patch_name: str) -> None:
        from ui.boundary_edit_dialog import BoundaryEditDialog, _parse_patch_content
        from ui.boundary_view_panel import _extract_boundary

        root = self._parsed_roots.get(path)
        if root is None:
            return

        field_name = Path(path).name
        empty_patch = FoamNode(name=patch_name, node_type="dictionary")
        dlg = BoundaryEditDialog(field_name, patch_name, empty_patch, self)
        if dlg.exec() != QDialog.Accepted:
            return

        content = dlg.new_dict_text.strip()
        if not content:
            return
        try:
            new_children = _parse_patch_content(content)
        except Exception as e:
            QMessageBox.warning(self, tr("Parse Error"), tr("Could not parse patch content:\n{e}").format(e=e))
            return

        boundary_field = next(
            (n for n in root.children if n.name == "boundaryField" and n.node_type == "dictionary"),
            None,
        )
        if boundary_field is None:
            QMessageBox.warning(self, tr("Error"), tr("No boundaryField found in {field}.").format(field=field_name))
            return

        new_patch = FoamNode(name=patch_name, node_type="dictionary", modified=True)
        new_patch.leading_trivia = ["\n"]
        new_patch.parent = boundary_field
        new_patch.children = new_children
        for child in new_children:
            child.parent = new_patch
        boundary_field.children.append(new_patch)
        boundary_field.modified = True

        self._apply_boundary_root_change(path, root)
        self.statusBar().showMessage(tr("Created boundary: {field} / {patch}").format(field=field_name, patch=patch_name), _STATUS_SHORT)

    def _on_patch_paste_requested(self, path: str, patch_name: str, content: str) -> None:
        from ui.boundary_edit_dialog import _parse_patch_content
        from ui.boundary_view_panel import _extract_boundary

        root = self._parsed_roots.get(path)
        if root is None:
            return
        try:
            new_children = _parse_patch_content(content)
        except Exception as e:
            QMessageBox.warning(self, tr("Paste Error"), tr("Could not parse copied content:\n{e}").format(e=e))
            return

        live_patch = _extract_boundary(root).get(patch_name)
        if live_patch is None:
            boundary_field = next(
                (n for n in root.children if n.name == "boundaryField" and n.node_type == "dictionary"),
                None,
            )
            if boundary_field is None:
                QMessageBox.warning(self, tr("Paste Error"), tr("No boundaryField in {file}.").format(file=Path(path).name))
                return
            live_patch = FoamNode(name=patch_name, node_type="dictionary", modified=True)
            live_patch.leading_trivia = ["\n"]
            live_patch.parent = boundary_field
            boundary_field.children.append(live_patch)
            boundary_field.modified = True

        live_patch.children = new_children
        for child in new_children:
            child.parent = live_patch
        live_patch.modified = True
        live_patch.raw_text = ""

        self._apply_boundary_root_change(path, root)
        self.statusBar().showMessage(tr("Pasted to {file} / {patch}").format(file=Path(path).name, patch=patch_name), _STATUS_SHORT)

    def _on_patch_delete_requested(self, path: str, patch_name: str) -> None:
        from ui.boundary_view_panel import _extract_boundary

        root = self._parsed_roots.get(path)
        if root is None:
            return
        boundary_field = next(
            (n for n in root.children if n.name == "boundaryField" and n.node_type == "dictionary"),
            None,
        )
        if boundary_field is None:
            return
        patch_node = next((c for c in boundary_field.children if c.name == patch_name), None)
        if patch_node is None:
            return

        boundary_field.children.remove(patch_node)
        boundary_field.modified = True

        self._apply_boundary_root_change(path, root)
        self.boundary_panel.refresh()
        self.statusBar().showMessage(tr("Deleted boundary: {file} / {patch}").format(file=Path(path).name, patch=patch_name), _STATUS_SHORT)

    def _on_rename_boundary_by_name(self, old_name: str) -> None:
        from ui.rename_boundary_dialog import RenameBoundaryDialog, find_rename_targets

        # Ensure all loaded files are parsed
        for path in list(self.file_buffers):
            if path not in self._parsed_roots:
                self._cache_parsed_root(path)

        # Use the live current_root for the open file
        roots: dict[str, FoamNode] = dict(self._parsed_roots)
        if self.current_file and self.current_root is not None:
            roots[self.current_file] = self.current_root

        targets = find_rename_targets(old_name, roots)

        dlg = RenameBoundaryDialog(old_name, targets, self.current_case_dir or "", self)
        if dlg.exec() != QDialog.Accepted:
            return

        new_name = dlg.new_name
        selected = set(dlg.selected_paths)

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
            tr("Renamed '{old}' → '{new}' in {n} file(s).").format(old=old_name, new=new_name, n=len(selected)),
            _STATUS_NORMAL,
        )

    def _on_patch_selected(self, path: str, patch_name: str) -> None:
        if path != self.current_file:
            self.load_selected_file(path)
            self.file_list_panel.select_file(path)
        self.editor_panel.jump_to_text(patch_name)

    def _apply_boundary_root_change(self, path: str, root) -> None:
        text = write_root(root)
        self.file_buffers[path] = text
        self._mark_path_dirty(path)
        if path == self.current_file:
            self.editor_panel.set_text(text)
            self._load_tree(root)
        self.boundary_panel.update_field(path, root)

    def _on_patch_delete_all_requested(self, patch_name: str) -> None:
        from ui.boundary_view_panel import _extract_boundary

        affected = [
            path for path, root in self._parsed_roots.items()
            if patch_name in _extract_boundary(root)
        ]
        if not affected:
            return

        file_list = "\n".join(f"  • {Path(p).name}" for p in sorted(affected, key=lambda p: Path(p).name))
        reply = QMessageBox.question(
            self,
            tr("Delete BoundaryField"),
            tr("Delete '{patch}' from {n} file(s)?\n\n{files}").format(patch=patch_name, n=len(affected), files=file_list),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        for path in affected:
            root = self._parsed_roots[path]
            boundary_field = next(
                (n for n in root.children if n.name == "boundaryField" and n.node_type == "dictionary"),
                None,
            )
            if boundary_field is None:
                continue
            patch_node = next((c for c in boundary_field.children if c.name == patch_name), None)
            if patch_node is None:
                continue
            boundary_field.children.remove(patch_node)
            boundary_field.modified = True
            self._apply_boundary_root_change(path, root)

        self.boundary_panel.refresh()
        self.statusBar().showMessage(tr("Deleted BoundaryField '{patch}' from {n} file(s).").format(patch=patch_name, n=len(affected)), _STATUS_SHORT)

    def _on_patch_add_all_requested(self, patch_name: str) -> None:
        from ui.boundary_view_panel import _extract_boundary

        targets = [
            path for path, root in self._parsed_roots.items()
            if patch_name not in _extract_boundary(root)
            and any(
                n.name == "boundaryField" and n.node_type == "dictionary"
                for n in root.children
            )
        ]
        if not targets:
            return

        reply = QMessageBox.question(
            self,
            tr("Add BoundaryField"),
            tr("An empty entry will be added to {n} field file(s).\nEdit each cell to add boundary condition content.\n\nProceed?").format(n=len(targets)),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        added: list[str] = []
        for path in targets:
            root = self._parsed_roots[path]
            boundary_field = next(
                (n for n in root.children if n.name == "boundaryField" and n.node_type == "dictionary"),
                None,
            )
            if boundary_field is None:
                continue

            new_patch = FoamNode(name=patch_name, node_type="dictionary", modified=True)
            new_patch.leading_trivia = ["\n"]
            new_patch.parent = boundary_field
            boundary_field.children.append(new_patch)
            boundary_field.modified = True
            self._apply_boundary_root_change(path, root)
            added.append(path)

        if added:
            self.boundary_panel.refresh()
            self.statusBar().showMessage(
                tr("Added BoundaryField '{patch}' to {n} file(s). Edit each cell to add boundary condition content.").format(patch=patch_name, n=len(added)),
                _STATUS_NORMAL,
            )
