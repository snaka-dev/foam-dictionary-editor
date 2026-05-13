# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from __future__ import annotations

from schemas._base import (
    ChoiceItem, KeySchema,
    FOUNDATION_V13, OPENCFD_SERIES,
)

TARGET_FILE = "controlDict"

SCHEMAS: dict[str, KeySchema] = {
    "startFrom": KeySchema(
        key="startFrom",
        label="Start From",
        description="Controls which time directory is used as the starting point for the run.",
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        note="The common values below are documented for Foundation v13 and commonly used in OpenCFD cases.",
        choices=(
            ChoiceItem(
                "firstTime",
                "Start from the earliest available time directory.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "startTime",
                "Start from the time specified by the startTime entry.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "latestTime",
                "Start from the latest available time directory.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
        ),
    ),
    "stopAt": KeySchema(
        key="stopAt",
        label="Stop At",
        description="Controls how the simulation decides when to stop.",
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        note="These are the standard values documented in Foundation v13 and used across major OpenFOAM distributions.",
        choices=(
            ChoiceItem(
                "endTime",
                "Stop when the specified endTime is reached.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "writeNow",
                "Stop after the current step and write data immediately.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "noWriteNow",
                "Stop after the current step without writing data.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "nextWrite",
                "Stop at the next scheduled write event.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
        ),
    ),
    "writeControl": KeySchema(
        key="writeControl",
        label="Write Control",
        description="Controls when result data is written to disk.",
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        note="This key is common to both major distributions; solver-specific runtime behavior can still vary.",
        choices=(
            ChoiceItem(
                "timeStep",
                "Write every writeInterval time steps.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "runTime",
                "Write every writeInterval seconds of simulated time.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "adjustableRunTime",
                "Write every writeInterval seconds of simulated time and adjust time steps if needed.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "cpuTime",
                "Write every writeInterval seconds of CPU time.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "clockTime",
                "Write every writeInterval seconds of real clock time.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
        ),
    ),
    "writeFormat": KeySchema(
        key="writeFormat",
        label="Write Format",
        description="Controls whether written data is stored as text or binary.",
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        choices=(
            ChoiceItem(
                "ascii",
                "Write output in text format.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "binary",
                "Write output in binary format.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
        ),
    ),
    "writeCompression": KeySchema(
        key="writeCompression",
        label="Write Compression",
        description="Controls whether output files are compressed when written.",
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        note="Foundation documentation explicitly lists on/off and also accepts yes/no and true/false forms.",
        choices=(
            ChoiceItem(
                "off",
                "Do not compress written files.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "on",
                "Compress written files.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "yes",
                "Alternative switch form for enabled state.",
                supported_in=(FOUNDATION_V13,),
                note="Documented switch synonym in Foundation v13 style documentation.",
            ),
            ChoiceItem(
                "no",
                "Alternative switch form for disabled state.",
                supported_in=(FOUNDATION_V13,),
                note="Documented switch synonym in Foundation v13 style documentation.",
            ),
            ChoiceItem(
                "true",
                "Alternative switch form for enabled state.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "false",
                "Alternative switch form for disabled state.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
        ),
    ),
    "timeFormat": KeySchema(
        key="timeFormat",
        label="Time Format",
        description="Controls how time directory names are formatted.",
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        choices=(
            ChoiceItem(
                "fixed",
                "Use fixed-point formatting with digits controlled by timePrecision.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "scientific",
                "Use scientific notation with digits controlled by timePrecision.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "general",
                "Use general formatting and switch to scientific notation when needed.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
        ),
    ),
    "graphFormat": KeySchema(
        key="graphFormat",
        label="Graph Format",
        description="Controls the output format used for graph-like data written by applications or function objects.",
        supported_in=(FOUNDATION_V13,),
        note="Included from Foundation v13 user guide. Verify exact availability in your OpenCFD release if you plan to constrain values strictly.",
        choices=(
            ChoiceItem("raw", "Write raw ASCII columns.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("gnuplot", "Write data in gnuplot format.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("csv", "Write comma-separated values.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("vtk", "Write VTK format.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("ensight", "Write EnSight format.", supported_in=(FOUNDATION_V13,)),
        ),
    ),
    "runTimeModifiable": KeySchema(
        key="runTimeModifiable",
        label="Run-Time Modifiable",
        description="Controls whether dictionaries can be re-read during the run.",
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        note="Foundation v13 examples use yes; OpenCFD examples commonly show true. Both forms are often accepted as dictionary switches.",
        choices=(
            ChoiceItem(
                "true",
                "Allow run-time rereading of supported dictionaries.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "false",
                "Do not reread dictionaries during the run.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "yes",
                "Alternative enabled switch form.",
                supported_in=(FOUNDATION_V13,),
                note="Shown in Foundation v13 user guide examples.",
            ),
            ChoiceItem(
                "no",
                "Alternative disabled switch form.",
                supported_in=(FOUNDATION_V13,),
            ),
        ),
    ),
    "adjustTimeStep": KeySchema(
        key="adjustTimeStep",
        label="Adjust Time Step",
        description="Controls whether the solver adjusts deltaT during the run, usually based on a Courant-number limit.",
        supported_in=(FOUNDATION_V13,),
        note="Documented in Foundation v13 user guide. OpenCFD cases often also use this entry, but check your target release and solver.",
        choices=(
            ChoiceItem("yes", "Enable automatic time-step adjustment.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem("no", "Disable automatic time-step adjustment.", supported_in=(FOUNDATION_V13,)),
            ChoiceItem(
                "true",
                "Alternative enabled switch form.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
            ChoiceItem(
                "false",
                "Alternative disabled switch form.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
        ),
    ),
    "purgeWrite": KeySchema(
        key="purgeWrite",
        label="Purge Write",
        description="Limits how many time directories are kept on disk. A value of 0 disables purging.",
        supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
        choices=(
            ChoiceItem(
                "0",
                "Keep all written time directories.",
                supported_in=(FOUNDATION_V13, OPENCFD_SERIES),
            ),
        ),
    ),
}

