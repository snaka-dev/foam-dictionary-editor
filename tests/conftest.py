# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
import pytest


@pytest.fixture
def main_window(qapp):
    """A real MainWindow instance, with the terminal/blockmesh features disabled
    to keep instantiation light and independent of VTK/QtWebEngine availability."""
    from app_config import get_app_config

    cfg = get_app_config()
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
