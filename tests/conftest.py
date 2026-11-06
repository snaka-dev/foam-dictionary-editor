# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
import os
from pathlib import Path

import pytest

# Every way the application opens a modal dialog. Each of these blocks until something
# answers it, and in a test nothing ever does -- so a handler that reaches one unstubbed
# hangs the run rather than failing it, with no indication of which test or which dialog.
_MODAL_ENTRY_POINTS = {
    "QDialog": ("exec",),
    "QMessageBox": ("exec", "question", "warning", "information", "critical"),
    "QFileDialog": (
        "getExistingDirectory", "getOpenFileName", "getOpenFileNames", "getSaveFileName",
    ),
    "QInputDialog": ("getText", "getItem"),
}


@pytest.fixture(scope="session", autouse=True)
def no_unstubbed_modals():
    """Turn an unanswered modal dialog from a hang into a named failure.

    Five hangs in one afternoon were all the same mistake: a handler under test reaches a
    dialog the test forgot to stub, `exec()` spins waiting for a click, and the run stops
    dead. Nothing points at the cause -- the test that hangs is not named in any output,
    so finding it means bisecting by hand, and a CI run just times out.

    Poisoning the entry points makes that impossible: the same mistake now fails
    immediately, in the test that made it, naming the class and method to stub. Verified
    against the whole suite before being switched on -- all 2747 tests pass with these
    raising, which is the same thing as saying no test legitimately opens a dialog.

    Constructing a dialog is untouched; only the blocking calls are replaced. Session
    scope rather than per-test because nothing needs the real ones back, and a test that
    stubs one with `monkeypatch` still works -- monkeypatch restores to the poisoned
    version, which is what should be there.
    """
    from PySide6 import QtWidgets

    saved = []
    for class_name, methods in _MODAL_ENTRY_POINTS.items():
        owner = getattr(QtWidgets, class_name)
        for method in methods:
            original = owner.__dict__.get(method, getattr(owner, method, None))
            saved.append((owner, method, original))
            setattr(owner, method, _refuse_modal(class_name, method))
    yield
    for owner, method, original in reversed(saved):
        if original is None:
            continue
        setattr(owner, method, original)


def _refuse_modal(class_name: str, method: str):
    def refuse(*args, **kwargs):
        raise AssertionError(
            f"{class_name}.{method}() was called without being stubbed.\n"
            f"A modal dialog blocks until someone answers it, and in a test nobody does, "
            f"so this would hang the run rather than fail it.\n"
            f"Stub it -- monkeypatch the attribute on ui.mixins.<module>, or patch "
            f"{class_name}.{method} directly -- and assert on what the handler did with "
            f"the answer."
        )

    return staticmethod(refuse) if method != "exec" else refuse


def _destroy_widget(widget) -> None:
    """Destroy *widget* and everything it owns, synchronously, right now.

    Qt's own answer -- ``deleteLater()`` -- does nothing here. Nothing in this suite runs a
    Qt event loop, and at loop level 0 ``processEvents()`` does not deliver
    ``DeferredDelete``: a widget is still in ``QApplication.allWidgets()`` after
    ``deleteLater()`` *and* ``processEvents()``. Dropping the last Python reference does not
    help either -- ``del win`` plus ``gc.collect()`` leaves all 237 of a MainWindow's widgets
    alive. Only ``shiboken6.delete`` frees the C++ object.

    Why it matters: ``ui.theme.apply_theme`` -> ``setStyle``/``setPalette``/``setStyleSheet``
    are broadcasts. Qt walks every live QWidget in the process and re-polishes it, at roughly
    half a millisecond each. One leaked window per test left tens of thousands alive, which is
    what made tests/ui/test_theme.py and tests/ui/test_icons.py -- 0.3 s on their own -- cost
    about 1300 s of a 1700 s suite. See DEVELOPER.md's "Destroying widgets in tests".

    Deliberately *not* ``close()``. ``MainWindow.closeEvent`` asks
    ``_confirm_discard_if_needed()``, which raises a modal QMessageBox when the editor is
    dirty -- and tests leave it dirty. With no event loop to answer it the suite hangs rather
    than fails; that happened. ``closeEvent`` also writes the session and the window size back
    to the config, which is teardown no test asked for. Hiding is all that is left.

    Callers destroy only what they built themselves. ``QApplication.topLevelWidgets()`` is a
    list of *windows by flag*, not ownership roots -- ``Qt::Popup`` carries the ``Qt::Window``
    bit, so a MainWindow contributes about ten live QMenus whose parents hold raw
    back-pointers to them -- and deleting one of those segfaults.
    """
    import shiboken6
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QWidget

    if widget is not None and shiboken6.isValid(widget):
        if isinstance(widget, QWidget):
            widget.hide()
        shiboken6.delete(widget)
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


