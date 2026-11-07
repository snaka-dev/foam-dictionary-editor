#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Write the Japanese caption track for each demo movie.

    python3 tools/make_ja_srt.py            # every docs/demo/<scene>.srt
    python3 tools/make_ja_srt.py --check    # exit 1 if any .ja.srt is stale

`tools/demo_driver.py` writes `docs/demo/<scene>.srt` from the scene's English
narration, timed to the take. The Japanese track keeps those timings and takes
its text from the Narration column of `docs/DEMO_SCRIPTS_ja.md`: each English
cue is found, word for word, in the same movie's table in `docs/DEMO_SCRIPTS.md`,
and the row in the same position of the Japanese table supplies the line. So
the two scripts stay the one source of the narration, and a retake needs only
this re-run.

A cue that matches no row is an error rather than a guess -- it means the
script and the recording have drifted, and a caption out of step with the
picture is worse than none.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "docs" / "demo"
SCRIPT_EN = ROOT / "docs" / "DEMO_SCRIPTS.md"
SCRIPT_JA = ROOT / "docs" / "DEMO_SCRIPTS_ja.md"

_ROW_RE = re.compile(r"^\| \d+:\d\d \|")
# Table cells are separated by '|' that is not escaped as '\|'.
_CELL_SPLIT = re.compile(r"(?<!\\)\|")


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\\|", "|")).strip()


def narration_tables(path: Path, heading: str, scene_label: str) -> dict[str, list[str]]:
    """Each movie's Narration column, keyed by scene name, in row order."""
    text = path.read_text(encoding="utf-8")
    starts = [m.start() for m in re.finditer(rf"^## {heading} \d+ ", text, re.MULTILINE)]
    tables: dict[str, list[str]] = {}
    for i, start in enumerate(starts):
        end = text.find("\n## ", start + 3)
        section = text[start:end if end != -1 else len(text)]
        scene = re.search(rf"\*\*{scene_label}:\*\* `([^`]+)`", section)
        if scene is None:
            raise SystemExit(f"{path.name}: movie section {i + 1} names no scene")
        rows = []
        for line in section.splitlines():
            if _ROW_RE.match(line):
                cells = _CELL_SPLIT.split(line)[1:-1]
                rows.append(_normalise(cells[-1]))
        tables[scene.group(1)] = rows
    return tables


def read_srt(path: Path) -> list[tuple[str, str]]:
    """(timing line, text) per cue."""
    cues = []
    for block in path.read_text(encoding="utf-8").strip().split("\n\n"):
        lines = block.split("\n")
        cues.append((lines[1], " ".join(lines[2:])))
    return cues


def japanese_srt(scene: str, en_srt: Path, en: dict[str, list[str]], ja: dict[str, list[str]]) -> str:
    rows_en, rows_ja = en.get(scene), ja.get(scene)
    if rows_en is None or rows_ja is None:
        missing = SCRIPT_EN if rows_en is None else SCRIPT_JA
        raise SystemExit(f"{scene}: no script table in {missing.name}")
    if len(rows_en) != len(rows_ja):
        raise SystemExit(f"{scene}: {len(rows_en)} rows in English, {len(rows_ja)} in Japanese")
    out = []
    for n, (timing, text) in enumerate(read_srt(en_srt), start=1):
        try:
            row = rows_en.index(_normalise(text))
        except ValueError:
            raise SystemExit(f"{scene}: cue {n} is in no row of DEMO_SCRIPTS.md: {text[:70]!r}")
        line = rows_ja[row]
        if not line:
            raise SystemExit(f"{scene}: row {row + 1} has no Japanese narration")
        out.append(f"{n}\n{timing}\n{line}\n")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="report stale tracks; write nothing")
    args = parser.parse_args(argv)
    en = narration_tables(SCRIPT_EN, "Movie", "Scene")
    ja = narration_tables(SCRIPT_JA, "動画", "シーン")
    stale = 0
    for en_srt in sorted(DEMO_DIR.glob("*.srt")):
        if en_srt.name.endswith(".ja.srt"):
            continue
        scene = en_srt.stem
        target = en_srt.with_name(f"{scene}.ja.srt")
        text = japanese_srt(scene, en_srt, en, ja)
        current = target.read_text(encoding="utf-8") if target.exists() else None
        if current == text:
            continue
        if args.check:
            print(f"stale: {target.relative_to(ROOT)}")
            stale += 1
        else:
            target.write_text(text, encoding="utf-8")
            print(f"→ {target.relative_to(ROOT)}")
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
