# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for the BlockMesh panel's Save Image action.

The capture itself goes through VTK's render window (plotter.screenshot), so
these tests stand a recording stub in for the plotter rather than opening one:
what is checked here is the Qt half -- when the action is offered, what path
the writer is handed, and what happens when it refuses.
"""
from __future__ import annotations

import pathlib

import pytest

from ui.panels import block_mesh_panel
from ui.panels.block_mesh_panel import BlockMeshPanel

pytestmark = pytest.mark.skipif(
    not block_mesh_panel._PYVISTA_OK, reason="pyvista/pyvistaqt not installed"
)


class _StubPlotter:
    """Records the paths screenshot() is called with; optionally refuses."""

    def __init__(self, error: Exception | None = None) -> None:
        self.paths: list[str] = []
        self._error = error

    def screenshot(self, path):
        self.paths.append(str(path))
        if self._error is not None:
            raise self._error

    def close(self) -> None:
        pass


def _choose(monkeypatch, path: str) -> None:
    """Make the Save Image dialog return *path* without showing it."""
    monkeypatch.setattr(
        block_mesh_panel.QFileDialog,
        "getSaveFileName",
        staticmethod(lambda *a, **k: (path, "")),
    )


def _capture_warnings(monkeypatch) -> list[str]:
    seen: list[str] = []
    monkeypatch.setattr(
        block_mesh_panel.QMessageBox,
        "warning",
        staticmethod(lambda _parent, _title, text, *a, **k: seen.append(text)),
    )
    return seen


def _decline_overwrite(monkeypatch) -> list[str]:
    """Answer No to any overwrite prompt; the returned list records the asks."""
    asked: list[str] = []
    monkeypatch.setattr(
        block_mesh_panel.QMessageBox,
        "question",
        staticmethod(
            lambda _parent, _title, text, *a, **k: (
                asked.append(text),
                block_mesh_panel.QMessageBox.StandardButton.No,
            )[1]
        ),
    )
    return asked


def _saved_paths(panel) -> list[str]:
    """Collect what the panel reports through image_saved."""
    emitted: list[str] = []
    panel.image_saved.connect(emitted.append)
    return emitted


# ── availability ──────────────────────────────────────────────────────────────

def test_action_starts_disabled(qapp):
    """No plotter yet, so there is no view to save."""
    panel = BlockMeshPanel()
    assert panel.save_image_action is not None
    assert not panel.save_image_action.isEnabled()


def test_shutdown_disables_the_action(qapp):
    panel = BlockMeshPanel()
    panel._plotter = _StubPlotter()   # type: ignore[assignment]
    # The stub is not a QWidget, so it cannot be un-parented from the real
    # layout; shutdown() skips that step when there is no layout to remove from.
    panel._plotter_layout = None
    panel.save_image_action.setEnabled(True)
    panel.shutdown()
    assert not panel.save_image_action.isEnabled()


def test_toolbar_button_and_menu_share_one_action(qapp):
    """The View-menu item MainWindow adds must be this very QAction."""
    panel = BlockMeshPanel()
    buttons = [
        w for w in panel.findChildren(block_mesh_panel.QToolButton)
        if w.defaultAction() is panel.save_image_action
    ]
    assert len(buttons) == 1


# ── writing ───────────────────────────────────────────────────────────────────

def test_writes_the_chosen_path(qapp, tmp_path, monkeypatch):
    panel = BlockMeshPanel()
    stub = _StubPlotter()
    panel._plotter = stub             # type: ignore[assignment]
    target = str(tmp_path / "view.png")
    _choose(monkeypatch, target)
    saved = _saved_paths(panel)

    panel._save_view_image()

    assert stub.paths == [target]
    assert saved == [target]


@pytest.mark.parametrize(
    ("chosen", "written"),
    [
        ("view", "view.png"),          # no suffix at all
        ("view.txt", "view.txt.png"),  # a suffix the writer cannot use
        ("view.JPG", "view.jpg"),      # supported format, rejected spelling
        ("view.PNG", "view.png"),
        ("a.b.TIFF", "a.b.tiff"),      # only the last component is a suffix
        ("view.png", "view.png"),      # already fine, left alone
    ],
)
def test_suffix_is_coerced_to_something_writable(
    qapp, tmp_path, monkeypatch, chosen, written
):
    """pyvista's SUPPORTED_FORMATS check is case-sensitive, so ".JPG" raises.

    Lowering a supported-but-shouted suffix is what keeps the user's chosen
    format; appending ".png" is the fallback for one pyvista cannot write.
    """
    panel = BlockMeshPanel()
    stub = _StubPlotter()
    panel._plotter = stub             # type: ignore[assignment]
    _choose(monkeypatch, str(tmp_path / chosen))

    panel._save_view_image()

    assert stub.paths == [str(tmp_path / written)]


def test_one_image_filter_covering_every_supported_suffix(qapp, monkeypatch):
    """A single filter, so the dropdown cannot disagree with the typed name.

    A native GTK chooser (what Qt uses on GNOME) treats a name filter as a
    view filter and never rewrites the name to match it, so per-format
    entries would let the user pick JPEG, keep a .png name, and get a PNG.
    """
    seen: list[str] = []
    monkeypatch.setattr(
        block_mesh_panel.QFileDialog,
        "getSaveFileName",
        staticmethod(lambda _p, _t, _d, filt="", *a, **k: (seen.append(filt), ("", ""))[1]),
    )
    panel = BlockMeshPanel()
    panel._plotter = _StubPlotter()   # type: ignore[assignment]

    panel._save_view_image()

    assert len(seen) == 1
    image_filter = seen[0].split(";;")[0]
    # Exactly one image entry, and it offers every suffix the writer accepts.
    assert len(seen[0].split(";;")) == 2, "expected one image filter plus All files"
    for suffix in block_mesh_panel._IMAGE_SUFFIXES:
        assert f"*{suffix}" in image_filter, suffix

    # Qt's gtk3 helper labels a native filter with filter.left(indexOf("(")),
    # so only this half is ever on screen under GNOME. It must still say what
    # the dialog accepts, and say nothing the writer would reject.
    visible = image_filter.split("(")[0]
    named = {w.strip(" ,-").lower() for w in visible.split() if w.strip(" ,-").isalnum()}
    named -= {"image", "files"}
    assert named, "the visible half of the filter names no format at all"
    for fmt in named:
        assert any(
            s.lstrip(".").startswith(fmt[:3]) for s in block_mesh_panel._IMAGE_SUFFIXES
        ), f"filter advertises {fmt!r}, which no supported suffix matches"


def test_every_coerced_suffix_is_one_pyvista_accepts(tmp_path):
    """The suffixes _writable_image_path can produce must satisfy pyvista.

    Guards the pairing directly rather than through the stub: a change to
    pyvista's list, or to the coercion, should fail here rather than in a
    dialog the user is looking at.
    """
    from pyvista.plotting.plotter import SUPPORTED_FORMATS

    assert set(block_mesh_panel._IMAGE_SUFFIXES) == set(SUPPORTED_FORMATS)
    for name in ("v", "v.txt", "v.JPG", "v.PNG", "v.tiff", "v.Bmp", "v.TIF"):
        written = block_mesh_panel._writable_image_path(str(tmp_path / name))
        assert pathlib.Path(written).suffix in SUPPORTED_FORMATS, name


# ── not clobbering a file the dialog never asked about ────────────────────────

def test_corrected_name_asks_before_overwriting(qapp, tmp_path, monkeypatch):
    """The dialog checked "view.txt"; nothing ever checked "view.txt.png"."""
    existing = tmp_path / "view.txt.png"
    existing.write_text("precious")
    panel = BlockMeshPanel()
    stub = _StubPlotter()
    panel._plotter = stub             # type: ignore[assignment]
    _choose(monkeypatch, str(tmp_path / "view.txt"))
    asked = _decline_overwrite(monkeypatch)

    panel._save_view_image()

    assert asked, "no overwrite confirmation was raised"
    assert stub.paths == []
    assert existing.read_text() == "precious"


def test_unchanged_name_does_not_ask_twice(qapp, tmp_path, monkeypatch):
    """QFileDialog already confirmed this one; a second prompt would be noise."""
    existing = tmp_path / "view.png"
    existing.write_text("stale")
    panel = BlockMeshPanel()
    stub = _StubPlotter()
    panel._plotter = stub             # type: ignore[assignment]
    _choose(monkeypatch, str(existing))
    asked = _decline_overwrite(monkeypatch)

    panel._save_view_image()

    assert not asked
    assert stub.paths == [str(existing)]


def test_corrected_name_that_is_free_writes_without_asking(
    qapp, tmp_path, monkeypatch
):
    panel = BlockMeshPanel()
    stub = _StubPlotter()
    panel._plotter = stub             # type: ignore[assignment]
    _choose(monkeypatch, str(tmp_path / "view.txt"))
    asked = _decline_overwrite(monkeypatch)

    panel._save_view_image()

    assert not asked
    assert stub.paths == [str(tmp_path / "view.txt.png")]


def test_cancelled_dialog_writes_nothing(qapp, monkeypatch):
    panel = BlockMeshPanel()
    stub = _StubPlotter()
    panel._plotter = stub             # type: ignore[assignment]
    _choose(monkeypatch, "")
    saved = _saved_paths(panel)

    panel._save_view_image()

    assert stub.paths == []
    assert saved == []


def test_no_plotter_is_a_no_op(qapp, tmp_path, monkeypatch):
    """The action is disabled in this state; the handler must not assume it."""
    panel = BlockMeshPanel()
    panel._plotter = None
    _choose(monkeypatch, str(tmp_path / "view.png"))
    saved = _saved_paths(panel)

    panel._save_view_image()

    assert saved == []


def test_write_failure_warns_and_reports_nothing_saved(qapp, tmp_path, monkeypatch):
    panel = BlockMeshPanel()
    panel._plotter = _StubPlotter(OSError("disk full"))  # type: ignore[assignment]
    _choose(monkeypatch, str(tmp_path / "view.png"))
    warnings = _capture_warnings(monkeypatch)
    saved = _saved_paths(panel)

    panel._save_view_image()

    assert len(warnings) == 1
    assert "disk full" in warnings[0]
    assert saved == []


# ── default filename ──────────────────────────────────────────────────────────

def test_default_path_is_named_after_the_case(qapp, tmp_path):
    panel = BlockMeshPanel()
    case = tmp_path / "damBreak"
    panel.set_case_dir(str(case))
    assert panel._default_image_path() == str(case / "damBreak-3Dview.png")


def test_default_path_without_a_case(qapp):
    panel = BlockMeshPanel()
    assert panel._default_image_path() == "3Dview.png"


def test_clear_forgets_the_case(qapp, tmp_path):
    """Opening another case clears the panel before set_case_dir re-points it."""
    panel = BlockMeshPanel()
    panel.set_case_dir(str(tmp_path / "cavity"))
    panel.clear()
    assert panel._default_image_path() == "3Dview.png"
