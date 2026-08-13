# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Schema for `system/controlDict`.

Enumerations come from the `Enum` name tables in `src/OpenFOAM/db/Time/Time.C`
and the keys read in `TimeIO.C` / `cfdTools/general/include/readTimeControls.H`.

Note that `writeControl` means two different things depending on where it
appears. At the top level it is `Time::writeControlNames` (Time.C:64-74); inside
a `functions {}` entry it is `functionObjects::timeControl::controlNames_`
(timeControl.C:38-50), which adds `always`, `writeTime`, `onStart` and `onEnd`.
The two are therefore separate entries here, the second qualified under
`functions`.
"""
from __future__ import annotations

from schemas._base import BOTH, SWITCH_CHOICES, ChoiceItem, KeySchema, entry

TARGET_FILE = "controlDict"

SCHEMAS: dict[str, KeySchema] = {
    # ── what to run ───────────────────────────────────────────────────────────
    "application": entry(
        "application", "Application",
        "Solver this case is written for. Not used by the solver itself, but the "
        "Allrun scripts and foamJob read it to decide what to launch.",
    ),
    "libs": entry(
        "libs", "Libraries",
        "Extra libraries loaded at start-up, as a list of quoted names — needed "
        "for custom boundary conditions, function objects or models.",
    ),

    # ── time ──────────────────────────────────────────────────────────────────
    "startFrom": entry(
        "startFrom", "Start From",
        "Which time directory the run starts from.",
        (
            ChoiceItem("startTime", "Start from the time given by the startTime entry.", BOTH),
            ChoiceItem("latestTime", "Start from the latest time directory present. "
                                     "The usual choice for restarting.", BOTH),
            ChoiceItem("firstTime", "Start from the earliest time directory present.", BOTH),
        ),
    ),
    "startTime": entry("startTime", "Start Time",
        "Time value used when startFrom is 'startTime'."),
    "stopAt": entry(
        "stopAt", "Stop At",
        "Condition that ends the run.",
        (
            ChoiceItem("endTime", "Run until endTime.", BOTH),
            ChoiceItem("writeNow", "Stop at the end of the current step and write.", BOTH),
            ChoiceItem("noWriteNow", "Stop at the end of the current step without writing.", BOTH),
            ChoiceItem("nextWrite", "Stop at the next scheduled write.", BOTH),
        ),
    ),
    "endTime": entry("endTime", "End Time",
        "Time at which the run stops, when stopAt is 'endTime'."),
    "deltaT": entry("deltaT", "Time Step",
        "Time-step size. The initial step only, when adjustTimeStep is on."),

    # ── adjustable time step ──────────────────────────────────────────────────
    "adjustTimeStep": entry(
        "adjustTimeStep", "Adjust Time Step",
        "Lets the solver resize the time step to satisfy the Courant limits below. "
        "Read by readTimeControls.H, which nearly every transient solver includes.",
        SWITCH_CHOICES,
    ),
    "maxCo": entry("maxCo", "Maximum Courant Number",
        "Courant-number ceiling used when adjustTimeStep is on. Typically 0.5-1."),
    "maxAlphaCo": entry("maxAlphaCo", "Maximum Alpha Courant Number",
        "Courant ceiling for the phase fraction in VOF solvers such as interFoam."),
    "maxDeltaT": entry("maxDeltaT", "Maximum Time Step",
        "Upper bound on the adjusted time step."),

    # ── writing ───────────────────────────────────────────────────────────────
    "writeControl": entry(
        "writeControl", "Write Control",
        "When results are written.",
        (
            ChoiceItem("timeStep", "Every writeInterval time steps.", BOTH),
            ChoiceItem("adjustable", "Every writeInterval seconds, adjusting the time "
                                     "step to land exactly on it. The usual choice for "
                                     "adjustable-time-step runs.", BOTH),
            ChoiceItem("runTime", "Every writeInterval seconds of simulated time.", BOTH),
            ChoiceItem("adjustableRunTime", "Same as 'adjustable'; the older spelling.", BOTH),
            ChoiceItem("clockTime", "Every writeInterval seconds of wall-clock time.", BOTH),
            ChoiceItem("cpuTime", "Every writeInterval seconds of CPU time.", BOTH),
            ChoiceItem("none", "Never write.", BOTH),
        ),
    ),
    "writeInterval": entry("writeInterval", "Write Interval",
        "Interval between writes, read in the unit chosen by writeControl."),
    "purgeWrite": entry(
        "purgeWrite", "Purge Write",
        "Number of time directories kept, oldest deleted first. 0 keeps everything.",
    ),
    "writeFormat": entry(
        "writeFormat", "Write Format",
        "Encoding of written field files.",
        (
            ChoiceItem("ascii", "Human-readable text. Larger and slower.", BOTH),
            ChoiceItem("binary", "Compact and fast, but not directly readable.", BOTH),
        ),
    ),
    "writePrecision": entry("writePrecision", "Write Precision",
        "Significant digits written in ascii format. Typically 6-12."),
    "writeCompression": entry(
        "writeCompression", "Write Compression",
        "Whether written files are gzip-compressed.", SWITCH_CHOICES,
    ),
    "writeVersion": entry("writeVersion", "Write Version",
        "Format version stamped into the FoamFile header."),
    "writeFrequency": entry("writeFrequency", "Write Frequency",
        "Write frequency used by the solvers that read it instead of writeInterval."),

    # ── time formatting ───────────────────────────────────────────────────────
    "timeFormat": entry(
        "timeFormat", "Time Format",
        "How time values are formatted when naming time directories.",
        (
            ChoiceItem("general", "Fixed or scientific, whichever is shorter.", BOTH),
            ChoiceItem("fixed", "Always fixed-point notation.", BOTH),
            ChoiceItem("scientific", "Always scientific notation.", BOTH),
        ),
    ),
    "timePrecision": entry("timePrecision", "Time Precision",
        "Significant digits in time-directory names. Raise this if steps are so "
        "small that two directories would otherwise collide."),

    # ── runtime behaviour ─────────────────────────────────────────────────────
    "runTimeModifiable": entry(
        "runTimeModifiable", "Run Time Modifiable",
        "Re-reads the dictionaries at every time step, so edits take effect "
        "without restarting. Costs a file check each step.",
        SWITCH_CHOICES,
    ),
    "graphFormat": entry(
        "graphFormat", "Graph Format",
        "Format for graph data written by the solvers that produce it.",
        (
            ChoiceItem("raw", "Plain columns of numbers.", BOTH),
            ChoiceItem("gnuplot", "gnuplot script format.", BOTH),
            ChoiceItem("xmgr", "Grace/xmgr format.", BOTH),
            ChoiceItem("jplot", "jPlot format.", BOTH),
        ),
    ),
    "fileHandler": entry(
        "fileHandler", "File Handler",
        "I/O implementation used for reading and writing.",
        (
            ChoiceItem("uncollated", "One file per processor directory. The default.", BOTH),
            ChoiceItem("collated", "Processor data gathered into single files.", BOTH),
            ChoiceItem("masterUncollated", "Master process performs all I/O.", BOTH),
        ),
    ),
    "DebugSwitches": entry("DebugSwitches", "Debug Switches",
        "Per-class debug levels, overriding etc/controlDict for this run."),
    "InfoSwitches": entry("InfoSwitches", "Info Switches",
        "Per-class info levels, overriding etc/controlDict for this run."),
    "OptimisationSwitches": entry("OptimisationSwitches", "Optimisation Switches",
        "Low-level I/O and communication tuning, overriding etc/controlDict."),

    # ── function objects ──────────────────────────────────────────────────────
    "functions": entry(
        "functions", "Functions",
        "Function objects run during the solution — sampling, forces, probes, "
        "field averaging. Each entry is a sub-dictionary, or a #includeFunc line.",
    ),
    "functions.*": entry(
        "*", "functions/<name>",
        "One function object. The name is chosen by the user; 'type' selects "
        "which function object it is.",
    ),
    # Inside functions{} this is the functionObjects enum, not Time's.
    "functions.writeControl": entry(
        "writeControl", "Write Control (function object)",
        "When this function object writes. A larger set than the top-level "
        "writeControl, because a function object can also act on start and end.",
        (
            ChoiceItem("timeStep", "Every writeInterval time steps.", BOTH),
            ChoiceItem("writeTime", "Whenever the solver itself writes.", BOTH),
            ChoiceItem("adjustable", "Every writeInterval seconds, adjusting the time step.", BOTH),
            ChoiceItem("runTime", "Every writeInterval seconds of simulated time.", BOTH),
            ChoiceItem("onEnd", "Once, at the end of the run.", BOTH),
            ChoiceItem("onStart", "Once, at the start of the run.", BOTH),
            ChoiceItem("always", "Every time step.", BOTH),
            ChoiceItem("outputTime", "Same as 'writeTime'; the older spelling.", BOTH),
            ChoiceItem("clockTime", "Every writeInterval seconds of wall-clock time.", BOTH),
            ChoiceItem("cpuTime", "Every writeInterval seconds of CPU time.", BOTH),
            ChoiceItem("none", "Never.", BOTH),
        ),
    ),
    "functions.executeControl": entry(
        "executeControl", "Execute Control (function object)",
        "When this function object executes, using the same set of values as its "
        "writeControl.",
        (
            ChoiceItem("timeStep", "Every executeInterval time steps.", BOTH),
            ChoiceItem("writeTime", "Whenever the solver writes.", BOTH),
            ChoiceItem("adjustable", "Every executeInterval seconds, adjusting the time step.", BOTH),
            ChoiceItem("runTime", "Every executeInterval seconds of simulated time.", BOTH),
            ChoiceItem("onEnd", "Once, at the end of the run.", BOTH),
            ChoiceItem("onStart", "Once, at the start of the run.", BOTH),
            ChoiceItem("always", "Every time step.", BOTH),
            ChoiceItem("none", "Never.", BOTH),
        ),
    ),
    "functions.writeInterval": entry("writeInterval", "Write Interval (function object)",
        "Interval between this function object's writes."),
    "functions.executeInterval": entry("executeInterval", "Execute Interval (function object)",
        "Interval between this function object's executions."),
    "functions.type": entry("type", "Function Object Type",
        "Which function object this is, e.g. probes, forces, fieldAverage, surfaces."),
    "functions.libs": entry("libs", "Function Object Libraries",
        "Libraries providing this function object, as a list of quoted names."),
    "functions.enabled": entry("enabled", "Enabled",
        "Set to false to switch this function object off without deleting it.",
        SWITCH_CHOICES),
    "functions.log": entry("log", "Log",
        "Writes this function object's results to the run log.", SWITCH_CHOICES),
    "functions.fields": entry("fields", "Fields",
        "Fields this function object acts on, as a list."),
    "functions.region": entry("region", "Region",
        "Mesh region this function object applies to, in a multi-region case."),
    "functions.timeStart": entry("timeStart", "Time Start",
        "Time before which this function object does nothing."),
    "functions.timeEnd": entry("timeEnd", "Time End",
        "Time after which this function object does nothing."),

    # Common settings across the sampling / field / forces function objects.
    "functions.name": entry("name", "Name",
        "Name this function object reports under, when it differs from the entry name."),
    "functions.field": entry("field", "Field",
        "Single field this function object acts on."),
    "functions.writeFields": entry("writeFields", "Write Fields",
        "Writes the derived fields as well as the summary values.", SWITCH_CHOICES),
    "functions.writeToFile": entry("writeToFile", "Write To File",
        "Writes results to postProcessing/ as well as the log.", SWITCH_CHOICES),
    "functions.useUserTime": entry("useUserTime", "Use User Time",
        "Reports time in the user time unit rather than seconds.", SWITCH_CHOICES),
    "functions.regionType": entry("regionType", "Region Type",
        "What the function object is evaluated over.",
        (
            ChoiceItem("patch", "A boundary patch.", BOTH),
            ChoiceItem("cellZone", "A cell zone.", BOTH),
            ChoiceItem("faceZone", "A face zone.", BOTH),
            ChoiceItem("all", "The whole domain.", BOTH),
            ChoiceItem("surface", "A sampled surface.", BOTH),
        )),
    "functions.operation": entry("operation", "Operation",
        "Reduction applied over the region.",
        (
            ChoiceItem("sum", "Sum of values.", BOTH),
            ChoiceItem("average", "Arithmetic mean.", BOTH),
            ChoiceItem("areaAverage", "Area-weighted mean.", BOTH),
            ChoiceItem("areaIntegrate", "Integral over the area.", BOTH),
            ChoiceItem("weightedAverage", "Mean weighted by weightField.", BOTH),
            ChoiceItem("volAverage", "Volume-weighted mean.", BOTH),
            ChoiceItem("volIntegrate", "Integral over the volume.", BOTH),
            ChoiceItem("min", "Minimum value.", BOTH),
            ChoiceItem("max", "Maximum value.", BOTH),
            ChoiceItem("none", "No reduction.", BOTH),
        )),
    "functions.weightField": entry("weightField", "Weight Field",
        "Field used as the weight by the weighted operations."),
    "functions.patches": entry("patches", "Patches",
        "Boundary patches this function object acts on, as a list."),
    "functions.interpolationScheme": entry("interpolationScheme", "Interpolation Scheme",
        "How cell values are interpolated to the sample locations.",
        (
            ChoiceItem("cell", "Nearest cell value; piecewise constant.", BOTH),
            ChoiceItem("cellPoint", "Interpolated from cell and point values.", BOTH),
            ChoiceItem("cellPointFace", "Cell, point and face values.", BOTH),
            ChoiceItem("pointMVC", "Mean-value coordinates from point values.", BOTH),
        )),
    "functions.setFormat": entry("setFormat", "Set Format",
        "Output format for sampled sets.",
        (
            ChoiceItem("raw", "Plain columns.", BOTH),
            ChoiceItem("csv", "Comma-separated values.", BOTH),
            ChoiceItem("gnuplot", "gnuplot script.", BOTH),
            ChoiceItem("vtk", "VTK format.", BOTH),
            ChoiceItem("xmgr", "Grace/xmgr format.", BOTH),
            ChoiceItem("jplot", "jPlot format.", BOTH),
        )),
    "functions.surfaceFormat": entry("surfaceFormat", "Surface Format",
        "Output format for sampled surfaces.",
        (
            ChoiceItem("vtk", "VTK format.", BOTH),
            ChoiceItem("ensight", "EnSight format.", BOTH),
            ChoiceItem("raw", "Plain columns.", BOTH),
            ChoiceItem("foam", "OpenFOAM native format.", BOTH),
            ChoiceItem("starcd", "STAR-CD format.", BOTH),
        )),
    "functions.formatOptions": entry("formatOptions", "Format Options",
        "Per-format output options, such as binary/ascii for VTK."),
    "functions.sets": entry("sets", "Sets",
        "Sample sets — lines or point clouds — evaluated by this function object."),
    "functions.surfaces": entry("surfaces", "Surfaces",
        "Sample surfaces, such as cutting planes or patch surfaces."),
    "functions.probeLocations": entry("probeLocations", "Probe Locations",
        "Points sampled by a probes function object, as a list of vectors."),
    "functions.fixedLocations": entry("fixedLocations", "Fixed Locations",
        "Samples at the requested points rather than snapping to mesh points.",
        SWITCH_CHOICES),
    "functions.rho": entry("rho", "Density Field",
        "Density field name, or 'rhoInf' to use the fixed value below."),
    "functions.rhoInf": entry("rhoInf", "Reference Density",
        "Fixed density used to dimensionalise forces in incompressible cases."),
    "functions.CofR": entry("CofR", "Centre of Rotation",
        "Point about which moments are taken."),
    "functions.mode": entry("mode", "Mode",
        "Mode of operation, as defined by this function object's type."),
    "functions.result": entry("result", "Result",
        "Name given to the value this function object produces."),
    "functions.fvOptions": entry("fvOptions", "fvOptions",
        "Finite-volume options applied by this function object."),

    # Sample-set entries sit one level deeper: functions/<obj>/sets/<name>/<key>,
    # so they resolve through the grandparent form "sets.<key>".
    "sets.*": entry("*", "sets/<name>",
        "One named sample set."),
    "sets.type": entry("type", "Set Type",
        "Geometry of the sample set.",
        (
            ChoiceItem("uniform", "Evenly spaced points between start and end.", BOTH),
            ChoiceItem("lineCell", "One sample per cell crossed by the line.", BOTH),
            ChoiceItem("lineCellFace", "Cell and face crossings along the line.", BOTH),
            ChoiceItem("midPoint", "Midpoint of each cell crossed.", BOTH),
            ChoiceItem("midPointAndFace", "Cell midpoints and face crossings.", BOTH),
            ChoiceItem("cloud", "An explicit list of points.", BOTH),
            ChoiceItem("face", "Face crossings only.", BOTH),
            ChoiceItem("polyLine", "Samples along a multi-segment line.", BOTH),
        )),
    "sets.axis": entry("axis", "Axis",
        "Coordinate written in the output's first column.",
        (
            ChoiceItem("x", "x coordinate.", BOTH),
            ChoiceItem("y", "y coordinate.", BOTH),
            ChoiceItem("z", "z coordinate.", BOTH),
            ChoiceItem("xyz", "All three coordinates.", BOTH),
            ChoiceItem("distance", "Distance along the set from its start.", BOTH),
        )),
    "sets.start": entry("start", "Start", "First point of the sample line."),
    "sets.end": entry("end", "End", "Last point of the sample line."),
    "sets.nPoints": entry("nPoints", "Number of Points",
        "Sample count along a uniform set."),
    "sets.points": entry("points", "Points",
        "Explicit sample points, for a cloud set."),
    "surfaces.*": entry("*", "surfaces/<name>",
        "One named sample surface."),

    # ── other solver controls found in controlDict ────────────────────────────
    "maxDi": entry("maxDi", "Maximum Diffusion Number",
        "Diffusion-number ceiling used alongside maxCo by the conjugate-heat "
        "solvers when adjusting the time step."),
}
