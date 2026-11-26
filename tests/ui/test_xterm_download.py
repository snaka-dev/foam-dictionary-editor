# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""The xterm.js download is installed only when every file has its pinned hash.

The terminal page has a QWebChannel bridge that writes straight to the shell,
so whoever controls that JavaScript controls the user's account. No network:
``fetch`` is replaced by a function writing known bytes.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from ui.widgets import _xterm_widget as xw


def _pin_to(monkeypatch, contents: dict[str, bytes]) -> None:
    """Pin the expected hashes to *contents*, keeping the real names and URLs."""
    files = tuple(
        (name, url, hashlib.sha256(contents[name]).hexdigest())
        for name, url, _digest in xw._XTERM_FILES
    )
    monkeypatch.setattr(xw, "_XTERM_FILES", files)


def _fetcher(contents: dict[str, bytes], tamper: str | None = None):
    by_url = {url: name for name, url, _ in xw._XTERM_FILES}

    def fetch(url: str, dest: Path) -> None:
        name = by_url[url]
        data = contents[name] + (b"// evil" if name == tamper else b"")
        Path(dest).write_bytes(data)

    return fetch


CONTENTS = {"xterm.js": b"js", "xterm.css": b"css", "xterm-addon-fit.js": b"fit"}


def test_pinned_hashes_cover_every_downloaded_file():
    names = [name for name, _, _ in xw._XTERM_FILES]
    assert names == ["xterm.js", "xterm.css", "xterm-addon-fit.js"]
    for _name, url, digest in xw._XTERM_FILES:
        assert url.startswith("https://")
        assert len(digest) == 64 and int(digest, 16) >= 0


def test_matching_download_is_installed(monkeypatch, tmp_path):
    _pin_to(monkeypatch, CONTENTS)
    target = tmp_path / "xterm"
    assert xw.download_xterm_files(target, fetch=_fetcher(CONTENTS)) is True
    assert xw.xterm_files_valid(target)
    assert (target / "version.txt").read_text() == xw._XTERM_VERSION


def test_tampered_download_is_discarded(monkeypatch, tmp_path):
    _pin_to(monkeypatch, CONTENTS)
    target = tmp_path / "xterm"
    ok = xw.download_xterm_files(target, fetch=_fetcher(CONTENTS, tamper="xterm.js"))
    assert ok is False
    assert not target.exists()


def test_tampered_download_leaves_a_good_install_alone(monkeypatch, tmp_path):
    _pin_to(monkeypatch, CONTENTS)
    target = tmp_path / "xterm"
    xw.download_xterm_files(target, fetch=_fetcher(CONTENTS))
    xw.download_xterm_files(target, fetch=_fetcher(CONTENTS, tamper="xterm.css"))
    assert xw.xterm_files_valid(target)


def test_failed_fetch_installs_nothing(monkeypatch, tmp_path):
    _pin_to(monkeypatch, CONTENTS)

    def fetch(url, dest):
        raise OSError("offline")

    target = tmp_path / "xterm"
    assert xw.download_xterm_files(target, fetch=fetch) is False
    assert not target.exists()


def test_a_file_changed_after_download_is_not_valid(monkeypatch, tmp_path):
    _pin_to(monkeypatch, CONTENTS)
    target = tmp_path / "xterm"
    xw.download_xterm_files(target, fetch=_fetcher(CONTENTS))
    (target / "xterm-addon-fit.js").write_bytes(b"changed")
    assert not xw.xterm_files_valid(target)
    (target / "xterm-addon-fit.js").unlink()
    assert not xw.xterm_files_valid(target)
