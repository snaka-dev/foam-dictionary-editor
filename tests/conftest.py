# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
import os

import pytest


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
