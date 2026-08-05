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

from schemas._base import FOUNDATION_SERIES, OPENCFD_SERIES, ChoiceItem, KeySchema

TARGET_FILE = "controlDict"

_BOTH = (FOUNDATION_SERIES, OPENCFD_SERIES)

# Switch accepts all of these spellings (primitives/bools/Switch/Switch.cxx).
_BOOL_CHOICES = (
    ChoiceItem("yes", "Enabled.", _BOTH),
    ChoiceItem("no", "Disabled.", _BOTH),
    ChoiceItem("true", "Enabled.", _BOTH),
    ChoiceItem("false", "Disabled.", _BOTH),
    ChoiceItem("on", "Enabled.", _BOTH),
    ChoiceItem("off", "Disabled.", _BOTH),
)


def _entry(key: str, label: str, description: str,
           choices: tuple[ChoiceItem, ...] = (), note: str = "") -> KeySchema:
    return KeySchema(
        key=key, label=label, description=description,
        supported_in=_BOTH, choices=choices, note=note,
    )


SCHEMAS: dict[str, KeySchema] = {
    # ── what to run ───────────────────────────────────────────────────────────
    "application": _entry(
        "application", "Application",
        "Solver this case is written for. Not used by the solver itself, but the "
        "Allrun scripts and foamJob read it to decide what to launch.",
    ),
    "libs": _entry(
        "libs", "Libraries",
        "Extra libraries loaded at start-up, as a list of quoted names — needed "
        "for custom boundary conditions, function objects or models.",
    ),

    # ── time ──────────────────────────────────────────────────────────────────
    "startFrom": _entry(
        "startFrom", "Start From",
        "Which time directory the run starts from.",
        (
            ChoiceItem("startTime", "Start from the time given by the startTime entry.", _BOTH),
            ChoiceItem("latestTime", "Start from the latest time directory present. "
                                     "The usual choice for restarting.", _BOTH),
            ChoiceItem("firstTime", "Start from the earliest time directory present.", _BOTH),
        ),
    ),
    "startTime": _entry("startTime", "Start Time",
        "Time value used when startFrom is 'startTime'."),
    "stopAt": _entry(
        "stopAt", "Stop At",
        "Condition that ends the run.",
        (
            ChoiceItem("endTime", "Run until endTime.", _BOTH),
            ChoiceItem("writeNow", "Stop at the end of the current step and write.", _BOTH),
            ChoiceItem("noWriteNow", "Stop at the end of the current step without writing.", _BOTH),
            ChoiceItem("nextWrite", "Stop at the next scheduled write.", _BOTH),
        ),
    ),
    "endTime": _entry("endTime", "End Time",
        "Time at which the run stops, when stopAt is 'endTime'."),
    "deltaT": _entry("deltaT", "Time Step",
        "Time-step size. The initial step only, when adjustTimeStep is on."),

    # ── adjustable time step ──────────────────────────────────────────────────
    "adjustTimeStep": _entry(
        "adjustTimeStep", "Adjust Time Step",
        "Lets the solver resize the time step to satisfy the Courant limits below. "
        "Read by readTimeControls.H, which nearly every transient solver includes.",
        _BOOL_CHOICES,
    ),
    "maxCo": _entry("maxCo", "Maximum Courant Number",
        "Courant-number ceiling used when adjustTimeStep is on. Typically 0.5-1."),
    "maxAlphaCo": _entry("maxAlphaCo", "Maximum Alpha Courant Number",
        "Courant ceiling for the phase fraction in VOF solvers such as interFoam."),
    "maxDeltaT": _entry("maxDeltaT", "Maximum Time Step",
        "Upper bound on the adjusted time step."),

    # ── writing ───────────────────────────────────────────────────────────────
    "writeControl": _entry(
        "writeControl", "Write Control",
        "When results are written.",
        (
            ChoiceItem("timeStep", "Every writeInterval time steps.", _BOTH),
            ChoiceItem("adjustable", "Every writeInterval seconds, adjusting the time "
                                     "step to land exactly on it. The usual choice for "
                                     "adjustable-time-step runs.", _BOTH),
            ChoiceItem("runTime", "Every writeInterval seconds of simulated time.", _BOTH),
            ChoiceItem("adjustableRunTime", "Same as 'adjustable'; the older spelling.", _BOTH),
            ChoiceItem("clockTime", "Every writeInterval seconds of wall-clock time.", _BOTH),
            ChoiceItem("cpuTime", "Every writeInterval seconds of CPU time.", _BOTH),
            ChoiceItem("none", "Never write.", _BOTH),
        ),
    ),
    "writeInterval": _entry("writeInterval", "Write Interval",
        "Interval between writes, read in the unit chosen by writeControl."),
    "purgeWrite": _entry(
        "purgeWrite", "Purge Write",
        "Number of time directories kept, oldest deleted first. 0 keeps everything.",
    ),
    "writeFormat": _entry(
        "writeFormat", "Write Format",
        "Encoding of written field files.",
        (
            ChoiceItem("ascii", "Human-readable text. Larger and slower.", _BOTH),
            ChoiceItem("binary", "Compact and fast, but not directly readable.", _BOTH),
        ),
    ),
    "writePrecision": _entry("writePrecision", "Write Precision",
        "Significant digits written in ascii format. Typically 6-12."),
    "writeCompression": _entry(
        "writeCompression", "Write Compression",
        "Whether written files are gzip-compressed.", _BOOL_CHOICES,
    ),
    "writeVersion": _entry("writeVersion", "Write Version",
        "Format version stamped into the FoamFile header."),
    "writeFrequency": _entry("writeFrequency", "Write Frequency",
        "Write frequency used by the solvers that read it instead of writeInterval."),

    # ── time formatting ───────────────────────────────────────────────────────
    "timeFormat": _entry(
        "timeFormat", "Time Format",
        "How time values are formatted when naming time directories.",
        (
            ChoiceItem("general", "Fixed or scientific, whichever is shorter.", _BOTH),
            ChoiceItem("fixed", "Always fixed-point notation.", _BOTH),
            ChoiceItem("scientific", "Always scientific notation.", _BOTH),
        ),
    ),
    "timePrecision": _entry("timePrecision", "Time Precision",
        "Significant digits in time-directory names. Raise this if steps are so "
        "small that two directories would otherwise collide."),

    # ── runtime behaviour ─────────────────────────────────────────────────────
    "runTimeModifiable": _entry(
        "runTimeModifiable", "Run Time Modifiable",
        "Re-reads the dictionaries at every time step, so edits take effect "
        "without restarting. Costs a file check each step.",
        _BOOL_CHOICES,
    ),
    "graphFormat": _entry(
        "graphFormat", "Graph Format",
        "Format for graph data written by the solvers that produce it.",
        (
            ChoiceItem("raw", "Plain columns of numbers.", _BOTH),
            ChoiceItem("gnuplot", "gnuplot script format.", _BOTH),
            ChoiceItem("xmgr", "Grace/xmgr format.", _BOTH),
            ChoiceItem("jplot", "jPlot format.", _BOTH),
        ),
    ),
    "fileHandler": _entry(
        "fileHandler", "File Handler",
        "I/O implementation used for reading and writing.",
        (
            ChoiceItem("uncollated", "One file per processor directory. The default.", _BOTH),
            ChoiceItem("collated", "Processor data gathered into single files.", _BOTH),
            ChoiceItem("masterUncollated", "Master process performs all I/O.", _BOTH),
        ),
    ),
    "DebugSwitches": _entry("DebugSwitches", "Debug Switches",
        "Per-class debug levels, overriding etc/controlDict for this run."),
    "InfoSwitches": _entry("InfoSwitches", "Info Switches",
        "Per-class info levels, overriding etc/controlDict for this run."),
    "OptimisationSwitches": _entry("OptimisationSwitches", "Optimisation Switches",
        "Low-level I/O and communication tuning, overriding etc/controlDict."),

    # ── function objects ──────────────────────────────────────────────────────
    "functions": _entry(
        "functions", "Functions",
        "Function objects run during the solution — sampling, forces, probes, "
        "field averaging. Each entry is a sub-dictionary, or a #includeFunc line.",
    ),
    "functions.*": _entry(
        "*", "functions/<name>",
        "One function object. The name is chosen by the user; 'type' selects "
        "which function object it is.",
    ),
    # Inside functions{} this is the functionObjects enum, not Time's.
    "functions.writeControl": _entry(
        "writeControl", "Write Control (function object)",
        "When this function object writes. A larger set than the top-level "
        "writeControl, because a function object can also act on start and end.",
        (
            ChoiceItem("timeStep", "Every writeInterval time steps.", _BOTH),
            ChoiceItem("writeTime", "Whenever the solver itself writes.", _BOTH),
            ChoiceItem("adjustable", "Every writeInterval seconds, adjusting the time step.", _BOTH),
            ChoiceItem("runTime", "Every writeInterval seconds of simulated time.", _BOTH),
            ChoiceItem("onEnd", "Once, at the end of the run.", _BOTH),
            ChoiceItem("onStart", "Once, at the start of the run.", _BOTH),
            ChoiceItem("always", "Every time step.", _BOTH),
            ChoiceItem("outputTime", "Same as 'writeTime'; the older spelling.", _BOTH),
            ChoiceItem("clockTime", "Every writeInterval seconds of wall-clock time.", _BOTH),
            ChoiceItem("cpuTime", "Every writeInterval seconds of CPU time.", _BOTH),
            ChoiceItem("none", "Never.", _BOTH),
        ),
    ),
    "functions.executeControl": _entry(
        "executeControl", "Execute Control (function object)",
        "When this function object executes, using the same set of values as its "
        "writeControl.",
        (
            ChoiceItem("timeStep", "Every executeInterval time steps.", _BOTH),
            ChoiceItem("writeTime", "Whenever the solver writes.", _BOTH),
            ChoiceItem("adjustable", "Every executeInterval seconds, adjusting the time step.", _BOTH),
            ChoiceItem("runTime", "Every executeInterval seconds of simulated time.", _BOTH),
            ChoiceItem("onEnd", "Once, at the end of the run.", _BOTH),
            ChoiceItem("onStart", "Once, at the start of the run.", _BOTH),
            ChoiceItem("always", "Every time step.", _BOTH),
            ChoiceItem("none", "Never.", _BOTH),
        ),
    ),
    "functions.writeInterval": _entry("writeInterval", "Write Interval (function object)",
        "Interval between this function object's writes."),
    "functions.executeInterval": _entry("executeInterval", "Execute Interval (function object)",
        "Interval between this function object's executions."),
    "functions.type": _entry("type", "Function Object Type",
        "Which function object this is, e.g. probes, forces, fieldAverage, surfaces."),
    "functions.libs": _entry("libs", "Function Object Libraries",
        "Libraries providing this function object, as a list of quoted names."),
    "functions.enabled": _entry("enabled", "Enabled",
        "Set to false to switch this function object off without deleting it.",
        _BOOL_CHOICES),
    "functions.log": _entry("log", "Log",
        "Writes this function object's results to the run log.", _BOOL_CHOICES),
    "functions.fields": _entry("fields", "Fields",
        "Fields this function object acts on, as a list."),
    "functions.region": _entry("region", "Region",
        "Mesh region this function object applies to, in a multi-region case."),
    "functions.timeStart": _entry("timeStart", "Time Start",
        "Time before which this function object does nothing."),
    "functions.timeEnd": _entry("timeEnd", "Time End",
        "Time after which this function object does nothing."),

    # Common settings across the sampling / field / forces function objects.
    "functions.name": _entry("name", "Name",
        "Name this function object reports under, when it differs from the entry name."),
    "functions.field": _entry("field", "Field",
        "Single field this function object acts on."),
    "functions.writeFields": _entry("writeFields", "Write Fields",
        "Writes the derived fields as well as the summary values.", _BOOL_CHOICES),
    "functions.writeToFile": _entry("writeToFile", "Write To File",
        "Writes results to postProcessing/ as well as the log.", _BOOL_CHOICES),
    "functions.useUserTime": _entry("useUserTime", "Use User Time",
        "Reports time in the user time unit rather than seconds.", _BOOL_CHOICES),
    "functions.regionType": _entry("regionType", "Region Type",
        "What the function object is evaluated over.",
        (
            ChoiceItem("patch", "A boundary patch.", _BOTH),
            ChoiceItem("cellZone", "A cell zone.", _BOTH),
            ChoiceItem("faceZone", "A face zone.", _BOTH),
            ChoiceItem("all", "The whole domain.", _BOTH),
            ChoiceItem("surface", "A sampled surface.", _BOTH),
        )),
    "functions.operation": _entry("operation", "Operation",
        "Reduction applied over the region.",
        (
            ChoiceItem("sum", "Sum of values.", _BOTH),
            ChoiceItem("average", "Arithmetic mean.", _BOTH),
            ChoiceItem("areaAverage", "Area-weighted mean.", _BOTH),
            ChoiceItem("areaIntegrate", "Integral over the area.", _BOTH),
            ChoiceItem("weightedAverage", "Mean weighted by weightField.", _BOTH),
            ChoiceItem("volAverage", "Volume-weighted mean.", _BOTH),
            ChoiceItem("volIntegrate", "Integral over the volume.", _BOTH),
            ChoiceItem("min", "Minimum value.", _BOTH),
            ChoiceItem("max", "Maximum value.", _BOTH),
            ChoiceItem("none", "No reduction.", _BOTH),
        )),
    "functions.weightField": _entry("weightField", "Weight Field",
        "Field used as the weight by the weighted operations."),
    "functions.patches": _entry("patches", "Patches",
        "Boundary patches this function object acts on, as a list."),
    "functions.interpolationScheme": _entry("interpolationScheme", "Interpolation Scheme",
        "How cell values are interpolated to the sample locations.",
        (
            ChoiceItem("cell", "Nearest cell value; piecewise constant.", _BOTH),
            ChoiceItem("cellPoint", "Interpolated from cell and point values.", _BOTH),
            ChoiceItem("cellPointFace", "Cell, point and face values.", _BOTH),
            ChoiceItem("pointMVC", "Mean-value coordinates from point values.", _BOTH),
        )),
    "functions.setFormat": _entry("setFormat", "Set Format",
        "Output format for sampled sets.",
        (
            ChoiceItem("raw", "Plain columns.", _BOTH),
            ChoiceItem("csv", "Comma-separated values.", _BOTH),
            ChoiceItem("gnuplot", "gnuplot script.", _BOTH),
            ChoiceItem("vtk", "VTK format.", _BOTH),
            ChoiceItem("xmgr", "Grace/xmgr format.", _BOTH),
            ChoiceItem("jplot", "jPlot format.", _BOTH),
        )),
    "functions.surfaceFormat": _entry("surfaceFormat", "Surface Format",
        "Output format for sampled surfaces.",
        (
            ChoiceItem("vtk", "VTK format.", _BOTH),
            ChoiceItem("ensight", "EnSight format.", _BOTH),
            ChoiceItem("raw", "Plain columns.", _BOTH),
            ChoiceItem("foam", "OpenFOAM native format.", _BOTH),
            ChoiceItem("starcd", "STAR-CD format.", _BOTH),
        )),
    "functions.formatOptions": _entry("formatOptions", "Format Options",
        "Per-format output options, such as binary/ascii for VTK."),
    "functions.sets": _entry("sets", "Sets",
        "Sample sets — lines or point clouds — evaluated by this function object."),
    "functions.surfaces": _entry("surfaces", "Surfaces",
        "Sample surfaces, such as cutting planes or patch surfaces."),
    "functions.probeLocations": _entry("probeLocations", "Probe Locations",
        "Points sampled by a probes function object, as a list of vectors."),
    "functions.fixedLocations": _entry("fixedLocations", "Fixed Locations",
        "Samples at the requested points rather than snapping to mesh points.",
        _BOOL_CHOICES),
    "functions.rho": _entry("rho", "Density Field",
        "Density field name, or 'rhoInf' to use the fixed value below."),
    "functions.rhoInf": _entry("rhoInf", "Reference Density",
        "Fixed density used to dimensionalise forces in incompressible cases."),
    "functions.CofR": _entry("CofR", "Centre of Rotation",
        "Point about which moments are taken."),
    "functions.mode": _entry("mode", "Mode",
        "Mode of operation, as defined by this function object's type."),
    "functions.result": _entry("result", "Result",
        "Name given to the value this function object produces."),
    "functions.fvOptions": _entry("fvOptions", "fvOptions",
        "Finite-volume options applied by this function object."),

    # Sample-set entries sit one level deeper: functions/<obj>/sets/<name>/<key>,
    # so they resolve through the grandparent form "sets.<key>".
    "sets.*": _entry("*", "sets/<name>",
        "One named sample set."),
    "sets.type": _entry("type", "Set Type",
        "Geometry of the sample set.",
        (
            ChoiceItem("uniform", "Evenly spaced points between start and end.", _BOTH),
            ChoiceItem("lineCell", "One sample per cell crossed by the line.", _BOTH),
            ChoiceItem("lineCellFace", "Cell and face crossings along the line.", _BOTH),
            ChoiceItem("midPoint", "Midpoint of each cell crossed.", _BOTH),
            ChoiceItem("midPointAndFace", "Cell midpoints and face crossings.", _BOTH),
            ChoiceItem("cloud", "An explicit list of points.", _BOTH),
            ChoiceItem("face", "Face crossings only.", _BOTH),
            ChoiceItem("polyLine", "Samples along a multi-segment line.", _BOTH),
        )),
    "sets.axis": _entry("axis", "Axis",
        "Coordinate written in the output's first column.",
        (
            ChoiceItem("x", "x coordinate.", _BOTH),
            ChoiceItem("y", "y coordinate.", _BOTH),
            ChoiceItem("z", "z coordinate.", _BOTH),
            ChoiceItem("xyz", "All three coordinates.", _BOTH),
            ChoiceItem("distance", "Distance along the set from its start.", _BOTH),
        )),
    "sets.start": _entry("start", "Start", "First point of the sample line."),
    "sets.end": _entry("end", "End", "Last point of the sample line."),
    "sets.nPoints": _entry("nPoints", "Number of Points",
        "Sample count along a uniform set."),
    "sets.points": _entry("points", "Points",
        "Explicit sample points, for a cloud set."),
    "surfaces.*": _entry("*", "surfaces/<name>",
        "One named sample surface."),

    # ── other solver controls found in controlDict ────────────────────────────
    "maxDi": _entry("maxDi", "Maximum Diffusion Number",
        "Diffusion-number ceiling used alongside maxCo by the conjugate-heat "
        "solvers when adjusting the time step."),
}
