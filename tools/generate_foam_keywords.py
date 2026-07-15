#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Generate app_config/foam_keywords.json from an OpenFOAM installation.

Usage:
    # explicit installation root (no environment sourcing needed):
    python3 tools/generate_foam_keywords.py --dir /usr/lib/openfoam/openfoam2512

    # or from the sourced environment:
    source /opt/openfoam*/etc/bashrc
    python3 tools/generate_foam_keywords.py

The output overrides the shipped app_config/foam_keywords.default.json.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app_config.keyword_generator import generate  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--dir",
        type=Path,
        default=None,
        metavar="INSTALL_ROOT",
        help="OpenFOAM installation root (e.g. /usr/lib/openfoam/openfoam2512); "
        "defaults to the sourced environment (WM_PROJECT_DIR etc.)",
    )
    args = parser.parse_args()

    try:
        count, path = generate(progress=print, project_dir=args.dir)
        print(f"\nWrote {count} keywords → {path}")
        print("This user-generated file overrides the bundled foam_keywords.default.json.")
    except RuntimeError as exc:
        print(f"\n{exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
