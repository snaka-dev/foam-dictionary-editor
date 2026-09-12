# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""A demo take must not read or write the recording user's own settings.

`seed_app_config` sandboxes the application's `app_config.json`, but Qt keeps
its widget state in `$XDG_CONFIG_HOME/QtProject.conf` instead, and that was
neither sandboxed nor harmless: the default QFileDialog sidebar is
`["file:", home]`, so every take that opened a chooser printed the recorder's
account name into the frame -- against the rule in DEMO_SCRIPTS.md that a movie
must not show it -- and the take then wrote its own history back into the
recorder's file.

The redirect covers ParaView too, which a step launches as a child process: it
inherits `XDG_CONFIG_HOME` and so picks up the profile shipped for the take
rather than the recorder's. That is what makes `cavity-full-workflow`'s pixel
coordinates mean the same thing on another machine.

These pin the mechanism. The outcome -- what a frame actually shows -- is
checked by looking at the frames where a chooser or ParaView is on screen; see
DEVELOPER.md's "Demo recording".
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from demo_driver import (  # noqa: E402
    _isolate_qt_settings,
    _seed_file_dialog_sidebar,
    _seed_paraview_profile,
)

# ── QSettings redirection ─────────────────────────────────────────────────────

class TestIsolateQtSettings:
    def test_points_xdg_config_home_inside_the_workdir(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", "/nonexistent/sentinel")
        returned = _isolate_qt_settings(tmp_path)
        assert Path(os.environ["XDG_CONFIG_HOME"]) == returned
        assert returned.is_relative_to(tmp_path)
        assert returned.is_dir()

    def test_is_idempotent(self, tmp_path, monkeypatch):
        # seed_app_config has already made workdir/config for its own file, so
        # this must not care whether the directory is there already.
        monkeypatch.setenv("XDG_CONFIG_HOME", "/nonexistent/sentinel")
        first = _isolate_qt_settings(tmp_path)
        (first / "QtProject.conf").write_text("[FileDialog]\n", encoding="utf-8")
        assert _isolate_qt_settings(tmp_path) == first
        assert (first / "QtProject.conf").is_file()

    def test_leaves_home_alone(self, tmp_path, monkeypatch):
        # Redirecting $HOME would drop Path.home() from case_fs_ops' protected
        # paths, on the code path the case browser exercises. See DEVELOPER.md.
        monkeypatch.setenv("XDG_CONFIG_HOME", "/nonexistent/sentinel")
        before = os.environ.get("HOME")
        _isolate_qt_settings(tmp_path)
        assert os.environ.get("HOME") == before


# ── the ParaView profile the take ships ───────────────────────────────────────

class TestParaViewProfile:
    def test_the_shipped_profile_exists(self):
        profile = ROOT / "tools" / "demo_paraview_profile"
        assert profile.is_dir(), (
            "cavity-full-workflow needs a ParaView profile of its own; "
            "regenerate with tools/make_paraview_demo_profile.sh"
        )
        assert list(profile.glob("ParaView*.ini")), "no ParaView settings file in the profile"

    def test_the_profile_suppresses_the_welcome_dialog(self):
        # A first-run ParaView puts a Getting Started splash across the window,
        # which is the visible half of why the take ships a profile at all.
        text = "\n".join(
            p.read_text(encoding="utf-8", errors="replace")
            for p in (ROOT / "tools" / "demo_paraview_profile").glob("ParaView*.ini")
        )
        assert "ShowWelcomeDialog=0" in text.replace(" ", "")

    def test_seeding_copies_it_into_the_takes_config(self, tmp_path):
        _seed_paraview_profile(tmp_path)
        copied = sorted(p.name for p in (tmp_path / "ParaView").iterdir())
        shipped = sorted(p.name for p in (ROOT / "tools" / "demo_paraview_profile").iterdir()
                         if p.is_file())
        assert copied == shipped

    def test_a_missing_profile_is_not_fatal(self, tmp_path, monkeypatch):
        # Missing means the take records ParaView's first-run splash, which is
        # a thing to notice in review, not a reason to refuse to record.
        import demo_driver

        monkeypatch.setattr(demo_driver, "ROOT", tmp_path / "nowhere")
        _seed_paraview_profile(tmp_path / "config")
        assert not (tmp_path / "config" / "ParaView").exists()


# ── the sidebar a take's dialogs come up with ─────────────────────────────────

def test_the_probe_uses_names_the_driver_still_defines():
    """The subprocess probe below reaches these by name from a string.

    A rename would surface there as a non-zero exit rather than a collection
    error, so this keeps the module-level reference that makes it obvious.
    """
    assert callable(_isolate_qt_settings)
    assert callable(_seed_file_dialog_sidebar)


_PROBE = """
import os, sys
from pathlib import Path
sys.path.insert(0, {tools!r})
work = Path(sys.argv[1])
from demo_driver import _isolate_qt_settings, _seed_file_dialog_sidebar
_isolate_qt_settings(work)

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFileDialog

QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeDialogs, True)
app = QApplication([sys.argv[0]])
scratch = work / "take"
scratch.mkdir(parents=True, exist_ok=True)
_seed_file_dialog_sidebar(app, [scratch])

later = QFileDialog()
later.setOption(QFileDialog.Option.DontUseNativeDialog, True)
print("SIDEBAR", "|".join(u.toLocalFile() for u in later.sidebarUrls()))
print("CONF", (work / "config" / "QtProject.conf").is_file())
print("HOMECONF_MTIME", os.stat(Path.home() / ".config" / "QtProject.conf").st_mtime_ns)
"""


class TestSeedFileDialogSidebar:
    """Checked in a subprocess, which is the only honest way to check it.

    QSettings caches its path the first time it is constructed, so inside the
    shared test process the redirect would arrive too late and the assertion
    would be measuring whichever config directory some earlier test had already
    fixed. A take is a fresh process that redirects before touching Qt at all,
    so that is what this reproduces.
    """

    @pytest.fixture(scope="class")
    @staticmethod
    def probe(tmp_path_factory):
        work = tmp_path_factory.mktemp("take")
        env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
        result = subprocess.run(
            [sys.executable, "-c", _PROBE.format(tools=str(ROOT / "tools")), str(work)],
            capture_output=True, text=True, env=env, timeout=120,
        )
        assert result.returncode == 0, result.stderr
        fields = {}
        for line in result.stdout.splitlines():
            key, _, value = line.partition(" ")
            fields[key] = value
        return work, fields

    def test_a_later_dialog_offers_only_the_seeded_entry(self, probe):
        work, fields = probe
        assert fields["SIDEBAR"] == str(work / "take")

    def test_no_sidebar_entry_names_the_home_directory(self, probe):
        _, fields = probe
        assert str(Path.home()) not in fields["SIDEBAR"]
        # Qt's default sidebar is ["file:", home]; an empty reading would pass
        # the check above for the wrong reason.
        assert fields["SIDEBAR"], "the sidebar was empty, so nothing was seeded"

    def test_the_state_lands_in_the_scratch_config(self, probe):
        _, fields = probe
        assert fields["CONF"] == "True", "Qt wrote its widget state somewhere else"

    def test_the_recorders_own_qt_settings_are_not_written(self, probe):
        _, fields = probe
        home_conf = Path.home() / ".config" / "QtProject.conf"
        assert fields["HOMECONF_MTIME"] == str(home_conf.stat().st_mtime_ns), (
            "a take modified the recording user's own QtProject.conf"
        )
