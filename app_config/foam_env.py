# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Resolve OpenFOAM installation directories from the sourced environment.

Single source of truth for reading ``WM_PROJECT_DIR`` / ``FOAM_*`` variables,
shared by ``services/example_search.py`` (installation discovery),
``app_config/keyword_generator.py`` (etc/src/applications scan roots), and
``AppConfigManager.foam_tutorials_dir`` (case library). Pure stdlib, no Qt.
Lives in ``app_config/`` rather than ``services/`` because it has no
dependency on the ``services`` layer; see DEVELOPER.md's architecture
overview for the layering.
"""
from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FoamEnvDirs:
    """Validated directories of the sourced OpenFOAM environment.

    Every field is None unless the resolved directory actually exists; the
    ``project_dir/<sub>`` fallbacks apply only when the specific variable is
    unset (or invalid) and ``project_dir`` itself is valid.
    """

    project_dir: Path | None    # $WM_PROJECT_DIR
    tutorials_dir: Path | None  # $FOAM_TUTORIALS, else project_dir/"tutorials"
    etc_dir: Path | None        # $FOAM_ETC, else project_dir/"etc"
    src_dir: Path | None        # $FOAM_SRC, else project_dir/"src"
    apps_dir: Path | None       # $FOAM_APP, else project_dir/"applications"
    version: str | None         # $WM_PROJECT_VERSION, else project_dir.name


def _env_dir(env: Mapping[str, str], key: str) -> Path | None:
    """Return the env value as an existing directory, or None (Path('') is cwd)."""
    value = env.get(key, "").strip()
    if not value:
        return None
    path = Path(value)
    return path if path.is_dir() else None


def foam_env_dirs(env: Mapping[str, str] | None = None) -> FoamEnvDirs:
    """Read the OpenFOAM environment variables into a FoamEnvDirs.

    ``env`` defaults to ``os.environ``; pass a mapping in tests.
    """
    if env is None:
        env = os.environ
    project = _env_dir(env, "WM_PROJECT_DIR")

    def _resolve(key: str, sub: str) -> Path | None:
        explicit = _env_dir(env, key)
        if explicit is not None:
            return explicit
        if project is not None and (project / sub).is_dir():
            return project / sub
        return None

    version = env.get("WM_PROJECT_VERSION", "").strip() or (
        project.name if project is not None else None
    )
    return FoamEnvDirs(
        project_dir=project,
        tutorials_dir=_resolve("FOAM_TUTORIALS", "tutorials"),
        etc_dir=_resolve("FOAM_ETC", "etc"),
        src_dir=_resolve("FOAM_SRC", "src"),
        apps_dir=_resolve("FOAM_APP", "applications"),
        version=version,
    )
