#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
#
# Stage the two runs the Plot Results screenshots and movie read.
#
#   tools/stage_plot_cases.sh [OPENFOAM_DIR] [DEST]
#
# OpenCFD's pitzDaily twice, once with kEpsilon (as it ships) and once with
# kOmegaSST, each with a probe and a sampled line across the channel added to
# controlDict, then meshed and run with simpleFoam into log.simpleFoam. The
# pair is what a comparison is for: the same velocity profile from two
# turbulence models.
#
# DEST defaults to /tmp/OpenFOAM/run/plot -- deliberately not under $HOME, for
# the reason DEVELOPER.md's "Screenshot capture" gives: the data-file window
# prints the file's full path, and a published image must not carry the
# capturing user's name. Existing cases there are replaced.
set -euo pipefail

FOAM=${1:-/usr/lib/openfoam/openfoam2606}
DEST=${2:-/tmp/OpenFOAM/run/plot}
SRC="$FOAM/tutorials/incompressible/simpleFoam/pitzDaily"

[ -d "$SRC" ] || { echo "no pitzDaily tutorial at $SRC" >&2; exit 1; }
# OpenFOAM's bashrc is not written for -e/-u: a failed test inside it would
# end this script.
set +eu
# shellcheck disable=SC1091
source "$FOAM/etc/bashrc"
set -eu
command -v simpleFoam > /dev/null || { echo "sourcing $FOAM/etc/bashrc gave no simpleFoam" >&2; exit 1; }

functions='
functions
{
    probes
    {
        type            probes;
        libs            (sampling);
        writeControl    timeStep;
        writeInterval   1;
        fields          (p U);
        probeLocations  ((0.1 0 0) (0.2 0 0));
    }

    lineSample
    {
        type            sets;
        libs            (sampling);
        writeControl    writeTime;
        interpolationScheme cellPoint;
        setFormat       raw;
        fields          (U p k);
        sets
        {
            x0.1
            {
                type    uniform;
                axis    y;
                start   (0.1 -0.0254 0);
                end     (0.1  0.0254 0);
                nPoints 100;
            }
        }
    }
}
'

stage() {
    local name=$1 model=$2
    local case="$DEST/$name"
    rm -rf "$case"
    mkdir -p "$DEST"
    cp -r "$SRC" "$case"
    # The tutorial's own functions block (#includeFunc streamlines) is
    # replaced: streamlines write VTK, nothing to plot.
    python3 - "$case/system/controlDict" "$functions" <<'PY'
import re, sys
path, block = sys.argv[1], sys.argv[2]
text = open(path).read()
text = re.sub(r"\nfunctions\s*\{.*?\n\}\n", "\n" + block, text, flags=re.S)
open(path, "w").write(text)
PY
    sed -i "s/RASModel *kEpsilon;/RASModel        $model;/" "$case/constant/turbulenceProperties"
    (cd "$case" && blockMesh > log.blockMesh 2>&1 && simpleFoam > log.simpleFoam 2>&1) &
}

stage pitzDaily-kEpsilon kEpsilon
stage pitzDaily-kOmegaSST kOmegaSST
wait
for c in "$DEST"/pitzDaily-*; do
    tail -n 3 "$c/log.simpleFoam" | grep -q '^End' || { echo "simpleFoam failed in $c" >&2; exit 1; }
    echo "staged $c ($(grep -c '^Time =' "$c/log.simpleFoam") iterations)"
done
