# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath

from app_config.json_io import load_json, save_json
from services.case_paths import case_root_changed

_CONFIG_FILENAME = ".foam-editor-files.json"

# (relative path, recursive)
DirEntry = tuple[str, bool]


def is_inside_case(rel_path: str) -> bool:
    """True when *rel_path* names something under the case directory, read lexically.

    ``.foam-editor-files.json`` travels inside a case, so a case from someone else
    decides what is in it. ``Path(case) / "/home/u/.ssh/id_rsa"`` is that absolute
    path, and ``case/../../x`` climbs out, so either would put an outside file in
    the file list -- and Duplicate Case, which copies ``source/rel`` to
    ``dest/rel``, would write outside the new case. Every path FoDE itself stores
    comes from ``relative_to(case)`` and passes. Both path flavours are checked so
    a config written on one platform is judged the same way on the other.
    """
    if not rel_path or "\0" in rel_path:
        return False
    for flavour in (PurePosixPath, PureWindowsPath):
        p = flavour(rel_path)
        if p.is_absolute() or p.anchor or ".." in p.parts:
            return False
    return True


class CaseFilesConfig:
    """Manages per-case extra file/directory list stored in .foam-editor-files.json."""

    def __init__(self, case_dir: str):
        self._case_dir = case_dir
        self._path = Path(case_dir) / _CONFIG_FILENAME
        self._extra_files: list[str] = []
        self._extra_dirs: list[DirEntry] = []
        # rel path -> viewer overlay key, for files whose name and FoamFile header do not
        # identify them (a renamed sampling dict has no header at all). Case-relative like
        # the lists above, so the override travels inside a case directory that is moved.
        self._viewer_kinds: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        data = load_json(self._path)
        if data is None:
            self._extra_files = []
            self._extra_dirs = []
            self._viewer_kinds = {}
            return
        # Entries that leave the case are dropped, not just skipped at use: a
        # later save() then writes the file back without them.
        self._extra_files = [
            str(f) for f in data.get("extra_files", []) if is_inside_case(str(f))
        ]
        self._viewer_kinds = {
            str(k): str(v) for k, v in (data.get("viewer_kinds") or {}).items() if v
        }
        self._extra_dirs = []
        for d in data.get("extra_dirs", []):
            if isinstance(d, dict):
                entry = (str(d.get("path", "")), bool(d.get("recursive", False)))
            else:
                # Backward compat: old format stored plain strings (non-recursive).
                entry = (str(d), False)
            if is_inside_case(entry[0]):
                self._extra_dirs.append(entry)

    def save(self) -> bool:
        """Write the file. False, writing nothing, when the case folder is no
        longer the one that was opened (see ``case_paths.pin_case_root``)."""
        if case_root_changed(self._case_dir):
            return False
        data: dict = {"extra_files": self._extra_files}
        if self._viewer_kinds:
            data["viewer_kinds"] = dict(self._viewer_kinds)
        if self._extra_dirs:
            data["extra_dirs"] = [
                {"path": p, "recursive": r} for p, r in self._extra_dirs
            ]
        save_json(self._path, data)
        return True

    def get_extra_files(self) -> list[str]:
        return list(self._extra_files)

    def add_file(self, rel_path: str) -> None:
        if is_inside_case(rel_path) and rel_path not in self._extra_files:
            self._extra_files.append(rel_path)

    def remove_file(self, rel_path: str) -> None:
        if rel_path in self._extra_files:
            self._extra_files.remove(rel_path)

    def get_extra_dirs(self) -> list[DirEntry]:
        return list(self._extra_dirs)

    def add_dir(self, rel_path: str, recursive: bool = False) -> None:
        if not is_inside_case(rel_path):
            return
        for i, (p, _) in enumerate(self._extra_dirs):
            if p == rel_path:
                self._extra_dirs[i] = (rel_path, recursive)
                return
        self._extra_dirs.append((rel_path, recursive))

    def remove_dir(self, rel_path: str) -> None:
        self._extra_dirs = [(p, r) for p, r in self._extra_dirs if p != rel_path]

    def get_viewer_kind(self, rel_path: str) -> str:
        """The user's "show this in the 3-D view as ..." choice, or "" for automatic."""
        return self._viewer_kinds.get(rel_path, "")

    def set_viewer_kind(self, rel_path: str, kind: str) -> None:
        """Pin *rel_path* to an overlay; an empty *kind* returns it to automatic."""
        if kind:
            self._viewer_kinds[rel_path] = kind
        else:
            self._viewer_kinds.pop(rel_path, None)

    def get_viewer_kinds(self) -> dict[str, str]:
        return dict(self._viewer_kinds)

    def reset(self) -> None:
        self._extra_files = []
        self._extra_dirs = []
        self._viewer_kinds = {}

    def delete_config_file(self) -> bool:
        """Delete .foam-editor-files.json. False when it is still there.

        The caller shows a confirmation promising the file will be deleted and then
        reloads the case from disk, so a swallowed failure told the user it had worked
        and then put every entry straight back in the list a moment later.
        """
        if case_root_changed(self._case_dir):
            return False  # another folder's file; the entries stay as they are
        ok = True
        try:
            if self._path.exists():
                self._path.unlink()
        except OSError:
            ok = False
        self.reset()
        return ok

    @property
    def config_filename(self) -> str:
        return _CONFIG_FILENAME

    @property
    def exists(self) -> bool:
        return self._path.exists()