@pytest.fixture
def destroy_widget():
    """Hand a widget-owning fixture the destructor it needs.

    A fixture rather than an import: ``tests/`` has no ``__init__.py``, so ``tests.conftest``
    is not importable, and requesting it by name is how a module under tests/ui/ reaches this
    file. It also puts the dependency in the fixture's signature, where it is visible.
    """
    return _destroy_widget


@pytest.fixture
def qt_widget():
    """Take ownership of widgets a *test body* builds by hand.

    ``dlg = qt_widget(ManageExtraFilesDialog([]))`` reads like the bare constructor it
    replaces and needs no try/finally. Widgets are destroyed in reverse construction order, so
    a child built after its owner still goes first. Use this inside a test; use
    :func:`destroy_widget` from a fixture that already has a teardown block.
    """
    created: list[object] = []

    def keep(widget):
        created.append(widget)
        return widget

    yield keep
    for widget in reversed(created):
        _destroy_widget(widget)


@pytest.fixture(scope="session", autouse=True)
def real_config_untouched():
    """The developer's own app_config.json must be byte-identical after the run.

    :func:`temp_config` redirects the singleton and ``$FODE_CONFIG`` for every test, which
    is what stops a test writing here. But that is a *per-test* redirect, and it cannot see
    a write from outside a test: a session- or module-scoped fixture, work at import time,
    or a subprocess this suite starts. This fixture states the property end to end, which
    is the one the person running `pytest` actually cares about -- the window size, case
    directory and session layout they had before the run are the ones they have after it.

    Window size is the one that bites. ``MainWindow.closeEvent`` writes ``self.width()``/
    ``self.height()`` and saves, so a single MainWindow built against the real config and
    closed would silently resize the developer's next launch to whatever some test used.
    Nothing about that failure is visible in the test that caused it.

    A failure here is not necessarily a bug in the suite: running the app itself while the
    tests run also changes the file. The message says so.
    """
    real = Path(__file__).resolve().parent.parent / "app_config.json"
    before = real.read_bytes() if real.exists() else None
    yield
    after = real.read_bytes() if real.exists() else None
    if before == after:
        return
    if before is None:
        raise AssertionError(
            f"The test run CREATED {real}, which did not exist before it. Something built "
            f"a config against the real path instead of the temp_config one."
        )
    verb = "DELETED" if after is None else "MODIFIED"
    raise AssertionError(
        f"The test run {verb} {real}.\n"
        f"Something wrote the real config instead of the throwaway temp_config points at "
        f"-- most likely a MainWindow built and closed outside the `main_window` fixture, "
        f"since closeEvent saves the window size. If you were running FoDE itself during "
        f"this test run, that is the explanation and this is not a suite bug."
    )


@pytest.fixture(scope="session", autouse=True)
def platform_default_font(qapp):
    """The application font *and style* as the session found them, before any test changed them.

    Returns `(font, style_name)`. The style is included because `ui.theme.apply_theme`
    calls `setStyle("Fusion")` and that is permanent for the session -- nothing restores
    it -- and a widget's size hints come from its style as much as its font. A test
    asserting an exact pixel width therefore depends on both.

    Autouse and session-scoped so it is captured once, immediately after pytest-qt builds
    the QApplication and before the first test runs. Five fixtures across tests/ui/ set an
    enlarged font and restore it, which is fine on its own -- but a test that asserts an
    *absolute* pixel width needs the real default rather than whatever the previous test
    left behind, and "whatever was left behind" stops being predictable the moment the
    suite runs in parallel.
    """
    from PySide6.QtGui import QFont

    return QFont(qapp.font()), qapp.style().objectName()


@pytest.fixture
def config_path(tmp_path):
    """The throwaway config file :func:`temp_config` writes to."""
    return tmp_path / "app_config.json"


