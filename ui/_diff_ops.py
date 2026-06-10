# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFileDialog

from foam.diff import diff_trees, diff_trees_reverse
from foam.parser import OpenFoamParser
from foam.utils import read_foam_file, is_large_non_foam_file
from i18n import tr
from ui.layout_constants import (
    SPLITTER_COMPARISON_WIDTH,
    SPLITTER_DETAIL_WIDTH,
    SPLITTER_TREE_WIDTH,
    STATUS_SHORT as _STATUS_SHORT,
)


class _DiffOpsMixin:
    """Diff/comparison overlay operations: open reference case, compute diffs, clear."""

    def _on_side_by_side_toggled(self, checked: bool) -> None:
        if self.right_upper_splitter is None:
            return
        if checked:
            self.comparison_panel.show()
            self.right_upper_splitter.setSizes(
                [SPLITTER_TREE_WIDTH // 2, SPLITTER_COMPARISON_WIDTH, SPLITTER_DETAIL_WIDTH]
            )
        else:
            self.right_upper_splitter.setSizes(
                [SPLITTER_TREE_WIDTH, 0, SPLITTER_DETAIL_WIDTH]
            )
            self.comparison_panel.hide()

    def _compare_with_case(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            tr("Select Reference Case Directory"),
            self.current_case_dir or "",
        )
        if not directory:
            return
        self._diff_case_dir = directory
        name = Path(directory).name or directory
        self._diff_path_label.setText(
            tr("Comparing with: <b>{name}</b>  ({directory})").format(name=name, directory=directory)
        )
        self._diff_path_label.setTextFormat(Qt.RichText)
        self._diff_bar.show()
        self._recompute_diff()
        QTimer.singleShot(0, self._precompute_all_diff_counts)
        self._side_by_side_cb.setChecked(True)

    def _clear_diff(self) -> None:
        self._diff_case_dir = None
        self._diff_parsed_roots.clear()
        self._diff_bar.hide()
        self.current_model.clear_diff()
        self.comparison_panel.clear()
        self.file_list_panel.clear_diff_marks()
        self.file_list_panel.set_diff_filter_enabled(False)
        if self.right_upper_splitter is not None:
            self.right_upper_splitter.setSizes(
                [SPLITTER_TREE_WIDTH, 0, SPLITTER_DETAIL_WIDTH]
            )
        self.comparison_panel.hide()
        self.statusBar().showMessage(tr("Diff cleared."), _STATUS_SHORT)

    def _recompute_diff(self) -> None:
        if not self._diff_case_dir or not self.current_file or not self.current_case_dir:
            return
        try:
            rel = Path(self.current_file).relative_to(Path(self.current_case_dir))
        except ValueError:
            return
        other_path = Path(self._diff_case_dir) / rel
        other_key = str(other_path)
        if other_key not in self._diff_parsed_roots:
            if not other_path.exists():
                self.current_model.clear_diff()
                self.comparison_panel.clear()
                self.statusBar().showMessage(
                    tr("Diff: {rel} not found in reference case.").format(rel=rel), _STATUS_SHORT
                )
                return
            try:
                self._diff_parsed_roots[other_key] = OpenFoamParser(
                    read_foam_file(other_key)
                ).parse()
            except Exception:
                self.current_model.clear_diff()
                self.comparison_panel.clear()
                return
        other_root = self._diff_parsed_roots[other_key]
        diff_map = diff_trees(self.current_root, other_root)
        rev_diff_map = diff_trees_reverse(other_root, self.current_root)
        self.current_model.set_diff(diff_map)
        case_name = Path(self._diff_case_dir).name or self._diff_case_dir
        self.comparison_panel.load(other_root, rev_diff_map, case_name)
        n = len(diff_map)
        self.file_list_panel.mark_diff(self.current_file, n)
        self.statusBar().showMessage(
            tr("Diff: {n} difference{s} in {rel}.").format(n=n, s="s" if n != 1 else "", rel=rel),
            _STATUS_SHORT,
        )

    def _precompute_all_diff_counts(self) -> None:
        if not self._diff_case_dir or not self.current_case_dir:
            return
        case_path = Path(self.current_case_dir)
        diff_path = Path(self._diff_case_dir)
        paths = [
            item.data(Qt.UserRole)
            for item in (
                self.file_list_panel._list.item(i)
                for i in range(self.file_list_panel._list.count())
            )
            if item.data(Qt.UserRole)
        ]
        self._precompute_diff_step(paths, 0, case_path, diff_path)

    def _precompute_diff_step(
        self, paths: list, idx: int, case_path: Path, diff_path: Path
    ) -> None:
        if not self._diff_case_dir:
            return
        if idx >= len(paths):
            self.file_list_panel.set_diff_filter_enabled(True)
            return
        path = paths[idx]
        advance = lambda: QTimer.singleShot(  # noqa: E731
            0, lambda: self._precompute_diff_step(paths, idx + 1, case_path, diff_path)
        )
        try:
            rel = Path(path).relative_to(case_path)
        except ValueError:
            advance()
            return
        other_path = diff_path / rel
        other_key = str(other_path)
        if other_key not in self._diff_parsed_roots:
            if not other_path.exists():
                self.file_list_panel.mark_diff(path, 0)
                advance()
                return
            if is_large_non_foam_file(str(other_path))[0]:
                advance()
                return
            try:
                self._diff_parsed_roots[other_key] = OpenFoamParser(
                    read_foam_file(other_key)
                ).parse()
            except Exception:
                advance()
                return
        other_root = self._diff_parsed_roots[other_key]
        if path == self.current_file:
            a_root = self.current_root
        elif path in self._parsed_roots:
            a_root = self._parsed_roots[path]
        else:
            if is_large_non_foam_file(path)[0]:
                advance()
                return
            try:
                a_root = OpenFoamParser(read_foam_file(path)).parse()
                self._parsed_roots[path] = a_root
            except Exception:
                advance()
                return
        d = diff_trees(a_root, other_root)
        self.file_list_panel.mark_diff(path, len(d))
        advance()
