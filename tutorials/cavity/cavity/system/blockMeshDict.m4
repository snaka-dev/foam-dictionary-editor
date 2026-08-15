/*--------------------------------*- C++ -*----------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  v2512                                 |
|   \\  /    A nd           | Website:  www.openfoam.com                      |
|    \\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    `format'      ascii;
    class       dictionary;
    object      blockMeshDict;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
// m4 source for the cavity blockMeshDict -- parametrised so the resolution
// and cavity size can be changed in one place and regenerated:
//   m4 blockMeshDict.m4 > blockMeshDict

changecom(//)changequote([,])
define(calc, [esyscmd(perl -e 'print ($1)')])

// Cavity side length
define(L, 0.1)

// Slab thickness (this is a 2-D case, one cell deep)
define(Z, calc(L))

// Cells per side
define(N, 20)

scale   1;

vertices
(
    (0 0 0)
    (L 0 0)
    (L L 0)
    (0 L 0)
    (0 0 Z)
    (L 0 Z)
    (L L Z)
    (0 L Z)
);

blocks
(
    hex (0 1 2 3 4 5 6 7) (N N 1) simpleGrading (1 1 1)
);

edges
(
);

boundary
(
    movingWall
    {
        type wall;
        faces
        (
            (3 7 6 2)
        );
    }
    fixedWalls
    {
        type wall;
        faces
        (
            (0 4 7 3)
            (2 6 5 1)
            (1 5 4 0)
        );
    }
    frontAndBack
    {
        type empty;
        faces
        (
            (0 3 2 1)
            (4 5 6 7)
        );
    }
);


// ************************************************************************* //
