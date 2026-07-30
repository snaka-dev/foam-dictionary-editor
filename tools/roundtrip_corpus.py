#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Count how many tutorial dictionaries survive a parse/write round trip byte for byte.

This is the measurement behind the round-trip figure quoted in RELEASE_NOTES.md.
It exists so that figure can be re-derived rather than taken on trust: run it
against an OpenFOAM installation and it prints the corpus size, how much of it
the parser accepts, and how much of that writes back identical.

Usage:
    # explicit installation root:
    python3 tools/roundtrip_corpus.py --dir /usr/lib/openfoam/openfoam2512

    # or from the sourced environment / a discovered installation:
    python3 tools/roundtrip_corpus.py

    # list the files that differ, to see what a change left behind:
    python3 tools/roundtrip_corpus.py --dir ... --list-differing

The corpus is every UTF-8 readable regular file under a tutorial case's
`system/`, `constant/`, `0/` or `0.orig/` directory, searched recursively.
Symlinks are skipped so a file shared between `0/` and `0.orig/` is counted
once. No filter on filename or content is applied beyond that: "parseable" is
whatever OpenFoamParser accepts, which is the number that matters here.
"""
from __future__ import annotations

import argparse
import sys
from collections.abc import Iterator
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from foam.parser import OpenFoamParser  # noqa: E402
from foam.writer import write_root  # noqa: E402
from services.example_search import discover_installations  # noqa: E402

CASE_DIRS = frozenset({"system", "constant", "0", "0.orig"})


def corpus_files(tutorials: Path) -> Iterator[Path]:
    """Yield every regular file under a case's system/constant/0/0.orig."""
    for path in sorted(tutorials.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        if CASE_DIRS.isdisjoint(path.relative_to(tutorials).parts[:-1]):
            continue
        yield path


def measure(tutorials: Path) -> tuple[int, int, list[Path]]:
    """Return (corpus size, parseable count, files that did not round-trip)."""
    total = parseable = 0
    differing: list[Path] = []

    for path in corpus_files(tutorials):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        total += 1
        try:
            written = write_root(OpenFoamParser(text).parse())
        except Exception:  # noqa: BLE001 -- any parse failure just leaves it out
            continue
        parseable += 1
        if written != text:
            differing.append(path)

    return total, parseable, differing


def resolve_tutorials(install_dir: Path | None) -> Path:
    if install_dir is not None:
        tutorials = install_dir / "tutorials"
        if not tutorials.is_dir():
            raise RuntimeError(f"No tutorials directory under {install_dir}")
        return tutorials

    for installation in discover_installations():
        if installation.tutorials_dir is not None:
            return installation.tutorials_dir
    raise RuntimeError(
        "No OpenFOAM installation with a tutorials directory found. "
        "Pass --dir, or source an OpenFOAM etc/bashrc first."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--dir",
        type=Path,
        default=None,
        metavar="INSTALL_ROOT",
        help="OpenFOAM installation root (e.g. /usr/lib/openfoam/openfoam2512); "
        "defaults to the sourced environment or a discovered installation",
    )
    parser.add_argument(
        "--list-differing",
        action="store_true",
        help="print the path of every file that did not round-trip",
    )
    args = parser.parse_args()

    try:
        tutorials = resolve_tutorials(args.dir)
    except RuntimeError as exc:
        print(exc)
        sys.exit(1)

    print(f"Corpus: {tutorials}")
    total, parseable, differing = measure(tutorials)
    identical = parseable - len(differing)

    print(f"  files in system/, constant/, 0/, 0.orig/ : {total}")
    print(f"  parsed without error                     : {parseable}")
    print(f"  written back byte-identical              : {identical}")
    if parseable:
        print(f"  round-trip rate                          : {identical / parseable:.2%}")

    if args.list_differing and differing:
        print(f"\n{len(differing)} file(s) did not round-trip:")
        for path in differing:
            print(f"  {path}")


if __name__ == "__main__":
    main()
