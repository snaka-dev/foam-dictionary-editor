# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""The manuals' mechanical consistency: contents, links, mirrors and counts.

These are the kinds of drift a pre-release read-through kept finding weeks
after the commit that caused them -- a section missing from the contents, a
test file missing from the coverage notes, a movie count left behind. Failing
here, in the commit that causes the drift, makes each a one-minute fix. The
judgment half (can a reader find a new feature?) is DEVELOPER.md's
pre-release checklist under "Release notes and cutting a release".
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

MANUALS = ["README.md", "USER_GUIDE.md", "DEVELOPER.md"]
MIRRORED = MANUALS + [m.replace(".md", "_ja.md") for m in MANUALS]

# The contents block of each guide, and the headings it deliberately leaves out.
CONTENTS = {
    "USER_GUIDE.md": ("## Contents", "## Where to Find Things", {"Contents"}),
    "USER_GUIDE_ja.md": ("## 目次", "\n## ", {"目次"}),
    "DEVELOPER.md": ("**Contents**", "\n## ", {"Overview"}),
    "DEVELOPER_ja.md": ("**目次**", "\n## ", {"概要"}),
}

NUMBER_WORDS = {
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
}


def _text(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def _outside_code(text: str) -> list[tuple[int, str]]:
    """(line number, line) for every line outside a fenced code block."""
    out, fenced = [], False
    for n, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            out.append((n, "```"))   # a fence line itself: not a heading, not blank
            continue
        if not fenced:
            out.append((n, line))
    return out


def _slug(heading: str) -> str:
    """GitHub's anchor for a heading: lower case, punctuation dropped, spaces to hyphens."""
    heading = re.sub(r"`|\*", "", heading.strip().lower())
    return re.sub(r"[^\w\- ]", "", heading).replace(" ", "-")


def _headings(text: str, max_level: int = 6) -> list[tuple[int, str]]:
    found = []
    for _n, line in _outside_code(text):
        m = re.match(r"(#{1,6}) (.+)", line)
        if m and len(m.group(1)) <= max_level:
            found.append((len(m.group(1)), m.group(2).strip()))
    return found


def _anchors(text: str) -> set[str]:
    """Every anchor the file defines, with GitHub's -1, -2 suffixes for repeats."""
    seen: dict[str, int] = {}
    anchors = set()
    for _level, heading in _headings(text):
        slug = _slug(heading)
        count = seen.get(slug, 0)
        anchors.add(slug if count == 0 else f"{slug}-{count}")
        seen[slug] = count + 1
    return anchors


@pytest.mark.parametrize("name", MIRRORED)
def test_every_anchor_link_resolves(name):
    text = _text(name)
    links = re.findall(r"\]\(([\w./-]*\.md)?#([^)\s]+)\)", text)
    broken = []
    for target, anchor in links:
        target_text = _text(str((ROOT / name).parent / target)) if target else text
        if anchor not in _anchors(target_text):
            broken.append(f"{target}#{anchor}")
    assert not broken, f"{name}: links to headings that do not exist: {broken}"


@pytest.mark.parametrize("name", sorted(CONTENTS))
def test_contents_lists_every_section(name):
    text = _text(name)
    start, end, exempt = CONTENTS[name]
    block = text.split(start, 1)[1]
    block = block.split(end, 1)[0] if end in block else block
    listed = set(re.findall(r"\]\(#([^)]+)\)", block))
    missing = [
        heading for level, heading in _headings(text, max_level=3)
        if level >= 2 and heading not in exempt and _slug(heading) not in listed
    ]
    assert not missing, f"{name}: sections missing from the contents: {missing}"


@pytest.mark.parametrize("name", ["USER_GUIDE.md", "DEVELOPER.md"])
def test_japanese_mirror_keeps_the_heading_levels(name):
    en = [level for level, _h in _headings(_text(name))]
    ja = [level for level, _h in _headings(_text(name.replace(".md", "_ja.md")))]
    assert len(en) == len(ja), (
        f"{name} has {len(en)} headings, its _ja mirror {len(ja)}: "
        "a section was added to one and not the other"
    )
    assert en == ja


@pytest.mark.parametrize("name", ["DEVELOPER.md", "DEVELOPER_ja.md"])
def test_coverage_notes_name_every_test_file(name):
    text = _text(name)
    on_disk = {p.name for p in (ROOT / "tests").rglob("test_*.py")}
    missing = sorted(f for f in on_disk if f"`{f}`" not in text)
    assert not missing, f"{name}'s Test coverage notes lack: {missing}"
    listed = set(re.findall(r"^- `(test_\w+\.py)`", text, flags=re.M))
    stale = sorted(listed - on_disk)
    assert not stale, f"{name}'s Test coverage notes list files that are gone: {stale}"


def test_readme_movie_count_matches_the_demo_table():
    rows = re.findall(r"^\| \d+ — ", _text("docs/DEMO_SCRIPTS.md"), flags=re.M)
    readme = _text("README.md")
    words = re.findall(r"\((\w+), on Vimeo\)|— (\w+) short walkthroughs", readme)
    said = [NUMBER_WORDS.get(a or b) for a, b in words]
    assert said and all(n == len(rows) for n in said), (
        f"README.md says {said} demo movies; docs/DEMO_SCRIPTS.md lists {len(rows)}"
    )
    ja = [
        int(a or b)
        for a, b in re.findall(r"（(\d+) 本、Vimeo）|紹介動画 (\d+) 本", _text("README_ja.md"))
    ]
    assert ja and all(n == len(rows) for n in ja), (
        f"README_ja.md says {ja} demo movies; docs/DEMO_SCRIPTS.md lists {len(rows)}"
    )


@pytest.mark.parametrize("name", MIRRORED)
def test_no_runs_of_blank_lines(name):
    runs, previous_blank = [], False
    for n, line in _outside_code(_text(name)):
        blank = line == ""
        if blank and previous_blank:
            runs.append(n)
        previous_blank = blank
    assert not runs, f"{name}: more than one blank line in a row at lines {runs}"
