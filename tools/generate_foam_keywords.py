#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Generate app_config/foam_keywords.json from an OpenFOAM installation.

Usage:
    source /opt/openfoam*/etc/bashrc   # source your OpenFOAM environment
    python3 tools/generate_foam_keywords.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app_config.keyword_generator import generate  # noqa: E402


def main() -> None:
    try:
        count, path = generate(progress=print)
        print(f"\nWrote {count} keywords → {path}")
    except RuntimeError as exc:
        print(f"\n{exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