@pytest.fixture(autouse=True)
def temp_config(config_path):
    """Point the config singleton at a throwaway file, for every test.

    Autouse and unconditional, because the ways a test can end up writing the
    repository's own ``app_config.json`` are not obvious from the test: closing
    a window saves, and so does anything that calls ``save()`` — and a test that
    turns a feature flag off to keep itself light would leave it off for the
    developer. That happened, so this is no longer left to each test to
    remember.

    ``$FODE_CONFIG`` is set as well as the singleton replaced: the first covers
    a manager built later from scratch, the second the one that already exists.

    Deliberately *not* implemented with ``monkeypatch``. An autouse fixture that
    requests it makes monkeypatch the earliest-created fixture in every test,
    which moves its undo to the end of teardown — and at least one test module
    relies on its patches being undone before its own teardown runs.
    """
    import app_config
    from app_config.app_config_manager import CONFIG_PATH_ENV, AppConfigManager

    previous_env = os.environ.get(CONFIG_PATH_ENV)
    previous_singleton = app_config._app_config

    os.environ[CONFIG_PATH_ENV] = str(config_path)
    manager = AppConfigManager(config_path=str(config_path))
    app_config._app_config = manager
    try:
        yield manager
    finally:
        app_config._app_config = previous_singleton
        if previous_env is None:
            os.environ.pop(CONFIG_PATH_ENV, None)
        else:
            os.environ[CONFIG_PATH_ENV] = previous_env


@pytest.fixture
def main_window(qapp, temp_config):
    """A real MainWindow instance, with the terminal/blockmesh features disabled
    to keep instantiation light and independent of VTK/QtWebEngine availability.

    Takes ``temp_config`` explicitly rather than trusting autouse ordering: the
    window this builds is one of the things that writes a config on the way out.
    """
    cfg = temp_config
    original = {name: cfg.get_feature(name) for name in ("terminal", "blockmesh")}
    cfg.set_feature("terminal", False)
    cfg.set_feature("blockmesh", False)

    from ui.main_window import MainWindow

    win = MainWindow()
    yield win

    win._file_list_refresh_timer.stop()
    if win._case_dir_watcher.directories():
        win._case_dir_watcher.removePaths(win._case_dir_watcher.directories())
    win._stop_foam_monitor()
    if win.terminal_panel is not None:
        win.terminal_panel.cleanup()
    if win.block_mesh_panel is not None:
        win.block_mesh_panel.shutdown()
    # Destruction goes last: the shutdown calls above release a PTY and the VTK render
    # window, and both need their QWidget still alive to do it. The flag restore moves into
    # a finally so a failed destruction cannot leak a process-global feature flag into the
    # rest of the session; nothing on the destruction path reads one, because we never call
    # close() and so never reach closeEvent's save_session()/cfg.save().
    try:
        _destroy_widget(win)
    finally:
        for name, value in original.items():
            cfg.set_feature(name, value)


@pytest.fixture
def control_dict_text():
    return """/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v2312                                 |
|   \\\\  /    A nd           | Website:  www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      controlDict;
}

application     interFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         1;
deltaT          0.005;
writeControl    timeStep;
writeInterval   20;
purgeWrite      0;
writeFormat     ascii;
writePrecision  6;
writeCompression off;
timeFormat      general;
timePrecision   6;
runTimeModifiable true;

// ************************************************************************* //
"""


@pytest.fixture
def fv_schemes_text():
    return """FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      fvSchemes;
}

ddtSchemes
{
    default         Euler;
}

gradSchemes
{
    default         Gauss linear;
    grad(p)         Gauss linear;
}

divSchemes
{
    default         none;
    div(phi,U)      Gauss linear;
}

laplacianSchemes
{
    default         Gauss linear orthogonal;
}

interpolationSchemes
{
    default         linear;
}

snGradSchemes
{
    default         orthogonal;
}
"""


@pytest.fixture
def fv_solution_text():
    return """FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      fvSolution;
}

solvers
{
    p
    {
        solver          GAMG;
        tolerance       1e-06;
        relTol          0.1;
        smoother        GaussSeidel;
    }

    pFinal
    {
        $p;
        relTol          0;
    }

    "(U|k|omega)"
    {
        solver          smoothSolver;
        smoother        symGaussSeidel;
        tolerance       1e-08;
        relTol          0.1;
    }
}

PIMPLE
{
    momentumPredictor yes;
    nOuterCorrectors  2;
    nCorrectors       2;
    nNonOrthogonalCorrectors 0;
}
"""
